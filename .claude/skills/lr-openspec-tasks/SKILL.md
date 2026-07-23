---
name: lr-openspec-tasks
description: 触发 lr-func-dev schema 的设计合并门禁、验收用例生成、实现任务生成。极简触发器，所有逻辑在 schema.yaml 中。
---

# OpenSpec Tasks 生成器（极简触发器）

## 角色与目标

面向技术评审完成后的阶段。输入是已评审的三端设计文档，输出是：
1. **design.md**（合并后的完整设计，含 Open Questions 门禁检查）
2. **test-cases.md**（验收测试用例）
3. **tasks.md**（实现任务清单）

**本 SKILL 只是 OpenSpec 原生指令的触发器**，所有逻辑在 `schemas/lr-func-dev/schema.yaml` 和 `schemas/lr-func-dev/rules/*.md` 中定义。

---

## 使用方式

```bash
/lr-openspec-tasks <change-id>
```

**示例**：
```bash
/lr-openspec-tasks growth-fund
```

---

## 前置条件检查

执行前必须确认以下文件存在：

| 文件 | 来源 | 检查命令 |
|-----|------|---------|
| `changes/<id>/design/client.md` | `/lr-openspec-design` 生成 | `ls changes/<id>/design/client.md` |
| `changes/<id>/design/server.md` | `/lr-openspec-design` 生成 | `ls changes/<id>/design/server.md` |
| `changes/<id>/design/config.md` | `/lr-openspec-design` 生成 | `ls changes/<id>/design/config.md` |
| `changes/<id>/specs/**/*.md` | `/lr-design` 生成 | `ls changes/<id>/specs/` |

**若文件不存在**：
```
❌ 错误：缺少必要输入文件

tasks 生成依赖三端设计文档，但未找到这些文件。

请先运行：
1. /lr-design <id>（生成 proposal + specs）
2. /lr-openspec-design <id>（生成三端设计）
3. 技术评审三端设计文档
4. 再运行 /lr-openspec-tasks <id>
```

---

## 执行流程

### 步骤 1：设计合并门禁（阶段 6）

```bash
openspec instructions design --change <id>
```

**功能**（由 schema.yaml 定义）：
1. **Open Questions 检查**（阻断性）
   - 检查三端设计的 Open Questions 是否全部解决
   - 检查回答质量：禁止模糊词汇、类型定义要求、处理策略要求
   - 若检查失败 → 阻断，输出错误详情

2. **跨文档对齐检查**（阻断性）
   - Record 表定义对齐（表名、列名、类型）
   - 协议定义对齐（协议号、参数）
   - 配置表定义对齐（表名、字段名、类型）
   - 若检查失败 → 阻断，输出差异详情

3. **合并生成 design.md**
   - 精简架构叙事（Context/Goals/Decisions/Risks）
   - 完整附录（附录 A：客户端详细设计、附录 B：服务端详细设计、附录 C：配置表详细设计）

**若门禁检查失败**：
```
❌ Open Questions 检查失败

design/client.md:
  - Q1: 回答包含"待定"（模糊词汇）
  - Q2: 缺少类型定义

design/server.md:
  - Q3: 回答包含"先这样"（模糊词汇）

请修正后重新运行。
```

**产物**：`changes/<id>/design.md`

---

### 步骤 2：验收用例生成（阶段 7）

```bash
openspec instructions test-cases --change <id>
```

