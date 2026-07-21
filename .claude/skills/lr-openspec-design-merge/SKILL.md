---
name: lr-openspec-design-merge
description: 评审完成后，读取 design/client.md、design/server.md、design/config.md 和评审意见，合并生成完整的 design.md，用于进入 tasks 环节。
---

# OpenSpec Design 合并器

## 角色与目标

面向评审后阶段。输入是评审后的三个详细设计文档（可能包含修改）和评审意见，输出是完整的 design.md（OpenSpec 标准格式），包含评审结果和关键设计决策。

本 skill 只做合并，不做新的设计工作。

## 核心原则

- design.md 是架构决策文档，包含"为什么这样设计"，不包含具体实现代码
- 从三个详细文档中提取关键设计决策，不是全部内容
- 评审意见中的风险和未决问题要合并到 design.md
- 合并后的 design.md 必须符合 OpenSpec 标准（Context / Goals / Decisions / Risks）

## 执行流程

### 第 0 步：输入验证

确认输入：
- `changes/<id>/design.md` 存在（lr-openspec-design 生成的初版）
- `changes/<id>/design/client.md` 存在
- `changes/<id>/design/server.md` 存在
- `changes/<id>/design/config.md` 存在
- 评审意见（可选）：可以是文本、markdown 文件或口头说明

### 第 1 步：读取现有文档

读取四个文档：
- `design.md` - 初版架构决策（lr-openspec-design 生成）
- `design/client.md` - 客户端详细设计（可能包含评审后的修改）
- `design/server.md` - 服务端详细设计（可能包含评审后的修改）
- `design/config.md` - 配置表详细设计（可能包含评审后的修改）

### 第 2 步：提取关键设计决策

从三个详细文档中提取：

**客户端关键决策**：
- 模块设计决策（为什么新增/修改模块）
- Record 表设计决策（为什么需要这些表，为什么这样设计列）
- 协议设计决策（为什么需要这些协议，为什么这样设计参数）
- UI 设计决策（为什么这样组织页面，为什么需要这些状态）
- 红点设计决策（为什么这样设计红点层级）

**服务端关键决策**：
- 模块设计决策（为什么新增/修改模块）
- Record 表设计决策（与客户端对齐的原因）
- 配置表设计决策（为什么需要这些配置表，为什么这样设计字段）
- 业务逻辑设计决策（为什么这样设计流程）
- 性能设计决策（为什么选择这种实现方式）

**配置表关键决策**：
- 新增配置表决策（为什么不能复用现有表）
- 字段设计决策（为什么需要这些字段，为什么选择这种类型）
- 对齐策略决策（如何保证客户端/服务端一致）
- 设计阶段配置表变更（评审确认的变更）

**提取规则**：
- 只提取"为什么"和"备选方案对比"，不提取具体实现
- 只提取关键决策，不提取所有细节
- 如果详细文档中有评审后的修改，优先使用修改后的内容

### 第 3 步：整合评审意见

如果有评审意见：

**评审中确认的设计变更**：
- 更新 Decisions 章节（反映评审后的最终决策）
- 说明变更原因

**评审中发现的风险**：
- 合并到 Risks / Trade-offs 章节
- 说明缓解策略或接受理由

**评审后解决的 Open Questions**：
- 从 Open Questions 中移除
- 将决策结果写入 Decisions 章节

**评审后剩余的 Open Questions**：
- 保留在 Open Questions 章节
- 标注优先级和责任人（如果有）

### 第 4 步：检查 Open Questions 是否全部回答

**硬性门槛检查**：

合并后的 design.md 中的 Open Questions 章节必须为空（或完全不存在该章节）。

**检查逻辑**：
1. 读取合并后的 design.md
2. 查找 `## Open Questions` 章节
3. 检查该章节下是否还有未回答的问题

**判定规则**：
- ✅ **允许通过**：
  - Open Questions 章节不存在
  - Open Questions 章节存在但为空（只有标题，没有内容）
  - Open Questions 章节明确标注"全部已解决"

