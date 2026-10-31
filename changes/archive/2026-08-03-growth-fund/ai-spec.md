# growth-fund — AI Ground-Truth Spec

> 用途：给 AI 用的单一稠密参考，不考虑人工可读性。合并了本 change 全部产物（proposal/design/specs/tasks/implementation-report/code-review-report/test-validate-report/protocol-*.md）里核实过的事实，并标出与早期草稿冲突、已被修正的地方。人工叙事版见 `plan/working.md`，两者冲突时以本文件为准。
> 快照时间：2026-08-01（implementation-report/code-review-report/test-validate-report 均产出于 2026-07-31，代码尚未按 test-validate-report 的 Bug-1~4 修复）。

## 1. 一句话模型

充值型活动：玩家付费购买某 `ActiveId` 的基金后解锁"投资奖励"领取权；"免费奖励"无论是否购买都可领。每只基金 10 档（可配），每档绑定一个条件（等级/爬塔/累计登录/任务/战力，配置化），条件达成后该档"可领取"，两条奖励轨道（免费/投资）各自独立领取状态，但同一轨道内必须按档位顺序领取（不可跳档，见 §6.2 的验证缺口）。复用已存在且已激活的服务端 `MixGrowthFundModule`（`BA_TYPE_MIX_GROWFUND=1018`），本次工作是新建客户端模块+UI+两张配置表数据。

## 2. 实体与状态（服务端真实结构，已核对代码，非草稿推测）

### 2.1 `GROWTH_FUND_OPEN_REC`（购买记录）
| Col | 字段 | 类型 |
|---|---|---|
| 0 | ACTIVITY_ID | dword |

只有这一列。**没有购买时刻字段**——proposal 早期讨论的"购买时刻+30天+缓冲"延长领取期机制，因为没有存储位置而被否决（见 §9）。

### 2.2 `MIX_GROWTH_FUND_REWARD_REC`（领取记录）
| Col | 字段 | 类型 | 语义 |
|---|---|---|---|
| 0 | KEY | int64 | `util_merge_int32_to_int64(activityID, rewardID)` |
| 1 | ACTIVITY_ID | dword | |
| 2 | REWARD_ID | dword | |
| 3 | FREE_REWARD_STATUS | dword | **0=未领 1=已领**（`MIX_GROWTHFUND_REWARD_UNCLAIMED=0` / `MIX_GROWTHFUND_REWARD_RECEIVED=1`） |
| 4 | PAID_REWARD_STATUS | dword | 同上编码 |

⚠️ 陷阱：这张表**不含条件是否达成**的信息，只记录"是否已领"。真实发生的 Bug-3（见 §8）就是把这张表的"已领=1"误当成"可领=1"（`BARewardState.Can==1`）来判断红点，逻辑刚好相反。

### 2.3 `STRUCT_ACTIVITY::ACTIVITY_GOAL_REC`（条件进度，由通用 `ActivityGoalModule` 管理，非本模块专属表）
| Col | 字段 | 类型 |
|---|---|---|
| 0 | KEY_ID | int64，`merge(activityID, rewardID)` |
| 1 | ACTIVITY_ID | dword |
| 2 | REWARD_ID | dword |
| 3 | GOAL_PROGRESS | int64（当前进度，即 CurNum） |
| 4 | REWARD_STATUS | byte（0=`ACTIVITY_GOAL_REWARD_CLOSE` 1=`OPEN` 2=`GOT`） |
| 5 | COUNT_TIMES_RECEIVED | dword |
| 6 | TYPE | dword（即 AM_TYPE，见 §3.4） |
| 7 | TARGET_CONDITION | string |
| 8 | CREATION_TIME | int64 |

条件是否达成 = `CurNum >= TargetNum`（`TargetNum` 来自配置，不在这张表里，是 `QueryInfo` 下发的动态值）。判断某档是否真正可领 = 本模块的 Record 状态（未领）**且** `ActivityGoalModule.CheckRewardCanGet`（条件达成）两者同时满足。

### 2.4 客户端缓存结构（真实实现，非设计稿）
```csharp
Dictionary<int, bool> m_PurchasedFunds;              // activityId -> 是否购买
Dictionary<long, MixGrowthFundRewardStatus> m_RewardStatuses;  // key(activityId,rewardId) -> 状态

struct MixGrowthFundRewardStatus {
    int RewardId; int FreeStatus; int PaidStatus;
    long CurNum; long TargetNum;   // ⚠️ 实现中这两个字段从未被赋值，恒为0，见 Bug-2
}

enum CellClaimState { Locked=0, LockedByPurchase=1, Claimable=2, Claimed=3 }
```

