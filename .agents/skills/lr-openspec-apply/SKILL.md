---
name: lr-openspec-apply
description: 按角色过滤执行 tasks.md 任务（前端/后端/策划）。支持多角色组合，逐个执行，实时勾选，支持中断恢复。
---

# Codex 适配器

完整读取并严格执行 `../../../.claude/skills/lr-openspec-apply/SKILL.md`。

- 以 `.claude/skills/lr-openspec-apply/` 为原始 Skill 根目录解析其中的相对路径。
- 将 `Read`、`Grep`、`Glob`、`Bash`、`Write`、`Edit` 等 Claude 工具表述映射到当前可用工具。
- 在面向 Codex 用户展示调用方式时，将 `/lr-openspec-apply` 写为 `$lr-openspec-apply`。
- 原始 Skill 执行完成后停止，不自动启动后续 Skill。
