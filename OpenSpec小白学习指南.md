# OpenSpec 小白学习指南

> 面向第一次接触“规范驱动开发”的读者。本文根据 OpenSpec 官方仓库与官方文档整理，内容核对日期：2026-07-17。

## 阅读路线

- 只想尽快跑起来：阅读第 1～9 节，跟着“深色模式”示例操作一次。
- 想在真实项目中使用：继续阅读第 10～16 节，重点掌握规范、审核和排错。
- 想系统练习：按照第 17 节的 7 天路线逐步完成。

## 1. 先用一句话认识 OpenSpec

OpenSpec 是一套帮助“人”和“AI 编程助手”先把需求说清楚，再开始写代码的工作方法。

官网把它定位为一个轻量的规范驱动框架。对新手来说，可以先记住四个特点：

- **通用**：能配合 Codex、Claude Code、Cursor、GitHub Copilot 等多种 AI 编程工具。
- **开源**：核心项目采用 MIT 许可证。
- **不需要 API Key**：OpenSpec 本身不是一个新的大模型服务。
- **不依赖 MCP**：初始化后主要通过项目文件、技能和命令与 AI 工具配合。

普通的 AI 编程经常是这样：

1. 你说：“帮我加一个深色模式。”
2. AI 立刻修改很多文件。
3. 做完后才发现：入口位置不对、没有保存用户选择、刷新后失效。

使用 OpenSpec 后会变成：

1. 先说明为什么做、做什么、不做什么。
2. 把需求写成可以检查的场景。
3. 确定技术方案和任务清单。
4. 你审核计划。
5. AI 按任务清单实现并验证。
6. 完成后把本次变更归档，项目规范同步更新。

可以把它理解为：**先画施工图，再让 AI 施工。**

## 2. OpenSpec 解决什么问题

AI 会写代码，但它不会自动知道你的完整想法。只在聊天窗口里描述需求，容易出现以下问题：

- 需求散落在多轮聊天中，后面很难追溯。
- 人和 AI 对“做完了”的理解不一致。
- AI 直接动手，返工时才发现方向错了。
- 新成员只看到代码，不知道当时为什么这样设计。
- 多个功能同时开发时，修改内容容易混在一起。

OpenSpec 会为每次变更建立独立目录，把需求、设计和任务都保存为 Markdown 文件。这些文件可以和代码一起提交到 Git，因此能被检查、修改和追溯。

## 3. 最重要的概念：两种命令、两个地方

这是新手最容易出错的地方。

| 命令形式 | 在哪里输入 | 用来做什么 | 示例 |
| --- | --- | --- | --- |
| `openspec ...` | 系统终端，如 PowerShell、CMD、Terminal | 安装、初始化、查看、校验和管理项目 | `openspec init` |
| `/opsx:...` 或工具对应形式 | AI 编程助手的聊天输入框 | 让 AI 按 OpenSpec 流程规划和实现 | `/opsx:propose add-dark-mode` |

请记住：

- `openspec init` 要输入到终端。
- `/opsx:propose` 要输入到 AI 聊天框。
- OpenSpec 没有一个需要单独启动的“交互模式”。日常开发主要发生在 AI 聊天框中。
- 不同 AI 工具的斜杠命令写法可能不同。例如有些工具使用冒号形式 `/opsx:propose`，有些使用短横线形式 `/opsx-propose`。不确定时，在聊天框输入 `/` 或 `opsx`，以工具显示的自动补全为准。

## 4. 安装前准备

### 4.1 必要条件

OpenSpec 当前要求：

- Node.js `20.19.0` 或更高版本。
- 一个已有或新建的代码项目。
- 一个 OpenSpec 支持的 AI 编程助手，例如 Codex、Claude Code、Cursor、Windsurf、GitHub Copilot 等。

先在终端检查 Node.js：

```bash
node --version
```

如果输出版本低于 `20.19.0`，先升级 Node.js。

### 4.2 安装 OpenSpec

最常见的 npm 安装方式：

```bash
npm install -g @fission-ai/openspec@latest
```

验证安装：

```bash
openspec --version
```

也可以使用 pnpm、yarn 或 bun 安装，但即使使用 bun，运行 OpenSpec 时仍然需要 Node.js 20.19.0 以上版本。

## 5. 在项目中初始化

进入你的项目根目录：

```bash
cd your-project
openspec init
```

初始化时，OpenSpec 会询问你使用哪个 AI 编程工具。选择你实际使用的工具即可。

