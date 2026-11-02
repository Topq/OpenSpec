---
name: lr-openspec-rule-candidates
description: 规则沉淀与文档补充：综合前三阶段发现，生成候选清单供人工勾选，回写config.yaml/schemas/design.md
---

# Codex 适配器

完整读取并严格执行 `../../../.claude/skills/lr-openspec-rule-candidates/SKILL.md`。

- 以 `.claude/skills/lr-openspec-rule-candidates/` 为原始 Skill 根目录解析其中的相对路径。
- 将 `Read`、`Grep`、`Glob`、`Bash`、`Write`、`Edit` 等 Claude 工具表述映射到当前可用工具。
- 在面向 Codex 用户展示调用方式时，将 `/lr-openspec-rule-candidates` 写为 `$lr-openspec-rule-candidates`。
- 原始 Skill 执行完成后停止，不自动启动后续 Skill。
