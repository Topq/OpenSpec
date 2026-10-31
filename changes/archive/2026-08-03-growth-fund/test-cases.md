# Test Cases: growth-fund

## 功能点：growth-fund

### TC-growth-fund-01：售卖期内未购买玩家点击购买按钮

- **前置条件**：
  - 基金处于售卖期
  - 玩家未购买该基金

- **操作步骤**：
  1. 玩家点击购买按钮
  2. 系统调起第三方SDK支付
  3. 玩家完成支付

- **预期结果**：
  - 服务端记录购买记录（基金ID、购买时刻）
  - 投资奖励列解锁（锁图标消失）
  - 购买按钮变为"已购买"状态且不可再次点击
  - 已达成条件的投资奖励档位标记为可领取（图标高亮+红点）

- **验证点**：
  - 服务端 `OnGrowthFundDispose` 被调用，`GROWTH_FUND_OPEN_REC` 新增一行（Col0 ACTIVITY_ID）
  - 客户端收到 `COMMAND_BIZ_ACTIV_CHANGED` 后重新发起 `CLIENT_CUSTOMMSG_QUERY_ACTIVITY_INFO`
  - 客户端 `m_PurchasedFunds[activityId]` 置为 true
  - `GetPaidRewardState` 对已达成条件（`CurNum >= TargetNum`）的档位返回 `Claimable`

- **来源**：specs/growth-fund/spec.md - 基金购买 - 售卖期内未购买玩家点击购买按钮

---

### TC-growth-fund-02：售卖期内已购买玩家查看面板

- **前置条件**：
  - 基金处于售卖期
  - 玩家已购买该基金

- **操作步骤**：
  1. 玩家打开基金主面板

- **预期结果**：
  - 购买按钮显示"已购买"且不可点击
  - 投资奖励列无锁图标
  - 已达成条件的投资奖励档位显示为可领取

- **验证点**：
  - `IsFundActivate` 返回 true（`GROWTH_FUND_OPEN_REC.FindInt(ACTIVITY_ID, activityId) >= 0`）
  - `GetPaidRewardState(key, isPurchased=true)` 不返回 `LockedByPurchase`

- **来源**：specs/growth-fund/spec.md - 基金购买 - 售卖期内已购买玩家查看面板

---

### TC-growth-fund-03：售卖期结束后查看面板

- **前置条件**：
  - 基金售卖期已结束

- **操作步骤**：
  1. 玩家打开基金主面板

- **预期结果**：
  - 购买按钮置灰且不可点击
  - 显示"售卖已结束"标签
  - 未购买玩家的投资奖励列仍带锁
  - 已购买玩家的投资奖励列正常显示

- **验证点**：
  - 客户端通过 `BusinessActivityModule.IsActivityOpen()` 判断售卖期状态并置灰购买按钮
  - 未购买玩家 `GetPaidRewardState` 返回 `LockedByPurchase`

- **来源**：specs/growth-fund/spec.md - 基金购买 - 售卖期结束后查看面板

---

### TC-growth-fund-04：玩家等级达到档位条件

- **前置条件**：
  - 某档奖励配置为"等级30解锁"（`activity_goal.xlsx` Type=1 AM_TYPE_PLAYER_LEVEL, Num=30）
  - 玩家当前等级为29

- **操作步骤**：
  1. 玩家升级到30级

- **预期结果**：
  - 该档奖励标记为"已解锁"
  - 免费奖励图标高亮并显示红点
  - 若已购买基金，投资奖励图标高亮并显示红点
  - 条件进度显示"Lv.30/Lv.30"

- **验证点**：
  - 服务端 `ActivityGoalModule` 的 `ACTIVITY_GOAL_REC.GOAL_PROGRESS` 更新为30，`REWARD_STATUS` 变为 `ACTIVITY_GOAL_REWARD_OPEN`
  - 客户端下次 `CLIENT_CUSTOMMSG_QUERY_ACTIVITY_INFO` 收到 `CurNum=30, TargetNum=30`
  - `GetFreeRewardState`/`GetPaidRewardState` 在 `CurNum >= TargetNum` 时返回 `Claimable`
  - 客户端条件文案模板（AM_TYPE_PLAYER_LEVEL → "Lv.{当前}/Lv.{目标}"）渲染为"Lv.30/Lv.30"
  - `HasRedPoint` 返回 true

- **来源**：specs/growth-fund/spec.md - 条件进度查询 - 玩家等级达到档位条件

---

### TC-growth-fund-05：玩家查看未达成档位

- **前置条件**：
  - 某档奖励配置为"等级35解锁"
  - 玩家当前等级为30

