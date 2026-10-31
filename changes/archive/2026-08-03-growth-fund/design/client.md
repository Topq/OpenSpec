# design-client.md

## 功能概述

实现成长基金活动客户端逻辑：玩家购买基金后，达成条件逐档解锁双轨奖励。复用服务端已有 MixGrowthFundModule (BA_TYPE=1018)。

**设计决策**:
- 复用服务端 MixGrowthFundModule (已完整实现)
- 接入 BusinessActivityModule 框架
- 新建客户端 MixGrowthFundModule.cs
- 新建 MixGrowthFundPanel UI

## 架构设计

### 模块依赖

```
MixGrowthFundModule (新建)
  ├─ BusinessActivityModule (活动注册、红点、菜单)
  ├─ TradeModule/MallModule (充值商品关联)
  ├─ UIModule (面板打开)
  └─ RedPointModule (红点通知)
```

## 文件结构

### 新建文件

| 文件路径 | 职责 |
|---------|------|
| `Assets/Script/LogicModule/ActivityModule/MixGrowthFundModule/MixGrowthFundModule.cs` | 核心业务模块 |
| `Assets/Script/LogicModule/ActivityModule/MixGrowthFundModule/MixGrowthFundModule_Net.cs` | 网络协议处理 |
| `Assets/Script/UISript/WelfareActivityPanel/MixGrowthFundPanel/MixGrowthFundPage.cs` | UI 主面板 |
| `Assets/Script/UISript/WelfareActivityPanel/MixGrowthFundPanel/MixGrowthFundRewardCell.cs` | 奖励格子组件 |

### 修改文件

| 文件路径 | 修改内容 |
|---------|---------|
| `Assets/Script/Main/GameLauncher.cs:715` | 取消注释 `new MixGrowthFundModule()` |
| `Assets/Script/LogicModule/TradeModule/Mall/MallModule.cs:24,202` | 取消注释 `m_MixGrowthFundModule` 相关逻辑 |
| `Assets/Script/LogicModule/GeneralActiveModule/GeneralActiveModule.cs:22,390` | 取消注释红点检查 |
| `Assets/Script/Define/CommandID.cs` | 添加 `OnGrowthFundHistory` / `OnMixGrowthFundRefresh` / `OnMixGrowthFundRewardClaim` |

## 核心数据结构

### Record 定义

已核对客户端现有镜像枚举 `BusinessActivityDefine.cs`（`BAGrowthFundOpenRecCol` / `BAMixGrowthFundRewardRecCol`）与服务端真实结构一致，此前草稿中的 GOAL_ID / GOAL_FINISH_FLAG 两列不存在，已删除：

```csharp
// GROWTH_FUND_OPEN_REC  ->  BAGrowthFundOpenRecCol
// Col 0: ActivityID (int)

// MIX_GROWTH_FUND_REWARD_REC  ->  BAMixGrowthFundRewardRecCol
// Col 0: Key (long, activityID/rewardID merge)
// Col 1: ActivityID (int)
// Col 2: RewardID (int)
// Col 3: FreeRewardState (int, 0=unclaimed, 1=claimed)
// Col 4: PaidRewardState (int, 0=unclaimed, 1=claimed)
```

**档位条件是否达成不在这张表里**。服务端 `OnBizActivCustomQueryInfo` 下发的每档数据里，最后两个字段是 `CurNum`（当前进度）和 `TargetNum`（目标进度），来自通用 `ActivityGoalModule` 的 `ActivityGoalProgress`（见 design/server.md「Record 表」章节的 `ACTIVITY_GOAL_REC`）。客户端用 `CurNum >= TargetNum` 判断条件是否达成，不存在单独的 "GoalFinishFlag" 字段。

### 客户端状态缓存

