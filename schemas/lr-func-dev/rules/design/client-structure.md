# design-client.md 生成规则（精简版 v2）

> **SE 适配说明**：GodFort/神域防线及其返工频次是 DL 来源案例，不是 SE 当前文件或接口的证据。实际审查先读 SE `config.yaml` 路由的 ai-core，再用 SE CodeGraph/源码复验；来源案例和缺失的历史附件仅作说明，不作为必读依赖或通过依据。


> **说明**: 本文档定义 design-client.md 的生成规则。
> 该文档从 proposal.md 和 specs/*.md 生成，用于客户端工程师技术评审。
> 
> **设计哲学**: 规则文件只包含"无法从代码推理的知识"，所有代码模板通过 CodeGraph 查询获取。

---

## 零、Pre-flight Check（代码库调查）

在生成 design-client.md 之前，**必须先执行代码库调查**，避免基于错误假设设计。

### 调查清单

使用 CodeGraph 查询以下内容（优先），或使用 Grep/Glob 作为备选：

| 调查项 | CodeGraph 查询示例 | 目的 |
|-------|------------------|------|
| **功能是否已实现** | `<功能名> Module Panel` | 避免重复设计 |
| **是否需接入 BA 框架** | `BusinessActivityModule BusinessActivityDefine <功能关键词>` | 判断是否复用活动框架 |
| **UI 组件是否存在** | `<功能名>Panel AbstractPanel` | 判断是新建还是修改 |

**项目路径**: `../develop/client/project`

### 调查结果的文档体现

调查结果必须体现在 design-client.md 的以下位置：

1. **`## ⚠️ 当前状态` 章节**（若发现与 proposal 假设冲突）
   - 说明现有实现概况
   - 说明本次设计调整范围

2. **`## 背景与目标`**（简要说明是新增还是修改）

3. **`## 模块定义`**（使用实际路径，不要猜测）

---

## 一、架构决策规则

以下规则定义了**无法从代码推理的架构决策标准**。

### 1.1 BusinessActivityModule 接入判断

**判断标准**（阻断性）：

```
IF `BusinessActivityDefine.cs` 中存在相关功能 ID 枚举值
THEN 必须接入 BusinessActivityModule
     - 复用 Panel 管理
     - 复用红点系统
     - 复用时间配置
     禁止设计独立的活动体系
ELSE 可设计独立模块
```

**检查方式**：
```
CodeGraph 查询：BusinessActivityModule BusinessActivityDefine <功能关键词>
若查询结果包含功能 ID → 必须接入
```

**文档体现**（在 design-client.md 的"依赖模块"章节）：
```markdown
**依赖模块**:
- BusinessActivityModule（必须接入）- 活动框架，提供 Panel 管理、红点注册、时间配置
```

---

### 1.2 Record 驱动 vs 传统协议模式选择

**选择标准**（架构决策）：

| 条件 | 选择模式 | 协议定义 |
|-----|---------|---------|
| 数据需要持久化（如购买记录、领取状态） | **Record 驱动** | 只需 C2S，无 S2C |
| 数据需要在多个 UI 界面共享 | **Record 驱动** | 只需 C2S，无 S2C |
| 一次性操作，需要立即反馈（如领取奖励显示特效） | **传统 C2S/S2C** | 需要 C2S + S2C |
| 需要返回临时数据（如奖励详情） | **传统 C2S/S2C** | 需要 C2S + S2C |

**Record 驱动模式工作流程**：
```
客户端发送 C2S 请求
  ↓
服务器更新 Record 表
  ↓
Record 自动同步到客户端（框架机制）
  ↓
UI 监听 Record 变化，自动刷新
```

**文档体现**（在 design-client.md 的"协议定义"章节顶部）：
```markdown
**返回机制**：无 S2C 协议，服务器直接更新 `XXX_REC`，客户端通过 Record 监听刷新 UI
```
或
```markdown
### S2C 协议
（定义返回协议）
```

---

### 1.2a 派生状态字段的赋值时机（强制）

若客户端状态缓存结构体中的字段不是 Record/协议原始字段的直接映射（如需要跨模块查询、
或由多个来源组合得到），设计文档必须明确指出：
1. 该字段在哪个回调函数中被赋值（如 `ParseQueryInfo`、`OnXxxRecChanged`）
2. 赋值的数据来源（如"来自 ActivityGoalModule.QueryGoalProgress 返回的进度数据"）

**检查方法**：对比"客户端状态缓存"章节声明的字段列表 与 "交互流程"/"协议解析"章节提到的
赋值语句，若某字段只在结构体定义处出现、在流程描述中找不到对应的赋值来源，视为设计缺口，
必须补充说明后才能合并。

**多实例场景的状态遍历（强制）**：若同一个 BusinessActivityType 允许同时存在多个活动实例
（activityId 不同），设计文档中涉及遍历状态缓存字典（如 `m_RewardStatuses`）的判断逻辑
（红点计算、进度汇总等）必须在伪代码中显式包含 activityId 过滤条件，不能假设"字典里只有
当前活动的数据"。

---

### 1.3 玩家属性监听架构规则

**适用场景**：功能需要监听玩家属性变化（如婚姻状态、好友申请、公会邀请、邮件通知等）

#### 属性分类原则

根据业务语义，玩家属性分为三类：

| 属性类型 | 业务特征 | 处理方式 | 示例 |
|---------|---------|---------|------|
| **主动弹窗类** | 收到请求、通知，需要用户立即响应 | **独立回调 + 强制弹窗** | `WeddingReceiveProposalRoleId`, `FriendApplyList`, `GuildInviteRoleId`, `MailNewId` |
| **状态变更类** | 玩家核心状态变化，影响多个界面 | **独立回调 + 事件广播** | `WeddingState`, `GuildId`, `TeamLeaderId`, `WeddingRoleId` |
| **数据更新类** | 数值变化，只需刷新已打开界面 | **独立回调 + 按需刷新** | `WeddingAffectionPoints`, `GuildContribution`, `FriendIntimacy`, `MailUnreadCount` |

#### 强制性架构约束（阻断性）

```
❌ 禁止：所有属性共用一个回调 + 全量刷新
   问题：
   - 性能差：多个属性同时变化时重复刷新
   - 逻辑混乱：无法区分业务场景
   - 漏掉主动弹窗：回调中只刷新界面，不弹窗

✅ 必须：每个属性独立回调，或统一回调 + switch-case 分发
   要求：
   - 主动弹窗类属性 → 必须在回调中立即弹窗
   - 状态变更类属性 → 必须广播事件通知所有相关界面
   - 数据更新类属性 → 只刷新已打开的界面（不主动弹窗）
```

#### 代码模式（推荐）

**方案 A：独立回调（性能最优，语义最清晰）**

```csharp
public override void OnInit() {
    // 主动弹窗类属性（收到请求立即响应）
    m_Player.AddPropertyCallback("XXXReceiveRequestRoleId", OnReceiveRequest);
    m_Player.AddPropertyCallback("XXXApplyRoleId", OnReceiveApply);
    
    // 状态变更类属性（影响多个界面）
    m_Player.AddPropertyCallback("XXXState", OnStateChanged);
    m_Player.AddPropertyCallback("XXXRoleId", OnPartnerChanged);
    
    // 数据更新类属性（实时刷新）
    m_Player.AddPropertyCallback("XXXPoints", OnPointsChanged);
}

// 主动弹窗类回调
void OnReceiveRequest(ObjectID sender, int propertyIndex) {
    long requesterId = m_Player.GetInt64(propertyIndex);
    if (requesterId > 0) {
        // 强制弹出确认界面
        UIModule.S.OpenPanel(UIID.XXXRequestPanel, requesterId);
    } else {
        // 请求槽清空（超时/取消/对方离线）
        // 关闭等待界面或显示提示
    }
}

// 状态变更类回调
void OnStateChanged(ObjectID sender, int propertyIndex) {
    // 广播状态变更事件，所有相关界面监听并刷新
    m_Kernel.CommandDynamic(CommandID.OnXXXStateChanged);
}

// 数据更新类回调
void OnPointsChanged(ObjectID sender, int propertyIndex) {
    // 只刷新已打开的界面
    m_Kernel.CommandDynamic(CommandID.OnXXXPointsChanged);
}
```

**方案 B：统一回调 + switch 分发（次优，但可接受）**

```csharp
void OnPropertyChanged(ObjectID sender, int propertyIndex) {
    string propertyName = m_Player.GetPropertyName(propertyIndex);
    
    switch (propertyName) {
        case "XXXReceiveRequestRoleId":
            HandleReceiveRequest();
            break;
        case "XXXState":
            HandleStateChanged();
            break;
        case "XXXPoints":
            HandlePointsChanged();
            break;
    }
}
```

#### 文档体现（强制要求）

在 design-client.md 的"数据流与刷新机制"章节，必须明确：

1. **列出所有监听的属性**（按类型分组：主动弹窗/状态变更/数据更新）
2. **每个属性的回调处理逻辑**（弹窗/广播/刷新）
3. **禁止使用"全量刷新"的模糊描述**

**示例**：

```markdown
### 属性监听

#### 主动弹窗类
- `WeddingReceiveProposalRoleId` → `OnReceiveProposal`
  - 触发时机：收到求婚请求（值 > 0）
  - 处理逻辑：强制弹出 `MarriageProposeReceivePanel`，传入求婚者 RoleId
  - 清空时机：求婚被接受/拒绝/超时（值 = 0）

- `WeddingDivorceApplyRoleId` → `OnReceiveDivorceRequest`
  - 触发时机：收到离婚申请（值 > 0）
  - 处理逻辑：强制弹出 `MarriageDivorceConfirmPanel`

#### 状态变更类
- `WeddingState` → `OnMarriageStateChanged`
  - 触发时机：订婚/结婚/离婚
  - 处理逻辑：广播 `CommandID.OnMarriageStateChanged`，相关界面监听并刷新

- `WeddingRoleId` → `OnSpouseChanged`
  - 触发时机：结婚/离婚（配偶 ID 变化）
  - 处理逻辑：刷新主界面页签（单身/已婚），刷新配偶信息

#### 数据更新类
- `WeddingAffectionPoints` → `OnAffectionChanged`
  - 触发时机：亲密度变化
  - 处理逻辑：若 `MarriageMarriedPage` 已打开，刷新亲密度进度条
```

#### 代码模板获取

```
CodeGraph 查询：AddPropertyCallback PropertyCallback Module
CodeGraph 查询：GetPropertyName Player 属性
```

---

### 1.4 协议解析起始索引规范（阻断性）

**原始协议**（AddCustomHook 注册）：从索引 0 开始

```csharp
// ✅ 正确
void OnRecvXXXInfo(IVarList args) {
    int index = 0;
    int param1 = args.GetInt32(index++);
}

// ❌ 错误：跳过第一个参数
void OnRecvXXXInfo(IVarList args) {
    int index = 1;  // 错误
}
```

**原因**：客户端框架已过滤协议号，业务参数从索引 0 开始

---

**BusinessActivity 协议**（ParamArgs 继承）：从 CustomStart（索引 13）开始

```csharp
// ✅ 正确
public override void ParamArgs(IVarList args) {
    int index = (int)BAActivityInfoIndex.CustomStart;  // 索引 13
    int param1 = args.GetInt32(index++);
}

// ❌ 错误：会把 ActivityID 误读成业务参数
public override void ParamArgs(IVarList args) {
    int index = 0;  // 错误
}
```

**原因**：框架前 13 个字段（ActivityID 到 SeasonId）是固定字段
**参考**：`TrialModule_Config.cs:76`

---

### 1.5 红点系统注册方式

**注册方式选择**（框架约定）：

| 场景 | 注册方法 | 回调签名 |
|-----|---------|---------|
| 活动菜单/入口红点（接入 BusinessActivityModule） | `BusinessActivityModule.RegisterRedPointCallback` | `bool callback(int activityId)` |
| 普通系统功能红点（非活动，或活动内自建红点节点） | `RedPointModule.Register` | `bool callback(RedPointType type)` |

**选择依据**：`BusinessActivityModule_RedPoint.cs` **只服务活动红点**——红点挂在哪个菜单由活动的 `Location` 决定，底层按 `funcId * 100` 注册到 `RedPointModule`。非活动的系统功能（主界面、养成、社交等）不要走 BA 回调，直接用 `RedPointModule`。

**注册时机**：模块初始化时（`OnInit()` 方法）；父子红点聚合用 `RedPointModule.Bind(parent, child)`，数据变化自动失效用 `SetHookRecord` / `SetHookProp`。

**红点刷新**：
- 活动红点：`m_BizActivityModule.DirtyRedPoint(activityId, activityType)`
- 系统功能红点：`m_RedPointModule.SetDirty(redPointType)`

**代码模板获取**：
```
CodeGraph 查询：RegisterRedPointCallback BusinessActivityModule
CodeGraph 查询：RedPointModule Register 红点注册
```

---

## 二、框架特殊约定

以下约定是**框架的特殊限制**，AI 无法从代码推理，必须明确告知。

### 2.1 UI 方法签名约定

**重要约定**（框架 API 限制）：

| 方法名 | 签名 | 特别注意 |
|-------|------|---------|
| `OnCellUpdated` | `(Transform root, int index)` | ⚠️ 第一个参数是 `Transform`，不是 `GameObject` |
| `AttachPage` | `(AbstractPage page, Transform parent)` | ⚠️ 参数顺序不能颠倒 |
| `DettachPage` | `(AbstractPage page)` | ⚠️ 拼写是两个 `t`（历史遗留） |

**错误示例**（编译失败）：
```csharp
void OnCellUpdated(GameObject root, int index)  // ❌ 第一个参数类型错误
void DettachPage(AbstractPage page)            // ❌ 拼写错误，框架找不到回调
```

**代码模板获取**：
```
CodeGraph 查询：OnCellUpdated AbstractPanel
CodeGraph 查询：AttachPage DettachPage Panel
```

---

### 2.3 UI 文件组织规范

**规则**：同一功能模块的所有 UI 组件（Page/Panel/Cell）必须在同一文件夹下。

**结构**：
```
UISript/<父级>/<功能模块>/
├── <功能>Page.cs
├── <功能>Panel.cs
└── <功能>Cell.cs
```

**禁止**：按 Panel 类型分散（如 MonthCardPage/、MonthCardPanel/、MonthCardGiftPanel/）

**原因**：功能内聚，删除功能时只需删除一个文件夹。

---

#### 2.3.1 配置表接入（DynamicConfigModule）

**接入判断**（架构决策）：

```
IF 满足以下任一条件
   - 客户端需要在协议下发前访问配置
   - 客户端需要根据配置做本地业务判断
   - 配置数据量大，协议推送不经济
THEN 必须走 DynamicConfigModule 同步流程
ELSE 协议实时下发即可
```

**接入步骤**（先确认使用 SE 数据库配置同步还是旧活动文件拉取链）：
1. 按 `schemas/lr-func-dev/rules/common/se-config-generation.md` 判断并修改 `../develop/client/tools/table/table_config/outcode_config.json` 的 `need_copy` 和 SE 专有 `NeedParseDataMethod`
2. 执行 `output_code_csharp.bat` 重新生成代码
3. 验证工具生成的 `TDXxxTableExtend.cs` 动态方法（`InsertDynamicData`, `ParseComplete`, `ClearDynamicData`），不手写替代生成产物
4. 在 `DynamicConfigModule_Process.cs::InitProcessDic()` 中调用 `RegisterTable(...)`（表级注册，让 `DynamicConfigModule` 认得这张表的强类型解析方法）
5. **仅旧活动文件拉取链要求活动级注册**：业务 Module 实现 `IConfigSyncMethod`，并在 `OnInit()` 中调用 `m_DynamicConfigModule.RegisterSyncMethod(this)`，声明该活动按何种时机拉取哪些表。
   - `fileNameList`：活动面板打开时（`BusinessActivityModule.RequestActivityInfo` → `DynamicConfigModule.StartLoadFile`）才拉取的表
   - `preFileNameList`：活动面板打开前就要提前拉取的表（如红点判断依赖的表）；两个属性均为 `string[]`，按实际加载时机填写，任一名单可为空，不强求两个都非空
   - 表名字符串必须与步骤 1 中 `outcode_config.json` 注册的表名完全一致（建议定义为 `{FuncName}Define.cs` 中的 `const string`，避免拼写不一致）

6. **数据库配置同步入口**：核查服务端登记/同步、首次主角 Ready 的数据库配置请求、版本计划与 `OnDataBaseConfigSync` 回包解析链；此入口不依赖 `IConfigSyncMethod`，不能因缺少活动级注册而判失败或补造活动类型。

**按实际入口验证注册完整性**：
- 旧活动文件拉取链缺步骤 5 → 目标活动无法按设计时机拉取配置；不能借其他活动已加载的数据掩盖遗漏。
- 两种入口都要验证步骤 4 的表级适配；缺适配可能使数据仅进入原始同步缓存，强类型表仍为空，不能只凭编译通过判定接入完成。

**验证方式（设计与实施阶段都必须检查）**：
- 先记录使用哪个同步入口及 SE 源码依据；数据库入口按步骤 6 验证，不强求活动级接口
- 旧活动文件拉取链：确认业务 Module 实现 `IConfigSyncMethod`，且 `OnInit()` 中存在 `m_DynamicConfigModule.RegisterSyncMethod(this)` 调用
- 参考正确实现：`ActivityDrawKOIModule`（`ActivityDrawKOIModule_Message.cs` 实现接口 + `ActivityDrawKOIModule.cs::OnInit()` 调用 `RegisterSyncMethod`）、`DevelopPlanModule`

**详细说明**：参考 `rules/tasks/client-implementation.md` §0.1 与 `rules/apply/config-execution.md` §4。

---

### 2.4 惯例落实五节（阻断性）

只写"模块、接口、流程"不足以约束实现。凡涉及**新增客户端 UI 或模块**的变更，design-client.md 必须包含以下五张表；缺任意一张视为设计未完成，不得进入合并门禁。

**依据**：神域防线（GodFort）初版 `r778930` 到终版的返工中，超过一半改动属于项目惯例对齐而非需求变化，全部落在下列五类。SE 的知识路由见 `../develop/client/project/docs/ai-core/knowledge/core-index.md`；以下五张表是本工作流交付要求，不假定 SE 有 DL 的阅读包。

#### 2.4.1 文件与职责清单（枚举，不写"等"）

| 文件 | 职责 | 拆分理由 |
|---|---|---|
| `XxxModule.cs` | public API + 生命周期 | 主文件 |
| `XxxModule_Net.cs` | 协议收发 | 网络回调独立 |
| `XxxPage.cs` | 页面交互与刷新 | 主文件 |
| ... | ... | ... |

要求：
- 每个计划新增/修改的 `.cs` 单独一行，禁止 `XxxModule*.cs`、"以及相关文件"这类写法；
- partial 拆分写理由（按职责还是按行数），不要求凑齐 `_State`/`_Net` 三件套；
- 这张清单同时作为 `reconcile` 文件结构对账的基线。

#### 2.4.2 事件订阅清单

| 事件 | 监听方 | 处理函数读取的数据 | 刷新范围 | 不监听其他事件的理由 |
|---|---|---|---|---|
| `OnBusinessActivityDirty` | `XxxPage` | 阶段集合 | 页签开放状态 | 不显示 BA 行值，无需 Changed/LateChanged |
| ... | ... | ... | ... | ... |

要求：每条订阅都要写出"处理函数实际消费的数据"；写不出来的订阅不应出现在设计里。默认只监听真正驱动本界面数据的事件。

#### 2.4.3 刷新粒度矩阵

| 变化源 | 刷新区域 | 不重建的部分 |
|---|---|---|
| 切换难度 | 阶段详情、难度选中态、按钮 | 阶段列表、队伍、背景 |
| 资金/冷却变化 | 可见格子 | 配置行、整页 |
| ... | ... | ... |

要求：禁止通篇只写 `RefreshState()`；必须说明哪些变化走全量刷新、哪些走局部刷新，并写明"重复选择同一项不刷新"。

#### 2.4.4 请求校验位置

| 协议/操作 | 本地校验内容 | 校验所在入口 | 服务器兜底的检查 |
|---|---|---|---|
| 领取奖励 | 是否已领取、是否达成 | `OnRewardCanGetBtn` | 领奖资格与幂等 |
| ... | ... | ... | ... |

要求：
- 按 SE 同类实现和实际调用链确定校验入口：纯发送方法负责组包；作为多个调用方共享操作入口的 `RequestXxx` 可以集中校验资格、场景、余额或 CD。不得仅凭方法名禁止校验，也不得将已有集中校验移到部分 UI 入口而漏掉其他调用方；
- 校验区分“未同步”与“已知不满足”；未同步时明确等待/重试或服务端兜底路径，不能直接视为资格通过；
- 明确哪些校验必须由服务器兜底，客户端校验只做体验优化。

#### 2.4.5 文案与就绪判定

| 项 | 结论 |
|---|---|
| 静态文案 | 挂 `Localizer` 组件；key 列表：`UI_XxxPage_Title`、... |
| 动态文案（含变量） | 脚本 `"{key}".ToLanguageF(...)`；key 列表：... |
| 数据就绪判定 | Record 可读 / 配置行存在 / 场景就绪，分别用什么条件判断 |
| 禁止缓存的状态 | 就绪标志、pending 表、版本号（可由数据直接判断） |

要求：文案 key 与 `Language_Keys.md` 保持一致；就绪判定必须给出可判定的条件，禁止写"加载完成后""数据准备好后"。

---

## 三、Open Questions 质量标准

<!-- 来源：schema.yaml design instruction lines 313-327 -->

**回答质量检查**（设计合并门禁）：

### 3.1 禁止模糊词汇（阻断性）

❌ **不合格词汇**："看情况""暂时这样""应该可以""先按现在的做""待定""后续再说"

✅ **处理方式**：若发现模糊词汇 → 阻断合并，要求重新回答

---

### 3.2 技术问题必须包含类型定义（阻断性）

❌ **不合格示例**："需要这个字段"（缺少类型）

✅ **合格示例**："int, 0=不显示 1=显示"

✅ **处理方式**：若缺少类型定义 → 阻断合并，要求补充类型

---

### 3.3 业务逻辑问题必须包含具体处理策略（阻断性）

❌ **不合格示例**："按常规处理"（什么是常规？）

✅ **合格示例**："活动结束后，已购买未领取的奖励发邮件补发，有效期 30 天"

✅ **处理方式**：若缺少具体策略 → 阻断合并，要求明确处理方式

---

## 四、文档结构模板

### 4.1 必需章节

```markdown
# Design: {功能名称} - Client

## ⚠️ 当前状态（若 Pre-flight Check 发现既有实现）

## 背景与目标

## 模块定义
- 模块名称
- 文件路径（使用 Pre-flight Check 发现的实际路径）
- 依赖模块（必须明确是否接入 BusinessActivityModule）

## Record 表定义
（必须与服务端完全对齐）

## 配置表数据获取决策
（说明是否需要 DynamicConfigModule）

## UI 设计
（从 demo/src/**/*.tsx 提取结构，包括拆分的独立组件）

