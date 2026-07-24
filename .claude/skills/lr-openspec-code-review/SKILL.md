---
name: lr-openspec-code-review
description: 按框架约定清单检查代码质量（协议参数索引、框架API签名、错误处理模式、性能模式），输出审查报告
---

# lr-openspec-code-review

> **职责**: 按项目框架约定清单逐项检查代码，发现违反约定或潜在风险的地方。
> **阶段**: 阶段 11a
> **依赖**: apply 阶段完成（不依赖 reconcile）

---

## 使用场景

**适用于**：
- apply 完成后，提交代码前的最后检查
- 多人协作，确保所有角色遵守框架约定
- 发现性能隐患、安全漏洞、框架API误用

**不检查**：
- 泛泛的"代码风格"（命名是否美观、注释是否充分）
- 业务逻辑正确性（由 test-validate 负责）

---

## 使用方式

```bash
/lr-openspec-code-review growth-fund
```

---

## 执行流程

### 步骤 1：加载检查清单

按项目框架约定（`schemas/lr-func-dev/rules/design/*-structure.md`）逐项检查，检查清单如下：

#### 服务端检查清单（server 组，共 4 项）

| ID | 检查项 | 规则来源 | 严重程度 |
|----|-------|---------|---------|
| server-001 | 协议参数起始索引检查 | server-structure.md § 1.1 | 高 |
| server-002 | 错误处理模式一致性检查 | server-structure.md § 1.2 | 中 |
| server-003 | 配置字段名检查 | server-structure.md § 2.1 | 高 |
| server-004 | Record 查询 null 保护检查 | （隐含规则） | 高 |

#### 客户端检查清单（client 组，共 4 项）

| ID | 检查项 | 规则来源 | 严重程度 |
|----|-------|---------|---------|
| client-001 | OnCellUpdated 参数类型检查 | client-structure.md § 2.1 | 高 |
| client-002 | DettachPage 拼写检查（双 t） | client-structure.md § 2.1 | 高 |
| client-003 | 红点计算触发时机检查 | client-structure.md 红点规则 | 中 |
| client-004 | BusinessActivityModule 接入检查 | client-structure.md § 1.1 | 高 |

#### 配置表检查清单（config 组，共 2 项）

| ID | 检查项 | 规则来源 | 严重程度 |
|----|-------|---------|---------|
| config-001 | outcode_config.json 配置完整性检查 | config-structure.md 代码生成配置 | 高 |
| config-002 | 字段属性标注完整性检查 | config-structure.md 字段定义 | 中 |

---

**检查清单维护**：

- 检查清单硬编码在本 SKILL 正文（步骤 1、3、4、5）
- 当 `schemas/lr-func-dev/rules/design/*-structure.md` 的框架约定更新时，同步更新本文件对应检查项

---

### 步骤 2：读取实施文件清单

```bash
Read(changes/{change-id}/implementation-report.md)
```

**提取已实现文件列表**：
- 服务端: `SourceModule/ActivityModule/MixGrowthFundModule.h`, `.cpp`
- 客户端: `Assets/Script/LogicModule/.../MixGrowthFundModule*.cs`
- 客户端 UI: `Assets/Script/UIScript/.../GrowthFundPage.cs`

---

### 步骤 3：执行服务端检查

#### 3.1 协议参数起始索引检查

**目标**: 确认所有协议处理函数从 `args.IntVal(1)` 开始，不用 `args.IntVal(0)`

**检查方法**:
```bash
codegraph_explore("OnCustom protocol handler args.IntVal MixGrowthFundModule", 
                  projectPath: "D:/se/develop/server/project")
```

查询结果中搜索 `args.IntVal(0)` 或 `args.StringVal(0)`。

**违反示例**:
```cpp
int OnCustomGetReward(..., const IVarList& args) {
    int activityID = args.IntVal(0);  // ❌ 应该从 1 开始
}
```

**符合示例**:
```cpp
int OnCustomGetReward(..., const IVarList& args) {
    int activityID = args.IntVal(1);  // ✅ 正确
    int tierIndex = args.IntVal(2);
}
```

