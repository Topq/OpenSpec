# 协议解析疏漏分析：应在哪个阶段补齐

## 问题回顾

**疏漏内容**：MixGrowthFundPage.cs 的 ParseQueryInfo 方法从 `index = 0` 开始解析，未考虑 BusinessActivity 协议的 13 个固定字段（ActivityID 到 SeasonId），导致所有自定义字段错位解析。

**正确做法**：应从 `BAActivityInfoIndex.CustomStart`（索引 13）开始解析，参考 TrialModule_Config.cs 的标准实现。

**问题性质**：
- **基础性错误**：协议框架的基本使用规范
- **隐蔽性高**：编译通过，只有运行时才会发现数据错误
- **影响范围大**：所有字段错位，导致功能完全不可用

---

## 当前 OpenSpec 流程覆盖情况

### ✅ 已覆盖的环节

#### 1. **阶段 11a：代码审查 (lr-openspec-code-review)**

**检查项 server-001**：协议参数起始索引检查
- **检查对象**：服务端 `args.IntVal(0)` vs `args.IntVal(1)`
- **规则来源**：`server-structure.md § Q1`
- **严重程度**：高

**实际执行**：
```bash
codegraph_explore("OnCustom protocol handler args.IntVal MixGrowthFundModule")
```

**问题**：
- ✅ 覆盖了服务端协议**构造**（从索引 1 开始）
- ❌ **未覆盖客户端协议解析**（BusinessActivity 框架的 ParamArgs 方法）

---

### ❌ 未覆盖的环节

#### 1. **阶段 5：三端设计 (lr-openspec-design)**

**当前状态**：`design/client.md` 生成规则 (`client-structure.md`) 中**未明确说明协议解析起始位置**

**问题**：
- BusinessActivity 框架的协议解析规范未在设计规则中体现
- `BActivityCommonParamArgs.GetParamArgs()` 返回完整协议（含固定字段）这一事实未在规则中说明

**应补充位置**：`schemas/lr-func-dev/rules/design/client-structure.md`

---

#### 2. **阶段 6-8：测试用例生成 (lr-openspec-tasks → test-cases.md)**

**当前状态**：`test-cases.md` 未包含**协议序列化/反序列化单元测试**

**问题**：
- 缺少协议字段对齐的验证用例
- 例如：服务端发送 `RechargeId=1001`，客户端解析应得到 `1001`（而不是 ActivityID 的值）

**应补充位置**：`test-cases.md` 模板，增加协议解析测试用例

---

#### 3. **阶段 9：代码实施 (lr-openspec-apply → tasks.md)**

**当前状态**：`tasks.md` 中客户端协议解析任务**未明确参考实现**

**问题**：
- 任务描述只说"解析协议参数"，未说明应参考 `TrialModule_Config.cs` 等标准实现
- 未要求从 `BAActivityInfoIndex.CustomStart` 开始解析

**应补充位置**：`schemas/lr-func-dev/rules/tasks/client-implementation.md`

---

#### 4. **阶段 11a：代码审查 (lr-openspec-code-review)**

**当前状态**：客户端检查清单（client-001 到 client-004）**未包含协议解析检查**

**检查清单缺失**：

| ID | 检查项 | 规则来源 | 严重程度 |
|----|-------|---------|---------|
| ❌ client-005 | BusinessActivity 协议解析起始索引检查 | client-structure.md § 新增 | 高 |

**应补充位置**：`.claude/skills/lr-openspec-code-review/SKILL.md` 步骤 4

---

## 建议修正方案

### 方案 A：在设计阶段明确（阻断性，推荐）

**修改文件**：`schemas/lr-func-dev/rules/design/client-structure.md`

**新增章节**（在 § 1.2 之后）：

```markdown
### 1.3 BusinessActivity 协议解析规范（阻断性）

**适用范围**：所有接入 BusinessActivityModule 的功能

**解析规则**：

```csharp
// ✅ 正确：从 CustomStart 开始解析自定义数据
public override void ParamArgs(IVarList args)
{
    int index = (int)BAActivityInfoIndex.CustomStart;
    m_RechargeId = args.GetInt32(index++);
    // ... 继续解析自定义字段
}

