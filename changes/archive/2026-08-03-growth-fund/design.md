# Design: growth-fund

## Context

成长基金活动是一种充值型成长福利活动：玩家一次性付费购买基金后，通过达成条件（等级/爬塔/累计登录/任务/战力）逐档解锁双轨奖励（免费奖励全玩家可领，投资奖励仅付费玩家可领），按档位顺序逐档领取（不可跳档）。

服务端 `MixGrowthFundModule`（BA_TYPE_MIX_GROWFUND=1018）已完整实现且激活中，Record 表、协议处理均已就位，只缺配置表数据文件。客户端需要新建 `MixGrowthFundModule.cs` 及配套 UI 面板，接入已有的 `BusinessActivityModule` 通用框架。策划需要新建两张配置表（`active_fund_main`、`activity_mix_growthfund_reward`）并在 `activity_goal.xlsx` 中为每档奖励配置解锁条件。

技术评审期间澄清的关键范围决策：
- **不做延长领取期机制**：proposal 早期讨论过"购买时刻+30天+缓冲"的个人领取期延长逻辑，但服务端现有实现不存在承载该逻辑的存储结构（`GROWTH_FUND_HISTORY_REC` 只有活动级 `EndTime`，无玩家个人字段），评审确认本次不实现，spec.md 中相关 Requirement 和 Scenario 已删除。
- **条件类型枚举值已核实**：ActivityGoalModule 支持的条件类型（LEVEL/TOWER_FLOOR/CUMULATIVE_LOGIN/QUEST/POWER）已对应到服务端真实的 `AM_TYPE` 枚举数值（见 Decisions）。
- **奖励高亮字段（FreeHighlight/PayHighlight）的真实用途**：配置的是特效ID，用于奖励可领取时给图标挂特效，不是"暂不使用"的预留字段。
- **Direct 字段多语言**：通过语言包处理，Direct 本身作为语言 key。

## Goals

### 客户端目标
- 新建 `MixGrowthFundModule.cs` + `MixGrowthFundModule_Net.cs`，接入 `BusinessActivityModule` 框架（活动注册、红点、菜单）。
- 新建 `MixGrowthFundPage.cs` 主面板 + `MixGrowthFundRewardCell.cs` 奖励格子组件。
- 维护条件类型（AM_TYPE）到显示文案的映射表，生成"Lv.X/Lv.Y"等条件进度文案。
- 实现格子状态机（Locked/LockedByPurchase/Claimable/Claimed）与红点逻辑。

### 服务端目标
- 无需新增代码，`MixGrowthFundModule` 已完整实现（购买、领取、条件追踪委托 `ActivityGoalModule`）。
- 仅需创建两张配置表的数据文件（`active_fund_main.txt`、`activity_mix_growthfund_reward.txt`）。

### 配置目标
- 新建 `active_fund_main.xlsx`（基金主表）、`activity_mix_growthfund_reward.xlsx`（奖励档位表）。
- 在 `recharge.xlsx` 新增 RechargeType=5 (GrowthFund) 商品条目。
- 在 `activity_goal.xlsx` 中为每档奖励配置对应的条件目标（Type 列填 AM_TYPE 数值）。

## Decisions

### 协议设计
复用通用 `BusinessActivityModule` 协议框架，非模块专属协议：
- `CLIENT_CUSTOMMSG_NOTIFY_OPEN_ACTIVITY_PANEL` → 服务端 `OnBizActivStart`（构建 ActivityGoal）
- `CLIENT_CUSTOMMSG_QUERY_ACTIVITY_INFO`（同步RPC）→ 服务端 `OnBizActivCustomQueryInfo`（返回主配置+每档奖励+CurNum/TargetNum）
- 点击任意奖励格子（免费或投资）统一走一键领取协议 `CLIENT_CUSTOMMSG_QUICK_GET_ACTIVITY_REWARD` → 服务端 `OnBizActivCustomQuickGetAllReward`（`GetAllReward`，一次性领取该活动下所有已解锁且可领取的奖励，不区分具体点击的是哪一格）——这是产品需求，不是简化实现
- `CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD` → 服务端 `OnCustomGetReward`（单格领取，服务端已实现该协议但客户端当前未调用，保留作为协议能力）
- `COMMAND_BIZ_ACTIV_CHANGED`（通用活动变化通知）→ 客户端收到后重新拉取 `CLIENT_CUSTOMMSG_QUERY_ACTIVITY_INFO`
- `OnGrowthFundDispose`（充值回调）→ 写入 `GROWTH_FUND_OPEN_REC`

