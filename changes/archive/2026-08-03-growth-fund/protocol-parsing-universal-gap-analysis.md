# 协议解析疏漏分析：通用前后端协议规范

## 核心观点

这个问题的本质**不是 BusinessActivity 框架特有的问题**，而是**所有前后端协议交互都需要遵守的通用规范**：

### 服务端协议构造规范

```cpp
// ✅ 正确：参数从索引 1 开始（索引 0 是协议号）
int XXXModule::OnCustomXXX(const PERSISTID& player, const PERSISTID& sender, const IVarList& args)
{
    int param1 = args.IntVal(1);  // 第一个业务参数
    int param2 = args.IntVal(2);  // 第二个业务参数
    // ...
}

// ❌ 错误：从索引 0 开始会读到协议号
int param1 = args.IntVal(0);  // 这会读到协议号，不是业务参数
```

### 客户端协议解析规范

分为两种情况：

#### 情况 1：原始协议（IVarList）

```csharp
// ✅ 正确：从索引 0 开始（协议号已被框架处理）
void OnRecvProtocol(IVarList args)
{
    int index = 0;
    int param1 = args.GetInt32(index++);  // 第一个业务参数
    int param2 = args.GetInt32(index++);  // 第二个业务参数
}
```

#### 情况 2：BusinessActivity 框架（BActivityCommonParamArgs）

```csharp
// ✅ 正确：从 CustomStart 开始（前 13 个是框架固定字段）
public override void ParamArgs(IVarList args)
{
    int index = (int)BAActivityInfoIndex.CustomStart;  // 跳过 13 个固定字段
    int param1 = args.GetInt32(index++);  // 第一个自定义参数
    int param2 = args.GetInt32(index++);  // 第二个自定义参数
}

// ❌ 错误：从 0 开始会把 ActivityID 当成业务参数
int index = 0;
int param1 = args.GetInt32(index++);  // 这会读到 ActivityID，不是业务参数
```

---

## 当前 OpenSpec 流程的问题

### 1. 服务端规范：已明确 ✅

**位置**：`schemas/lr-func-dev/rules/design/server-structure.md § 1.1`

```markdown
### 1.1 协议处理函数标准结构

⚠️ 关键约定（框架限制）：
- 参数从 args.IntVal(1) 开始，索引 0 是协议号
- 不要写成 args.IntVal(0)，会导致参数错位
```

**检查项**：`lr-openspec-code-review/SKILL.md` 有 server-001 检查

**结论**：服务端规范完整 ✅

---

### 2. 客户端规范：严重缺失 ❌

**位置**：`schemas/lr-func-dev/rules/design/client-structure.md`

**问题**：
- ❌ 没有说明原始协议（IVarList）的解析规则
- ❌ 没有说明 BusinessActivity 框架的解析规则
- ❌ 没有说明两者的区别和判断标准

**检查项**：`lr-openspec-code-review/SKILL.md` **没有任何客户端协议解析检查**

**结论**：客户端规范完全缺失 ❌

---

## 通用协议规范应该如何定义

### 原则：按协议处理层次分类

| 协议类型 | 特征 | 解析起始索引 | 原因 |
|---------|------|------------|------|
| **原始协议** | 直接 AddCustomHook 注册 | **索引 0** | 框架已过滤协议号 |
| **BusinessActivity 协议** | 通过 BActivityParamArgs | **索引 13** (CustomStart) | 框架添加了 13 个固定字段 |
| **其他框架协议** | 通过 XXXParamArgs | **取决于框架** | 需查看框架定义 |

### 判断标准

```
IF 协议处理函数签名是 void OnRecvXXX(IVarList args)
THEN 从索引 0 开始解析

IF 协议处理函数签名是 override void ParamArgs(IVarList args)
THEN 需要查看父类框架定义，确定起始索引
    - BusinessActivity 框架 → 从 BAActivityInfoIndex.CustomStart (13) 开始
    - 其他框架 → 查看框架文档或参考实现
```

---

## 建议修正方案（通用版）

### 方案 A：在设计规则中明确（阻断性，推荐）

**修改文件**：`schemas/lr-func-dev/rules/design/client-structure.md`

**新增章节**（在 § 1.2 之后）：

