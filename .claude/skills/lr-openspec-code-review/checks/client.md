# 客户端检查项（client 组，共 12 项）

> **SE 适配说明**：GodFort/神域防线及其返工频次是 DL 来源案例，不是 SE 当前文件或接口的证据。实际审查先读 SE `config.yaml` 路由的 ai-core，再用 SE CodeGraph/源码复验；来源案例和缺失的历史附件仅作说明，不作为必读依赖或通过依据。


> 由 `lr-openspec-code-review` 步骤 3 读取，只对本轮改动的客户端 `.cs` 文件及其对应 prefab 执行。
> CodeGraph 的 `projectPath` 指向客户端工程根目录（默认 `../develop/client/project`）。
> 档位：**P0 阻断（权重 10）** / **P1 结构契约（权重 5）** / **P2 质量建议（权重 1）**。
> 报告排序：先档位，同档按 GodFort 实证频次降序。

---

## 0. 完整性前置

用模块名查询代码，确认模块/页面存在：

```
codegraph_explore("<模块名> OnCreate Refresh", projectPath: "<客户端工程>")
```

- **找不到** -> 报告“缺失实施：预期有客户端 <模块名>，但搜索不到”，跳过本组质量检查。
- **找到了** -> 继续执行下列检查。

---

## client-001 UI 框架方法签名（P0 / 权重 10 / GodFort 实证 0）

**目标**：框架回调的方法名与参数类型必须与基类完全一致。写错时**不一定编译失败**（非 override 写法会变成新方法），但回调永远不会被调用。

| 方法 | 正确签名 | 常见错误 |
|---|---|---|
| `OnCellUpdated` | `(Transform root, int index)` | 写成 `GameObject` |
| `AttachPage` | `(AbstractPage page, Transform parent)` | 参数顺序颠倒 |
| `DettachPage` | `(AbstractPage page)` | 写成 `DetachPage`（单 t） |

**检查方法**：

```
codegraph_explore("OnCellUpdated AttachPage DettachPage <模块名>", projectPath: "<客户端工程>")
```

```bash
rg -n "OnCellUpdated|AttachPage|DetachPage|DettachPage" <本次改动的 .cs>
```

**说明**：原 client-002（DettachPage 拼写）已并入本项，不再单独编号。

**报告格式**：

```
❌ client-001: UI 框架方法签名错误
位置: <文件:行号>
方法: OnCellUpdated / AttachPage / DettachPage
现状: <错误签名>
影响: 编译可能通过，但回调不会执行
建议: <正确签名>
```

---

## client-003 红点归属与触发时机（P1 / 权重 5 / GodFort 实证 4）

**目标**：先判断红点归属，再检查注册 API 与置脏时机。**两类红点不能混用**，也不能自造活动类型。

| 场景 | 框架 | 注册 / 刷新 API |
|---|---|---|
| 活动菜单/入口红点（接入 BusinessActivityModule，位置由活动行 `Location` 决定） | `BusinessActivityModule_RedPoint.cs` | `RegisterRedPointCallback(type, Func<int,bool>)`；`DirtyRedPoint(activityId, activityType)` / `DirtyRedPointType(type)` |
| 普通系统功能红点（非活动：主界面、养成、社交等），或活动内自建红点节点 | `RedPointModule/RedPointModule.cs` | `Register(type, Func<RedPointType,bool>)`；父子聚合 `Bind(parent, child)`；自动失效 `SetHookRecord` / `SetHookProp`；置脏 `SetDirty(type)` |

**框架约束**：

- `Bind` 出来的父节点只做聚合，不能再对父节点调用 `Register` / `SetDirty` / `SetHookRecord` / `SetHookProp`，否则框架打印 `Cannot ... bind type` 并静默忽略。
- BA 内部按 `funcId * 100` 注册到 `RedPointModule`，业务模块不要重复注册同一个 `RedPointType`。
- 多期活动必须用 `GetSoloActivityId` 或精确 `activityId` 过滤；不要用“存在阶段列表”推断主活动，也不要把展示期活动判成不可展示。
- 不要自造 `BusinessActivityType` 或红点类型；共享枚举缺失时先登记，再使用。

**触发时机**：

- 只在数据真正变化时置脏（Record Hook、Prop Hook、协议回调里数据实际变化处）。
- 不在纯 UI 刷新函数、定时轮询、`OnOpen` 全量刷新里无条件置脏。