// ❌ 错误：从 0 开始会把 ActivityID 误读成 RechargeId
public override void ParamArgs(IVarList args)
{
    int index = 0;  // ← 错误：跳过了 13 个固定字段
    m_RechargeId = args.GetInt32(index++);
}
```

**原因**：
- `BActivityCommonParamArgs.GetParamArgs()` 返回完整协议（包含 13 个固定字段）
- 自定义数据从 `BAActivityInfoIndex.CustomStart`（索引 13）开始
- 参考标准实现：`TrialModule_Config.cs:76`

**文档体现**（在 design-client.md 的"协议定义"章节）：
```markdown
### ParamArgs 解析（自定义数据）

从 `BAActivityInfoIndex.CustomStart` 开始解析：

| 索引偏移 | 字段 | 类型 | 说明 |
|---------|------|------|------|
| +0 | RechargeId | int | 充值配置ID |
| +1 | RewardId₁ | int | 第1档奖励ID |
| +2 | CurNum₁ | long | 第1档当前进度 |
| +3 | TargetNum₁ | long | 第1档目标进度 |
| ... | ... | ... | 后续档位重复 |

**参考实现**：`TrialModule_Config.cs:69-144`
```
```

---

### 方案 B：在测试用例阶段补齐（验证性）

**修改文件**：`schemas/lr-func-dev/rules/tasks/client-implementation.md`

**新增测试用例模板**（在"验收测试"章节）：

```markdown
### 协议序列化/反序列化测试

**测试目的**：验证客户端协议解析与服务端下发数据一致

**测试步骤**：
1. 服务端构造测试数据：
   - RechargeId = 1001
   - Tier 1: RewardId=2001, CurNum=100, TargetNum=500
   - Tier 2: RewardId=2002, CurNum=200, TargetNum=1000

2. 模拟服务端下发 SERVER_CUSTOMMSG_BACTIVITY_INFO 协议

3. 客户端解析后验证：
   - `m_RechargeId == 1001`（不是 ActivityID 的值）
   - `m_TierDataCache[0].RewardId == 2001`（不是 ActivityState 的值）
   - `m_TierDataCache[0].CurNum == 100`
   - `m_TierDataCache[0].TargetNum == 500`

**预期结果**：所有字段值与服务端下发一致

**失败诊断**：
- 若 `m_RechargeId` 等于 ActivityID 的值 → 解析起始索引错误（未从 CustomStart 开始）
```

---

### 方案 C：在代码审查阶段检查（兜底性）

**修改文件**：`.claude/skills/lr-openspec-code-review/SKILL.md`

**步骤 1：加载检查清单** - 新增检查项：

```markdown
#### 客户端检查清单（client 组，共 5 项）

| ID | 检查项 | 规则来源 | 严重程度 |
|----|-------|---------|---------|
| client-001 | OnCellUpdated 参数类型检查 | client-structure.md § 2.1 | 高 |
| client-002 | DettachPage 拼写检查（双 t） | client-structure.md § 2.1 | 高 |
| client-003 | 红点计算触发时机检查 | client-structure.md 红点规则 | 中 |
| client-004 | BusinessActivityModule 接入检查 | client-structure.md § 1.1 | 高 |
| **client-005** | **BusinessActivity 协议解析起始索引检查** | **client-structure.md § 1.3** | **高** |
```

**步骤 4：执行客户端检查** - 新增检查项：

```markdown
#### 4.5 BusinessActivity 协议解析起始索引检查

**目标**：确认 BusinessActivity 框架的 ParamArgs 方法从 `BAActivityInfoIndex.CustomStart` 开始解析

**检查方法**：
```bash
codegraph_explore("ParamArgs IVarList BAActivityInfoIndex <模块名>Module", 
                  projectPath: "D:/se/develop/client/project")
```

**检查规则**：
- ✅ 正确模式：`int index = (int)BAActivityInfoIndex.CustomStart;`
- ❌ 错误模式：`int index = 0;`（会跳过 13 个固定字段）

**参考实现**：`TrialModule_Config.cs:76`

**报告格式**（若发现问题）：
```
❌ client-005: BusinessActivity 协议解析起始索引错误

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

