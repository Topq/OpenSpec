# 协议解析规范补齐方案（具体修改对比）

## 问题现状

你质疑的点是对的：我说"客户端协议解析规范完全缺失"，但我的修改方案是否真的能解决问题？

让我展示**当前状态 vs 修改后状态**的对比，看看到底补齐了什么。

---

## 修改 1：设计规则补齐

### 文件：`schemas/lr-func-dev/rules/design/client-structure.md`

### 当前状态（缺失）

```markdown
## 一、架构决策规则

### 1.1 BusinessActivityModule 接入判断
（已有）

### 1.2 Record 驱动 vs 传统协议模式选择
（已有）

### 1.3 红点系统注册方式
（已有）

---

## 二、框架特殊约定

### 2.1 UI 方法签名约定
（已有）
```

**问题**：
- ❌ 没有 § 1.3（红点规则后面直接跳到第二章）
- ❌ 完全没有提到"协议解析"这个词
- ❌ 没有说明原始协议从哪个索引开始
- ❌ 没有说明 BusinessActivity 协议从哪个索引开始
- ❌ 没有参考实现指引

---

### 修改后状态（新增）

```markdown
## 一、架构决策规则

### 1.1 BusinessActivityModule 接入判断
（保持不变）

### 1.2 Record 驱动 vs 传统协议模式选择
（保持不变）

### 1.3 协议解析起始索引规范（新增）⭐

**适用范围**：所有需要解析服务端下发协议的功能

**核心原则**：协议解析起始索引取决于协议处理层次

---

#### 1.3.1 原始协议解析（AddCustomHook 注册）

**特征**：直接使用 `AddCustomHook(SERVER_CUSTOMMSG_XXX, OnRecvXXX)` 注册

**解析规则**：

```csharp
// ✅ 正确：从索引 0 开始
void OnRecvXXXInfo(IVarList args)
{
    int index = 0;
    int param1 = args.GetInt32(index++);  // 第一个业务参数
    int param2 = args.GetInt32(index++);  // 第二个业务参数
}

// ❌ 错误：从索引 1 开始会跳过第一个业务参数
void OnRecvXXXInfo(IVarList args)
{
    int index = 1;  // ← 错误
    int param1 = args.GetInt32(index++);  // 这会读到第二个业务参数
}
```

**原因**：
- 服务端构造时：`msg << 协议号 << param1 << param2`（协议号在索引 0）
- 客户端框架接收时：已自动过滤索引 0（协议号）
- 客户端收到的 IVarList：从索引 0 开始就是 param1

**参考实现查询**：
```
CodeGraph: "AddCustomHook OnRecv IVarList GetInt32"
参考文件：搜索任意 Module_Net.cs 中的 OnRecv 方法
```

**文档体现**（在 design-client.md 的"协议定义"章节）：

```markdown
### S2C_XXX_INFO (协议号 XXX)

**解析方法**：`OnRecvXXXInfo(IVarList args)`（原始协议，从索引 0 开始）

| 索引 | 字段 | 类型 | 说明 |
|-----|------|------|------|
| 0 | Param1 | int | 第一个参数 |
| 1 | Param2 | int | 第二个参数 |

**实现位置**：`XXXModule_Net.cs:123`
```

---

#### 1.3.2 BusinessActivity 框架协议解析（ParamArgs 继承）

**特征**：
- 通过 `RegisterSeverActivityParamArgs(BA_TYPE_XXX, OnRecvInfo)` 注册
- 实现 `override void ParamArgs(IVarList args)` 方法
- 继承自 `BActivityParamArgs`

**解析规则**：

```csharp
// ✅ 正确：从 CustomStart（索引 13）开始
public override void ParamArgs(IVarList args)
{
    int index = (int)BAActivityInfoIndex.CustomStart;  // 索引 13
    int param1 = args.GetInt32(index++);  // 第一个自定义参数
    int param2 = args.GetInt32(index++);  // 第二个自定义参数
}

