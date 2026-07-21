# openspec 化规则:从定稿 working.md 到 proposal + delta

本文是 lr-design 第 5 步(openspec 化)的执行规范。输入是闸门 B 之后的定稿 `working.md`、对齐循环的决策挂账、假设清单裁决结果;输出是 `changes/<id>/proposal.md` 和 `changes/<id>/specs/<capability>/spec.md`,以 `openspec validate <id>` 清零为完成标志。

## 变更名

- 用功能的英文短名,kebab-case:基金功能 → `fund-func`,公会战 → `guild-war`。
- CLI 硬性拒绝下划线(`fund_func` 会直接报错),也不接受中文名。
- 名字在闸门 A(规则定稿)时和策划确认;策划给了下划线或驼峰形式就静默转成 kebab 并复述一遍。
- 用 `openspec new change <id>` 创建骨架,不要手工 mkdir。

## proposal.md

沿用 CLI 模板的四段结构,不增删标题:

```markdown
## Why
## What Changes
## Capabilities
### New Capabilities
### Modified Capabilities
## Impact
```

各段规则:

- **Why**:从策划案的立项动机提炼,2~4 句。写玩法目标和玩家价值,不写实现。
- **What Changes**:按玩家可感知的变化列条目。
- **Capabilities**:按业务能力划分(fund、guild-war),禁止按客户端/服务端/配置/QA 分层——这是 config.yaml 的项目规则。每个 New Capability 对应一个 `specs/<name>/spec.md`。只有当 `openspec/specs/` 下已存在同名能力且本次改其行为时才填 Modified。
- **Impact**:必须分别写明 客户端 / 服务端 / 策划配置 三端各自受影响的区域,以及**本次明确不涉及的区域**。三端职责边界见 openspec 根 config.yaml。

### 决策记录(附加段)

模板四段之后追加 `## 决策记录`,把对齐循环和假设清单裁决中策划拍板的每一条沉淀进来:

```markdown
## 决策记录

| # | 问题 | 决定 | 理由 |
|---|------|------|------|
| 1 | 基金到期未领取是否过期作废 | 永久保留,不作废 | 避免付费投诉 |
```

联合评审直接看这张表,不用重新吵一遍。只记"策划必须决定"的项;工程实现问题不进这张表。

## specs delta

### 判断 ADDED 还是 MODIFIED

- 先看 `openspec/specs/` 下有没有这个能力的既有 spec。没有(目前项目基线为空,绝大多数情况)→ 一律 `## ADDED Requirements`。
- 有既有 spec 且本次改变其行为 → `## MODIFIED Requirements`,并且写**修改后的完整 requirement 全文**,不是只写差异。

### 格式

```markdown
## ADDED Requirements

### Requirement: <行为名>
<一句 SHALL 陈述>

#### Scenario: <场景名>
- **WHEN** <触发条件或玩家操作>
- **THEN** <可观察的结果>
```

硬性格式点(validate 会查):

- Requirement 正文必须含 SHALL。
- 每个 Requirement 至少一个 Scenario。
- WHEN/THEN 用 `- **WHEN**` 加粗形式。可用 **AND** 补充;前置条件写进 WHEN 或用 GIVEN。

### 内容边界(比格式更重要)

只写**行为层**——可观察、可测试、可验收的玩家/系统结果:

- 进不进:**数值不进,规则进**。"档位 6/30/68 元"不进 spec,写"按配置表档位购买";但"到期未领取永久保留"是规则,进。
- 表格不进:策划案里的奖励表、档位表引用一句"见策划配置基金档位表",不抄内容。
- 表现不进:视觉方向、布局、动效、文案措辞留在 working.md(plan/ 留档)和 demo 里。
- 实现不进:协议字段、存储结构、类名、红点实现方式都不写。红点**何时出现/消失**是行为,进;**怎么实现**不进。

### 场景覆盖

每个 Requirement 对照检查:正常流、失败流(条件不足、货币不足)、边界(等级临界、活动结束瞬间)、异常(断线重连后的状态)。对齐循环里策划确认过的每条规则都应能在 delta 里找到落点;找不到落点的规则说明场景漏了。

## 交叉核对(写完 delta 后、validate 前)

逐条对照 delta 场景与 demo 行为:

1. delta 有、demo 有 → 行为一致才算过。
2. delta 有、demo 没实现 → demo 补,或在交接摘要里标注"demo 未覆盖场景"。
3. demo 有、delta 没有 → 要么是表现层(不用进 delta),要么是漏写的行为(补 delta),要么是 demo 越权发明的规则(改 demo)。逐个归类,不许跳过。

假设清单里被裁决为"占位"的项,不进 delta;被升级为规则的项,必须进 delta。

## 完成标准

- `openspec validate <id>` 通过,无 error 无 warning。
- `openspec status --change <id>` 显示 proposal、specs 两项 complete(design/tasks 留空是本 skill 的预期状态,不要去补)。
- 策划过目场景清单 + 决策记录(闸门 C)。
