# 协议解析规范补齐方案（完整解决方案）

## 执行机制排查结果

### 1. OpenSpec 指令是否引用规则文件？✅

**排查证据**：`schemas/lr-func-dev/schema.yaml`

```yaml
- id: design-client
  instruction: |
    **规则文件**：
    schemas/lr-func-dev/rules/design/client-structure.md
    
    请完整阅读该规则文件，按其定义的结构生成 design/client.md。
```

**结论**：✅ **OpenSpec 指令会强制读取规则文件**
- `openspec instructions design-client` 会明确要求 AI "完整阅读 client-structure.md"
- 规则文件的所有章节（§ 1.1, § 1.2, § 1.3）都会被读取
- 如果我们在 client-structure.md 新增 § 1.3，AI 在生成 design/client.md 时会自动引用

---

### 2. Code Review SKILL 是否执行检查项？✅

**排查证据**：`.claude/skills/lr-openspec-code-review/SKILL.md`

```markdown
### 步骤 1：加载检查清单

#### 客户端检查清单（client 组，共 4 项）
| ID | 检查项 | 规则来源 | 严重程度 |
| client-001 | OnCellUpdated 参数类型检查 | ... |
| client-002 | DettachPage 拼写检查 | ... |
| client-003 | 红点计算触发时机检查 | ... |
| client-004 | BusinessActivityModule 接入检查 | ... |

### 步骤 4：执行客户端检查

#### 4.1 UI 方法签名检查
（client-001 的具体检查逻辑）

#### 4.2 红点计算触发时机检查
（client-003 的具体检查逻辑）

#### 4.3 BusinessActivityModule 接入检查
（client-004 的具体检查逻辑）
```

**结论**：✅ **SKILL 会遍历执行所有检查项**
- 步骤 1 定义检查清单（client-001 到 client-004）
- 步骤 4 对每个检查项提供具体检查逻辑
- 如果我们新增 client-005/client-006，需要在两个地方同步：
  1. 步骤 1 的检查清单表格
  2. 步骤 4 新增对应的检查子章节

---

## 完整解决方案

### 修改 1：补齐设计规则（client-structure.md）

**文件**：`schemas/lr-func-dev/rules/design/client-structure.md`

**修改位置**：在 § 1.2 和 § 1.3（红点系统）之间插入新章节

**修改内容**：

