# test-validate-report.md 模板

> 顺序固定。`runtime: skipped(...)` 必须在第 2 节首屏可见，不能藏到附录。
> 第 5 节（交互契约对齐）**不能是空表**——空表等于交互没验。

```markdown
# Test Validation Report: <change-id>

**生成时间**：
**执行技能**：/lr-openspec-test-validate
**范围**：

---

## 1. 摘要

| 结果 | 数量 | 说明 |
|---|---|---|
| TC 总数 | | |
| 静态通过 | | |
| 静态未覆盖 | | |
| 运行时通过（含 mock） | | |
| 运行时失败/阻断 | | |
| 交互点总数（safe + unsafe） | | |
| 已实际执行交互（C3） | | |
| 人工测试 | | |
| 联调测试 | | |

**最高严重度**：
**change 级结论**：passed / not_passed / blocked

> 只有全部面板为 `passed` / `passed_mock` / `visual_review_needed` 才能写 `passed`。
> `visual_review_needed` 只覆盖颜色/美术资源；布局几何必须验过 GL1~GL5。
> 生成/修改过 Prefab 的面板未完成 4c（无 GL1/GL2 实测）→ 最多 `inconclusive`，不得判 passed。
> 出现任一 `runtime_config_only` / `runtime_interaction_incomplete` / `runtime_partial_unsafe` 即为 `not_passed`。

---

## 2. 环境与基线

```
runtime:              passed | skipped(reason)
project_identity:
  expected:           <config.yaml 客户端路径>
  actual_dataPath:    <script-execute 结果>
  matched:            true/false
compile_result:       passed | failed_related | blocked | static_fallback
console_cleanup:      passed | blocked
playmode:             entered | reused | not_entered
login:                reused | direct_command | game-login | blocked
data_source:          real | gm | mock
mock_level:           - | gm | L3 | L4
touches_entry:        true | false
entry:                real | gm | parent_chain_click | synthetic_setactivity | injected_ui_open | n/a
entry_verified:       true | false
entry_chain:          verified | failed | not_applicable
empty_state:          none | injected | blocked（空内容页面是否垫数后复验）
empty_reason:         n/a | config_empty | player_data_empty | feature_locked
layout_baseline:      demo-styles | layout-contract.json | partial（4c 期望值来源；partial 表示有 expected_unknown）
view_resolution:      <宽>x<高>（默认 1920x1080）
view_aspect:          <例 16:9>
canvas_size:          <例 1920x1080>
view_size_before:     <切换前 Game View 尺寸>（批次后恢复）
debug_hud:            hidden | visible(ignored)（截图前应 `debugpage 0`）
cleanup:              restored | exited_play | failed | n/a
capability_matrix:
  script-execute:     ok / denied
  console:            ok / denied
  ui-api:             ok / degraded
  reflection:         ok / degraded
  component-get:      ok / degraded
  interaction-chain:  ok / degraded（EventSystem / GraphicRaycaster）
