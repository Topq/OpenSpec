---
name: lr-openspec-code-review
description: 按框架约定清单检查代码质量（协议契约、框架注册、Module 数据边界、红点归属、错误反馈、刷新粒度、过度设计、Localizer），按 P0/P1/P2 权重输出审查报告
---

> **SE 适配说明**：GodFort/神域防线及其返工频次是 DL 来源案例，不是 SE 当前文件或接口的证据。实际审查先读 SE `config.yaml` 路由的 ai-core，再用 SE CodeGraph/源码复验；来源案例和缺失的历史附件仅作说明，不作为必读依赖或通过依据。


# lr-openspec-code-review

> **职责**: 按项目框架约定清单逐项检查代码，发现违反约定或潜在风险的地方。同时检查完整性（应实施的模块是否存在）和质量（已实施代码是否符合框架约定）。
> **阶段**: 阶段 11a
> **依赖**: tasks.md 和 design.md 已生成（不依赖 apply 完成，可在实施过程中执行）

---

## 使用场景

**适用于**：
- 实施过程中或完成后的代码质量检查
- 提交代码前的最后检查
- 多人协作，确保所有角色遵守框架约定
- 发现实施遗漏、静默失效、性能隐患、框架 API 误用

**检查范围**：
- **完整性检查**：tasks.md 要求的模块/协议/配置是否存在
- **质量检查**：已实施代码是否符合框架约定

**不检查**：
- 命名、注释密度、排版等纯风格问题——由 SE `docs/ai-core/rules/coding_standards/` 及客户端治理文档路由的审查流程覆盖
- 业务逻辑正确性——由 `lr-openspec-test-validate` 负责

**审查边界**：
- 默认**只报告，不改代码**。用户明确要求修复时才修改。
- 一旦修改了代码，按 `schemas/lr-func-dev/rules/common/compile-verification.md` §5.3 做一次编译验证（客户端 Unity MCP 优先，服务端 MSBuild）。
- 历史代码除非本轮改动直接涉及，只报告不修改。

---

## 使用方式

```bash
/lr-openspec-code-review <change-id>          # 按变更审查
/lr-openspec-code-review <文件或目录路径>      # 按文件/目录审查
```

示例：

```bash
/lr-openspec-code-review sanctum-bulwark
/lr-openspec-code-review <SE客户端工程>/Assets/Script/UISript/<本功能>/<页面>.cs
```

---

## 执行流程

### 步骤 1：确定审查范围

按优先级选择一种方式，不要叠加。

#### 1.1 方式 A：change-id（推荐）

1. 检查 `changes/<change-id>/implementation-report.md` 是否存在。
2. 读取 `## 2. 生成文件清单` 章节，提取反引号包裹的文件名（`.cs/.cpp/.h/.txt/.xlsx`）。
3. 按角色分类：
   - 服务端：`.cpp` / `.h`
   - 客户端：`.cs`
   - 配置表：`.txt` / `.xlsx`
4. report 记录的是 apply 已验证的文件清单，无噪音优先使用。

#### 1.2 方式 B：显式路径

用户直接给了文件或目录时：

1. 目录 -> 递归收集 `.cs/.cpp/.h`；
2. 文件 -> 直接使用；
3. 逐个确认文件存在，不存在的路径在报告中标注后跳过。

#### 1.3 方式 C：工作区回退（仅当 A/B 都不可用）

先按 `config.yaml` 解析 SE 客户端和服务端路径，检测实际版本管理。SE 开发目录是 SVN 工作副本，优先 `svn status <工程绝对路径>`；只有确认目标是 Git 仓库时才用 `git -C <工程> status --porcelain`。OpenSpec 自身使用 Git，不代表外部开发工程也使用 Git。

用 tasks.md 模块/文件清单过滤本轮变更，保留空格路径，忽略无关资源与生成缓存。报告标注来源为工作区，不把无匹配当成“审查通过”。

#### 1.4 空结果处理

