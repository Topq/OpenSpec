---
name: lr-openspec-sync
description: 同步代码改动到 design.md（可选 tasks.md），扫描协议参数/Record字段/配置字段/UI组件差异，生成回写建议供人工勾选后自动回写
---

# Codex 适配器

完整读取并严格执行 `../../../.claude/skills/lr-openspec-sync/SKILL.md`。

- 以 `.claude/skills/lr-openspec-sync/` 为原始 Skill 根目录解析其中的相对路径。
- 将 `Read`、`Grep`、`Glob`、`Bash`、`Write`、`Edit` 等 Claude 工具表述映射到当前可用工具。
- 在面向 Codex 用户展示调用方式时，将 `/lr-openspec-sync` 写为 `$lr-openspec-sync`。
- 原始 Skill 执行完成后停止，不自动启动后续 Skill。