**判定分档**：归属/注册错误记 **P1**；仅置脏时机问题记 **P2**；同一项都命中时按 P1 记录，并在报告里分两行写。

**检查方法**：

```
codegraph_explore("RedPoint Register Bind SetHookRecord SetDirty RegisterRedPointCallback <模块名>", projectPath: "<客户端工程>")
```

**参考实现**：`GodFortModule_RedPoint.cs:200-238`（系统功能直连 RedPointModule）、`BusinessActivityModule_RedPoint.cs`（活动红点）。

**报告格式**：

```
❌ client-003: 红点归属错误（P1）
位置: <文件:行号>
现状: <BA 回调 / 自造枚举 / Bind 父节点上 Register>
建议: <RedPointModule.Register + Bind + SetHookRecord>

⚠️ client-003: 置脏时机过粗（P2）
位置: <文件:行号>
现状: 在 OnOpen/RefreshUI 里无条件 SetDirty
建议: 移到 Record/Prop 回调的数据实际变化处
```

---

## client-004 BusinessActivityModule 接入（P1 / 权重 5 / GodFort 实证 4）

**目标**：接入 BA 的活动模块正确注册活动信息回调，并能解析活动参数；主活动身份唯一。

**必需调用**：

- `m_BusinessActivityModule.RegisterSeverActivityParamArgs(BusinessActivityType.Xxx, OnRecvBusinessActivityInfo)`
- 对应 `ParamArgs(IVarList args)` 重写（起始索引见 client-005）
- 主活动身份使用 `BusinessActivityModule.GetSoloActivityId(BusinessActivityType.Xxx)`，而不是自己维护活动 ID 列表

**说明**：活动红点注册不在此项重复要求，按 client-003 的归属判定执行；非活动功能不要求接入 BA。不要自造 `BusinessActivityType` 值，必须登记到共享枚举。

**检查方法**：

```
codegraph_explore("RegisterSeverActivityParamArgs GetSoloActivityId ParamArgs <模块名>", projectPath: "<客户端工程>")
```

**报告格式**：

```
⚠️ client-004: BA 接入不完整
位置: <文件:行号>
问题: 未注册活动参数回调 / 主活动 ID 由自己推断 / 自造 BusinessActivityType
建议: <补 RegisterSeverActivityParamArgs / 改用 GetSoloActivityId / 登记共享枚举>
```

---

## client-005 协议解析契约（P0 / 权重 10 / GodFort 实证 3）

**目标**：两端对同一条报文的解析必须一致，包含四件事。

1. **原始协议**（`AddCustomHook` 注册的回调）：业务参数从索引 **0** 开始。
2. **BA 协议**（`ParamArgs`）：从 `(int)BAActivityInfoIndex.CustomStart`（索引 **13**）开始。
3. **字段个数/类型/可选尾**：按 `count` 分支；失败包与成功包字段数不同的协议，必须分别处理。
4. **类型兼容**：`int` / `string` 参数两种来源都要兼容；禁止 `long` 到 `int` 的静默窄化。

**说明**：原 client-006（BA 起始索引）已并入本项。GodFort 实际问题是“51 成功包 4→5 字段、失败包 2 字段被丢弃、LinkUI 字符串活动 ID 被解析成 0”，不是 0/1 偏移。

**检查方法**：

```
codegraph_explore("OnRecv ParamArgs IVarList BAActivityInfoIndex <模块名>", projectPath: "<客户端工程>")
```

```bash
rg -n "args.GetInt32\(|args.GetString\(|args.count|args.Count" <本次改动的 .cs>
```

**违反示例**：

```csharp
// 原始协议从 1 开始
int index = 1;

// 固定按 4 字段解析；服务端成功包已变 5 字段
if (args.Count != 4) return;

// 只认 int 活动 ID
int activityId = args.GetInt32(0);
```

**符合示例**：

```csharp
int index = 0;                                   // 原始协议
int index = (int)BAActivityInfoIndex.CustomStart; // BA

if (args.Count < 2) return;
int result = args.GetInt32(index++);
if (args.Count >= 5) hubHpPercent = args.GetInt32(index++);
```

**报告格式**：

```
❌ client-005: 协议解析契约不一致
位置: <文件:行号>
问题: 索引起点 / 固定字段数 / 类型不兼容 / 窄化
契约: <服务端发送 N 字段 / design 文档>
现状: <代码>
建议: <按 count 分支 / 兼容 int+string / 对齐索引>
```

---

