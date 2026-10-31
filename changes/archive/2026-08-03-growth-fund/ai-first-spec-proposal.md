
> **设计目标**：让 AI 在第一步就能准确理解功能，无需人类策划案的叙事性包装。
> **验证方法**：用这个格式描述 growth-fund，对比原始 `plan/working.md`（350行含大量讨论）→ 目标压缩到 150-200 行纯事实。

---

## § ESSENCE（本质）

### 一句话
玩家一次性付费解锁"投资奖励"领取权，通过达成条件（等级/爬塔等）逐档解锁双轨奖励（免费全员可领，投资仅付费可领）。

### 核心循环
```
未购买时：达成条件 → 领取免费奖励
已购买时：达成条件 → 领取免费奖励 + 投资奖励
```

### 类比已知概念
- **Battle Pass**（战斗通行证）：Fortnite/Genshin 的双轨奖励机制
- **差异点**：条件不是"完成任务获得经验"而是"等级/爬塔层数"等玩家成长指标

---

## § WORLD（世界观）

### Entities（实体定义）

#### Entity: Fund（基金）
```yaml
Fund:
  id: ActiveId (int, PK)               # 活动ID
  price: RechargeId → recharge.xlsx    # 价格（通过充值表关联）
  category: Direct (string)            # 分类标识（相同值归到同一Tab）
  tiers: Tier[] (1..N)                 # 档位列表
  sale_period: [start_time, end_time]  # 售卖时段
```

#### Entity: Tier（档位）
```yaml
Tier:
  id: RewardId (int, 1..10)            # 档位序号（固定1-10）
  condition:                           # 解锁条件
    type: ConditionType (enum)         # 条件类型
    value: int                         # 目标值
  rewards:
    free: ItemReward[]                 # 免费奖励（所有玩家）
    paid: ItemReward[]                 # 投资奖励（付费玩家）
```

#### Entity: PlayerFundState（玩家状态）
```yaml
PlayerFundState:
  player_id: int
  fund_id: ActiveId
  purchased: bool                      # 是否购买
  tier_states: Map<RewardId, TierState>

TierState:
  free_claimed: bool                   # 免费奖励已领
  paid_claimed: bool                   # 投资奖励已领
  condition_progress: int              # 条件当前进度（如当前等级30）
  condition_target: int                # 条件目标值（如目标等级35）
```

### State Machine（关键状态转移）

```
档位状态（单档单轨道）:
  Locked（条件未达成）
    ↓ [条件达成]
  Claimable（可领取）
    ↓ [点击领取 + 背包不满]
  Claimed（已领取）

投资奖励额外前置状态:
  LockedByPurchase（未购买基金）
    ↓ [购买成功]
  （进入上述流程）
```

### Relations（实体关系）

```
Player --[0..N]--> PlayerFundState --[1]-- Fund
Fund --[1..10]--> Tier
Tier --[委托]--> ActivityGoalModule (条件追踪)
```

---

## § RULES（规则）

### R1: 基金购买
```gherkin
GIVEN 基金处于售卖期 AND 玩家未购买
WHEN 点击购买按钮 AND 完成第三方SDK支付
THEN 
  - PlayerFundState.purchased = true
  - 所有投资奖励列从 LockedByPurchase → (Locked | Claimable)
  - 购买按钮显示"已购买"且禁用

NOT ALLOWED:
  - 重复购买同一基金
  - 售卖期结束后购买（按钮置灰）
```

### R2: 奖励领取（免费/投资共用逻辑，差异只在前置条件）
```gherkin
GIVEN 档位N的条件已达成 (progress >= target)
  AND 档位N-1的同轨道奖励已领取（顺序校验）
  AND 档位N的该轨道奖励未领取
  AND [仅投资奖励] PlayerFundState.purchased = true
WHEN 点击奖励图标
THEN
  - 校验背包空间（满则拒绝，不扣记录）
  - 发放奖励到背包
  - TierState.{free|paid}_claimed = true
  - 图标变灰 + 红点消失

NOT ALLOWED:
  - 跳档领取（第N档在第N-1档未领时不可领）
  - 条件未达成时领取（按钮置灰不响应）
```

### R3: 条件追踪（委托给通用模块）
```gherkin
GIVEN 档位N配置了条件 (type=LEVEL, value=30)
WHEN 玩家等级从29升到30
THEN ActivityGoalModule 更新 ACTIVITY_GOAL_REC.GOAL_PROGRESS = 30
  AND 客户端下次拉取数据时 condition_progress = 30
  AND 档位状态从 Locked → Claimable

支持的条件类型（枚举）:
  LEVEL(1) → 玩家等级
  TOWER_FLOOR(37) → 爬塔层数
  CUMULATIVE_LOGIN(244) → 累计登录天数
  QUEST(8) → 任务完成
  POWER(109) → 战力值
```

