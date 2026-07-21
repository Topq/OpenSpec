---
name: lr-openspec-tasks
description: 设计评审阶段完成后，自动触发 lr-openspec-design-merge 合并 design/client.md、design/server.md、design/config.md 为 design.md（含 Open Questions 硬性检查），再读取合并后的 design.md + specs/*.md（可选参考 demo/*.html），并行生成 tasks.md（实现任务清单，供 openspec apply 执行）和 test-cases.md（验收测试用例，人工/QA 使用）。是 lr-openspec-design-merge 之后、openspec apply 之前的衔接环节。
---

# OpenSpec Tasks 生成器

## 角色与目标

面向设计评审完成、开始实现之前的阶段。本 skill 每次运行都会先触发一次 `lr-openspec-design-merge`（重新合并当前的 design/*.md 并做 Open Questions 硬性检查），合并成功后再读取合并出的 `design.md` 和 specs，输出两份并行产物：

- `tasks.md`：OpenSpec 原生 artifact，`openspec apply` 靠它的 checkbox 追踪实现进度
- `test-cases.md`：非原生 artifact，供人工/QA 对照验收，不受 `openspec apply` 追踪

本 skill 只做任务拆解和验收用例生成，不做设计决策，不执行任何代码生成或 Prefab 生成。

## 核心原则

- `tasks.md` 里的每一条任务只是一段描述文字，本 skill 运行期间不会因为写了这条任务就去生成代码——真正的代码生成发生在 `openspec apply` 执行这个 checkbox 的时候，跟其他 `[Server]`/`[Config]` 任务的执行时机完全一致，UI 相关任务没有任何特殊之处
- `tasks.md` 和 `test-cases.md` 是两个独立产物，回答不同的问题：`tasks.md` 回答"怎么做"（面向实现），`test-cases.md` 回答"验证什么"（面向 specs 的验收场景），两者都只读 `design.md` 和 specs，互不依赖，可以视为并行生成
- 本 skill 只依赖合并后的单一 `design.md`，不单独读取 `design/*.md`——`design.md` 是 `lr-openspec-design-merge` 装配出来的完整文件（精简叙事 + 三份详细设计的完整附录），是唯一权威、完整的输入源
- 本 skill 不做设计决策，也不会自己判断 Open Questions 是否解决——那是 `lr-openspec-design-merge` 的职责，见下方"与 lr-openspec-design-merge 的关系"
- Prefab 生成、UI 样式/布局调整不属于本 skill 的产物范围，即使读取了 demo 也不会为此生成任务

## 与 lr-openspec-design-merge 的关系

`design/client.md`、`design/server.md`、`design/config.md` 是持续可编辑的源文件，评审后可能被再次修改；`design.md` 是从它们装配出来的产物，用来保证 `lr-openspec-tasks` 读到的始终是当前最新版本，**本 skill 每次运行都无条件先触发一次 `lr-openspec-design-merge`**，重新读取当前的 design/*.md 并重新装配 design.md，而不是检查一个旧的 design.md 是否"足够新"。

选择"每次都重新合并"而不是"检测是否过期再决定要不要合并"，是因为过期检测天然不可靠：文件系统的修改时间会被 git checkout、跨机器同步、批量生成等操作打乱，不能反映"内容有没有真的被改过"。既然重新合并的成本不高，而且 `lr-openspec-design-merge` 本身是幂等的（同样的 design/*.md 输入会产生同样的 design.md 输出），直接每次都跑一遍，比维护一套不可靠的过期检测更简单也更可靠。

`lr-openspec-design-merge` 在合并前有一道硬性检查：三份详细文档的 Open Questions 必须全部回答，且回答质量合格。**本 skill 不会重新做这个检查，也不会在检查失败时自己代为合并或绕过**。原因是两个 skill 的职责必须保持单一：`lr-openspec-design-merge` 是评审闸门，决定"能不能进入实现阶段"；`lr-openspec-tasks` 只负责"设计已经冻结的前提下怎么拆任务"。如果 `lr-openspec-tasks` 自己重新实现一遍简化版的检查逻辑，等于给这道闸门开了后门。

所以第 0 步触发合并后，只需要确认一件事：**合并是否成功**。判断依据是合并后的 `design.md` 是否存在、且其 `## Open Questions` 顶层章节为空——因为 `lr-openspec-design-merge` 的设计是"检查不通过就不会走到生成 design.md 这一步"，所以只要 design.md 被更新且 Open Questions 章节为空，就代表合并链路走完了整个闸门。如果合并失败（`lr-openspec-design-merge` 输出了阻断信息，没有生成合规的 design.md），本 skill 直接中止，转发阻断信息，不生成任何文件。

## 执行流程

### 第 0 步：触发合并并验证结果（严格中断）

1. 无条件触发 `lr-openspec-design-merge`（不做任何"是否需要合并"的判断，每次都跑）
2. `lr-openspec-design-merge` 内部会先检查三份详细文档的 Open Questions 是否全部解决——这是它自己的硬性门槛，不通过就不会生成合规的 design.md，会直接输出阻断信息
3. 合并完成后，检查结果：
   - `changes/<id>/design.md` 是否存在
   - `design.md` 的 `## Open Questions` 顶层章节是否为空
4. 检查 `changes/<id>/specs/*.md` 是否存在（至少一个 capability 目录下有 spec.md）

**中断条件**（任一满足即中止，不生成任何文件）：

1. `lr-openspec-design-merge` 输出了阻断信息（说明 Open Questions 未全部解决或回答质量不合格）
2. 合并后 `design.md` 不存在，或其 Open Questions 章节仍有内容
3. `specs/*.md` 不存在

中止时输出：

```text
❌ lr-openspec-tasks 中止

原因：lr-openspec-design-merge 未能成功合并 design.md
     （通常是因为 design/*.md 的 Open Questions 尚未全部解决）

详情：
  [转发 lr-openspec-design-merge 的阻断信息]

下一步：
  回到评审，针对未解决的问题给出明确、完整、可执行的答案，
  更新 design/[client|server|config].md，然后重新运行本 skill
  （本 skill 会自动重新触发 lr-openspec-design-merge）
```

这是硬性中断，不允许带警告继续执行，不允许本 skill 自己代为合并或跳过检查。理由见上方"与 lr-openspec-design-merge 的关系"。

### 第 1 步：读取输入

- `design.md` —— 合并后的完整文档：精简架构叙事（Context/Goals/Decisions/Risks）+ 三份详细设计的完整附录（附录 A 客户端、附录 B 服务端、附录 C 配置表），Open Questions 章节应为空
- `specs/*.md` —— 验收场景，WHEN/THEN 格式，按 capability 分目录
- `demo/*.html`（可选，仅当 `changes/<id>/demo/` 目录存在时读取）——只读取以下已冻结白名单内的属性，用于定位某个 UI Panel/Page 对应哪些标注节点：
  - `data-lr-component`（组件语义类型）
  - `data-lr-bind`（数据绑定意图）
  - `data-lr-action`（操作意图）
  - `data-lr-visible-when`（可见性意图）
  - `data-lr-template` / `data-lr-slot`（模板与插槽标识）
  - `data-lr-bake`（Prefab 烘焙时的结构处理方式，仅用于识别节点，不在本 skill 中执行烘焙）

  不解析 CSS 样式、不推导布局、锚点、位置——这些信息属于策划验收 Web Demo 阶段就该定案的范畴，本环节不重新决策，也用不上（`tasks.md` 里的 UI 骨架任务只需要"有哪些字段、字段是什么类型"，不需要"字段长什么样、放哪里"）。

### 第 2 步：并行生成 tasks.md 和 test-cases.md

两者都只读第 1 步的输入，互不依赖，视为两个独立的生成任务。

#### 2.1 tasks.md 生成规则

输出路径：`changes/<id>/tasks.md`

**格式要求**（硬性约束，`openspec apply` 依赖这个格式追踪进度）：

```markdown
## N. 分组标题

- [ ] N.1 [分类标签] 任务描述
- [ ] N.2 [分类标签] 任务描述
```

- 每条任务必须是 `- [ ] N.M 描述` 的 checkbox 格式，不用这个格式的任务不会被 `openspec apply` 追踪
- 分类标签固定五种，写在任务描述最前面：`[Contract]`、`[Config]`、`[Server]`、`[Client]`、`[Integration]`（`config.yaml` 的 tasks 规则定义的强约束，不得增减或改名）
- 每个实现任务必须写明目标工程或目标路径（比如 `FsGame/ActivityModule/BusinessActivity/GrowthFund/` 或 `Assets/Script/LogicModule/GrowthFundModule/`）
- `[Integration]`（跨端联调）任务组必须排在所有其他分类任务组之后

**任务组划分**：按 design.md 的模块/功能点分组，通常对应：
- 一个 `[Contract]` 组：协议号分配、字段定义对齐
- 一个 `[Config]` 组：配置表新增/字段补充（依据 design.md 附录 C 的"设计阶段配置表变更"）
- 一个或多个 `[Server]` 组：按 design.md 附录 B 的模块划分
- 一个或多个 `[Client]` 组：按 design.md 附录 A 的模块/Panel/Page 划分
- 一个 `[Integration]` 组：跨端联调验证

**UI 相关的 [Client] 任务**：每个 Panel/Page 固定拆成三条子任务，不再拆更细：

```markdown
- [ ] N.1 [Client] 生成 {XxxPanel}.cs 骨架
  目标路径：Assets/Script/UIScript/{XxxPanel}/{XxxPanel}.cs
  依据：design.md 附录 A 的 UI 设计章节 + demo/{xxx}.html 的 data-lr-* 标注（如果 demo 存在）
  内容：按命名约定生成成员变量声明（如 data-lr-bind="title" → m_TxtTitle: Text）和空方法签名
  说明：这条任务描述本身不执行代码生成，只有当 openspec apply 执行这条 checkbox 时才会真正生成代码，
        这跟其他 [Server]/[Config] 任务的执行时机完全一致，不是特殊情况

- [ ] N.2 [Client] 实现 {XxxPanel} 状态机与交互逻辑
  目标路径：Assets/Script/UIScript/{XxxPanel}/{XxxPanel}.cs
  依据：design.md 附录 A 的"状态机"和"交互流程"章节

- [ ] N.3 [Client] 实现 {XxxPanel} 协议收发
  目标路径：Assets/Script/UIScript/{XxxPanel}/{XxxPanel}.cs（或对应 Module 文件）
  依据：design.md 附录 A 的"协议定义"章节
```

如果某个模块没有 demo 可参考（比如纯后台逻辑模块，没有 UI），第一条任务改为直接依据 design.md 附录 A 的模块定义章节生成骨架，不提 demo。

**明确禁止出现的任务类型**（不做的事）：

- ❌ 不得出现任何"生成 Prefab""创建 GameObject""绑定字段到 Prefab"类任务。Prefab 生成是 `openspec apply` 完成之后由另一个独立的 skill 处理，不受 `openspec apply` 追踪，不属于 OpenSpec 原生结构的一部分，不应该出现在 `tasks.md` 里。
- ❌ 不得出现"设计 UI 样式""调整布局""确定锚点/位置"类任务。样式和布局已经在策划验收 Web Demo 阶段定案，`tasks.md` 阶段只消费已确定的语义标注（组件类型、绑定意图），不重新决策视觉细节。

#### 2.2 test-cases.md 生成规则

输出路径：`changes/<id>/test-cases.md`

test-cases.md 不是 OpenSpec 原生 artifact，`openspec validate` 不检查它，格式相对自由，但按以下默认模板生成：

```markdown
# Test Cases: {变更名}

## 功能点：{spec 目录名，如 growth-fund-claim}

### 场景 1：{spec.md 中 Scenario 的标题}

- **前置条件**：[从 GIVEN 提取]
- **操作步骤**：[从 WHEN 提取]
- **预期结果**：[从 THEN 提取]
- **验证点**：
  - [从 design.md 的 Decisions 章节或附录 A/B/C 提取的技术验证细节，
    比如协议号、错误码、Record 表字段、配置表字段]
- **来源**：specs/{spec目录名}/spec.md - {Requirement 标题} - {Scenario 标题}

### 场景 2：...
```

- 按 `specs/*.md` 的目录结构分组，一个 spec 目录（一个 capability）对应一个"功能点"分组
- 每条 `#### Scenario` 场景生成至少一条测试用例，`GIVEN` → 前置条件，`WHEN` → 操作步骤，`THEN` → 预期结果
- "验证点"字段从 `design.md` 中提取技术细节作为补充（比如"验证协议返回码 XXX_ERR_ALREADY_CLAIMED=1004"、"验证 GROWTH_FUND_OPEN_REC 新增一行"），让测试用例不止是复述 specs，还能落到可核对的技术信号
- "来源"字段必须精确到具体是哪个 spec 文件的哪个 Requirement 下的哪个 Scenario，方便测试用例和验收场景对得上

### 第 3 步：test-cases.md 完整性自检（仅警告，不阻断）

- 遍历 `specs/*.md` 的所有 `#### Scenario` 场景
- 检查每个场景是否在生成的 `test-cases.md` 里有对应的测试用例（按"来源"字段回溯匹配）
- 缺失场景只输出警告清单，不阻断流程：

```text
⚠️ test-cases.md 完整性检查

以下 specs 场景未在 test-cases.md 中找到对应测试用例：
  - specs/growth-fund-xxx/spec.md - {Requirement} - {Scenario}
  - ...

说明：某些场景可能是纯技术实现细节，不一定需要独立测试用例。
      请人工评审时确认这些缺失是否合理。
```

不设置任何人工豁免标记机制（比如不提供"标记为不需要用例"的功能），这次先不扩展，后续视实际使用情况再决定是否需要。

### 第 4 步：运行 openspec validate

运行 `openspec validate <id>`，检查范围：

- `tasks.md` 的结构（checkbox 格式、`[Contract]`/`[Config]`/`[Server]`/`[Client]`/`[Integration]` 分类标签、`[Integration]` 排在最后）
- 复检 `proposal.md`、`specs/*.md`、`design.md` 是否仍然合法

**明确说明**：`test-cases.md` 不在 `openspec validate` 的覆盖范围内。它的完整性检查是本 skill 第 3 步自己做的，不是 OpenSpec 原生机制的一部分——`openspec validate` 只认 schema 里定义的 artifact（`proposal`/`specs`/`design`/`tasks`），`test-cases.md` 不是其中之一。

如果 validate 失败，修复 `tasks.md` 中的结构问题后重新运行，直到通过。

### 第 5 步：输出交接摘要

```text
变更名: <id>

tasks.md 生成完成:
  - 共 N 个任务组，M 个任务
  - 分类：[Contract] X 个，[Config] Y 个，[Server] Z 个，[Client] W 个，[Integration] V 个

test-cases.md 生成完成:
  - 共 K 个功能点，L 条测试用例
  - 完整性检查: ✅ 所有 specs 场景已覆盖
                / ⚠️ 缺少 N 个场景对应用例（见上方清单）

openspec validate: ✅ 通过

下一步: 人工联合评审
  1. 评审 tasks.md：任务拆分是否合理？目标路径是否正确？跨端联调顺序是否恰当？
  2. 评审 test-cases.md：验收场景覆盖是否完整？验证点是否可核对？
  3. 评审通过后，运行 openspec apply <id> 开始实施
```

## 完成条件

- `changes/<id>/tasks.md` 已生成，符合 OpenSpec checkbox 格式和 `config.yaml` 的分类约束
- `changes/<id>/test-cases.md` 已生成，覆盖 specs 的验收场景
- 完整性自检已执行（警告级，不阻断）
- `openspec validate <id>` 通过
- 输出交接摘要，明确"tasks 生成完成，等待人工联合评审，评审通过后可以 openspec apply"

## 不做的事

- 不做设计决策（假设 design 已经冻结，只负责任务拆解）
- 不重新检查 Open Questions 的具体内容（那是 `lr-openspec-design-merge` 内部的职责；本 skill 只确认合并链路是否成功完成，见上方"与 lr-openspec-design-merge 的关系"）
- 不跳过 `lr-openspec-design-merge`（每次运行都无条件先触发一次，不允许因为"看起来没改过"就跳过合并）
- 不生成任何 UI 脚本代码、Prefab 或其他实现产物（本 skill 只生成任务描述和测试用例文档，实际代码生成发生在 `openspec apply` 阶段）
- 不生成"生成 Prefab"类任务（Prefab 生成是 apply 之后的独立 skill 职责）
- 不生成"设计 UI 样式/布局"类任务（已在策划验收阶段定案）
- 不修改 `design.md`、`design/*.md`、`specs/*.md`（只读取；`design.md` 由 `lr-openspec-design-merge` 负责写入）
- 不为 test-cases.md 的完整性检查提供人工豁免标记机制

## 路径约定

- **openspec 根**：包含 config.yaml 的目录
- **changes 目录**：`<openspec根>/changes/<id>/`
- **合并后设计**（唯一读取的设计输入）：`<changes目录>/design.md`
- **详细设计源文件**（由 `lr-openspec-design-merge` 读取，本 skill 不直接读取）：`<changes目录>/design/*.md`
- **验收场景**：`<changes目录>/specs/*/spec.md`
- **Web 原型**（可选）：`<changes目录>/demo/*.html`
- **任务清单**：`<changes目录>/tasks.md`
- **测试用例**：`<changes目录>/test-cases.md`

所有路径引用使用相对路径，不使用绝对路径。

## 使用场景

```
完整链路：
1. lr-design 生成 proposal + specs delta + demo（策划侧闭环）
2. lr-openspec-design 生成 design/client.md + design/server.md + design/config.md（技术评审准备）
3. 前端/后端/策划联合评审，直接修改 design/*.md 反映评审结果
4. lr-openspec-tasks（本 skill）启动：
   a. 无条件先触发 lr-openspec-design-merge
      （内部硬性检查 design/*.md 的 Open Questions 全部解决，通过后装配 design.md）
   b. 若合并失败则中止；若成功则继续
   c. 只读取合并后的 design.md，并行生成 tasks.md + test-cases.md
5. 人工联合评审 tasks.md + test-cases.md
6. openspec apply <id> 按 tasks.md 逐条实施
7. （apply 完成后）独立 skill 处理 Prefab 生成，读取已完成的 UI 脚本和 demo，不属于本链路
```