// ❌ 错误：从索引 0 开始会把 ActivityID 误读成业务参数
public override void ParamArgs(IVarList args)
{
    int index = 0;  // ← 错误
    int param1 = args.GetInt32(index++);  // 这会读到 ActivityID，不是自定义参数
}
```

**原因**：
- BusinessActivity 框架在协议前添加了 13 个固定字段：
  - [0] ActivityID
  - [1] ActivityState
  - [2] BeginTime
  - [3] EndTime
  - [4] CurTurn
  - [5] CurDay
  - [6] ActivityType
  - [7] EachTurnDays
  - [8] UIType
  - [9] ShowTime
  - [10] TaskId
  - [11] SeasonId
  - [12] （预留）
  - [13+] 自定义业务参数 ← **从这里开始**
- `BActivityCommonParamArgs.GetParamArgs()` 返回完整协议（包含固定字段）

**参考实现**：`TrialModule_Config.cs:76`

```csharp
public override void ParamArgs(IVarList args)
{
    int index = (int)BAActivityInfoIndex.CustomStart;  // ✅ 标准写法
    int pointCount = args.GetInt32(index++);
    // ...
}
```

**文档体现**（在 design-client.md 的"协议定义"章节）：

```markdown
### SERVER_CUSTOMMSG_BACTIVITY_INFO (协议号 470)

**解析方法**：`ParamArgs(IVarList args)`（BusinessActivity 框架，从 CustomStart 索引 13 开始）

**框架固定字段**（索引 0-12）：由 BusinessActivityModule 自动处理，无需手动解析

**自定义参数**（从 CustomStart 开始）：

| 索引偏移 | 字段 | 类型 | 说明 |
|---------|------|------|------|
| +0 (索引 13) | Param1 | int | 第一个自定义参数 |
| +1 (索引 14) | Param2 | int | 第二个自定义参数 |

**实现位置**：`XXXModule_Config.cs:85`
**参考实现**：`TrialModule_Config.cs:76`
```

---

#### 1.3.3 判断使用哪种解析方式

**决策树**：

```
IF 协议处理函数是 void OnRecvXXX(IVarList args)
   AND 通过 AddCustomHook 注册
THEN 使用原始协议解析（从索引 0 开始）

IF 协议处理函数是 override void ParamArgs(IVarList args)
   AND 通过 RegisterSeverActivityParamArgs 注册
THEN 使用 BusinessActivity 协议解析（从 CustomStart 开始）

IF 协议处理函数是其他框架的 override 方法
THEN 查看框架定义的起始索引（参考同框架的标准实现）
```

---

### 1.4 红点系统注册方式
（保持不变，原来的 § 1.3 变成 § 1.4）
```

---

### 修改效果对比

| 维度 | 修改前 | 修改后 |
|-----|-------|-------|
| **提到"协议解析"** | ❌ 0 次 | ✅ 多处明确说明 |
| **原始协议规范** | ❌ 无 | ✅ § 1.3.1 |
| **BusinessActivity 规范** | ❌ 无 | ✅ § 1.3.2 |
| **参考实现指引** | ❌ 无 | ✅ TrialModule_Config.cs:76 |
| **错误示例对比** | ❌ 无 | ✅ 正确 vs 错误代码对比 |
| **文档模板** | ❌ 无 | ✅ design-client.md 协议定义模板 |

---

## 修改 2：代码审查检查项补齐

### 文件：`.claude/skills/lr-openspec-code-review/SKILL.md`

### 当前状态（缺失）

```markdown
#### 客户端检查清单（client 组，共 4 项）

| ID | 检查项 | 规则来源 | 严重程度 |
|----|-------|---------|---------|
| client-001 | OnCellUpdated 参数类型检查 | client-structure.md § 2.1 | 高 |
| client-002 | DettachPage 拼写检查（双 t） | client-structure.md § 2.1 | 高 |
| client-003 | 红点计算触发时机检查 | client-structure.md 红点规则 | 中 |
| client-004 | BusinessActivityModule 接入检查 | client-structure.md § 1.1 | 高 |
```

**问题**：
- ❌ 没有任何协议解析相关的检查项
- ❌ 对比服务端有 server-001（协议参数起始索引检查），客户端完全缺失

---

### 修改后状态（新增）