三种方式都拿不到文件时，直接提示：

```
未发现可审查文件：<change-id> 的 implementation-report.md 不存在，工作区也没有匹配改动。
请确认 apply 已执行，或直接用文件路径调用。
```

不生成空报告，不猜测文件。

#### 1.5 完整性对照

拿到文件清单后，与 tasks.md 的任务文件映射对比：

- tasks.md 要求、清单中没有 -> 报告“缺失实施”；
- 清单中有、tasks.md 没要求 -> 报告“额外实施，需人工确认”（可能合理）。

---

### 步骤 2：加载检查清单

按本次涉及的角色读取对应检查项文件（**不要凭记忆执行**）：

| 角色 | 文件 | 项数 |
|---|---|---|
| 服务端 | `checks/server.md` | 4 |
| 客户端 | `checks/client.md` | 12 |
| 配置表 | `checks/config.md` | 2 |

#### 权重规则

| 档位 | 权重 | 定义 | 门禁 |
|---|---:|---|---|
| **P0 阻断** | 10 | 确定性契约违反，编译失败或必然运行失败 | 不修不能合入 |
| **P1 结构契约** | 5 | 编译通过但会静默失效，或造成返工 | 必须修复或书面接受 |
| **P2 质量建议** | 1 | 性能、维护成本、可读性 | 可选 |

- **报告排序**：先按档位，同档按 GodFort 实证频次降序；索引表按 ID 排列，ID 不代表执行优先级。
- **风险分**：`10 × P0 命中数 + 5 × P1 命中数 + 1 × P2 命中数`。
- 同一问题只归一个检查项；需要交叉引用时写“另见 client-00X”。

#### 检查清单索引

**服务端（4 项）**

| ID | 检查项 | 档位 | 权重 | GodFort 实证 | 规则来源 |
|---|---|---|---:|---:|---|
| server-001 | 协议契约完整性（C2S 索引 / S2C 字段 / 两端协议 ID） | P0 | 10 | 2 | server-structure.md §1.1；本变更 design.md 的协议附录（若另有 protocol-contract.md 也一并核对） |
| server-002 | 错误反馈完整性 | P1 | 5 | 1 | server-structure.md §1.2.1；error-completion-contract.md（GodFort 示例） |
| server-003 | 配置字段名与列结构（以导出 txt 为准） | P0 | 10 | ≥3 | server-structure.md §2.1 |
| server-004 | Record 访问保护与结构（Exist / 列枚举） | P0 | 10 | 0（有列漂移） | server-structure.md §1.3.1（IRecord& + Exist） |

**客户端（12 项）**

| ID | 检查项 | 档位 | 权重 | GodFort 实证 | 规则来源 |
|---|---|---|---:|---:|---|
| client-001 | UI 框架方法签名 | P0 | 10 | 0 | client-structure.md §2.1 |
| client-003 | 红点归属与触发时机 | P1 | 5 | 4 | client-structure.md §1.5；RedPointModule.cs |
| client-004 | BusinessActivityModule 接入 | P1 | 5 | 4 | client-structure.md §1.1 |
| client-005 | 协议解析契约（索引 / 字段数 / 类型） | P0 | 10 | 3 | client-structure.md §1.4 |
| client-008 | 跨端枚举契约 | P1 | 5 | 3 | csharp_spec.md 常量规范；table.md |
| client-009 | 过度设计与职责倒置 | P1 | 5 | 19 | 项目惯例（负向清单见 checks/client.md） |
| client-010 | 刷新粒度 | P2 | 1 | 5 | ../develop/client/project/docs/ai-core/knowledge/modules/ui-management-system.md |
| client-011 | Localizer 与语言 key | P1 | 5 | 4 | ../develop/client/project/docs/ai-core/knowledge/modules/ui-management-system.md（Localizer）；apply/client-execution.md §3 |
| client-012 | 框架注册完整性（UI / DynamicConfig / 条件 / 共享枚举） | P0 | 10 | 6 | client-structure.md §2.3.1（DynamicConfigModule）；tasks/client-implementation.md §0.1 |
| client-013 | 序列化字段与 Prefab 绑定 | P1 | 5 | 5 | compile-verification.md §4.4；ui-prefab |
| client-014 | 生命周期与订阅配对 | P1 | 5 | 6 | 项目惯例；compile-verification.md |
| client-015 | Module 数据边界与 Record 注册 | P1 | 5 | 3 | ../develop/client/project/docs/ai-core/knowledge/external/soul-engine-client-bridge.md |