- ❌ **阻断流程**：
  - Open Questions 章节下还有任何未回答的问题
  - 即使标注为"低优先级"或"可选"，也不能放行

**阻断时的行为**：
1. 停止执行，不生成"可以进入 tasks"的结论
2. 输出阻断原因：
   ```text
   ❌ design.md 合并阻断
   
   原因：仍有 N 条 Open Questions 未回答
   
   未回答的问题：
   1. [问题描述]
      - 影响：[影响范围]
      - 来源：design/[client|server|config].md
   
   2. [问题描述]
      - 影响：[影响范围]
      - 来源：design/[client|server|config].md
   
   下一步：
   1. 回到评审，针对上述问题做出决策
   2. 更新 design/[client|server|config].md，反映决策结果
   3. 重新运行 lr-openspec-design-merge
   
   注意：
   - design 环节的 Open Questions 通常涉及协议字段、配置表结构、存储结构等底层技术契约
   - 这些问题不回答，tasks 环节无法正确拆分任务，会导致返工
   - 请确保所有问题都在评审中得到明确答复
   ```

**设计原则**：
- 为什么硬性要求全部回答：与 lr-design 的"闸门 B：假设清单全部裁决完毕"保持一致，用硬性门槛避免主观判断
- 为什么不区分优先级：如果 Open Questions 生成规则严格执行（排除技术细节、已明确定义、宽泛问题），那剩下的都应该是"不回答就无法继续"的问题
- 为什么阻断而非警告：防止评审流于形式，带着未决问题进入 tasks 会增加返工成本

### 第 5 步：生成完整 design.md

按照 OpenSpec 标准格式更新 design.md：

```markdown
## Context

[保留初版的背景和当前状态]
[如果评审中发现新的约束，补充到这里]

## Goals / Non-Goals

[保留初版的目标]
[如果评审中调整了范围，更新这里]

**Goals:**
- [设计要达成的目标]

**Non-Goals:**
- [明确排除的范围]

## Decisions

### 客户端设计决策

**模块设计**：[从 client.md 提取的关键决策]
- 决策：[具体决策内容]
- 原因：[为什么这样决策]
- 备选方案：[考虑过的其他方案]
- 为什么不选：[不选备选方案的原因]
- [如果评审中有变更，说明变更和原因]

**Record 表设计**：[从 client.md 提取]
- [关键设计点和原因]

**协议设计**：[从 client.md 提取]
- [关键设计点和原因]

**UI 设计**：[从 client.md 提取]
- [关键设计点和原因]

详细设计见：design/client.md

### 服务端设计决策

**模块设计**：[从 server.md 提取的关键决策]

**Record 表设计**：[从 server.md 提取]
- 对齐说明：与客户端完全对齐（表名、列顺序、类型）

**配置表设计**：[从 server.md 提取]
- [关键设计点和原因]

**业务逻辑设计**：[从 server.md 提取]
- [关键流程设计和原因]

详细设计见：design/server.md

### 配置表设计决策

**新增配置表决策**：[从 config.md 提取]
- [为什么需要新增，为什么不能复用]

**字段设计决策**：[从 config.md 提取]
- [关键字段设计和原因]

**设计阶段配置表变更**：[从 config.md 的"设计阶段配置表变更"章节提取]
- 新增配置表：[列表]
- 补充字段：[列表]
- 评审结果：[已确认 / 已调整 / 待后续讨论]

**对齐策略**：[从 config.md 提取]
- [如何保证客户端/服务端一致]

详细设计见：design/config.md

## Risks / Trade-offs

[从初版 design.md 和评审意见中整合]

### 技术风险
- **风险**：[具体风险描述]
  - 缓解策略：[如何降低风险]
  - 评审意见：[如果评审中讨论过，记录结论]

### 性能风险
- **风险**：[具体风险描述]
  - 缓解策略：[如何降低风险]

### 兼容性风险
- **风险**：[具体风险描述]
  - 缓解策略：[如何降低风险]

### Trade-offs
- **选择A而非B**：[说明权衡]
  - 优点：[选择A的好处]
  - 缺点：[选择A的代价]
  - 评审结论：[如果评审中讨论过，记录结论]

## Open Questions

[从三个详细文档的 Open Questions 中整合，移除评审中已解决的]

### 高优先级
1. **[问题描述]**
   - 影响：[影响范围]
   - 决策人：[谁来决定]
   - 截止日期：[什么时候必须决定]

### 中优先级
2. **[问题描述]**
   - 影响：[影响范围]

### 低优先级（可选）
3. **[问题描述]**
   - 说明：可以在实现阶段决定
```

