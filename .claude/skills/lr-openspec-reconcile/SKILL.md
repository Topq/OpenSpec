---
name: lr-openspec-reconcile
description: 检查设计文档与实际代码的一致性（协议参数、Record结构、配置字段定义、设计文件清单与实际目录），输出差异报告供人工判定
---

# lr-openspec-reconcile

> **职责**: 检查 design.md 与实际代码的一致性（协议参数、Record 结构、配置字段、文件结构），发现"设计 vs 实现"差异，输出报告但不自动判定谁对谁错。
> **阶段**: 阶段 10（可选）
> **依赖**: apply 阶段完成

---

## 使用场景

**推荐在以下情况运行**：
- 多人协作（前后端分开跑 `/lr-openspec-apply`）
- apply 完成后手动修改了代码
- apply 跨越多天，中途改过 design.md

**不需要运行的情况**：
- 单人全栈，一次性跑完 apply
- 对三端对齐没有疑虑

---

## 使用方式

```bash
/lr-openspec-reconcile growth-fund
```

---

## 执行流程

### 步骤 1：读取输入文件

```bash
Read(changes/{change-id}/design.md)
Read(changes/{change-id}/implementation-report.md)
```

**从 design.md 提取检查基线**：
- 附录 A（客户端设计）：Record 表定义、UI 组件结构、文件与职责清单
- 附录 B（服务端设计）：Record 表定义、协议处理函数、配置结构体
- 附录 C（配置设计）：配置表字段定义

**从 implementation-report.md 提取已实现文件清单**。

---

### 步骤 2：维度 1 - 协议参数一致性

**检查内容**：前后端协议定义与实际代码的四向对齐检查

#### 2.1 提取 design.md 的协议定义

从附录 A/B 或协议章节提取：
```
CLIENT_CUSTOMMSG_QUERY_MONTH_CARD_GIFT_TARGET (678)
参数：activityID(int), targetRoleId(int64)

SERVER_CUSTOMMSG_MONTH_CARD_GIFT_TARGET_STATUS (2146)
参数：activityID(int), targetRoleId(int64), cardCount(int), cardList(varlist: cardType, surplusDay)
```

#### 2.2 提取前后端 define 文件的协议注释

**读取四个 define 文件**：

```bash
# 服务端协议定义
Read("../develop/server/project/define/ClientCustomDefine.h")
Read("../develop/server/project/define/ServerCustomDefine.h")

# 客户端协议定义
Read("../develop/client/project/Assets/Script/Define/ClientCustomID.cs")
Read("../develop/client/project/Assets/Script/Define/ServerCustomID.cs")
```

**提取协议注释**（使用 Grep 定位协议号，然后读取前面的注释行）：

```bash
# 示例：提取协议 678 的注释
Grep("CLIENT_CUSTOMMSG_QUERY_MONTH_CARD_GIFT_TARGET.*678", 
     path: "../develop/server/project/define/ClientCustomDefine.h",
     output_mode: "content", -B: 3)
```

提取出每个协议的**四份注释**：
- 服务端 C2S 注释（ClientCustomDefine.h）
- 服务端 S2C 注释（ServerCustomDefine.h）
- 客户端 C2S 注释（ClientCustomID.cs）
- 客户端 S2C 注释（ServerCustomID.cs）

#### 2.3 查询实际代码的发送/解析逻辑

**C2S 协议（如 678）**：

客户端发送代码：
```bash
codegraph_explore("SendQueryGiftTarget CLIENT_CUSTOMMSG_QUERY_MONTH_CARD_GIFT_TARGET VarList", 
                  projectPath: "../develop/client/project")
```
查询目标：`VarList < activityId < targetRoleId` 的实际参数顺序和类型

服务端解析代码：
```bash
codegraph_explore("OnCustomQueryGiftTarget args.IntVal CLIENT_CUSTOMMSG_QUERY_MONTH_CARD_GIFT_TARGET", 
                  projectPath: "../develop/server/project")
```
查询目标：`args.IntVal(1)`, `args.Int64Val(2)` 的实际参数顺序和类型

**S2C 协议（如 2146）**：

服务端发送代码：
```bash
codegraph_explore("SERVER_CUSTOMMSG_MONTH_CARD_GIFT_TARGET_STATUS Custom CVarList msg", 
                  projectPath: "../develop/server/project")
```
查询目标：`msg << activityId << targetRoleId << cardCount` 的实际参数顺序