**配置表（2 项）**

| ID | 检查项 | 档位 | 权重 | GodFort 实证 | 规则来源 |
|---|---|---|---:|---:|---|
| config-001 | outcode_config.json 完整性 | P0 | 10 | 0 | config-structure.md 代码生成配置 |
| config-002 | 字段 S/C/A 与三层一致性 | P1 | 5 | 5 | config-structure.md §2.4/§四 |

> **已退役 ID**：client-002（并入 client-001）、client-006（并入 client-005）、client-007（交由 SE 编码规范检查）。这些编号不再复用。

---

### 步骤 3：执行检查

1. **服务端**：读 `checks/server.md`，按 server-001 ~ server-004 逐项执行。无服务端改动时，报告中写“无服务端改动”，不执行。
2. **客户端**：读 `checks/client.md`，按 client-001 / 003 / 004 / 005 / 008 / 009 / 010 / 011 / 012 / 013 / 014 / 015 逐项执行。无客户端改动时同理。
3. **配置表**：读 `checks/config.md`，按 config-001 ~ config-002 逐项执行。无配置表变更时同理。

**执行顺序**：同一端内先跑全部 P0 项，再跑 P1/P2；`client-009`（过度设计）放在最后一遍整体评估——它依赖 client-015（数据边界）和 client-014（生命周期）的结论，先跑容易把有实际消费的抽象误判为多余。只覆盖部分检查项时，未执行的项在报告中写“未执行”，不要省略。

**每项检查的产出要求**：

- 明确判定：通过 / 建议 / 违反 / 无法验证；
- 给出证据：`文件:行号` + 关键代码片段；
- 规则来源：规则文件 + 章节，或检查项 ID；
- 档位：P0 / P1 / P2；
- 无法验证时写“无法验证”并说明原因（如缺配置、缺运行环境），不要臆断通过。

**同一问题不重复报**：能归到一个检查项的，不要同时出现在两个项下；需要交叉引用时写“另见 client-00X”。

---

### 步骤 4：输出 code-review-report.md

```bash
Write(changes/{change-id}/code-review-report.md)
```

按文件路径审查（没有 change-id）时，输出到当前工作目录或用户指定路径，文件名用 `code-review-report-<文件名>-<日期>.md`。

**报告模板**：

