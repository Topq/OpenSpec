# design-client.md 生成规则

> **说明**: 本文档定义 design-client.md 的生成规则。
> 该文档从 proposal.md 和 specs/*.md 生成，用于客户端工程师技术评审。
> 
> **重要**: design-client.md 是技术评审的必要输入，用于对齐协议、Record表、UI设计。

---

## 一、design-client.md 规则

### 1.1 文档结构

```markdown
# Design: {功能名称} - Client

## 背景与目标
[从 proposal.md 的 Why 部分继承]

## 模块定义

**模块名称**: {XXX}Module
**文件路径**: `Assets/Script/LogicModule/{XXX}Module/`

**文件组织**:
- {XXX}Module.cs          // 主模块，实现 ILogicModule
- {XXX}Define.cs          // 常量、枚举、适配器定义
- {XXX}Module_Record.cs   // Record 操作（可选）
- {XXX}Module_Net.cs      // 协议收发（可选）
- {XXX}Module_RedPoint.cs // 红点逻辑（可选）

**UI文件组织** (如果有UI):
- `Assets/Script/UIScript/{XXX}Panel/`
  - {XXX}Panel.cs              // 主面板
  - {XXX}Panel_PanelTab.cs     // 标签页逻辑（如果有多标签页）
  - {XXX}{TabName}Page.cs      // 各个标签页页面

**依赖模块**:
- XXXModule (说明依赖原因)
- YYYModule (说明依赖原因)

**功能ID分配**:
```csharp
// FuncDefine.cs
FUNC_{MODULE_NAME} = {主ID},              // {中文名} - 主入口
FUNC_{MODULE_NAME}_{TAB1} = {子ID1},      // {中文名} - {标签页1}（如有）
FUNC_{MODULE_NAME}_{TAB2} = {子ID2},      // {中文名} - {标签页2}（如有）
```

**UI ID分配**:
```csharp
// UIDefine.cs
{ModuleName}Panel,              // {中文名} - 主界面
{ModuleName}{Tab1}Page,         // {中文名} - {标签页1}（如有）
```

**红点ID分配**:
```csharp
// RedPointDefine.cs
{ModuleName} = {主ID * 100},              // {中文名} - 主入口
{ModuleName}{Tab1} = {子ID1 * 100},       // {中文名} - {标签页1}（如有）
```

## Record 表定义

> **重要**: Record 表定义必须与服务器端完全对齐（表名、列顺序、数据类型）

### {表名1}

**表名常量**: `{TABLE_NAME_REC}`
**用途**: [说明这个表存储什么数据]
**数据持久化**: 是/否
**同步时机**: 登录时 / 变化时推送

**列定义**:
```csharp
// {XXX}Define.cs
public const string {TABLE_NAME_REC} = "table_name_rec";

public enum {TableName}Col
{
    ColumnName1 = 0,  // int    - 字段说明
    ColumnName2 = 1,  // string - 字段说明
    ColumnName3 = 2,  // int64  - 字段说明
}
```

**数据来源**: 
- 登录时服务器推送完整数据
- 协议 S2C_XXX_YYY 增量更新

**访问方式说明**：
- 通过 `m_Kernel.FindRecord(player, {TABLE_NAME_REC})` 获取表实例
- 通过 `rec.QueryInt(row, (int){TableName}Col.ColumnName)` 查询字段值
- 通过 `rec.FindInt((int){TableName}Col.ColumnName, value)` 查找行索引

**设计决策**：
- 为什么：使用 Record 系统而非自定义缓存，保证与服务器数据一致性
- 同步策略：登录全量 + 变化增量，减少网络传输

### {表名2}
[重复上述结构]

## 配置表数据获取决策

> **关键判断**: 设计客户端如何获取配置表数据时，先区分数据性质，再选择对应的获取方式。

### 数据性质分类

1. **运行时状态数据**（每个玩家/活动实例不同）
   - 特征：玩家专属、实例专属、会变化
   - 示例：玩家当前等级、某活动的已领取状态、某任务的进度
   - 获取方式：走协议推送（如 `S2C_XXX_Info` 的 specialInfo 段、`ACTIVITY_GOAL_REC` 等 Record 表）
   - **不需要**额外配置表接入工作

2. **静态配置数据**（所有玩家一致）
   - 特征：全局一致、不常变化、客户端业务逻辑需要主动查表
   - 示例：活动基础信息（名称/时间）、奖励配置、条件类型枚举
   - 分两种情况：
     - **2a. 协议已下发**：服务端通过协议（如470协议 specialInfo）推送了这部分配置数据 → 不需要额外加载配置表
     - **2b. 协议未下发且客户端需要查**：需要走 `DynamicConfigModule` 动态配置表同步流程（见下）

### 何时需要 DynamicConfigModule 接入

**满足以下任一条件时**，必须走动态配置表同步流程：

- 客户端需要在**协议下发前**就访问配置（例如：福利中心列表要在打开活动 Page 前就展示活动名称）
- 客户端需要根据配置做**本地业务逻辑判断**（例如：某跳转链接的条件判断、客户端预校验）
- 配置数据量大，协议推送不经济（例如：大型配置表、多语言文本）

**不需要时**：

- 所有配置数据都通过协议实时下发（如活动信息协议的 specialInfo 段已包含所有展示字段）
- 客户端只负责展示协议数据，不做本地查表判断

### DynamicConfigModule 接入标准步骤

> **前置说明**：`DynamicConfigModule` 是客户端从服务器动态同步配置表的机制，支持版本管理和增量更新。注册后，客户端可以通过强类型 `TDXXXTable.GetData(id)` 访问配置数据。

#### 步骤概览

1. **修改 `outcode_config.json`**：将表名加入 `need_copy`（生成 C# 结构体）和 `NeedParseDataMethod`（支持动态推送）
2. **重新生成代码**：执行 `output_code_csharp.bat`，生成 `TDXxxTable.cs`
3. **实现扩展类**：创建 `XxxTableExtend.cs`，实现 `InsertDynamicData`/`ParseComplete`/`ClearDynamicData` 三个方法
4. **注册到模块**：在 `DynamicConfigModule_Process.cs` 的 `InitProcessDic()` 里调用 `RegisterTable(...)`
5. **使用**：通过 `m_TableCfgMod.XxxTable.GetData(id)` 强类型访问

#### 关键文件路径

- **配置文件**：`D:\se\develop\public\table_config\outcode_config.json`（⚠️ 不是 `client/tools/table/table_config/` 那个空目录，也不是 `xlsxconvert/source/golang/xlsx2csv/` 工具源码模板）
- **生成工具**：`D:\se\develop\client\tools\table\output_code_csharp.bat`
- **注册位置**：`Assets/Script/LogicModule/DynamicConfigModule/DynamicConfigModule_Process.cs`
- **扩展类目录**：`Assets/Script/Table/Data/`

#### `need_copy` vs `NeedParseDataMethod` 的区别

- **只在 `need_copy`**：生成 C# 结构体，但只能用于客户端本地打包的配置表（`Resources/Data/` 下的 CSV）
- **同时在 `NeedParseDataMethod`**：额外生成 `ParseData(IVarList)` 方法，支持服务器动态推送数据

#### 扩展类必须实现的三个方法

```csharp
public partial class TDXxxTable
{
    // 1. 服务器每推送一行数据调用一次
    public void InsertDynamicData(IVarList args)
    {
        TDXxx data = new TDXxx();
        data.ParseData(args); // 调用自动生成的方法
        Insert(data.PrimaryKey, data);
    }

    // 2. 整张表推送完成后调用（可选：构建业务缓存索引）
    public void ParseComplete() { }

    // 3. 清空内存数据（重新加载时调用）
    public void ClearDynamicData()
    {
        Clear();
    }
}
```

#### 注意事项

- `output_code_csharp.bat` 是人工本地工具链操作，tasks 阶段需列为人工执行步骤
- 使用强类型 `TDXxxTable.GetData(id)`，不要用弱类型 `DynamicConfigModule.GetData("table_name")`（那是给 Lua 用的）
- 若表有组合主键，需要手动构造 key（例如 `(long)id1 << 32 | (uint)id2`），具体编码方式需与服务端对齐

### 设计文档中的写法

**当选择"不加载配置表"时**：
```markdown
### 客户端侧流程（当前方案假设）

**当前设计假设**：客户端不主动加载 XXX 配置表，所有展示数据来自服务端协议 YYY 的 specialInfo 段实时下发。

**假设成立的前提**：
- UI 逻辑都在收到协议后才触发
- 不需要在协议下发前预览信息
- 不需要客户端本地根据配置表做业务判断

**若假设不成立**：需要走 `DynamicConfigModule` 动态配置表同步流程，具体步骤见本文档"配置表数据获取决策"章节或 `tmp/design-client-implementation-details.md`。
```

**当选择"需要加载配置表"时**：
```markdown
### 客户端侧流程

客户端通过 `DynamicConfigModule` 同步以下配置表：
- `xxx_main.txt` → `TDXxxMainTable`
- `xxx_reward.txt` → `TDXxxRewardTable`

**接入步骤**（tasks 阶段执行）：
1. 修改 `D:\se\develop\public\table_config\outcode_config.json`，将 `xxx_main`/`xxx_reward` 加入 `need_copy` 和 `NeedParseDataMethod`
2. 执行 `output_code_csharp.bat` 重新生成代码
3. 实现 `TDXxxMainTableExtend.cs`/`TDXxxRewardTableExtend.cs`
4. 在 `DynamicConfigModule_Process.cs` 注册

**使用方式**：
```csharp
TDXxxMain cfg = m_TableCfgMod.XxxMainTable.GetData(activityId);
```
```

## UI 设计

### 页面结构

**Panel 路径**: `UI/Welfare/{XXX}Panel`

**主要组件**:
- {组件1}: 用途说明（使用 `data-lr-component="list.single-scroll"`）
- {组件2}: 用途说明
- {弹窗1}: 触发时机

**数据绑定**:
- {UI元素} ← Record 表 {表名}.{列名}
- {列表} ← Record 表 {表名} 全部行

### 状态机

**页面状态**:
```
未开启 → 已开启未购买 → 已购买 → 活动结束
```

**按钮状态**:
- 购买按钮: 未开启（隐藏）/ 可购买（高亮）/ 已购买（置灰）
- 领取按钮: 未达成（置灰）/ 可领取（高亮）/ 已领取（置灰）

### 交互流程

#### {功能1 - 例如购买}
```
用户点击购买按钮
  ↓
弹出二次确认弹窗（显示价格、回报率、截止日期）
  ↓
用户确认
  ↓
发送协议 C2S_XXX_Purchase(参数)
  ↓
等待响应（按钮置灰、显示 loading）
  ↓
收到 S2C_XXX_Purchase_Result
  ├─ 成功: 更新 Record → 刷新 UI → 显示成功弹窗
  └─ 失败: 显示错误提示（根据错误码）
```

#### {功能2 - 例如领取}
[重复上述结构]

## 协议定义

> **协议号生成机制**: 
> - 服务器端在 `ServerCustomDefine.h` 和 `ClientCustomDefine.h` 中自动判断并分配未使用的协议号
> - 客户端依据服务器定义，更新 `public/proto` 后通过 `convert_proto_csharp.bat` 自动生成
> - **design 文档中协议号写 `{待自动分配}`，不需要手动指定具体数值**

### C2S 协议 (客户端 → 服务器)

#### C2S_XXX_Purchase - 购买请求
```csharp
协议号: {待自动分配} - CLIENT_CUSTOMMSG_{XXX}_PURCHASE
参数 (IVarList):
  [0] int activityID    // 活动ID
  [1] int rechargeID    // 充值档位ID

触发时机: 用户点击购买按钮并确认后
处理函数: SendPurchaseRequest()
```

#### C2S_XXX_Claim - 领取请求
```csharp
协议号: {待自动分配} - CLIENT_CUSTOMMSG_{XXX}_CLAIM
参数 (IVarList):
  [0] int activityID    // 活动ID
  [1] int rewardID      // 奖励ID
  [2] int claimType     // 领取类型：1=单个, 2=批量

触发时机: 用户点击领取按钮
处理函数: SendClaimRequest()
```

### S2C 协议 (服务器 → 客户端)

#### S2C_XXX_Purchase_Result - 购买结果
```csharp
协议号: {待自动分配} - SERVER_CUSTOMMSG_{XXX}_PURCHASE_RESULT
参数 (IVarList):
  [0] int result        // 结果码: 0=成功, 其他=错误码

接收回调: OnPurchaseResult()
处理逻辑: 更新 Record → 刷新 UI → 显示结果弹窗
```

#### S2C_XXX_Claim_Result - 领取结果
```csharp
协议号: {待自动分配} - SERVER_CUSTOMMSG_{XXX}_CLAIM_RESULT
参数 (IVarList):
  [0] int result        // 结果码
  [1] string rewards    // 奖励列表（格式: "itemID:count;itemID:count"）

接收回调: OnClaimResult()
处理逻辑: 更新 Record → 刷新 UI → 播放奖励特效
```

#### S2C_XXX_ConditionUpdate - 条件变化推送
```csharp
协议号: {待自动分配} - SERVER_CUSTOMMSG_{XXX}_CONDITION_UPDATE
参数 (IVarList):
  [0] int activityID    // 活动ID
  [1] int rewardID      // 奖励ID
  [2] int conditionMet  // 是否达成: 0=否, 1=是

接收回调: OnConditionUpdate()
处理逻辑: 更新 Record → 刷新 UI → 刷新红点
```

### 错误码

> **说明**: 客户端错误码主要用于表现层提示，需与服务器错误码数值对齐

**错误码定义**：
| 错误码 | 含义 | 提示文案 |
|--------|------|----------|
| 0 | 成功 | - |
| 1001 | 活动未开启 | "活动未开启" |
| 1002 | 已购买 | "您已购买过该基金" |
| 1003 | 条件未达成 | "条件未达成，无法领取" |
| 1004 | 已领取 | "奖励已领取" |
| 1005 | 配置错误 | "系统异常，请联系客服" |

**设计决策**：
- 为什么：错误码与服务器对齐，确保错误提示一致性
- 实现方式：使用枚举定义错误码，使用字典映射到提示文案
- 备选方案：直接在代码中硬编码提示文案
- 为什么不选：不利于多语言和文案统一管理

## 红点规则

**触发条件**:
- {条件1}: 例如有可领取的免费奖励
- {条件2}: 例如有可领取的投资奖励（已购买）

**清除时机**:
- 打开界面
- 领取完所有可领奖励

**红点层级**:
```
福利中心主入口
  └─ 基金Tab
      └─ 奖励行
```

## 关键功能说明

> **说明**: 本节说明关键功能的职责和设计决策，不包含具体实现代码（实现代码在 tasks 环节）

### 模块初始化

**职责**：
- 获取依赖模块（RedPointModule、RechargeModule 等）
- 注册事件监听（OnMainPlayerReady 等）
- 注册协议回调（接收服务器推送）
- 注册红点规则（绑定父子红点、注册计算函数）

**设计决策**：
- 为什么：模块启动时必须完成依赖注入和事件注册，确保功能正常运行
- 备选方案：延迟注册（首次使用时注册）
- 为什么不选：延迟注册可能导致首次交互卡顿，且增加状态管理复杂度

### 红点管理

**职责**：
- 绑定红点层级关系（福利中心 → 基金Tab → 奖励行）
- 计算红点状态（检查是否有可领取奖励）
- 监听数据变化（条件达成、领取成功时刷新红点）

**设计决策**：
- 为什么：使用三级红点系统，符合现有红点架构
- 备选方案：自定义红点系统
- 为什么不选：增加维护成本，且与其他模块不一致

### 数据查询

**职责**：
- 检查购买状态（查询 GROWTH_FUND_OPEN_REC）
- 检查领取状态（查询 MIX_GROWTH_FUND_REWARD_REC）
- 检查条件达成（查询 ACTIVITY_GOAL_REC）

**设计决策**：
- 为什么：直接查询 Record 表，无需缓存
- 备选方案：在模块内缓存查询结果
- 为什么不选：Record 表已在内存，缓存带来同步复杂度

### 协议发送

**职责**：
- 发送购买请求（C2S_XXX_PURCHASE）
- 发送领取请求（C2S_XXX_CLAIM）
- 构造协议参数（使用 IVarList）

**设计决策**：
- 为什么：使用 IVarList 构造参数，符合现有协议框架
- 参数顺序：按协议定义顺序添加（activityID, rechargeID 等）

### 协议接收

**职责**：
- 接收购买结果（S2C_XXX_PURCHASE_RESULT）
- 接收领取结果（S2C_XXX_CLAIM_RESULT）
- 接收条件更新（S2C_XXX_CONDITION_UPDATE）
- 根据结果更新 Record、刷新 UI、播放特效

**设计决策**：
- 为什么：协议回调中先更新数据再刷新UI，确保UI显示最新状态
- 错误处理：根据错误码显示对应提示文案

### UI 方法约定

**重要约定**（参考现有 Panel 实现）：
- `OnCellUpdated(Transform root, int index)` - 列表单元格更新（注意第一个参数是 Transform）
- `OnTabPreselect(int index)` - Tab 预选检查（使用 IsOpenOnlyCheckCondition）
- `OnTabSelect(int index)` - Tab 选中处理
- `OnRedPointWatcher(int index)` - 红点监听（返回 void）
- `AttachPage()` - 附加子页面（注意参数顺序）
- `DettachPage()` - 移除子页面（注意拼写是两个 t）

**设计决策**：
- 为什么：遵循现有 Panel 基类约定，确保与框架兼容
- 备选方案：自定义方法签名
- 为什么不选：违反框架约定，可能导致运行时错误

## 异常处理

### 网络异常
- **请求超时**: 显示"网络超时，请重试"，按钮恢复可点击
- **断线重连**: 重新拉取 Record 数据，刷新 UI

### 配置缺失
- **表数据不存在**: 记录错误日志，界面显示"配置错误"
- **字段缺失**: 使用默认值，记录警告日志

### 状态异常
- **已购买但未激活**: 提示"购买失败，请联系客服"
- **已领取但记录缺失**: 以服务器数据为准，刷新 Record

## Open Questions

> **Open Questions 明确规则**: 
> 
> **必须出现的问题类型**:
> 1. **协议字段未确定**: 需要与服务器对齐但尚未确定的字段定义
> 2. **UI交互细节**: 需要策划或产品确认的交互细节（动画、弹窗、提示）
> 3. **边界条件**: 需要明确的边界情况处理（网络异常、状态冲突）
> 4. **配置表依赖**: 需要策划配置但字段或取值范围尚未确定
> 5. **性能影响**: 可能影响性能的设计需要确认（频繁推送、大量计算）
> 6. **跨模块依赖**: 需要其他模块提供支持但尚未确认的功能
> 
> **不应出现的问题**:
> - 已在 proposal 或 specs 中明确定义的内容
> - 纯技术实现细节（这应该在 design 中直接决定）
> - 过于宽泛的问题（"这个功能怎么做"）

### 协议相关

1. **C2S_XXX_Claim 是否需要 `claimAll` 字段？**
   - 当前设计: 通过 `claimType` 参数区分单个/批量
   - 问题: 批量领取时是否需要返回每个奖励的详细信息？
   - 影响: 协议字段定义、服务器处理逻辑

2. **S2C_XXX_ConditionUpdate 推送频率？**
   - 当前设计: 条件达成时立即推送
   - 问题: 等级变化等高频事件是否需要延迟合并推送（避免频繁刷新UI）？
   - 影响: 性能、用户体验

### UI交互相关

3. **购买确认弹窗是否需要显示"不可退款"提示？**
   - 当前设计: 弹窗显示价格、回报率、首档立得、截止日期
   - 问题: 是否需要增加"购买后不可退款"的明确提示？
   - 影响: UI文案、合规风险

4. **批量领取动画处理？**
   - 当前设计: 一键领取所有可领奖励
   - 问题: 一次领取10+个奖励时，是播放合并特效还是逐个播放？
   - 影响: 用户体验、动画资源

### 配置表相关

5. **条件类型枚举是否需要扩展？**
   - 当前定义: 等级、爬塔层数、累计登录
   - 问题: 是否需要支持"累计充值"、"完成指定任务"等条件类型？
   - 影响: 配置表字段、服务器判定逻辑

### 性能相关

6. **红点刷新频率控制？**
   - 当前设计: 条件达成时立即刷新红点
   - 问题: 是否需要增加刷新间隔（避免1秒内多次刷新）？
   - 影响: 性能、红点系统设计

### 跨模块依赖

7. **充值系统回调时机？**
   - 当前设计: 充值成功后调用 OnGrowthFundDispose
   - 问题: 如果充值系统延迟回调（等待支付平台确认），基金激活是否需要额外状态？
   - 影响: 购买流程、状态管理
```
