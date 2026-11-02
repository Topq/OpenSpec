---
name: lr-design
description: 灵刃策划案 → OpenSpec 变更(proposal + specs delta + React TypeScript 原型 demo)的策划侧闭环流程。只要用户给出飞书策划案链接,或提到"策划案审查""生成原型/demo""建 proposal""提变更""开需求"等意图,即使没有点名 openspec,也应使用本技能。覆盖:下载飞书策划案、完整性审查与对齐、生成带 Unity 组件标识的 React TypeScript 原型、策划验收,再触发 lr-func-dev schema 的 proposal/specs 产物并通过校验。不做 design.md 和 tasks.md(那是开发阶段的事,由同一 schema 的后续产物接手),不回写飞书。 SE UI 优先 ai-game-developer MCP。
---

# Codex 适配器

完整读取并严格执行 `../../../.claude/skills/lr-design/SKILL.md`。

- 以 `.claude/skills/lr-design/` 为原始 Skill 根目录解析其中的相对路径。
- 将 `Read`、`Grep`、`Glob`、`Bash`、`Write`、`Edit` 等 Claude 工具表述映射到当前可用工具。
- 在面向 Codex 用户展示调用方式时，将 `/lr-design` 写为 `$lr-design`。
- 原始 Skill 执行完成后停止，不自动启动后续 Skill。
