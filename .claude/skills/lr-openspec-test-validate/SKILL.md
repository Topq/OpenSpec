---
name: lr-openspec-test-validate
description: 测试用例覆盖分析与验证。静态验证逻辑类 TC；通过 ai-game-developer MCP 在真实 Unity 中批量验证 UI 结构、字段绑定、状态，并按 demo 交互契约逐项验证组件类型、能力与实际操作（滚动/点击/切换/关闭）；对生成/修改过 Prefab 的页面追加布局几何对照验收（宿主内缩、一级区域占比、文本单行、模板尺度、图片比例）；页面因数据缺失而内容为空时，先垫测试数据再验、验证后清理；新增/修改页签或入口时，必须走父面板真实入口链路，不能只注入目标页；无法自动验证的输出人工/联调清单。
---

# lr-openspec-test-validate

> **职责**：把 `test-cases.md` 变成可执行的验证结论。能静态判的静态判，能进 Unity 跑的进 Unity 跑，跑不了的输出人工/联调清单。
> **阶段**：11b
> **前置**：`/lr-openspec-apply` 已产出 `test-cases.md`、`implementation-report.md`
> **产出**：一份 `changes/<id>/test-validate-report.md`

本文件只保留**路由、门禁、判定口径和安全红线**。执行细节按步骤读取 `references/` 下对应文档，不要一次全读。

---

## 适用 / 不适用

**适用**：
- apply 完成后，判断哪些 TC 已被实现覆盖
- 有 UI 脚本 / Prefab 的 change，做运行时结构与交互验证
- 需要把可自动化验证的 TC 从人工清单里扣掉

**不适用**：
- 替代 QA 验收和真机回归
- 自动修复发现的问题（本技能只验证、只报告）
- 改客户端/服务端代码、改配置表、改 Prefab

---

## 核心口径：交互与布局像 demo，样式不用

Demo 是 Web 原型，**颜色、贴图、美术资源**必须适配项目，不要求与 demo 一致。但两类东西必须一致：**交互**——demo 里能滑的区域，prefab 必须挂 ScrollRect 且真的滑得动，demo 里是单选，运行时不能变成多选；**布局几何**——一级区域的边界与占比按 demo，见下方 GL 层。

UI 组件用错不会报编译错误，只会静默改变行为。因此每个交互点都要过三层契约：

| 层 | 检查 | 典型失败 |
|---|---|---|
| **C1 类型** | 位置上挂的是不是对的组件 | Toggle 挂成 Button、缺 ScrollRect |
| **C2 能力** | 组件配好了没 | content 没绑、ToggleGroup 缺失 |
| **C3 行为** | 实际操作，反馈对不对 | 滑不动、点不响应、切页不换内容 |

**只做 C1/C2 不能写 passed**，上限是 `runtime_config_only`。判据见 `references/interaction-contract.md`。

页面内契约不覆盖“这个页面能不能被用户走到”。新增/修改页签或入口的 change 还要过**入口链路**：

| 层 | 检查 | 典型失败 |
|---|---|---|
| **E1 配置** | 入口/页签 func 的 `isOpen` 与开放条件 | `func.IsOpen` 漏配，父面板把页签过滤掉 |
| **E2 父面板** | 父面板页签列表包含目标 funcID | `RefreshList()` 过滤后没有目标页 |
| **E3 真实点击** | 入口卡片 → 目标页签 → 页面 active | 卡片 handler 打不开父面板、页签点不开 |

只做 `ui-open` 目标页，E1~E3 全都是空的；页内 100% 通过也不能证明用户进得去。

生成/修改过 Prefab 的页面还要过**布局几何契约**：

