---
name: lr-openspec-design
description: 触发 lr-func-dev schema 的三端技术设计文档生成。极简触发器，只负责调用 OpenSpec 原生指令，所有设计逻辑在 schema.yaml 和 rules/*.md 中。
---

# OpenSpec Design 生成器（极简触发器）

## 角色与目标

面向技术评审阶段。输入是策划侧已完成的 proposal + specs delta（来自 `/lr-design`），输出是前后端工程师和策划联合评审用的三端 design 文档。

**本 SKILL 只是 OpenSpec 原生指令的触发器**，所有设计逻辑在 `schemas/lr-func-dev/schema.yaml` 和 `schemas/lr-func-dev/rules/*.md` 中定义。

---

## 使用方式

```bash
/lr-openspec-design <change-id>
```

**示例**：
```bash
/lr-openspec-design growth-fund
```

---

## 前置条件检查

执行前必须确认以下文件存在：

| 文件 | 来源 | 检查命令 |
|-----|------|---------|
| `changes/<id>/proposal.md` | `/lr-design` 生成 | `ls changes/<id>/proposal.md` |
| `changes/<id>/specs/**/*.md` | `/lr-design` 生成 | `ls changes/<id>/specs/` |
| `changes/<id>/demo/*.html` | `/lr-design` 生成 | `ls changes/<id>/demo/` |

**若文件不存在**：
```
❌ 错误：缺少必要输入文件

design 生成依赖 proposal.md 和 specs/*.md，但未找到这些文件。

请先运行 /lr-design <id> 生成这些文件。
```

---

## 执行流程

### 步骤 1：生成 design-client.md

```bash
openspec instructions design-client --change <id>
```

执行 OpenSpec 返回的 `<instruction>` 块中的所有指令。

**产物**：`changes/<id>/design/client.md`

---

### 步骤 2：生成 design-server.md

```bash
openspec instructions design-server --change <id>
```

执行 OpenSpec 返回的 `<instruction>` 块中的所有指令。

**产物**：`changes/<id>/design/server.md`

---

### 步骤 3：生成 design-config.md

```bash
openspec instructions design-config --change <id>
```

执行 OpenSpec 返回的 `<instruction>` 块中的所有指令。

**产物**：`changes/<id>/design/config.md`

---

### 步骤 4：验证生成结果

```bash
openspec validate <id>
```

**若验证失败**：
- 检查错误输出
- 修正对应的 design/*.md 文件
- 重新运行 `openspec validate <id>` 直到通过

---

## 输出摘要

生成完成后，输出摘要：

```text
✅ Design 文档生成完成

变更名: <id>
产物:
  - changes/<id>/design/client.md
  - changes/<id>/design/server.md
  - changes/<id>/design/config.md

验证状态: ✅ 通过 / ❌ 失败（见错误详情）

下一步:
1. 技术评审：前后端工程师 + 策划联合评审 design/*.md
2. 评审通过后，生成任务列表：openspec instructions tasks --change <id>
```

---

## 设计逻辑说明

**本 SKILL 不包含任何设计逻辑**，所有逻辑在以下文件中定义：

| 文件 | 职责 |
|-----|------|
| `schemas/lr-func-dev/schema.yaml` | artifact 定义、instruction 模板、验证规则 |
| `schemas/lr-func-dev/rules/design/client-structure.md` | 客户端设计文档结构规则 |
| `schemas/lr-func-dev/rules/design/server-structure.md` | 服务端设计文档结构规则 |
| `schemas/lr-func-dev/rules/design/config-structure.md` | 配置表设计文档结构规则 |

**为什么这样设计？**
1. ✅ **单一真相来源**：设计逻辑只在 schema.yaml 中维护，不重复
2. ✅ **维护成本低**：SKILL 只是触发器，无需同步更新
3. ✅ **符合 OpenSpec 哲学**：利用 OpenSpec 原生机制，不重复发明轮子

---

## 与旧版本的差异

**旧版本**（已废弃）：
- SKILL 中包含大量设计逻辑和代码模板
- 与 schema.yaml 的逻辑重复
- 维护成本高（两处都要改）

**新版本**（当前）：
- SKILL 只是触发器，调用 OpenSpec 原生指令
- 所有设计逻辑在 schema.yaml 和 rules/*.md 中
- 维护成本低（只改一处）

---

## 常见问题 FAQ

### Q1: 如果生成的 design 文档不符合预期怎么办？

**A**: 修改对应的规则文件：
- 客户端设计问题 → 修改 `schemas/lr-func-dev/rules/design/client-structure.md`
- 服务端设计问题 → 修改 `schemas/lr-func-dev/rules/design/server-structure.md`
- 配置表设计问题 → 修改 `schemas/lr-func-dev/rules/design/config-structure.md`

然后重新运行 `/lr-openspec-design <id>`

---

### Q2: 如何查看 OpenSpec 的 instruction 内容？

**A**: 运行命令后，查看输出的 `<instruction>` 块，里面包含了 AI 应该执行的所有指令。

---

### Q3: 为什么不把设计逻辑放在 SKILL 里？

**A**: 
1. 设计逻辑在 schema.yaml 中定义，是 OpenSpec 的标准做法
2. 避免重复维护（SKILL 和 schema.yaml 两处都要改）
3. 规则文件支持 Pre-flight Check、CodeGraph 查询等高级功能，SKILL 很难实现

---

## 版本信息

**版本**: v2.0 (极简触发器)  
**更新日期**: 2026-07-22  
**设计哲学**: SKILL 只负责触发，逻辑在 schema.yaml 中
