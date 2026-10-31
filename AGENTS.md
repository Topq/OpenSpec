# 给 AI 执行者的须知

本仓库是灵刃 OpenSpec 工作流（策划案 → 三端设计 → 实施 → 归档）。完整流程、阶段划分、产物依赖见 [README.md](./README.md)。这里只记录一条容易被忽略、导致 AI 自动越界执行的硬性规则。

## 阶段边界：每个 SKILL 执行完就停，不自动串下一个 SKILL

`openspec instructions <artifact-id> --change <id>` 对流程里任意 artifact（`design`、`test-cases`、`tasks`、`apply` 等）都是可调用的。**这不是无副作用的只读命令**——调用即代表"生成/合并该阶段的产物"。

工作流按 `.Codex/skills/lr-openspec-*` 拆成了明确阶段（见 README「阶段与 SKILL 对照表」）。每个 SKILL.md 自己定义了一套步骤（有的只调用一次 `openspec instructions`，有的连续调用多次，例如 `lr-openspec-tasks` 内部依次跑 `design`→`test-cases`→`tasks` 三步）——**这些是该 SKILL 自身职责范围内的合法调用，不受本规则限制**。

真正要卡住的是两种情况：

1. **没有 SKILL 被显式触发时，不要自己顺手调用任何阶段的 `openspec instructions`。** 比如你在阶段 5（人工技术评审期间）帮忙修正 `design/*.md` 里的错误，这是普通编辑工作，不是在执行 `lr-openspec-design` 或 `lr-openspec-tasks` 的步骤——此时只能用 `openspec validate <id>` 确认格式，不要调用 `openspec instructions design`（那是 `lr-openspec-tasks` 阶段 6 的合并门禁，会直接生成 `design.md`，代表评审已结束）。
2. **某个 SKILL 按自己 SKILL.md 定义的步骤跑完后，必须停下汇报产物，不能自动接着执行下一个 SKILL。** 例如 `lr-openspec-tasks` 产出 `tasks.md` 后必须停止；即使 SKILL.md 里写了"下一步：`/lr-openspec-apply`"这类提示，那也只是给用户看的建议，不是让 AI 自己接着调用。等用户显式说"继续""执行下一步"或直接触发下一个 `/lr-openspec-*` 命令，才能进入下一阶段。

**判断准则**：调用 `openspec instructions <artifact>` 前，先确认——我现在是在执行哪个 SKILL？这次调用是不是这个 SKILL 自己 SKILL.md 里写明的步骤？如果没有 SKILL 在执行，或者这个调用属于另一个（尤其是编号更靠后的）SKILL 的步骤，就不要调用，先向用户确认。

跨文档一致性检查（例如确认 Record 表 / 协议名 / 配置表字段在 `design/client.md`、`design/server.md`、`design/config.md` 之间是否对齐）应该靠人工/AI 重新读取并比对文件内容完成，不要靠调用合并门禁命令来"顺便检查"。
