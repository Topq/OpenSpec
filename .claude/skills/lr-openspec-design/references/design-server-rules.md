# design-server.md 生成规则

> **说明**: 本文档定义 design-server.md 的生成规则。
> 该文档从 proposal.md 和 specs/*.md 生成，用于服务端工程师技术评审。
> 
> **重要**: design-server.md 是技术评审的必要输入，用于对齐协议、Record表、配置表设计。

---

## 一、design-server.md 规则

### 1.1 文档结构

```markdown
# Design: {功能名称} - Server

## 背景与目标
[从 proposal.md 的 Why 部分继承]

## 模块定义

**模块名称**: {XXX}Module
**文件路径**: `FsGame/{YYY}Module/{XXX}Module/`

**文件组织**:
- {XXX}Module.h              // 模块定义、接口声明、配置结构体
- {XXX}Func.cpp              // 业务逻辑实现
- {XXX}EventCallBack.cpp     // 事件监听回调（可选）
- {XXX}Define.h              // 宏定义、枚举、常量

**依赖模块**:
- XXXModule (说明依赖原因)
- YYYModule (说明依赖原因)

## Record 表定义

> **重要**: Record 表定义必须与客户端完全对齐（表名、列顺序、数据类型）

### {表名1}

**表名宏**: `{TABLE_NAME_REC}`
**用途**: [说明这个表存储什么数据]
**数据持久化**: 是/否
**同步到客户端**: 登录时 / 变化时推送

**列定义**:
```cpp
// {XXX}Define.h
#define {TABLE_NAME_REC} "table_name_rec"
enum
{
    TNREC_COL_COLUMN_NAME1,  // int    - 字段说明
    TNREC_COL_COLUMN_NAME2,  // string - 字段说明
    TNREC_COL_COLUMN_NAME3,  // int64  - 字段说明
};
```

**访问方式说明**：
- 通过 `pKernel->GetRecord(player, {TABLE_NAME_REC})` 获取表引用
- 通过 `rec.QueryInt(row, TNREC_COL_COLUMN_NAME)` 查询字段值
- 通过 `rec.FindInt(TNREC_COL_COLUMN_NAME, value)` 查找行索引

**设计决策**：
- 为什么：使用 Record 系统统一管理玩家数据，支持持久化和同步
- 列枚举顺序：必须与客户端完全一致，避免数据错位

### {表名2}
[重复上述结构]

## 配置表定义

> **重要**: 必须列出完整字段（字段名、类型、说明、示例值）

### {配置表1} - `{table_name}.xlsx`

**表用途**: [说明这个配置表的作用]

**完整字段定义**:

| 字段名 | 类型 | 说明 | 示例值 | 必填 |
|--------|------|------|--------|------|
| ActiveId | int | 活动ID，唯一标识 | 1001 | 是 |
| RechargeId | int | 关联的充值档位ID | 5001 | 是 |
| Name | string | 基金名称（客户端显示） | "成长基金" | 是 |
| DisplayType | int | 显示类型：1=自然时间, 2=永久 | 1 | 是 |
| PeriodName | string | 时间配置名称（关联时间表） | "growth_fund_202607" | 否 |
| RewardList | string | 奖励列表（格式："id:id:id"） | "1:2:3:4" | 是 |
| FreeReward | string | 免费奖励（格式："itemID,count;itemID,count"） | "10001,100;10002,50" | 是 |
| PayReward | string | 投资奖励（格式同上） | "10001,300;10002,150" | 是 |
| ConditionType | int | 条件类型：1=等级, 2=爬塔, 3=累计登录 | 1 | 是 |
| ConditionValue | int | 条件值 | 40 | 是 |

**配置结构体**:
```cpp
// {XXX}Module.h
struct ST{ConfigName}
{
    int nActiveId;              // 活动ID
    int nRechargeId;            // 充值ID
    fast_string strName;        // 基金名称
    int nDisplayType;           // 显示类型
    fast_string strPeriodName;  // 时间配置名称
    fast_string strRewardList;  // 奖励列表
    // ... 其他字段
};
```

**加载方式说明**:
- 使用 `READ_FILE` 宏读取 txt 文件
- 使用 `txt.ReadInt(i, "FieldName")` 按字段名读取（字段名必须与 Excel 列名完全一致）
- 使用 `std::map` 存储配置，主键作为 map 的 key
- 使用 `LogicAssert` 检查主键不重复

**设计决策**:
- 为什么：使用 READ_FILE 宏统一配置加载方式，减少重复代码
- 字段名匹配：必须与 Excel 列名完全一致（大小写敏感），确保读取正确
- map 存储：按主键索引，O(log n) 查询效率
- 备选方案：使用 vector 存储
- 为什么不选：查询效率低（O(n)），不适合频繁查询场景

### {配置表2}
[重复上述结构]

## 协议定义

> **协议号生成机制**: 同客户端，由服务器端在 `ClientCustomDefine.h` 和 `ServerCustomDefine.h` 中自动分配
> **协议定义必须与客户端完全对齐**（协议号、参数顺序、数据类型）

### C2S 协议处理

#### C2S_XXX_Purchase - 购买请求处理
```cpp
协议号: {待自动分配} - CLIENT_CUSTOMMSG_{XXX}_PURCHASE
参数 (IVarList):
  [0] int activityID    // 活动ID
  [1] int rechargeID    // 充值档位ID

处理回调: OnGrowthFundDispose (由充值系统触发，不是直接协议回调)
注册方式: 通过充值模块注册发货回调
```

#### C2S_XXX_Claim - 领取请求处理
```cpp
协议号: {待自动分配} - CLIENT_CUSTOMMSG_{XXX}_CLAIM
参数 (IVarList):
  [0] int activityID    // 活动ID
  [1] int rewardID      // 奖励ID
  [2] int claimType     // 领取类型：1=单个, 2=批量

处理回调: OnCustomGetReward
注册方式: ADD_INT_CUSTOM_HOOK("MainPlayer", CLIENT_CUSTOMMSG_{XXX}_CLAIM, OnCustomGetReward, SERVER_TYPE_GAME_MEMBER)
```

### S2C 协议下发

#### S2C_XXX_Purchase_Result - 购买结果下发
```cpp
协议号: {待自动分配} - SERVER_CUSTOMMSG_{XXX}_PURCHASE_RESULT
参数 (IVarList):
  [0] int result        // 结果码: 0=成功, 其他=错误码

下发时机: 充值回调处理完成后，由充值系统自动下发
```

#### S2C_XXX_Claim_Result - 领取结果下发
```cpp
协议号: {待自动分配} - SERVER_CUSTOMMSG_{XXX}_CLAIM_RESULT
参数 (IVarList):
  [0] int result        // 结果码
  [1] string rewards    // 奖励列表

下发函数:
CVarList msg;
msg << SERVER_CUSTOMMSG_{XXX}_CLAIM_RESULT << result << rewards;
pKernel->Custom(player, msg);
```

#### S2C_XXX_ConditionUpdate - 条件变化推送
```cpp
协议号: {待自动分配} - SERVER_CUSTOMMSG_{XXX}_CONDITION_UPDATE
参数 (IVarList):
  [0] int activityID    // 活动ID
  [1] int rewardID      // 奖励ID
  [2] int conditionMet  // 是否达成: 0=否, 1=是

推送时机: 监听到等级变化/爬塔进度变化等事件后，检查条件并推送
```

### 错误码

> **说明**: 服务器错误码用于行为判断，需与客户端错误码数值对齐

```cpp
// {XXX}Define.h
#define XXX_ERR_SUCCESS 0                // 成功
#define XXX_ERR_NOT_OPEN 1001            // 活动未开启
#define XXX_ERR_ALREADY_PURCHASED 1002   // 已购买（不可重复购买）
#define XXX_ERR_CONDITION_NOT_MET 1003   // 条件未达成
#define XXX_ERR_ALREADY_CLAIMED 1004     // 已领取
#define XXX_ERR_CONFIG_ERROR 1005        // 配置错误（找不到配置）
#define XXX_ERR_NOT_PURCHASED 1006       // 未购买（领取投资奖励时）
#define XXX_ERR_BAG_FULL 1007            // 背包已满（无法发放奖励）
```

## 业务逻辑流程

### 购买流程

```cpp
1. OnGrowthFundDispose() - 充值回调
   ↓
2. CheckCanRecharge() - 检查是否可购买
   - 查找配置 GetMainConfig(activityID)
   - 检查 rechargeID 是否匹配
   - 检查 Record 表是否已购买
   ↓
3. DoGrowthFundDispose() - 发货逻辑
   - 写入购买记录到 GROWTH_FUND_OPEN_REC
   - 写统计日志
   ↓
4. 返回 RECHARGE_DISPOSE_RES_CODE_OK
   ↓
5. 充值系统通知客户端购买成功
```

### 领取流程

```cpp
1. OnCustomGetReward() - 协议处理
   ↓
2. GetReward() - 检查领取条件
   - IsFundActivate() 检查是否已购买（投资奖励需要）
   - CheckRewardCanGet() 检查条件是否达成
   - 检查 Record 是否已领取
   ↓
3. SendReward() - 发放奖励
   - SendFreeReward() 发放免费奖励
   - SendPayReward() 发放投资奖励（已购买）
   - 更新 Record 领取标记
   - 写统计日志
   ↓
4. QueryInfo() - 构造返回数据
   ↓
5. 返回 S2C_XXX_Claim_Result
```

### 条件触发流程

```cpp
1. BuildGoal() - 活动开始时创建条件目标
   ↓
2. 监听事件（例如等级变化）
   ↓
3. 条件达成检查
   - 更新 ACTIVITY_GOAL_REC
   - 标记为可领取状态
   ↓
4. 推送客户端 S2C_XXX_ConditionUpdate
   ↓
5. 客户端刷新红点
```

### 过期处理流程

```cpp
1. OnBizActivRemove() - 活动结束回调
   ↓
2. ClearGoal() - 清理目标
   - 遍历 ACTIVITY_GOAL_REC
   - 检查未领取的奖励
   - 构造邮件附件列表
   ↓
3. SendRetrieveMail() - 发送补发邮件
   ↓
4. ClearRewardRecord() - 清理领取记录
   ↓
5. CloseFund() - 移除购买记录
```

## 关键功能说明

> **说明**: 本节说明关键功能的职责和设计决策，不包含具体实现代码（实现代码在 tasks 环节）

### 充值回调处理

**职责**：
- 接收充值系统回调（OnGrowthFundDispose）
- 校验充值档位是否匹配配置
- 检查是否重复购买
- 写入购买记录到 GROWTH_FUND_OPEN_REC
- 写统计日志

**设计决策**：
- 为什么：由充值系统触发，而非客户端直接协议，确保支付完成后才发货
- 参数传递：通过 szParam 传递 activityID，充值系统透传
- 备选方案：客户端协议直接触发购买
- 为什么不选：无法保证支付成功，存在刷单风险

### 领取奖励处理

**职责**：
- 接收客户端领取请求（OnCustomGetReward）
- 检查是否已购买（投资奖励需要）
- 检查条件是否达成
- 检查是否已领取
- 发放奖励（免费 / 投资）
- 更新领取记录
- 返回奖励数据给客户端

**设计决策**：
- 为什么：服务器权威校验，防止客户端伪造领取请求
- 领取顺序：无需强制顺序，任意档位达成即可领取
- 备选方案：强制按顺序领取
- 为什么不选：限制玩家体验，且无业务必要性

### 条件目标管理

**职责**：
- 活动开始时创建条件目标（BuildGoal）
- 监听事件（等级变化、爬塔进度等）
- 检查条件达成，更新 ACTIVITY_GOAL_REC
- 推送客户端条件更新（S2C_XXX_ConditionUpdate）

**设计决策**：
- 为什么：复用现有活动目标系统，减少重复实现
- 推送时机：条件达成时立即推送，触发客户端红点刷新
- 备选方案：客户端轮询查询
- 为什么不选：增加服务器压力，且实时性差

### 过期处理

**职责**：
- 活动结束回调（OnBizActivRemove）
- 清理条件目标（ClearGoal）
- 检查未领取奖励，构造邮件附件
- 发送补发邮件（SendRetrieveMail）
- 清理领取记录和购买记录

**设计决策**：
- 为什么：邮件补发确保玩家不丢失奖励
- 补发范围：已购买但未领取的奖励
- 免费奖励：不补发（活动结束后失效）
- 备选方案：所有未领取奖励都补发
- 为什么不选：免费奖励是活跃激励，过期失效符合设计

## 事件监听

**注册的事件**:
- 充值成功 → `OnGrowthFundDispose`
- 等级变化 → 检查条件并推送
- 爬塔进度变化 → 检查条件并推送
- 活动开始 → `OnBizActivStart`
- 活动结束 → `OnBizActivRemove`

**推送时机**:
- 条件达成时立即推送 `S2C_XXX_ConditionUpdate`
- 购买成功时推送购买记录（由充值系统触发）
- 领取成功时返回奖励数据

## 性能考虑

- **缓存配置**: 配置表加载到内存 map，避免每次查询读取文件
- **增量推送**: 条件变化时只推送变化的奖励ID，不全量推送
- **防刷检查**: 领取时校验条件达成和未领取，防止客户端伪造

## Open Questions

> **Open Questions 明确规则**: 
> 
> **必须出现的问题类型**:
> 1. **协议字段未确定**: 需要与客户端对齐但尚未确定的字段定义
> 2. **配置表结构**: 配置表字段、格式或关联关系未明确
> 3. **业务逻辑边界**: 状态机转换、错误处理或边界条件
> 4. **性能影响**: 可能影响性能的设计需要确认
> 5. **数据持久化**: Record 表持久化策略或同步时机
> 6. **跨模块依赖**: 需要其他模块提供支持但尚未确认的功能
> 
> **不应出现的问题**:
> - 已在 proposal 或 specs 中明确定义的内容
> - 纯技术实现细节（这应该在 design 中直接决定）
> - 过于宽泛的问题（"这个功能怎么做"）

### 协议相关

1. **C2S_XXX_Claim 批量领取返回值？**
   - 当前设计: 返回奖励列表字符串
   - 问题: 批量领取时是否需要返回每个奖励的详细信息（成功/失败）？
   - 影响: 协议字段定义、客户端处理逻辑

2. **S2C_XXX_ConditionUpdate 推送策略？**
   - 当前设计: 条件达成时立即推送
   - 问题: 等级变化等高频事件是否需要延迟合并推送？
   - 影响: 性能、推送频率控制

### 配置表相关

3. **条件类型枚举是否需要扩展？**
   - 当前定义: 1=等级, 2=爬塔, 3=累计登录
   - 问题: 是否需要支持"累计充值"、"完成指定任务"等条件类型？
   - 影响: 配置表字段、服务器判定逻辑

4. **奖励格式是否需要统一？**
   - 当前设计: 使用字符串格式 "itemID,count;itemID,count"
   - 问题: 是否需要支持多种奖励类型（道具、货币、经验）？
   - 影响: 配置表格式、解析逻辑

### 业务逻辑相关

5. **活动结束后未领取奖励的处理？**
   - 当前设计: 发送补发邮件
   - 问题: 邮件有效期是多久？是否需要区分免费和投资奖励？
   - 影响: 邮件系统、玩家体验

6. **购买后退款处理？**
   - 当前设计: 不支持退款
   - 问题: 如果支付平台退款，是否需要回收已领取的奖励？
   - 影响: 充值系统回调、Record 表设计

### 性能相关

7. **条件检查频率控制？**
   - 当前设计: 每次等级变化/爬塔进度变化时检查
   - 问题: 是否需要增加检查间隔或批量检查？
   - 影响: 性能、数据库查询频率
```