也可以直接指定工具。例如为 Codex 初始化：

```bash
openspec init --tools codex
```

为多个工具初始化：

```bash
openspec init --tools codex,cursor
```

初始化完成后，建议重启或重新打开 AI 编程助手，让它重新扫描项目中的命令和技能文件。

## 6. 初始化后会看到什么

项目中通常会出现下面的结构：

```text
openspec/
├── specs/                  # 当前系统规范，也就是“现在系统应该怎样工作”
├── changes/                # 正在进行的变更
│   └── add-dark-mode/      # 一次具体变更，一个变更一个目录
│       ├── proposal.md     # 为什么做、准备做什么
│       ├── design.md       # 技术上准备怎么做
│       ├── tasks.md        # 可以逐项勾选的实施任务
│       └── specs/          # 本次变更对规范的增量修改
└── config.yaml             # 项目上下文和 OpenSpec 配置
```

只需要先记住两个目录：

- `openspec/specs/`：描述系统当前已经具备的行为，是项目规范的“现状”。
- `openspec/changes/`：描述准备进行的修改，是项目规范的“提案”。

变更完成并归档后，变更中的规范会合并到 `specs/`，变更目录则会移动到 `changes/archive/` 留作历史记录。

## 7. 四种核心产物

OpenSpec 把一次变更拆成四类文件。它们通常由 AI 生成，但必须由人审核。

| 产物 | 回答的问题 | 审核重点 |
| --- | --- | --- |
| `proposal.md` | 为什么做？做什么？范围是什么？ | 目标是否正确，边界是否清楚 |
| `specs/` | 用户或系统应该表现出什么行为？ | 每条需求是否可测试，场景是否完整 |
| `design.md` | 技术上怎么做？ | 方案是否适合现有项目，有无明显风险 |
| `tasks.md` | 具体分几步完成？ | 是否可执行，是否遗漏测试和文档 |

它们之间的大致关系是：

```text
proposal → specs → design → tasks → 实现代码
    ↑         ↑        ↑          │
    └─────────┴────────┴──────────┘
             实现中可以继续修订
```

OpenSpec 不是严格的瀑布流程。实现过程中发现理解有误，可以回头修改前面的文件，再继续开发。

## 8. 默认工作流

OpenSpec 默认使用 `core` 配置，包含以下工作流：

```text
explore（可选）→ propose → apply → sync → archive
```

### 8.1 `/opsx:explore`：先讨论，不落地

当你的想法还比较模糊时使用。

示例：

```text
/opsx:explore

我想给后台系统增加操作日志，但还不确定应该记录哪些内容，
请先阅读现有代码，和我一起分析方案，不要修改代码。
```

这一阶段适合：

- 了解现有代码结构。
- 比较几种实现方案。
- 找出需求中的遗漏和冲突。
- 把一句模糊想法整理成可执行需求。

### 8.2 `/opsx:propose`：生成完整变更计划

当需求已经比较明确时，可以直接提出变更：

```text
/opsx:propose add-dark-mode

为管理后台增加深色模式：
- 用户可以在设置页手动切换；
- 第一次访问时跟随系统主题；
- 用户的选择需要在刷新后保留；
- 暂不支持自定义配色。
```

AI 通常会创建 `proposal.md`、增量 `specs/`、`design.md` 和 `tasks.md`。

不要看到“Ready for implementation”就马上开始。先打开这些文件检查，尤其要确认“不做什么”是否写清楚。

### 8.3 `/opsx:apply`：按任务实施

审核计划后，在 AI 聊天框中输入：

```text
/opsx:apply
```

如果项目里同时有多个变更，最好明确写出名称：

```text
/opsx:apply add-dark-mode
```

AI 会读取任务列表，逐项修改代码并更新勾选状态。完成后不要只看 AI 的总结，还要运行测试并检查实际效果。

### 8.4 `/opsx:sync`：同步规范

`sync` 会把变更中的增量规范合并到主规范中。通常归档时也会提示同步。

适合在以下情况主动同步：

- 代码还没有完全结束，但规范已经确定。
- 其他并行工作需要尽早看到最新规范。
- 希望在归档前先检查合并结果。

### 8.5 `/opsx:archive`：完成并归档

确认代码、测试和规范都完成后：

```text
/opsx:archive
```

归档通常会：

1. 校验当前变更。
2. 将增量规范同步到 `openspec/specs/`。
3. 把变更移动到 `openspec/changes/archive/日期-变更名/`。
4. 保留完整历史，方便以后追溯。