```markdown
# {功能名} Code Review Report

**检查时间**: 2026-10-31
**检查清单**: 服务端 4 项 + 客户端 12 项 + 配置表 2 项
**文件范围**: 见 implementation-report.md（或：用户指定的 N 个文件）
**项目路径**:
- 服务端: ../develop/server/project
- 客户端: ../develop/client/project

---

## 总览

- P0 阻断：0 项
- P1 结构契约：2 项
- P2 质量建议：1 项
- 无法验证：0 项
- 风险分：10 × 0 + 5 × 2 + 1 × 1 = 11

---

## 详细发现

### P0-1：旧活动文件拉取链遗漏活动级注册

**位置**: `Assets/Script/LogicModule/GrowthFundModule.cs:42`
**检查项**: client-012
**档位**: P0 阻断
**规则来源**: client-structure.md §2.3；tasks/client-implementation.md §0.1

```csharp
// 本例明确走旧活动文件拉取链，目标活动未声明加载配置
// DynamicConfigModule_Process.InitProcessDic 内
RegisterTable(...);
// 缺少：class GrowthFundModule : IConfigSyncMethod
// 缺少：m_DynamicConfigModule.RegisterSyncMethod(this);
```

**问题**: 此旧活动文件拉取链只做表级注册，缺少目标活动的按需/提前拉取声明，无法按设计时机加载配置。数据库配置同步入口不适用此判定，应独立核查数据库请求、服务端同步和表级适配。
**建议**: 实现 `IConfigSyncMethod`，按加载时机在 `string[] fileNameList` 或 `string[] preFileNameList` 加入表名（任一名单可为空），并在 `OnInit()` 调用 `m_DynamicConfigModule.RegisterSyncMethod(this)`。

---

### P1-1：疑似过度设计

**位置**: `Assets/Script/UISript/GrowthFund/GrowthFundPage.cs:47`
**检查项**: client-009
**档位**: P1 结构契约

```csharp
m_Page.OnKeyTableReady += RefreshState;  // 处理函数未读取表版本
```

**三行证据**:
- 参照模块：`DesperateTrialTalentPanel.cs:68-69`（不监听 TableReady）
- 数据链路：事件 -> RefreshState -> 未读取表版本，无实际消费
- 删除测试：删掉后功能不变

**建议**: 删除该监听。

---

### P2-1：刷新粒度过粗

**位置**: `Assets/Script/UISript/GrowthFund/GrowthFundPage.cs:210`
**检查项**: client-010
**档位**: P2 质量建议

```csharp
void OnSelectDifficulty(int index)
{
    m_Difficulty = index;
    RefreshState();          // 重建阶段列表、队伍、背景
}
```

**建议**: 改为 `RefreshStageDetails + RefreshDifficultyList + RefreshButtons`，重复选择时提前返回。

---

## 通过的检查

### client-001 UI 框架方法签名

`GrowthFundRewardCell.cs`: `void OnCellUpdated(Transform root, int index)`。

### server-004 Record 访问保护

`MixGrowthFundModule.cpp:156`、`:203` 均在使用前判 `Exist()`。

### client-004 BusinessActivityModule 接入

`GrowthFundModule.cs:45`: `RegisterSeverActivityParamArgs(BusinessActivityType.GrowthFund, ...)`。

（按实际检查结果逐项列出，不要求复制全部 18 项。）

---

## 知识库回写建议

每条因“项目惯例”而非“代码错误”产生的问题，给出可回写的知识库条目候选；只列候选，不直接改文档。

| 问题 ID | 惯例分类 | 建议补充/校正的页面 | 建议内容（一句话） | 是否重复出现 |
|---|---|---|---|---|
| client-009 | 订阅与通知 | `reference/ui.md`「运营活动监听」 | 面板只挂 Dirty，需显示行值才加 Changed | 是 |

---

## 后续步骤

1. 人工评审建议项，决定是否修复
2. 修复后重新运行 code-review（如需要）
3. 运行 `/lr-openspec-test-validate <id>` 检查测试覆盖
```

---

### 步骤 5：输出提示

```
已生成代码审查报告：changes/<change-id>/code-review-report.md

检查结果：
- P0 阻断：0 项
- P1 结构契约：3 项
- P2 质量建议：1 项
- 风险分：10 × 0 + 5 × 3 + 1 × 1 = 16

门禁策略：P0 必须修复；P1 必须修复或书面接受；P2 可选。

下一步：
- 运行 `/lr-openspec-test-validate <change-id>` 检查测试覆盖
```

审查完成即停止。**不要自动执行 test-validate / sync / rule-candidates**，等用户显式触发。

---

## 技术要点

### 工具约定

| 用途 | 工具 | 说明 |
|---|---|---|
| 符号/调用关系 | `codegraph_explore(query, projectPath: "<工程根目录>")` | 一次拿源码和调用链；查不到再降级 |
| 文本检索 | `rg -n "<pattern>" <files>` | 统一用 ripgrep，不用 `grep -oP` |
| 读文档/配置 | `Read(<path>)` | 规则文件、outcode_config.json、生成的 TD 类 |
| git 工作区 | `git -C <repo> status --porcelain` | 用 `-C`，不要 `cd` 串联 |

