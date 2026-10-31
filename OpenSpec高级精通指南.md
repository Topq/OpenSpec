# OpenSpec 高级精通指南

> 面向已经跑通默认工作流、想深入掌握底层机制的读者。核对环境：OpenSpec `1.5.0`，核对日期 2026-07-22。
> 如果你还没走过 `propose → apply → archive`，请先读《OpenSpec 小白学习指南》。本文假设你已经理解四类产物和增量规范的基本概念。

## 阅读路线

- 想真正理解「为什么这样设计」：读第 1～4 节，建立心智模型。
- 想在团队/多项目落地：读第 5～8 节，掌握根解析、stores、worksets 和全局配置。
- 想定制自己的工作流：读第 9～12 节，掌握 schema 系统。
- 想接入 CI 和自动化：读第 13～14 节。

---

## 1. 重新理解 OpenSpec：它到底是什么

小白阶段我们把 OpenSpec 理解成「先画施工图，再让 AI 施工」。高级阶段要换一个更准确的定义：

**OpenSpec 是一个「产物有向无环图（DAG）+ 状态机」的引擎，外加一套给 AI 读的指令注入系统。**

拆开看：

- **产物（artifact）**：`proposal`、`specs`、`design`、`tasks` 不是四个随意的文件，而是 schema 里显式声明的节点。
- **依赖关系（requires）**：每个产物声明它依赖哪些前置产物。这构成一张 DAG，决定了「哪个产物现在可以生成、哪个被阻塞」。
- **状态机**：`status` 命令读这张图，算出每个产物是「未开始 / 可开始 / 已完成 / 被阻塞」。
- **指令注入**：每个产物带一段 `instruction`（写给 AI 的话）和一个 `template`（文件骨架）。`openspec instructions` 把它们和你项目的 `config.yaml` 规则拼在一起，喂给 AI。

也就是说：斜杠命令（`/opsx:propose` 等）背后并不是硬编码的逻辑，而是**读取当前 schema 的 DAG，找出下一个可生成的产物，取出它的指令和模板，交给 AI**。理解了这一点，你就能定制它。

---

## 2. 核心机制：产物 DAG 与 requires 图

打开当前默认 schema 定义（`openspec schema which spec-driven` 能告诉你它在哪），你会看到每个产物都有一个 `requires` 字段：

```yaml
artifacts:
  - id: proposal
    requires: []              # 无依赖，最先生成
  - id: specs
    requires: [proposal]      # 必须先有 proposal
  - id: design
    requires: [proposal]      # 只依赖 proposal，和 specs 并列
  - id: tasks
    requires: [specs, design] # 必须 specs 和 design 都完成
apply:
  requires: [tasks]           # 实现阶段依赖 tasks
  tracks: tasks.md            # 通过解析 tasks.md 的 checkbox 追踪进度
```

画成图：

```text
proposal ──┬──> specs ──┐
           └──> design ─┴──> tasks ──> apply
```

关键点：

- **`design` 只依赖 `proposal`，不依赖 `specs`。** 所以 specs 和 design 可以并行推进。这解释了小白指南里「proposal 完成后 specs 和 design 才能继续，两者完成后才能生成 tasks」的依赖关系——它不是约定，是 schema 里写死的。
- **`tasks` 是汇聚点。** 只有 specs 和 design 都完成，tasks 才「可开始」。这是 `No artifacts ready` 报错的根源：某个前置产物还没标记完成。
- **`apply` 不是产物，是独立阶段。** 它依赖 tasks，并通过 `tracks: tasks.md` 解析 checkbox 来算实现进度。

用 `openspec status --change <名字>` 看这张图的实时状态，用 `--json` 拿到机器可读版本：

```bash
openspec status --change add-dark-mode --json
```

它会告诉你每个产物的状态和「为什么被阻塞」，比你手动翻文件靠谱。

---

## 3. 增量规范（delta spec）精通

这是 OpenSpec 最容易「静默失败」的地方，也是高级用户和新手的分水岭。

### 3.1 四种 delta 操作

规范增量用 `##` 二级标题声明操作类型：