```diff
### 1.2 Record 驱动 vs 传统协议模式选择
（保持不变）

---

+### 1.3 协议解析起始索引规范（阻断性）
+
+**适用范围**：所有需要解析服务端下发协议的功能
+
+**核心原则**：协议解析起始索引取决于协议处理层次
+
+---
+
+#### 1.3.1 原始协议解析（AddCustomHook 注册）
+
+**特征**：直接使用 `AddCustomHook(SERVER_CUSTOMMSG_XXX, OnRecvXXX)` 注册
+
+**解析规则**：
+
+```csharp
+// ✅ 正确：从索引 0 开始
+void OnRecvXXXInfo(IVarList args)
+{
+    int index = 0;
+    int param1 = args.GetInt32(index++);  // 第一个业务参数
+    int param2 = args.GetInt32(index++);  // 第二个业务参数
+}
+
+// ❌ 错误：从索引 1 开始会跳过第一个业务参数
+void OnRecvXXXInfo(IVarList args)
+{
+    int index = 1;  // ← 错误
+    int param1 = args.GetInt32(index++);  // 这会读到第二个业务参数
+}
+```
+
+**原因**：
+- 服务端构造时：`msg << 协议号 << param1 << param2`（协议号在索引 0）
+- 客户端框架接收时：已自动过滤索引 0（协议号）
+- 客户端收到的 IVarList：从索引 0 开始就是 param1
+
+**参考实现查询**：
+```
+CodeGraph: "AddCustomHook OnRecv IVarList GetInt32"
+参考文件：搜索任意 Module_Net.cs 中的 OnRecv 方法
+```
+
+**文档体现**（在 design-client.md 的"协议定义"章节）：
+
+```markdown
+### S2C_XXX_INFO (协议号 XXX)
+
+**解析方法**：`OnRecvXXXInfo(IVarList args)`（原始协议，从索引 0 开始）
+
+| 索引 | 字段 | 类型 | 说明 |
+|-----|------|------|------|
+| 0 | Param1 | int | 第一个参数 |
+| 1 | Param2 | int | 第二个参数 |
+
+**实现位置**：`XXXModule_Net.cs:123`
+```
+
+---
+
+#### 1.3.2 BusinessActivity 框架协议解析（ParamArgs 继承）
+
+**特征**：
+- 通过 `RegisterSeverActivityParamArgs(BA_TYPE_XXX, OnRecvInfo)` 注册
+- 实现 `override void ParamArgs(IVarList args)` 方法
+- 继承自 `BActivityParamArgs`
+
+**解析规则**：
+
+```csharp
+// ✅ 正确：从 CustomStart（索引 13）开始
+public override void ParamArgs(IVarList args)
+{
+    int index = (int)BAActivityInfoIndex.CustomStart;  // 索引 13
+    int param1 = args.GetInt32(index++);  // 第一个自定义参数
+    int param2 = args.GetInt32(index++);  // 第二个自定义参数
+}
+
+// ❌ 错误：从索引 0 开始会把 ActivityID 误读成业务参数
+public override void ParamArgs(IVarList args)
+{
+    int index = 0;  // ← 错误
+    int param1 = args.GetInt32(index++);  // 这会读到 ActivityID，不是自定义参数
+}
+```
+
+**原因**：
+- BusinessActivity 框架在协议前添加了 13 个固定字段：
+  - [0] ActivityID, [1] ActivityState, [2] BeginTime, [3] EndTime,
+  - [4] CurTurn, [5] CurDay, [6] ActivityType, [7] EachTurnDays,
+  - [8] UIType, [9] ShowTime, [10] TaskId, [11] SeasonId, [12] 预留
+  - [13+] 自定义业务参数 ← **从这里开始**
+- `BActivityCommonParamArgs.GetParamArgs()` 返回完整协议（包含固定字段）
+
+**参考实现**：`TrialModule_Config.cs:76`
+
+```csharp
+public override void ParamArgs(IVarList args)
+{
+    int index = (int)BAActivityInfoIndex.CustomStart;  // ✅ 标准写法
+    int pointCount = args.GetInt32(index++);
+    // ...
+}
+```
+
+**文档体现**（在 design-client.md 的"协议定义"章节）：
+
+```markdown
+### SERVER_CUSTOMMSG_BACTIVITY_INFO (协议号 470)
+
+**解析方法**：`ParamArgs(IVarList args)`（BusinessActivity 框架，从 CustomStart 索引 13 开始）
+
+**框架固定字段**（索引 0-12）：由 BusinessActivityModule 自动处理，无需手动解析
+
+**自定义参数**（从 CustomStart 开始）：
+
+| 索引偏移 | 字段 | 类型 | 说明 |
+|---------|------|------|------|
+| +0 (索引 13) | Param1 | int | 第一个自定义参数 |
+| +1 (索引 14) | Param2 | int | 第二个自定义参数 |
+
+**实现位置**：`XXXModule_Config.cs:85`
+**参考实现**：`TrialModule_Config.cs:76`
+```
+
+---
+
+#### 1.3.3 判断使用哪种解析方式
+
+**决策树**：
+
+```
+IF 协议处理函数是 void OnRecvXXX(IVarList args)
+   AND 通过 AddCustomHook 注册
+THEN 使用原始协议解析（从索引 0 开始）
+
+IF 协议处理函数是 override void ParamArgs(IVarList args)
+   AND 通过 RegisterSeverActivityParamArgs 注册
+THEN 使用 BusinessActivity 协议解析（从 CustomStart 开始）
+
+IF 协议处理函数是其他框架的 override 方法
+THEN 查看框架定义的起始索引（参考同框架的标准实现）
+```
+
+---

-### 1.3 红点系统注册方式
+### 1.4 红点系统注册方式
（内容不变，章节号从 1.3 变成 1.4）
```

---

### 修改 2：补齐代码审查检查项（lr-openspec-code-review SKILL）

**文件**：`.claude/skills/lr-openspec-code-review/SKILL.md`

**修改位置 1**：步骤 1 的检查清单

```diff
#### 客户端检查清单（client 组，共 4 项）
+#### 客户端检查清单（client 组，共 6 项）

| ID | 检查项 | 规则来源 | 严重程度 |
|----|-------|---------|---------|
| client-001 | OnCellUpdated 参数类型检查 | client-structure.md § 2.1 | 高 |
| client-002 | DettachPage 拼写检查（双 t） | client-structure.md § 2.1 | 高 |
| client-003 | 红点计算触发时机检查 | client-structure.md 红点规则 | 中 |
| client-004 | BusinessActivityModule 接入检查 | client-structure.md § 1.1 | 高 |
+| client-005 | 原始协议解析起始索引检查 | client-structure.md § 1.3.1 | 高 |
+| client-006 | BusinessActivity 协议解析起始索引检查 | client-structure.md § 1.3.2 | 高 |
```

**修改位置 2**：步骤 4 新增检查子章节