- **操作步骤**：
  1. 玩家打开基金主面板

- **预期结果**：
  - 该档奖励图标置灰并显示锁图标
  - 条件进度显示"Lv.30/Lv.35"
  - 条件提示显示"Lv.35解锁"

- **验证点**：
  - 服务端下发 `CurNum=30, TargetNum=35`
  - `GetFreeRewardState` 返回 `Locked`（`CurNum < TargetNum`）
  - 条件文案模板渲染为"Lv.30/Lv.35"

- **来源**：specs/growth-fund/spec.md - 条件进度查询 - 玩家查看未达成档位

---

### TC-growth-fund-06：按顺序解锁规则（不可跳档）

- **前置条件**：
  - 档位1、2、3条件分别为等级20、25、30
  - 玩家当前等级30
  - 玩家未领取档位1和档位2的免费奖励

- **操作步骤**：
  1. 系统计算可领取档位

- **预期结果**：
  - 档位1标记为可领取
  - 档位2和档位3标记为"已解锁但需先领取前档"
  - 玩家必须先领取档位1，才能领取档位2

- **验证点**：
  - 服务端 `SendReward`/`GetReward` 调用 `g_pActivityGoalModule->CheckRewardCanGet`，该校验按档位顺序判断前档是否已领
  - 客户端点击档位2/3的领取按钮时，因服务端拒绝而不产生实际发放（前端仅展示态，实际拦截以服务端校验为准）

- **来源**：specs/growth-fund/spec.md - 条件进度查询 - 按顺序解锁规则（不可跳档）

---

### TC-growth-fund-07：条件达成后领取免费奖励

- **前置条件**：
  - 某档免费奖励已解锁（条件达成且前档已领）
  - 玩家未领取该档免费奖励

- **操作步骤**：
  1. 玩家点击免费奖励图标

- **预期结果**：
  - 服务端校验条件达成且前档已领
  - 发放免费奖励到玩家背包
  - 记录该档免费奖励已领取
  - 免费奖励图标变为置灰状态
  - 红点消失
  - 下一档（若条件达成）的免费奖励图标高亮并显示红点

- **验证点**：
  - 客户端发送 `CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD`（MIX_GROWTHFUND_REWARD_TYPE_FREE=1）
  - 服务端 `OnCustomGetReward` → `GetReward` → `SendFreeReward` → `CheckRewardCanGet(isFree=true)` 通过后 `SendReward` 写入 `MIX_GROWTH_FUND_REWARD_REC`
  - `MIX_GROWTH_FUND_REWARD_REC.FREE_REWARD_STATUS` 从 0 变为 1（MIX_GROWTHFUND_REWARD_RECEIVED）
  - `g_pItemBaseModule->AutoAddItems` 被调用发放 `cfg->freeReward`
  - 客户端本地 `MixGrowthFundRewardStatus.FreeStatus` 更新为1，`GetFreeRewardState` 返回 `Claimed`

- **来源**：specs/growth-fund/spec.md - 免费奖励领取 - 条件达成后领取免费奖励

---

### TC-growth-fund-08：条件未达成时点击免费奖励图标

- **前置条件**：
  - 某档免费奖励未解锁（条件未达成）

- **操作步骤**：
  1. 玩家点击免费奖励图标

- **预期结果**：
  - 图标不响应点击
  - 不发送领取请求

- **验证点**：
  - 客户端 UI 层在 `GetFreeRewardState` 返回 `Locked` 时禁用按钮点击事件，不触发 `CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD`

- **来源**：specs/growth-fund/spec.md - 免费奖励领取 - 条件未达成时点击免费奖励图标

---

### TC-growth-fund-09：已领取后查看免费奖励

- **前置条件**：
  - 某档免费奖励已领取

- **操作步骤**：
  1. 玩家打开基金主面板

- **预期结果**：
  - 该档免费奖励图标置灰
  - 无红点
  - 不可再次点击领取

- **验证点**：
  - 服务端下发的 `MIX_GROWTH_FUND_REWARD_REC.FREE_REWARD_STATUS` 为1
  - `GetFreeRewardState` 返回 `Claimed`
  - `HasRedPoint` 对该档不计入红点判断（`s.FreeStatus == 0` 条件不满足）

- **来源**：specs/growth-fund/spec.md - 免费奖励领取 - 已领取后查看免费奖励

---

### TC-growth-fund-10：购买后领取投资奖励

- **前置条件**：
  - 玩家已购买基金
  - 某档投资奖励已解锁（条件达成且前档已领）
  - 玩家未领取该档投资奖励

