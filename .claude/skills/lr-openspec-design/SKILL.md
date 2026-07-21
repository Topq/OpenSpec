---
name: lr-openspec-design
description: 从 proposal.md 和 specs/*.md 生成 design-client.md、design-server.md、design-config.md 三件套，用于技术评审准备。只做 design 生成，不做 tasks（那是人工评审通过后的事）。输入是已通过 openspec validate 的 proposal + specs，输出是对齐的三端 design 文档。
---

# OpenSpec Design 生成器

## 角色与目标

面向技术评审阶段。输入是策划侧已完成的 proposal + specs delta（来自 lr-design 或手工编写），输出是前后端工程师和策划联合评审用的三端 design 文档。

本 skill 只做 design 生成，不做 tasks 生成（那是评审通过后的事）。

## 核心原则

- design 文档从 proposal.md 和 specs/*.md 生成，不依赖 demo 或策划案原文。
- 三端 design 必须对齐：Record 表、协议、配置表的定义在三份文档中必须一致。
- 设计阶段发现的配置表变更（proposal 未提及）必须在 design-config.md 的专门章节记录。
- 协议号写 `{待自动分配}`，不手动指定具体数值。
- 错误码客户端和服务器各自定义，数值必须对齐。
- 伪代码只写关键函数签名和核心逻辑，不需要完整实现。
- Open Questions 只记录需要评审决策的问题，不记录已在 proposal/specs 中明确的内容。

## 文档写作规范

### 避免写"与旧版本的差异"

**禁止**：在 design 文档中写"⚠️ 与本文档旧版本的差异"/"旧版本设计了 XXX，现在发现是 YYY"这类对比。

**原因**：
- 评审者看不到"旧版本"，这类对比对他们没有意义
- 随时间腐烂：文档多次修订后"旧版本"指代不清
- 和 Open Questions 重复：这类差异本质上是"我以前以为 X，现在发现是 Y"的纠错过程脚手架

**正确做法**：

1. **直接陈述当前设计**：
   ```markdown
   ❌ 错误：旧版本设计了独立的购买协议，实际是通过 Record 表感知
   ✅ 正确：购买成功通过 GROWTH_FUND_OPEN_REC 表变化感知，无专属购买结果协议
   ```

2. **proposal 期望 vs 代码实际支持的对比**，集中放在一个表格里（适用于配置表字段差异）：
   ```markdown
   ## ⚠️ 设计阶段配置表变更（相对 proposal 的差异）
   
   | proposal 字段 | 代码实际情况 | 差异说明 | 状态 |
   |---|---|---|---|
   | 基金ID | 无独立"基金ID" | proposal 设想二级关系，实际一一对应 | ⚠️ 待评审确认 |
   | 价格 | 无此字段 | 价格由 RechargeId 关联充值表 | ⚠️ 跨表查询 |
   ```

3. **需要评审决策的点**，归并进 Open Questions：
   ```markdown
   ❌ 错误：旧版本设计了独立红点枚举，实际不需要
   ✅ 正确：在 Open Questions 里写"红点系统是否满足 proposal 要求的三级体系？"
   ```

4. **重要的架构性说明**，用"说明"/"关键架构说明"段落：
   ```markdown
   **关键架构说明**：这张表不含"条件是否达成"的字段，条件达成状态完全委托给 ActivityGoalModule。
   ```

5. **跨文档引用**，避免同一份差异分析散落多处：
   ```markdown
   **说明**：结构体不含"价格"/"类型"/"互斥组"字段，完整的字段差异对照见 [design/config.md](design/config.md) 的"字段差异对照表"。
   ```

### 真正有价值的对比维度

design 文档应该保留的唯一对比维度是：**"proposal 期望 vs 代码实际支持"**

这是评审要决策的真实差异（业务期望 vs 技术现实），不是写作者的纠错历史。

## 执行流程

### 第 0 步：输入验证

确认输入：
- `changes/<id>/proposal.md` 存在且包含 Why / What Changes / Capabilities / Impact / 决策记录
- `changes/<id>/specs/` 下至少有一个 capability 的 spec.md
- 运行 `openspec validate <id>` 确保 proposal 和 specs 通过校验

如果 validate 失败，停止并报告错误。

### 第 0.5 步：获取 OpenSpec 指令

运行 `openspec instructions design --change <id>`，获取：
- **project_context**：工程路径（客户端、服务端、策划配置）
- **rules**：设计规则（跨端功能描述要求、Open Questions 要求）
- **template**：design.md 标准结构（Context / Goals / Decisions / Risks）
- **dependencies**：需要读取的依赖文件（proposal.md）

这些指令将指导后续所有生成步骤。

### 第 0.6 步：分析实际代码库

根据 project_context 提供的工程路径，分析现有代码：

**客户端分析**（`../develop/client/project`）：
- 检查是否已有相关模块（搜索模块名）
- 如果存在：记录现有文件路径、类名、Record 表定义
- 如果不存在：记录为新建模块

**服务端分析**（`../develop/server/project`）：
- 检查是否已有相关模块（搜索模块名）
- 如果存在：记录现有文件路径、模块名、配置表路径
- 如果不存在：记录为新建模块

**配置表分析**（`../design/table/default_ios`）：
- 检查是否已有相关配置表
- 如果存在：记录现有字段定义
- 如果不存在：记录为新建配置表

分析结果将用于 design.md 的 Context 章节（当前状态）和 Decisions 章节（是新增还是修改）。

### 第 0.7 步：Pre-flight Check（代码库架构性调查）

> **目的**：在生成 design 文档前，自动执行代码库深度调查，避免基于错误假设设计。这一步的发现可能**改变整个 design 的性质**（从"设计新系统"变成"审查现有实现"）。

执行以下三项检查（直接搜索代码，不向用户提问）：

#### 检查 1：功能是否已有历史实现（服务端/客户端）

**搜索范围**：
- 服务端：`FsGame/*/`、`define/`、协议定义文件
- 客户端：`Assets/Script/LogicModule/`、`Assets/Script/UIScript/`、`BusinessActivityDefine.cs`

**搜索关键词**：
- proposal 中的功能名称（如"成长基金"、"MixGrowthFund"）
- 核心实体名（如"GrowthFund"、"ActivityGoal"）
- specs 中提及的专有名词

**判断标准与处理**：

| 发现情况 | 判断标准 | design 职责变化 | 必须在 design.md 新增的章节 |
|---------|---------|----------------|--------------------------|
| **已激活的完整实现** | 找到完整模块代码 + 已在入口注册（如 `GameLauncher.cs` / `FsGame.cpp` 的模块列表）| **从"设计新系统"变成"审查现有实现能否满足 proposal，列缺口"** | `## ⚠️ 当前状态：接入现有实现` 章节，说明代码位置、激活状态、本次职责（审查/补缺口） |
| **未启用的历史实现** | 找到模块代码但被注释/未注册 | 需判断是"恢复"还是"推翻重写" | 同上，额外说明"历史实现未启用，本次决策是..."  |
| **仅有预留定义** | 只找到常量/枚举（如 `BusinessActivityType.MixGrowthFund = 1018` 被注释），无模块代码 | 按常规 design 流程，但需复用已预留的常量 | `## Context` 中说明"已预留但未实现" |
| **完全全新** | 完全找不到相关代码 | 按常规 design 流程自由设计 | 无需特殊章节 |

