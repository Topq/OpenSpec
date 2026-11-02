---
name: lr-openspec-ui-prefab
description: 根据已验收的 React 原型 + lr-openspec-apply 生成的 UI 脚本，生成 Unity UI Prefab 的中间数据（TSX），校验字段完整性后交给临时部署的 Unity 生成器一次性构建 GameObject 树、挂载组件、绑定序列化字段。强制使用 TextMeshPro。 SE UI 优先 ai-game-developer MCP。
---

# Codex 适配器

完整读取并严格执行 `../../../.claude/skills/lr-openspec-ui-prefab/SKILL.md`。

- 以 `.claude/skills/lr-openspec-ui-prefab/` 为原始 Skill 根目录解析其中的相对路径。
- 将 `Read`、`Grep`、`Glob`、`Bash`、`Write`、`Edit` 等 Claude 工具表述映射到当前可用工具。
- 在面向 Codex 用户展示调用方式时，将 `/lr-openspec-ui-prefab` 写为 `$lr-openspec-ui-prefab`。
- 原始 Skill 执行完成后停止，不自动启动后续 Skill。