归档的含义是“这次变更已经结束”，不是“临时把文件收起来”。

## 9. 第一次完整实战：添加深色模式

下面用一个小功能走完整流程。

### 第 1 步：确认环境

在终端输入：

```bash
node --version
openspec --version
```

### 第 2 步：初始化项目

在项目根目录的终端输入：

```bash
openspec init --tools codex
```

使用其他 AI 工具时，把 `codex` 替换为相应工具 ID，或者直接运行交互式的 `openspec init`。

### 第 3 步：和 AI 讨论需求

在 AI 聊天框输入：

```text
/opsx:explore

我想给当前应用增加深色模式。请先分析现有样式方案，
告诉我最小改动方案、可能影响的页面和需要补充的测试，暂时不要改代码。
```

### 第 4 步：建立变更

想法确认后，在 AI 聊天框输入：

```text
/opsx:propose add-dark-mode

根据刚才讨论的方案建立变更。用户可以手动切换主题；
没有保存记录时跟随系统设置；选择保存在本地；不增加新依赖。
```

变更名推荐使用小写短横线格式，例如：

- 正确：`add-dark-mode`
- 正确：`fix-login-timeout`
- 不推荐：`AddDarkMode`
- 不推荐：`add_dark_mode`
- 不推荐：`增加深色模式`

### 第 5 步：人工审核

至少检查以下内容：

- `proposal.md` 是否写清业务目标和不做的内容。
- `specs/` 是否包含手动切换、首次加载、保存选择等场景。
- `design.md` 是否符合项目现有技术栈。
- `tasks.md` 是否包含实现、测试和必要文档。
- AI 是否擅自引入了不需要的新依赖或大规模重构。

如果不满意，直接让 AI 修改产物。例如：

```text
请修改 add-dark-mode 的方案：
1. 不引入第三方主题库；
2. 增加“系统主题改变时自动响应”的场景；
3. tasks.md 中补充单元测试和端到端测试。
```

### 第 6 步：执行实现

在 AI 聊天框输入：

```text
/opsx:apply add-dark-mode
```

### 第 7 步：检查和校验

在终端输入：

```bash
openspec show add-dark-mode
openspec validate add-dark-mode
```

然后运行项目本身的测试、构建和人工验收。

### 第 8 步：归档

全部通过后，在 AI 聊天框输入：

```text
/opsx:archive add-dark-mode
```

最后检查：

- `openspec/specs/` 中是否已经出现深色模式的最终规范。
- `openspec/changes/archive/` 中是否保留本次变更。
- Git 中是否只包含预期的代码和文档修改。

## 10. 怎么读懂增量规范

增量规范只描述“相对于当前系统发生了什么变化”。常见标记有三种：

- `ADDED`：新增要求。
- `MODIFIED`：修改已有要求。
- `REMOVED`：删除已有要求。

示例：

```markdown
## ADDED Requirements

### Requirement: 主题选择
系统 SHALL 允许用户在浅色和深色主题之间切换。

#### Scenario: 手动切换主题
- GIVEN 用户已经打开设置页面
- WHEN 用户选择深色主题
- THEN 页面应立即切换为深色主题
- AND 刷新页面后仍保持深色主题
```

其中：

- `GIVEN`：前置条件。
- `WHEN`：用户操作或事件。
- `THEN`：预期结果。
- `AND`：补充条件或结果。

一条好场景应该可以直接转化为测试。像“界面要好看”“性能要高”这样的说法无法直接判断是否完成，需要改成可观察、可衡量的结果。

## 11. 常用终端命令速查

下面的命令全部在终端中运行。

| 命令 | 作用 |
| --- | --- |
| `openspec init` | 在当前项目初始化 OpenSpec |
| `openspec update` | 升级后重新生成 AI 工具的命令和技能文件 |
| `openspec list` | 查看正在进行的变更 |
| `openspec list --specs` | 查看当前主规范 |
| `openspec show <名称>` | 查看某个变更或规范的详情 |
| `openspec validate <名称>` | 校验指定变更或规范 |
| `openspec validate --all` | 校验全部变更和规范 |
| `openspec status --change <名称>` | 查看产物完成进度和阻塞原因 |
| `openspec view` | 打开终端交互式浏览面板 |
| `openspec archive <名称>` | 从终端归档指定变更 |
| `openspec --version` | 查看当前安装版本 |

常见排查组合：

```bash
openspec list
openspec status --change add-dark-mode
openspec show add-dark-mode
openspec validate add-dark-mode
```

