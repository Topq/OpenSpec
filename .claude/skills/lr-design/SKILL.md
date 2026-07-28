---
name: lr-design
description: 灵刃策划案 → OpenSpec 变更(proposal + specs delta + React TypeScript 原型 demo)的策划侧闭环流程。只要用户给出飞书策划案链接,或提到"策划案审查""生成原型/demo""建 proposal""提变更""开需求"等意图,即使没有点名 openspec,也应使用本技能。覆盖:下载飞书策划案、完整性审查与对齐、生成带 Unity 组件标识的 React TypeScript 原型、策划验收,再触发 lr-func-dev schema 的 proposal/specs 产物并通过校验。不做 design.md 和 tasks.md(那是开发阶段的事,由同一 schema 的后续产物接手),不回写飞书。
---

# 灵刃策划案 → OpenSpec 变更(策划侧闭环)

## 角色与目标

面向策划工作。帮助策划把飞书策划案讲完整、消除冲突,先用 React TypeScript 原型验证体验,再沉淀为 openspec 变更(proposal + specs delta),交给联合评审和后续开发。

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
- 本技能负责 demo、proposal、specs delta 三件产物,其中 proposal 和 specs 通过触发 `lr-func-dev` schema 的 proposal/specs 产物生成(见第 5 步),不是本技能直接写文件。**不生成 design.md、tasks.md**,即使策划要求也先解释:那两件由开发在技术评审阶段通过同一个 schema 的后续产物生成。
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

策划案中标题含"美术需求""美术资源"等、内容是对美术团队的资源/风格描述(素材参考图、色系、元素替换说明等)的章节,不纳入完整性判定和阻断问题扫描——那是写给美术的产出要求,不是玩法规则。生成原型时仍可从中提取视觉方向(配色、氛围)作为参考,但缺失或模糊不作为阻断依据。

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

不属于阻断:防连点、请求禁用等通用工程保护;协议、数据结构、配置表的工程实现方式;生产美术未完成但页面结构和视觉方向已足够;美术需求章节本身的缺失或模糊。若工程处理会改变玩家可见结果或经济结果,重新归类为策划问题。

## 执行流程

命令中 `scripts/`、`tmp/`、`references/` 以**本技能目录**为基准,`changes/` 以 **openspec 根**(本技能目录向上两级,即包含 config.yaml 的目录)为基准。执行时使用相对路径,让 Python 脚本内部自行解析(已通过 `Path(__file__).parent` 实现)。

### 第 0 步:下载策划案

输入:飞书链接(wiki 或 docx)。运行:

```powershell
python scripts/workflow.py --url <飞书链接> --name <功能名>
```

脚本下载前会先清空 `tmp/` 下所有历史会话目录(避免跨任务污染),再静默完成认证、拉取正文表格、下载图片、转换 Markdown,产出 `tmp/session-<名>-<时间戳>/working.md`(凭据读 skill 根目录 config.json;首次使用需从 config.json.example 复制填写)。完成后只说:"已下载策划案《标题》,正在分析..."

若策划直接给的是本地 md/文本/粘贴内容而非飞书链接,跳过下载:先运行 `python scripts/manage_session.py clean` 清空历史会话,再用 `manage_session.py create` 建会话目录,把内容存为其中的 working.md(引用图片一并复制到 images/)继续。

### 第 1 步:首轮审查

通读 working.md,形成玩法理解,按完整性判定逐项检查,按沟通规则输出首轮审查。

### 第 2 步:对齐循环

有阻断问题时:策划回答 → 改 working.md → 复审 → 仍有阻断继续问。期间随手维护**决策挂账**(策划拍板的每一条:问题/决定/理由),后面第 5 步直接沉淀进 proposal 的决策记录。

策划说已直接改了飞书时,重新下载合并到 working.md 再继续。

**── 闸门 A:策划确认规则定稿 ──**

过闸动作:与策划确认变更名(功能英文短名,kebab-case,如 `fund-func`;策划给中文名/下划线名时转换后复述确认),然后运行 `openspec new change <id>` 建立 `changes/<id>/`。

### 第 3 步:生成 React + TypeScript 原型

产出位置:`changes/<id>/demo/`，包含：
- **固定配置**（从模板复制，AI 不修改）：
  - `package.json` / `vite.config.ts` / `tsconfig.json` / `tsconfig.node.json` / `index.html`
  - `src/main.tsx` / `src/styles.css`（包含 1920×1080 画布约束）