```csharp
public class MixGrowthFundModule : ILogicModule
{
    Dictionary<int, bool> m_PurchasedFunds = new();
    Dictionary<long, MixGrowthFundRewardStatus> m_RewardStatuses = new();
}

public struct MixGrowthFundRewardStatus
{
    public int RewardId;
    public int FreeStatus;
    public int PaidStatus;
    public long CurNum;     // 来自 ActivityGoalProgress，条件当前进度
    public long TargetNum;  // 来自 ActivityGoalProgress，条件目标值
}
```

## 网络协议

已核对通用 `BusinessActivityModule_Net.cs` 和 `ClientCustomID.cs` 的真实协议常量，此前草稿中的 `C2S_BIZACTIV_START`/`S2C_BIZACTIV_START`/`S2C_BIZACTIV_REMIND` 不存在，本模块复用通用 BusinessActivity 框架的协议（非模块专属），修正为：

| 协议名 | 方向 | 用途 | 对应服务端处理（见 design/server.md「协议」章节） |
|-------|------|------|------|
| `CLIENT_CUSTOMMSG_NOTIFY_OPEN_ACTIVITY_PANEL` | C→S | 通知面板打开（触发 `BuildData`） | `OnBizActivStart` |
| `CLIENT_CUSTOMMSG_QUERY_ACTIVITY_INFO` | C→S（同步RPC，outArgs 即返回数据） | 拉取活动数据（主配置+每档奖励+条件进度），无独立 S2C 消息 | `OnBizActivCustomQueryInfo` |
| `CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD` | C→S | 领取单格奖励（免费/投资） | `OnCustomGetReward` |
| （一键领取，挂载于 `BizActivNtf_OnQuickGetAllReward`，客户端侧调用入口需在 `MixGrowthFundModule_Net.cs` 中新增） | C→S | 一键领取 | `OnBizActivCustomQuickGetAllReward` |
| `COMMAND_BIZ_ACTIV_CHANGED`（id=263，通用活动变化通知，非模块专属） | S→C | 服务端推送活动数据变化（收到后客户端重新发起 `CLIENT_CUSTOMMSG_QUERY_ACTIVITY_INFO`） | 服务端在购买/领取后触发该 command |

**协议参数格式** (S2C `OnBizActivCustomQueryInfo` outArgs，已核对 `MixGrowthFundModule::QueryInfo` 真实代码顺序):

先是基金主配置（5 个字段，一次性）：
```
RechargeId(int), Direct(string), DisplayType(int), Name(string), NextActiveName(string)
```
然后每档奖励重复 9 个字段（按 `activity_goal` 配置的档位顺序）：
```
RewardId(int), FreeReward(string), FreeHighlight(string), PayReward(string), PayHighlight(string),
LanguagePack(string), Url(string), CurNum(int64), TargetNum(int64)
```
客户端按固定字段数逐组解析 outArgs，不是分号拼接的字符串。

### amType 数据来源（用于条件文案映射）

outArgs 中不包含 amType 字段。客户端 `amType` 应从本地已同步的 `activity_goal` 配置表读取
（`TDActivityGoalTable.GetData(goalId).Type`），`goalId` 通过 `activity_mix_growthfund_reward.xlsx`
的 `RewardId` 与 `activity_goal.xlsx` 交叉关联获得（见"配表依赖"章节）。

`MixGrowthFundRewardTierRow.SetData` 必须接收 amType 参数并传给 `GetConditionText`，
不能硬编码为固定值。

## UI 组件映射

### FundPanel 主面板

| demo 元素 ID | Unity 组件 | 职责 |
|-------------|-----------|------|
| `#title-fund` | TextMeshProUGUI `m_TxtTitle` | 基金名称 |
| `#price-fund` | TextMeshProUGUI `m_TxtPrice` | 价格文本 |
| `#btn-purchase` | Button `m_BtnPurchase` | 购买按钮 |
| `#list-reward-tiers` | SingleScrollView `m_ScrollRewards` | 奖励列表（回调模式） |

### RewardRow 奖励行

demo 原型（`RewardRow.tsx`）包含：进度条 + 免费格子 + 投资格子

Unity 实现：`MixGrowthFundRewardTierRow.cs`