客户端解析代码：
```bash
codegraph_explore("SERVER_CUSTOMMSG_MONTH_CARD_GIFT_TARGET_STATUS IntVal VarList", 
                  projectPath: "../develop/client/project")
```
查询目标：`args.IntVal(1)`, `args.Int64Val(2)` 的实际参数解析顺序

#### 2.4 四向对齐验证

对于每个协议，进行**多层次对比**：

**第一层：前后端 define 注释对比（静态文档一致性）**

| 协议 | 服务端 define 注释 | 客户端 define 注释 | 状态 |
|-----|------------------|------------------|------|
| 678 (C2S) | int activityId, int64 targetRoleId | int activityId, int targetRoleId（低32位）, int targetRoleId（高32位）| ❌ 客户端注释错误（说是拆分但实际不是）|
| 2146 (S2C) | int activityId, int cardCount | int activityId, int64 targetRoleId, int cardCount, varlist cardList | ❌ 服务端注释缺少 targetRoleId 和 cardList |

**第二层：define 注释 vs 实际代码（文档与实现一致性）**

| 协议 | define 注释 | 实际代码 | 状态 |
|-----|------------|---------|------|
| 678 客户端发送 | int activityId, int targetRoleId（低32位）, int targetRoleId（高32位）| `VarList < activityId < targetRoleId` (int64) | ❌ 注释与代码不符 |
| 678 服务端解析 | int activityId, int64 targetRoleId | `args.IntVal(1), args.Int64Val(2)` | ✅ 一致 |
| 2146 服务端发送 | int activityId, int cardCount | `msg << activityId << targetRoleId << cardCount << [cardType << surplusDay]...` | ❌ 注释缺少参数 |
| 2146 客户端解析 | int activityId, int64 targetRoleId, int cardCount, varlist cardList | （需查询实际解析代码）| 待验证 |

**第三层：前后端实际代码对接（运行时正确性）**

| 协议 | 客户端发送 | 服务端解析 | 状态 |
|-----|----------|----------|------|
| 678 (C2S) | `VarList < activityId(int) < targetRoleId(int64)` | `args.IntVal(1), args.Int64Val(2)` | ✅ 对接正确 |
| 2146 (S2C) | `msg << activityId << targetRoleId << cardCount << [cards]...` | （需查询客户端解析代码）| 待验证 |

**第四层：design.md vs 实际实现（设计与实现一致性）**

| 协议 | design.md 定义 | 实际实现 | 状态 |
|-----|--------------|---------|------|
| 678 | activityID(int), targetRoleId(int64) | 前后端代码均为 int + int64 | ✅ 一致 |
| 2146 | activityID, targetRoleId, cardCount, cardList | 服务端发送完整参数 | ✅ 一致（但服务端 define 注释未同步）|

#### 2.5 问题分类与报告

**严重问题（影响运行）**：
- 前后端实际代码参数不匹配（发送 3 个参数，解析 4 个参数）

**文档问题（不影响运行，但会误导维护）**：
- define 注释与实际代码不一致
- 前后端 define 注释互相冲突

**设计文档问题**：
- design.md 定义与实际实现不一致
- design.md 缺失协议定义但代码已实现

**输出示例**：

```markdown
## 协议 678: 查询月卡赠送目标状态

### 运行状态
✅ 前后端代码对接正确（客户端发送 int64，服务端解析 int64）

### 文档问题
❌ 客户端 define 注释错误
- 位置：`Assets/Script/Define/ClientCustomID.cs:1815-1820`
- 注释说明：`int targetRoleId（低32位）, int targetRoleId（高32位）`
- 实际代码：`VarList < targetRoleId` (int64)
- 建议：修改注释为 `int64 targetRoleId`

---

## 协议 2146: 月卡赠送目标状态回包

### 运行状态
⚠️ 需验证客户端解析代码是否处理完整参数

### 文档问题
❌ 服务端 define 注释过期
- 位置：`define/ServerCustomDefine.h:3657-3660`
- 注释说明：`int activityId, int cardCount`
- 实际代码：`msg << activityId << targetRoleId << cardCount << [cardType << surplusDay]...`
- 建议：补充注释 `int64 targetRoleId, varlist cardList (int cardType, int surplusDay)`
```

---

### 步骤 3：维度 2 - Record 表结构一致性

**检查内容**：design.md 的 Record 表定义 vs 实际服务端/客户端 Record 表宏定义

#### 3.1 提取 design.md 的 Record 表定义