**输出示例**（若发现已激活实现）：
```markdown
## ⚠️ 当前状态：这不是全新功能，是接入一套已存在但未启用的历史遗留架构

第一版本设计文档假设成长基金是全新模块，深入代码库调查后发现这个假设是错的。真实情况：

- **服务端**：`MixGrowthFundModule` 已完整实现且处于注册激活状态（`FsGame/ActivityModule/BusinessActivity/GrowthFund/`）
- **客户端**：`BusinessActivityType.MixGrowthFund = 1018` 枚举已预留，但模块类、Page 脚本完全不存在
- **配置表**：字段由 `LoadMainCfg` 代码固定（`ActiveId/RechargeId/Direct/...`），不是可以自由设计的空间

**这意味着本次 design 的性质是**：审查现有服务端代码能否满足 proposal 需求，客户端如何正确接入现有架构，而非设计一个新系统。
```

#### 检查 2：（活动类功能）是否需要接入 BusinessActivityModule（客户端专属）

**触发条件**：proposal 或 specs 中出现以下关键词之一：
- "活动"、"限时"、"运营"、"周期"、"赛季"
- "business_activity"、"BA_TYPE"
- specs 提及"活动开启时"、"活动结束后"

**若触发，执行以下检查**：

1. **搜索 `BusinessActivityType` 枚举**（`BusinessActivityDefine.cs`）：
   - 若找到已预留但被注释的枚举值（如 `//MixGrowthFund = 1018`）→ 需取消注释
   - 若找到已启用的枚举值 → 直接复用
   - 若完全没有 → 需申请新数值

2. **搜索对应 Record 表常量**（同文件）：
   - 若找到 `BA_{TABLENAME}_REC` 常量和 `Col` 枚举 → 复用（即使定义与当前需求不完全匹配，也先对齐再评估）
   - 若没有 → 需新增