### 状态管理
- 条件是否达成不由布尔标记表示，而是服务端下发 `CurNum`/`TargetNum`（来自 `ActivityGoalModule` 的 `ActivityGoalProgress`），客户端用 `CurNum >= TargetNum` 判定。
- 免费/[protocol-alignment-analysis.md](protocol-alignment-analysis.md)投资奖励的领取状态分别存储在 `MIX_GROWTH_FUND_REWARD_REC` 的 `FreeRewardState`/`PaidRewardState`（0=未领 1=已领）。
- 客户端格子状态机：`Locked`（条件未达成）→ `Claimable`（条件达成未领）→ `Claimed`（已领）；投资奖励额外有 `LockedByPurchase`（未购买）。

### 存储方案
服务端 Record 表（已核实与真实代码一致）：
- `GROWTH_FUND_OPEN_REC`：Col0 ACTIVITY_ID (dword) — 购买记录
- `MIX_GROWTH_FUND_REWARD_REC`：KEY(int64) / ACTIVITY_ID(dword) / REWARD_ID(dword) / FREE_REWARD_STATUS(dword) / PAID_REWARD_STATUS(dword) — 领取记录
- 条件进度存储在通用 `STRUCT_ACTIVITY::ACTIVITY_GOAL_REC`（9列，含 GOAL_PROGRESS/REWARD_STATUS/TYPE 等），由 `ActivityGoalModule` 管理，非本模块专属表。

### 配置结构
- 主表 `active_fund_main`：ActiveId, RechargeId, Direct, DisplayType(保留), Name(保留), NextActiveName(保留), ReserveTime(保留)
- 奖励表 `activity_mix_growthfund_reward`：ActiveId, RewardId, FreeReward, FreeHighlight(特效ID), PayReward, PayHighlight(特效ID)
- 条件类型枚举映射（`activity_goal.xlsx` 的 Type 列）：
  | ConditionType | AM_TYPE 枚举 | 数值 |
  |---|---|---|
  | LEVEL | AM_TYPE_PLAYER_LEVEL | 1 |
  | TOWER_FLOOR | AM_TYPE_PASS_TOWER_CHALLENGE | 37 |
  | CUMULATIVE_LOGIN | AM_TYPE_ACC_LOGIN_DAY | 244 |
  | QUEST | AM_TYPE_FINISH_TASK | 8 |
  | POWER | AM_TYPE_PLAYER_CP | 109 |

## Risks

### 性能风险
- `QueryInfo` 一次性下发全部档位数据（每档9个字段），档位数量固定（1-10档），数据量可控，无分页需求。

### 兼容性风险
- 客户端条件类型显示文案映射表硬编码在 `MixGrowthFundModule.cs`，新增条件类型需要代码发版才能显示对应文案（当前5种类型已覆盖 proposal 全部场景）。

### 数据一致性风险
- Excel 列顺序必须与服务端 `READ_FILE` 解析顺序一致，客户端自动生成代码依赖列顺序，需要在配置表创建后做三端联调验证（读取日志确认无解析错误）。
- 条件目标关联（`activity_goal.xlsx` 的 GoalId）需要与基金奖励档位（`activity_mix_growthfund_reward.xlsx` 的 RewardId）保持 key 对应，创建配置时需交叉核对。

## Open Questions
无

---

## 附录 A：客户端详细设计

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

**档位条件是否达成不在这张表里**。服务端 `OnBizActivCustomQueryInfo` 下发的每档数据里，最后两个字段是 `CurNum`（当前进度）和 `TargetNum`（目标进度），来自通用 `ActivityGoalModule` 的 `ActivityGoalProgress`（见附录B「Record 表」章节的 `ACTIVITY_GOAL_REC`）。客户端用 `CurNum >= TargetNum` 判断条件是否达成，不存在单独的 "GoalFinishFlag" 字段。

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

| 协议名 | 方向 | 用途 | 对应服务端处理（见附录B「协议」章节） |
|-------|------|------|------|
| `CLIENT_CUSTOMMSG_NOTIFY_OPEN_ACTIVITY_PANEL` | C→S | 通知面板打开（触发 `BuildData`） | `OnBizActivStart` |
| `CLIENT_CUSTOMMSG_QUERY_ACTIVITY_INFO` | C→S（同步RPC，outArgs 即返回数据） | 拉取活动数据（主配置+每档奖励+条件进度），无独立 S2C 消息 | `OnBizActivCustomQueryInfo` |
| `CLIENT_CUSTOMMSG_QUICK_GET_ACTIVITY_REWARD`（通用一键领取协议，客户端 `MixGrowthFundModule_Net.SendQuickGetAllRewardMsg`） | C→S | 点击任意奖励格子（免费/投资）实际调用的协议：一次性领取该活动下所有已解锁且可领取的奖励 | `OnBizActivCustomQuickGetAllReward` |
| `CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD` | C→S | 单格领取（免费/投资），服务端已实现，客户端当前未调用 | `OnCustomGetReward` |
| `COMMAND_BIZ_ACTIV_CHANGED`（id=263，通用活动变化通知，非模块专属） | S→C | 服务端推送活动数据变化（收到后客户端重新发起 `CLIENT_CUSTOMMSG_QUERY_ACTIVITY_INFO`） | 服务端在购买/领取后触发该 command |

