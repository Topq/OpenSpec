# 成长基金 Test Validation Report

**生成时间**: 2026-07-31  
**TC 总数**: 20 条（TC-growth-fund-01 ~ TC-growth-fund-20）  
**静态验证**: 11 条（其中 ✅ 6 条 / ❌ 3 条未覆盖 / ⚠️ 2 条部分覆盖）  
**需人工执行**: 14 条（集成测试 9 条 + 联调测试 5 条）

> 注：部分 TC 兼属多类，总计大于 20。

---

## 📊 静态验证结果概览

| TC | 标题 | 结论 | 备注 |
|----|------|------|------|
| TC-02 | 已购买玩家查看面板 | ✅ | 购买按钮禁用逻辑存在 |
| TC-03 | 售卖期结束后查看面板 | ❌ | "售卖已结束"标签未实现 |
| TC-05 | 未达成档位条件进度 | ❌ | amType 硬编码 0，条件文案格式失效 |
| TC-08 | 条件未达成时点击 | ✅ | 不触发领取协议 |
| TC-09 | 已领取免费奖励 | ✅ | Claimed 状态显示正确 |
| TC-11 | 未购买点击投资奖励 | ✅ | LockedByPurchase + 服务端双重保护 |
| TC-14 | 售卖期未购买红点 | ⚠️ | IsNewActivity 框架处理，但 OnRedChanged 逻辑有误 |
| TC-15 | 可领免费奖励红点 | ❌ | HasRedPoint CurNum 未从 Record 读取 |
| TC-16 | 可领投资奖励红点 | ❌ | 同 TC-15 |
| TC-17 | 全部领完无红点 | ⚠️ | HasRedPoint 未过滤 activityId |

---

## 🐛 静态验证发现的问题

### ❌ Bug-1（高）：条件文案类型被硬编码为 0

**文件**: `Assets/Script/UISript/WelfareActivityPanel/MixGrowthFundPanel/MixGrowthFundRewardTierRow.cs:21`

```csharp
int amType = 0; // 由 ActivityGoal 配置得到，参见 MixGrowthFundModule.GetConditionText
string conditionText = GameWorld.gameKernel.GetModule<MixGrowthFundModule>()
    .GetConditionText(amType, tierData.CurNum, tierData.TargetNum);
```

`GetConditionText` 有针对等级(1)、爬塔(37)、登录(244)、任务(8)、战力(109) 的专属格式，但 amType 永远传 0 → 始终走 `default` 分支 → 所有档位显示 `{0}/{1}`，TC-04/05/18/19 中期望的 `Lv.{0}/Lv.{1}` 格式无法呈现。

**修复方向**: `QueryInfo` 服务端已在 outArgs 中输出 `entryCfg->strLanguage` 和 `entryCfg->strUrl`，但客户端 `ParseQueryInfo` 跳过了这两个字段（`index += 5` 跳过了 FreeReward/FreeHighlight/PayReward/PayHighlight/LanguagePack，`index += 1` 跳过 Url）。需要从 outArgs 解析出 amType（或直接用 `activity_goal` 本地配表的 `type` 字段），传入 `MixGrowthFundRewardTierRow.SetData`。

**影响 TC**: TC-04, TC-05, TC-18, TC-19

---

### ❌ Bug-2（高）：HasRedPoint 的 CurNum/TargetNum 恒为 0

**文件**: `Assets/Script/LogicModule/ActivityModule/MixGrowthFundModule/MixGrowthFundModule.cs:179-196`

```csharp
public bool HasRedPoint(int activityId)
{
    bool isPurchased = IsPurchased(activityId);
    foreach (var kvp in m_RewardStatuses)
    {
        var status = kvp.Value;
        bool goalFinished = status.CurNum >= status.TargetNum;  // 恒 0 >= 0 = true
        if (goalFinished && status.FreeStatus == 0)
            return true;
        ...
    }
}
```

`MixGrowthFundRewardStatus.CurNum` / `.TargetNum` 在 `RefreshRewardStatuses`（:137）只从 `BA_MIX_GROWTH_FUND_REWARD_REC` 读取 FreeStatus/PaidStatus，从未写入 CurNum/TargetNum → 两个字段始终为 struct 默认值 0 → `goalFinished` 永远为 true → 任何未领取的奖励均触发红点，与条件是否达成无关。

**影响 TC**: TC-15, TC-16, TC-17

---

