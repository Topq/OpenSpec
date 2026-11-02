---
name: lr-openspec-design
description: 触发 lr-func-dev schema 的三端技术设计文档生成。极简触发器，只负责调用 OpenSpec 原生指令，所有设计逻辑在 schema.yaml 和 rules/*.md 中。
---

# Codex 适配器

完整读取并严格执行 `../../../.claude/skills/lr-openspec-design/SKILL.md`。

- 以 `.claude/skills/lr-openspec-design/` 为原始 Skill 根目录解析其中的相对路径。
- 将 `Read`、`Grep`、`Glob`、`Bash`、`Write`、`Edit` 等 Claude 工具表述映射到当前可用工具。
- 在面向 Codex 用户展示调用方式时，将 `/lr-openspec-design` 写为 `$lr-openspec-design`。
- 原始 Skill 执行完成后停止，不自动启动后续 Skill。