| 操作 | 用途 | 硬性要求 |
| --- | --- | --- |
| `## ADDED Requirements` | 新增要求 | 每条要求至少一个场景 |
| `## MODIFIED Requirements` | 改变已有行为 | **必须粘贴完整的新版全文**，不是差异片段 |
| `## REMOVED Requirements` | 删除要求 | 必须写 `**Reason**` 和 `**Migration**` |
| `## RENAMED Requirements` | 仅改名 | 用 `FROM:` / `TO:` 格式 |

### 3.2 两个会「静默失败」的坑

这两个坑不会报错，但会让你的规范在归档时悄悄丢内容：

**坑 1：场景必须用正好 4 个 `#`。**

```markdown
#### Scenario: 手动切换主题      ✅ 正好 4 个 #
### Scenario: ...                ❌ 3 个 # —— 会被当成 Requirement，静默忽略
- Scenario: ...                  ❌ 用 bullet —— 解析不到，静默忽略
```

用 3 个井号或 bullet 写场景，校验可能通过，但这条场景不会被识别。写完务必 `openspec validate` 并肉眼确认场景数。

**坑 2：`MODIFIED` 必须写完整全文。**

`MODIFIED` 的语义是「用这段内容整体替换旧要求」，不是「打补丁」。正确做法：

1. 去 `openspec/specs/<capability>/spec.md` 找到原要求。
2. **整块复制**（从 `### Requirement:` 到它下面所有场景）。
3. 粘到 `## MODIFIED Requirements` 下，再改成新行为。
4. 确保标题文字和原文完全一致（空白不敏感，但文字要对上）。

如果你只在 `MODIFIED` 里写了改动的那一句，归档时旧要求的其余场景会**全部丢失**。判断原则：**只是新增关注点、不改旧行为 → 用 ADDED；真的要改旧行为 → 用 MODIFIED 且写全文。**

### 3.3 归档时 delta 如何合并进主规范

`archive`（及 `sync`）会把 `changes/<名字>/specs/` 里的 delta 应用到 `openspec/specs/`：ADDED 追加、MODIFIED 整体替换、REMOVED 删除、RENAMED 改名。合并后主规范就是「系统当前应有行为」的唯一真相。这就是为什么 MODIFIED 写不全会丢内容——合并是「替换」而非「叠加」。

---

## 4. 配置系统：两层 config 与规则注入

OpenSpec 有**两层配置**，很多人只知道第一层。

### 4.1 项目级：`openspec/config.yaml`

管这个项目怎么工作。三个关键字段：

```yaml
schema: spec-driven        # 用哪套产物 DAG（决定工作流形状）

context: |                 # 每次生成产物都会注入给 AI 的项目背景
  技术栈、架构、目录布局、职责边界……

rules:                     # 按产物注入的额外硬性约束
  proposal:
    - Impact 必须标出受影响区域
  design:
    - 未确认字段必须列为 Open Questions
  tasks:
    - 任务必须用 [Server]/[Client] 分类
```

- **`context`** 解决「AI 不懂我的项目」——把技术栈和约定写这里，比每次在提案里重复强。
- **`rules`** 是**按产物分组**的。`rules.design` 下的规则只在生成 design 时注入。这让你能针对某类产物强制团队规范，而不用改 schema 本身。

想确认某个产物最终拿到的完整指令（模板 + schema instruction + 你的 rules），运行：

```bash
openspec instructions design --change add-dark-mode
```

这就是 AI 实际看到的东西。调 prompt 效果不好时，先看这个输出。

### 4.2 全局级：`openspec config`

管这台机器/这个用户怎么工作，跨所有项目。

```bash
openspec config list        # 看全部设置
openspec config path        # 配置文件位置
openspec config get profile
openspec config set <key> <value>
```

核心字段：

- **`profile`**：工作流预设。当前版本内置 `core`（= `propose, explore, apply, sync, archive`）。用 `openspec config profile core` 切换。
- **`delivery`**：`both`（默认）等，控制产物如何交付。
- **`featureFlags`**：实验特性开关。

改完全局配置后，必须在每个项目里 `openspec update` 才能把新的命令/技能文件刷进 AI 工具。

---

## 5. 根解析（Root Resolution）：多数疑难杂症的根源