| demo 组件 | Unity 字段 | 类型 | 职责 |
|----------|-----------|------|------|
| `.condition-text` | `m_TxtCondition` | TextMeshProUGUI | 条件进度文本 |
| `control.progress` | `m_ConditionBar` | LRProgressBar | 进度条（0.0-1.0） |
| `RewardCell(free)` | `m_FreeCell` | MixGrowthFundRewardCell | 免费奖励格子 |
| `RewardCell(pay)` | `m_PayCell` | MixGrowthFundRewardCell | 投资奖励格子 |

### RewardCell 奖励格子

demo 原型（`RewardCell.tsx`）：可点击图标 + 锁定标记 + 红点 + 已领取遮罩

Unity 实现：`MixGrowthFundRewardCell.cs`

| demo 组件 | Unity 字段 | 类型 | 职责 |
|----------|-----------|------|------|
| `button[data-lr-action]` | `m_BtnClaim` | Button | 点击领取按钮 |
| `.reward-icon-glyph` | `m_ImgIcon` | Image | 奖励图标 |
| `.lock-badge` | `m_LockBadge` | GameObject | 锁定标记（🔒） |
| `feedback.red-point` | `m_RedPoint` | GameObject | 可领取红点 |
| `.is-claimed` mask | `m_ClaimedMask` | GameObject | 已领取遮罩 |

状态映射逻辑（`MixGrowthFundRewardCell.SetData`）：
- `Locked` / `LockedByPurchase` → 显示 `m_LockBadge`，按钮不可交互
- `Claimable` → 显示 `m_RedPoint`，按钮可交互
- `Claimed` → 显示 `m_ClaimedMask`，按钮不可交互

## 状态机定义

### 格子状态枚举

```csharp
public enum CellClaimState
{
    Locked = 0,              // 条件未达成
    LockedByPurchase = 1,    // 未购买基金 (投资奖励)
    Claimable = 2,           // 可领取
    Claimed = 3              // 已领取
}
```

### 状态判定

```csharp
CellClaimState GetFreeRewardState(long key)
{
    if (!m_RewardStatuses.TryGetValue(key, out var s)) return Locked;
    if (s.FreeStatus == 1) return Claimed;
    if (s.CurNum >= s.TargetNum) return Claimable;
    return Locked;
}

CellClaimState GetPaidRewardState(long key, bool isPurchased)
{
    if (!isPurchased) return LockedByPurchase;
    if (!m_RewardStatuses.TryGetValue(key, out var s)) return Locked;
    if (s.PaidStatus == 1) return Claimed;
    if (s.CurNum >= s.TargetNum) return Claimable;
    return Locked;
}
```

## 交互流程

### 打开面板
1. 用户点击入口 → `UIModule.OpenPanel(MixGrowthFundPanel)`
2. 发送 `CLIENT_CUSTOMMSG_NOTIFY_OPEN_ACTIVITY_PANEL(activityId)`
3. 发送 `CLIENT_CUSTOMMSG_QUERY_ACTIVITY_INFO(activityId)`，同步获得 outArgs（主配置+每档奖励+进度）
4. 刷新 UI (购买按钮、奖励列表、进度条)

### 售卖期结束状态
- 打开面板时调用 `BusinessActivityModule.IsActivityOpen(activityId)` 判断售卖期是否已结束
- 已结束：购买按钮置灰，文案改为 "UI_MixGrowthFundPage_BtnPurchase_SaleEnded".ToLanguage()（键名待定，需补充到 Language_Keys.md）
- 未购买玩家的投资奖励列仍带锁（LockedByPurchase）；已购买玩家的投资奖励列正常显示

### 购买基金
1. 点击购买按钮 → `TradeModule.OpenRechargePanel(rechargeId)`
2. 完成支付 → 服务端 `OnGrowthFundDispose` 触发
3. 收到 `COMMAND_BIZ_ACTIV_CHANGED(activityId)` → 重新发送 `CLIENT_CUSTOMMSG_QUERY_ACTIVITY_INFO` 拉取最新数据
4. 刷新 UI (投资奖励解锁、红点更新)