## 推荐实施顺序

### 第一优先级：设计阶段明确（方案 A）

**为什么优先**：
- **最早介入**：在设计阶段就明确规范，避免错误进入实施
- **阻断性**：AI 在生成 design-client.md 时会自动引用规则
- **可参考**：明确指出标准实现位置（TrialModule_Config.cs）

**实施步骤**：
1. 修改 `schemas/lr-func-dev/rules/design/client-structure.md`（新增 § 1.3）
2. 下次执行 `/lr-openspec-design` 时自动生效

---

### 第二优先级：代码审查阶段检查（方案 C）

**为什么第二**：
- **兜底保障**：即使设计阶段遗漏，代码审查也能发现
- **自动化检查**：通过 CodeGraph 搜索可自动检测

**实施步骤**：
1. 修改 `.claude/skills/lr-openspec-code-review/SKILL.md`（新增 client-005）
2. 下次执行 `/lr-openspec-code-review` 时自动生效

---

### 第三优先级：测试用例阶段补齐（方案 B）

**为什么第三**：
- **验证性**：需要手动编写测试代码，执行成本较高
- **发现较晚**：在测试阶段才发现，修复成本已较高

**实施步骤**：
1. 修改 `schemas/lr-func-dev/rules/tasks/client-implementation.md`（新增测试用例模板）
2. 下次执行 `/lr-openspec-tasks` 时，test-cases.md 会自动包含协议解析测试

---

## 根因分析

### 为什么这次会疏漏？

1. **设计规则不完整**：
   - `client-structure.md` 只说明了 BusinessActivityModule 接入判断（§ 1.1）
   - **未说明协议解析起始位置**（应有 § 1.3）

2. **缺少参考实现指引**：
   - 设计文档未明确指出应参考 `TrialModule_Config.cs`
   - AI 在实施时只关注"简化字段"目标，未对比同框架的标准实现

3. **代码审查检查项不全**：
   - 服务端有 server-001（协议参数起始索引检查）
   - **客户端缺少对应检查项**（client-005）

4. **测试用例未覆盖**：
   - test-cases.md 未包含协议序列化/反序列化测试
   - 只有功能性测试（购买、领取），未验证协议字段对齐

---

## 预期效果

### 实施方案 A + C 后的流程改进

**阶段 5：设计生成**（方案 A）
```
/lr-openspec-design growth-fund
→ design/client.md 自动生成协议解析示例代码
→ 明确标注"从 BAActivityInfoIndex.CustomStart 开始"
→ 引用参考实现 TrialModule_Config.cs:76
```

**阶段 9：代码实施**
```
AI 读取 design/client.md
→ 看到协议解析规范和参考实现
→ 按标准实现编写代码
→ 从 CustomStart 开始解析 ✅
```

**阶段 11a：代码审查**（方案 C）
```
/lr-openspec-code-review growth-fund
→ 执行 client-005 检查
→ CodeGraph 搜索 ParamArgs 方法
→ 自动检测起始索引是否正确
→ 若错误，输出报告并指出参考实现
```

---

## 总结

### 最佳实践：三层防护

| 层级 | 阶段 | 方案 | 作用 |
|-----|------|------|------|
| **第一层：设计规范** | 阶段 5（设计） | 方案 A | **预防错误进入实施** |
| **第二层：自动检查** | 阶段 11a（审查） | 方案 C | **自动发现实施错误** |
| **第三层：测试验证** | 阶段 11b（测试） | 方案 B | **运行时发现逻辑错误** |

### 立即行动项

1. ✅ **修改 client-structure.md**（新增 § 1.3 协议解析规范）
2. ✅ **修改 lr-openspec-code-review/SKILL.md**（新增 client-005 检查项）
3. 🔲 修改 client-implementation.md（新增协议解析测试用例模板）

### 长期改进

- **规则沉淀**：将本次问题添加到 `lr-openspec-rule-candidates`，作为客户端设计规则的强化项
- **参考库建设**：在 client-structure.md 中明确列出各框架的标准参考实现（BusinessActivity → TrialModule，UI → XXX）