## 协议定义
（说明是 Record 驱动还是传统模式）

## 红点规则
（说明注册方式）

## 惯例落实（五张表，见 §2.4，缺一不可）
- 文件与职责清单（枚举每个 .cs）
- 事件订阅清单
- 刷新粒度矩阵
- 请求校验位置
- 文案与就绪判定

## 关键功能说明
（职责和设计决策，不包含代码实现）

## 异常处理

## Open Questions
（必须全部解决且回答质量合格）
```

---

## 五、代码模板查询指南

所有代码模板通过 CodeGraph 查询获取，不在规则文件中硬编码。

### 5.1 模块相关

| 需求 | CodeGraph 查询 | 参考模块 |
|-----|---------------|---------|
| 模块初始化 | `LogicModule OnInit 协议注册` | GrowthFundModule, AccumulateModule |
| 模块文件组织 | `<类似功能>Module 文件结构` | - |
| 依赖模块获取 | `GetModule BusinessActivityModule` | - |

---

### 5.2 Record 相关

| 需求 | CodeGraph 查询 | 参考模块 |
|-----|---------------|---------|
| Record 表定义 | `Define.cs Record 表常量 enum` | BusinessActivityDefine.cs |
| Record 访问 | `FindRecord QueryInt GetInt` | - |
| Record 监听 | `AddRecordHook Record 监听` | - |

---

### 5.3 协议相关

| 需求 | CodeGraph 查询 | 参考模块 |
|-----|---------------|---------|
| 协议发送 | `Custom CLIENT_CUSTOMMSG IVarList` | - |
| 协议接收 | `AddCustomHook SERVER_CUSTOMMSG` | - |
| 协议参数构造 | `CVarList << 协议参数` | - |

---

### 5.4 UI 相关

| 需求 | CodeGraph 查询 | 参考模块 |
|-----|---------------|---------|
| Panel 结构 | `AbstractPanel OnOpen OnClose` | - |
| Page 结构 | `AbstractPage OnShow OnHide` | - |
| 列表刷新 | `OnCellUpdated Transform index` | - |

---

### 5.5 红点相关

| 需求 | CodeGraph 查询 | 参考模块 |
|-----|---------------|---------|
| 活动红点注册 | `RegisterRedPointCallback BusinessActivityType` | BusinessActivityModule_RedPoint.cs |
| 系统功能红点注册 | `RedPointModule Register Bind RedPointType` | RedPointModule.cs |
| 红点刷新 | `DirtyRedPoint SetDirty` | - |

---

## 六、常见问题 FAQ

### Q1: 为什么规则文件不包含代码示例？

**A**: 代码示例容易过时。当项目重构 API 时，规则文件中的示例会失效，导致 AI 生成错误代码。通过 CodeGraph 查询，AI 永远获取最新的代码模板。

---

### Q2: 如果 CodeGraph 查询不到怎么办？

**A**: 使用 Grep/Glob 作为备选：
```bash
# 搜索模块初始化模式
grep -r "class.*Module.*ILogicModule" Assets/Script/LogicModule/

# 搜索协议注册模式
grep -r "AddCustomHook.*CLIENT_CUSTOMMSG" Assets/Script/LogicModule/
```

---

### Q3: 哪些内容必须在规则文件中？

**A**: 只有以下 3 类内容：
1. **架构决策标准**（如何判断是否接入 BA 框架）
2. **框架特殊约定**（如 `DettachPage` 的拼写错误）
3. **质量门禁规则**（Open Questions 回答标准）

其他内容（代码模板、文件路径、字段定义）都应该从代码库获取。

---

## 附录：精简前后对比

| 内容类型 | 精简前 | 精简后 | 变化 |
|---------|-------|-------|------|
| **架构决策规则** | 分散在示例中 | 集中在"架构决策规则"章节 | ✅ 更清晰 |
| **代码模板** | 50+ 行代码示例 × 10 处 | 改为 CodeGraph 查询指南 | ✅ 不会过时 |
| **具体项目内容** | 20+ 个字段定义 | 删除 | ✅ 减少冗余 |
| **文件总行数** | ~753 行 | ~300 行 | ✅ -60% |

---

**版本**: v2 (精简版)
**最后更新**: 2026-10-31（新增 §2.4 惯例落实五节）
**维护原则**: 只包含"无法从代码推理的知识"