```markdown
### 1.3 协议解析通用规范（阻断性）

**适用范围**：所有需要解析服务端下发协议的功能

---

#### 1.3.1 原始协议解析规范

**适用场景**：直接使用 `AddCustomHook` 注册的协议

**解析规则**：

```csharp
// ✅ 正确：从索引 0 开始（框架已过滤协议号）
void OnRecvProtocol(IVarList args)
{
    int index = 0;
    int param1 = args.GetInt32(index++);  // 第一个业务参数
    int param2 = args.GetInt32(index++);  // 第二个业务参数
}
```

**原因**：
- 服务端构造时从索引 1 开始（索引 0 是协议号）
- 客户端框架接收时已过滤索引 0（协议号）
- 客户端收到的 IVarList 从索引 0 开始就是业务参数

**参考实现**：搜索 `AddCustomHook SERVER_CUSTOMMSG` 找到标准实现

---

#### 1.3.2 BusinessActivity 框架协议解析规范

**适用场景**：通过 `RegisterSeverActivityParamArgs` 注册的活动协议

**解析规则**：

```csharp
// ✅ 正确：从 CustomStart 开始（跳过 13 个固定字段）
public override void ParamArgs(IVarList args)
{
    int index = (int)BAActivityInfoIndex.CustomStart;  // 索引 13
    int param1 = args.GetInt32(index++);  // 第一个自定义参数
    int param2 = args.GetInt32(index++);  // 第二个自定义参数
}

// ❌ 错误：从 0 开始会把 ActivityID 误读成业务参数
int index = 0;
int param1 = args.GetInt32(index++);  // 这会读到 ActivityID，不是自定义参数
```

**原因**：
- BusinessActivity 框架在协议前添加了 13 个固定字段：
  - [0-12]: ActivityID, ActivityState, BeginTime, EndTime, CurTurn, CurDay, ActivityType, EachTurnDays, UIType, ShowTime, TaskId, SeasonId
  - [13+]: 自定义业务参数
- `BActivityCommonParamArgs.GetParamArgs()` 返回完整协议（包含固定字段）

**参考实现**：`TrialModule_Config.cs:76`

```csharp
public override void ParamArgs(IVarList args)
{
    int index = (int)BAActivityInfoIndex.CustomStart;  // 从 13 开始
    int pointCount = args.GetInt32(index++);
    // ...
}
```

---

#### 1.3.3 其他框架协议（待补充）

**原则**：使用框架提供的参数解析方法前，必须先查看框架定义

**检查方式**：
1. 查看父类的参数结构定义（如 BAActivityInfoIndex）
2. 查找同框架的参考实现（CodeGraph 搜索同类型 ParamArgs）
3. 从参考实现确认起始索引

---

#### 1.3.4 文档体现（在 design-client.md 的"协议定义"章节）

**原始协议示例**：

```markdown
### S2C_XXX_INFO (协议号 XXX)

**解析方法**：`OnRecvXXXInfo(IVarList args)`

**参数列表**（从索引 0 开始）：

| 索引 | 字段 | 类型 | 说明 |
|-----|------|------|------|
| 0 | RechargeId | int | 充值配置ID |
| 1 | RewardId | int | 奖励ID |
| 2 | CurNum | long | 当前进度 |
| 3 | TargetNum | long | 目标进度 |

**参考实现**：`XXXModule.cs:123`
```

**BusinessActivity 框架协议示例**：

```markdown
### SERVER_CUSTOMMSG_BACTIVITY_INFO (协议号 470)

**解析方法**：`ParamArgs(IVarList args)` (继承自 BActivityParamArgs)

**参数列表**（从 CustomStart 索引 13 开始）：

| 索引偏移 | 字段 | 类型 | 说明 |
|---------|------|------|------|
| +0 | RechargeId | int | 充值配置ID |
| +1 | RewardId | int | 奖励ID |
| +2 | CurNum | long | 当前进度 |
| +3 | TargetNum | long | 目标进度 |

**框架固定字段**（索引 0-12）：由 BusinessActivityModule 自动处理

**参考实现**：`TrialModule_Config.cs:69-144`
```
```

---

### 方案 B：在代码审查阶段检查（兜底）

**修改文件**：`.claude/skills/lr-openspec-code-review/SKILL.md`

**步骤 1：加载检查清单** - 修改客户端检查清单：