```

---

## 3. 静态验证详情

### ✅ TC-x 标题

- 验证方法：
- 代码位置：path:line
- 关键片段：
- 判定：通过 / 未覆盖 / 无法判定

### ❌ TC-y 标题

- 现象：
- 证据：
- 判定：
- 建议：

---

## 4. 运行时验证

### 4.1 面板批次清单

| # | 面板 | UIID | 目标 TC | 入口级别 | 数据来源 | 前置 |
|---|---|---|---|---|---|---|
| 1 | | | | real / gm / parent_chain / L2 / L3 | | |

### 4.2 批次总览

| 面板 | entry | entry_verified | data_source | 4a | 4b | 判定 | 缺陷数 | cleanup |
|---|---|---|---|---|---|---|---|---|
| | | | | pass/fail | 3/5 | | | |

**批次结论**：已验 N / 通过 M / failed X / blocked Y
**环境级故障**：无 / ...
**isolation**：clean / warning（说明）

### 4.3 逐面板详情

#### 面板名

- 入口方式：真实入口 / GM / 父面板链路 / 合成菜单数据 / ui-open（**L2/L3 必须写 `entry_verified=false`**）
- 结构断言：
- 字段绑定断言（C1）：serialized N 项 / runtime_bound M 项 / 类型不符 K 项，逐项证据
- 状态断言：
- **4a 配置断言**：滚动 / 点击 / 切换 / 面板级，逐项 pass/fail
- **4b 实际交互**：
  - 覆盖率：`safe_c3_done=?/?`，`unsafe_total=?`，`critical_done=?/?`
  - 逐项：交互 → 操作方式（click / drag / toggle / close）→ 断言值 → 结论
- **4c 布局几何（默认态，先于 4b 采集）**：GL1~GL5 结论，期望/实测见 4.5；截图必须 16:9、≥1280×720
- 视觉（先 `debugpage 0` 关闭调试浮层，`debug_hud=hidden`）：
- 布局相交检查：N 组，无相交 / 相交项（两个矩形 + 面积）
- 截图：
- Console：
- 判定：
- 清理：

### 4.4 入口链路（`touches_entry=true` 时必填）

| 环节 | 实际 | 断言 | 结论 |
|---|---|---|---|
| E1 入口 func 配置 | funcID / isOpen / IsOpenOnlyCheckCondition | 均为 true | pass/fail |
| E2 父面板页签 | 父面板 / 触发方式 / `leftTabs` | 包含目标 funcID | pass/fail |
| E3 点击页签 | 点击方式 / 目标页 / 当前页状态 | 目标页 active | pass/fail |

- `entry`：
- `entry_verified`：
- `entry_chain`：verified / failed / not_applicable
- 截图：
- Console：
- 结论：verified / failed / not_applicable

> `touches_entry=false` 写 `not_applicable`。为 true 时 `entry_verified=false` → change 级 `not_passed`，不能只进人工清单。

### 4.5 布局几何对照（生成/修改过 Prefab 的面板必填）

| 区域 | 类型 | demo 证据 | 期望表达式 | 期望(canvas) | 实测(canvas) | 偏差 | 容差 | 严重度 | 结论 |
|---|---|---|---|---|---|---|---|---|---|
| 宿主页签 | host | 父面板页签 x 13~333 | 页面起点 ≥ 354 | | | | 1% canvasW | P1 | pass/fail |
| 详情栏 | fixed | `.tc-detail width:628` | 右对齐：内容右 − 628 | | | | max(8px,1%W) | P1 | pass/fail/waived |
| 副本列表 | fixed | `.tc-dungeon-list width:112` | 左对齐：内容左 + 112 | | | | max(8px,1%W) | P1 | |
| 立绘 | flex | `.tc-art flex:1` | 内容区 − fixed − gap | | | | max(12px,2%W) | P2 | |
| 副标题 | text | demo nowrap | lineCount=1；文本框宽度按 GL2 容差核对 | | | | 0 行 | P1 | |
| 难度格 | grid | 约 56×66 | (内容宽−(n−1)gap)/n × 66 | | | | 宽度 1%W；高度 P2 | P1/P2 | |
| 立绘贴图 | media | SVG `slice`（裁切） | crop：uvRect 居中裁切或父级 Mask 裁切 | | | | fit 模式一致 | P1 | |

```
view_resolution:     1920x1080
view_aspect:         16:9
canvas_size:         1920x1080
debug_hud:           hidden
layout_baseline:     demo-styles | layout-contract.json | partial
view_size_restored:  true/false（批次后是否恢复原 Game View 尺寸）
screenshot:          1920x1080（与 demo 同尺寸并排）
```

- 期望值来源与推导：按 `references/layout-geometry.md`；fixed 1:1、percentage 相对父内容区、flex 吃剩余、replaced_by_host 不参与；内嵌页面按宿主实际占位，不按 demo 绝对 x 硬抄。
- GL1 只查一级内容容器；全屏 `Bg`、弹窗 `WindowBg` / 遮罩 / dimmer / 滚动条 / 装饰层不参与相交判定。
- 4c 在状态改变型 4b 之前采集默认态；4b 后补测必须先恢复默认页签与滚动位置并强制重建布局，否则记 `inconclusive`。
- fixed 失败时，flex 只记连带，不重复计缺陷；fixed 被 `waived` 后 flex 期望重算。
- GL1/GL2/GL3/GL5 失败，或 GL4 溢出/重叠/裁切 → 面板 `runtime_failed_related`，缺陷类型 `visual_layout_mismatch`；GL4 纯高度差 P2。
- 结论：pass / fail / waived / not_applicable（非 Prefab 页面）；`expected_unknown` 进第 10 节。

---

## 5. 交互契约对齐

### 5.1 契约表

| # | 区域 | demo 证据 | 期望操作 | 期望反馈 | prefab 路径 | 期望组件 | 安全 | C1 | C2 | C3 | 结论 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | safe/unsafe | | | | |

### 5.2 覆盖率

```
safe_c3_done:   ?/?
unsafe_total:   ?
critical_done:  ?/?（滚动 / 切换 / 安全按钮 / 关闭）
```

### 5.3 未映射与缺口

- `unmapped_interaction`（prefab 有、demo 没有）：N 项，逐项列出
- `interaction_unsupported`（demo 有、项目没有等价能力）：N 项，写明缺什么
- `unsafe` 未执行：N 项，进人工清单
- `entry_unverified`（L2/L3 打开）：N 个面板（入口类 change 为阻断项，不放人工清单）

### 5.4 反向扫描与射线

- 反向扫描：Selectable N / ScrollRect M / 未映射 K
- 射线不可达：N 项（写出最上层遮挡节点路径）

### 5.5 语义复核

- `manual_review_required`：N 项（组件与行为都对，但交互语义与 demo 不同）

---

## 6. Mock 数据附录

```
mock_level:
覆盖状态：
注入位置：
数值来源：
未覆盖：
empty_state:    none | injected | blocked
empty_reason:   n/a | config_empty | player_data_empty | feature_locked
有数据态复验：  已验 / 未验（原因）
cleanup:        restored | exited_play | failed
局限：不能证明 配置表→Module→UI 的映射
```

---

## 7. Console 归因

```
观察窗口：起止时间 / 面板标记
related:
unrelated:
unknown:
self_inflicted_tool_errors:
```

---

## 8. 缺陷清单

| ID | 级别 | 定责 | 类型 | TC | 状态 | 现象 |
|---|---|---|---|---|---|---|
| D-01 | P1 | client | component_type_mismatch | TC-x | open | |

### D-01 标题

- 现象：
- 预期：
- 实际：
- 证据：节点路径 / 组件实例 / 截图 / Console 原文
- 复现：
- 建议：
- 状态：open / fixed / verified / waived（豁免人+理由）

**分级**：P0 阻断 / P1 功能 / P2 质量 / unrelated
**定责**：client / config / design / environment

**交互类缺陷类型**（必须选一个，便于定位断点）：

| 类型 | 含义 | 通常定责 |
|---|---|---|
| `component_missing` | 该有的组件没有 | 生成器 / 配方 |
| `component_type_mismatch` | 组件类型不对 | 生成器 / 配方 |
| `interaction_unavailable` | 组件在但配置不可用（content 未绑等） | 生成配置 |
| `interaction_behavior_mismatch` | 操作后反馈不符 | 运行时代码 / prefab |
| `unreachable_interaction` | 被遮挡 / 射线不可达 | prefab 层级 |
| `unmapped_interaction` | prefab 多出 demo 没有的交互 | 待人工确认 |
| `interaction_semantic_mismatch` | 行为对但语义不同 | 设计 / 代码 |

**布局几何缺陷子类**（类型统一写 `visual_layout_mismatch`）：

| 子类 | 含义 | 通常定责 |
|---|---|---|
| `host_inset_missing` | 页面未按宿主内容区内缩 | prefab 生成 |
| `region_ratio_mismatch` | fixed/percentage 区域与 demo 偏差超容差 | prefab 生成 |
| `text_wrap_regression` | 宽度变更导致单行文案折行/截断 | prefab 生成 |
| `element_scale_mismatch` | 模板/图标/网格尺度不当，或导致溢出 | prefab 生成 |
| `image_aspect_distortion` | 应裁切/留白却拉伸，或 uvRect 未按 fit 模式裁切 | prefab 生成 |
| `missing_region` | demo 有一级区域，Unity 缺失 | prefab 生成 |
| `unmapped_region` | Unity 有 demo 没有的区域 | 设计确认 |

---

## 9. 人工测试清单

> 已扣除运行时覆盖 N 项。

（按 `manual-test-list.md` 格式输出）

---

## 10. 未验证项与缺口

| 项 | 原因 | 建议 |
|---|---|---|
| 配置表→Module 映射 | 表为空（前置任务未执行） | 完成导表后复验 |
| 真实入口 | 仅 L2/L3 打开，`entry_verified=false` | 人工从主界面进入复验；**入口类 change 不得放这里，直接判 `not_passed`** |
| unsafe 交互（购买/领取） | 规则禁止执行 | 人工/联调 |
| 交互语义复核 | 自动判定不可靠 | 人工对照 demo |
| 布局几何（GL1~GL5） | 期望表缺失或 Game View 不达标 | 补基线后复验 |
| 布局未知项（`expected_unknown`） | demo 使用 calc/百分比/min-max/媒体查询 | 人工按设计稿确认 |
| 有数据态展示 | 空数据且垫不出合法数据 | 人工准备数据后复验 |
| 视觉像素 | 需人眼 | 人工 |

---

## 复验记录

| 轮次 | 时间 | 修复项 | 复验结果 | 证据刷新 |
|---|---|---|---|---|
| 1 | | | | |
```