**协议参数格式** (S2C `OnBizActivCustomQueryInfo` outArgs，已核对 `MixGrowthFundModule::QueryInfo` 真实代码，服务端在 r215465 精简了该协议的下发字段——原设计"服务端不改动"的假设已不成立，以下为精简后的当前格式):

先是基金主配置（**1 个字段**，一次性）：
```
RechargeId(int)
```
然后每档奖励重复 **3 个字段**（按 `activity_goal` 配置的档位顺序）：
```
RewardId(int), CurNum(int64), TargetNum(int64)
```
客户端按固定字段数逐组解析 outArgs（`MixGrowthFundPage.ParseQueryInfo`），不是分号拼接的字符串。

**客户端消费范围**：`Direct/DisplayType/Name/NextActiveName/FreeReward/FreeHighlight/PayReward/PayHighlight` 等静态展示字段已不再经由协议下发，服务端 `QueryInfo` 直接不发送这些字段，客户端改为通过 `active_fund_main`/`activity_mix_growthfund_reward` 两张配置表的本地同步数据获取（见"配表依赖"章节）。客户端从 outArgs 里只取 `RechargeId`（一次）、`RewardId`（作为与本地配置表的联接键）、`CurNum`、`TargetNum`（每档各一次）这些玩家状态/关联数据，因为它们不在配置表里，无法通过配置表同步获得。

### amType 数据来源（用于条件文案映射）

outArgs 中不包含 amType 字段。客户端 `amType` 应从本地已同步的 `activity_goal` 配置表读取
（`TDActivityGoalTable.GetData(goalId).Type`），`goalId` 通过 `activity_mix_growthfund_reward.xlsx`
的 `RewardId` 与 `activity_goal.xlsx` 交叉关联获得（见"配表依赖"章节）。

`MixGrowthFundRewardTierRow.SetData` 必须接收 amType 参数并传给 `GetConditionText`，
不能硬编码为固定值。

## UI 组件映射

### FundPanel 主面板

已核对 `MixGrowthFundPage.cs` 实际声明的 `[SerializeField]` 字段，修正如下（`m_TxtPrice` 不存在，价格拼进按钮文案；补充缺失的 `m_Root`/`m_TxtDesc`/`m_TxtBtnPurchase`；`m_ScrollRewards` 实际类型是 `SingleScrollView` 非 `ScrollRect`）：

| demo 元素 ID | Unity 组件 | 职责 |
|-------------|-----------|------|
| `#root-panel` | GameObject `m_Root` | 面板根节点 |
| `#title-fund` | TextMeshProUGUI `m_TxtTitle` | 基金名称 |
| `#desc-fund` | TextMeshProUGUI `m_TxtDesc` | 基金描述文本 |
| `#btn-purchase` | Button `m_BtnPurchase` | 购买按钮 |
| `#txt-btn-purchase` | TextMeshProUGUI `m_TxtBtnPurchase` | 购买按钮文案（含价格，如"购买 30元"/"已购买"） |
| `#list-reward-tiers` | SingleScrollView `m_ScrollRewards` | 奖励列表（回调模式，非 ScrollRect 手动 Instantiate） |

### RewardCell 奖励格子

已核对代码实际实现拆成了两层组件（`MixGrowthFundRewardTierRow.cs` 每档一行的容器 + `MixGrowthFundRewardCell.cs` 单个格子），修正如下（`m_BtnClaim` 不存在，实际是挂 `ItemIconBase` 的 `m_ImgIconRoot`；补充缺失的 TierRow 层与 `m_ClaimedMask`）：

#### RewardTierRow 档位行（每档一行，包含条件展示 + 免费/投资两个格子）