**功能**（由 schema.yaml 定义）：
- 从 specs/*.md 和 design.md 生成验收测试用例
- 每条用例包含：编号、前置条件、操作步骤、预期结果
- 编号格式：`TC-{spec目录名}-{两位序号}`（如 `TC-growth-fund-purchase-01`）

**产物**：`changes/<id>/test-cases.md`

---

### 步骤 3：实现任务生成（阶段 8）

```bash
openspec instructions tasks --change <id>
```

**功能**（由 schema.yaml 定义）：
- 从 design.md 生成前后端和配置表的实现任务
- 任务拆分遵循粒度规则（30 分钟 ~ 2 小时，50 ~ 200 行代码）
- 验证性任务引用 test-cases.md 的用例编号

**产物**：`changes/<id>/tasks.md`

---

### 步骤 4：验证生成结果

```bash
openspec validate <id>
```

**若验证失败**：
- 检查错误输出
- 修正对应的文件
- 重新运行 `openspec validate <id>` 直到通过

---

## 输出摘要

生成完成后，输出摘要：

```text
✅ Tasks 生成完成

变更名: <id>

产物:
  - changes/<id>/design.md（合并后的完整设计）
  - changes/<id>/test-cases.md（验收用例，N 条）
  - changes/<id>/tasks.md（实现任务，客户端 X 个，服务端 Y 个，配置表 Z 个）

验证状态: ✅ 通过 / ❌ 失败（见错误详情）

下一步:
1. 审查 tasks.md，确认任务拆分合理
2. 执行代码生成：openspec apply <id>
```

---

## 设计逻辑说明

**本 SKILL 不包含任何设计逻辑**，所有逻辑在以下文件中定义：

| 文件 | 职责 |
|-----|------|
| `schemas/lr-func-dev/schema.yaml` | artifact 定义、门禁检查规则、合并规则 |
| `schemas/lr-func-dev/rules/tasks/client-implementation.md` | 客户端任务拆分规则 |
| `schemas/lr-func-dev/rules/tasks/server-implementation.md` | 服务端任务拆分规则 |
| `schemas/lr-func-dev/rules/tasks/config-implementation.md` | 配置表任务拆分规则 |

---

## 与旧版本的差异

### 旧版本（已废弃）

- SKILL 包含设计合并逻辑
- SKILL 包含 Open Questions 检查逻辑
- SKILL 包含任务拆分逻辑
- 需要先运行 `/lr-openspec-design-merge`（独立 SKILL）

### 新版本（当前）

- SKILL 只是触发器，调用 OpenSpec 原生指令
- 所有逻辑在 schema.yaml 中
- 设计合并门禁（阶段 6）已集成到 `openspec instructions design`
- 无需独立的 `lr-openspec-design-merge` SKILL

---

## 与 lr-openspec-design-merge 的关系

**lr-openspec-design-merge 已废弃**，其功能已完全集成到 OpenSpec 的 `design` artifact（阶段 6：设计合并门禁）中。

**原 lr-openspec-design-merge 的功能**：
1. ✅ Open Questions 检查 → 已集成到 `openspec instructions design`
2. ✅ 回答质量检查 → 已集成到 `openspec instructions design`
3. ✅ 跨文档对齐检查 → 已集成到 `openspec instructions design`
4. ✅ 合并生成 design.md → 已集成到 `openspec instructions design`

**新流程**：
```
/lr-openspec-design <id>
  ↓
技术评审（人工）
  ↓
/lr-openspec-tasks <id>
  ↓ 自动调用 openspec instructions design（含门禁检查）
  ↓ 自动调用 openspec instructions test-cases
  ↓ 自动调用 openspec instructions tasks
  ↓
design.md + test-cases.md + tasks.md
```

---

## 常见问题 FAQ

### Q1: 如果 Open Questions 检查失败怎么办？

**A**: 修改对应的 design/*.md 文件，解决所有 Open Questions，然后重新运行 `/lr-openspec-tasks <id>`。

门禁检查会告诉你哪些问题未解决、哪些回答质量不合格。

---

### Q2: 为什么要合并三端设计为 design.md？

**A**: 
1. 避免后续步骤（tasks 生成、apply 执行）重复读取三个文件
2. 强制执行 Open Questions 门禁检查
3. 提供精简的架构叙事（Context/Goals/Decisions/Risks）供评审和查阅

---

### Q3: 如果生成的 tasks 不符合预期怎么办？

**A**: 修改对应的规则文件：
- 客户端任务问题 → 修改 `schemas/lr-func-dev/rules/tasks/client-implementation.md`
- 服务端任务问题 → 修改 `schemas/lr-func-dev/rules/tasks/server-implementation.md`
- 配置表任务问题 → 修改 `schemas/lr-func-dev/rules/tasks/config-implementation.md`

然后重新运行 `/lr-openspec-tasks <id>`

---

### Q4: 为什么不需要 lr-openspec-design-merge 了？

**A**: 
1. 设计合并门禁功能已集成到 OpenSpec 的 `design` artifact（阶段 6）
2. 所有检查逻辑在 schema.yaml 中定义，避免重复维护
3. 简化用户心智模型（少一个 SKILL）

---

## 版本信息

**版本**: v2.0 (极简触发器)  
**更新日期**: 2026-07-22  
**设计哲学**: SKILL 只负责触发，逻辑在 schema.yaml 中  
**废弃 SKILL**: lr-openspec-design-merge（功能已集成）