## client-008 跨端枚举契约（P1 / 权重 5 / GodFort 实证 3）

**目标**：服务器/配置/协议中的业务枚举在客户端已建模且值一致；不使用自造常量或裸数字绕过共享入口。

**检查点**：

- 业务枚举/协议枚举 -> 使用 `XxxDefine.cs` 或共享枚举（`GameFuncID`、`LEVEL_CLASSS`、`SceneType`、`RedPointType` 等）；
- 协议参数数量、`args.GetInt32(index)` 下标、`parts.Length` -> 可以保留裸数字；
- 对外方法优先收枚举而不是 `int`；
- 通用魔法数字（非跨端契约）由 SE 编码规范检查负责，本项不重复报。

**检查方法**：

```bash
rg -n "case [0-9]+:|(difficulty|propType|result|type|phase|tab|levelClass)\s*[=!<>]=?\s*[0-9]+" <本次改动的 .cs>
rg -n "const int (FUNC_|LEVELCLASS_|RED_POINT)|\(BusinessActivityType\)|\(GodFortDifficulty\)" <本次改动的 .cs>
```

**违反示例**：

```csharp
if (row.type == 2) ...
const int FUNC_GOD_FORT = 7202;              // 自造常量
(BusinessActivityType)1130                      // 自造活动类型
```

**符合示例**：

```csharp
if ((GodFortBuildType)row.type == GodFortBuildType.Soldier) ...
GameFuncID.FUNC_GOD_FORT
BusinessActivityType.GodFort
```

**报告格式**：

```
⚠️ client-008: 跨端枚举契约漂移
位置: <文件:行号>
现状: 裸数字 / 自造常量 / 强转
应有: <共享枚举或 Define 枚举>
建议: <登记枚举并替换>
```

---

## client-009 过度设计与职责倒置（P1 / 权重 5 / GodFort 实证 19）

**目标**：只审查本次变更新增的监听、持久状态、对外接口/包装方法和依赖方向，找出“加了但没人消费”的抽象与反向依赖。**不做跨模块重构**；历史代码除非本轮改动直接涉及，只报告不修改。

**三行证据**：每个新增的 `AddDynamicCommand` / `AddEventHook` / `RegisterPropHook` / `AddPropHook` / 持久状态字段 / 接口或包装方法 / Actions 类，必须写出：

```
参照模块：<成熟模块文件:行号>
数据链路：事件 X -> 处理 Y -> 消费字段 Z -> 影响 UI/状态 W
删除测试：如果现在删掉，具体哪个功能会坏
```

任一行写不出来，判定为过度设计，建议删除。

**负向清单**（命中即逐条检查，默认删除，除非能给出反证）：

1. `m_IsXxxReady` / `m_HasXxxLoaded` / `Registered` / `Hooked` / `m_RecordLoaded` 类就绪状态；数据是否可读看数据本身（`HasProp` / `FindRecord`）。
2. 面板监听 `OnTableReady` / `OnKeyTableReady` / `OnSwitchLanguage`；除非面板可能先于配置打开，或明确要求打开期间切语言即时刷新。
3. BA 通知同时监听 `Changed` / `LateChanged` / `Dirty`；除需要显示 BA 行值外，只保留 `OnBusinessActivityDirty`。
4. 缓存主角色 `ObjectID`；在回调里重复 `self == GetMainPlayer()`；手动 Remove 主角钩子。
5. 客户端校验生成表的 `colCount`；缺表/零行按合法空数据。
6. 在纯协议发送方法里重复业务校验，或迁移校验后遗漏调用方。先按 SE 同类实现判断它是否为共享操作入口；共享入口集中做活动/场景/CD/余额/资格校验可以合理存在，不按 `Request` 命名判违规，服务器仍负责权威校验。
7. 纯包装：`TryDecodeXxx`、`GetReadyData`、`IsXxxReady`、只有一个调用者且无额外语义的抽象。
8. 可派生状态：`version` / `frame` / `ready` / `revision` 计数；每次刷新都 `Clear()` 的缓存字典；只为一次刷新服务的 `StringBuilder` 字段。
9. `OnOpen` 首行的 `ClearDynamicCommand()`；框架在关闭页面前已统一清理（同一页面做显隐切换、需要主动停订阅的除外）。
10. 新增每秒 Timer 做轮询；已有事件能覆盖时不要加。

**职责倒置**（GodFort 实证 4 例）：