### 第 6 步：运行 openspec validate

运行 `openspec validate <id>`，确保：
- design.md 格式符合 OpenSpec 标准
- design.md 中引用的三个详细文档存在

如果 validate 失败，修复错误后重新运行。

### 第 7 步：输出交接摘要

输出交接摘要：

```text
变更名: <id>
design.md 合并完成:
  - 已整合客户端、服务端、配置表的关键设计决策
  - 已整合评审意见和风险
  - 已更新 Open Questions（移除已解决的 N 条，剩余 M 条）

评审结果摘要:
  - 设计变更: N 项
  - 新增风险: M 项
  - 已解决问题: K 项
  - Open Questions: ✅ 全部已回答（0 条剩余）

openspec validate: ✅ 通过

下一步: 进入 tasks 环节
  - design.md 作为技术设计文档
  - design/*.md 作为详细参考文档
  - tmp/*-implementation-details.md 作为实现参考
```

**注意**：只有第 4 步检查通过（Open Questions 全部回答）才会输出上述摘要。如果检查不通过，会输出阻断信息（见第 4 步）。

## 完成条件

- `changes/<id>/design.md` 已更新，包含评审结果
- design.md 包含从三个详细文档提取的关键决策
- design.md 包含评审意见和风险
- **design.md 的 Open Questions 章节为空（全部问题已回答）** - 硬性要求
- `openspec validate <id>` 通过
- 输出交接摘要，明确"design 合并完成，可以进入 tasks"

**如果 Open Questions 未全部回答**：
- 不满足完成条件
- 输出阻断信息
- 要求回到评审解决问题

## 不做的事

- 不做新的设计决策（只整合已有的）
- 不修改三个详细文档（只读取）
- 不生成 tasks.md（那是下一个环节）
- 不修改 proposal.md 或 specs/*.md

## 使用场景

```
评审流程：
1. lr-openspec-design 生成 design.md（初版）+ design/*.md（详细）
2. 前端/后端/策划分别评审 design/*.md，提出修改意见
3. 修改 design/*.md，反映评审结果
4. 使用 lr-openspec-design-merge 合并评审结果到 design.md
5. design.md 作为最终技术设计文档，进入 tasks 环节
```

## 路径约定

- **openspec 根**：包含 config.yaml 的目录
- **changes 目录**：`<openspec根>/changes/<id>/`
- **design 文档**：`<changes目录>/design.md`
- **详细设计**：`<changes目录>/design/*.md`
- **实现细节**：`<openspec根>/tmp/*-implementation-details.md`

## 合并策略

### 什么内容需要合并到 design.md

- ✅ 架构决策（为什么选择这个方案）
- ✅ 技术选型（为什么选择这个技术）
- ✅ 关键设计点（为什么这样设计）
- ✅ 备选方案对比（为什么不选其他方案）
- ✅ 设计阶段的配置表变更（评审确认的）
- ✅ 风险和缓解策略
- ✅ Open Questions（评审后剩余的）

### 什么内容不需要合并

- ❌ 具体实现代码（伪代码、示例代码）
- ❌ 详细的字段定义（完整的表格）
- ❌ 完整的协议字段列表（只合并关键设计点）
- ❌ UI 方法签名（这是实现细节）
- ❌ 配置表加载的完整代码（这是实现细节）