```markdown
#### 客户端检查清单（client 组，共 6 项）

| ID | 检查项 | 规则来源 | 严重程度 |
|----|-------|---------|---------|
| client-001 | OnCellUpdated 参数类型检查 | client-structure.md § 2.1 | 高 |
| client-002 | DettachPage 拼写检查（双 t） | client-structure.md § 2.1 | 高 |
| client-003 | 红点计算触发时机检查 | client-structure.md 红点规则 | 中 |
| client-004 | BusinessActivityModule 接入检查 | client-structure.md § 1.1 | 高 |
| **client-005** | **原始协议解析起始索引检查** | **client-structure.md § 1.3.1** | **高** |
| **client-006** | **BusinessActivity 协议解析起始索引检查** | **client-structure.md § 1.3.2** | **高** |
```

**步骤 4：执行客户端检查** - 新增两个检查项：

```markdown
#### 4.5 原始协议解析起始索引检查（client-005）

**目标**：确认原始协议（AddCustomHook 注册）从索引 0 开始解析

**检查方法**：
```bash
# 找出所有协议处理函数
codegraph_explore("OnRecv AddCustomHook IVarList <模块名>Module", 
                  projectPath: "D:/se/develop/client/project")
```

**检查规则**：
- ✅ 正确模式：`int index = 0;` 或直接 `args.GetInt32(0)`
- ❌ 错误模式：`int index = 1;` 或 `args.GetInt32(1)` 作为第一个业务参数

**报告格式**（若发现问题）：
```
❌ client-005: 原始协议解析起始索引错误

文件: XXXModule.cs:123
问题: OnRecvXXXInfo 方法从 index=1 开始解析，跳过了第一个业务参数

当前代码:
  int index = 1;
  int param1 = args.GetInt32(index++);  // ← 这会跳过索引 0

应改为:
  int index = 0;
  int param1 = args.GetInt32(index++);

原因: 客户端框架已过滤协议号，业务参数从索引 0 开始
```

---

#### 4.6 BusinessActivity 协议解析起始索引检查（client-006）

**目标**：确认 BusinessActivity 框架的 ParamArgs 方法从 CustomStart 开始解析

**检查方法**：
```bash
codegraph_explore("ParamArgs IVarList BAActivityInfoIndex <模块名>Module", 
                  projectPath: "D:/se/develop/client/project")
```

**检查规则**：
- ✅ 正确模式：`int index = (int)BAActivityInfoIndex.CustomStart;`
- ❌ 错误模式：`int index = 0;`（会把 ActivityID 误读成业务参数）

**参考实现**：`TrialModule_Config.cs:76`

**报告格式**（若发现问题）：
```
❌ client-006: BusinessActivity 协议解析起始索引错误

文件: MixGrowthFundModule_Config.cs:85
问题: ParamArgs 方法从 index=0 开始解析，跳过了 13 个 BusinessActivity 固定字段

当前代码:
  int index = 0;
  m_RechargeId = args.GetInt32(index++);  // ← 这会读到 ActivityID 而不是 RechargeId

应改为:
  int index = (int)BAActivityInfoIndex.CustomStart;
  m_RechargeId = args.GetInt32(index++);

参考: TrialModule_Config.cs:76
```
```

---

### 方案 C：在测试用例阶段验证（运行时）

**修改文件**：`schemas/lr-func-dev/rules/tasks/client-implementation.md`

**新增测试用例模板**：

```markdown
### 协议序列化/反序列化测试（通用）

**测试目的**：验证客户端协议解析与服务端下发数据一致

---

#### 原始协议测试

**测试步骤**：
1. 服务端构造测试数据：
   ```cpp
   CVarList msg;
   msg << CLIENT_CUSTOMMSG_XXX_INFO;  // 协议号（索引 0，客户端框架会过滤）
   msg << 1001;  // param1（客户端索引 0）
   msg << 2002;  // param2（客户端索引 1）
   ```

2. 模拟服务端下发协议

3. 客户端解析后验证：
   - `param1 == 1001`（不是协议号）
   - `param2 == 2002`

**预期结果**：所有字段值与服务端下发一致

**失败诊断**：
- 若 `param1` 等于协议号 → 解析起始索引错误（应从 0 开始）

---

#### BusinessActivity 协议测试

**测试步骤**：
1. 服务端构造测试数据（模拟 BusinessActivityModule 框架）：
   ```cpp
   CVarList msg;
   msg << SERVER_CUSTOMMSG_BACTIVITY_INFO;  // 协议号
   msg << activityID;       // 索引 0
   msg << activityState;    // 索引 1
   // ... 共 13 个固定字段
   msg << 1001;  // RechargeId（索引 13，CustomStart）
   msg << 2001;  // RewardId（索引 14）
   ```

2. 模拟服务端下发协议

3. 客户端解析后验证：
   - `m_RechargeId == 1001`（不是 ActivityID 的值）
   - `RewardId == 2001`（不是 ActivityState 的值）

**预期结果**：所有自定义字段值与服务端下发一致

**失败诊断**：
- 若 `m_RechargeId` 等于 ActivityID 的值 → 解析起始索引错误（应从 CustomStart 开始）
```