| demo 元素 | Unity 组件 | 职责 |
|----------|-----------|------|
| `#condition-text` | TextMeshProUGUI `m_TxtCondition` | 条件进度文案（如"Lv.30/Lv.30"） |
| `#condition-bar` | LRProgressBar `m_ConditionBar` | 条件进度条 |
| `#cell-free` | MixGrowthFundRewardCell `m_FreeCell` | 免费奖励格子 |
| `#cell-pay` | MixGrowthFundRewardCell `m_PayCell` | 投资奖励格子 |

#### RewardCell 奖励格子（免费/投资各一个实例）

| demo 元素 | Unity 组件 | 职责 |
|----------|-----------|------|
| `#icon-root-{free/pay}` | Transform `m_ImgIconRoot` | 奖励图标容器（挂 ItemIconBase，点击回调而非 Button） |
| `.lock-badge` | GameObject `m_LockBadge` | 锁图标 |
| `#redpoint-{free/pay}` | GameObject `m_RedPoint` | 红点 |
| `.claimed-mask` | GameObject `m_ClaimedMask` | 已领取遮罩 |

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
1. 点击任意可领取格子（免费或投资）→ 检查背包空间 → 发送 `CLIENT_CUSTOMMSG_QUICK_GET_ACTIVITY_REWARD(activityId)`（一键领取，不区分点击的具体格子）
2. 服务端一次性发放该活动下所有已解锁且可领取的免费+投资奖励，收到响应 → 更新本地状态 → 刷新 UI → 弹出奖励面板

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

| 表名 | 读取字段 | 用途 | 获取方式 |
|-----|---------|------|---------|
| `TDActiveFundMain`（表：active_fund_main，此前误写为 TDMixGrowthFundMain） | ActiveId, RechargeId, Direct, DisplayType, Name, NextActiveName | 活动主配置 | `DynamicConfigModule` 整表同步后 `TDActiveFundMainTable.GetData(activeId)` 本地查表 |
| `TDActivityMixGrowthfundReward`（表：activity_mix_growthfund_reward，此前误写为 TDMixGrowthFundReward） | ActiveId, RewardId, FreeReward, FreeHighlight, PayReward, PayHighlight | 奖励配置 | `DynamicConfigModule` 整表同步后 `TDActivityMixGrowthfundRewardTable.GetDataList()` 本地查表 |
| `TDRecharge` | RechargeId, Price | 充值商品 | 静态配置表，客户端打包内置 |

**两张新表接入 `DynamicConfigModule` 的方式**（参照 `TDActivityKoiRewardTable` 真实用法：`DynamicConfigModule_Process.cs::InitProcessDic()` 里的 `RegisterTable` + `ActivityDrawKOIModule_Message.cs` 里的 `TDActivityKoiRewardTable.GetDataList()`）：
1. `outcode_config.json` 的 `need_copy` 和 `NeedParseDataMethod` 都加入这两个表名（生成 `ParseData` 方法，供整表同步时逐行解析用）
2. 在 `DynamicConfigModule_Process.cs::InitProcessDic()` 中调用 `RegisterTable(TDActiveFundMainTable.metaData.tableName, typeof(TDActiveFundMainTable), TDActiveFundMainTable.InsertDynamicData, TDActiveFundMainTable.ParseComplete, TDActiveFundMainTable.ClearDynamicData)`，`TDActivityMixGrowthfundRewardTable` 同理
3. 在对应 `TDActiveFundMainTableExtend.cs`/`TDActivityMixGrowthfundRewardTableExtend.cs` 中实现 `InsertDynamicData`/`ParseComplete`/`ClearDynamicData`（参照 `TDActivityKoiRewardTableExtend.cs`）
4. **`MixGrowthFundModule` 必须实现 `IConfigSyncMethod` 接口并调用 `RegisterSyncMethod`**（活动级注册，与步骤 2 的表级注册是两个独立维度，缺一不可）：
   - `fileNameList` 返回 `{ "active_fund_main", "activity_mix_growthfund_reward" }`
   - `preFileNameList` 返回空数组
   - `businessActivityType` 返回 `BusinessActivityType.MixGrowthFund`
   - 在 `OnInit()` 中调用 `m_DynamicConfigModule.RegisterSyncMethod(this)`
   - 缺这一步不会编译报错，但玩家打开面板时框架不会主动去拉取这两张表，`TDActiveFundMainTable.GetData()` 永远返回空/默认值（参照 `ActivityDrawKOIModule_Message.cs` 真实用法）