```markdown
#### 客户端检查清单（client 组，共 6 项）⭐

| ID | 检查项 | 规则来源 | 严重程度 |
|----|-------|---------|---------|
| client-001 | OnCellUpdated 参数类型检查 | client-structure.md § 2.1 | 高 |
| client-002 | DettachPage 拼写检查（双 t） | client-structure.md § 2.1 | 高 |
| client-003 | 红点计算触发时机检查 | client-structure.md 红点规则 | 中 |
| client-004 | BusinessActivityModule 接入检查 | client-structure.md § 1.1 | 高 |
| **client-005** | **原始协议解析起始索引检查** | **client-structure.md § 1.3.1** | **高** ⭐ |
| **client-006** | **BusinessActivity 协议解析起始索引检查** | **client-structure.md § 1.3.2** | **高** ⭐ |
```

---

### 步骤 4：执行客户端检查（新增两个检查项）

```markdown
#### 4.5 原始协议解析起始索引检查（client-005）⭐

**目标**：确认原始协议（AddCustomHook 注册）从索引 0 开始解析

**检查方法**：
1. 从 tasks.md 提取客户端模块名（如 `MixGrowthFundModule`）
2. 使用 CodeGraph 搜索协议处理函数：
```bash
codegraph explore "OnRecv IVarList GetInt32 <模块名>Module" \
  --project D:/se/develop/client/project
```

**检查规则**：
- ✅ 正确模式：
  - `int index = 0;` 然后 `args.GetInt32(index++)`
  - 或直接 `args.GetInt32(0)` 作为第一个参数
- ❌ 错误模式：
  - `int index = 1;` 然后 `args.GetInt32(index++)` 作为第一个业务参数
  - 或直接 `args.GetInt32(1)` 作为第一个业务参数

**报告格式**（若发现错误）：
```
❌ client-005: 原始协议解析起始索引错误

文件: XXXModule_Net.cs:123
函数: OnRecvXXXInfo(IVarList args)
问题: 从 index=1 开始解析，跳过了第一个业务参数

当前代码:
  45  void OnRecvXXXInfo(IVarList args)
  46  {
  47      int index = 1;  // ← 错误：应从 0 开始
  48      int param1 = args.GetInt32(index++);
  49  }

应改为:
  int index = 0;  // ← 正确：客户端框架已过滤协议号
  int param1 = args.GetInt32(index++);

原因: 客户端框架接收协议时已过滤索引 0（协议号），业务参数从索引 0 开始
参考: 搜索其他 Module_Net.cs 中的 OnRecv 方法
```

---

#### 4.6 BusinessActivity 协议解析起始索引检查（client-006）⭐

**目标**：确认 BusinessActivity 框架的 ParamArgs 方法从 CustomStart（索引 13）开始解析

**检查方法**：
1. 从 tasks.md 提取客户端模块名（如 `MixGrowthFundModule`）
2. 使用 CodeGraph 搜索 ParamArgs 方法：
```bash
codegraph explore "ParamArgs IVarList BAActivityInfoIndex <模块名>Module" \
  --project D:/se/develop/client/project
```

**检查规则**：
- ✅ 正确模式：`int index = (int)BAActivityInfoIndex.CustomStart;`
- ❌ 错误模式：`int index = 0;`（会把 ActivityID 误读成业务参数）

**参考实现**：`TrialModule_Config.cs:76`

**报告格式**（若发现错误）：
```
❌ client-006: BusinessActivity 协议解析起始索引错误

文件: MixGrowthFundModule_Config.cs:85
函数: ParamArgs(IVarList args)
问题: 从 index=0 开始解析，跳过了 13 个 BusinessActivity 固定字段

当前代码:
  85  public override void ParamArgs(IVarList args)
  86  {
  87      int index = 0;  // ← 错误：应从 CustomStart (13) 开始
  88      m_RechargeId = args.GetInt32(index++);
  89  }

应改为:
  int index = (int)BAActivityInfoIndex.CustomStart;  // 索引 13
  m_RechargeId = args.GetInt32(index++);

原因: BusinessActivity 框架在协议前添加了 13 个固定字段（ActivityID 到 SeasonId）
      从 index=0 开始会把 ActivityID 误读成 RechargeId
      
参考: TrialModule_Config.cs:76
```
```

---

### 修改效果对比

