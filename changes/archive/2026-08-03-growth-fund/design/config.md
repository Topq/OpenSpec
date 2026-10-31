# design-config.md

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
3. 生成 .txt 文件到  目录

### 服务端侧（txt → 内存结构）
1. 服务器启动时读取 .txt 文件
2.  解析主表
3.  解析奖励表
4. 加载到  和 
5. 通过  和  查询

### 客户端侧（txt → 自动生成代码）
1. Unity 编辑器读取 .txt 文件
2. 自动生成  和  类
3. 生成  注册代码
4. 客户端通过  访问配置

**注册说明**:
- 文件位置：
- 注册方式：在  数组中添加：
  - 
  - 

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

**属性说明**：本表全部字段为 **S（Server-only）**：字段语义完全属于服务端业务（活动ID、充值商品ID、分类标识），客户端不定义、不拥有这些字段的业务含义。但客户端仍需要以强类型对象形式使用这些值（见"客户端使用"列），因此需要生成配置表代码并接入 `DynamicConfigModule` 整表同步（不是通过协议解析获得，见下）。

**配置加载方式**：动态配置——本表内容（充值商品、分类标识）属于运营期间可调整的活动参数，服务端可随时修改 txt 文件后通过 `ConfigSyncModule` 整表推送机制同步给客户端本地内存，不需要客户端重新打包即可生效。

**⚠️ 服务端接入要求**：服务端配置加载必须使用 `READ_SYNC_FILE` 宏（而非 `READ_FILE` 宏），才能将表注册进 `ConfigSyncModule::mFileMap`。`READ_SYNC_FILE` 宏内部会调用 `load_sync_file()` → `ConfigSyncModule::LoadFile()` 完成注册；仅使用 `READ_FILE` 的表不会被注册，客户端无法通过 `CLIENT_CUSTOMMSG_PULL_CFGSYNC_FILES` 拉取。参考正确实现：`BATreasureHuntModule::LoadRoutimeCfg` 使用 `READ_SYNC_FILE`。

**客户端消费方式**：`output_code_csharp.bat` 生成 `TDActiveFundMain.cs`（数据行类，含 `ParseData`）和 `TDActiveFundMainTable.cs`（表管理类）后，接入 `DynamicConfigModule` 整表同步（在 `DynamicConfigModule_Process.cs::InitProcessDic()` 调用 `RegisterTable`），用法与 `TDActivityKoiRewardTable` 一致。`MixGrowthFundModule` 业务代码直接 `TDActiveFundMainTable.GetData(activeId)` 读取本地已同步数据，不从 `CLIENT_CUSTOMMSG_QUERY_ACTIVITY_INFO` 协议 outArgs 解析这些字段（该协议仍会下发这些字段，但客户端只取其中的 `RewardId`/`CurNum`/`TargetNum`，其余静态字段来自本表，见 design/client.md 网络协议章节）。

**outcode_config.json 配置建议**：需要配置。在 `need_copy` 中添加本表以生成客户端代码；在 `NeedParseDataMethod` 中添加本表以生成 `ParseData` 方法（供 `DynamicConfigModule` 整表同步时逐行解析）——判断依据是"动态配置 + 用于活动系统"。

**枚举值**:


**数据示例**:


**设计决策**:
- **ActiveId**: 沿用 BusinessActivity 框架的活动ID体系
- **RechargeId**: 关联充值系统，避免硬编码价格
- **Direct**: 用字符串而非枚举，支持策划灵活扩展基金类型

---

### activity_mix_growthfund_reward.xlsx

**表文件路径**: 
**用途**: 定义每档奖励内容（免费奖励、投资奖励）
**主键**: 复合键 (ActiveId + RewardId)

**字段定义**:

| 字段名 | 类型 | 属性 | 说明 | 示例值 | 必填/可选 | 客户端使用 | 服务器使用 |
|--------|------|------|------|--------|-----------|-----------|-----------|
| Id | int | S | 自增ID（忽略） | 1 | 否 | 否 | 否 |
| ActiveId | int | S | 所属活动ID | 10008 | 是 | 是 | 是 |
| RewardId | int | S | 奖励档位ID（1-10） | 1 | 是 | 是 | 是 |
| FreeReward | string | S | 免费奖励串 | 1003:188 | 是 | 是 | 是 |
| FreeHighlight | string | S | 免费奖励高亮标记（特效ID） |  | 否 | 是 | 否 |
| PayReward | string | S | 投资奖励串 | 1003:1080 | 是 | 是 | 是 |
| PayHighlight | string | S | 投资奖励高亮标记（特效ID） |  | 否 | 是 | 否 |