## 3. 配置表（真实字段名，早期草稿的错误命名已在此处订正）

### 3.1 `active_fund_main`（txt 路径 `ini/activity/active_fund_main.txt`；早期草稿误写表名为 `activity_mix_growthfund_main`）
| 字段 | 类型 | 必填 | 备注 |
|---|---|---|---|
| ActiveId | int | 是 | 主键 |
| RechargeId | int | 是 | 关联 recharge.xlsx |
| Direct | string | 是 | 语言包 key，同时用作客户端 Tab 分组依据（相同 Direct 归同一 Tab） |
| DisplayType | int | 否 | 保留 |
| Name | string | 否 | 保留，**早期草稿误写为 PeriodName** |
| NextActiveName | string | 否 | 保留，**早期草稿误写为 NextPeriodName** |
| ReserveTime | int | 否 | 保留，**早期草稿误写为 ReserveSec** |

属性必须标 **A（All）**，不能标 S（Server-only）——标 S 会导致客户端代码生成器不生成强类型字段访问器，只能用 `extend.GetInt(...)` 弱类型读（实践中踩过这个坑，见 tasks.md 技术债务记录 / code-review-report config-002）。

### 3.2 `activity_mix_growthfund_reward`
| 字段 | 类型 | 必填 | 备注 |
|---|---|---|---|
| Id | int | 否 | 自增，忽略 |
| ActiveId | int | 是 | |
| RewardId | int | 是 | 档位 1-10，固定顺序 |
| FreeReward | string | 是 | `"itemId:count"` |
| FreeHighlight | string | 否 | **特效ID**，不是废弃占位字段——档位可领取时用来给图标挂特效 |
| PayReward | string | 是 | |
| PayHighlight | string | 否 | 同 FreeHighlight |

同样必须标 A 属性。

### 3.3 `activity_goal.xlsx`（每档一行，通用条件配置表，非本功能专属）
每个 `(ActiveId, RewardId)` 组合需要一行：`ActivityId`, `RewardId`, `Type`(=AM_TYPE 数值), `Target`(见 3.4 的 Target 格式), `Num`(目标数值)。

### 3.4 AM_TYPE 枚举映射（已核对 `GameGoalDefine.h` + `GoalFunc.cpp::InitGoalFunc` 真实注册项，非猜测）
| ConditionType（策划语义） | AM_TYPE 常量 | 数值 | Target 格式 | Num 含义 |
|---|---|---|---|---|
| LEVEL | AM_TYPE_PLAYER_LEVEL | **1** | 空 | 目标等级 |
| TOWER_FLOOR | AM_TYPE_PASS_TOWER_CHALLENGE | **37** | `"章节ID,层数"`，用 `GoalCondMatchParam1EqAndParam2GTE` 匹配 | 目标层数（与 Target 第二段一致） |
| CUMULATIVE_LOGIN | AM_TYPE_ACC_LOGIN_DAY | **244** | 空 | 累计登录天数 |
| QUEST | AM_TYPE_FINISH_TASK | **8** | `"taskId,subTaskId"`，用 `GoalCondMatchParamsByTwoIntEQ` 匹配 | 通常填 1 |
| POWER | AM_TYPE_PLAYER_CP | **109** | 空 | 目标战力值 |

条件文案模板（客户端 `GetConditionText(amType, cur, target)`，硬编码映射表，新增条件类型需要发版）：LEVEL→`"Lv.{cur}/Lv.{target}"`，TOWER_FLOOR→`"爬塔{cur}/爬塔{target}"`，其余类似。**Bug-1（见 §8）：实际代码里 amType 参数被硬编码传 0，导致所有档位显示 `"{0}/{1}"` 而不是上述格式，尚未修复。**

### 3.5 `recharge.xlsx` 关联
新增 `RechargeType=5 (GrowthFund)` 商品条目，示例：`RechargeId=1013, Price=30, ProductId=com.lingren.growthfund.30`。基金购买复用现有充值底层流程，不新增支付逻辑。

## 4. 协议（复用通用 BusinessActivity 框架协议，非模块专属；早期草稿虚构的协议名已删除）

