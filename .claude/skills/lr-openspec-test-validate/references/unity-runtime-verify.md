# Unity 运行时验证

## 目标与非目标

**目标**：通过 ai-game-developer MCP，在真实 Unity 中验证 UI 结构、字段绑定、状态、交互契约（C1 类型 / C2 能力 / C3 行为）、Console，并把结论写成可复验的证据。

**非目标**：
- 不做像素级视觉验收（交人工）
- 不真实支付、不领取、不消耗
- 不修工程、不改 Prefab、不改配置表
- 不把 GM/注入打开面板等同于真实入口验证

三份配套文档：

- `interaction-contract.md`：交互契约表、C1/C2/C3 判据、安全分级、覆盖率门禁
- `mock-data-shim.md`：数据缺失时的注入与清理
- `tc-classification.md`：TC 归类与 2a 拆分为 2a-struct / 2a-interact

---

## G0 能力预检

工具在列表里 ≠ 能用。先探，再决定跑不跑。

| 探测项 | 方法 | 不通过时 |
|---|---|---|
| MCP 连通 | `editor-application-get-state` | `runtime_skipped(blocked_tooling)` |
| 动态 C# | `script-execute` 执行一行 `Debug.Log` | 同上（身份、注入、交互都依赖它） |
| Console | `console-get-logs` 返回 | 同上（无法归因） |
| 面板 API | `ui-list-opened-panels` | 降级：只能做 Prefab 资产态验证 |
| 反射 | `reflection-method-find` 能查到目标类型 | 降级：登录/关闭走 UI 兜底 |
| 组件读取 | `gameobject-component-get(paths=...)` | 降级：只验层级存在性 |
| **交互链** | `script-execute` 读 `EventSystem.current != null` + 面板 Canvas 上的 `GraphicRaycaster` | **只能做 4a 配置断言**，4b 全部 `blocked_tooling` |

交互链不通时不是整批失败：C1/C2 仍然可做，C3 记 blocked，面板判定最高 `runtime_config_only`。

工具被权限拒绝时，**提示用户**在 `.claude/settings.local.json` 的 `permissions.allow` 加入 `mcp__ai-game-developer__*`，**不要自动改配置**。

能力矩阵要写进报告第 2 节。

---

## G1 身份门禁

```
script-execute: Debug.Log(Application.dataPath)
→ console-get-logs 取回
→ 与 config.yaml 的客户端工程路径比对
```

- **不用** `reflection-method-find` 查 `Application.get_dataPath`（它只搜工程程序集，查不到 UnityEngine 核心）
- 路径不匹配：`unity_mcp_project_mismatch`，**停止所有 Unity 写操作**，不读取当前 Console 作为证据

---

## G2 编译基线

```
身份通过
→ assets-refresh（ForceUpdate）
→ 轮询 editor-application-get-state，直到 IsCompiling=false 且 IsUpdating=false
→ console-get-logs 读本轮 Error
```

- 没有真实编译结果，只有“刷新成功”，**不能判 compile_passed**
- `console-clear-logs` 可能因文件占用失败：改用**时间戳基线**，并记录 `console_cleanup=blocked`
- 编译有 error → `runtime_skipped(compile_not_passed)`，最多给 `inconclusive`

---

## G3 进 Play

- `editor-application-set-state(isPlaying=true)`
- PlayMode 切换时 MCP 可能断连（`Failed to invoke ... after 10 retries`）：**这是预期**，轮询恢复即可，不得判环境失败
- 等资源加载完成、登录面板出现

---

## G4 进入主游戏（三级优先）

```
1. 复用现场
   ui-list-opened-panels（必须在 PlayMode 内，非 Play 时结果是陈旧的）
   + 反射/AIMCP 的 IsSceneDataReady 之类只读方法
   → 已在主游戏：绝不登录

2. 直接发命令（绕开包装工具的私有锁）
   reflection-method-find 找到当前工程的登录命令发送方法（不要写死方法名）
   reflection-method-call 调用
   → 轮询场景就绪

3. 包装工具
   game-login，整个批次最多 2 次
   → 返回 in-progress 超过 60s：blocked_tool_lock，降级到第 2 级
```

**禁止**反复调用 `game-login`。它的锁一旦卡住不会自己释放。

如果出现 `Debugger.Assert: Can not read table while parsing.`：

- 判 `blocked_game_assert`
- 记录断言原文、堆栈、当前面板列表、截图
- **停止**，不修改表、不修工程

---

## G5 面板清单与批次分组

从 `tasks.md` / `test-cases.md` / `design.md` 提取：

```
面板名 | UIID/pName | Prefab 路径 | 目标 TC | 运行前置（账号/等级/数据）
```