```diff
#### 4.3 BusinessActivityModule 接入检查
（保持不变）

+---
+
+#### 4.4 原始协议解析起始索引检查（client-005）
+
+**目标**：确认原始协议（AddCustomHook 注册）从索引 0 开始解析
+
+**检查方法**：
+1. 从 tasks.md 提取客户端模块名（如 `MixGrowthFundModule`）
+2. 使用 CodeGraph 搜索协议处理函数：
+```bash
+codegraph explore "OnRecv IVarList GetInt32 <模块名>Module" \
+  --project D:/se/develop/client/project
+```
+
+**检查规则**：
+- ✅ 正确模式：
+  - `int index = 0;` 然后 `args.GetInt32(index++)`
+  - 或直接 `args.GetInt32(0)` 作为第一个参数
+- ❌ 错误模式：
+  - `int index = 1;` 然后 `args.GetInt32(index++)` 作为第一个业务参数
+  - 或直接 `args.GetInt32(1)` 作为第一个业务参数
+
+**报告格式**（若发现错误）：
+```
+❌ client-005: 原始协议解析起始索引错误
+
+文件: XXXModule_Net.cs:123
+函数: OnRecvXXXInfo(IVarList args)
+问题: 从 index=1 开始解析，跳过了第一个业务参数
+
+当前代码:
+  45  void OnRecvXXXInfo(IVarList args)
+  46  {
+  47      int index = 1;  // ← 错误：应从 0 开始
+  48      int param1 = args.GetInt32(index++);
+  49  }
+
+应改为:
+  int index = 0;  // ← 正确：客户端框架已过滤协议号
+  int param1 = args.GetInt32(index++);
+
+原因: 客户端框架接收协议时已过滤索引 0（协议号），业务参数从索引 0 开始
+参考: 搜索其他 Module_Net.cs 中的 OnRecv 方法
+```
+
+---
+
+#### 4.5 BusinessActivity 协议解析起始索引检查（client-006）
+
+**目标**：确认 BusinessActivity 框架的 ParamArgs 方法从 CustomStart（索引 13）开始解析
+
+**检查方法**：
+1. 从 tasks.md 提取客户端模块名（如 `MixGrowthFundModule`）
+2. 使用 CodeGraph 搜索 ParamArgs 方法：
+```bash
+codegraph explore "ParamArgs IVarList BAActivityInfoIndex <模块名>Module" \
+  --project D:/se/develop/client/project
+```
+
+**检查规则**：
+- ✅ 正确模式：`int index = (int)BAActivityInfoIndex.CustomStart;`
+- ❌ 错误模式：`int index = 0;`（会把 ActivityID 误读成业务参数）
+
+**参考实现**：`TrialModule_Config.cs:76`
+
+**报告格式**（若发现错误）：
+```
+❌ client-006: BusinessActivity 协议解析起始索引错误
+
+文件: MixGrowthFundModule_Config.cs:85
+函数: ParamArgs(IVarList args)
+问题: 从 index=0 开始解析，跳过了 13 个 BusinessActivity 固定字段
+
+当前代码:
+  85  public override void ParamArgs(IVarList args)
+  86  {
+  87      int index = 0;  // ← 错误：应从 CustomStart (13) 开始
+  88      m_RechargeId = args.GetInt32(index++);
+  89  }
+
+应改为:
+  int index = (int)BAActivityInfoIndex.CustomStart;  // 索引 13
+  m_RechargeId = args.GetInt32(index++);
+
+原因: BusinessActivity 框架在协议前添加了 13 个固定字段（ActivityID 到 SeasonId）
+      从 index=0 开始会把 ActivityID 误读成 RechargeId
+      
+参考: TrialModule_Config.cs:76
+```

---
```

---

### 修改 3：补齐测试用例模板（client-implementation.md）

**文件**：`schemas/lr-func-dev/rules/tasks/client-implementation.md`

**修改位置**：在现有测试章节后追加