---

#### 3.2 错误处理模式检查

**目标**: 确认大部分协议处理函数使用"模式 1：静默返回"（与现有代码保持一致）

**检查方法**:
```bash
Grep("return ERR_", path: "D:/se/develop/server/project/SourceModule/ActivityModule/MixGrowthFundModule.cpp")
```

统计：
- `return 0;` 出现次数
- `return ERR_*` 出现次数

**判定**:
- 比例 > 80% 使用 `return 0;` → ✅ 符合模式 1
- 比例混杂 → ⚠️ 建议统一为模式 1

---

#### 3.3 配置字段名检查

**目标**: 确认 `txt.ReadInt(i, "FieldName")` 的字段名与 Excel 列名完全一致（大小写敏感）

**检查方法**:
```bash
codegraph_explore("LoadResource READ_FILE txt.ReadInt MixGrowthFundModule", 
                  projectPath: "D:/se/develop/server/project")
```

对比 design.md 附录 C 的字段名。

**潜在问题**:
- Excel 列名: `recharge_id`
- 代码写成: `txt.ReadInt(i, "RechargeId")` ← 大小写不一致，会解析失败

---

#### 3.4 Record 查询 null 保护检查

**目标**: 所有 `FindRecord` 调用后必须检查返回值

**检查方法**:
```bash
codegraph_explore("FindRecord MixGrowthFundModule null check", 
                  projectPath: "D:/se/develop/server/project")
```

**违反示例**:
```cpp
IRecord* rec = m_Kernel.FindRecord(player, GROWTH_FUND_OPEN_REC);
int activityID = rec->QueryInt(0, GROWTH_FUND_OPEN_REC_ACTIVITYID);  // ❌ 没检查 null
```

**符合示例**:
```cpp
IRecord* rec = m_Kernel.FindRecord(player, GROWTH_FUND_OPEN_REC);
if (rec == NULL) return 0;  // ✅ 有保护
int activityID = rec->QueryInt(0, GROWTH_FUND_OPEN_REC_ACTIVITYID);
```

---

### 步骤 4：执行客户端检查

#### 4.1 UI 方法签名检查

**目标**: 确认框架回调方法签名正确

**检查方法**:
```bash
codegraph_explore("OnCellUpdated signature GrowthFundRewardCell", 
                  projectPath: "D:/se/develop/client/project")
```

**检查点**:
- `OnCellUpdated(Transform root, int index)` ← 第一个参数必须是 `Transform`
- `DettachPage(AbstractPage page)` ← 必须是双 t 拼写

**违反示例**:
```csharp
void OnCellUpdated(GameObject root, int index) { }  // ❌ 参数类型错误
void DetachPage(AbstractPage page) { }             // ❌ 单 t 拼写错误
```

---

#### 4.2 红点计算触发时机检查

**目标**: 确认红点计算只在 Record 变化时触发，不在刷新循环中

**检查方法**:
```bash
codegraph_explore("DirtyRedPoint MixGrowthFundModule RefreshUI Update", 
                  projectPath: "D:/se/develop/client/project")
```

**违反示例**:
```csharp
void OnRecvActivityInfo() {
    RefreshUI();
    m_BAModule.DirtyRedPoint(activityId, type);  // ⚠️ 每次刷新都触发（性能隐患）
}
```

**符合示例**:
```csharp
void OnGrowthFundOpenRecChanged() {  // Record Hook 回调
    m_BAModule.DirtyRedPoint(activityId, type);  // ✅ 只在数据变化时触发
}
```

---

#### 4.3 BusinessActivityModule 接入检查

**目标**: 确认活动模块正确接入 BA 框架

**检查方法**:
```bash
codegraph_explore("RegisterRedPointCallback BusinessActivityModule MixGrowthFundModule", 
                  projectPath: "D:/se/develop/client/project")
```

**必需调用**:
- `RegisterRedPointCallback(BusinessActivityType.MixGrowthFund, OnRedPointCallback)`
- `RegisterSeverActivityParamArgs(BusinessActivityType.MixGrowthFund, OnRecvInfo)`