### R4: 红点显示
```gherkin
主入口红点:
  WHEN 售卖期内未购买 OR 任意档位任意轨道可领取
  THEN 显示红点

档位图标红点:
  WHEN 该档该轨道 (条件达成 AND 未领取 AND [投资需已购买])
  THEN 显示红点

全部领完:
  WHEN 所有档位免费已领 AND (未购买 OR 所有档位投资已领)
  THEN 无红点 + 显示"已完成"角标
```

---

## § BOUNDARIES（边界）

### Reuse（复用现有系统）

| 功能 | 复用模块 | 接口/协议 |
|-----|---------|----------|
| 支付流程 | 充值系统 | `RechargeType=5` (GrowthFund) + 第三方SDK |
| 条件追踪 | ActivityGoalModule | `CheckRewardCanGet` / `ACTIVITY_GOAL_REC` |
| 活动框架 | BusinessActivityModule | `BA_TYPE_MIX_GROWFUND=1018` |
| 配置同步 | ConfigSyncModule | `READ_SYNC_FILE` / `DynamicConfigModule` |

### Data Sources（数据分层）

| 数据类型 | 来源 | 示例 |
|---------|------|------|
| 静态配置 | 配置表（整表同步到客户端） | 奖励内容、条件类型、价格 |
| 玩家状态 | 服务端Record表 + 协议下发 | 是否购买、已领取档位、条件当前进度 |
| UI文案 | 语言表 | "购买"/"已购买"/"Lv.{0}/Lv.{1}" |

### Out of Scope（明确不做）

```diff
- 不做领取期延长机制（无存储字段支持"购买时刻+30天"）
- 不做每日返利/累计返利等其他形态（只做条件解锁型）
- 不做独立的"一键领取"按钮（点任意可领格子触发全部领取）
- 不显示档位序号文案（用条件文案标识，如"Lv.30"而非"第3档"）
- 不显示整体进度条（只显示单档进度，如"25/30"）
- 不做终极大奖独立展示区（最后一档与其他档位平等呈现）
- 购买按钮无"购买中"等待态（第三方SDK接管交互）
- 领取按钮无"领取中"等待态（同步协议立即返回）
```

---

## § EVIDENCE（验证标准）

### Golden Path（黄金路径）

```gherkin
场景1: 未购买玩家领取免费奖励
  1. 打开基金面板 → 看到10档奖励，投资列带锁
  2. 玩家等级达到20级 → 第1档免费奖励图标高亮+红点
  3. 点击第1档免费奖励 → 奖励到背包，图标变灰
  4. 尝试点击第3档免费奖励 → 按钮置灰不响应（因第2档未领）

场景2: 已购买玩家领取双轨奖励
  1. 点击购买按钮 → 调起SDK支付 → 完成
  2. 投资奖励列解锁，第1档投资奖励高亮+红点
  3. 点击第1档免费奖励 → 免费奖励到背包
  4. 点击第1档投资奖励 → 投资奖励到背包
  5. 两个奖励独立变灰，互不阻塞
```

### Edge Cases（边界场景）

```gherkin
E1: 背包满时领取
  WHEN 点击领取 BUT 背包空间不足
  THEN 提示"背包已满" + 领取记录不扣 + 状态仍为可领取

E2: 售卖期结束后
  WHEN 售卖期结束 AND 玩家未购买
  THEN 购买按钮置灰 + 显示"售卖已结束"
  AND 已购买玩家仍可正常领取（无领取期限制）

E3: 跨档领取校验
  WHEN 第1/2/3档条件全达成 BUT 第1档未领
  THEN 第2/3档点击无响应（服务端拒绝）

E4: 多基金独立性
  WHEN 配置ActiveId=10001和10002两个基金
  THEN 购买记录独立、领取记录独立、红点独立
```

### Anti-Patterns（防错模式）

```diff
❌ 错误实现1: 从协议解析奖励内容
  问题: 奖励内容是静态配置，应从本地配置表读取
  正确: 协议只下发 RewardId + 条件进度，奖励内容查表

❌ 错误实现2: 红点判断用 Record 的"已领=1"当"可领=1"
  问题: MIX_GROWTH_FUND_REWARD_REC 的 1=已领取，0=未领取
  正确: 可领 = (条件达成 AND 未领取 AND [投资需已购买])

❌ 错误实现3: 条件文案硬编码
  问题: 所有档位显示"{0}/{1}"而非"Lv.30/Lv.35"
  正确: 维护 AM_TYPE → 文案模板映射表

❌ 错误实现4: 协议解析起始索引错误
  问题: BusinessActivity框架已占用前13个字段，从0解析会错位
  正确: 从 BAActivityInfoIndex.CustomStart (索引13) 开始解析
```