### ❌ Bug-3（高）：OnRedChanged 比较值与服务端语义相反

**文件**: `Assets/Script/LogicModule/ActivityModule/MixGrowthFundModule/MixGrowthFundModule.cs:109-115`

```csharp
int freeState = rec.GetInt(i, (int)BAMixGrowthFundRewardRecCol.FreeRewardState);
int paidState = rec.GetInt(i, (int)BAMixGrowthFundRewardRecCol.PaidRewardState);
if (freeState == (int)BARewardState.Can || paidState == (int)BARewardState.Can)
    return true;
```

`BARewardState.Can = 1`，但服务端 `MIX_GROWTH_FUND_REWARD_REC` 中：
- `MIX_GROWTHFUND_REWARD_UNCLAIMED = 0`
- `MIX_GROWTHFUND_REWARD_RECEIVED = 1`

即 1 代表**已领取**，不是可领取。`OnRedChanged` 当前在奖励**已领取时**返回 true（有红点），而在奖励**未领取时**返回 false（无红点）——逻辑完全相反。

此处应改为：
```csharp
if (freeState == MIX_GROWTHFUND_REWARD_UNCLAIMED || paidState == MIX_GROWTHFUND_REWARD_UNCLAIMED)
```
或直接复用 `HasRedPoint` 逻辑。

**影响 TC**: TC-14, TC-15, TC-16, TC-17

---

### ❌ Bug-4（中）：HasRedPoint 遍历未过滤 activityId

**文件**: `Assets/Script/LogicModule/ActivityModule/MixGrowthFundModule/MixGrowthFundModule.cs:182`

`foreach (var kvp in m_RewardStatuses)` 遍历了所有活动的奖励记录，但传入的 `activityId` 只用于 `IsPurchased(activityId)` 判断，档位记录不按 activityId 过滤。TC-20 多基金并存时，基金 B 的未领取记录会影响基金 A 的红点判断。

**影响 TC**: TC-20

---

### ⚠️ 未覆盖（低）：TC-03 "售卖已结束"标签未实现

**文件**: `Assets/Script/UISript/WelfareActivityPanel/MixGrowthFundPanel/MixGrowthFundPage.cs:129-132`

```csharp
m_BtnPurchase.interactable = !isPurchased;
m_TxtBtnPurchase.text = isPurchased
    ? "UI_MixGrowthFundPage_BtnPurchase_Purchased".ToLanguage()
    : "UI_MixGrowthFundPage_BtnPurchase_Buy".ToLanguageF(price);
```

TC-03 预期在售卖期结束后显示"售卖已结束"标签并禁用购买按钮（未购买玩家）。当前代码只处理 isPurchased 两种状态，无活动时段状态（`IsActivityActive` 已实现，但 `MixGrowthFundPage` 中未调用）。售卖期结束 + 未购买时，按钮仍会显示"购买"文案（只是因活动数据不再下发而不可用）。

**影响 TC**: TC-03

---

## ✅ 静态验证通过详情

### ✅ TC-02：已购买玩家查看面板

**验证路径**:
1. 购买记录写入服务端 `GROWTH_FUND_OPEN_REC` → 客户端 Record Hook 触发 `OnOpenRecChanged` → `RefreshPurchasedFunds` → `m_PurchasedFunds[activityId] = true`
2. `RefreshView` 调用 `IsPurchased(activityId)` → `m_PurchasedFunds.GetValueOrDefault(activityId, false)`
3. `m_BtnPurchase.interactable = !isPurchased` → 按钮不可点击 ✅
4. `m_TxtBtnPurchase.text = "UI_MixGrowthFundPage_BtnPurchase_Purchased"` ✅
5. `GetPaidRewardState(status, tierData, isPurchased=true)` → 不返回 LockedByPurchase ✅

**代码位置**: `MixGrowthFundPage.cs:121-136`

---

### ✅ TC-08：条件未达成时点击免费奖励图标

**验证路径**:
1. `GetFreeRewardState`: `FreeStatus != 1` 且 `CurNum < TargetNum` → 返回 `CellClaimState.Locked`
2. `MixGrowthFundRewardCell.SetData`: state != Claimable → `m_ItemIcon.onClick = OnItemIconClick`（仅弹 ItemTips）
3. `OnItemIconClick` 调用 `BagHelper.OpenItemTips`，不调用 `m_OnClaimClick` → 不触发 `CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD` ✅

**代码位置**: `MixGrowthFundRewardCell.cs:47-57`, `MixGrowthFundPage.cs:169-179`