```diff
## 测试验证

### 功能性测试
（保持原有功能测试，如购买、领取、UI 显示）

+### 协议解析测试（通用）
+
+#### 原始协议解析测试
+
+**测试目的**：验证客户端原始协议解析与服务端下发数据一致
+
+**测试步骤**：
+1. 服务端构造测试数据：
+   ```cpp
+   CVarList msg;
+   msg << CLIENT_CUSTOMMSG_XXX_INFO;  // 协议号（索引 0，客户端框架会过滤）
+   msg << 1001;  // param1（客户端索引 0）
+   msg << 2002;  // param2（客户端索引 1）
+   msg << "test";  // param3（客户端索引 2）
+   ```
+
+2. 模拟服务端下发协议（单元测试 mock）
+
+3. 客户端解析后验证：
+   ```csharp
+   Assert.AreEqual(1001, receivedParam1);  // 不是协议号
+   Assert.AreEqual(2002, receivedParam2);
+   Assert.AreEqual("test", receivedParam3);
+   ```
+
+**预期结果**：所有字段值与服务端下发一致
+
+**失败诊断**：
+- 若 `receivedParam1` 等于协议号 → 解析起始索引错误（应从 0 开始，不是 1）
+- 若 `receivedParam1` 等于 2002 → 解析起始索引错误（多跳了一个索引）
+
+---
+
+#### BusinessActivity 协议解析测试
+
+**测试目的**：验证客户端 BusinessActivity 协议解析与服务端下发数据一致
+
+**测试步骤**：
+1. 服务端构造测试数据（模拟 BusinessActivityModule 框架）：
+   ```cpp
+   CVarList msg;
+   msg << SERVER_CUSTOMMSG_BACTIVITY_INFO;  // 协议号
+   msg << 10001;  // ActivityID（索引 0）
+   msg << 1;      // ActivityState（索引 1）
+   msg << 1234567890;  // BeginTime（索引 2）
+   msg << 1234567890;  // EndTime（索引 3）
+   msg << 1;      // CurTurn（索引 4）
+   msg << 1;      // CurDay（索引 5）
+   msg << 1018;   // ActivityType（索引 6）
+   msg << 7;      // EachTurnDays（索引 7）
+   msg << 1;      // UIType（索引 8）
+   msg << 1234567890;  // ShowTime（索引 9）
+   msg << 0;      // TaskId（索引 10）
+   msg << 0;      // SeasonId（索引 11）
+   // 索引 12 预留
+   msg << 1001;   // RechargeId（索引 13，CustomStart）← 第一个自定义参数
+   msg << 2001;   // RewardId（索引 14）← 第二个自定义参数
+   ```
+
+2. 模拟服务端下发协议
+
+3. 客户端解析后验证：
+   ```csharp
+   Assert.AreEqual(1001, m_RechargeId);  // 不是 ActivityID 的值 10001
+   Assert.AreEqual(2001, firstRewardId);  // 不是 ActivityState 的值 1
+   ```
+
+**预期结果**：所有自定义字段值与服务端下发一致
+
+**失败诊断**：
+- 若 `m_RechargeId` 等于 10001（ActivityID 的值）→ 解析起始索引错误（应从 CustomStart 13 开始，不是 0）
+- 若 `m_RechargeId` 等于 1（ActivityState 的值）→ 解析起始索引错误（从 1 开始，应从 13 开始）
```

---

## 验证方案是否有效

### 测试 1：设计阶段是否生效

**执行命令**：
```bash
cd D:/se/openspec
openspec instructions design-client --change test-protocol
```

**预期输出**：
- instruction 中包含 "请完整阅读 schemas/lr-func-dev/rules/design/client-structure.md"
- AI 在生成 design/client.md 时会引用 § 1.3.1 和 § 1.3.2
- 协议定义章节会自动生成解析规范和参考实现

---

### 测试 2：代码审查阶段是否生效

**执行命令**：
```bash
/lr-openspec-code-review growth-fund
```

**预期执行流程**：
1. 步骤 1：加载检查清单 → 看到 client-005 和 client-006
2. 步骤 4：执行客户端检查 → 执行 § 4.4 和 § 4.5
3. 使用 CodeGraph 搜索协议处理函数
4. 检测索引起始位置
5. 输出错误报告（如果发现问题）

---

## 总结

### 修改清单

| # | 文件 | 修改内容 | 作用 |
|---|------|---------|------|
| 1 | `schemas/lr-func-dev/rules/design/client-structure.md` | 新增 § 1.3 协议解析规范 | 设计阶段指导 |
| 2 | `.claude/skills/lr-openspec-code-review/SKILL.md` | 新增 client-005/006 检查项 | 审查阶段检查 |
| 3 | `schemas/lr-func-dev/rules/tasks/client-implementation.md` | 新增协议解析测试模板 | 测试阶段验证 |

### 执行保证

| 阶段 | 执行机制 | 保证方式 |
|-----|---------|---------|
| **设计阶段** | `openspec instructions design-client` | 明确要求 AI "完整阅读 client-structure.md" |
| **审查阶段** | `/lr-openspec-code-review` SKILL | 遍历执行 client-001 到 client-006 |
| **测试阶段** | `test-cases.md` 生成 | 从 client-implementation.md 读取测试模板 |

### 三层防护

| 层级 | 修改文件 | 效果 |
|-----|---------|------|
| **第一层** | client-structure.md § 1.3 | AI 生成 design/client.md 时自动引用规范 |
| **第二层** | code-review SKILL client-005/006 | CodeGraph 自动检测协议解析错误 |
| **第三层** | client-implementation.md 测试模板 | 运行时验证字段对齐 |

### 立即行动

三个文件修改，按优先级：
1. ✅ `client-structure.md` - 最优先（源头规范）
2. ✅ `lr-openspec-code-review/SKILL.md` - 第二优先（兜底检查）
3. 🔲 `client-implementation.md` - 第三优先（运行时验证）

**是否需要我立即执行这 3 个修改？**
