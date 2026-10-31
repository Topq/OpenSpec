# design-server.md

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

### OnCustomGetReward（挂载于自定义协议 CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD，此前误写为 OnBizActivCustomGetReward）
领取单格奖励（免费或投资），校验条件达成/防重复/背包空间后发放道具

### OnBizActivCustomQuickGetAllReward（挂载于 BizActivNtf_OnQuickGetAllReward）
一键领取活动下所有可领取奖励

### OnGrowthFundDispose（挂载于 RECHARGE_TYPE_MIX_GROWTH_FUND 的 RegisterDisposeFunc）
充值回调，写入购买记录（GROWTH_FUND_OPEN_REC）

## 业务逻辑

### 条件追踪
委托 ActivityGoalModule (支持 189+ 条件类型)

### 防重复领取
Record 表状态检查

## Open Questions

### Q1: ActivityGoalModule 条件类型枚举值？

**Answer**: 已查 `define/GameGoalDefine.h` + `FsGame/GoalModule/GoalFunc.cpp`（`GoalModule::InitGoalFunc` 中已注册、非注释项）确认以下映射，`activity_goal.xlsx` 的 Type 列直接填数值：

| proposal ConditionType | AM_TYPE 枚举 | 数值 | Target 格式 | Num 含义 |
|---|---|---|---|---|
| LEVEL（等级） | AM_TYPE_PLAYER_LEVEL | 1 | 空 | 目标等级 |
| TOWER_FLOOR（爬塔） | AM_TYPE_PASS_TOWER_CHALLENGE | 37 | "章节ID,层数"，用 `GoalCondMatchParam1EqAndParam2GTE` 匹配（章节相等且层数>=Num） | 目标层数（与 Target 第二段一致） |
| CUMULATIVE_LOGIN（累计登录） | AM_TYPE_ACC_LOGIN_DAY | 244 | 空 | 累计登录天数 |
| QUEST（任务完成） | AM_TYPE_FINISH_TASK | 8 | "taskId,subTaskId"，用 `GoalCondMatchParamsByTwoIntEQ` 匹配 | 通常填 1 |
| POWER（战力） | AM_TYPE_PLAYER_CP | 109 | 空 | 目标战力值 |

### Q2: 是否需要延长领取期？
不用

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
