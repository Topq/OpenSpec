---
name: lr-openspec-code-review
description: 按框架约定清单检查代码质量（协议契约、框架注册、Module 数据边界、红点归属、错误反馈、刷新粒度、过度设计、Localizer），按 P0/P1/P2 权重输出审查报告
---

# Codex 适配器

完整读取并严格执行 `../../../.claude/skills/lr-openspec-code-review/SKILL.md`。

- 以 `.claude/skills/lr-openspec-code-review/` 为原始 Skill 根目录解析其中的相对路径。
- 将 `Read`、`Grep`、`Glob`、`Bash`、`Write`、`Edit` 等 Claude 工具表述映射到当前可用工具。
- 在面向 Codex 用户展示调用方式时，将 `/lr-openspec-code-review` 写为 `$lr-openspec-code-review`。
- 原始 Skill 执行完成后停止，不自动启动后续 Skill。