`openspec` 命令怎么知道「当前项目根在哪」？它从**当前工作目录向上查找最近的 OpenSpec 根**（nearest 策略）。这条规则简单，但有两个高级陷阱。

### 5.1 陷阱：真实根可能比你以为的高一层

如果目录结构是 `D:\se\openspec\`（里面直接放 config.yaml / specs / changes），那么 **OpenSpec 根是 `D:\se`**，而 `D:\se\openspec` 只是那个约定的子目录。`openspec list --json` 的 `root.path` 会证实这一点。

**实践建议：在真实根目录下运行 openspec 命令，避免根解析歧义。** 用 `openspec doctor` 确认当前解析到的根：

```bash
openspec doctor
# Root
#   Location: D:\se
#   OpenSpec root: ok
```

### 5.2 陷阱：`schema` 子命令用的是 cwd，不是 nearest 根

这是个真实的坑：`openspec schema fork` / `schema init` 把**当前工作目录当作 projectRoot**，而不是 nearest 根。如果你在 `D:\se\openspec` 里跑 `schema fork`，它会把 schema 写到 `D:\se\openspec\openspec\schemas\`（**深了一层**）。但真正的 change/list/apply 工作流用 nearest 根 `D:\se`，只会去 `D:\se\openspec\schemas\` 找项目级 schema。

**修复**：项目级 schema 必须在 `D:\se\openspec\schemas\<name>\`。如果被 fork 放到了双层的 `openspec\openspec\schemas`，手动移上来一层，再用 `openspec schema which <name>` 确认 `Path` 正确。

---

## 6. Schema 系统：定制你自己的工作流

这是 OpenSpec 从「工具」变成「团队方法论引擎」的地方。⚠️ schema 子命令目前标注为 **experimental**，接口可能变。

### 6.1 查看现有 schema

```bash
openspec schemas                    # 列出所有可用 schema + 描述
openspec schemas --json             # 机器可读
openspec schema which spec-driven   # 某 schema 从哪解析（package/project/store）
openspec templates --schema spec-driven --json   # 每个产物的模板路径
```

`source` 字段告诉你 schema 来自哪：`package`（内置）、`project`（你 fork 到项目里的）。project 级会覆盖同名的 package 级。

### 6.2 fork 一个 schema 来改

```bash
# 在真实根目录下运行（避免 5.2 的双层坑）
cd D:/se
openspec schema fork spec-driven my-workflow
```

这会把内置 schema 复制到 `<根>/openspec/schemas/my-workflow/`，包含 `schema.yaml` 和 `templates/`。然后改 `schema.yaml`，再在 `config.yaml` 里 `schema: my-workflow` 启用。

### 6.3 schema.yaml 的结构

一个产物节点的完整字段：

```yaml
artifacts:
  - id: proposal              # 产物唯一 ID，命令和 requires 引用它
    generates: proposal.md    # 生成什么文件（可用 glob，如 specs/**/*.md）
    description: ...           # 简短描述
    template: proposal.md      # templates/ 下的骨架文件
    instruction: |            # 注入给 AI 的详细指令（最重要）
      Create the proposal that establishes WHY...
    requires: []              # 依赖哪些前置产物（构成 DAG）

apply:
  requires: [tasks]           # 实现阶段的前置
  tracks: tasks.md            # 解析哪个文件的 checkbox 追踪进度
  instruction: |
    Read context, work through pending tasks...
```

改 schema 时你能做的：

- **增删产物节点**：比如加一个 `test-plan` 产物，`requires: [specs]`。
- **改 requires 拓扑**：让 design 也依赖 specs（强制先定规范再设计）。
- **改 instruction**：这是最常用的——把团队的写法要求直接写进产物指令。
- **改 template**：给产物一个更贴合团队的骨架。
- **用 glob generates**：`specs/**/*.md` 表示一个产物可以产出多个文件（每能力一个 spec）。

### 6.4 校验你的 schema

```bash
openspec schema validate my-workflow
```

它会检查产物结构、requires 是否成环、模板是否存在。改完必跑。

---

## 7. 设计一条真实的跨端流水线（案例）

默认 4 产物只是起点。真实团队常需要更复杂的 DAG。举个跨端游戏项目的例子——把「一次业务变更同时影响客户端、服务端、策划配置」这件事编码进 schema：

思路是在标准链路里**扇出（fan-out）到三端 design，再扇入（fan-in）到统一 tasks**：

```text
proposal ──> specs ──┬──> design/client ──┐
                     ├──> design/server ──┼──> tasks ──> apply
                     └──> design/config ──┘