- Actions 自转发类、`BindActions` 自绑定；
- Panel 反查 Module、Module 反查 Panel、Cell 持有 Panel/Module；
- 重复页面状态副本（`m_CurrentPage` / `m_OpenRevision` / `m_IsOpen` / `m_IsRefreshing`）；
- 20 个纯转发方法 + 15 个 Ready 代理属性这类抽象层。

**检查命令**（只对本轮改动文件执行）：

```bash
rg -n "AddDynamicCommand|AddEventHook|RegisterPropHook|AddPropHook|AddTimer" <changed files>
rg -n "m_Is[A-Za-z]*(Ready|Loaded|Registered|Hooked)|m_Has[A-Za-z]*Loaded|m_RecordLoaded|colCount" <changed files>
rg -n "ClearDynamicCommand\(\)|ClearTimer\(\)" <changed files>
rg -n "OnTableReady|OnKeyTableReady|OnSwitchLanguage" <changed files>
rg -n "OnBusinessActivity(Changed|LateChanged|Dirty)" <changed files>
rg -n "Actions|BindActions|GetModule<|GetPanel<|m_Panel|m_Module" <changed files>
```

**参照实现**：`DesperateTrialPage.cs:181-184`、`DesperateTrialTalentPanel.cs:68-69`、`DesperateTrialModule.cs:460-461,523-527`。

**豁免**：

- 协议下标、`args.count`、数组长度的防御校验；
- 场景/NPC/plane/载具等短生命周期对象的 `isZero` / `Exists` / `RemovePropHook` / `RemoveRecLateHook`；
- 需要显示 BA 行值（活动时间、人数等）而额外监听的 `OnBusinessActivityChanged`；
- 页面显隐切换时主动 `ClearDynamicCommand` / `ClearTimer` 的对称实现。

**报告格式**：

```
⚠️ client-009: 疑似过度设计 / 职责倒置

| 文件:行 | 新增内容 | 消费点证据 | 判定 | 建议 |
|---|---|---|---|---|
| XXXPanel.cs:47 | OnKeyTableReady 监听 | 处理函数未读取表版本 | 过度设计 | 删除 |
| XXXModule.cs:73 | m_IsXxxReady 字段 | 可由 FindRecord 派生 | 过度设计 | 删除 |
| XXXCell.cs:21 | Cell 持有 Module | 仅用于取主活动 ID | 职责倒置 | Panel 传参 |
```

---

## client-010 刷新粒度（P2 / 权重 1 / GodFort 实证 5）

**目标**：找出“任一变化都整页刷新”“重复选择也刷新”“无变化仍重算”的位置。功能正确但会造成性能与交互副作用。

**检查点**：

1. 整页 `RefreshState()` / `RefreshAll()` 的每个调用点，触发源是什么？为什么不只刷新受影响区域？
2. 重复选择同一项时是否提前返回？
3. 是否有每秒 Timer 或每帧轮询？已有事件能覆盖时删除。
4. `SetText` / `SetActive` 前是否比较当前值，避免无效写入？
5. 是否订阅了与本面板无关的通知（cd/boost/队伍变化等）？

**检查方法**：

```bash
rg -n "RefreshState\(|RefreshAll\(|Refresh\(\)|AddTimer|SetText\(" <本次改动的 .cs>
```

**违反示例**：

```csharp
void OnSelectDifficulty(int index)
{
    m_Difficulty = index;
    RefreshState();          // 错误：重建阶段列表、队伍、背景
}
```

**符合示例**：

```csharp
void OnSelectDifficulty(int index)
{
    if (m_Difficulty == index) return;
    m_Difficulty = index;
    RefreshStageDetails();   // 正确：只刷新受影响的区域
    RefreshDifficultyList();
    RefreshButtons();
}
```

**参考**：`GodFortPage.OnSelectDifficulty`、`refresh-state-audit-2026-10-20`（21 个调用点只删 2 个多余全量刷新）。

**豁免**：页面打开、活动/阶段集合变化时允许全量刷新；资金/冷却/倒计时只刷可见格子不算过粗。

**报告格式**：

```
⚠️ client-010: 刷新粒度过粗
文件: XXXPage.cs:210
触发源: 切换难度
问题: 调用 RefreshState() 重建了阶段列表与队伍
建议: 改为 RefreshStageDetails + RefreshDifficultyList + RefreshButtons
```

---

## client-011 Localizer 与语言 key（P1 / 权重 5 / GodFort 实证 4）