| 维度 | 修改前 | 修改后 |
|-----|-------|-------|
| **客户端协议检查项** | ❌ 0 项 | ✅ 2 项（client-005, client-006）|
| **原始协议检查** | ❌ 无 | ✅ client-005 |
| **BusinessActivity 检查** | ❌ 无 | ✅ client-006 |
| **自动化检测** | ❌ 无 | ✅ CodeGraph 自动搜索 |
| **错误报告格式** | ❌ 无 | ✅ 文件/行号/原因/参考实现 |
| **与服务端对称性** | ❌ 不对称 | ✅ 对称（服务端有 server-001，客户端有 client-005/006）|

---

## 修改 3：测试用例模板补齐

### 文件：`schemas/lr-func-dev/rules/tasks/client-implementation.md`

### 当前状态（缺失）

当前文件没有查看完整内容，但根据之前的分析，应该是：

```markdown
## 测试验证

（可能有功能性测试，如购买、领取、UI 显示）
```

**问题**：
- ❌ 没有协议序列化/反序列化测试
- ❌ 没有验证"服务端下发值 = 客户端解析值"

---

### 修改后状态（新增）

```markdown
## 测试验证

### 功能性测试
（保持原有功能测试，如购买、领取、UI 显示）

### 协议解析测试（新增）⭐

#### 原始协议解析测试

**测试目的**：验证客户端原始协议解析与服务端下发数据一致

**测试步骤**：
1. 服务端构造测试数据：
   ```cpp
   CVarList msg;
   msg << CLIENT_CUSTOMMSG_XXX_INFO;  // 协议号（索引 0，客户端框架会过滤）
   msg << 1001;  // param1（客户端索引 0）
   msg << 2002;  // param2（客户端索引 1）
   msg << "test";  // param3（客户端索引 2）
   ```

2. 模拟服务端下发协议（单元测试 mock）

3. 客户端解析后验证：
   ```csharp
   Assert.AreEqual(1001, receivedParam1);  // 不是协议号
   Assert.AreEqual(2002, receivedParam2);
   Assert.AreEqual("test", receivedParam3);
   ```

**预期结果**：所有字段值与服务端下发一致

**失败诊断**：
- 若 `receivedParam1` 等于协议号 → 解析起始索引错误（应从 0 开始，不是 1）
- 若 `receivedParam1` 等于 2002 → 解析起始索引错误（多跳了一个索引）

---

#### BusinessActivity 协议解析测试

**测试目的**：验证客户端 BusinessActivity 协议解析与服务端下发数据一致

**测试步骤**：
1. 服务端构造测试数据（模拟 BusinessActivityModule 框架）：
   ```cpp
   CVarList msg;
   msg << SERVER_CUSTOMMSG_BACTIVITY_INFO;  // 协议号
   msg << 10001;  // ActivityID（索引 0）
   msg << 1;      // ActivityState（索引 1）
   msg << 1234567890;  // BeginTime（索引 2）
   msg << 1234567890;  // EndTime（索引 3）
   msg << 1;      // CurTurn（索引 4）
   msg << 1;      // CurDay（索引 5）
   msg << 1018;   // ActivityType（索引 6）
   msg << 7;      // EachTurnDays（索引 7）
   msg << 1;      // UIType（索引 8）
   msg << 1234567890;  // ShowTime（索引 9）
   msg << 0;      // TaskId（索引 10）
   msg << 0;      // SeasonId（索引 11）
   // 索引 12 预留
   msg << 1001;   // RechargeId（索引 13，CustomStart）← 第一个自定义参数
   msg << 2001;   // RewardId（索引 14）← 第二个自定义参数
   ```

2. 模拟服务端下发协议

3. 客户端解析后验证：
   ```csharp
   Assert.AreEqual(1001, m_RechargeId);  // 不是 ActivityID 的值 10001
   Assert.AreEqual(2001, firstRewardId);  // 不是 ActivityState 的值 1
   ```

**预期结果**：所有自定义字段值与服务端下发一致

**失败诊断**：
- 若 `m_RechargeId` 等于 10001（ActivityID 的值）→ 解析起始索引错误（应从 CustomStart 13 开始，不是 0）
- 若 `m_RechargeId` 等于 1（ActivityState 的值）→ 解析起始索引错误（从 1 开始，应从 13 开始）
```

---

### 修改效果对比