```

对应 schema 片段（示意）：

```yaml
artifacts:
  - id: proposal
    requires: []
  - id: specs
    requires: [proposal]
  - id: design-client
    generates: design/client.md
    requires: [specs]
    instruction: 只描述 Unity UI、客户端状态、表现和协议调用……
  - id: design-server
    generates: design/server.md
    requires: [specs]
    instruction: 只描述权威状态、业务校验、存储、奖励发放……
  - id: design-config
    generates: design/config.md
    requires: [specs]
    instruction: 只描述活动、奖励、目标、商品等数据表……
  - id: tasks
    generates: tasks.md
    requires: [design-client, design-server, design-config]
    instruction: 任务用 [Contract]/[Config]/[Server]/[Client]/[Integration] 分类，联调任务排最后……
```

配合 `config.yaml` 的 `context`（写清三端工程路径和职责边界）和 `rules`（每端的硬性约束），你就得到一条**强制跨端分析、职责不混淆**的流水线。这正是把方法论固化成工具的方式。

---

## 8. 自定义 Schema 的完整调用流程（实战）

理解了 schema 的结构后，我们来走一遍完整的「定制 → 验证 → 使用」流程。

### 8.1 第一步：Fork 基础 schema

```bash
# 在真实根目录下运行（避免双层目录坑）
cd D:/se
openspec schema fork spec-driven my-custom-workflow
```

这会复制到 `<根>/openspec/schemas/my-custom-workflow/`，包含：
- `schema.yaml`（产物 DAG 定义）
- `templates/`（各产物的模板骨架）

### 8.2 第二步：修改 schema 定义

打开 `schema.yaml`，在 `artifacts:` 列表末尾、`apply:` 之前插入新产物：

```yaml
  - id: review-checklist
    generates: review.md
    description: Review checklist for quality assurance
    template: review.md
    instruction: |
      Create a review checklist covering:
      - Code quality checks
      - Test coverage verification
      - Performance considerations
      - Security review points
    requires:
      - tasks    # 依赖 tasks 完成后才能生成

apply:
  requires:
    - tasks
  ...
```

**关键点**：
- 新产物必须插在 `artifacts:` 数组里，不能放到 `apply:` 后面（那会导致 YAML 解析错误）。
- `requires: [tasks]` 让它出现在 tasks 之后，形成 `proposal → specs/design → tasks → review-checklist` 的链。
- `generates: review.md` 告诉 OpenSpec 这个产物会生成哪个文件。

### 8.3 第三步：创建对应模板

在 `templates/` 下创建 `review.md`：

```bash
cat > openspec/schemas/my-custom-workflow/templates/review.md << 'EOF'
# Review Checklist

## Code Quality
- [ ] Code follows project style guide
- [ ] No code smells or anti-patterns

## Testing
- [ ] Unit tests added
- [ ] Integration tests pass

## Performance
- [ ] No obvious performance issues

## Security
- [ ] Input validation present
- [ ] No security vulnerabilities
EOF
```

### 8.4 第四步：校验 schema

```bash
openspec schema validate my-custom-workflow
```

如果报错，常见原因：
- `requires` 引用了不存在的产物 ID
- 产物定义在 `apply:` 后面（YAML 结构错）
- 模板文件路径不存在

### 8.5 第五步：在项目中启用

修改 `<根>/openspec/config.yaml`：

```yaml
schema: my-custom-workflow   # 从 spec-driven 改成你的 schema 名
```

### 8.6 第六步：验证解析

```bash
openspec schema which my-custom-workflow
# 输出：
# Schema: my-custom-workflow
# Source: project
# Path: D:\se\openspec\schemas\my-custom-workflow