5. `MixGrowthFundModule` 在打开面板/收到 `COMMAND_BIZ_ACTIV_CHANGED` 时，直接调用 `TDActiveFundMainTable.GetData(activeId)` / `TDActivityMixGrowthfundRewardTable.GetDataList()` 读取本地已同步数据，不再从 `QueryInfo` outArgs 解析这些静态字段
6. **服务端需修改配置加载宏**：`MixGrowthFundEventCallBack.cpp` 的 `LoadMainCfg`/`LoadRewardCfg` 需将 `READ_FILE` 改为 `READ_SYNC_FILE`，才能将这两张表注册进 `ConfigSyncModule::mFileMap`，否则客户端 `DynamicConfigModule` 整表同步无法收到数据。`READ_SYNC_FILE` 宏内部会调用 `load_sync_file()` → `ConfigSyncModule::LoadFile()`，将表注册进同步列表；`READ_FILE` 宏只加载到模块自己的内存 map，不会触发注册。参考正确做法：`BATreasureHuntModule::LoadRoutimeCfg` 使用 `READ_SYNC_FILE`。

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

---

## 附录 B：服务端详细设计

## ⚠️ 当前状态

**服务端 MixGrowthFundModule 已完整实现且激活中**。本文档记录现有实现。

- 模块: FsGame/ActivityModule/BusinessActivity/GrowthFund/MixGrowthFundModule.h
- 状态: ✅ 已注册 (BA_TYPE=1018)
- Record: ✅ 已定义
- 协议: ✅ 已实现
- 配置表: ❌ 数据文件待创建

**设计决策**: 服务端代码无需修改，只需创建配置表数据文件。

## Record 表

已核对 `define/struct/activity/struct_growth_fund.h`（由 `cons/res/struct/activity/growth_fund.xml` 生成）与 `MixGrowthFundFunc.cpp` 中的 `AddRowValue` 调用，实际列定义如下（此前草稿中的 GOAL_ID / GOAL_FINISH_FLAG 两列不存在，已删除）：

### GROWTH_FUND_OPEN_REC
- Col 0: ACTIVITY_ID (dword)

### MIX_GROWTH_FUND_REWARD_REC
- Col 0: KEY (int64, `util_merge_int32_to_int64(activityID, rewardID)`)
- Col 1: ACTIVITY_ID (dword)
- Col 2: REWARD_ID (dword)
- Col 3: FREE_REWARD_STATUS (dword, 0=未领 1=已领)
- Col 4: PAID_REWARD_STATUS (dword, 0=未领 1=已领)

**档位条件是否达成不在此表中**，由通用的 `ActivityGoalModule` 管理，存储在玩家的 `STRUCT_ACTIVITY::ACTIVITY_GOAL_REC` 表（9 列，`define/struct/player/struct_activity.h`）：
- Col 0: KEY_ID (int64, `merge(activityID, rewardID)`，与本模块的 nRewardID 对应)
- Col 1: ACTIVITY_ID (dword)
- Col 2: REWARD_ID (dword)
- Col 3: GOAL_PROGRESS (int64, 当前进度)
- Col 4: REWARD_STATUS (byte, 0=不可领取 1=可领取 2=已领取完毕；枚举见 `ActivityGoalDefine.h` 的 `ACTIVITY_GOAL_REWARD_CLOSE/OPEN/GOT`)
- Col 5: COUNT_TIMES_RECEIVED (dword)
- Col 6: TYPE (dword, 即 AM_TYPE)
- Col 7: TARGET_CONDITION (string)
- Col 8: CREATION_TIME (int64)

`MixGrowthFundModule::QueryInfo` 通过 `g_pActivityGoalModule->QueryGoalProgress` 读取该表，取每档的 `CurNum`/`TargetNum` 下发给客户端（而不是一个布尔"完成标记"）；奖励是否可领取的最终判定用 `CheckRewardCanGet`（本模块内的免费/付费领取状态）与 `g_pActivityGoalModule->CheckRewardCanGet`（条件是否达成）两者共同决定。

## 配置表

已核对 `MixGrowthFundEventCallBack.cpp` 的 `util_set_path_value` 路径与 `LoadMainCfg`/`LoadRewardCfg` 中的 `txt.ReadInt/ReadString` 真实列名，此前草稿中主表表名和三个字段名有误，已修正：

### active_fund_main.txt（此前误写为 activity_mix_growthfund_main.txt）
- ActiveId (int, 必填)
- RechargeId (int, 必填)
- Direct (string, 必填)
- DisplayType (int, 可选)
- Name (string, 可选，此前误写为 PeriodName)
- NextActiveName (string, 可选，此前误写为 NextPeriodName)
- ReserveTime (int, 可选，此前误写为 ReserveSec)