| 层 | 检查 | 典型失败 |
|---|---|---|
| **GL1 宿主边界** | 页面一级内容容器与宿主 chrome 不相交；内容起点 = 宿主内容区 + 声明内边距（全屏 `Bg` / `WindowBg` / 遮罩 / dimmer / 滚动条 / 装饰层不参与） | 内容压在父面板页签下 |
| **GL2 区域几何** | fixed / percentage / flex / replaced_by_host 按 `references/layout-geometry.md` 推导；先做区域清单比对 | 详情栏 860 vs demo 628；列表 170 vs 112 |
| **GL3 文本适配** | 按 demo 的 nowrap / 换行 / ellipsis 意图判行数与裁切 | 收窄后副标题折行 |
| **GL4 元素适配** | 行/列/网格由父区域和 gap 推导；图标/格子比例；整行放得下 | 34px 图标塞进 56px 格子；行溢出 |
| **GL5 媒体适配** | 按 demo 的 stretch / crop / contain 意图判 fit 模式 | 应裁切却全图拉伸 |

推导规则、容差、四类页面适配与示例见 **`references/layout-geometry.md`**。GL1/GL2/GL3/GL5 失败，或 GL4 导致溢出/重叠/裁切 → `runtime_failed_related`；GL4 纯高度/尺度差记 P2，可豁免。不能用「没重叠」代替。

**数据为空时先垫再验（硬规则）**：页面因服务器数据或配置表缺失而展示为空时，**空页面不算通过**。先按 `references/mock-data-shim.md` 的「空内容页面」垫最小测试数据 → 刷新/重开 → 在有数据状态下做 4a/4b/4c → 验证后清理。垫不出合法数据 → `blocked_precondition`，报告写 `empty_state=blocked`。

---

## 执行流程（六步）

| 步骤 | 做什么 | 按需读取 | 产出 |
|---|---|---|---|
| 1 | 读 TC、实施清单、设计文档、demo 源码 | — | TC 原始清单 |
| 2 | TC 分类（1 / 2a-struct / 2a-interact / 2b / 3） | `references/tc-classification.md` | 分类结果 |
| 3 | 静态验证类型 1 | `references/static-validation.md` | 静态结论 + 证据 |
| 4 | 提取交互契约：demo 每个交互点 → 期望组件/操作/反馈 + handler 级安全分级；同时提取布局基准（一级区域固定宽/占比、宿主内容区） | `references/interaction-contract.md` | 交互契约表 + 布局基准表 + 覆盖率分母 |
| 5 | 运行时验证（**条件执行，批量**）：4a 配置断言（C1+C2+E1）→ **4c 布局几何对照（GL1~GL5，默认态，生成/修改过 Prefab 的面板必做）** → 4b 实际交互（C3） → 入口类 change 追加父面板链路（E2+E3） | `references/unity-runtime-verify.md`、`references/layout-geometry.md`、`references/mock-data-shim.md` | 逐面板结论 |
| 6 | 汇总报告 + 人工清单 | `references/report-template.md`、`references/manual-test-list.md` | `test-validate-report.md` |

**第 5 步是开关式的**：前置门禁不过就整步跳过，在报告首屏写 `runtime: skipped(reason)`，**不影响**第 3、4、6 步的产出。非 UI 的 change 完全不受影响。

**4c 复用同一 Play 会话和已打开的面板**：只量一级容器和关键单行文本（约 5~10 个矩形），不额外开面板、不改工程。

**第 4 步不能省。** 没有契约表就没有“该验哪些交互”的分母，4b 会退化成“看到什么点什么”，这正是之前只做了配置断言的原因。

---

## 前置门禁（运行时 + 入口 + 布局）