3. **检查服务端对应常量**（`BusinessActivityDefine.h`）：
   - 确认 `BA_TYPE_{XXX}` 数值与客户端 `BusinessActivityType` 一致

**输出到 design/client.md**：
- 在"模块定义"章节前，新增 `## ⚠️ 重大前提：必须接入现有 BusinessActivityModule 通用活动框架`
- 明确说明：不是独立模块、不新建 Panel/红点枚举、必须继承 `BaseActivityPage` 并通过 `RegisterSeverActivityParamArgs`/`RegisterRedPointCallback` 接入
- 新增"活动类型分配"章节，说明 `BusinessActivityType` 在框架里的三个作用点（解析路由/红点判断/UI模板路由）

#### 检查 3：（配置表相关）配置表字段是否已由代码固定（服务端专属）

**搜索范围**：服务端代码库

**搜索关键词**：
- `READ_FILE` + proposal 中的表名关键词
- `Load{TableName}Cfg` / `LoadMainCfg` / `LoadRewardCfg`

**判断标准与处理**：

| 发现情况 | 判断标准 | design/config.md 职责变化 | 必须新增的章节 |
|---------|---------|-------------------------|--------------|
| **字段已由代码固定** | 找到 `READ_FILE(xxx, "ActiveId", ...)` 等加载代码 | **从"设计字段"变成"按代码反推真实字段，对照 proposal 列差异"** | `## ⚠️ 设计阶段配置表变更`，逐字段对照 proposal 期望 vs 代码实际支持，标注差异状态（⚠️ 缺失/⚠️ 不一致/已对齐）|
| **可自由设计字段** | 只找到 Excel 表或配置文件，无加载代码 | 按 proposal 需求自由设计字段 | 无需特殊章节 |

**特殊情况处理**：
- 配置表实体文件（`.txt`/`.xlsx`）不存在，但加载代码存在 → 仍然是"字段已固定"（说明这套代码从未在生产环境配置过，但字段结构已锁定）
- 历史 proposal/设计文档里的字段列表 ≠ 当前代码实际支持的字段 → 以代码为准，历史文档作废

**输出示例**（若发现字段已固定）：
```markdown
## ⚠️ 设计阶段配置表变更（相对 proposal 的差异，非相对空白的新增）

> proposal 阶段策划按照"从零设计"的思路写了字段列表（基金ID/名称/价格/类型/互斥组），但代码库调查显示实际可用的配置表结构与 proposal 描述有实质性差异。以下逐项对照：

### 字段差异对照表（proposal 期望 vs 代码实际支持）

| proposal 字段 | 代码实际情况 | 差异说明 | 状态 |
|---|---|---|---|
| 基金ID | 无独立"基金ID"，`ActiveId` 直接就是活动ID | proposal 设想二级关系，实际是一一对应 | ⚠️ 待评审确认是否接受该简化 |
| 价格 | **配置表无此字段** | 价格由 `RechargeId` 关联充值配置表得到 | ⚠️ proposal 需要的展示依赖跨表查询 |
| 互斥组 | **配置表和代码均无此字段/逻辑** | 现有代码只防止"同一活动重复购买" | ⚠️ 待评审：是否需要新增字段+校验逻辑 |
| 名称 | 对应字段是 `Name` | 命名一致 | 已对齐 |
```

#### Pre-flight Check 完成后的决策

根据以上三项检查的发现，**在生成任何 design 文档前**，先确定本次 design 的实际性质：

- **若发现"已激活的完整实现"**：在 design.md 开头明确告知"这不是设计新系统，是审查现有实现"，三端 design 文档的写法全部改为"现有实现审查+缺口清单"模式
- **若发现"需要接入 BusinessActivityModule"**：在 design/client.md 开头明确告知"必须接入现有框架"，不设计独立 Panel/红点体系
- **若发现"配置表字段已固定"**：在 design/config.md 开头明确告知"字段由代码固定"，逐字段对照 proposal 列差异，不自由设计字段

**若以上任一发现与 proposal 隐含假设严重冲突**（如 proposal 按"全新功能"描述，但代码已存在），在 design.md 的 Context 章节用专门的 `## ⚠️ 当前状态` 章节说明差异，避免评审时产生认知错位。

### 第 1 步：生成 design.md（OpenSpec 入口）

按照 `openspec instructions design` 提供的 template 生成：

**Context 章节**：
- 背景：从 proposal.md 的 Why 继承
- 当前状态：第 0.6 步分析的代码库现状
- 约束：project_context 中的职责边界