### activity_mix_growthfund_reward.txt
- ActiveId (int, 必填)
- RewardId (int, 必填)
- FreeReward (string, 必填, 格式: "itemId:count;itemId:count")
- FreeHighlight (string, 可选)
- PayReward (string, 必填)
- PayHighlight (string, 可选)

## 协议

已核对 `MixGrowthFundEventCallBack.cpp::Init` 中的 `AddNotifyHook`/`AddCustomHook`/`RegisterDisposeFunc` 真实挂载点，函数名修正如下（此前草稿把领取奖励的入口名写错为 `OnBizActivCustomGetReward`）：

### OnBizActivStart（挂载于 BA_TYPE_MIX_GROWFUND 的 BizActivNtf_OnStart）
打开面板时初始化数据（构建 ActivityGoal）

### OnBizActivCustomQueryInfo（挂载于 BizActivNtf_OnCustomQueryInfo）
打开面板查询活动数据，返回主配置 + 每档奖励配置 + 条件进度（CurNum/TargetNum）

### OnBizActivCustomQuickGetAllReward（挂载于 BizActivNtf_OnQuickGetAllReward）
**客户端点击任意奖励格子实际调用的协议**（`GetAllReward`）：一次性领取该活动下所有已解锁且可领取的免费+投资奖励，不区分玩家点击的具体格子。这是产品需求（一键领取），不是简化实现。

**协议参数**（C→S `CLIENT_CUSTOMMSG_QUICK_GET_ACTIVITY_REWARD`，客户端调用 `MixGrowthFundModule_Net.SendQuickGetAllRewardMsg(activityId)`）：
1. activityId (int) — 活动ID

### OnCustomGetReward（挂载于自定义协议 CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD，此前误写为 OnBizActivCustomGetReward）
单格领取（免费或投资），校验条件达成/防重复/背包空间后发放道具。**服务端已实现该协议，但客户端当前未调用**（客户端点击格子统一走一键领取，见上），保留作为协议能力，不需要客户端对接。

**协议参数**（C→S，已核对 `MixGrowthFundEventCallBack.cpp::OnCustomGetReward` 真实代码，对应 `GetReward(IKernel*, PERSISTID&, int nActivityID, int nEntryID, int nRecvType)`）：
1. activityId (int) — 活动ID
2. rewardId (int) — 档位ID（对应 `GetReward` 的 `nEntryID` 参数）
3. recvType (int) — 领取类型（免费/投资，对应 `GetReward` 的 `nRecvType` 参数，取值 `MIX_GROWTHFUND_REWARD_TYPE_FREE`/`MIX_GROWTHFUND_REWARD_TYPE_PAY`）

### OnGrowthFundDispose（挂载于 RECHARGE_TYPE_MIX_GROWTH_FUND 的 RegisterDisposeFunc）
充值回调，写入购买记录（GROWTH_FUND_OPEN_REC）

## 业务逻辑

### 条件追踪
委托 ActivityGoalModule (支持 189+ 条件类型)

### 防重复领取
Record 表状态检查

## 检查清单

- [x] 模块已实现
- [x] Record 已定义
- [x] 协议已实现
- [ ] 创建 active_fund_main.txt
- [ ] 创建 activity_mix_growthfund_reward.txt

## 参考

- FsGame/ActivityModule/BusinessActivity/GrowthFund/
- define/struct/activity/struct_growth_fund.h
- changes/growth-fund/design/client.md

---

## 附录 C：配置表详细设计

## 背景与目标

成长基金活动需要两张配置表：主表定义基金活动参数（活动ID、充值商品ID、名称），奖励表定义每档奖励内容（档位ID、免费奖励、投资奖励）。

**当前状态**:
- 服务端配置加载代码已完成（MixGrowthFundModule::LoadMainCfg/LoadRewardCfg）
- 配置结构体已定义（STFund, STReward）
- 但配置表数据文件尚未创建

**目标**: 创建两张新配置表，无需修改代码，直接填充数据即可使用。

---

## ⚠️ 设计阶段配置表变更

已核对服务端真实加载路径（`MixGrowthFundEventCallBack.cpp::Init` 的 `util_set_path_value`），主表真实表名为 `active_fund_main`（此前草稿误写为 `activity_mix_growthfund_main`），已修正：

### 新增配置表

| 表名 | 原因 | 影响范围 |
|------|------|---------|
| active_fund_main.xlsx（此前误写为 activity_mix_growthfund_main.xlsx） | 定义基金活动主配置（活动ID、充值ID、分类标识） | 服务端/客户端 |
| activity_mix_growthfund_reward.xlsx | 定义每档奖励内容（免费奖励、投资奖励） | 服务端/客户端 |