- **操作步骤**：
  1. 玩家点击投资奖励图标

- **预期结果**：
  - 服务端校验购买记录、条件达成且前档已领
  - 发放投资奖励到玩家背包
  - 记录该档投资奖励已领取
  - 投资奖励图标变为置灰状态
  - 红点消失

- **验证点**：
  - 客户端发送 `CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD`（MIX_GROWTHFUND_REWARD_TYPE_PAY=2）
  - 服务端 `SendPayReward` 先校验 `IsFundActivate`，再校验 `CheckRewardCanGet(isFree=false)`
  - `MIX_GROWTH_FUND_REWARD_REC.PAID_REWARD_STATUS` 从 0 变为 1
  - `g_pItemBaseModule->AutoAddItems` 被调用发放 `cfg->payReward`
  - 客户端 `GetPaidRewardState` 返回 `Claimed`

- **来源**：specs/growth-fund/spec.md - 投资奖励领取 - 购买后领取投资奖励

---

### TC-growth-fund-11：未购买时点击投资奖励图标

- **前置条件**：
  - 玩家未购买基金
  - 某档投资奖励已解锁（条件达成）

- **操作步骤**：
  1. 玩家点击投资奖励图标

- **预期结果**：
  - 图标不响应点击（带锁状态）
  - 不发送领取请求

- **验证点**：
  - 客户端 `GetPaidRewardState(key, isPurchased=false)` 返回 `LockedByPurchase`
  - UI 层禁用点击，不触发 `CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD`
  - 服务端 `SendPayReward` 即使被调用也会因 `IsFundActivate` 为 false 而拒绝（双重保护）

- **来源**：specs/growth-fund/spec.md - 投资奖励领取 - 未购买时点击投资奖励图标

---

### TC-growth-fund-12：先领免费后领投资

- **前置条件**：
  - 某档免费奖励和投资奖励均已解锁
  - 玩家已购买基金

- **操作步骤**：
  1. 玩家先点击免费奖励图标领取
  2. 玩家再点击投资奖励图标领取

- **预期结果**：
  - 免费奖励发放且标记为已领
  - 投资奖励仍保持可领取状态（图标高亮+红点）
  - 投资奖励发放且标记为已领

- **验证点**：
  - `MIX_GROWTH_FUND_REWARD_REC` 的 `FREE_REWARD_STATUS` 和 `PAID_REWARD_STATUS` 分别独立更新，互不影响
  - 领取免费奖励后 `GetPaidRewardState` 仍返回 `Claimable`（不受 `FreeStatus` 变化影响）

- **来源**：specs/growth-fund/spec.md - 双轨奖励独立领取 - 先领免费后领投资

---

### TC-growth-fund-13：仅领免费不领投资

- **前置条件**：
  - 某档免费奖励和投资奖励均已解锁
  - 玩家已购买基金

- **操作步骤**：
  1. 玩家只领取免费奖励，不领投资奖励

- **预期结果**：
  - 下一档的免费奖励（若条件达成）可正常领取
  - 当前档投资奖励保持可领取状态

- **验证点**：
  - 领取档位N的免费奖励不影响档位N+1的 `CheckRewardCanGet` 判定（前档判定只看该链路自身的领取状态，见 TC-growth-fund-06 的顺序解锁逻辑）
  - 当前档 `PAID_REWARD_STATUS` 保持0，`GetPaidRewardState` 持续返回 `Claimable`

- **来源**：specs/growth-fund/spec.md - 双轨奖励独立领取 - 仅领免费不领投资

---

### TC-growth-fund-14：售卖期内未购买（红点）

- **前置条件**：
  - 基金处于售卖期
  - 玩家未购买该基金

- **操作步骤**：
  1. 玩家查看主界面

- **预期结果**：
  - 基金主入口icon显示红点

- **验证点**：
  - 红点传播路径：`MixGrowthFundModule → BusinessActivityModule → GeneralActiveModule → RedPointModule → UI`
  - `GeneralActiveModule.OnMixGrowthFundRed` 被调用并返回 true

- **来源**：specs/growth-fund/spec.md - 红点显示 - 售卖期内未购买

---

### TC-growth-fund-15：有可领取的免费奖励（红点）

- **前置条件**：
  - 某档免费奖励已解锁且未领取

- **操作步骤**：
  1. 玩家打开基金主面板

- **预期结果**：
  - 该档免费奖励图标显示红点
  - 基金主入口icon显示红点

- **验证点**：
  - `HasRedPoint` 中 `goalFinished && s.FreeStatus == 0` 条件成立返回 true
  - 单档格子红点绑定 `#redpoint-free-{id}` GameObject 激活