**Goals / Non-Goals 章节**：
- Goals：从 proposal.md 的 What Changes 提取
- Non-Goals：明确排除的范围（引擎层、其他模块）

**Decisions 章节**：
- 客户端设计决策（高层概述 + 引用 design/client.md）
- 服务端设计决策（高层概述 + 引用 design/server.md）
- 配置表设计决策（高层概述 + 引用 design/config.md）

**Risks / Trade-offs 章节**：
- 从三个详细文档中提取关键风险
- 说明缓解策略

输出：`changes/<id>/design.md`

### 第 2 步：生成 design/client.md（客户端详细设计）

读取 `references/design-client-rules.md`，按规则生成：

1. **背景与目标**：从 proposal.md 的 Why 部分继承
2. **模块定义**：
   - 从 proposal Impact 提取客户端受影响区域
   - 结合第 0.6 步代码分析，判断是新增还是修改现有模块
   - 推断模块名称、文件组织、依赖模块
   - 分配功能ID、UI ID、红点ID
3. **Record 表定义**：
   - 从 specs 中识别需要客户端存储的数据
   - 结合代码分析，复用现有表或新建表
   - 定义表名、列枚举、数据类型（必须与服务器对齐）
   - **只写定义和决策，不写伪代码**
4. **UI 设计**：
   - 从 specs 的 WHEN/THEN 识别页面、状态、交互流程
   - 定义页面结构、状态机、红点规则
   - **只写设计决策，不写具体实现代码**
5. **协议定义**：
   - 从 specs 识别客户端触发的协议
   - 定义 C2S 请求、S2C 响应、错误码
   - 协议号写 `{待自动分配}`
   - **只写协议契约，不写发送/接收的具体代码**
6. **设计决策说明**：
   - 每个关键设计增加"为什么"说明
   - 说明备选方案和不选的原因
7. **Open Questions**：
   - 检查协议字段、UI交互、边界条件等未确定项

输出：`changes/<id>/design/client.md`

### 第 3 步：生成 design/server.md（服务端详细设计）

读取 `references/design-server-rules.md`，按规则生成：

1. **背景与目标**：从 proposal.md 的 Why 部分继承
2. **模块定义**：
   - 从 proposal Impact 提取服务端受影响区域
   - 结合第 0.6 步代码分析，判断是新增还是修改现有模块
   - 推断模块名称、文件组织、依赖模块
3. **Record 表定义**：
   - 与 design/client.md 完全对齐（表名、列顺序、数据类型）
   - **只写定义和决策，不写访问代码**
4. **配置表定义**：
   - 从 proposal Impact 和 specs 识别需要配置的数据
   - 定义完整字段（字段名、类型、说明、示例值）
   - 说明加载方式（READ_FILE 宏），**不写完整代码**
5. **协议定义**：
   - 与 design/client.md 完全对齐（协议号、参数顺序、数据类型）
   - 说明协议处理回调、注册方式，**不写完整代码**
6. **业务逻辑流程**：
   - 从 specs 的 WHEN/THEN 生成购买、领取、触发、过期流程图
   - **只写流程和关键步骤，不写函数实现**
7. **设计决策说明**：
   - 每个关键设计增加"为什么"说明
   - 说明备选方案和不选的原因
8. **Open Questions**：
   - 与 design/client.md 对齐，检查协议、配置表、性能等未确定项

输出：`changes/<id>/design/server.md`

### 第 4 步：生成 design/config.md（配置表详细设计）

读取 `references/design-config-rules.md`，按规则生成：

1. **背景与目标**：从 proposal.md 的 Why 部分继承
2. **⚠️ 设计阶段配置表变更**（重点）：
   - 新增配置表：列出 proposal 未提及但设计阶段必须新增的表
   - 现有配置表补充字段：列出需要补充的字段及原因
   - 关联变更说明：proposal 原描述 vs design 实际需要
3. **配置表生成和使用机制**：
   - 策划侧流程：Excel → txt
   - 服务器侧流程：READ_FILE 宏概述，**不写完整代码**
   - 客户端侧流程：output_code_csharp.bat → TableConfig.cs 注册概述，**不写完整代码**
4. **配置表定义**：
   - 列出 design/client.md 和 design/server.md 中引用的所有配置表
   - 完整字段表格（字段名、类型、说明、示例值、必填、客户端/服务器使用、**状态**）
   - 字段状态标注：proposal已提 / ⚠️ 设计阶段补充 / 设计优化
5. **访问方式**：
   - 客户端：说明 TDXXXTable.GetData() 用法，**不写完整代码**
   - 服务器：说明 GetXXXConfig() 用法，**不写完整代码**