| 协议 | 方向 | 用途 | 服务端处理函数 |
|---|---|---|---|
| `CLIENT_CUSTOMMSG_NOTIFY_OPEN_ACTIVITY_PANEL` | C→S | 通知面板打开（触发 BuildData/构建 ActivityGoal） | `OnBizActivStart` |
| `CLIENT_CUSTOMMSG_QUERY_ACTIVITY_INFO` | C→S，**同步 RPC**，outArgs 即返回值，无独立 S2C 消息 | 拉取主配置+每档奖励+CurNum/TargetNum | `OnBizActivCustomQueryInfo` |
| `CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD` | C→S | 领取单格奖励（免费或投资，`nRecvType`：1=FREE 2=PAY） | `OnCustomGetReward`（早期草稿误写为 `OnBizActivCustomGetReward`，实际无此名） |
| （客户端一键领取调用入口，挂在 `MixGrowthFundModule_Net.cs`） | C→S | 一键领取该活动全部可领奖励 | `OnBizActivCustomQuickGetAllReward`（挂载于 `BizActivNtf_OnQuickGetAllReward`） |
| `COMMAND_BIZ_ACTIV_CHANGED`（id=263，通用活动变化通知，非模块专属） | S→C | 购买/领取后触发，客户端收到后重新发 `CLIENT_CUSTOMMSG_QUERY_ACTIVITY_INFO` 拉最新数据 | — |
| （充值回调） | — | 购买成功后写入 `GROWTH_FUND_OPEN_REC` | `OnGrowthFundDispose`（挂载于 `RECHARGE_TYPE_MIX_GROWTH_FUND` 的 `RegisterDisposeFunc`） |

### 4.1 `OnBizActivCustomQueryInfo` outArgs 真实字段布局（已核对 `MixGrowthFundFunc.cpp:218-273` 源码，非猜测）

这是走 `BusinessActivityModule` 通用框架的自定义数据段，**前面还有框架自己的 13 个固定字段**（ActivityID/ActivityState/BeginTime/EndTime/CurTurn/CurDay/ActivityType/EachTurnDays/UIType/ShowTime/TaskId/SeasonId/预留，索引 0~12，`BAActivityInfoIndex.CustomStart`=13）。客户端如果用 `BActivityCommonParamArgs.ParamArgs(args)` 这类框架方法接收，框架已经处理了这个偏移，业务代码看到的是"自定义数据段"本身，从索引 0 开始就是下面这些字段：

先是基金主配置（5 个字段，一次性）：
```
RechargeId(int), Direct(string), DisplayType(int), Name(string), NextActiveName(string)
```
然后每档奖励重复 9 个字段（按 `activity_goal` 配置的档位顺序循环）：
```
RewardId(int), FreeReward(string), FreeHighlight(string), PayReward(string), PayHighlight(string),
LanguagePack(string), Url(string), CurNum(int64), TargetNum(int64)
```

⚠️ **两层不同的"起始索引"概念不要混淆**（这是本 change 真实踩过的坑，见 §8 Bug 及 protocol-parsing-*.md 系列文档）：
1. 如果客户端直接监听原始协议（`AddCustomHook` 注册）→ 从索引 0 开始就是业务参数，无框架偏移。
2. 如果客户端走 `RegisterSeverActivityParamArgs`/`ParamArgs` 这类 BusinessActivity 框架接口 → 框架已经吃掉了前 13 个固定字段，业务代码拿到的 `outArgs`/`args` 里索引 0 就是本表的 `RechargeId`；**但如果错误地又手动加一次 `CustomStart` 偏移，或者反过来漏掉框架层，都会导致错位解析**。判断依据：看协议处理函数签名是 `void OnRecvXXX(IVarList args)`（原始，走 1）还是 `override void ParamArgs(IVarList args)` / 框架回调（走 2）。

### 4.2 客户端实际消费范围（关键架构决策，多份文档反复确认）
`outArgs` 里 `RechargeId/Direct/DisplayType/Name/NextActiveName/FreeReward/FreeHighlight/PayReward/PayHighlight/LanguagePack/Url` 这些**静态配置字段**，服务端仍会照常下发（服务端代码不改），但客户端**不解析它们**，改为通过 `active_fund_main`/`activity_mix_growthfund_reward` 两张配置表的本地同步数据获取（见 §5）。客户端从 outArgs 里只取每档的 `RewardId`（联接键）、`CurNum`、`TargetNum` 三个**玩家状态字段**，因为它们无法从配置表获得。