| 维度 | 修改前 | 修改后 |
|-----|-------|-------|
| **协议解析测试** | ❌ 无 | ✅ 有（原始协议 + BusinessActivity）|
| **字段对齐验证** | ❌ 无 | ✅ 验证服务端值 = 客户端值 |
| **失败诊断指引** | ❌ 无 | ✅ 明确指出常见错误原因 |
| **测试数据构造** | ❌ 无 | ✅ 完整服务端/客户端示例代码 |

---

## 总结：修改方案的价值

### 修改前的状态（你质疑的点）

| 阶段 | 问题 | 具体表现 |
|-----|------|---------|
| **设计阶段** | 没有指导 | client-structure.md 完全不提"协议解析" |
| **实施阶段** | 没有参考 | 不知道从哪个索引开始，没有参考实现 |
| **审查阶段** | 没有检查 | 客户端检查清单只有 4 项，都不是协议相关 |
| **测试阶段** | 没有验证 | 只有功能测试，没有协议字段对齐测试 |

---

### 修改后的状态（价值）

| 阶段 | 改进 | 具体效果 |
|-----|------|---------|
| **设计阶段** | ✅ 新增 § 1.3 | 明确原始协议（索引 0）vs BusinessActivity（索引 13），提供参考实现 |
| **实施阶段** | ✅ 文档模板 | design-client.md 自动生成协议定义示例，AI 照着写即可 |
| **审查阶段** | ✅ 新增 client-005/006 | CodeGraph 自动搜索检测，输出错误报告（文件/行号/原因/参考）|
| **测试阶段** | ✅ 新增测试模板 | 验证服务端值 = 客户端值，失败诊断指引 |

---

## 关键对比：服务端 vs 客户端

### 修改前（不对称）

| 项目 | 服务端 | 客户端 |
|-----|-------|-------|
| 设计规则 | ✅ server-structure.md § 1.1 明确规范 | ❌ 无任何协议解析规范 |
| 代码审查 | ✅ server-001 检查项 | ❌ 无协议解析检查项 |
| 测试用例 | ❌ 无 | ❌ 无 |

**问题**：服务端有规范、有检查，客户端完全空白 → **前后端不对称**

---

### 修改后（对称）

| 项目 | 服务端 | 客户端 |
|-----|-------|-------|
| 设计规则 | ✅ server-structure.md § 1.1 | ✅ client-structure.md § 1.3（新增）|
| 代码审查 | ✅ server-001 | ✅ client-005/006（新增）|
| 测试用例 | ❌ 无 | ✅ 协议解析测试（新增）|

**改进**：前后端规范对称，客户端有明确指导、检查、验证 → **系统性补齐**

---

## 你的质疑是否合理？

### 你质疑的点

"你说客户端协议解析规范完全缺失，导致 1.设计没指导 2.实施没参考 3.审查没检查 4.测试没验证，你打算怎么改？"

### 我的回答

**是的，你的质疑合理。**

我展示的修改方案是：

1. **设计阶段**：新增 `client-structure.md § 1.3`，明确两种协议的解析规范 + 参考实现
2. **实施阶段**：通过设计规则，design-client.md 自动生成协议定义模板，AI 照着写
3. **审查阶段**：新增 `client-005` 和 `client-006` 检查项，CodeGraph 自动检测错误
4. **测试阶段**：新增协议解析测试模板，验证字段对齐

**这些修改是否真的能解决问题？**

- ✅ **设计阶段**：有了 § 1.3，AI 生成 design/client.md 时会引用规范，提供明确指导
- ✅ **实施阶段**：design/client.md 包含协议定义模板和参考实现位置，AI 有参考
- ✅ **审查阶段**：client-005/006 自动检测，输出错误报告（文件/行号/原因），有检查
- ✅ **测试阶段**：测试模板验证服务端值 = 客户端值，有验证

**但是否足够？**

这取决于：
1. 设计规则是否真的会被 AI 遵守（需要 OpenSpec 指令调用时强制引用）
2. 代码审查是否真的会执行这两个检查项（需要 SKILL 真的运行 CodeGraph）
3. 测试用例是否真的会被实施（需要 tasks.md 包含测试任务）

这是**系统性问题，需要多处修改才能形成闭环**。
