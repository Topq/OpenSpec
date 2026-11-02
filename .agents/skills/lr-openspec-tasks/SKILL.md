---
name: lr-openspec-tasks
description: 触发 lr-func-dev schema 的设计合并门禁、验收用例生成、实现任务生成。极简触发器，所有逻辑在 schema.yaml 中。
---

# Codex 适配器

完整读取并严格执行 `../../../.claude/skills/lr-openspec-tasks/SKILL.md`。

- 以 `.claude/skills/lr-openspec-tasks/` 为原始 Skill 根目录解析其中的相对路径。
- 将 `Read`、`Grep`、`Glob`、`Bash`、`Write`、`Edit` 等 Claude 工具表述映射到当前可用工具。
- 在面向 Codex 用户展示调用方式时，将 `/lr-openspec-tasks` 写为 `$lr-openspec-tasks`。
- 原始 Skill 执行完成后停止，不自动启动后续 Skill。