`protocol-alignment-analysis.md` 和 `protocol-redundancy-analysis.md` / `protocol-simplification-report.md` 三份文档讨论过"既然客户端不用这些字段，能否精简协议只发 RewardId+CurNum+TargetNum"——**这是一个未采纳的优化提案，当前代码仍按上面 §4.1 的完整 9 字段格式发送/解析**，只是客户端解析时跳过不用的字段（`index += 5` 跳过 FreeReward~LanguagePack，`index += 1` 跳过 Url）。不要假设协议已被精简；如果要改，需要同步改服务端 `MixGrowthFundFunc.cpp::QueryInfo` 和客户端解析逻辑，且需评估已上线客户端的协议兼容性。

## 5. 配置表接入客户端的完整链路（这是本 change 最容易漏掉的一层，务必完整走通）

"表级注册"和"活动级注册"是两个独立维度，缺一不可，且都不会在编译期报错：

1. **表级注册**：`outcode_config.json` 的 `need_copy` 和 `NeedParseDataMethod` 都要加入两张新表名 → 生成 `TDActiveFundMain.cs`/`TDActiveFundMainTable.cs` 等 8 个文件（含 `ParseData` 方法）→ 在 `DynamicConfigModule_Process.cs::InitProcessDic()` 里对每张表调 `RegisterTable(表类.metaData.tableName, typeof(表类), 表类.InsertDynamicData, 表类.ParseComplete, 表类.ClearDynamicData)`。
   - 缺这一步：编译不过（`RegisterTable` 是必需调用）。
2. **活动级注册**：`MixGrowthFundModule` 必须实现 `IConfigSyncMethod` 接口并在 `OnInit()` 末尾调用 `m_DynamicConfigModule.RegisterSyncMethod(this)`；`fileNameList` 返回两张表名常量，`preFileNameList` 返回空数组，`businessActivityType` 返回 `BusinessActivityType.MixGrowthFund`。
   - 缺这一步：**编译通过，但 `TDActiveFundMainTable.GetData(activeId)` 永远返回空/默认值**——因为框架不知道"打开成长基金面板时要主动去拉这两张表"。这是本 change 实际发生过的疏漏（tasks.md 任务 4.1a 专门记录了这个坑）。
3. **服务端侧**：`MixGrowthFundEventCallBack.cpp` 的 `LoadMainCfg`/`LoadRewardCfg` 必须用 `READ_SYNC_FILE` 宏（不是 `READ_FILE`）加载这两张配置文件——`READ_SYNC_FILE` 内部调 `load_sync_file()`→`ConfigSyncModule::LoadFile()` 把表注册进 `mFileMap`，才能被客户端的 `CLIENT_CUSTOMMSG_PULL_CFGSYNC_FILES` 整表同步拉到。这是本 change 实际发生的疏漏——design.md 早期错误声明"服务端代码无需修改"，实施时才发现要改这两行宏（tasks.md 任务 2.7，implementation-report.md 问题记录 #2）。

判断某个模块是否正确接入的检查方法：打开面板后调 `TDActiveFundMainTable.GetData(activeId)`，如果拿到非默认值才算真正接通；"类存在、编译通过"不代表数据链路是通的。

## 6. 业务规则（来自 spec.md，逐条列出，附带真实实现状态）

### 6.1 基金购买
- 售卖期内未购买→点击购买→调起第三方 SDK 支付→支付成功→服务端 `OnGrowthFundDispose` 写 `GROWTH_FUND_OPEN_REC`→客户端收到 `COMMAND_BIZ_ACTIV_CHANGED`→重新拉 `QueryInfo`→投资奖励列解锁+购买按钮变"已购买"。
- **购买中/购买失败无中间态 UI**：这是决策记录 #2 的产品决策，不是技术限制——第三方 SDK 全权接管支付交互，客户端只管调起和收回调。
- 售卖期结束：购买按钮置灰+"售卖已结束"标签；**这一状态未实现**（见 §8 Bug-5/TC-03，`MixGrowthFundPage.cs` 只处理 isPurchased 两态，没调用已存在的 `IsActivityActive` 判断）。