---

### ✅ TC-09：已领取后查看免费奖励

**验证路径**:
1. 服务端 `MIX_GROWTH_FUND_REWARD_REC.FREE_REWARD_STATUS = 1` → 客户端 `status.FreeStatus = 1`
2. `GetFreeRewardState`: `FreeStatus == 1` → 返回 `CellClaimState.Claimed`
3. `UpdateVisualState`: `m_ClaimedMask.SetActive(true)`, `m_RedPoint.SetActive(false)` ✅
4. onClick = OnItemIconClick → 不触发领取协议 ✅

**代码位置**: `MixGrowthFundRewardCell.cs:62-82`

---

### ✅ TC-11：未购买时点击投资奖励图标

**验证路径**:
1. `GetPaidRewardState(status, tierData, isPurchased=false)`: 第一个 if → 返回 `CellClaimState.LockedByPurchase`
2. `UpdateVisualState`: `locked = true` → `m_LockBadge.SetActive(true)`, onClick = OnItemIconClick
3. 不触发 `CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD` ✅
4. 服务端 `SendPayReward` 另有 `IsFundActivate` 校验作双重保护 ✅

**代码位置**: `MixGrowthFundPage.cs:182-197`, `MixGrowthFundFunc.cpp:372-395`

---

### ✅ TC-07/TC-10 服务端奖励发放流程（背包满保护）

**验证路径**（以 TC-07 免费奖励为例）:
1. `OnCustomGetReward` → `GetReward(nRecvType=FREE)` → `SendFreeReward`
2. `CheckRewardCanGet(isFree=true)`: 查 `MIX_GROWTH_FUND_REWARD_REC`，`FREE_REWARD_STATUS == UNCLAIMED(0)` 才允许 ✅
3. `SendReward` → `CheckRewardCanGet(ActivityGoal)`: 状态 == `ACTIVITY_GOAL_REWARD_OPEN` 才允许 ✅
4. `TestAutoAddItems` → 背包满时返回 `ERR_BAG_FULL`，不发放不写 Record ✅
5. 背包有位置：`SetInt(row, col, RECEIVED)` 先写 Record → 再 `AutoAddItems` ✅

**代码位置**: `MixGrowthFundFunc.cpp:275-395`

---

## 🧪 人工测试清单（14 条）

### 集成测试（9 条，需客户端连接服务端）

- [ ] **TC-01** 售卖期内未购买 → 点击购买完成支付
  - **前置**: 基金处于售卖期，玩家未购买
  - **操作**: 点击"购买" → SDK 支付 → 完成
  - **预期**: 购买按钮变"已购买"，投资列解锁，已达成条件档位高亮+红点
  - **验证点**: 客户端 `m_PurchasedFunds[activityId] = true`；已达成档位的 `GetPaidRewardState` 返回 Claimable

- [ ] **TC-03** 售卖期结束后查看面板
  - **前置**: 活动售卖期已过期
  - **操作**: 打开基金面板
  - **预期**: 购买按钮置灰，显示"售卖已结束"
  - **已知缺陷**: Bug-5（"售卖已结束"标签未实现），此 TC 预计失败，需先修复

- [ ] **TC-04** 等级达到档位条件 → 解锁
  - **前置**: 某档配置等级 30，玩家当前 29 级
  - **操作**: 升级到 30 级
  - **预期**: 该档解锁，红点出现，条件进度显示"Lv.30/Lv.30"
  - **已知缺陷**: Bug-1（amType=0 → 条件文案不显示 Lv 格式），此 TC 条件进度预计失败

- [ ] **TC-06** 按顺序解锁（不可跳档）
  - **前置**: 3 档条件分别达成，档位 1 未领
  - **操作**: 尝试点击档位 2 领取
  - **预期**: 服务端拒绝，档位 2 不发放
  - **验证点**: 服务端 `ACTIVITY_GOAL_REC_COL_REWARD_STATUS = ACTIVITY_GOAL_REWARD_OPEN` 状态校验是否包含前档已领逻辑（设计文档描述此逻辑，但未在代码中找到明确实现，需联调确认）

- [ ] **TC-07** 条件达成后领取免费奖励
  - **前置**: 某档解锁且前档已领
  - **操作**: 点击免费奖励图标
  - **预期**: 奖励到背包，图标变灰，红点消失
  - **验证点**: `FREE_REWARD_STATUS` 从 0 变 1