## 12. 默认命令和扩展命令

### 12.1 默认核心命令

默认 `core` 配置一般包含：

| AI 聊天命令 | 用途 |
| --- | --- |
| `explore` | 讨论想法，不创建变更、不修改代码 |
| `propose` | 一次生成完整变更计划 |
| `apply` | 按任务实施变更 |
| `sync` | 将增量规范同步到主规范 |
| `archive` | 归档已完成变更 |

### 12.2 扩展工作流

如果希望更细地控制每一步，可在终端运行：

```bash
openspec config profile
openspec update
```

扩展命令可能包括：

| 命令 | 适合场景 |
| --- | --- |
| `new` | 只创建一个空的变更骨架 |
| `continue` | 一次生成一个准备就绪的产物，边生成边审核 |
| `ff` | 快速生成所有规划产物 |
| `verify` | 归档前检查实现是否符合规范和任务 |
| `bulk-archive` | 一次归档多个已完成变更 |
| `onboard` | 在真实项目中带讲解地完成一次完整练习 |

新手建议先使用默认的 `explore → propose → apply → archive`。当你理解四类产物后，再开启扩展命令。

## 13. 一份实用的人工审核清单

### 提案阶段

- [ ] 问题和目标写清楚了。
- [ ] 范围内和范围外的内容写清楚了。
- [ ] 没有把无关重构偷偷塞进来。
- [ ] 对用户、接口和数据的影响已说明。

### 规范阶段

- [ ] 每条需求都能通过观察或测试来判断。
- [ ] 正常流程、异常流程、边界情况都有场景。
- [ ] 使用 `ADDED`、`MODIFIED`、`REMOVED` 的位置正确。
- [ ] 修改已有行为时，写的是完整的新版本，而不是零散说明。

### 设计阶段

- [ ] 技术方案符合项目现有架构和编码习惯。
- [ ] 数据迁移、兼容性、安全、性能等风险已考虑。
- [ ] 没有为小功能设计过度复杂的架构。
- [ ] 关键选择写明了理由。

### 实现阶段

- [ ] 任务足够小，可以逐项完成和检查。
- [ ] 代码、测试和文档任务都已覆盖。
- [ ] 测试、构建和静态检查已经执行。
- [ ] 实际行为与规范一致，而不只是任务被打勾。
- [ ] 归档前没有遗留未解释的任务。

## 14. 常见问题与解决办法

### 问题 1：提示 `openspec: command not found`

重新安装并验证：

```bash
npm install -g @fission-ai/openspec@latest
openspec --version
```

如果仍然找不到，通常是 npm 的全局可执行目录没有加入系统 `PATH`。

### 问题 2：提示 Node.js 版本过低

```bash
node --version
```

升级到 Node.js `20.19.0` 或更高版本。使用 bun 安装也不能省略 Node.js。

### 问题 3：AI 聊天框里没有 OpenSpec 命令

按顺序检查：

1. 确认是在 AI 聊天框输入，不是在终端输入。
2. 在项目根目录运行 `openspec update`。
3. 重启 AI 编程助手或重新打开项目。
4. 确认初始化时选择了当前使用的 AI 工具。
5. 确认项目中存在该工具对应的 OpenSpec 技能或命令文件。
6. 输入 `/` 查看工具自动补全提供的是冒号、短横线还是技能形式。

### 问题 4：提示 `Change not found`

先查看现有变更：

```bash
openspec list
```

然后在命令中明确写出名称，并确认终端或 AI 当前打开的是正确项目。

### 问题 5：提示 `No artifacts ready`

查看哪个产物还没完成：

```bash
openspec status --change <变更名>
```

默认依赖关系大致是：`proposal` 完成后才能继续 `specs` 和 `design`，两者完成后才能生成 `tasks`。

### 问题 6：`validate` 报错

运行：

```bash
openspec validate <变更名>
```

错误信息通常会指出文件和问题。常见原因包括：缺少必要章节、需求没有场景、增量标题格式错误。修复后再次校验，不要直接跳过校验。

### 问题 7：AI 生成的方案不符合项目实际

这通常说明 AI 得到的上下文不足。可以：

- 在 `openspec/config.yaml` 的 `context` 中简要说明技术栈、架构和项目约定。
- 在提案描述中明确限制条件和不做的内容。
- 使用扩展的 `continue` 工作流，一次审核一个产物。
- 要求 AI 先读取相关代码，再生成设计。