### 6.2 按顺序解锁（不可跳档）
- 规则：档位必须按 1→2→3→... 顺序领取，不能跳过未领档位去领后面的档位（即使后面档位条件已达成）。
- 服务端理论上通过 `g_pActivityGoalModule->CheckRewardCanGet` 做该校验，但 test-validate-report.md TC-06 明确指出："设计文档描述此逻辑，但未在代码中找到明确实现，需联调确认"——**这条规则的服务端强制性尚未被静态验证确认，需要人工用两个真实账号联调复现**。不要假设它已经生效。

### 6.3 免费奖励 / 投资奖励领取
- 免费：任何玩家，条件达成+前档已领即可领；投资：额外要求已购买。
- 两条轨道领取状态互相独立存储（`FREE_REWARD_STATUS`/`PAID_REWARD_STATUS` 分列），互不阻塞（先领免费不影响投资奖励仍可领，反之亦然）。
- 服务端发放前有背包满保护：`TestAutoAddItems` 检测背包满时返回 `ERR_BAG_FULL`，**不发放、不写 Record**（不会出现"扣了记录但东西没发"的情况）。写入顺序：先 `SetInt` 写 Record 为已领，再 `AutoAddItems` 真正发货。

### 6.4 红点
- 规则意图：售卖期内未购买→主入口红点；任意档位可领取（条件达成+未领）→该档图标红点+主入口红点；全部领完→无红点+"已完成"角标。
- **红点逻辑当前有 3 个已知 bug 未修复**（Bug-2/3/4，见 §8），实际表现与规则意图不一致，不要以为红点已经能正确工作。

### 6.5 配置化支持
- 不同 `ActiveId` 独立配一套档位+条件类型+条件数值，互不影响；`Direct` 字段相同的 ActiveId 归到同一个客户端 Tab。
- 本次原型范围**只验证了 LEVEL 一种条件类型、单一 ActiveId**，多 Tab/多条件类型混排未做端到端验证（proposal 决策记录 #12 明确说明范围收窄的原因是"配置化能力"与"多玩法混排"是两件事，前者已够验证架构）。

## 7. proposal 阶段讨论过、最终被否决/未实现的机制（重要：不要被 plan/working.md 误导）

`plan/working.md`（原始策划案）里写的下列内容，在技术评审后被**明确否决，且已从 spec.md 删除对应 Requirement/Scenario**，AI 阅前必须知道这些不是本次范围：

1. **§2.5 自然时间基金"领取期延长"机制**（购买时刻+30天+1天缓冲，公式化计算新截止时间，兜底日期防恶意拖延）——否决原因：服务端 `GROWTH_FUND_OPEN_REC` 只有 `ACTIVITY_ID` 一列，没有购买时刻字段，没有实现载体。**本次售卖期结束后，玩家仍可正常领取已解锁奖励，没有独立的个人领取期限制**（proposal.md "范围说明"段的最终结论）。
2. **§2.4.1 多种 claim_mode**（DAILY/CUMULATIVE_LOGIN/LADDER/ONCE 等其他返利形态）——只实现 `CONDITION`（条件解锁型）一种，其余是 proposal 早期头脑风暴，未落地。
3. **§2.5.3 提到的方案 A/C/D（等比例缩放/直接作废/下架入口）**——纯讨论对比，从未打算实现。
4. **§2.6 退款/异常处理表**、**§2.7 系统关联表里的"推送/邮件"、"客服系统"**——这些是 proposal 里的运营层描述，本次技术范围（客户端+服务端+配置表）未涉及任何推送/邮件/客服系统代码改动。
5. **一键领取按钮的决策发生过一次反转**：plan/working.md 原文写"逐档点击对应行的领取按钮，不提供一键批量领取"（§2.4.2），但 proposal.md 决策记录 #10 标注"已变更"——最终决定**不新增独立按钮，点击任意可领取格子即触发一键领取该活动全部可领取奖励**，复用服务端已有的 `OnBizActivCustomQuickGetAllReward`。以决策记录 #10 和 design.md 为准，plan/working.md 原文已过时。
6. **多基金 Tab 切换、条件类型混排展示**——proposal 决策记录 #12 明确排除在本次原型范围外，只做单一基金+LEVEL条件的完整链路验证。
7. **档位编号显示、整体进度条、终极大奖独立展示区**——决策记录 #5/#6/#7 均为"不做"。

## 8. 已知代码缺陷（test-validate-report.md 静态验证发现，截至快照时间**均未修复**，实现代码与 spec 行为不一致）