openspec schemas
# 应该看到 my-custom-workflow 在列表里，artifacts 包含新产物
```

### 8.7 第七步：更新 AI 工具指令文件

```bash
openspec update
```

这会根据新 schema 重新生成 AI 工具的命令/技能文件（如 Codex 的 `.codex/skills/opsx-propose/SKILL.md` 等）。**不跑这一步，AI 仍用旧 schema。**

### 8.8 第八步：创建变更并查看新 DAG

```bash
# 创建一个测试变更
mkdir -p openspec/changes/test-feature
echo "# Test Proposal" > openspec/changes/test-feature/proposal.md

# 查看产物状态
openspec status --change test-feature
```

输出示例：

```
Change: test-feature
Schema: my-custom-workflow
Progress: 1/5 artifacts complete

[x] proposal
[ ] design
[ ] specs
[-] tasks (blocked by: design, specs)
[-] review-checklist (blocked by: tasks)
```

注意到 `review-checklist` 出现了，且被 `tasks` 阻塞——DAG 生效了。

### 8.9 第九步：查看新产物的实际指令

```bash
openspec instructions review-checklist --change test-feature
```

输出包含：
- `<project_context>`：你的 `config.yaml` 中的 `context`
- `<dependencies>`：`requires: [tasks]` 对应的前置文件路径
- 你在 `instruction:` 里写的生成指令
- 如果你在 `config.yaml` 的 `rules.review-checklist` 里写了额外约束，也会注入

**这就是 AI 实际读到的完整指令。** 如果 AI 生成不符合预期，先看这个输出——问题通常在指令不够明确，而非 AI 能力。

### 8.10 实际工作流中的调用

当你在 AI 聊天框输入 `/opsx:propose test-feature` 或 `/opsx:apply test-feature` 时，背后发生：

1. **AI 工具调用 `openspec instructions <产物> --change test-feature`**，拿到该产物的完整指令。
2. **指令包含**：schema 的 `instruction`、模板路径、`config.yaml` 的 `context` 和 `rules.<产物>`、前置依赖文件列表。
3. **AI 根据指令生成内容**，写入 `generates` 指定的文件。
4. **产物完成**，`openspec status` 解析 DAG，判断下一个可生成的产物。

如果你的自定义 schema 有 5 个产物，AI 就会按 DAG 依次生成 5 次，每次调用 `instructions` 拿当前产物的指令。

### 8.11 多 schema 并存

项目级 schema 会覆盖同名的 package 级（内置）schema。一台机器上可以有：
- 内置的 `spec-driven`（package）
- 项目 A 的 `openspec/schemas/team-workflow`（project）
- 项目 B 的 `openspec/schemas/another-workflow`（project）

每个项目的 `config.yaml` 独立指定 `schema:`，互不干扰。用 `openspec schemas` 能看到所有可用 schema 及其来源（package/project）。

### 8.12 调试自定义 schema 的清单

| 症状 | 定位命令 | 常见原因 |
| --- | --- | --- |
| AI 没生成新产物 | `openspec update` | 没刷新 AI 工具指令文件 |
| 产物一直 blocked | `openspec status --change <名>` | `requires` 的前置产物没标记完成 |
| 校验失败 | `openspec schema validate <名>` | YAML 结构错、模板缺失、requires 成环 |
| 产物指令不对 | `openspec instructions <产物> --change <名>` | `instruction` 或 `rules` 没写到位 |
| schema 解析不到 | `openspec schema which <名>` | 放错目录（双层坑）或 config.yaml 没改 |

---

## 9. Stores 与 Worksets：跨项目和团队协作

### 9.1 Stores：独立的 OpenSpec 仓库

Store 是「注册在这台机器上的、独立的 OpenSpec 仓库」。典型用途：**团队共享上下文**——把团队约定、共享规范放进一个 store，多个项目引用它。

```bash
openspec store setup team-context --path ~/openspec/team-context   # 创建并注册
openspec store register /path/to/existing-store                    # 注册已有的
openspec store list                                                # 列出
openspec store doctor <id>                                         # 检查注册健康
openspec store unregister <id>                                     # 忘记注册（不删文件）
openspec store remove <id>                                         # 忘记并删除本地文件夹
```

很多命令支持 `--store <id>`，把某个 store 当作临时根来操作：

```bash
openspec context --store team-context
openspec instructions proposal --store team-context
```

### 9.2 Worksets：个人的工作视图

Workset 是**纯本地**的「你自己挑的一组文件夹」的命名视图，用来在编辑器/agent 会话里一次打开相关的几个工程（比如跨端项目里同时打开 client + server + config）。它**不碰成员文件夹本身**。

```bash
openspec workset create cross-end          # 交互式挑选文件夹并命名保存
openspec workset list                       # 看已保存的视图及成员
openspec workset open cross-end             # 在工具里打开这组文件夹
openspec workset remove cross-end           # 删视图（不删文件）
```

对跨端/monorepo 开发特别有用：一条命令把散落的工程拉进同一个窗口。

---

## 10. Agent 面向命令：AI 实际消费的接口

日常你用 `/opsx:*` 斜杠命令，但底层这些命令是 AI（或 CI）真正调用的。理解它们能帮你调试「为什么 AI 生成得不对」。

| 命令 | 作用 | 什么时候手动用 |
| --- | --- | --- |
| `openspec context` | 打印当前根的「工作简报」（agent brief） | 想知道 AI 拿到的项目背景 |
| `openspec context --json` | 机器可读版简报 | 接自动化 |
| `openspec instructions <产物> --change <名>` | 打印某产物的完整注入指令（模板+schema+rules） | 调 prompt、排查生成质量 |
| `openspec templates --json` | 每个产物的模板路径映射 | 检查用了哪个模板 |
| `openspec status --change <名> --json` | 产物 DAG 实时状态 | 排查 `No artifacts ready` |
| `openspec doctor --json` | 根解析和引用关系健康 | 排查根/store 问题 |

排查「AI 生成的 design 不符合要求」的标准动作：

```bash
openspec instructions design --change my-change   # 看 AI 到底被告知了什么
```

如果指令里没有你的约束，说明 `config.yaml` 的 `rules.design` 或 schema 的 `instruction` 没写到位——问题在配置，不在 AI。

---

## 11. 并行开发多个变更

`changes/` 下可以同时存在多个变更目录，各自独立。高级要点：

- **每个变更是独立的 DAG 实例。** 状态、产物、delta 互不干扰。
- **命令要显式带名字。** 多变更并存时，`openspec show`、`validate`、`status`、`/opsx:apply` 都要写清变更名，否则会有歧义。
- **delta 冲突在归档时才显现。** 如果两个并行变更都 MODIFIED 同一条要求，先归档的会改主规范，后归档的可能基于旧版全文——归档前用 `openspec validate --all` 和肉眼 review 主规范。
- **建议拆分而非合并。** 把「重做整个系统」拆成多个小变更，每个独立走完流水线，比一个巨型变更好审核、好回滚。

批量操作：某些 profile 提供 `bulk-archive` 类工作流一次归档多个已完成变更；以 `openspec config profile` 和 `openspec update` 后你的工具实际显示的命令为准。

---

## 12. sync 与 archive 的区别（进阶）

小白阶段容易混淆。精确区分：

- **`sync`**：把当前变更的 delta 合并进主规范 `openspec/specs/`，但**变更目录留在原地**。用于「规范已定、代码还没写完，但想让主规范/并行工作尽早看到最新规范」。可多次 sync。
- **`archive`**：校验 → 合并 delta 到主规范 → 把整个变更目录移到 `changes/archive/<日期-名字>/`。表示「这次变更彻底结束」。

换句话说：sync 是「提前把规范部分定稿」，archive 是「收尾归档」。archive 内部通常也会做一次 sync 的合并动作。

---

## 13. 校验体系的层次

`validate` 不是单一检查，理解它的层次能更快定位问题：

```bash
openspec validate <名字>          # 单个变更或规范
openspec validate --all           # 全部变更和规范
openspec spec validate <spec-id>  # 只校验某条主规范结构
openspec change validate <名字>   # 只校验某个变更提案
openspec schema validate <名>     # 校验 schema 定义本身
```

常见校验失败原因（按频率）：

1. 场景不是正好 4 个 `#`（第 3.2 节）。
2. 某要求没有场景（每要求至少一个）。
3. delta 标题格式错（`## ADDED Requirements` 拼写/大小写）。
4. MODIFIED 引用的要求在主规范里找不到（标题对不上）。
5. schema 校验：requires 成环，或模板文件缺失。