**目标**：静态显示文案绑定 `Localizer` 组件；脚本只负责随数据变化的动态文案；所有 key 真实可解析。

**P1（阻断级，命中即修）**：

- 硬编码中文或英文文案；
- 新增 key 未登记 `changes/<id>/Language_Keys.md`；
- key 在 `BuildRes/config/language.txt` 中不存在；
- `ToLanguageF` 缺 key 时返回原 key 或空串，代码仍直接显示（应判空/判 key 后回退或隐藏）；
- `OnSwitchLanguage` 后立即刷新，未等语言表解析完成（应先清缓存，等表完成通知再刷）。

**P2（质量建议）**：

- 文案不随数据变化，却由脚本赋值（应由 prefab 上的 `Localizer` 提供）。

**检查方法**：

```bash
rg -n "m_(Txt|Lbl)[A-Za-z0-9_]*\.text\s*=\s*\"|ToLanguageF?\(|OnSwitchLanguage" <本次改动的 .cs>
rg -n "<新增key>" BuildRes/config/language.txt
```

逐条判断：

- 文案含变量/分支 -> 保留脚本赋值，但必须走 `"{key}".ToLanguage()` / `ToLanguageF(...)`，每个分支独立 key；
- 文案固定 -> 由 prefab `Localizer` 提供，脚本不赋值；
- 缺 key -> 先补 `Language_Keys.md` 与 `language.txt`，再做显示兜底。

**违反示例**：

```csharp
m_TxtTitle.text = "神域防线";                  // P1：硬编码
m_TxtBtn.text = isGot ? "已领取" : "领取";      // P1：硬编码 + 分支共用
m_TxtScore.text = "UI_Xxx_Score".ToLanguageF(score); // 若 key 不存在 -> 显示原文/空
```

**符合示例**：

```csharp
// 静态标题由 Localizer 组件提供，脚本不赋值
m_TxtBtn.text = isGot
    ? "UI_XxxPage_BtnGot".ToLanguage()
    : "UI_XxxPage_BtnGet".ToLanguage();
```

**报告格式**：

```
❌ client-011: 语言 key 不可用（P1）
文件: XXXPage.cs:88
问题: 硬编码中文 / key 未登记 / key 不在 language.txt / 缺 key 仍显示
建议: <改 key / 补登记 / 加缺 key 兜底>

⚠️ client-011: 静态文案应由 Localizer 提供（P2）
文件: XXXPage.cs:88
问题: m_TxtTitle 文案固定，却在脚本里赋值
建议: 在 prefab 的 m_TxtTitle 上挂 Localizer 并填 key，删除该行赋值
```

---

## client-012 框架注册完整性（P0 / 权重 10 / GodFort 实证 6）

**目标**：新增模块、面板、配置表、条件类型、共享枚举时，框架要求的注册点一个都不能少。这类问题**编译通过、运行静默失效**，是本项目最高频的“看起来做完了”缺陷。

**检查点**：

1. **UI 注册**：`UIDefine` 枚举 + `UIDataTable.AddPanelData`（`typeof` + prefab 路径）两处都齐；只加枚举不加表 -> `OpenPanel` 找不到资源，窗口打不开。
2. **DynamicConfigModule 按实际同步入口核查**：
   - 表级：`outcode_config.json` + `DynamicConfigModule_Process.InitProcessDic/RegisterTable`；
   - 仅旧活动文件拉取链要求活动级：业务 Module 实现 `IConfigSyncMethod`，`string[] fileNameList` / `string[] preFileNameList` 按加载时机列出表名，任一名单可为空；`OnInit()` 调用 `m_DynamicConfigModule.RegisterSyncMethod(this)`。
   - 数据库配置同步核查服务端登记/同步、首次 Ready 请求、版本计划与 `OnDataBaseConfigSync` 回包解析，不强求活动级接口，不补造活动类型。
   - 旧活动链遗漏活动级注册会导致目标活动无法按设计时机拉表；不能把此结论推广到数据库入口，也不能仅凭表暂时为空判为未接入。
3. **条件/扩展点注册**：新增条件类型必须在 `ConditionModule.InitCondition` 注册（如 `ConditionGodFortTalentLevel`）；新增 Command/事件/属性钩子同理。
4. **共享枚举入口**：不自造 `GameFuncID` / `LEVEL_CLASSS` / `SceneType` / `RedPointType` / `BusinessActivityType`；缺失时先登记，再使用。

**检查方法**：

