# Growth Fund Sync Suggestions

**生成时间**: 2026-08-03（第三次执行，纠正此前错误记录后重新核对）
**说明**: 上一版本此文件第 12 行声称"UI 组件的 3 处遗漏已在此前手动修正中处理"，该说法不实——核对 design.md 与代码后确认从未执行任何回写。本次重新如实列出所有未处理的差异。

**对比范围**: design.md vs 实际代码（直接读取代码文件核对，代码库已同步到最新版本）

---

## 📝 design.md 回写建议

### 建议 1：修正 FundPanel 主面板 UI 组件映射表

- [X] **采纳此建议** → ✅ 已回写（design.md 第 203-214 行）

**位置**: `design.md` 附录A「UI 组件映射 → FundPanel 主面板」表格（第 203-210 行）

**当前 design.md 内容**（第 205-210 行）：
```markdown
| demo 元素 ID | Unity 组件 | 职责 |
|-------------|-----------|------|
| `#title-fund` | TextMeshProUGUI `m_TxtTitle` | 基金名称 |
| `#price-fund` | TextMeshProUGUI `m_TxtPrice` | 价格文本 |
| `#btn-purchase` | Button `m_BtnPurchase` | 购买按钮 |
| `#list-reward-tiers` | ScrollRect `m_ScrollRewards` | 奖励列表 |
```

**代码依据**：`MixGrowthFundPage.cs:11-22` 实际声明的字段：
```csharp
[SerializeField] GameObject m_Root;
[SerializeField] TextMeshProUGUI m_TxtTitle;
[SerializeField] TextMeshProUGUI m_TxtDesc;
[SerializeField] Button m_BtnPurchase;
[SerializeField] TextMeshProUGUI m_TxtBtnPurchase;
[SerializeField] SingleScrollView m_ScrollRewards;
```

**差异**：
- ❌ design.md 写的 `m_TxtPrice` 在代码中**不存在**
- ⚠️ 代码里没有单独的价格文本，价格是拼进 `m_TxtBtnPurchase` 的按钮文案里的（`MixGrowthFundPage.cs:126-128`："购买"文案里带价格：`"UI_MixGrowthFundPage_BtnPurchase_Buy".ToLanguageF(price)`）
- ➕ 代码里有但表格没写：`m_Root`（面板根节点）、`m_TxtDesc`（描述文本）、`m_TxtBtnPurchase`（购买按钮文案，含价格）
- 类型也不同：design.md 写 `ScrollRect m_ScrollRewards`，代码实际是 `SingleScrollView m_ScrollRewards`

**建议改为**：
```markdown
| demo 元素 ID | Unity 组件 | 职责 |
|-------------|-----------|------|
| `#root-panel` | GameObject `m_Root` | 面板根节点 |
| `#title-fund` | TextMeshProUGUI `m_TxtTitle` | 基金名称 |
| `#desc-fund` | TextMeshProUGUI `m_TxtDesc` | 基金描述文本 |
| `#btn-purchase` | Button `m_BtnPurchase` | 购买按钮 |
| `#txt-btn-purchase` | TextMeshProUGUI `m_TxtBtnPurchase` | 购买按钮文案（含价格，如"购买 30元"/"已购买"） |
| `#list-reward-tiers` | SingleScrollView `m_ScrollRewards` | 奖励列表（回调模式，非 ScrollRect 手动 Instantiate） |
```

---

### 建议 2：RewardCell 表格改为实际的三层组件结构（Cell → TierRow → RewardCell）

- [X] **采纳此建议** → ✅ 已回写（design.md 第 216-236 行）

**位置**: `design.md` 附录A「UI 组件映射 → RewardCell 奖励格子」表格（第 213-220 行）

**当前 design.md 内容**：
```markdown
| demo 元素 | Unity 组件 | 职责 |
|----------|-----------|------|
| `#cell-{free/pay}-{id}` | GameObject | 格子容器 |
| `#icon-{free/pay}-{id}` | Button `m_BtnClaim` | 可点击图标 |
| `.lock-badge` | GameObject `m_LockBadge` | 锁图标 |
| `#redpoint-{free/pay}-{id}` | GameObject `m_RedPoint` | 红点 |
```

**代码依据**：实际实现拆成了两层组件，design.md 没有反映这个层级结构：

`MixGrowthFundRewardTierRow.cs`（每档一行，免费列+投资列的容器）：
```csharp
[SerializeField] TextMeshProUGUI m_TxtCondition;      // 条件文案，如 "Lv.30/Lv.30"
[SerializeField] LRProgressBar m_ConditionBar;         // 条件进度条
[SerializeField] MixGrowthFundRewardCell m_FreeCell;   // 免费奖励格子
[SerializeField] MixGrowthFundRewardCell m_PayCell;    // 投资奖励格子
```

`MixGrowthFundRewardCell.cs`（单个格子，免费/投资各一个实例）：
```csharp
[SerializeField] Transform m_ImgIconRoot;    // 奖励图标容器（非 Button，用 ItemIconBase 点击）
[SerializeField] GameObject m_LockBadge;     // 锁图标
[SerializeField] GameObject m_RedPoint;      // 红点
[SerializeField] GameObject m_ClaimedMask;   // 已领取遮罩（design.md 未提及）
```

**差异**：
- ❌ design.md 写的 `m_BtnClaim` 不存在。实际是 `m_ImgIconRoot`（挂 `ItemIconBase` 组件，点击事件是 `onClick` 回调而非 Button 组件）
- ➕ design.md 没有反映 `TierRow` 这一层（条件文案 `m_TxtCondition` + 进度条 `m_ConditionBar` + 免费/投资两个 Cell 的容器）
- ➕ 缺少 `m_ClaimedMask`（已领取遮罩）

**建议改为**（拆成两张表反映实际层级）：
```markdown
### RewardTierRow 档位行（每档一行，包含条件展示 + 免费/投资两个格子）

