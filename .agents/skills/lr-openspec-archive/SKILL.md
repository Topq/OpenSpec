---
name: lr-openspec-archive
description: 归档已完成的变更，合并 specs delta 到主规范，移动变更目录到 archive（封装 openspec archive 命令）
---

# Codex 适配器

完整读取并严格执行 `../../../.claude/skills/lr-openspec-archive/SKILL.md`。

- 以 `.claude/skills/lr-openspec-archive/` 为原始 Skill 根目录解析其中的相对路径。
- 将 `Read`、`Grep`、`Glob`、`Bash`、`Write`、`Edit` 等 Claude 工具表述映射到当前可用工具。
- 在面向 Codex 用户展示调用方式时，将 `/lr-openspec-archive` 写为 `$lr-openspec-archive`。
- 原始 Skill 执行完成后停止，不自动启动后续 Skill。
