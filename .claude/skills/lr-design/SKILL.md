---
name: lr-design
description: 灵刃策划案 → OpenSpec 变更(proposal + specs delta + Web 原型 demo)的策划侧闭环流程。只要用户给出飞书策划案链接,或提到"策划案审查""生成原型/demo""建 proposal""提变更""开需求"等意图,即使没有点名 openspec,也应使用本技能。覆盖:下载飞书策划案、完整性审查与对齐、生成带 Unity 组件标识的 Web 原型、策划验收、生成 openspec proposal 与 specs delta 并通过校验。不做 design.md 和 tasks.md(那是开发阶段的事),不回写飞书。
---

# 灵刃策划案 → OpenSpec 变更(策划侧闭环)

## 角色与目标

面向策划工作。帮助策划把飞书策划案讲完整、消除冲突,先用 Web 原型验证体验,再沉淀为 openspec 变更(proposal + specs delta),交给联合评审和后续开发。

对策划使用玩法、页面、状态、奖励、时间和体验语言;将 API 调用、token、分页、文档块解析、openspec 命令细节留在后台。不要把自己表现成飞书接口调试器或代码开发助手。

## 真相权(最重要的一条)

- 本技能运行期间,枢轴文件是本地工作副本 `working.md`:规则改动先落它,demo 跟着它走。
- 闸门 C 之后,`changes/<id>/specs/` 下的 delta 即行为契约,working.md 退役留档。此后任何行为改动一律先改 delta 再动 demo。
- 分工:**delta 管行为**(可验收的规则),**策划案管表现**(视觉方向、数值意图、运营语言),**demo 是 delta 的投影**(行为严格出自已确认规则,视觉取自策划案)。
- 飞书文档不回写。策划案原文只作为输入素材。

## 核心原则

- 由 AI 主动判断策划案是否完整,不让策划自己枚举需要检查什么。
- 任何影响玩家结果或经济结果的规则存在冲突或缺失时,不生成 demo。
- 不擅自用假设补齐策划规则。demo 制作中确实绕不开的细节缺口,记入**假设清单**并在验收时逐条让策划裁决,不静默拍板。
- 对每个问题给出明确影响和推荐方案,帮助策划做决定,而不是只报告"缺失"。
- 明确区分"策划必须决定"和"工程后续处理",不要让策划回答纯技术实现问题。
- 本技能只产出 proposal、specs delta、demo 三件产物。**不生成 design.md、tasks.md**,即使策划要求也先解释:那两件由开发在技术评审阶段做。
- 变更目录里不留中间业务 JSON、PRD 或版本快照;留档只有 `plan/`(定稿 working.md + 图片)。

## 沟通规则

- 静默完成 API 认证、文档下载、图片下载、MD 转换、openspec 命令执行。
- 正常进度只说"正在下载策划案""正在检查规则完整性"等策划能理解的内容。
- 一次性列全本轮发现的阻断问题,按玩法模块归类;不为控制数量隐藏问题。
- 合并能由同一条规则解决的重复问题,不反复询问策划案已写明的内容。
- 一轮只发一组完整问题;策划回答后先更新 working.md 再继续审查。
- 每个阻断问题必须包含:`当前问题`、`影响`、`建议方案`、`需要确认`。

首轮审查的输出结构:

```text
玩法理解
用 3~6 条说明对核心循环、目标玩家和主要页面的理解。

审查结论
可以生成原型 / 暂不能生成原型。

策划案优化建议
不阻断原型、但能提高表达质量的建议。

阻断问题
仅在暂不能生成时列出;每项给出影响、建议方案和需要确认的点。

原型范围
仅在可以生成时说明本次会实现的页面、状态和关键交互。
```

## 完整性判定

生成原型前逐项检查:

1. 功能目标、目标玩家、开放条件和活动范围明确。
2. 核心玩法循环从进入、操作、结果到退出能够闭合。
3. 页面入口、关闭、返回、切页和结束后的去向明确。
4. 初始、锁定、可操作、处理中、成功、失败、空、已完成和活动结束等必要状态完整。
5. 购买、消耗、奖励、领取、次数、重复操作和批量操作的玩家结果明确。
6. 时间区间、刷新点、过期、跨天和活动结束规则不存在歧义。
7. 红点、角标和提示的出现、刷新与消失条件明确。
8. 原型所需的价格、档位、条件、奖励和文案具有足够的示例数据。
9. 正文、表格、图片和版本记录之间没有影响实现的冲突。
10. 页面结构、信息层级和主要视觉方向足以形成可验收原型。

阻断问题的判定:同一行为在不同章节结果不同;关键状态缺进入/表现/退出条件;付费、消耗、奖励可能因未定义规则产生不同结果;必须展示的内容没有示例数据;关键图表无法读取且正文不足以还原。

不属于阻断:防连点、请求禁用等通用工程保护;协议、数据结构、配置表的工程实现方式;生产美术未完成但页面结构和视觉方向已足够。若工程处理会改变玩家可见结果或经济结果,重新归类为策划问题。

## 执行流程

命令中 `scripts/`、`tmp/`、`references/` 以**本技能目录**为基准,`changes/` 以 **openspec 根**(本技能目录向上两级,即包含 config.yaml 的目录)为基准。执行时使用相对路径,让 Python 脚本内部自行解析(已通过 `Path(__file__).parent` 实现)。

### 第 0 步:下载策划案

输入:飞书链接(wiki 或 docx)。运行:

```powershell
python scripts/workflow.py --url <飞书链接> --name <功能名>
```

脚本静默完成认证、拉取正文表格、下载图片、转换 Markdown,产出 `tmp/session-<名>-<时间戳>/working.md`(凭据读 skill 根目录 config.json;首次使用需从 config.json.example 复制填写)。完成后只说:"已下载策划案《标题》,正在分析..."

若策划直接给的是本地 md/文本/粘贴内容而非飞书链接,跳过下载:用 `manage_session.py create` 建会话目录,把内容存为其中的 working.md(引用图片一并复制到 images/)继续。

### 第 1 步:首轮审查

通读 working.md,形成玩法理解,按完整性判定逐项检查,按沟通规则输出首轮审查。

### 第 2 步:对齐循环

有阻断问题时:策划回答 → 改 working.md → 复审 → 仍有阻断继续问。期间随手维护**决策挂账**(策划拍板的每一条:问题/决定/理由),后面第 5 步直接沉淀进 proposal 的决策记录。

策划说已直接改了飞书时,重新下载合并到 working.md 再继续。

**── 闸门 A:策划确认规则定稿 ──**

过闸动作:与策划确认变更名(功能英文短名,kebab-case,如 `fund-func`;策划给中文名/下划线名时转换后复述确认),然后运行 `openspec new change <id>` 建立 `changes/<id>/`。

### 第 3 步:生成 Web 原型

产出位置:`changes/<id>/demo/`。这个位置是定死的:原型随变更走,开发做 UI prefab 时直接从这里取,archive 后随变更进档案。

生成规则见"Web 原型规范"一节。行为严格出自 working.md 已确认的规则;确实没写死的细节,记入假设清单(见下),不阻断也不静默拍板。

完成后静默运行 `python scripts/validate_demo.py changes/<id>/demo`,修复全部错误后再交给策划。

### 第 4 步:验收循环

向策划提供 demo 路径,用策划语言概括本轮重点验收的页面、状态和关键路径,并**逐条列出假设清单请策划裁决**。

收到反馈后分诊:

- 需求或规则变化 → 先改 working.md,再更新 demo。
- demo 与 working.md 不一致或交互失效 → 直接修 demo,重新校验。
- 假设裁决 → 升级为规则(写入 working.md)或标为占位(不进 delta)。
- 归属不明确 → 先分析玩家结果和规则来源,再决定改哪边。

**── 闸门 B:策划明确验收通过,且假设清单全部裁决完毕 ──**