---

### 步骤 5：执行配置表检查

#### 5.1 outcode_config.json 配置检查

**目标**: 确认新增配置表已配置代码生成

**检查方法**:
```bash
Read(D:/se/develop/client/tools/table/table_config/outcode_config.json)
```

**检查点**:
- design.md 附录 C 提到的配置表是否在 `need_copy` 数组中
- 如果是动态活动配置，是否在 `NeedParseDataMethod` 数组中

**违反示例**:
```json
{
  "need_copy": [
    "activity_koi"
    // ❌ 缺少 active_fund_main
  ]
}
```

---

### 步骤 6：输出 code-review-report.md

```bash
Write(changes/{change-id}/code-review-report.md)
```

**报告结构**:

```markdown
# Growth Fund Code Review Report

**检查时间**: 2026-07-24
**检查清单**: 18 项框架约定
**文件范围**: 见 implementation-report.md
**项目路径**:
- 服务端: D:/se/develop/server/project
- 客户端: D:/se/develop/client/project

---

## 📊 总览

- ✅ 通过：15 项
- ⚠️ 建议优化：3 项
- ❌ 违反约定：0 项

---

## 详细发现

### ⚠️ 建议 1：红点计算可能在刷新循环中触发

**位置**: `Assets/Script/UIScript/.../GrowthFundPage.cs:142`

**代码**:
```csharp
void OnRecvActivityInfo() {
    RefreshUI();
    m_BAModule.DirtyRedPoint(activityId, type); // ← 每次刷新都触发
}
```

**规则来源**: client-structure.md "红点规则"章节

**问题**: 红点计算应该只在 Record 表变化时触发（RegisterRecHook 回调），不应该在 UI 刷新时触发。

**建议**: 改为在 `OnGrowthFundOpenRecChanged` Hook 回调中触发红点刷新。

**严重程度**: ⚠️ 中（性能隐患，频繁刷新时影响帧率）

---

### ⚠️ 建议 2：错误处理模式不统一

**统计结果**:
- `return 0;` 静默返回: 2 处
- `return ERR_COMMON_FAIL;` 返回错误码: 1 处

**规则来源**: server-structure.md 1.2 错误处理模式选择

**问题**: 项目推荐使用"模式 1：静默返回"，但发现混用两种模式。

**建议**: 统一改为模式 1（在校验函数内部调用 `CustomCommonErrorSysInfo()` 提示错误）。

**严重程度**: ⚠️ 中（不影响功能，但代码风格不一致）

---

### ⚠️ 建议 3：配置表字段名大小写疑似不一致

**位置**: `SourceModule/ActivityModule/MixGrowthFundModule.cpp:87`

**代码**:
```cpp
int nRechargeID = txt.ReadInt(i, "RechargeId");
```

**规则来源**: server-structure.md 2.1 配置加载约定

**问题**: design.md 附录 C 显示 Excel 列名为 `recharge_id`（下划线），代码写成 `RechargeId`（驼峰）。

**建议**: 确认 Excel 实际列名，确保大小写完全一致（框架对字段名大小写敏感）。

**严重程度**: ⚠️ 中（如果 Excel 列名确实是驼峰，则不是问题）

---

## ✅ 通过的检查

### ✅ 协议参数起始索引

**检查结果**: 所有协议处理函数均从 `args.IntVal(1)` 开始，符合框架约定。

**检查文件**: 
- `OnCustomGetReward`: args.IntVal(1), args.IntVal(2), args.IntVal(3) ✓

---

### ✅ UI 方法签名

**检查结果**: `OnCellUpdated` 第一个参数类型正确（Transform），`DettachPage` 拼写正确（双 t）。

**检查文件**:
- `GrowthFundRewardCell.cs`: `void OnCellUpdated(Transform root, int index)` ✓

---

### ✅ Record 查询 null 保护

**检查结果**: 所有 `FindRecord` 调用后均有 null 检查。

**检查文件**:
- `MixGrowthFundModule.cs:156`: `if (rec == null) return;` ✓
- `MixGrowthFundModule.cs:203`: `if (rec == null) continue;` ✓

---

### ✅ BusinessActivityModule 接入

**检查结果**: 已正确注册红点回调和活动信息回调。

**检查文件**:
- `MixGrowthFundModule.cs:45`: `RegisterRedPointCallback(BA_TYPE_MIX_GROWFUND, ...)` ✓
- `MixGrowthFundModule.cs:46`: `RegisterSeverActivityParamArgs(BA_TYPE_MIX_GROWFUND, ...)` ✓

---

### ✅ outcode_config.json 配置

**检查结果**: 配置表已正确配置代码生成。

**检查内容**:
- `need_copy` 包含 `active_fund_main` ✓
- `NeedParseDataMethod` 包含 `active_fund_main`（动态活动配置） ✓

---

## 📋 后续步骤

1. **人工评审建议项**，决定是否修复
2. **修复后重新运行 code-review**（如需要）
3. **运行下一阶段**: `/lr-openspec-test-validate growth-fund` 检查测试覆盖
```