**属性说明**：本表全部字段为 **S（Server-only）**，理由同 active_fund_main.xlsx：字段语义属于服务端业务（奖励内容、档位ID），客户端需要以强类型对象形式使用这些值，接入 `DynamicConfigModule` 整表同步获得。

**配置加载方式**：动态配置——每档奖励内容属于运营期间可调整的活动参数，服务端可随时修改 txt 文件后通过 `ConfigSyncModule` 整表推送机制同步给客户端。

**⚠️ 服务端接入要求**：服务端配置加载必须使用 `READ_SYNC_FILE` 宏（而非 `READ_FILE` 宏），才能将表注册进 `ConfigSyncModule::mFileMap`。参考 active_fund_main.xlsx 的说明。

**客户端消费方式**：同 active_fund_main.xlsx，`output_code_csharp.bat` 生成 `TDActivityMixGrowthfundReward.cs`（数据行类）和 `TDActivityMixGrowthfundRewardTable.cs`（表管理类）后接入 `DynamicConfigModule` 整表同步，`MixGrowthFundModule` 业务代码直接 `TDActivityMixGrowthfundRewardTable.GetDataList()` 读取本地已同步数据。

**outcode_config.json 配置建议**：需要配置。在 `need_copy` 和 `NeedParseDataMethod` 中都添加本表——判断依据是"动态配置 + 用于活动系统"。

**奖励串格式**:


**数据示例**:


**设计决策**:
- **RewardId**: 1-10 档位，固定顺序展示，不支持跳档
- **奖励串格式**: 沿用项目通用格式（itemId:count分号分隔）
- **Highlight**: 预留字段，用于客户端特殊展示需求（暂不使用）

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
- 保留字段（DisplayType, PeriodName, ReserveSec）可填 0 或空字符串

### 枚举值
- Direct 字段无硬编码枚举，策划自由填写
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

每个奖励档位需配置对应的目标：

| GoalId | GoalType | TargetValue | Description |
|--------|----------|-------------|-------------|
| 10001 | 1 | 20 | 达到20级 |
| 10002 | 1 | 25 | 达到25级 |
| ... | ... | ... | ... |

**说明**: GoalType 枚举值需与服务端  对齐（见 Open Questions）

---

## Open Questions

### Q1: ActivityGoalModule 的条件类型枚举值是什么？

**Answer**: 已查服务端代码确认（见 design/server.md Q1），`activity_goal.xlsx` 的 GoalType 列填以下数值：
- LEVEL → 1 (AM_TYPE_PLAYER_LEVEL)
- TOWER_FLOOR → 37 (AM_TYPE_PASS_TOWER_CHALLENGE)
- CUMULATIVE_LOGIN → 244 (AM_TYPE_ACC_LOGIN_DAY)
- QUEST → 8 (AM_TYPE_FINISH_TASK)
- POWER → 109 (AM_TYPE_PLAYER_CP)

### Q2: 奖励高亮字段的 JSON 格式是什么？
FreeHighlight 和 PayHighlight 是配置的特效ID, 用来当前奖励 可以领取的时候 给icon上挂特效

### Q3: 是否需要配置领取期延长天数字段？
不处理

### Q4: Direct 字段是否需要多语言支持？
用语言包就行了

## 实现检查清单

- [ ] 创建 active_fund_main.xlsx 并填充数据
- [ ] 创建 activity_mix_growthfund_reward.xlsx 并填充数据
- [ ] 在 recharge.xlsx 中新增 RechargeType=5 商品
- [ ] 在 activity_goal.xlsx 中配置每档目标
- [ ] 运行 TableTool.exe 导出 .txt 文件
- [ ] 客户端验证自动生成的 TDActiveFundMain.cs
- [ ] 服务端验证配置加载（查看日志）
- [ ] 测试数据完整性（10档奖励是否都有）

---

## 参考资料

- 服务端配置结构体: 
- 配置Schema: 
- 客户端设计: 
- 服务端设计: 
- 策划提案: 