CodeGraph 只能给源码，不能判断业务语义；结论必须来自阅读源码后的判断。查不到时降级到 `rg`，并在报告中标注“Grep 模糊匹配，建议确认 CodeGraph 索引是否更新”。

### 权重与排序

- **P0 阻断（10）**：不修不能合入。典型：协议契约、框架注册、序列化字段缺失、配置字段名错。
- **P1 结构契约（5）**：编译通过但静默失效或造成返工。典型：红点归属、过度设计、生命周期、Localizer 缺 key。
- **P2 质量建议（1）**：性能和维护成本。典型：刷新粒度、静态文案赋值。

排序：先档位，同档按 GodFort 实证频次降序。报告总览计算风险分，便于比较多次审查。

### 报告可操作性

每个发现项必须包含：位置（文件 + 行号）、代码片段、规则来源、问题说明、具体修改建议、档位。缺任何一项视为报告不合格。

### 检查项维护

- 检查项定义**只在 `checks/*.md` 维护**，`SKILL.md` 只保留索引表和流程；
- 新增/修改检查项时，同步更新：`checks/<role>.md` 小节 + 本文步骤 2 索引表 + `CHANGELOG.md`；
- 已退役的 ID 不复用，避免历史报告引用歧义；
- **生成期同步**：P0 子集同时写进 apply 的完成前自检（客户端 `apply/client-execution.md` §5.2、服务端 `apply/server-execution.md` §5、配置 `apply/config-execution.md` §3.4）。code-review 只做复核，不替代生成期自检。
- `schemas/lr-func-dev/rules/design/*-structure.md` 更新框架约定时，同步对应检查项。

---

## 常见问题

### Q1: 检查清单会随时间过时吗？

会。所有检查项集中在 `checks/*.md`，改一处即可；`CHANGELOG.md` 记录变更，便于回溯。规则文件更新后必须同步对应检查项。

### Q2: 如何添加新的检查项？

1. 在 `checks/<role>.md` 追加一节（目标、检查方法、违反/符合示例、报告格式、档位、权重、实证频次）；
2. 在本文步骤 2 的索引表加一行；
3. 在 `CHANGELOG.md` 记录；
4. 如果属于 P0，同步写进 apply 的生成期自检。

### Q3: CodeGraph 查询不到怎么办？

降级到 `rg` 全文检索，并在报告中标注“使用 rg 模糊匹配，建议确认 CodeGraph 索引是否更新”。

### Q4: 只想审查本次改动的几个文件？

直接用显式路径调用（见“使用方式”），跳过步骤 1.1/1.3。

### Q5: 审查时发现代码写错了，要直接改吗？

默认不改。报告写清问题和建议，由人工决定；用户明确要求修复时才动代码，并按 compile-verification.md §5.3 编译验证。

### Q6: 为什么没有 client-002 / client-006 / client-007？

- client-002（DettachPage 拼写）并入 client-001（UI 框架方法签名）；
- client-006（BA 索引起点）并入 client-005（协议解析契约）；
- client-007（类内成员顺序）交由 SE `csharp_spec.md` 与 `csharp_self.md` 按项目治理优先级检查，不导入 DL 个人风格要求。

这些编号已退役，不再复用。

### Q7: 为什么不再用“高 / 中 / 低”？

GodFort 复盘显示“高/中/低”把编译失败、确定性运行失败、静默失效、纯风格混在同一档，门禁无法执行。P0/P1/P2 分别对应“阻断 / 结构契约 / 质量建议”，并带可计算的权重。

---

## 版本信息

**版本**: v1.3.1
**创建日期**: 2026-07-24
**最近更新**: 2026-10-31
**设计哲学**: 检查项拆到 `checks/*.md`；按 P0/P1/P2 权重排序，并以 GodFort 实际返工证据校准优先级