- 面板不在 UIDataTable、Prefab 不存在 → 该面板 `blocked`，其余继续
- 同账号/同等级/同前置 → 同一批次（一次 Play）
- 前置不同 → 拆批次

批次开始前把清单写进报告。

### 活动页入口：四级与红线

活动类界面（继承 `BaseActivityPage`）不能直接 `ui-open`，必须同时提供菜单数据。按证明力从高到低选，**能高不低**：

| 级别 | 入口方式 | 证明力 | 标注 |
|---|---|---|---|
| L0 真实入口 | 点击主界面活动图标进入 | 最强，覆盖入口链路 | `entry=real` |
| L1 GM / 配置 | `game-execute-gm-command` 打开活动界面 | 中 | `entry=gm` |
| L2 合成菜单数据 | 反射设 `m_MenuData`，再调 `OpenPageUI(...)` + 面板刷新入口 | 弱，只证明页面渲染与交互 | `entry=synthetic_setactivity` |
| L3 直接注入 | `ui-open` 强开 | 最弱 | `entry=injected_ui_open` |

**红线：不要用 `SetActivity(...)` 注入。** `BaseActivityPage.SetActivity` 会依次调用 `RecordRedPoint()` 和 `RequestActivityInfo()`：前者在 `redType=LocationDay` 时通过 `LocalPlayerConfig.SetDictionary` **写本地存档**，违反 mock 红线。

需要注入时，只做这两步：

1. 反射把合成好的 `BusinessActivityMenuData` 写进面板的 `m_MenuData`
2. 调 `OpenPageUI(args)`（或面板自己的刷新方法），**不要**调 `SetActivity`

另外：`m_Module` 在 `OnCreateUI` 里已被 `m_Kernel.GetModule<T>()` 赋值，**不要重复注入**；只有确实为 null 时才补。

报告里必须写 `entry` 与 `entry_verified`：

- `entry_verified=true` 仅当走 L0 或 L1 且确实点/发成功
- L2 / L3 一律 `entry_verified=false`，并把“真实入口未验证”写进人工清单

---

## 批处理执行

```
准备一次（G0~G4）
  → 每个面板：
      标记日志 [LR-VERIFY][panel=X][phase=open]
      → 打开（按 G5 入口级别，优先真实/GM）
      → 有界等待稳定（面板 active、loading 消失）
      → mock（按需，见 mock-data-shim.md）
      → 采证（结构 / 绑定 / 状态 / 视觉）
      → 4a 配置断言（C1 + C2）
      → 4b 实际交互（C3，仅 safe 项）
      → 清理 mock
      → 关闭（CloseButton 优先；AbstractPanel.CloseSelf 兜底）
      → 核对面板列表回到基线
      → 标记日志 [LR-VERIFY][panel=X][phase=done]
  → 收尾一次（退出 Play）
```

**4a / 4b 必须分开记录**：4a 只读，任意面板都能做；4b 会被安全分级和工具能力卡住。只做 4a 的面板判 `runtime_config_only`，不能与做了 4b 的面板混为一谈。

**失败隔离**：

| 情况 | 处理 |
|---|---|
| 单面板打不开/断言失败 | 标该面板 failed/blocked，继续下一个 |
| 单面板超时 | 标 blocked，继续 |
| mock 失败 | 标 blocked_precondition，继续 |
| 4b 某个交互抛异常 | 该交互 inconclusive，其余继续；面板结论按覆盖率门禁降级 |
| 环境级故障（Play 崩/MCP 断/编译失败） | 终止整批，保留已完成结果 |

**隔离失败**（面板列表没回到基线）：下一个面板标 `isolation_warning`，断言降为 `inconclusive`，不能带污染继续判。

---

## 面板寻址

运行时面板在 `DontDestroyOnLoad`：

1. `ui-get-panel-gameobject-path` 拿到 `UIRoot/RootCanvas/PanelRoot/XxxPanel(Clone)`
2. `gameobject-find` **按这个路径/名字找不到**（它只搜 active scene）
3. 用 `script-execute` 拿面板 GameObject 和关键组件的 `instanceID`
4. 再用 `gameobject-component-get`（传 `gameObjectRef.instanceID` + `componentRef.instanceID`）做原生读取

活动页（`BaseActivityPage` 及其子类）用 `ui-get-panel-gameobject-path` 可能失败，直接走第 3 步。

**Prefab 资产态**则相反：

```
assets-prefab-open → gameobject-find(path/name) → assets-prefab-close(save=false)
```

不先打开 Prefab，`gameobject-find` 传 path 会被忽略、始终返回根节点。

---

## 采证六类

### 1. 结构