---

## 缺陷写作要求

- 一条缺陷只描述一个问题
- 必须有“预期 vs 实际”
- 证据至少包含：节点路径或代码位置 + 截图或 Console 原文
- 交互类缺陷必须标明 `C1/C2/C3` 哪一层失败，以及断点类型
- `mock_suspected` 的缺陷单列，不混进确认缺陷
- 用户豁免后状态改 `waived`，保留理由

## 报告自检

提交前逐项确认：

1. 第 5 节契约表非空，且每行都有 demo 证据
2. 每个面板写了 `safe_c3_done / safe_total` 与 `critical_done`
3. 没有把 `runtime_config_only` 写成 passed
4. L2/L3 打开的面板都标了 `entry_verified=false`
5. 没有 `unsafe` 交互被执行
6. mock 清理结果已写
7. 入口/页签类 change 有 4.4 `entry_chain` 段，且 `entry_verified=true`
8. 入口 func 做了 `isOpen` / `IsOpenOnlyCheckCondition` 断言
9. 视觉结论基于 >=1280x720 的 Game View，并记录了 `view_resolution`；截图前已 `debugpage 0` 关闭 `ShellDebugInfo`（`debug_hud=hidden`）
10. 列表/页签/容器做过兄弟 RectTransform 相交检查；相交面积为 0，或已作为缺陷记录
11. 生成/修改过 Prefab 的面板有 4.5 几何表（类型/期望表达式/容差/严重度），GL1/GL2 实测值齐全；Game View 为 1920×1080（或记录降级原因），截图与 demo 同尺寸
12. 空内容页面已垫数复验并清理；`empty_state`、`empty_reason` 与 `cleanup` 已写