### 补充字段

无。两张表为全新配置表。

### 关联变更

| 变更类型 | 说明 |
|---------|------|
| 充值商品关联 | recharge.xlsx 需新增 RechargeType=5 (GrowthFund) 的商品条目 |
| 条件目标关联 | 需在 activity_goal.xlsx 中为每档奖励配置对应的目标（goalId）|

---

## 配置表生成和使用机制

### 策划侧（Excel → txt）
1. 策划在 Excel 中编辑配置数据
2. 运行配置表导出工具（TableTool.exe）
3. 生成 .txt 文件到目录

### 服务端侧（txt → 内存结构）
1. 服务器启动时读取 .txt 文件
2. 解析主表
3. 解析奖励表
4. 加载到内存
5. 通过配置查询接口查询

### 客户端侧（txt → 自动生成代码）
1. Unity 编辑器读取 .txt 文件
2. 自动生成配置类
3. 生成注册代码
4. 客户端通过配置类访问配置

---

## 配置表定义

### active_fund_main.xlsx（此前误写为 activity_mix_growthfund_main.xlsx）

**表文件路径**: ini/activity/active_fund_main.txt
**用途**: 定义基金活动主配置（活动ID、充值商品ID、分类标识）
**主键**: ActiveId

**字段定义**（已核对 `MixGrowthFundEventCallBack.cpp::LoadMainCfg` 的 `txt.ReadInt/ReadString` 真实列名，Name/NextActiveName/ReserveTime 三列此前误写为 PeriodName/NextPeriodName/ReserveSec）：

| 字段名 | 类型 | 属性 | 说明 | 示例值 | 必填/可选 | 客户端使用 | 服务器使用 |
|--------|------|------|------|--------|-----------|-----------|-----------|
| ActiveId | int | S | 活动ID，唯一标识 | 10008 | 是 | 是 | 是 |
| RechargeId | int | S | 关联充值商品ID（recharge.xlsx） | 1013 | 是 | 是 | 是 |
| Direct | string | S | 基金类型标识（用于客户端Tab分类） | 成长计划 | 是 | 是 | 是 |
| DisplayType | int | S | 显示类型（保留字段） | 0 | 否 | 否 | 是 |
| Name | string | S | 当前周期名称（保留，此前误写为 PeriodName） |  | 否 | 否 | 是 |
| NextActiveName | string | S | 下一周期名称（保留，此前误写为 NextPeriodName） |  | 否 | 否 | 是 |
| ReserveTime | int | S | 保留时间秒数（保留，此前误写为 ReserveSec） | 0 | 否 | 否 | 是 |

**属性说明**：本表全部字段为 **S（Server-only）**：字段语义属于服务端业务，客户端不定义、不拥有这些字段的业务含义。客户端接入 `DynamicConfigModule` 整表同步获得本表数据（见下），不从 `CLIENT_CUSTOMMSG_QUERY_ACTIVITY_INFO` 协议 outArgs 解析这些静态字段（该协议仍会下发它们，但客户端只取其中的玩家状态字段，见"网络协议"章节的"客户端消费范围"）。

**配置加载方式**：动态配置——服务端可在运营期间调整本表内容（txt 文件更新后），`ConfigSyncModule` 通用机制自动同步给客户端本地内存，不需要客户端重新打包生效。

**客户端消费方式**：接入 `DynamicConfigModule` 整表同步（用法与 `TDActivityKoiRewardTable` 一致，见"配表依赖"章节）。`output_code_csharp.bat` 生成 `TDActiveFundMain.cs`（数据行类，含 `ParseData`）和 `TDActiveFundMainTable.cs`（表管理类）后，在 `DynamicConfigModule_Process.cs::InitProcessDic()` 注册 `RegisterTable`，业务代码直接 `TDActiveFundMainTable.GetData(activeId)` 读取本地已同步数据，不从协议 outArgs 解析这些字段。

**outcode_config.json 配置建议**：需要配置。在 `need_copy` 和 `NeedParseDataMethod` 中都添加本表——生成 `ParseData` 方法供 `DynamicConfigModule` 整表同步时逐行解析，且本表用于活动系统、服务端在运营期间可动态调整。

**设计决策**:
- **ActiveId**: 沿用 BusinessActivity 框架的活动ID体系
- **RechargeId**: 关联充值系统，避免硬编码价格
- **Direct**: 用字符串而非枚举，支持策划灵活扩展基金类型；作为语言包 key 支持多语言

---

### activity_mix_growthfund_reward.xlsx

