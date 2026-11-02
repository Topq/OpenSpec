---
name: lr-openspec-test-validate
description: 测试用例覆盖分析，静态验证逻辑类TC，生成人工测试清单（集成/联调类TC）
---

# Codex 适配器

完整读取并严格执行 `../../../.claude/skills/lr-openspec-test-validate/SKILL.md`。

- 以 `.claude/skills/lr-openspec-test-validate/` 为原始 Skill 根目录解析其中的相对路径。
- 将 `Read`、`Grep`、`Glob`、`Bash`、`Write`、`Edit` 等 Claude 工具表述映射到当前可用工具。
- 在面向 Codex 用户展示调用方式时，将 `/lr-openspec-test-validate` 写为 `$lr-openspec-test-validate`。
- 原始 Skill 执行完成后停止，不自动启动后续 Skill。
