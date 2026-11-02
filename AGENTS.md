# Codex 项目规则

在本仓库工作时，先完整读取并遵守 `CLAUDE.md`。其中的阶段边界对 Codex 同样是强制规则。

项目 Skill 的唯一真相源是 `.claude/skills/`。`.agents/skills/` 仅用于 Codex 发现和兼容适配，不得在适配层复制或维护业务流程、脚本、引用资料、配置和临时产物。

调用 Skill 时遵守以下规则：

- Codex 显式调用使用 `$skill-name`；原始 Skill 文档可以继续保留 Claude 的 `/skill-name` 示例。
- 没有触发对应阶段 Skill 时，不得调用 `openspec instructions <artifact>`。
- 一个 Skill 执行完成后必须停止并汇报，不得自动执行后续 Skill。
- `.agents/skills/<name>/SKILL.md` 与 `.claude/skills/<name>/SKILL.md` 冲突时，以 `.claude` 下的原始 Skill 为准。

## SE 固定适配

- 工程路径和知识库按本仓库 `config.yaml` 解析；相对路径以其所在目录为基准。使用 SE 的 `../develop/client/project/docs/ai-core/`，不导入其他项目知识库或个人规范。
- `NeedParseDataMethod` 是 SE 专有机制，设计、模板、任务、合并门禁和审查均保留；细节见 `schemas/lr-func-dev/rules/common/se-config-generation.md`。
- `lr-design`、`lr-openspec-ui-prefab` 涉及 Unity UI 的参考查询、生成和验证时优先 ai-game-developer MCP；先按 `Application.dataPath` 识别 SE 工程，参见 `schemas/lr-func-dev/rules/common/unity-ui-mcp.md`。CLI 仅在 MCP 不可用或能力不足时兜底。
- Unity 版本按 SE 的 ProjectVersion.txt，当前为 2022.3.62f2；工程素材和实际 API 不随 DL 示例覆盖。
- 外部客户端和服务端工程按实际版本管理选择 SVN/Git；不能由 OpenSpec 使用 Git 推断外部工程也使用 Git。

## CodeGraph

目标工程存在 `.codegraph/` 时，理解或定位代码先用 `codegraph_explore`（传实际 `projectPath`），再按需要做文本搜索；没有索引时不自行创建。历史归档和外部工程默认只读，本工作流维护不代表授权执行任一业务阶段。
