---
name: lr-openspec-reconcile
description: 检查设计文档与实际代码的一致性（协议参数、Record结构、配置字段定义），输出差异报告供人工判定
---

# Codex 适配器

完整读取并严格执行 `../../../.claude/skills/lr-openspec-reconcile/SKILL.md`。

- 以 `.claude/skills/lr-openspec-reconcile/` 为原始 Skill 根目录解析其中的相对路径。
- 将 `Read`、`Grep`、`Glob`、`Bash`、`Write`、`Edit` 等 Claude 工具表述映射到当前可用工具。
- 在面向 Codex 用户展示调用方式时，将 `/lr-openspec-reconcile` 写为 `$lr-openspec-reconcile`。
- 原始 Skill 执行完成后停止，不自动启动后续 Skill。