从附录 A/B 提取：
```
GROWTH_FUND_OPEN_REC
列：ActivityID(int), GoodID(int), OpenTime(int)
```

#### 3.2 查询实际代码

**服务端**：
```bash
codegraph_explore("GROWTH_FUND_OPEN_REC Record.h 列枚举定义")
```
项目路径：`../develop/server/project`

**客户端**：
```bash
codegraph_explore("BA_GROWTH_FUND_OPEN_REC BusinessActivityDefine.cs 枚举常量")
```
项目路径：`../develop/client/project`

查询目标：
- 服务端：`#define GROWTH_FUND_OPEN_REC "growth_fund_open_rec"` + 列枚举
- 客户端：`BA_GROWTH_FUND_OPEN_REC` 常量 + `GROWTH_FUND_OPEN_REC_ACTIVITYID` 等枚举

#### 3.3 对比结果

**检查点**：
- 列名是否三端一致（大小写敏感）
- 列顺序是否一致
- 是否有 design.md 没写但代码里加了的列

**输出格式**：

#### GROWTH_FUND_OPEN_REC
| 列名 | design.md | 服务端 Record.h | 客户端 Define.cs | 状态 |
|-----|----------|----------------|----------------|------|
| ActivityID | ✅ 第1列 | ✅ 列枚举索引0 | ✅ 枚举常量存在 | 一致 |
| GoodID | ✅ 第2列 | ✅ 列枚举索引1 | ✅ 枚举常量存在 | 一致 |
| OpenTime | ✅ 第3列 | ✅ 列枚举索引2 | ❌ 未找到 | ⚠️ 客户端疑似遗漏 |

---

### 步骤 4：维度 3 - 配置表字段定义一致性

**检查内容**：design.md 的配置表字段定义 vs 实际服务端/客户端配置结构体

#### 4.1 提取 design.md 的配置表定义

从附录 C 提取：
```
active_fund_main.txt
字段：id(int), name(string), recharge_id(int), period_name(string)
```

#### 4.2 查询实际代码

**服务端配置结构体**：
```bash
codegraph_explore("struct STActiveFundMain 配置结构体字段")
```
项目路径：`../develop/server/project`

**客户端配置生成类**：
```bash
codegraph_explore("TDActiveFundMainTable class 字段属性")
```
项目路径：`../develop/client/project`

查询目标：
- 服务端：`struct STActiveFundMain { int nActiveId; fast_string strName; ... }`
- 客户端：`public class TDActiveFundMainTable { public int ID; public string Name; ... }`

#### 4.3 检查 outcode_config.json 配置

```bash
Read(../develop/client/tools/table/table_config/outcode_config.json)
```

检查：
- `need_copy` 数组是否按静态客户端需求配置
- 按 `schemas/lr-func-dev/rules/common/se-config-generation.md` 检查 SE 专有 `NeedParseDataMethod`：需要动态表类解析时已登记，`ParseData`/强类型字段/动态扩展实际生成；不将纯 S 作为唯一判断条件

#### 4.4 对比结果

**检查点**：
- 字段名是否三端一致（表头、服务端结构体、客户端生成类）
- 字段类型是否一致（int ↔ int, string ↔ fast_string/string）
- 客户端代码生成配置是否已配置

**输出格式**：

#### active_fund_main.txt
| 字段名 | design.md | 服务端结构体 | 客户端生成类 | 状态 |
|-------|----------|------------|------------|------|
| id | int | int nActiveId | int ID | ⚠️ 命名风格不一致（驼峰 vs 下划线） |
| name | string | fast_string strName | string Name | ✅ 类型兼容 |
| recharge_id | int | int nRechargeID | ❌ 未找到 | ⚠️ 客户端生成类疑似未生成 |

**代码生成配置检查**：
- outcode_config.json：✅ 已配置 `need_copy`
- 备注：客户端可能还未运行 `output_code_csharp.bat` 生成代码

---

### 步骤 5：维度 4 - 设计文件清单与目录结构一致性

**检查内容**：`design/client.md` 的「文件与职责清单」（`client-structure.md` §2.4.1）或 `design.md` 附录 A 的文件列表，与实际 `Assets/Script/` 下的文件是否一致。

**背景**：协议、Record、配置字段都有独立对账，但"设计列 10 个 UI 文件、实际 28 个"这类结构漂移过去没有检查项，会直接导致 apply 遗漏拆分、code-review 找不到目标文件。

#### 5.1 提取设计基线