| # | 严重度 | 位置 | 问题 | 影响 |
|---|---|---|---|---|
| Bug-1 | 高 | `MixGrowthFundRewardTierRow.cs:21` | `amType` 硬编码传 0，永远走 `GetConditionText` 的 default 分支，所有档位条件文案显示为 `"{0}/{1}"` 而非 `"Lv.X/Lv.Y"` 等预期格式 | TC-04/05/18/19 |
| Bug-2 | 高 | `MixGrowthFundModule.cs:137`（`RefreshRewardStatuses`） | `CurNum`/`TargetNum` 从未被赋值，恒为 0，导致 `HasRedPoint` 里 `0>=0` 恒真，任何未领取奖励都误报红点，与条件是否达成无关 | TC-15/16/17 |
| Bug-3 | 高 | `MixGrowthFundModule.cs:109-115`（`OnRedChanged`） | 把 `BARewardState.Can==1` 当"可领"判断，但 Record 里 1 实际是"已领取"（`MIX_GROWTHFUND_REWARD_RECEIVED=1`），逻辑完全反了——已领取时误报有红点，未领取时误报无红点 | TC-14/15/16/17 |
| Bug-4 | 中 | `MixGrowthFundModule.cs:182`（`HasRedPoint`） | 遍历 `m_RewardStatuses` 未按 `activityId` 过滤（`key>>32==activityId`），多基金并存时基金 B 的未领记录会污染基金 A 的红点判断 | TC-20 |
| Bug-5 | 低 | `MixGrowthFundPage.cs:129-132` | 只处理 `isPurchased` 两态文案，没调用已存在的 `IsActivityActive`，售卖期结束后未购买玩家仍看到"购买"文案（按钮虽因活动数据不下发而失效，但文案误导） | TC-03 |

修复建议摘要（详见 test-validate-report.md 原文）：Bug-1 需要 `SetData` 接收 amType（从本地 `activity_goal` 配表查 `Type` 字段，而不是从协议解析，因为协议这块已被设计为跳过）；Bug-2 需要在 `ParseQueryInfo` 回调时把 `CurNum`/`TargetNum` 一起写入 `m_RewardStatuses`；Bug-3 改判断 `UNCLAIMED(0)` 而不是 `Can(1)`，且应结合条件达成态（建议直接复用修复后的 `HasRedPoint` 逻辑代替 `OnRedChanged` 里的独立判断）；Bug-4 加 activityId 过滤。

## 9. 设计文档里已订正的错误（早期草稿 vs 最终核实结果，AI 若读到旧措辞要能识别是错的）