| 门禁 | 检查 | 不满足时 |
|---|---|---|
| **G0 能力预检** | MCP 连通 + 关键工具可调用 + `EventSystem`/`GraphicRaycaster` 存在 | 无 MCP → `runtime: skipped(blocked_tooling)`；有 MCP 但无交互链 → 只做 4a，4b 全 blocked |
| **G1 身份** | Unity 连接指向 `config.yaml` 里的 SE 工程 | **立即停止所有 Unity 操作**（防误操作别的工程） |
| **G2 编译基线** | 真实编译后无有效 error | `runtime: skipped(compile_not_passed)` |
| **G3 可运行** | 无编译错误、非导入中、可进 Play | `runtime: skipped(editor_not_ready)` |
| **G4 进入主游戏** | 优先复用现场；必要时直接发命令；包装工具最多 2 次 | 该批次 `blocked_precondition` / `blocked_tool_lock` / `blocked_game_assert` |
| **G5 目标面板** | UIDataTable 有 UIID，Prefab 存在，入口级别已确定 | 该面板 `blocked`，其余面板继续 |
| **G6 入口链路** | change 是否新增/修改页签或入口；是则必须走父面板链路 | 只做 L2/L3 注入 → `entry_verified=false`，该 change **直接 `not_passed`** |
| **G7 布局基线** | 生成/修改过 Prefab 的页面：已拿到 demo 几何基准；Game View 已切到设计分辨率 `Full HD (1920x1080)`；调试浮层已关闭 | 无法切到设计分辨率时，至少 16:9、≥1280×720，y 轴降级；布局判定降为 `inconclusive`，不能判 passed |
| **S0 安全分级** | 4b 开始前，契约表每一行的 `安全` 列已填 | 未分级项按 `unsafe` 处理，不许执行 |

`touches_entry` 从 design/tasks 判定：涉及页签、入口卡片/按钮、父面板过滤或入口 func 配置的改动记为 `true`，并在报告第 2 节记录。

没有可信编译基线，**不给 `runtime_passed`**，最多 `inconclusive`。

---

## 批处理规则（多个界面一口气验完）

同一 change 的可运行时验证面板，**一次 Play 会话内全部验完**：

```
准备一次（G0~G4）
→ 逐面板：打开（按入口级别） → 稳定 → mock（空数据页面必做） → 采证 → 4a 配置断言 → 4c 布局几何（默认态，生成/修改过 Prefab 的面板） → 4b 实际交互 → 清理 mock → 关闭 → 基线核对
→ 收尾一次（退出 Play）
```

**批次选型**：

- 开始前先把**面板清单**写进报告；中途环境崩了能说清验到第几个
- 同账号/同等级/同前置的面板放同一批；前置不同的拆批次
- 同一面板的所有 safe 交互点必须在同一批次内一次做完，不要分多次开面板
- **单个面板失败不终止整批**；只有环境级故障（Play 崩、MCP 断、编译失败）才终止
- 面板之间必须隔离：恢复 mock 快照 → 关闭面板 → `ui-list-opened-panels` 回到基线；未回基线时下一面板标 `isolation_warning`，断言降为 `inconclusive`
- Console 不能 clear，按面板打标记日志分段归因
- **视觉判定前先确认 Game View ≥1280×720，并关闭调试浮层**：GM `debugpage 0`（或隐藏 `UIRoot/RootCanvas/PanelRoot/ShellDebugInfo(Clone)`）。该浮层的 `FPS/OC/ME/MDC` 文本默认压在左上角，会被误看成页签/列表重叠
- **4c 布局几何**：在状态改变型 4b **之前**量默认态（必要时先恢复默认页签/滚动位置并 `ForceUpdateCanvases`）；先把 Game View 切到设计分辨率 `Full HD (1920x1080)`（记录切换前后尺寸，批次结束恢复），再量宿主内容区与页面一级容器；截图 1920×1080、`debugpage 0`，与 demo 同尺寸并排。无法切到设计分辨率时按 G7 降级。
- 小窗口下中文像方块是采样伪影，不是字体缺陷

**入口按证明力选，能高不低**（活动页和页签/入口页都适用）：

| 级别 | 入口 | 证明力 |
|---|---|---|
| L0 | 真实点击主界面入口（活动图标 / 冒险按钮） | `entry=real`，`entry_verified=true` |
| L1 | GM 打开 | `entry=gm`，`entry_verified=true` |
| L1.5 | 父面板链路：打开父入口面板 → 调真实卡片/入口 handler → 点目标页签 | `entry=parent_chain_click`，`entry_verified=true` |
| L2 | 反射设 `m_MenuData` + `OpenPageUI`（**不调 `SetActivity`**） | `entry=synthetic_setactivity`，`entry_verified=false` |
| L3 | `ui-open` 强开 | `entry=injected_ui_open`，`entry_verified=false` |