**用途**: 定义每档奖励内容（免费奖励、投资奖励）
**主键**: 复合键 (ActiveId + RewardId)

**字段定义**:

| 字段名 | 类型 | 属性 | 说明 | 示例值 | 必填/可选 | 客户端使用 | 服务器使用 |
|--------|------|------|------|--------|-----------|-----------|-----------|
| Id | int | S | 自增ID（忽略） | 1 | 否 | 否 | 否 |
| ActiveId | int | S | 所属活动ID | 10008 | 是 | 是 | 是 |
| RewardId | int | S | 奖励档位ID（1-10） | 1 | 是 | 是 | 是 |
| FreeReward | string | S | 免费奖励串 | 1003:188 | 是 | 是 | 是 |
| FreeHighlight | string | S | 免费奖励特效ID，奖励可领取时给图标挂特效 |  | 否 | 是 | 否 |
| PayReward | string | S | 投资奖励串 | 1003:1080 | 是 | 是 | 是 |
| PayHighlight | string | S | 投资奖励特效ID，奖励可领取时给图标挂特效 |  | 否 | 是 | 否 |

**属性说明**：本表全部字段为 **S（Server-only）**，理由同 active_fund_main.xlsx。客户端经协议获得每档奖励原始数据，调用生成的 `TDActivityMixGrowthfundReward.ParseData(Dictionary<string, Var>)` 方法组装为强类型对象。

**配置加载方式**：动态配置——服务端可在运营期间调整每档奖励内容，`ConfigSyncModule` 通用机制自动同步给客户端本地内存。

**客户端消费方式**：同 active_fund_main.xlsx，接入 `DynamicConfigModule` 整表同步，业务代码直接 `TDActivityMixGrowthfundRewardTable.GetDataList()` 读取本地已同步数据。

**outcode_config.json 配置建议**：需要配置。在 `need_copy` 和 `NeedParseDataMethod` 中都添加本表——生成 `ParseData` 方法供 `DynamicConfigModule` 整表同步时逐行解析，且本表用于活动系统、服务端在运营期间可动态调整每档奖励内容。

**设计决策**:
- **RewardId**: 1-10 档位，固定顺序展示，不支持跳档
- **奖励串格式**: 沿用项目通用格式（itemId:count分号分隔）
- **Highlight**: 配置特效ID，奖励达到可领取状态时用于图标特效展示

---

## 对齐要求

### 字段顺序
- Excel 列顺序必须与服务端 READ_FILE 解析顺序一致
- 客户端自动生成代码依赖列顺序

### 数据类型
- int: 整数类型，客户端/服务端一致
- string: 字符串类型，奖励串需符合解析格式

### 必填/可选
- ActiveId, RechargeId, RewardId, FreeReward, PayReward 为必填
- 保留字段（DisplayType, Name, NextActiveName, ReserveTime）可填 0 或空字符串

### 枚举值
- Direct 字段无硬编码枚举，策划自由填写，作为语言包 key
- 客户端根据 Direct 值动态生成 Tab（相同 Direct 分到同一 Tab）

---

## 关联配置表

### recharge.xlsx

需新增 RechargeType=5 (GrowthFund) 的商品条目：

| RechargeId | RechargeType | Price | ProductId | Name |
|------------|--------------|-------|-----------|------|
| 1013 | 5 | 30 | com.lingren.growthfund.30 | 成长计划 |
| 1014 | 5 | 68 | com.lingren.growthfund.68 | 爬塔回赠 |

### activity_goal.xlsx

每个奖励档位需配置对应的目标，Type 列填 AM_TYPE 枚举数值（见 Decisions 章节的条件类型枚举映射表）：

| Id | ActivityId | RewardId | Type | Target | Num |
|----|-----------|----------|------|--------|-----|
| ... | 10008 | 1 | 1 (LEVEL) | 空 | 20 |
| ... | 10008 | 2 | 1 (LEVEL) | 空 | 25 |
| ... | ... | ... | ... | ... | ... |

---

## 实现检查清单

- [ ] 创建 active_fund_main.xlsx 并填充数据
- [ ] 创建 activity_mix_growthfund_reward.xlsx 并填充数据
- [ ] 在 recharge.xlsx 中新增 RechargeType=5 商品
- [ ] 在 activity_goal.xlsx 中配置每档目标
- [ ] 运行 TableTool.exe 导出 .txt 文件
- [ ] 客户端验证自动生成的 TDActiveFundMain.cs
- [ ] 服务端验证配置加载（查看日志）
- [ ] 测试数据完整性（10档奖励是否都有）