| demo 元素 | Unity 组件 | 职责 |
|----------|-----------|------|
| `#condition-text` | TextMeshProUGUI `m_TxtCondition` | 条件进度文案（如"Lv.30/Lv.30"） |
| `#condition-bar` | LRProgressBar `m_ConditionBar` | 条件进度条 |
| `#cell-free` | MixGrowthFundRewardCell `m_FreeCell` | 免费奖励格子 |
| `#cell-pay` | MixGrowthFundRewardCell `m_PayCell` | 投资奖励格子 |

### RewardCell 奖励格子（免费/投资各一个实例）

| demo 元素 | Unity 组件 | 职责 |
|----------|-----------|------|
| `#icon-root-{free/pay}` | Transform `m_ImgIconRoot` | 奖励图标容器（挂 ItemIconBase，点击回调而非 Button） |
| `.lock-badge` | GameObject `m_LockBadge` | 锁图标 |
| `#redpoint-{free/pay}` | GameObject `m_RedPoint` | 红点 |
| `.claimed-mask` | GameObject `m_ClaimedMask` | 已领取遮罩 |
```

---

### 建议 3：补充 CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD 的具体参数清单

- [x] **采纳此建议** → ✅ 已回写（design.md 附录B「协议」章节 `OnCustomGetReward` 小节）

**位置**: `design.md` 附录A「网络协议」表格第 174 行 之后（或附录B「协议」章节 `OnCustomGetReward` 小节，第 421-422 行）

**代码依据**：
```cpp
// MixGrowthFundEventCallBack.cpp:143-147
int MixGrowthFundModule::OnCustomGetReward(const PERSISTID &self, const PERSISTID &sender, const IVarList &args)
{
    return g_pMixGrowthFundModule->GetReward(g_pKernel, self, args.IntVal(1), args.IntVal(2), args.IntVal(3));
}
// GetReward 签名：GetReward(IKernel*, PERSISTID&, int nActivityID, int nEntryID, int nRecvType)
```

**差异**：design.md 只写了"领取单格奖励（免费/投资）"，从未列出这条协议的 3 个具体参数

**补充内容**：
```markdown
**协议参数**（C→S `CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD`，对应 `OnCustomGetReward`）：
1. activityId (int) — 活动ID
2. rewardId (int) — 档位ID（对应 GetReward 的 nEntryID 参数）
3. recvType (int) — 领取类型（免费/投资，对应 GetReward 的 nRecvType 参数，具体枚举值需与 STATIC_OPT 相关常量核对）
```

---

## ⚠️ 已知但未列为回写建议的问题（需人工先决策，见下）

### 问题 1：客户端从未调用 CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD，实际点击行为是"统一一键领取"

**代码位置**: `MixGrowthFundPage.cs:214-223`
```csharp
void OnClaimReward(int activityId, int rewardId, bool isPayColumn)
{
    if (m_Kernel.GetModule<BagDataModule>().IsAnyBagFull()) { ... }
    m_Module.SendQuickGetAllRewardMsg(activityId);   // rewardId、isPayColumn 参数完全未使用
}
```

**现象**：格子把 `rewardId`/`isPayColumn` 传给 `OnClaimReward`，但该函数忽略这两个参数，只调用一键领取协议（`CLIENT_CUSTOMMSG_QUICK_GET_ACTIVITY_REWARD`）。经代码搜索确认，客户端代码里**没有任何地方**调用 973 号协议（即建议 3 里补充参数的那条协议）。

**决策结果（已更正）**：~~不改 design.md，判定为代码 bug~~ ——此结论已被用户否定并纠正。**正确决策是：一键领取就是产品需求，改 design.md/spec.md 以反映这个真实行为**，客户端代码不需要改。

**已执行的回写**：
- design.md：协议设计、网络协议表、交互流程、附录B协议说明均已改为"点击任意格子统一走一键领取协议 `CLIENT_CUSTOMMSG_QUICK_GET_ACTIVITY_REWARD`，这是产品需求"；`CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD`（单格领取）标注为"服务端已实现但客户端未调用，保留作为协议能力"
- specs/growth-fund/spec.md："免费奖励领取"/"投资奖励领取"两个 Requirement 补充说明；"双轨奖励独立领取"改名为"双轨奖励独立解锁，合并领取"，Scenario 按一键领取语义重写
- tasks.md：1.1 Contract 清单补充一键领取协议、标注单格领取协议未被调用

---

## 📊 统计

- design.md 回写建议：3 项，均已采纳并回写（UI 组件×2 + 协议参数×1）
- 一键领取 vs 单格领取的行为矛盾：已确认为产品需求，design.md/spec.md/tasks.md 均已同步更新，无遗留代码问题

---

## 📋 处理状态

本次 sync 已完成：3 项回写建议 + 一键领取语义澄清，已写入 design.md、spec.md、tasks.md 三个文件。`openspec validate growth-fund` 校验通过。