以下是 design.md/design/*.md 正文里明确标注"此前草稿误写为 XXX"的项，列出来避免重复犯错：

| 类别 | 早期错误写法 | 订正后正确写法 |
|---|---|---|
| 主表表名 | `activity_mix_growthfund_main` | `active_fund_main` |
| 主表字段名 | `PeriodName`/`NextPeriodName`/`ReserveSec` | `Name`/`NextActiveName`/`ReserveTime` |
| Record 列 | 曾假设存在 `GOAL_ID`/`GOAL_FINISH_FLAG` 两列 | 这两列**不存在**，条件进度用通用 `ACTIVITY_GOAL_REC` 的 `GOAL_PROGRESS`/`REWARD_STATUS` |
| 服务端领取协议函数名 | `OnBizActivCustomGetReward` | `OnCustomGetReward` |
| 服务端基础协议名 | 曾假设存在 `C2S_BIZACTIV_START`/`S2C_BIZACTIV_START`/`S2C_BIZACTIV_REMIND` | 这些协议**不存在**，复用通用 BusinessActivity 框架协议（见 §4） |
| 配置表字段属性 | 全部标 `S`（Server-only） | 全部改标 `A`（All）——S 会导致不生成强类型字段 |
| 客户端模块目录 | `LogicModule/BusinessActivityModule/MixGrowthFundModule/` | `LogicModule/ActivityModule/MixGrowthFundModule/`（与 ActivityDrawKOIModule 等同类模块保持一致；**但 `LogicModule/BusinessActivityModule/MixGrowthFundModule` 目录在文件系统里依然存在**，可能是迁移残留，见 §11） |
| UI 面板注册路径 | 三层路径 `WelfareActivityPanel/MixGrowthFundPanel/MixGrowthFundPage` | 两层路径 `WelfareActivityPanel/MixGrowthFundPage`（实际 prefab 在 `Assets/Resources/PanelUI/WelfareActivityPanel/MixGrowthFundPage.prefab`） |
| 服务端配置加载宏 | `READ_FILE`（design.md 早期声明"服务端无需改动"） | 必须改成 `READ_SYNC_FILE`（见 §5 第3点），design.md 这一处早期判断是错的 |
| "延长领取期"机制 | plan/working.md 详细设计了公式化延期方案 | 服务端无存储载体，**技术评审后确认不实现**，见 §7 |
| 一键领取 | plan/working.md 原文"逐档点击，不提供一键批量领取" | 决策记录 #10 反转为"点击任意格子触发一键领取全部" |

## 10. 文件系统实际落点（已用 find 核实，D:/se/develop/client/project 下真实存在的文件，可与 tasks.md/design.md 声称的路径交叉核对）

```
Assets/Script/LogicModule/ActivityModule/MixGrowthFundModule/
  MixGrowthFundDefine.cs
  MixGrowthFundModule.cs
  MixGrowthFundModule_Net.cs
Assets/Script/UISript/WelfareActivityPanel/MixGrowthFundPanel/
  MixGrowthFundPage.cs
  MixGrowthFundRewardCell.cs
  MixGrowthFundRewardTierRow.cs
Assets/Script/Table/Generate/Activity/
  TDActivityMixGrowthfundReward.cs
  TDActivityMixGrowthfundRewardTable.cs
Assets/Script/Table/Extend/Activity/
  TDActivityMixGrowthfundRewardExtend.cs
  TDActivityMixGrowthfundRewardTableExtend.cs
Assets/Resources/PanelUI/WelfareActivityPanel/
  MixGrowthFundPage.prefab
  MixGrowthFundPanel/MixGrowthFundPageClone.prefab
```

`TDActiveFundMain*.cs`（主表代码生成产物，`Assets/Script/Table/Generate|Extend/Activity/TDActiveFundMain*.cs`）已核实确实存在，implementation-report.md 声称生成的 8 个文件（ActiveFundMain 4个 + ActivityMixGrowthfundReward 4个）都能在文件系统找到。

`LogicModule/BusinessActivityModule/MixGrowthFundModule/` 目录仍存在于文件系统，但**已核实为空目录**（无 .cs 文件，只有目录本身+.meta），是迁移到 `LogicModule/ActivityModule/MixGrowthFundModule/` 后的残留空壳，不含代码，不影响编译，可忽略。

## 11. 与 test-cases.md 的映射（AI 做回归验证时用这张表定位，不用重新读 spec.md 拆需求）

TC-01~03 购买；TC-04~06 条件进度+顺序解锁；TC-07~09 免费奖励；TC-10~11 投资奖励；TC-12~13 双轨独立；TC-14~17 红点；TC-18~20 配置化。已知会失败/受已知 bug 影响的：TC-03(Bug-5)、TC-04/05(Bug-1)、TC-06(未验证服务端实现)、TC-14~17(Bug-2/3)、TC-18/19(Bug-1)、TC-20(Bug-4)。TC-02/07/08/09/10/11/12/13 静态验证通过，逻辑可信。

## 12. 尚未执行的收尾工作（implementation-report.md §5/§7 记录，非本次 AI 阅读范围但要知道存在）

- 4 个策划配置任务未填数据（active_fund_main.xlsx / activity_mix_growthfund_reward.xlsx / recharge.xlsx 新增条目 / activity_goal.xlsx 10 档条件）。
- 8 个 Integration 联调任务（tasks.md §5）未执行，全部依赖上面配置数据到位后才能跑。
- 语言表 12 个 key 待导入 `language.xlsx`（清单见 `Language_Keys.md`）。
- 服务端编译未在 Linux 环境验证（implementation-report.md 在 Windows 环境跳过）。
- 7 个非相关配置表（Fashion/Minigame/Pet/Prop/Pushgift/Question）在代码生成过程中被工具误触，需核实是否有意外改动。
- `protocol-*.md` 系列 6 份文档讨论的"协议精简"（把每档 9 字段减到 3 字段）和"design 规则补全"（client-structure.md 新增协议解析起始索引章节）都是**提案性质，未被采纳/未被执行**，不代表当前协议或 SKILL 规则已经改变。