6. **配置表对齐检查**：
   - 字段顺序、数据类型、使用情况对齐检查表
7. **配置表新增/修改流程**：
   - 策划侧、客户端侧、服务器侧的操作步骤说明
8. **Open Questions**：
   - 配置表新增决策、字段格式、默认值、关联配置等未确定项

输出：`changes/<id>/design/config.md`

### 第 5 步：对齐检查

执行跨文档对齐检查：

1. **Record 表对齐**：
   - 检查 design/client.md 和 design/server.md 的 Record 表定义
   - 表名、列顺序、数据类型必须一致
   - 不一致则报错并停止

2. **协议对齐**：
   - 检查 design/client.md 和 design/server.md 的协议定义
   - 协议号占位符、参数顺序、数据类型、错误码必须一致
   - 不一致则报错并停止

3. **配置表对齐**：
   - 检查 design/client.md、design/server.md、design/config.md 中引用的配置表
   - 配置表名称、字段定义必须一致
   - 不一致则报错并停止

### 第 6 步：运行 openspec validate

运行 `openspec validate <id>`，确保：
- proposal.md 和 specs/*.md 仍然通过校验
- design.md 格式符合 OpenSpec 标准
- design/ 目录下的三个详细文档存在

如果 validate 失败，修复错误后重新运行。

### 第 7 步：输出交接摘要

输出交接摘要：

```text
变更名: <id>
design 文档已生成:
  - design.md（OpenSpec 入口，架构决策）
  - design/client.md（客户端详细设计）
  - design/server.md（服务端详细设计）
  - design/config.md（配置表详细设计）

代码库分析:
  - 客户端：[新增模块 / 修改现有模块 XXX]
  - 服务端：[新增模块 / 修改现有模块 XXX]
  - 配置表：[新增 N 个表 / 补充 N 个字段]

设计阶段配置表变更（见 design/config.md）:
  - 新增配置表: N 个
  - 补充字段: N 个
  - 关联变更: N 条

对齐检查: ✅ 通过
  - Record 表对齐
  - 协议对齐
  - 配置表对齐

openspec validate: ✅ 通过

下一步: 进入联合评审（策划+客户端+服务端+测试）
  1. 架构师评审 design.md（架构决策）
  2. 前端工程师评审 design/client.md（客户端详细设计）
  3. 后端工程师评审 design/server.md（服务端详细设计）
  4. 策划评审 design/config.md（配置表详细设计，重点关注"设计阶段配置表变更"）
  5. 联合确认 Open Questions
  6. 评审通过后使用 lr-openspec-design-merge 合并评审结果
  7. 合并后进入 tasks 环节（本 skill 不做）
```

## 完成条件

- `changes/<id>/design.md` 存在且符合 OpenSpec 标准格式（Context / Goals / Decisions / Risks）
- `changes/<id>/design/` 下有 client.md、server.md、config.md 三件套
- 三端详细文档的 Record 表、协议、配置表定义完全对齐
- design.md 中引用了三个详细文档
- 设计阶段配置表变更在 design/config.md 中完整记录
- `openspec validate <id>` 通过
- 输出交接摘要，明确"design 完成，等待人工评审，评审后需合并再进入 tasks"

## 不做的事

- 不生成 tasks.md（那是人工评审通过后的事）
- 不修改 proposal.md 或 specs/*.md（输入是只读的）
- 不生成或修改 demo/（demo 是 lr-design 的产物）
- 不回写飞书或其他外部系统

## 与 lr-design 的关系

- `lr-design`：策划案 → proposal + specs + demo（策划侧闭环）
- `lr-openspec-design`：proposal + specs → design 三件套（技术评审准备）

两者串联：
1. 策划使用 lr-design 生成 proposal + specs + demo
2. 策划验收通过后，使用 lr-openspec-design 生成 design 三件套
3. 联合评审（策划+前端+后端）确认 design 和 Open Questions
4. 评审通过后，手工或用其他工具生成 tasks

## 路径约定

- **openspec 根**：包含 config.yaml 的目录（即 `D:\se\openspec`）
- **changes 目录**：`<openspec根>/changes/<id>/`
- **references 目录**：本 skill 目录下的 `references/`
- 所有路径引用使用相对路径，不使用绝对路径

## 策划权限约束

策划只有配置表权限，无前后端程序代码权限。所有涉及代码的决策必须联合前后端工程师。

design-config.md 中的"设计阶段配置表变更"是技术评审的重点讨论项，策划不能单独决定新增表或字段。