```
codegraph_explore("UIDefine UIDataTable AddPanelData <Panel名>", projectPath: "<客户端工程>")
codegraph_explore("IConfigSyncMethod RegisterSyncMethod <Module名>", projectPath: "<客户端工程>")
codegraph_explore("InitCondition <条件类型名>", projectPath: "<客户端工程>")
```

```bash
rg -n "AddPanelData|RegisterSyncMethod|fileNameList|InitCondition|RegisterCondition" <本次改动的 .cs>
rg -n "const int (FUNC_|LEVELCLASS_|RED_POINT)|\(BusinessActivityType\)\s*[0-9]" <本次改动的 .cs>
```

**违反示例**：

```csharp
// 只加了枚举，没有 AddPanelData -> 窗口打不开
public enum UIID { GodFortPanel = 1866 }

// 旧活动文件拉取链只做表级注册，未声明活动拉取时机
// DynamicConfigModule_Process.InitProcessDic 内
RegisterTable(...);
// 缺少：class XxxModule : ILogicModule, IConfigSyncMethod
// 缺少：m_DynamicConfigModule.RegisterSyncMethod(this);

// 自造条件类型，未注册 -> 条件永远 false
const int CONDITION_GOD_FORT_TALENT_LEVEL = 60;
```

**符合示例**（旧活动文件拉取链注册节选；接口其他成员与依赖获取仍须按 SE 实际定义补齐）：

```csharp
UIDataTable.AddPanelData(UIID.GodFortPanel, typeof(GodFortPanel), "GodFortPanel/GodFortPanel");

class GodFortModule : ILogicModule, IConfigSyncMethod {
    public string[] fileNameList { get; } = { "sanctumbulwark_stage" };
    public string[] preFileNameList { get; } = System.Array.Empty<string>();
    // 其余接口成员与依赖获取按 SE IConfigSyncMethod 和同类模块补齐
    protected override void OnInit() { m_DynamicConfigModule.RegisterSyncMethod(this); }
}

// 在 ConditionModule.InitCondition() 内注册
m_ConditionDic[(int)ConditionType.GodFortTalentLevel] = new ConditionGodFortTalentLevel();
```

**报告格式**：

```
❌ client-012: 框架注册缺失
类型: UI 注册 / DynamicConfig 表级适配或旧活动链注册 / 条件扩展点 / 共享枚举
位置: <文件:行号>
缺失: <具体注册点>
影响: 窗口打不开 / 配置永远为空 / 条件永远 false / 枚举漂移
建议: <补注册 / 先登记枚举>
```

---

## client-013 序列化字段与 Prefab 绑定（P1 / 权重 5 / GodFort 实证 5）

**目标**：脚本新增/改名/拆分的序列化字段，在 prefab 上真实绑定；列表模板、运行时启用状态不遗漏。编译通过但字段为 null 时，界面表现为空白、按钮点不动。

**检查点**：

1. 每个新增 `[SerializeField]` / public 序列化字段，在对应 prefab 中有同名属性；引用型字段不能是 `{fileID: 0}`。
2. 字段改名或拆分后，旧 prefab 行不会自动迁移：检查 `FormerlySerializedAs` 或“待资源重绑”记录。
3. 列表：`m_CellTemplate` 非空；模板节点不在 Content 内（否则被当第 0 行复用）；ScrollRect 的 viewport/content 指向本区。
4. 运行时启用：代码中从未 `SetActive(true)` / `m_Enabled = true` 的 Toggle/Button，是否本来就该显示？反之，禁用节点是否仍被代码访问。
5. TMP：新增文本必须用 `TextMeshProUGUI`，禁止 `UnityEngine.UI.Text`。

**检查方法**：

```bash
rg -n "\[SerializeField\]" <本次改动的 .cs>
rg -n "m_<字段名>:" <对应 .prefab>
```

如果工程存在 `orphan-check.py`（`rules/common/compile-verification.md` §4.4），先运行它，把输出作为线索，再逐条人工确认；脚本告警不等于违反。

**豁免**：

- 可选引用字段允许 `{fileID: 0}`，但代码必须有 null 判断；
- 页面/面板实例由运行时 `AttachPage` / `OpenDependPanel` 赋值的，不要求 prefab 绑定；
- prefab 尚未生成（ui-prefab 阶段在后）-> 记为“待绑定清单”，不算违反。

**报告格式**：