---

### 步骤 7：输出提示

```
✅ 已生成代码审查报告：changes/growth-fund/code-review-report.md

📊 检查结果：
- ✅ 通过：15 项
- ⚠️ 建议优化：3 项（性能隐患、代码风格）
- ❌ 违反约定：0 项

🔍 建议项不影响功能，可选择性修复。

📌 下一步：
- 运行 `/lr-openspec-test-validate growth-fund` 检查测试覆盖
```

---

## 技术要点

### 检查清单来源

**硬编码在本 SKILL 正文**，来源于 `schemas/lr-func-dev/rules/design/*-structure.md` 的框架约定（server/client/config 三组，共 10 项）。

**维护方式**：
- 规则文件（`*-structure.md`）更新时，人工同步修改本文件对应检查项（步骤 1 的清单表格 + 步骤 3/4/5 的具体检查逻辑）
- 检查项数量不多、变化不频繁，直接维护成本低于额外维护一份结构化数据文件

### CodeGraph 查询说明

**CodeGraph 的能力边界**：
- ✅ 能做：返回符号定义、调用关系、源码片段
- ❌ 不能做：理解业务语义（如"这段代码是否实现了防重复逻辑"）

**实际执行流程**：
1. 用 CodeGraph 查询符号源码
   ```bash
   codegraph_explore("OnCustomGetReward args.IntVal", 
                     projectPath: "D:/se/develop/server/project")
   ```
2. AI 阅读返回的源码，判断是否符合检查项要求
3. 输出判断结果和证据（代码位置 + 代码片段）

**不是自动化验证，是 AI 辅助的代码审查**。

### 严重程度分级

- **高**：违反框架约定，可能导致运行时崩溃或编译失败
- **中**：代码风格不一致，或潜在性能隐患
- **低**：仅提醒，不影响功能

### 报告可操作性

每个建议项必须包含：
- **位置**：文件路径 + 行号
- **代码片段**：有问题的代码
- **规则来源**：哪个规则文件的哪个章节
- **问题说明**：为什么这是问题
- **建议操作**：具体怎么改

---

## 常见问题

### Q1: 检查清单会随时间过时吗？

**A**: 检查清单硬编码在本 SKILL 正文，不会自动同步。当 `server-structure.md`/`client-structure.md`/`config-structure.md` 更新框架约定时，需要人工同步修改本文件对应章节。

---

### Q2: 如何添加新的检查项？

**A**: 先在对应的规则文件（如 `server-structure.md`）补充约定，再手动在本文件的步骤 1 检查清单表格 + 步骤 3/4/5 补充对应的检查逻辑（目标、检查方法、违反/符合示例）。

---

### Q3: CodeGraph 查询不到怎么办？

**A**: 退化到 Grep，但在报告中标注"使用 Grep 模糊匹配，建议确认 CodeGraph 索引是否更新"。

---

## 版本信息

**版本**: v1.0  
**创建日期**: 2026-07-24  
**设计哲学**: 检查清单直接硬编码在 SKILL 正文，与规则文件保持人工同步