### 领取奖励
1. 点击格子 → 检查状态 → 发送 `CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD`
2. 收到响应 → 更新本地状态 → 刷新 UI → 弹出奖励面板

## 红点逻辑

### 触发条件

```csharp
bool HasRedPoint(int activityId)
{
    bool isPurchased = m_PurchasedFunds.GetValueOrDefault(activityId);
    foreach (var (key, s) in m_RewardStatuses)
    {
        if ((int)(key >> 32) != activityId) continue;  // 多基金并存时必须按 activityId 过滤
        bool goalFinished = s.CurNum >= s.TargetNum;
        if (goalFinished && s.FreeStatus == 0) return true;
        if (isPurchased && goalFinished && s.PaidStatus == 0) return true;
    }
    return false;
}
```

### 传播路径
```
MixGrowthFundModule → BusinessActivityModule → GeneralActiveModule → RedPointModule → UI
```

## 配表依赖

客户端自动生成的表类名遵循「表名去下划线转驼峰 + TD 前缀」规则（参照 `TDActivityDevelopplanPage` ← `activity_developplan_page`），已按修正后的真实表名更新：

| 表名 | 读取字段 | 用途 |
|-----|---------|------|
| `TDActiveFundMain`（表：active_fund_main，此前误写为 TDMixGrowthFundMain） | ActiveId, RechargeId, Direct | 活动主配置 |
| `TDActivityMixGrowthfundReward`（表：activity_mix_growthfund_reward，此前误写为 TDMixGrowthFundReward） | ActiveId, RewardId, FreeReward, PayReward | 奖励配置 |
| `TDRecharge` | RechargeId, Price | 充值商品 |

## Open Questions

### Q1: 是否支持多基金 Tab 切换？
不用处理

### Q2: 售卖期结束后可否购买？
走通用 活动结束后，界面就关闭       

### Q3: 条件类型如何映射显示文本？

**Answer**: 已与服务端确认 `AM_TYPE` 枚举值（见 design/server.md Q1），客户端维护如下映射表用于生成条件进度文案：

| AM_TYPE | 数值 | 显示文案模板 |
|---|---|---|
| AM_TYPE_PLAYER_LEVEL | 1 | "Lv.{当前}/Lv.{目标}" |
| AM_TYPE_PASS_TOWER_CHALLENGE | 37 | "爬塔{当前}/爬塔{目标}"（{目标}取Target第二段的层数） |
| AM_TYPE_ACC_LOGIN_DAY | 244 | "已登录{当前}/{目标}天" |
| AM_TYPE_FINISH_TASK | 8 | "任务进度{当前}/{目标}" |
| AM_TYPE_PLAYER_CP | 109 | "战力{当前}/{目标}" |

映射表硬编码在 `MixGrowthFundModule.cs` 中（非配置驱动），因为 AM_TYPE 数量固定且新增需要代码支持文案模板。

## 实现检查清单

- [ ] 创建 `MixGrowthFundModule.cs` 并注册
- [ ] 创建 `MixGrowthFundModule_Net.cs`
- [ ] 创建 `MixGrowthFundPage.cs` 主面板
- [ ] 创建 `MixGrowthFundRewardCell.cs`
- [ ] 取消注释 `GameLauncher.cs:715`
- [ ] 取消注释 `MallModule.cs` 逻辑
- [ ] 取消注释 `GeneralActiveModule.cs` 红点
- [ ] 添加 `CommandID` 定义
- [ ] 实现配表读取扩展
- [ ] 实现红点逻辑
- [ ] 测试购买/领取/进度流程

## 参考资料

- 服务端: `D:/se/develop/server/project/FsGame/ActivityModule/BusinessActivity/GrowthFund/`
- 协议: `define/struct/activity/struct_growth_fund.h`
- 原型: `D:/se/openspec/changes/growth-fund/demo/`
- 规范: `changes/growth-fund/specs/growth-fund/spec.md`