```
⚠️ client-013: 序列化字段未绑定 / 绑定待确认
文件: XXXPage.cs:24（字段 m_BtnChest）
Prefab: XXXPage.prefab
现状: prefab 中无同名属性 / {fileID: 0} / 旧字段名残留
影响: 按钮点不动 / 列表不渲染 / 复用显示旧数据
建议: <补绑 / 加 FormerlySerializedAs / 记录待绑定>
```

---

## client-014 生命周期与订阅配对（P1 / 权重 5 / GodFort 实证 6）

**目标**：模块初始化顺序、网络会话清理、订阅/反订阅、面板打开时序正确。这类问题只在换场景、断线重连、二次打开时暴露。

**检查点**：

1. **模块注册顺序**：新 Module 已在 `GameLauncher` 注册；依赖 Module 在其之前初始化；`GetModule<T>()` 不会为 null。
2. **网络生命周期**：`InitNetwork` / `ResetNetworkSession` / `CloseNetwork` 在 `OnInit` / `OnReset` / `OnClose` / 断线回调中成对接入；`InitNetwork` 里 `AddCustomHook` 注册的 S2C 回调不能漏（漏注册时包进不了回调，编译不报错），清理时同时清等待队列、结算候选、缓存。
3. **订阅配对**：新增 `AddDynamicCommand` / `AddEventHook` / `RegisterPropHook` / `AddPropHook` 是否有对应清理；框架已统一清理的不要重复（见 client-009 豁免）。
4. **打开时序**：`OnOpen` 首帧不要依赖尚未赋值的 Page/Panel 引用；上下文应由 `onOpened` 或 `AttachPage` 之后再读取。
5. **场景归属**：场景内活动的结算/广播包只处理当前场景/当前活动；离场或迟到的包直接丢弃，不另造 token/上下文。

**检查方法**：

```
codegraph_explore("OnInit OnReset OnClose InitNetwork ResetNetworkSession <模块名>", projectPath: "<客户端工程>")
```

```bash
rg -n "AddDynamicCommand|AddEventHook|RegisterPropHook|AddPropHook|ClearDynamicCommand|RemovePropHook|RemoveRecLateHook|OnReset|OnClose" <本次改动的 .cs>
rg -n "GameLauncher|AddModule|RegisterModule" <本次改动的 .cs>
```

**违反示例**：

```csharp
// BattleModule 未在 GameLauncher 注册 -> GetModule 返回 null
// OnClose 只清 UI，不清等待队列 -> 重登后仍在等旧请求
// OnOpen 首行读取 m_Page.Context，但 m_Page 尚未 AttachPage
```

**报告格式**：

```
⚠️ client-014: 生命周期 / 订阅不配对
位置: <文件:行号>
问题: 未注册 Module / 未清理网络会话 / 订阅无清理 / OnOpen 时序错误 / 迟到包未丢弃
影响: GetModule 为 null / 重登串旧状态 / 二次打开不刷新 / 跨场景弹结算
建议: <补注册 / 补清理 / 调整读取时机 / 按场景过滤>
```

---

## client-015 Module 数据边界与 Record 注册（P1 / 权重 5 / GodFort 实证 3）

先读 SE `../develop/client/project/docs/ai-core/knowledge/external/soul-engine-client-bridge.md` 的模块接入章节，并按 SE 源码确认 owner 和回调/对象绑定的两个时点；不要把 DL 的单个模块模式当成所有 SE 模块的实现。

**目标**：检查 Module 层的数据注册、就绪判定、命令分发与请求职责。典型表现是编译通过、页面能打开，但数据永远为空或永远不刷新。只查本轮新增或改动的 Module 及其 Record/属性钩子相关代码；历史代码除本轮直接涉及外只报告不修改。

**与 client-009 的分工**：009 抓“新增了但没人消费”的抽象（删除测试）；015 抓“用了，但语义或边界错”。同一位置命中两项时按 015 记，009 只写“另见 client-015”。

**检查点**：

