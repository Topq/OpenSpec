---
name: lr-openspec-test-validate
description: 测试用例覆盖分析与验证。静态验证逻辑类 TC；通过 ai-game-developer MCP 在真实 Unity 中批量验证 UI 结构、字段绑定、状态，并按 demo 交互契约逐项验证组件类型、能力与实际操作（滚动/点击/切换/关闭）；数据缺失可临时模拟并在验证后清理；无法自动验证的输出人工/联调清单。
---

# Codex 适配器

完整读取并严格执行 `../../../.claude/skills/lr-openspec-test-validate/SKILL.md`。

- 以 `.claude/skills/lr-openspec-test-validate/` 为原始 Skill 根目录解析其中的相对路径。
- 将 `Read`、`Grep`、`Glob`、`Bash`、`Write`、`Edit` 等 Claude 工具表述映射到当前可用工具。
- 将 `mcp__ai-game-developer__*` 一类 MCP 工具调用映射到当前可用的 Unity MCP 工具；能力不足时按 SKILL.md 的降级规则记录，不跳过。
- 在面向 Codex 用户展示调用方式时，将 `/lr-openspec-test-validate` 写为 `$lr-openspec-test-validate`。
- 原始 Skill 执行完成后停止，不自动启动后续 Skill。