从 `design/client.md` 的「文件与职责清单」或「UI 设计」章节提取：
- 计划新增的 `.cs` 文件路径
- 每个文件的职责（Module 主文件 / `_State` / `_Net` / Page / Panel / Cell）

若 design 没有该章节（旧变更），退化为：从「UI 设计」「模块定义」中提取文件路径，**并在报告中标注"设计缺少文件清单，本次对账不完整"**。

**只取本功能自己的文件**。不做这一步过滤，参考实现会被算成"设计有、实际无"，报出一堆假差异：
- 只取设计里标注「新增 / 修改」的文件；旧变更的 ASCII 目录树（```text 块）里按同样口径取；
- 明确写了「不新增 / 不创建 / 不单独新增」的文件名要**排除**——它出现在设计里是说明"为什么不做"；
- 作为「参考实现 / 参照」提到的其他模块文件（如 `XxxPage.cs`、`ContainerPage.cs`、`TableConfig.cs`）不算基线。

#### 5.2 扫描实际目录

按设计清单里出现的目录逐个扫；再补扫功能常驻的两处：

```bash
find ../develop/client/project/Assets/Script/LogicModule/{Func}Module -name "*.cs"
find ../develop/client/project/Assets/Script/UISript/{Func}Panel -name "*.cs"
```

目录名不确定时，从 `implementation-report.md` 的「生成文件清单」取模块根路径。

设计把入口/区域/容器文件放在功能目录之外时（如 `LogicModule/MainPanelModule/MainArea_{Func}.cs`、`UISript/MainPanel/Container/{Func}/`），**按设计里写的完整路径单独确认**，不能因为不在两个主目录里就判成"实际无"。

#### 5.3 对比与分类

| 差异类型 | 判定 |
|---|---|
| 设计有、实际无 | 实施遗漏，或设计过时 → 列差异 |
| 实际有、设计无 | 实现时按职责拆分 → 列差异，判断是否应回写设计 |
| 职责描述不一致 | 列差异（如设计写"状态/刷新"，实际承担网络回调） |
| partial 拆法与设计不同 | 列差异；按 `../develop/client/project/docs/ai-core/knowledge/modules/ui-management-system.md` 的拆分规则判断是否合理，不强制三件套 |

判定原则同前：**只列差异，不判定谁对谁错**。

**输出格式**：

```markdown
#### 客户端 UI 文件结构

| 文件 | design/client.md | 实际目录 | 职责一致 | 状态 |
|---|---|---|---|---|
| XxxPage.cs | 存在 | 存在 | 主文件 + 交互 | 一致 |
| XxxPage_State.cs | 存在 | 不存在 | - | ⚠️ 实际并入主文件 |
| XxxDetailCell.cs | 未列出 | 存在 | 天赋连线行 | ⚠️ 设计未列 |
```

**范围限制**：只对账本功能目录（`LogicModule/{Func}Module*`、`UISript/{Func}*`），不扫描整个 `Assets/Script`，也不把无关的历史文件算进差异。

---

### 步骤 6：输出 reconcile-report.md

```bash
Write(changes/{change-id}/reconcile-report.md)
```

**报告结构**：

```markdown
# Growth Fund Reconcile Report

**检查时间**: 2026-07-24
**检查维度**: 协议参数、Record 表结构、配置表字段定义
**项目路径**:
- 服务端: ../develop/server/project
- 客户端: ../develop/client/project

---

## 📊 总览

- ✅ 一致：23 项
- ⚠️ 疑似差异：5 项
- ❌ 确认错误：0 项

---

## 1. 协议参数一致性

[维度 1 的对比表格]

---

## 2. Record 表结构一致性

[维度 2 的对比表格]

---

## 3. 配置表字段定义一致性

[维度 3 的对比表格]

---

## 4. 文件结构一致性

[维度 4 的对比表格]

---

## 🔍 需要人工确认的差异

### 差异 1：客户端 GROWTH_FUND_OPEN_REC 缺少 OpenTime 列

**design.md 定义**：第 3 列 OpenTime(int)
**实际代码**：客户端 BusinessActivityDefine.cs 只定义了 ActivityID, GoodID

**可能原因**：
1. 实现时发现客户端不需要这个字段（合理优化）
2. 实现时遗漏（需补代码）

**建议操作**：
- [ ] 若确认客户端不需要，回写 design.md 附录 A 标注"客户端不存储 OpenTime"
- [ ] 若确认是遗漏，补充客户端 BusinessActivityDefine.cs 枚举常量