- 面板真的打开：`ui-list-opened-panels` + `ui-get-panel-gameobject-path`
- 关键节点存在、active 状态正确
- 层级关系与设计一致
- **路径来源**：代码里的 `PATH_*` 常量 > prefab 实际层级 > demo；**禁止猜**

### 2. 字段绑定（C1 的一部分）

绑定的判定不是“非空”，是“**非空且类型可赋值**”。

```csharp
bool ok = expectedType.IsInstanceOfType(actual) || (go != null && go.GetComponent(expectedType) != null);
```

- **必须区分绑定来源**，两个都记：
  - `binding_source=serialized`：`[SerializeField]` 字段
  - `binding_source=runtime`：`OnCreateUI` 等运行时赋值
- 运行时字段**不是**“不算绑定项”，而是**单独一类证据**。之前写法把运行时绑定漏掉，正是组件用错没被发现的原因之一
- `GameObject` / `Transform` 类型字段：`IsInstanceOfType` 恒真，等于没验；必须再断言它身上挂了期望组件
- 项目自定义组件用序列化字段名：`paths=["m_CurCount","m_ShopBtn"]`
- Unity 内置组件用**属性名**：`paths=["interactable","content","viewport","vertical"]`
- 对内置组件用 `m_*` 会得到 `<unresolved>`
- 数组按元素逐个核对，不能只看 `Length > 0`

### 3. 状态

- 用代码常量定位状态标记：`BigCell/RedDot`、`Received`、`BigCell/CheckImg`
- 逐节点核对：`RedDot.activeSelf`、`Received.activeSelf`、`CheckImg.activeSelf`、`ItemIcon.activeSelf`
- 文本/进度：`ProgressText`、`NameText`、数量角标
- 状态数量与 mock/真实数据预期一致

### 4. 4a 交互配置断言（C1 + C2）

只读，不改状态。逐项对照 `interaction-contract.md` 的契约表。

| 组件 | 读什么 | 判定要点 |
|---|---|---|
| ScrollRect | `content` / `viewport` / `horizontal` / `vertical` / `movementType` | 非空且父子关系正确；方向与 demo 一致 |
| 可滚动性 | `content.size` vs `viewport.size` | **条件断言**：仅当内容超出时才要求可滚 |
| Button | `interactable` / `transition` / `targetGraphic` | 状态符合预期；targetGraphic 非空 |
| Toggle | `group` / `isOn` / `graphic` | 单选组 `allowSwitchOff=false`，初始唯一选中 |
| 动态列表（SE ScrollView） | `totalCount` | 断言条数，**不要数子节点**（分帧创建，第一次读偏少） |
| 动态列表（ScrollRect 模板） | 模板 inactive、实例数 | 实例数 = 数据条数 |
| 遮罩 / 射线 | `GraphicRaycaster`、`CanvasGroup.blocksRaycasts` | 缺 GraphicRaycaster → 整面板点不到 |

**注意**：`GetPersistentEventCount()==0` 不代表没监听；运行时 `AddListener` 添加的监听不计入持久事件。

### 5. 4b 实际交互（C3）

MCP 没有点击工具，用 `script-execute`。**必须走 UI 事件链**，禁止 `onClick.Invoke()`（会绕过 interactable、遮罩、raycast）。

前置：安全分级已完成。**只执行 `safe` / `read_only_request` 的项；`unsafe` 一项都不许打。**

| 交互 | 操作 | 断言 |
|---|---|---|
| 点击 | RaycastAll → `GetEventHandler<IPointerClickHandler>` → 执行 down/up/click | 目标反馈（弹窗、切页、状态变化） |
| 滚动 C3a | 设 `verticalNormalizedPosition` 0→1 | `content.anchoredPosition` 变化 |
| 滚动 C3b | 构造 `PointerEventData` + `ExecuteEvents.dragHandler` | content 位移 + 无异常；**每个面板至少一次** |
| 切页 | 点击目标 Toggle | 目标页 active、旧页 inactive、组内唯一 |
| 展开/收起 | 点击表头/按钮 | 区域 active 翻转 |
| 关闭 | 点击 CloseButton | 面板从 `ui-list-opened-panels` 消失 |

配方与判据详见 `interaction-contract.md` 第八、十一节。

**射线可达**：点击前先确认解析出的 handler 是目标或其子节点；被无关节点挡住 → `unreachable_interaction`，不能靠 `Invoke()` 绕过。

**覆盖率**：每个面板记录 `safe_c3_done / safe_total`、`unsafe_total`、`critical_done`。缺 critical（滚动/切换/安全按钮/关闭）一律不得 passed。

### 6. 视觉

- `screenshot-game-view` 作为证据附在报告
- 只做**角色一致性**检查（标题/按钮/价格用了对的样式角色）
- 像素级差异交人工，标 `runtime_visual_review_needed`