`SetActivity` 会 `RecordRedPoint()` 写本地存档，**禁止用于注入**。L2/L3 必须把“真实入口未验证”写进人工清单。

**例外：新增/修改页签或入口的 change，L2/L3 不可接受。** 这类 change 必须走到 L1.5 或更高；`ui-open` 会绕过父面板的页签过滤，页内全过也证明不了用户能进来。判法见 G6。

细节见 `references/unity-runtime-verify.md`。

---

## 判定口径

| 判定 | 含义 |
|---|---|
| `static_passed` / `static_failed` | 类型 1 的静态结论 |
| `runtime_passed` | 门禁通过 + C1/C2/C3 覆盖全部 safe 交互点 + critical 全做 + Console 无 related/unknown + 生成/修改过 Prefab 的面板已完成 4c（GL1/GL2 有实测值，GL3/GL4/GL5 有结论或显式 `not_applicable`） |
| `runtime_passed_mock` | 同上，但数据来自 mock；**不得写成 `runtime_passed`** |
| `runtime_failed_related` | 发现本功能问题（含类型错、行为不符、射线不可达、布局几何偏差） |
| `runtime_partial_unsafe` | 其余全过，但存在 unsafe 交互无法执行 |
| `runtime_interaction_incomplete` | safe 项未做 C3，或 critical（滚动/切换/安全按钮/关闭）有缺 |
| `runtime_config_only` | 只做了 C1/C2，**未做任何 C3** |
| `runtime_visual_review_needed` | 结构/交互/布局通过，颜色或美术资源待人工 |
| `runtime_blocked_precondition` | 账号/场景/数据/配置导致验不了 |
| `runtime_blocked_tooling` | 缺少读字段/截图/交互/日志能力 |
| `runtime_inconclusive` | 有证据但不足以判定（如缺编译基线、isolation 污染、交互抛异常） |
| `runtime_skipped(reason)` | 门禁未过，整步没跑 |
| `manual` / `integration` | 归入人工或联调清单 |

4c 未做或没有实测值的 Prefab 面板最多 `runtime_inconclusive`，不得判 `runtime_passed` / `runtime_passed_mock`。

**同一面板取最严重者**：

```
skipped > blocked_tooling > blocked_precondition > failed_related
        > interaction_incomplete > partial_unsafe > inconclusive
        > config_only > visual_review_needed > passed_mock > passed
```

**change 级结论**：只有全部面板为 `passed` / `passed_mock` / `visual_review_needed` 才是 `passed`；出现任一 `failed` 或未覆盖态即 `not_passed`；全部 blocked 才是 `blocked`。**`runtime_config_only` 永远不算 passed。**

**入口类 change 额外规则**：change 新增/修改页签或入口时，`entry_verified=false` 一律 `not_passed`，即使所有面板页内通过。

**布局几何规则**：GL1/GL2/GL3/GL5 失败，或 GL4 导致溢出/重叠/裁切 → `runtime_failed_related`，缺陷类型 `visual_layout_mismatch`；GL4 纯高度/尺度差记 P2，可 `waived`。`runtime_visual_review_needed` 只覆盖颜色/美术资源，不覆盖布局。

**禁止**把 `inconclusive` / `skipped` / `config_only` 写成“通过”；**禁止**把 GM/注入打开面板说成“真实入口已验证”。

---

## 四条安全红线

1. **mock 只在本次 Play 内存里**：不落库、不写 `PlayerPrefs`/`LocalPlayerConfig`/本地存档、不触发发协议的操作
2. **unsafe 交互一律不执行**：按 handler 分级，追不到 handler 就判 unsafe；禁止 `onClick.Invoke()` 伪造点击，必须走 `ExecuteEvents`
3. **不改工程**：不改客户端/服务端代码、不改配置表、不改 Prefab；发现问题只报告
4. **身份不匹配立即停**：G1 不过就停止所有 Unity 写操作

---

## 发现问题后