- **来源**：specs/growth-fund/spec.md - 红点显示 - 有可领取的免费奖励

---

### TC-growth-fund-16：有可领取的投资奖励（红点）

- **前置条件**：
  - 玩家已购买基金
  - 某档投资奖励已解锁且未领取

- **操作步骤**：
  1. 玩家打开基金主面板

- **预期结果**：
  - 该档投资奖励图标显示红点
  - 基金主入口icon显示红点

- **验证点**：
  - `HasRedPoint` 中 `isPurchased && goalFinished && s.PaidStatus == 0` 条件成立返回 true
  - 单档格子红点绑定 `#redpoint-pay-{id}` GameObject 激活

- **来源**：specs/growth-fund/spec.md - 红点显示 - 有可领取的投资奖励

---

### TC-growth-fund-17：全部领完（无红点）

- **前置条件**：
  - 玩家已领取所有免费奖励
  - 玩家已购买基金且领取所有投资奖励

- **操作步骤**：
  1. 玩家查看主界面

- **预期结果**：
  - 基金主入口icon无红点
  - 基金主面板显示"已完成"角标

- **验证点**：
  - `HasRedPoint` 遍历所有档位后返回 false（`CheckRewardAllGet` 对 FREE 和 PAID 两列均为 true）
  - 客户端根据全部档位 `FreeStatus==1 && PaidStatus==1` 判定显示"已完成"角标

- **来源**：specs/growth-fund/spec.md - 红点显示 - 全部领完

---

### TC-growth-fund-18：配置等级解锁型基金

- **前置条件**：
  - 策划配置 `active_fund_main` 表：ActiveId=10001, Direct="成长计划"
  - 配置 `activity_mix_growthfund_reward` 表：10档奖励
  - 配置 `activity_goal.xlsx`：10条目标，Type=1 (AM_TYPE_PLAYER_LEVEL)，Num=20/25/30/35/40/45/50/55/60/65

- **操作步骤**：
  1. 客户端/服务端读取配置

- **预期结果**：
  - 系统按配置生成10档等级解锁型基金
  - 每档条件进度显示"Lv.X/Lv.Y"

- **验证点**：
  - 服务端 `LoadMainCfg`/`LoadRewardCfg` 成功加载，`m_fundCfgs`/`m_rewardCfgs` 各10条数据（无解析错误日志）
  - 客户端自动生成的 `TDActiveFundMain`/`TDActivityMixGrowthfundReward` 数据条数与配置一致
  - 条件文案模板对 AM_TYPE_PLAYER_LEVEL(1) 渲染"Lv.X/Lv.Y"格式

- **来源**：specs/growth-fund/spec.md - 配置化支持 - 配置等级解锁型基金

---

### TC-growth-fund-19：配置爬塔解锁型基金

- **前置条件**：
  - 策划配置ActiveId=10002
  - 配置 `activity_goal.xlsx`：Type=37 (AM_TYPE_PASS_TOWER_CHALLENGE)，Target="章节ID,层数"格式

- **操作步骤**：
  1. 客户端/服务端读取配置

- **预期结果**：
  - 系统按配置生成爬塔解锁型基金
  - 每档条件进度显示"爬塔X/爬塔Y"

- **验证点**：
  - 服务端 `GoalCondMatchParam1EqAndParam2GTE` 按 Target 的章节ID和层数匹配条件
  - 客户端条件文案模板对 AM_TYPE_PASS_TOWER_CHALLENGE(37) 渲染"爬塔X/爬塔Y"格式（Y取Target第二段层数）

- **来源**：specs/growth-fund/spec.md - 配置化支持 - 配置爬塔解锁型基金

---

### TC-growth-fund-20：多基金并存（不同ActiveId）

- **前置条件**：
  - 策划配置ActiveId=10001（成长计划）和ActiveId=10002（爬塔回赠）

- **操作步骤**：
  1. 客户端读取配置

- **预期结果**：
  - 基金主面板显示两个Tab（成长计划 / 爬塔回赠）
  - 每只基金独立购买记录、独立领取记录、独立条件进度

- **验证点**：
  - 客户端根据 `Direct` 字段值动态生成Tab，相同 `Direct` 分到同一Tab
  - `GROWTH_FUND_OPEN_REC`/`MIX_GROWTH_FUND_REWARD_REC` 按 `ActivityID` 区分不同基金的记录，互不影响

- **来源**：specs/growth-fund/spec.md - 配置化支持 - 多基金并存（不同ActiveId）