---

### 差异 2：配置表字段命名风格不一致

**design.md 定义**：recharge_id (下划线命名)
**服务端代码**：nRechargeID (驼峰命名)

**可能原因**：
1. 服务端约定用驼峰，design.md 用下划线只是表头名（不算差异）
2. 字段映射规则不一致（需统一）

**建议操作**：
- [ ] 确认项目规范：配置表字段名用下划线还是驼峰
- [ ] 统一 design.md 和代码的命名风格

---

## 📋 后续步骤

1. **人工评审本报告**，逐条差异判断是"设计有误"还是"实现遗漏"
2. **回写 design.md**（若确认设计有误）
3. **补充代码**（若确认实现遗漏）
4. **运行下一阶段**：`/lr-openspec-code-review` 和 `/lr-openspec-test-validate`
```

---

### 步骤 7：输出提示

```
✅ 已生成一致性检查报告：changes/growth-fund/reconcile-report.md

📊 检查结果：
- ✅ 一致：23 项
- ⚠️ 疑似差异：5 项（需人工确认）
- ❌ 确认错误：0 项

🔍 请人工评审报告，判断每条差异是"设计有误"还是"实现遗漏"。

📌 下一步：
- 运行 `/lr-openspec-code-review growth-fund` 检查框架约定
- 运行 `/lr-openspec-test-validate growth-fund` 检查测试覆盖
```

---

## 技术要点

### CodeGraph 查询策略

**CodeGraph 的能力边界**：
- ✅ 能做：返回符号定义、源码片段、调用关系
- ❌ 不能做：自动理解业务语义（如"协议参数是否从 1 开始"需要 AI 阅读源码判断）

**实际执行流程**：
1. 用 CodeGraph 查询符号源码
2. AI 阅读返回的源码，提取关键信息（参数顺序、字段名、类型）
3. 与 design.md 定义对比，输出差异清单

**优先使用 CodeGraph**（两个工程都有索引）：
```bash
# 协议处理函数
codegraph_explore("OnCustomGetReward args.IntVal protocol handler", 
                  projectPath: "../develop/server/project")

# Record 表定义
codegraph_explore("GROWTH_FUND_OPEN_REC Record.h enum COL", 
                  projectPath: "../develop/server/project")
codegraph_explore("BA_GROWTH_FUND_OPEN_REC BusinessActivityDefine.cs", 
                  projectPath: "../develop/client/project")

# 配置结构体
codegraph_explore("struct STActiveFundMain", 
                  projectPath: "../develop/server/project")
codegraph_explore("TDActiveFundMainTable class fields", 
                  projectPath: "../develop/client/project")
```

**备用方案**（CodeGraph 查询不到时）：
```bash
Grep("args.IntVal", path: "../develop/server/project/FsGame/ActivityModule/", glob: "*.cpp")
Grep("#define.*_REC", path: "../develop/server/project/FsGame/")
```

**这不是自动化验证，而是 AI 辅助的一致性检查**。

### 差异判定原则

**AI 只列差异，不判定对错**：
- ❌ 不要写"设计错误，应该回写 design.md"
- ❌ 不要写"实现遗漏，应该补充代码"
- ✅ 只写"可能原因 1...，可能原因 2..."
- ✅ 提供"建议操作"供人工勾选

### 报告可读性

**用表格而非长段落**：
- 每个维度用一张对比表
- 状态列用 emoji（✅ ⚠️ ❌）
- 疑似差异单独列出，附带"可能原因"和"建议操作"

---

## 常见问题

### Q1: CodeGraph 查询不到怎么办？

**A**: 退化到 Grep，但在报告中标注"使用 Grep 模糊匹配，可能不准确"。

---

### Q2: 客户端代码生成类不存在怎么办？

**A**: 在报告中标注"客户端可能还未运行 output_code_csharp.bat 生成代码，建议先生成再复查"。

---

### Q3: 差异太多怎么办？

**A**: 按严重程度分组：
- 确认错误（如协议号冲突）→ ❌ 
- 疑似差异（如字段名不一致）→ ⚠️
- 仅提醒（如命名风格）→ 💡

---

## 版本信息

**版本**: v1.1
**创建日期**: 2026-07-24  
**最后更新**: 2026-10-31（新增维度 4：设计文件清单与目录结构一致性）
**设计哲学**: AI 只列差异不判定，人工评审后决定回写方向