---

## Console 归因

- 被测流程开始后**禁止 clear**
- 每个面板打阶段标记：`[LR-VERIFY][panel=X][phase=open|done]`
- 按时间窗 + 标记归因到面板
- 分类：
  - `related`：涉及被测面板/Module/协议
  - `unrelated`：他人改动、既有噪音、表字段不匹配、AB 缺失
  - `unknown`：无法排除影响 → 相关断言不能判通过
- **自己探测失败产生的 Error 单独归类**（如工具调用报错、脚本编译失败），不算被测功能

Console/反射输出经常超 token：必须用 `logTypeFilter` + `lastMinutes` + 精确过滤，超限就落盘后本地解析。

---

## 判定

| 判定 | 条件 |
|---|---|
| `runtime_passed` | 门禁通过 + C1/C2/C3 全覆盖 safe 项 + critical 全做 + Console 无 related/unknown |
| `runtime_passed_mock` | 同上，数据来自 mock |
| `runtime_failed_related` | 发现本功能问题（含 `component_type_mismatch` / `interaction_behavior_mismatch` / `unreachable_interaction`） |
| `runtime_partial_unsafe` | 其余全过，但存在 unsafe 交互无法执行 |
| `runtime_interaction_incomplete` | safe 项未做 C3，或 critical 有缺 |
| `runtime_config_only` | 只做了 C1/C2，未做 C3 |
| `runtime_visual_review_needed` | 结构/交互通过，视觉待人工 |
| `runtime_blocked_precondition` | 账号/场景/数据/配置 |
| `runtime_blocked_tooling` | 工具能力不足（无 EventSystem / 无 GraphicRaycaster / 动态 C# 不可用） |
| `runtime_inconclusive` | 证据不足、缺编译基线、isolation 污染、交互抛异常 |
| `runtime_skipped(reason)` | 门禁未过 |

**同一面板出现多种情况时取最严重者**（从上到下优先级递减）：

```
skipped > blocked_tooling > blocked_precondition > failed_related
        > interaction_incomplete > partial_unsafe > inconclusive
        > config_only > visual_review_needed > passed_mock > passed
```

**change 级结论映射**：

| 面板判定 | change 级 |
|---|---|
| 全部 `runtime_passed` / `runtime_passed_mock` / `runtime_visual_review_needed` | `passed`（视觉项进人工清单） |
| 任一 `runtime_failed_related` | `not_passed` |
| 任一 `runtime_interaction_incomplete` / `runtime_partial_unsafe` / `runtime_inconclusive` / `runtime_config_only` | `not_passed`（写清未覆盖范围） |
| 全部 `blocked_*` / `skipped` | `blocked` |

**`runtime_config_only` 绝不能映射成 `passed`。** 它只说明组件配置对，不能说明交互对——而这正是本阶段要防的问题。

---

## 工具坑位（实测）

| 坑 | 处理 |
|---|---|
| `gameobject-find` 找不到 DontDestroyOnLoad 面板 | script-execute 取 instanceID |
| `gameobject-find` 对 Prefab 资产忽略 path | 先 `assets-prefab-open` |
| 内置组件用 `m_*` 读字段 → `<unresolved>` | 改用属性名 |
| 非 Play 时 `ui-list-opened-panels` 返回陈旧面板 | 先查 `IsPlaying` |
| `reflection-method-find` 查 `Task<T>` 方法输出巨大 | 精确 type/method + `parametersMatchLevel=0` |
| `console-clear-logs` 文件占用 | 时间窗基线 + `console_cleanup=blocked` |
| PlayMode 切换 MCP 断连 | 轮询恢复，不判失败 |
| `ping` 工具可能不存在 | 用 `editor-application-get-state` 探活 |
| `object-get-*` 非 Play 返回 not ready | 只在 PlayMode 用 |
| `IsAllDataReady` 是 IVar 不是 C# 属性 | 用反射调工程的只读判断方法 |
| **SE ScrollView 分帧创建**（`m_MaxCreateCountPerFrame=1`） | 断言 `totalCount`，不要数子节点；读一次就断言必然误判 |
| **`onClick.Invoke()` 看似“点过了”** | 绕过 interactable/遮罩/raycast，禁止使用；必须走 `ExecuteEvents` |
| **`GetPersistentEventCount()==0` 被当成无监听/安全** | 运行时 `AddListener` 不计入；安全分级必须追 handler |
| **`SetActivity(...)` 注入活动页** | 会 `RecordRedPoint` 写本地存档；改为反射设 `m_MenuData` + `OpenPageUI` |
| **`content.size > viewport.size` 当绝对断言** | 数据不足时滚不动是正确行为；改为条件断言 |
