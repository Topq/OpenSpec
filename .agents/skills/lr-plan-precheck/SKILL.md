---
name: lr-plan-precheck
description: 策划案完整性自检——在正式发起 lr-design 之前,让策划自己反复核对飞书策划案是否足够完整,产出一份"如果现在提交会被挑出哪些问题"的报告。下载内容只落本技能自己的 tmp/(每次调用前自动清空,不留跨任务残留),不建 changes/ 目录、不产生 lr-design 需要读取的持久产物,可无限次重复调用。当用户提到"先检查一下策划案""这个案子写完整了吗""能不能先自己看看有没有漏的""还没准备好走 lr-design"等意图时使用。不生成 demo、不生成 proposal/specs、不建 change 目录——这些是 lr-design 的职责,本技能只读不写。
---

# Codex 适配器

完整读取并严格执行 `../../../.claude/skills/lr-plan-precheck/SKILL.md`。

- 以 `.claude/skills/lr-plan-precheck/` 为原始 Skill 根目录解析其中的相对路径。
- 将 `Read`、`Grep`、`Glob`、`Bash`、`Write`、`Edit` 等 Claude 工具表述映射到当前可用工具。
- 在面向 Codex 用户展示调用方式时，将 `/lr-plan-precheck` 写为 `$lr-plan-precheck`。
- 原始 Skill 执行完成后停止，不自动启动后续 Skill。