---

## 根因总结

### 为什么这次会疏漏？（通用视角）

1. **设计规则不对称**：
   - ✅ 服务端有明确规范（`args.IntVal(1)` 开始）
   - ❌ 客户端完全没有规范（原始协议、框架协议都未说明）

2. **缺少通用协议规范章节**：
   - `client-structure.md` 只说明了业务逻辑（Record、UI、红点）
   - **未说明协议解析这个基础操作**

3. **代码审查检查项不全**：
   - 服务端有 server-001（协议参数索引）
   - 客户端**完全没有协议解析检查**

4. **测试用例未覆盖**：
   - 只有功能性测试（购买、领取）
   - **未验证协议字段对齐**（序列化/反序列化测试）

---

## 立即行动项（通用版）

需要修改以下文件补齐**通用协议规范**：

### 1. 设计规则（阻断性）
**文件**：`schemas/lr-func-dev/rules/design/client-structure.md`
**修改**：新增 § 1.3 协议解析通用规范
- § 1.3.1 原始协议解析规范（从索引 0 开始）
- § 1.3.2 BusinessActivity 框架协议解析规范（从 CustomStart 开始）
- § 1.3.3 其他框架协议（待补充）

### 2. 代码审查检查项（兜底）
**文件**：`.claude/skills/lr-openspec-code-review/SKILL.md`
**修改**：新增 client-005 和 client-006 检查项
- client-005: 原始协议解析起始索引检查
- client-006: BusinessActivity 协议解析起始索引检查

### 3. 测试用例模板（验证）
**文件**：`schemas/lr-func-dev/rules/tasks/client-implementation.md`
**修改**：新增协议序列化/反序列化测试用例模板
- 原始协议测试
- BusinessActivity 协议测试

---

## 预期效果

### 实施后的流程改进

**阶段 5：设计生成**（方案 A）
```
/lr-openspec-design growth-fund
→ design/client.md 自动生成协议解析示例代码
→ 原始协议：明确从索引 0 开始
→ BusinessActivity 协议：明确从 CustomStart 开始
→ 引用参考实现位置
```

**阶段 9：代码实施**
```
AI 读取 design/client.md
→ 看到协议类型和解析规范
→ 判断是原始协议还是框架协议
→ 按对应规范实现 ✅
```

**阶段 11a：代码审查**（方案 B）
```
/lr-openspec-code-review growth-fund
→ 执行 client-005 检查（原始协议）
→ 执行 client-006 检查（BusinessActivity 协议）
→ 自动检测起始索引是否正确
→ 若错误，输出报告并指出参考实现
```

**阶段 11b：测试验证**（方案 C）
```
/lr-openspec-test-validate growth-fund
→ 运行协议序列化/反序列化测试
→ 验证服务端下发值 = 客户端解析值
→ 若不一致，报告字段错位问题
```

---

## 总结

### 核心观点

这不是 **BusinessActivity 框架特有的问题**，而是**前后端协议交互的通用规范问题**：

| 层面 | 服务端 | 客户端 |
|-----|-------|-------|
| **规范状态** | ✅ 已明确（从索引 1 开始） | ❌ 完全缺失 |
| **设计规则** | ✅ server-structure.md § 1.1 | ❌ 无 |
| **代码审查** | ✅ server-001 检查 | ❌ 无 |
| **测试验证** | ❌ 无 | ❌ 无 |

### 修正范围

不应该只针对 BusinessActivity 框架，应该补齐**所有协议类型**的解析规范：

1. **原始协议**（AddCustomHook）→ 从索引 0 开始
2. **BusinessActivity 协议**（BActivityParamArgs）→ 从 CustomStart（13）开始
3. **其他框架协议**（待发现）→ 按框架定义

### 三层防护（通用版）

| 层级 | 阶段 | 方案 | 作用 |
|-----|------|------|------|
| **第一层：设计规范** | 阶段 5（设计） | 方案 A | **预防错误进入实施** |
| **第二层：自动检查** | 阶段 11a（审查） | 方案 B | **自动发现实施错误** |
| **第三层：测试验证** | 阶段 11b（测试） | 方案 C | **运行时发现逻辑错误** |