- **只验证，不修复**；不自动触发 `/lr-openspec-apply`，不自动改 `tasks.md` / `design.md` / Prefab
- 按 `P0 / P1 / P2 / unrelated` 分级，按 `client / config / design / environment` 定责
- 交互类缺陷必须区分断点：`component_missing` / `component_type_mismatch` / `interaction_unavailable` / `interaction_behavior_mismatch` / `unreachable_interaction` / `unmapped_interaction` / `interaction_semantic_mismatch`
- 布局几何类缺陷统一记 `visual_layout_mismatch`，子类写清：`host_inset_missing` / `region_ratio_mismatch` / `text_wrap_regression` / `element_scale_mismatch` / `image_aspect_distortion`
- 每条缺陷固化：现象、预期、实际、证据（节点路径/组件实例/截图/Console 原文）、复现步骤、建议
- 支持 `waived`（用户确认豁免），复验时不再阻断
- 修复后由用户**显式重新触发**本技能，做**增量复验**；证据必须刷新；连续 3 轮仍不通过则停止并升级

发现断点在 prefab 生成侧时，**只在报告里建议用户显式触发 `/lr-openspec-ui-prefab`**，不要自己串过去。

细节见 `references/report-template.md` 的缺陷清单部分。

---

## 报告契约

一份 `changes/<id>/test-validate-report.md`，必须包含（顺序固定）：

1. 摘要（总数 / 静态 / 运行时 / 人工 / 联调 + 最高严重度 + change 级结论 `passed|not_passed|blocked`）
2. **环境与基线**（project identity、compile_result、playmode、能力矩阵、`data_source`、`entry`、`entry_verified`、`entry_chain`、`empty_state`、`empty_reason`、`layout_baseline`、`view_resolution`、`view_aspect`、`canvas_size`、`view_size_before`、`view_size_restored`、`runtime`、`cleanup`）——`skipped` 必须在首屏可见
3. 静态验证详情
4. 运行时批次总览 + 逐面板详情（每面板必须有 `safe_c3_done / safe_total`、`unsafe_total`、`critical_done`）+ 4.4 入口链路（`touches_entry=true` 时必填）+ 4.5 布局几何对照（生成/修改过 Prefab 的面板必填：按 `references/layout-geometry.md` 的表格，含类型/期望表达式/容差/严重度/waived）
5. **交互契约对齐**：契约表（demo 证据 → 期望组件 → C1/C2/C3 结论）+ 覆盖率 + 未映射交互 + 反向扫描 + 射线可达 + 语义复核
6. Mock 数据附录（注入了什么、`mock_level`、覆盖状态、清理结果、局限；空内容页面单列 `empty_state` 与 `empty_reason`）
7. Console 归因（related / unrelated / unknown）
8. 缺陷清单（级别、定责、类型、状态、证据）
9. 人工测试清单（2b + 3 + unsafe + entry_unverified + empty_data_unverified，已扣除运行时覆盖项）
10. 未验证项与缺口（`interaction_unsupported`、`manual_review_required`、布局基线缺失、空数据未垫、能力缺口）

**第 5 节不能是空表。** 没有契约表的运行时报告视为不合格——它无法证明交互被验过。

完整模板见 `references/report-template.md`。

---

## 上下游接口

- **读**：`test-cases.md`、`implementation-report.md`、`tasks.md`、`design.md`、`demo/src/**`
- **写**：只写 `test-validate-report.md`
- **不写**：源码、配置、Prefab、`tasks.md`、`design.md`
- **下一步**：修复由用户显式触发 `/lr-openspec-apply`；复验由用户显式再次触发本技能。**本技能跑完即停，不自动串任何后续 Skill。**

---

## 版本信息

**版本**：v2.5（4c 升级为通用布局几何契约：fixed/percentage/flex 推导、四类页面适配、设计分辨率 1920×1080、媒体 fit 模式、豁免与未知项；v2.4 的空内容先垫数再验、v2.3 的视觉取证、v2.2 的入口链路保持不变）
**依赖工具**：ai-game-developer MCP（Unity 插件）
**依赖文档**：`schemas/lr-func-dev/rules/common/unity-ui-mcp.md`（工程身份与 MCP 约定）