- **AI 自由创建/修改**（src/ 目录下任意 .tsx/.ts 文件）：
  - `src/App.tsx` - 根组件
  - `src/data.ts` / `src/types.ts` - 数据与类型
  - `src/components/*.tsx` - 可复用组件（对应 Unity Cell 模板）
  - **复杂界面建议拆分**：弹窗、列表项、独立区块可拆成独立组件

生成规则见"React 原型规范"一节。行为严格出自 working.md 已确认的规则;确实没写死的细节,记入假设清单(见下),不阻断也不静默拍板。

**构建与验收**：
1. 生成后运行 `npm install`（首次）
2. 运行 `npm run build` → 产出 `demo/dist/index.html`
3. 完成后静默运行 `python scripts/validate_demo.py changes/<id>/demo`,修复全部错误后再交给策划
4. **默认在后台启动 `npm run dev`**,把可访问地址(如 `http://localhost:3000/`)直接发给策划,不要求策划自己执行命令;策划验收全程结束或会话中止时关闭该进程

### 第 4 步:验收循环

向策划提供 demo 路径,用策划语言概括本轮重点验收的页面、状态和关键路径,并**逐条列出假设清单请策划裁决**。

收到反馈后分诊:

- 需求或规则变化 → 先改 working.md,再更新 demo。
- demo 与 working.md 不一致或交互失效 → 直接修 demo,重新校验。
- 假设裁决 → 升级为规则(写入 working.md)或标为占位(不进 delta)。
- 归属不明确 → 先分析玩家结果和规则来源,再决定改哪边。

**── 闸门 B:策划明确验收通过,且假设清单全部裁决完毕 ──**

### 第 5 步:openspec 化

不再自己写 proposal.md 和 specs delta,而是触发 openspec 根 config.yaml 声明的自定义 schema(`lr-func-dev`)生成:

1. 留档:定稿 working.md 与引用图片复制到 `changes/<id>/plan/`(必须先做,proposal 产物读取的是这份留档,不是 tmp 会话目录里的临时文件)。
2. 生成 proposal:运行 `openspec instructions proposal --change <id>`,按输出的 `<instruction>` 块执行,写 `changes/<id>/proposal.md`。
3. 生成 specs:运行 `openspec instructions specs --change <id>`,按输出的 `<instruction>` 块执行,写 `changes/<id>/specs/<capability>/spec.md`。
4. 交叉核对:delta 场景逐条对照 demo 行为,不一致按 [proposal 与 delta 生成规则](references/proposal-rules.md)的三分法处理。
5. 运行 `openspec validate <id>`,错误清零。

[proposal 与 delta 生成规则](references/proposal-rules.md)仍然是权威规则来源——`openspec instructions` 输出的 `<instruction>` 内容与该文档保持一致,该文档描述"为什么这样写",instruction 输出描述"这次具体写什么"。两者对不上时以 instruction 输出为准(它反映的是 schema 当前版本),并回头检查该文档是否需要同步更新。

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

## React 原型规范

原型是后续 Unity UI prefab 制作的输入,标注质量直接影响开发,严格遵守:

### 1. 文件组织

**固定配置**（从 `templates/react-demo/` 模板复制，**AI 不得修改**）：
- `package.json`、`vite.config.ts`、`tsconfig.json`、`tsconfig.node.json`
- `index.html`、`src/main.tsx`
- `src/styles.css` - 包含 **强制 1920×1080 画布约束**

**AI 自由创建/修改**（`src/` 目录下任意 `.tsx` / `.ts` 文件）：
- `src/App.tsx` - 根组件
- `src/data.ts` - 业务数据（从 working.md 提取）
- `src/types.ts` - TypeScript 类型定义
- `src/components/*.tsx` - 可复用组件（可选）

**拆分原则**：
- 简单界面（<5个交互元素）：可保持单文件 `App.tsx`
- 复杂界面（≥5个弹窗/多层 Tab/复用列表项）：**建议拆分**
  - 弹窗 → 独立组件（如 `PurchaseModal.tsx`）
  - 列表项 → 独立组件（如 `RewardCell.tsx`，对应 Unity 的 Cell Prefab）
  - 独立区块 → 独立组件（如 `FundHeader.tsx`）

### 2. 画布尺寸约束（强制）

**所有原型必须在固定的 1920×1080 画布内设计**。