**永远不要跳过校验直接归档**——delta 的静默失败只有校验+肉眼才能抓到。

---

## 14. 接入 CI 与自动化

所有关键读命令都有 `--json`，这让 OpenSpec 能进流水线。典型 CI 检查：

```bash
# 1. 全量校验，失败即挂 CI
openspec validate --all

# 2. 检查根解析健康
openspec doctor --json

# 3. 遍历活动变更，确认没有「假完成」（tasks 全勾但校验不过）
openspec list --json
openspec status --change <名> --json
```

自动化建议：

- **在 PR 里跑 `openspec validate --all`**，把规范格式错误挡在合并前。
- **用 `--json` 解析 status**，在 PR 描述里自动贴出每个变更的产物完成度。
- **CI 里固定 cwd 到真实根**（第 5 节），避免根解析在不同 runner 上漂移。
- **schema 变更也要校验**：`openspec schema validate <名>` 加进 CI，防止有人改坏团队工作流。

---

## 15. 升级与迁移

```bash
npm install -g @fission-ai/openspec@latest   # 升级全局包
cd your-project && openspec update            # 在每个项目重新生成 AI 指令/命令文件
```

高级注意：

- **`update` 会重写工具的命令/技能文件**，但**不会动你的 `config.yaml`、schema、changes、specs**。放心升级。
- **schema 是 experimental**，跨版本升级后建议 `openspec schema validate` 你 fork 的自定义 schema，确认字段没被改。
- **升级后斜杠命令没变**：多半是没跑 `openspec update`，或 AI 工具没重启重新扫描文件。
- **全局配置随版本可能新增字段**：`openspec config list` 看当前全部设置；不确定的键用 `openspec config unset <key>` 回到默认。