1. **一表一注册一回调一命令**：对每张被监听的 Record，记录 `Record 名 / owner / 具名回调 / 添加 Hook 的时点 / 下游 Command`。初始化时通过实际 API 登记具名回调（如 `RegisterRecLateHook`），取得对应 owner 后添加 Hook（如 `AddRecLateHook`）：主角 Record 在主角 Ready 后绑定当前主角；场景 Record 在对应场景对象就绪后绑定；plane Record 在 `OnPlaneObjAdd` 等对应对象到位时绑定。不得要求非主角 owner 统一改到主角 Ready；owner 重建或切换后核对旧绑定清理和新对象绑定，按实际框架生命周期处理。回调名统一为 `"XxxModule:OnXxxChanged"`；每张表只派发自己的 Command，不在一个 `NotifyAll` 里把全部表命令发一遍。
2. **禁止平行分发表**：不要用 `RecordKind` + 通用 switch、`m_RecordLoaded[]` 并行数组做分发或就绪判断。
3. **缺表语义**：`FindRecord == null` 只表示该玩家/该场景暂无数据，不等于“尚未同步”。使用前核对服务端 struct xml（是否有默认行）和写入路径（首次写入、进副本时 `ClearRecord`）。同步完成后缺表/缺行按空数据返回默认值，`TryGetXxx` 的 false 只表示未同步或参数非法。
4. **ready 粒度**：同一个 ready flag 只能覆盖 owner、同步时点、缺表语义都相同的一组数据，任一不同就拆；能直接从对象引用、集合内容或框架生命周期得到的值不再另存。
5. **请求职责**：按 SE 同类实现与调用链区分纯发送方法和共享操作入口。纯发送方法负责组包；`RequestXxx` 若作为共享入口，可以集中校验活动/场景/CD/余额/资格，不得仅凭方法名判违规或将校验迁移到部分 UI 后遗漏其他调用方。服务器负责权威校验；未同步数据按设计等待/重试或交服务端兜底，不当作资格通过（与 client-009 #6 交叉引用，不重复报）。SE `BossChallengeModule_Net.RequestChallengeTeamBoss`、`CarnivalActivityModule_Net.RequestTriggerReward` 可作集中校验的现场参照。
6. **依赖与清理**：依赖模块在 `OnInit` 取；实现 `OnClose` 的模块在其中置空依赖、清缓存/命令/红点；`GetSoloActivityId` 可能返回 `-1`，业务入口统一归 `0`。
7. **属性钩子按 owner 绑定**：初始化时登记 `RegisterPropHook`，在实际 owner 可用时 `AddPropHook`。只有主角属性采用主角 Ready；场景、plane 或其他对象按各自就绪事件和对象 ID 绑定。回调是否需要 `self` 过滤、对象切换时如何解绑，依据实际绑定范围和生命周期判断；不要给非主角钩子机械添加主角过滤。框架已统一清理的绑定不重复移除，短生命周期对象的成对清理见 client-014 #3。

**豁免**：属性/BA/场景的就绪判定按各自边界（见 client-014）；不要求 Module 判断生成表 `colCount`（见 client-009 #5）。

**检查方法**：

```
codegraph_explore("RegisterRecLateHook AddRecLateHook RegisterPropHook AddPropHook OnMainPlayerReady OnSceneReady OnPlaneObjAdd FindRecord NotifyAll <模块名>", projectPath: "<客户端工程>")
```

```bash
rg -n "RegisterRecLateHook|AddRecLateHook|FindRecord|NotifyAll|RecordKind|m_RecordLoaded|m_[A-Za-z]*Ready" <本次改动的 .cs>
rg -n "Request[A-Za-z]+\(|GetSoloActivityId|void OnClose|void OnInit" <本次改动的 .cs>
```

**SE owner 参考实现**：`SceneNpcModule.OnInit` 登记回调，`OnPlaneObjAdd` 向实际 `planeObj` 添加两张 NPC Record 的 Hook；`BubbleArcadeModule` 在场景 Ready 后向场景对象绑定 Record/属性。主角 Record 可对照知识库中的 `DailyGiftModule` / `SeasonTaskModule`。这些 owner 分支按当前 SE 源码核对，不互相替代。

**DL 来源案例**：`GodFortModule_Record.cs`（一表一 hook 一命令；`TryGetLevelState` 缺表返回零值且返回 true）、`DesperateTrialModule.cs`（`OnMainPlayerReady` 重新 Add 钩子，不保存返回值）、`GodFortModule.cs`（`GetMainActivity` 把 `-1` 归零）；仅作规则说明，不代替 SE owner 事实。

**报告格式**：

```
❌ client-015: Module 数据边界错误
位置: <文件:行号>
问题: 一表多命令 / 平行数组分发 / 缺表当未同步 / ready 粒度错误 / 校验入口边界错误或漏覆盖调用方
影响: 页面不刷新 / 数据永远为空 / 重登后状态残留
建议: <按 module.md 对应条目修改>
```

---