**原因**：
- Unity Canvas 参考分辨率是 1920×1080
- 后续坐标自动化提取需要固定尺寸基准
- 保证策划验收时看到的布局与最终 Unity UI 一致

**实现方式**（已在模板 `src/styles.css` 中定义）：
```css
#root {
  width: 1920px;
  height: 1080px;
  overflow: hidden;
  position: relative;
}
```

**禁止修改** `#root` 的 width/height。

### 3. 标注规范

严格实现 working.md 已确认的页面、状态、购买、领取、红点和异常流程。

使用下载的图片和策划案视觉方向;生产美术未完成时可制作符合方向的原型视觉,但不改变策划规则。

读取 [Unity UI 组件白名单](references/unity-ui-components.md)，只使用白名单语义 ID。

**JSX 属性标注**（与 HTML 版本完全相同）：
- **常规必填**：`id`、`data-lr-component`
- **业务按需**：`data-lr-template`、`data-lr-slot`、`data-lr-bind`、`data-lr-action`、`data-lr-visible-when`、`data-lr-bake`
- **示例**：
  ```tsx
  <button 
    id="btn-purchase"
    data-lr-component="control.button"
    data-lr-action="purchase-fund"
    onClick={handlePurchase}
  >
    购买
  </button>
  ```

**禁止**：
- 添加白名单之外的 `data-lr-*` 属性
- `data-lr-component` 写实现类名（如 `LR.SingleScrollView`），必须用语义 ID（如 `list.single-scroll`）

### 4. 调试控制台（强制）

demo 必须自带一个悬浮调试控制台,让策划不依赖真实触发条件就能切换状态验收,而不是只能被动看初始数据。控制台本身不算业务组件,不需要 `data-lr-component` 标注,仅用按钮驱动 demo 内部 state。

**文件名固定为 `src/components/DebugConsole.tsx`**(不可改名、不可拆成多个文件)。这是后续 `lr-openspec-ui-prefab` 识别并跳过该文件的唯一依据,改名会导致调试代码被误当成业务节点分析。

按需覆盖的操作类型(按 working.md 已确认的状态机来定,不是每个都要有):
- **推进条件进度**:如 +N 次抽卡/孵蛋、跳到指定档位解锁
- **领取类动作**:单档领取、一键领取全部、清空领取记录(重置)
- **购买态切换**:模拟购买成功、切回未购买
- **阶段切换**:售卖中 / 售卖结束 / 领取期结束等 `phase` 之间切换
- **多实例场景**:多个基金/多个 Tab 场景下,分别提供各自的操作或统一批量操作

放置于页面固定定位(如 `position: fixed; bottom` ),不占用 1920×1080 画布内的业务布局区域。

### 5. 验证与构建

交付前必须通过：
1. **属性校验**：`python scripts/validate_demo.py changes/<id>/demo` 零错误
2. **构建验证**：`npm run build` 成功产出 `demo/dist/`
3. **画布验证**（在浏览器 DevTools 中）：
   ```javascript
   document.getElementById('root').getBoundingClientRect()
   // 应返回：{ width: 1920, height: 1080, ... }
   ```

### 假设清单

demo 需要而 working.md 没写死的细节(空态文案、失败提示样式、边界时序等),不阻断生成,但必须:

- 在 demo 中按最合理方案实现;
- 记入假设清单:`# | 假设内容 | demo 中的处理 | 需要策划裁决什么`;
- 验收时逐条呈给策划,裁决后要么升级为规则进 working.md(最终进 delta),要么标为占位(不进 delta,交接摘要里注明)。

任何影响玩家结果或经济结果的缺口不走假设清单,一律回到对齐循环阻断解决。

## 完成条件

- 策划案已完整审查,规则无冲突、无缺失,决策有记录。
- `changes/<id>/` 下有 proposal.md(含决策记录)、specs delta、demo/、plan/ 四件产物。
- `openspec validate <id>` 通过;`openspec status --change <id>` 显示 proposal 与 specs 完成,design-*/design/test-cases/tasks 保持 blocked(这是预期状态,由后续技术评审阶段的 schema 产物接手,不要在本技能里补)。
- demo 与 delta 行为一致,validate_demo.py 通过,策划已验收。
- 假设清单全部裁决,遗留占位项已写入交接摘要。
- tmp 会话目录已清理,无残留污染下次任务。