---

## 16. 高级用户排错清单

| 症状 | 可能根因 | 定位命令 |
| --- | --- | --- |
| `No artifacts ready` | 前置产物没标记完成 | `openspec status --change <名> --json` |
| 场景在归档后消失 | 场景没用 4 个 `#`，或 MODIFIED 没写全文 | `openspec validate <名>` + 肉眼 |
| AI 生成不符合团队规范 | rules/instruction 没注入到位 | `openspec instructions <产物> --change <名>` |
| 命令找不到自定义 schema | fork 到了双层目录（第 5.2 节） | `openspec schema which <名>` |
| 根解析到错误位置 | cwd 不在真实根 | `openspec doctor` |
| 主规范 MODIFIED 后丢内容 | MODIFIED 只写了片段 | 对比归档前后 `specs/` |
| 并行变更合并冲突 | 两个变更改同一要求 | `openspec validate --all` |

---

## 17. 从「会用」到「精通」的检验标准

你应该能够：

- 画出当前 schema 的产物 DAG，并解释某个产物为什么被阻塞。
- 区分 ADDED / MODIFIED / ADDED-新关注点，知道什么时候用哪个。
- 说清 delta 合并是「替换」而非「叠加」，以及它对 MODIFIED 的硬性要求。
- 用 `openspec instructions` 反查 AI 实际拿到的指令，据此调 config 而不是反复改 prompt。
- fork 一个 schema，增删产物节点，改 requires 拓扑，并通过 `schema validate`。
- 为跨端/多模块项目设计扇出-扇入的产物流水线。
- 用 stores 共享团队上下文，用 worksets 组织个人工作视图。
- 在 CI 里用 `--json` 命令做规范校验和完成度检查。
- 快速定位根解析、静默失败、schema 双层等高级陷阱。

---

## 18. 官方与延伸资料

- [OpenSpec 官网](https://openspec.dev/)
- [OpenSpec GitHub 仓库](https://github.com/Fission-AI/OpenSpec)
- [How Commands Work](https://github.com/Fission-AI/OpenSpec/blob/main/docs/how-commands-work.md)
- [CLI Reference](https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md)
- 本机内置 schema 定义：`openspec schema which spec-driven` 给出的路径下的 `schema.yaml`

> schema / store / workset 等命令目前标注 experimental，接口可能随版本变化。核对本文时以 `openspec <命令> --help` 的实际输出为准。