---

## § IMPLEMENTATION HINTS（实现提示）

### 配置表结构速查

```yaml
active_fund_main.xlsx:
  - ActiveId (int, PK)
  - RechargeId (int, FK → recharge)
  - Direct (string, 分组key)
  - 保留字段: DisplayType, Name, NextActiveName, ReserveTime

activity_mix_growthfund_reward.xlsx:
  - ActiveId (int, FK)
  - RewardId (int, 1..10)
  - FreeReward (string, "itemId:count")
  - FreeHighlight (string, 特效ID)
  - PayReward (string, "itemId:count")
  - PayHighlight (string, 特效ID)

activity_goal.xlsx (通用表):
  - ActivityId + RewardId (复合key)
  - Type (int, AM_TYPE枚举值: 1/37/244/8/109)
  - Num (int, 目标值)
  - Target (string, 部分条件类型需要，如爬塔的"章节ID,层数")
```

### 服务端 Record 表速查

```yaml
GROWTH_FUND_OPEN_REC:
  Col0: ACTIVITY_ID (dword)

MIX_GROWTH_FUND_REWARD_REC:
  Col0: KEY (int64, merge(activityID, rewardID))
  Col1: ACTIVITY_ID (dword)
  Col2: REWARD_ID (dword)
  Col3: FREE_REWARD_STATUS (dword, 0=未领 1=已领)
  Col4: PAID_REWARD_STATUS (dword, 0=未领 1=已领)

ACTIVITY_GOAL_REC (通用表):
  Col3: GOAL_PROGRESS (int64, 当前进度 CurNum)
  Col6: TYPE (dword, AM_TYPE)
  # 其余列见完整文档
```

### 协议字段速查（自定义数据段，前面还有13个框架固定字段）

```yaml
OnBizActivCustomQueryInfo outArgs:
  # 基金主配置 (一次性)
  [0] RechargeId (int)
  [1] Direct (string)
  [2] DisplayType (int)
  [3] Name (string)
  [4] NextActiveName (string)
  
  # 每档奖励 (循环N次)
  [+0] RewardId (int)
  [+1] FreeReward (string)       ← 客户端跳过，查本地表
  [+2] FreeHighlight (string)    ← 客户端跳过
  [+3] PayReward (string)        ← 客户端跳过
  [+4] PayHighlight (string)     ← 客户端跳过
  [+5] LanguagePack (string)     ← 客户端跳过
  [+6] Url (string)              ← 客户端跳过
  [+7] CurNum (int64)            ← 客户端需要
  [+8] TargetNum (int64)         ← 客户端需要
```

### 客户端配置表接入检查清单

```
☐ outcode_config.json 的 need_copy 和 NeedParseDataMethod 都添加两张表
☐ 生成 8 个文件 (TDActiveFundMain + TDActivityMixGrowthfundReward 各4个)
☐ DynamicConfigModule_Process.cs 里对两张表各调一次 RegisterTable（表级注册）
☐ MixGrowthFundModule 实现 IConfigSyncMethod + OnInit里调 RegisterSyncMethod(this)（活动级注册）
☐ 服务端 LoadMainCfg/LoadRewardCfg 用 READ_SYNC_FILE 而非 READ_FILE
☐ 测试: TDActiveFundMainTable.GetData(activeId) 返回非默认值（表示数据链路通了）
```

---

## § METADATA（元信息）

**验证案例**: changes/growth-fund  
**实施时间**: 2026-07-31  
**文档版本**: v1.0  
**对比基线**: plan/working.md (350行，含大量人类决策过程)  
**压缩率**: 本文档 ~220行（纯事实，无叙事包装）

**已知实现缺陷**（快照时未修复）:
- Bug-1: 条件文案 amType 硬编码0
- Bug-2/3: 红点逻辑错误（CurNum恒0 + 已领/可领判断反了）
- Bug-4: HasRedPoint 未按 activityId 过滤
- Bug-5: 售卖期结束 UI 状态未实现

**该格式解决的问题**:
1. ✅ 无歧义：Rules 用 GIVEN/WHEN/THEN，防止 AI 误读
2. ✅ 防过度：Out of Scope 明确列出不做的东西（原文档里"延长领取期"写了2屏但最终没做）
3. ✅ 可验证：Evidence 可直接转测试用例
4. ✅ 可解析：Entities 可直接生成 Record 表定义
5. ✅ 快速定位：Implementation Hints 列出关键字段/枚举值，AI 无需反复查文档