### 问题 8：升级后命令还是旧的

升级全局包后，还要在每个项目中刷新生成文件：

```bash
npm install -g @fission-ai/openspec@latest
cd your-project
openspec update
```

然后重启 AI 编程助手。

## 15. 新手最容易踩的坑

1. **把斜杠命令输入终端。** `/opsx...` 应输入 AI 聊天框。
2. **计划没看就直接实现。** AI 生成计划不等于计划正确。
3. **需求写得太大。** “重做整个系统”很难审核，最好拆成多个独立变更。
4. **只写正常流程。** 登录失败、网络中断、空数据、权限不足等场景也要写。
5. **只看任务勾选。** 任务全勾不代表行为真的符合规范，仍需测试和验收。
6. **把 `specs/` 当普通文档。** 它代表系统当前应有的行为，修改时必须保持准确。
7. **过早开启全部高级功能。** 先掌握默认工作流，再学习自定义 schema、stores 等高级能力。
8. **忘记升级后的 `openspec update`。** 只升级 npm 包不会自动刷新每个项目的 AI 指令文件。

## 16. 推荐的日常节奏

对于一个普通功能，可以固定使用下面的节奏：

```text
1. /opsx:explore        想法不清楚时先讨论
2. /opsx:propose        生成提案、规范、设计和任务
3. 人工审核             修正范围、场景和技术方案
4. /opsx:apply          实施代码和测试
5. 项目测试 + validate  检查代码和规范
6. /opsx:archive        同步规范并归档
7. git review/commit    最后检查版本控制中的修改
```

对于一个很小、需求非常清楚的修改，可以跳过 `explore`，直接从 `propose` 开始。但不建议跳过提案审核和测试。

## 17. 7 天学习路线

### 第 1 天：理解概念

- 分清终端命令和 AI 聊天命令。
- 理解 `specs/` 与 `changes/` 的区别。
- 阅读一个 `proposal.md` 和一个 `tasks.md`。

### 第 2 天：完成安装

- 检查 Node.js 版本。
- 安装 OpenSpec。
- 在练习项目中运行 `openspec init`。
- 确认 AI 聊天框能找到 OpenSpec 命令。

### 第 3 天：完成小变更

- 选择“修改按钮文字”“增加一个设置项”一类低风险功能。
- 走完 `propose → apply → archive`。

### 第 4 天：学习写场景

- 为同一需求补充正常、异常和边界场景。
- 检查每个 `THEN` 是否可以测试。

### 第 5 天：练习先探索

- 使用 `explore` 分析一个模糊需求。
- 比较两种技术方案，但暂时不修改代码。

### 第 6 天：学习校验和排错

- 使用 `list`、`show`、`status`、`validate`。
- 故意制造一个规范格式错误，再根据提示修复。

### 第 7 天：完成一次正式变更

- 选择真实项目中的一个小功能。
- 审核四类产物。
- 运行项目测试和 OpenSpec 校验。
- 归档并检查最终主规范。

## 18. 学完后你应该能够做到

- 解释 OpenSpec 为什么要“先规范、后编码”。
- 正确区分终端命令和 AI 聊天命令。
- 独立安装、初始化和升级 OpenSpec。
- 看懂 `proposal`、`specs`、`design`、`tasks`。
- 使用默认工作流完成一个小功能。
- 写出包含 `GIVEN / WHEN / THEN` 的可测试场景。
- 使用 `list`、`show`、`status`、`validate` 排查问题。
- 在归档前判断实现是否真正符合规范。

## 19. 官方资料

- [OpenSpec 官网](https://openspec.dev/)
- [OpenSpec GitHub 仓库](https://github.com/Fission-AI/OpenSpec)
- [官方 Getting Started](https://github.com/Fission-AI/OpenSpec/blob/main/docs/getting-started.md)
- [官方 How Commands Work](https://github.com/Fission-AI/OpenSpec/blob/main/docs/how-commands-work.md)
- [官方 Installation](https://github.com/Fission-AI/OpenSpec/blob/main/docs/installation.md)
- [官方 CLI Reference](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md)
- [官方 Supported Tools](https://github.com/Fission-AI/OpenSpec/blob/main/docs/supported-tools.md)
- [官方 Troubleshooting](https://github.com/Fission-AI/OpenSpec/blob/main/docs/troubleshooting.md)

> OpenSpec 更新较快。升级全局包后，请在项目中运行 `openspec update`，并以官方文档和当前工具的命令自动补全为准。