- [ ] **TC-10** 购买后领取投资奖励
  - **前置**: 已购买，某档解锁，前档已领
  - **操作**: 点击投资奖励图标
  - **预期**: 奖励到背包，`PAID_REWARD_STATUS` 从 0 变 1

- [ ] **TC-12** 先领免费后领投资（独立性）
  - **前置**: 某档两列均解锁，已购买
  - **操作**: 先领免费，再领投资
  - **预期**: 两列状态互不影响

- [ ] **TC-13** 仅领免费不领投资
  - **前置**: 某档两列均解锁，已购买
  - **操作**: 只领免费，不领投资
  - **预期**: 投资列保持 Claimable，下一档免费可正常领取

- [ ] **TC-14** 售卖期内未购买红点
  - **前置**: 活动售卖期内，玩家未购买
  - **操作**: 查看主界面
  - **预期**: 活动入口图标显示红点
  - **已知风险**: Bug-3（OnRedChanged 逻辑相反），此红点可能依赖 `IsNewActivity` 框架处理，需联调确认实际表现

### 联调测试（5 条，需服务端 + 客户端配合）

- [ ] **TC-15** 可领免费奖励时红点
  - **前置**: 某档条件达成，免费奖励未领
  - **预期**: 奖励图标显示红点
  - **已知缺陷**: Bug-2 + Bug-3，红点逻辑有误，预计失败

- [ ] **TC-16** 可领投资奖励时红点
  - **前置**: 已购买，某档达成，投资未领
  - **预期**: 奖励图标显示红点
  - **已知缺陷**: Bug-2 + Bug-3，预计失败

- [ ] **TC-17** 全部领完无红点
  - **前置**: 所有档位全部领取
  - **预期**: 活动入口无红点
  - **已知缺陷**: Bug-2 + Bug-3，预计失败

- [ ] **TC-18** 配置等级解锁型基金
  - **前置**: 策划配置 10 档等级解锁型基金
  - **操作**: 读取配置，打开面板
  - **预期**: 10 档正确展示，条件显示 `Lv.X/Lv.Y`
  - **已知缺陷**: Bug-1，条件格式不正确

- [ ] **TC-19** 配置爬塔解锁型基金
  - **前置**: 策划配置爬塔型基金
  - **预期**: 条件格式显示"爬塔X/爬塔Y"
  - **已知缺陷**: Bug-1

- [ ] **TC-20** 多基金并存
  - **前置**: 配置两个 ActiveId 不同的基金
  - **操作**: 分别操作两个基金的购买和领取
  - **预期**: 记录互相独立，红点互不干扰
  - **已知缺陷**: Bug-4（HasRedPoint 跨活动污染）

---

## 📋 后续步骤

### 必修（影响功能正确性）

1. **修复 Bug-1**：`MixGrowthFundRewardTierRow.SetData` 需接收 `amType` 参数。方案：从 `TDActivityGoalTable.GetData` 本地查表取 `type` 字段，或从 `ParseQueryInfo` 新增对 LanguagePack/AM_TYPE 字段的解析。影响 TC-04/05/18/19。

2. **修复 Bug-2**：`RefreshRewardStatuses` 需同时缓存 CurNum/TargetNum（可在 `ParseQueryInfo` 回调时写入，或查 ActivityGoal Record 的进度数据）。影响 TC-15/16/17。

3. **修复 Bug-3**：`OnRedChanged` 中将 `BARewardState.Can` 改为检查 UNCLAIMED(0) 状态，即 `freeState == 0` 表示可领取（需同时结合条件已达成，单纯 ==0 还会在条件未达成时误报，应配合 ActivityGoal 状态或修复 Bug-2 后用 `HasRedPoint` 逻辑替代）。影响 TC-14/15/16/17。

4. **修复 Bug-4**：`HasRedPoint` 遍历时添加 activityId 过滤（`key >> 32 == activityId`）。影响 TC-20。

### 建议修复

5. **补充 TC-03 售卖期结束 UI 状态**：在 `RefreshView` 中检查 `IsActivityActive(activityId)` 并添加相应显示状态。

### QA 执行

6. 修复 Bug-1~4 后，执行本清单全部 14 条人工测试用例。
7. 优先执行：TC-07（核心领取）、TC-01（核心购买）、TC-12/13（双轨独立性）。
8. 红点相关 TC（14/15/16/17）需在修复 Bug-2+3 后执行。