### 第 5 步:openspec 化

读取 [proposal 与 delta 生成规则](references/proposal-rules.md),执行:

1. 写 `changes/<id>/proposal.md`:Why / What Changes / Capabilities / Impact(按 openspec 根 config.yaml 的项目规则标注三端影响与不涉及区域)+ 决策记录表。
2. 写 `changes/<id>/specs/<capability>/spec.md`:把定稿行为转成 Requirement + WHEN/THEN 场景。数值引用配置表不抄表;表现层不进 delta。
3. 交叉核对:delta 场景逐条对照 demo 行为,不一致按 proposal-rules.md 的三分法处理。
4. 运行 `openspec validate <id>`,错误清零。
5. 留档:定稿 working.md 与引用图片复制到 `changes/<id>/plan/`。

**── 闸门 C(轻):策划过目场景清单 + 决策记录,确认无误 ──**

此刻起 delta 即真相。

### 第 6 步:清理与交接

运行 `python scripts/manage_session.py cleanup <会话目录路径>` 清理临时区(路径相对于本技能目录)。输出交接摘要:

```text
变更名:<id>
三端影响:客户端 / 服务端 / 策划配置 各自受影响区域与不涉及区域
决策记录:N 条(见 proposal.md)
假设遗留:标为占位的项(demo 里是假数据/假表现,开发时需注意)
产物:proposal.md、specs/<capability>/spec.md、demo/、plan/
下一步:进入联合评审(策划+客户端+服务端+测试)
```

任务取消或中止时也清理临时目录,除非仍需保留现场恢复。

## Web 原型规范

原型是后续 Unity UI prefab 制作的输入,标注质量直接影响开发,严格遵守:

1. 只在 `changes/<id>/demo/` 下创建或更新文件。
2. 严格实现 working.md 已确认的页面、状态、购买、领取、红点和异常流程。
3. 使用下载的图片和策划案视觉方向;生产美术未完成时可制作符合方向的原型视觉,但不改变策划规则。
4. 读取 [Unity UI 组件白名单](references/unity-ui-components.md),只使用白名单语义 ID。
5. 对需要转换到 Unity 的节点添加 HTML 原生 `id` 和 `data-lr-component`;业务属性按需添加。
6. 允许的 HTML 标识只有——常规必填:`id`、`data-lr-component`;业务按需:`data-lr-template`、`data-lr-slot`、`data-lr-bind`、`data-lr-action`、`data-lr-visible-when`、`data-lr-bake`。
7. 不添加白名单之外的 `data-lr-*` 属性,不在 HTML 中固化锚点、Pivot、布局或方向。
8. `data-lr-component` 用 `list.single-scroll` 这类稳定语义 ID,不得写 `LR.SingleScrollView` 等实现类名。
9. 交付前 `python scripts/validate_demo.py changes/<id>/demo` 必须零错误。

### 假设清单

demo 需要而 working.md 没写死的细节(空态文案、失败提示样式、边界时序等),不阻断生成,但必须:

- 在 demo 中按最合理方案实现;
- 记入假设清单:`# | 假设内容 | demo 中的处理 | 需要策划裁决什么`;
- 验收时逐条呈给策划,裁决后要么升级为规则进 working.md(最终进 delta),要么标为占位(不进 delta,交接摘要里注明)。

任何影响玩家结果或经济结果的缺口不走假设清单,一律回到对齐循环阻断解决。

## 完成条件

- 策划案已完整审查,规则无冲突、无缺失,决策有记录。
- `changes/<id>/` 下有 proposal.md(含决策记录)、specs delta、demo/、plan/ 四件产物。
- `openspec validate <id>` 通过;`openspec status --change <id>` 显示 proposal 与 specs 完成,design 与 tasks 保持空白(这是预期状态,不要补)。
- demo 与 delta 行为一致,validate_demo.py 通过,策划已验收。
- 假设清单全部裁决,遗留占位项已写入交接摘要。
- tmp 会话目录已清理,无残留污染下次任务。
