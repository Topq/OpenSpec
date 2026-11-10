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
entry:                real | gm | synthetic_setactivity | injected_ui_open | n/a
entry_verified:       true | false
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
| 1 | | | | real / gm / L2 / L3 | | |

### 4.2 批次总览

| 面板 | entry | entry_verified | data_source | 4a | 4b | 判定 | 缺陷数 | cleanup |
|---|---|---|---|---|---|---|---|---|
| | | | | pass/fail | 3/5 | | | |

**批次结论**：已验 N / 通过 M / failed X / blocked Y
**环境级故障**：无 / ...
**isolation**：clean / warning（说明）

### 4.3 逐面板详情

#### 面板名

- 入口方式：真实入口 / GM / 合成菜单数据 / ui-open（**L2/L3 必须写 `entry_verified=false`**）
- 结构断言：
- 字段绑定断言（C1）：serialized N 项 / runtime_bound M 项 / 类型不符 K 项，逐项证据
- 状态断言：
- **4a 配置断言**：滚动 / 点击 / 切换 / 面板级，逐项 pass/fail
- **4b 实际交互**：
  - 覆盖率：`safe_c3_done=?/?`，`unsafe_total=?`，`critical_done=?/?`
  - 逐项：交互 → 操作方式（click / drag / toggle / close）→ 断言值 → 结论
- 视觉：
- 截图：
- Console：
- 判定：
- 清理：

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
- `entry_unverified`（L2/L3 打开）：N 个面板

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

---

## 9. 人工测试清单

> 已扣除运行时覆盖 N 项。

（按 `manual-test-list.md` 格式输出）

---

## 10. 未验证项与缺口

| 项 | 原因 | 建议 |
|---|---|---|
| 配置表→Module 映射 | 表为空（前置任务未执行） | 完成导表后复验 |
| 真实活动入口 | 仅 L2/L3 打开，`entry_verified=false` | 人工从主界面进入复验 |
| unsafe 交互（购买/领取） | 规则禁止执行 | 人工/联调 |
| 交互语义复核 | 自动判定不可靠 | 人工对照 demo |
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
