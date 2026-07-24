---
name: lr-openspec-rule-candidates
description: 规则沉淀与文档补充：综合前三阶段发现，生成候选清单供人工勾选，回写config.yaml/schemas/design.md
---

# lr-openspec-rule-candidates

> **职责**: 综合 reconcile/code-review/test-validate 的发现，生成三类候选：本变更文档补充、规则沉淀到 config.yaml、schema 优化建议。
> **阶段**: 阶段 11c
> **依赖**: reconcile（可选）、code-review（必需）、test-validate（必需）

---

## 使用场景

**适用于**：
- 前三阶段完成后，总结共性问题并沉淀为规则
- 发现 apply 中途添加的临场优化，补充到 design.md
- 优化 schema 规则文件，提升下一次变更的质量

**核心价值**：
- **本变更文档补充**：防止 design.md 变成过时文档
- **规则沉淀（config.yaml）**：让下一次变更自动避开本次踩的坑
- **schema 优化**：让规则文件更精准，reconcile/code-review 更自动化

---

## 使用方式

```bash
/lr-openspec-rule-candidates growth-fund
```

---

## 执行流程

### 步骤 1：读取前三阶段报告

```bash
Read(changes/{change-id}/reconcile-report.md)  # 可选，可能不存在
Read(changes/{change-id}/code-review-report.md)
Read(changes/{change-id}/test-validate-report.md)
```

如果 `reconcile-report.md` 不存在：
```
⚠️ 未找到 reconcile-report.md，跳过差异模式分析
   如需完整分析，请先运行 /lr-openspec-reconcile growth-fund
```

---

### 步骤 2：读取设计文档和实际代码

```bash
Read(changes/{change-id}/design.md)
Read(changes/{change-id}/implementation-report.md)
```

**对比分析**：
- design.md 提到的功能 vs implementation-report.md 实际文件清单
- 找出"代码里有但设计文档没写"的部分

---

### 步骤 3：生成候选清单

#### 输出 1：本变更文档补充建议

**来源**：
1. reconcile-report 的差异清单（代码多了字段/函数，但设计没写）
2. implementation-report 里提到的"实施时修正"（AI 自己记录的偏差）
3. CodeGraph 扫描实际代码，发现 design.md 没提到的功能点

**示例**：
```
场景 1：reconcile 发现 GoodID 字段代码有但 design.md 没写
→ 建议在 design.md 附录 B 补充：
  | GoodID | int | 基金商品ID（用于多基金并存时区分商品） | 实施时补充 |

场景 2：CodeGraph 发现背包满检查逻辑，但 design.md 交互流程没提
→ 建议在 design.md "附录 A → 交互流程 → 领取流程" 补充：
  客户端本地校验背包是否已满（背包已满则直接提示"背包已满"，不发送协议）

场景 3：implementation-report 提到"实施时发现红点框架有现成方法"
→ 建议在 design.md "附录 A → 红点规则" 补充框架方法说明
```

**输出格式**：
```markdown
## 📝 本变更文档补充建议

### 建议 1：design.md 补充 GoodID 字段说明

- [ ] **采纳此建议**

**位置**: 附录 B → Record 表定义 → GROWTH_FUND_OPEN_REC

**补充内容**:
```markdown
| GoodID | int | 基金商品ID（用于多基金并存时区分商品） | 实施时补充 |
```

**理由**: reconcile-report 发现实际代码有此字段，但 design.md 没写

**回写目标**: `changes/growth-fund/design.md` 第 285 行附近（附录 B Record 表定义表格）

---

### 建议 2：design.md 补充背包满保护逻辑

- [ ] **采纳此建议**

**位置**: 附录 A → 交互流程 → 领取流程

**补充内容**:
```markdown
客户端本地校验背包是否已满（背包已满则直接提示"背包已满"，不发送协议）
```

**理由**: implementation-report.md 显示实现了此逻辑（GrowthFundPage.cs:142），但设计文档缺失

**回写目标**: `changes/growth-fund/design.md` 第 200 行附近（交互流程章节）
```

---

#### 输出 2：规则沉淀候选（写入 config.yaml）

**来源**：
1. code-review 发现的共性问题（如 3 处都忘记检查 null）
2. reconcile 发现的命名不一致（如 5 处字段名大小写混乱）
3. design.md 反复强调的约束（如"所有活动必须接入 BA 框架"）

**提取规则的标准**：
- **共性问题**：至少出现 2 次
- **严重程度**：高或中（低优先级问题不沉淀）
- **可检查性**：能被 reconcile/code-review 自动检查

**示例**：
```
来源 1：code-review 发现 3 处 FindRecord 后没有 null 检查
→ 候选规则：design-server 阶段要求"所有 Record 查询必须有 null 保护示例"

来源 2：reconcile 发现 5 处配置字段命名不一致（驼峰 vs 下划线）
→ 候选规则：design-config 阶段要求"配置表字段统一用 snake_case 命名"

来源 3：design.md 第 12 行强调"必须接入 BusinessActivityModule"
→ 候选规则：design-client 阶段要求"确认活动是否接入 BA 框架"
```

**输出格式**：
```markdown
## 🔧 规则沉淀候选（写入 config.yaml）

### 规则 1：Record 查询后必须检查 null

- [ ] **采纳此规则**

**适用阶段**: `design-server`

**规则内容**: 
```
所有 Record 表查询（FindRecord）后必须检查返回值是否为 null，示例代码必须包含 null 保护。
```

**严重程度**: 高

**证据来源**: 
- code-review 发现 3 处遗漏（可能导致空指针崩溃）
- growth-fund 实施时手动补充了保护逻辑

**回写目标**: `config.yaml` → `rules.design-server` 数组

**预期效果**: 下一次生成 design-server.md 时，AI 会自动在 Record 表操作示例中加上 null 检查

---

### 规则 2：配置表字段统一用 snake_case 命名

- [ ] **采纳此规则**

**适用阶段**: `design-config`

**规则内容**: 
```
配置表 Excel 列名必须用 snake_case（如 recharge_id），不用驼峰（RechargeId）。
```

**严重程度**: 中

**证据来源**: 
- reconcile 发现 5 处命名不一致，导致客户端/服务端字段映射混乱
- 服务端框架对字段名大小写敏感

**回写目标**: `config.yaml` → `rules.design-config` 数组

**预期效果**: 下一次生成 design-config.md 时，AI 会在字段定义表格中强制使用 snake_case

---

### 规则 3：活动必须接入 BusinessActivityModule 框架

- [ ] **采纳此规则**

**适用阶段**: `design-client`

**规则内容**: 
```
确认活动是否接入 BA 框架：如果 BusinessActivityDefine.cs 存在对应枚举（如 BA_TYPE_MIX_GROWFUND），则必须接入，不能自建独立 Panel。
```

**严重程度**: 高

**证据来源**: 
- design.md 第 12 行反复强调
- 历史上有独立实现导致后续难以维护（需要在规则里写明历史教训）

**回写目标**: `config.yaml` → `rules.design-client` 数组

**预期效果**: 下一次生成 design-client.md 时，AI 会强制检查 BA 框架接入
```

---

#### 输出 3：Schema 优化建议（写入 schemas/lr-func-dev/）

**来源**：
1. reconcile 时发现"难以自动化验证"的点（如协议参数顺序）
2. code-review 时发现规则文件里缺失的检查项（如红点触发时机）
3. test-validate 时发现"可测试性"不足的设计模式

**提取标准**：
- **自动化痛点**：reconcile/code-review 无法机械检查的规则
- **规则缺失**：code-review 发现问题，但规则文件里没写
- **设计模式改进**：发现更好的设计约定，值得推广

**示例**：
```
痛点 1：reconcile 时无法自动验证协议参数顺序
→ 优化：design-server-structure.md 补充"协议定义必须包含参数顺序表"

痛点 2：code-review 发现红点在刷新循环中触发，但规则文件没有这条检查清单
→ 优化：design-client-structure.md 补充"红点计算禁止触发场景清单"

痛点 3：test-validate 发现大量"无法静态验证"的 TC，都是因为缺少单元级接口
→ 优化：design-client-structure.md 补充"可测试性设计要求"
```

**输出格式**：
```markdown
## 🏗️ Schema 优化建议（写入 schemas/lr-func-dev/）

### 优化 1：design-server 要求协议参数顺序表

- [ ] **采纳此优化**

**修改文件**: `schemas/lr-func-dev/rules/design/server-structure.md`

**修改位置**: 1.1 协议处理函数标准结构

**补充内容**:
```markdown
### 协议参数顺序表（必需）

协议定义必须包含参数顺序表，用于 reconcile 阶段自动对比：

| 索引 | 参数名 | 类型 | 说明 |
|-----|-------|------|------|
| 1   | activityID | int | 活动ID |
| 2   | tierIndex | int | 档位序号（0-based） |
| 3   | rewardType | int | 领取类型（1=免费/2=付费） |

**索引从 1 开始**（索引 0 是协议号本身）。
```

**理由**: reconcile 阶段难以自动化验证参数顺序，补充此要求后可机械对比

**预期效果**: 
- 下一次生成 design-server.md 时，协议章节自动包含参数顺序表
- reconcile 可以直接对比表格 vs `args.IntVal(n)` 顺序

---

### 优化 2：design-client 补充红点计算触发时机检查清单

- [ ] **采纳此优化**

**修改文件**: `schemas/lr-func-dev/rules/design/client-structure.md`

**修改位置**: 红点规则章节

**补充内容**:
```markdown
### 红点计算触发时机约束

⚠️ **禁止在以下场景触发红点计算**：
- `Update` / `LateUpdate` 循环（每帧触发，性能隐患）
- UI 刷新函数（`RefreshUI` / `OnRecvActivityInfo`）
- 定时器回调（高频触发）

✅ **正确触发点**：
- Record 表变化 Hook（`RegisterRecHook`）
- 业务状态变化回调（如任务完成、等级提升）

**检查方法**：
Grep `DirtyRedPoint` 调用点，确认上下文是 Record Hook 或状态变化回调。
```

**理由**: code-review 发现 1 处在刷新循环中触发红点（性能隐患），但规则文件缺失此条约束

**预期效果**: 
- 下一次生成 design-client.md 时，红点规则章节自动包含触发时机约束
- code-review 可以按此清单逐项检查

---

### 优化 3：design-client 补充可测试性设计要求

- [ ] **采纳此优化**

**修改文件**: `schemas/lr-func-dev/rules/design/client-structure.md`

**修改位置**: 新增章节"六、可测试性设计"

**补充内容**:
```markdown
## 六、可测试性设计

为了提升 test-validate 阶段的静态验证能力，设计时应遵循：

### 6.1 边界保护逻辑独立

将边界保护逻辑（如背包满检查、防重复领取）提取为独立函数：
```csharp
bool CanClaim(int tier) {
    if (HasClaimed(tier)) return false;
    if (!ConditionMet(tier)) return false;
    if (ItemModule.CheckBagFull()) return false;
    return true;
}
```

这样 test-validate 可以静态验证"CanClaim 是否覆盖所有边界条件"。

### 6.2 状态机显式化

避免隐式状态机（散落在多个 if/else），用枚举显式定义状态：
```csharp
enum RewardState { Locked, Unlocked, Claimed }
RewardState GetRewardState(int tier);
```

这样 test-validate 可以验证状态转换逻辑完整性。
```

**理由**: test-validate 发现 76 个 TC 无法静态验证，主要因为逻辑耦合在 UI 刷新函数中

**预期效果**: 
- 下一次生成 design-client.md 时，自动包含可测试性设计要求
- 提升静态验证覆盖率（从 28 项提升到 50+ 项）
```

---

### 步骤 4：生成 rule-candidates.md

```bash
Write(changes/{change-id}/rule-candidates.md)
```

**完整结构**：
```markdown
# Growth Fund Rule Candidates

**生成时间**: 2026-07-24
**综合来源**: reconcile-report + code-review-report + test-validate-report + design.md

---

## 📝 本变更文档补充建议

[输出 1 的内容]

---

## 🔧 规则沉淀候选（写入 config.yaml）

[输出 2 的内容]

---

## 🏗️ Schema 优化建议（写入 schemas/lr-func-dev/）

[输出 3 的内容]

---

## 📊 统计

- 本变更文档补充建议：2 项
- 规则沉淀候选（config.yaml）：3 项
- Schema 优化建议：3 项
- 总计：8 项

---

## 📋 使用说明

1. **编辑此文件**，在需要采纳的条目前打勾 `[x]`
2. **保存文件**
3. **回复 'continue'**，AI 将根据勾选结果执行回写

**编辑示例**：
```markdown
- [x] **采纳此建议**  ← 打勾表示采纳
- [ ] **采纳此规则**  ← 不打勾表示不采纳
```
```

---

### 步骤 5：等待用户编辑并回复

```
✅ 已生成规则候选清单：changes/growth-fund/rule-candidates.md

📊 候选统计：
- 本变更文档补充建议：2 项
- 规则沉淀候选（config.yaml）：3 项
- Schema 优化建议：3 项
- 总计：8 项

📝 请编辑此文件，在需要采纳的条目前打勾 [x]，完成后回复 'continue'。
```

---

### 步骤 6：读取勾选结果并执行回写

用户回复 'continue' 后：

```bash
Read(changes/{change-id}/rule-candidates.md)
```

**解析勾选状态**：
```python
def parse_selections(md_content):
    selected = {"doc_amendments": [], "config_rules": [], "schema_optimizations": []}
    current_section = None
    current_item = None
    
    for line in md_content.split('\n'):
        if line.startswith('## 📝 本变更文档补充建议'):
            current_section = "doc_amendments"
        elif line.startswith('## 🔧 规则沉淀候选'):
            current_section = "config_rules"
        elif line.startswith('## 🏗️ Schema 优化建议'):
            current_section = "schema_optimizations"
        
        if line.startswith('- [x]'):  # 已勾选
            # 提取后续的"建议 N"或"规则 N"
            # 继续解析直到找到"回写目标"字段
            current_item = parse_item(line, following_lines)
            selected[current_section].append(current_item)
    
    return selected
```

---

### 步骤 7：执行回写操作

#### 7.1 回写本变更文档（design.md）

对每条已勾选的文档补充建议：

```bash
Read(changes/{change-id}/design.md)
Edit(changes/{change-id}/design.md):
  old_string: [原表格内容]
  new_string: [原表格内容 + 新增行]
```

**示例**：
```
建议 1：补充 GoodID 字段

回写目标：changes/growth-fund/design.md 第 285 行（附录 B Record 表定义表格）

执行：
Edit(changes/growth-fund/design.md):
  old_string: |
    | ActivityID | int | 活动ID | proposal已提 |
    | OpenTime | int | 开启时间戳 | proposal已提 |
  new_string: |
    | ActivityID | int | 活动ID | proposal已提 |
    | GoodID | int | 基金商品ID（用于多基金并存时区分商品） | 实施时补充 |
    | OpenTime | int | 开启时间戳 | proposal已提 |
```

---

#### 7.2 回写项目规则（config.yaml）

对每条已勾选的规则沉淀候选：

**健壮的回写策略**：

```bash
Read(config.yaml)

# 步骤 1：检查目标 key 是否存在
# 步骤 2：去重检查（避免重复写入相同规则）
# 步骤 3：使用 Edit 精确追加到数组末尾

Edit(config.yaml):
  old_string: |
    rules:
      design-server:
        - 任务必须使用 [Contract]、[Config]、[Server]、[Client]、[Integration] 分类。
        - 现有规则 2
        - 现有规则 3
  new_string: |
    rules:
      design-server:
        - 任务必须使用 [Contract]、[Config]、[Server]、[Client]、[Integration] 分类。
        - 现有规则 2
        - 现有规则 3
        - 所有 Record 表查询（FindRecord）后必须检查返回值是否为 null。
```

**关键点**：
- **old_string 必须包含整个数组块**（所有现有规则），而非只包含最后一条
- **去重逻辑**：回写前检查规则文本是否已存在（完全匹配），已存在则跳过
- **不存在的 key**：如果 `rules.design-server` 完全不存在，创建新 key：
  ```yaml
  rules:
    design-server:
      - 所有 Record 表查询（FindRecord）后必须检查返回值是否为 null。
  ```

**验证回写正确性**（回写后立即执行）：

```bash
# 验证 YAML 语法
Bash: python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# 如果语法错误，回滚并报告
```

---

#### 7.3 回写 Schema 规则文件（schemas/lr-func-dev/）

对每条已勾选的 schema 优化建议：

```bash
Read(schemas/lr-func-dev/rules/design/server-structure.md)
Edit(schemas/lr-func-dev/rules/design/server-structure.md):
  old_string: [原章节内容]
  new_string: [原章节内容 + 补充内容]
```

**示例**：
```
优化 1：补充协议参数顺序表要求

修改文件：schemas/lr-func-dev/rules/design/server-structure.md
修改位置：1.1 协议处理函数标准结构

执行：
Edit(schemas/lr-func-dev/rules/design/server-structure.md):
  old_string: |
    ## 1.1 协议处理函数标准结构
    
    参数从 `args.IntVal(1)` 开始（索引 0 是协议号）。
  new_string: |
    ## 1.1 协议处理函数标准结构
    
    参数从 `args.IntVal(1)` 开始（索引 0 是协议号）。
    
    ### 协议参数顺序表（必需）
    
    协议定义必须包含参数顺序表，用于 reconcile 阶段自动对比：
    
    | 索引 | 参数名 | 类型 | 说明 |
    |-----|-------|------|------|
    | 1   | activityID | int | 活动ID |
    ...
```

---

### 步骤 8：输出回写报告

**成功情况**：

```
✅ 回写完成！

📝 本变更文档补充：
  ✅ changes/growth-fund/design.md（补充 2 处遗漏）

🔧 规则沉淀（config.yaml）：
  ✅ rules.design-server：补充 1 条规则
  ✅ rules.design-config：补充 1 条规则
  ✅ rules.design-client：补充 1 条规则
  ✅ YAML 语法验证通过

🏗️ Schema 优化：
  ✅ schemas/lr-func-dev/rules/design/server-structure.md（补充协议参数顺序表要求）
  ✅ schemas/lr-func-dev/rules/design/client-structure.md（补充红点触发时机约束）

📋 统计：
  - 已勾选并回写：6 项
  - 未勾选（本次不采纳）：2 项

🎯 预期效果：
  - 下一次运行 /lr-openspec-design 时，AI 会自动应用新规则
  - reconcile/code-review 的检查能力得到增强

📌 下一步：
  - 运行 git diff 确认修改
  - 运行 openspec archive growth-fund 归档变更
```

---

**失败情况**（部分回写失败）：

```
⚠️ 回写部分完成

📝 本变更文档补充：
  ✅ design.md: 成功（2/2）

🔧 规则沉淀（config.yaml）：
  ❌ 失败：YAML 语法错误（第 28 行缩进不正确）
  
  原因：规则文本包含特殊字符，导致 YAML 解析失败
  已回滚 config.yaml 的修改

🏗️ Schema 优化：
  ✅ server-structure.md: 成功（1/1）
  ⚠️ client-structure.md: 跳过（目标章节"六、可测试性设计"不存在）

📋 统计：
  - 成功回写：3 项
  - 失败/跳过：2 项

🔍 失败排查：
  - config.yaml: 请检查 rule-candidates.md 中规则 2 的文本格式
  - client-structure.md: 目标章节不存在，需要手动创建后重新运行

📌 建议操作：
  1. 修复 rule-candidates.md 中的规则格式
  2. 重新运行 /lr-openspec-rule-candidates growth-fund
```

---

## 技术要点

### 规则提取策略

**共性问题识别**：
- 同类型错误出现 ≥ 2 次 → 值得沉淀
- 单次错误但严重程度高 → 也值得沉淀（防止下次再犯）

**规则粒度**：
- **太细**：`design-server 要求 OnCustomGetReward 第一个参数名为 player` ← 过度约束
- **太粗**：`design-server 要求代码质量高` ← 无法检查
- **合适**：`design-server 要求 Record 查询后必须检查 null` ← 可检查、有价值

**注意**：规则沉淀依赖前三阶段的发现（reconcile、code-review、test-validate），这些发现本质上是 AI 辅助的代码审查，而非自动化验证结果。

### artifact id 映射

| 规则适用阶段 | config.yaml key | 注入时机 |
|------------|----------------|---------|
| 客户端设计 | `rules.design-client` | 生成 design-client.md |
| 服务端设计 | `rules.design-server` | 生成 design-server.md |
| 配置设计 | `rules.design-config` | 生成 design-config.md |
| 任务生成 | `rules.tasks` | 生成 tasks.md |
| 提案生成 | `rules.proposal` | 生成 proposal.md |

**关键**：必须写到正确的 key，否则规则不会在对应阶段生效。

### 回写安全性

**防止破坏现有内容**：
- 使用 `Edit` 工具的精确匹配（old_string）
- 如果匹配失败，报错并要求人工介入
- 不使用正则替换或模糊匹配

**回写前确认**：
- 显示完整的 old_string / new_string diff
- 让用户有机会中止（通过 'continue' 确认机制）

---

## 常见问题

### Q1: 如果勾选了冲突的规则怎么办？

**A**: AI 会检测冲突（如同一位置要插入不同内容），报告冲突并要求用户重新编辑 rule-candidates.md。

---

### Q2: 规则沉淀后什么时候生效？

**A**: 下一次运行对应阶段时生效。例如 `rules.design-server` 在下一次运行 `/lr-openspec-design xxx` 时自动注入给 AI。

---

### Q3: 如何验证规则是否生效？

**A**: 运行 `openspec instructions design-server --change xxx`，查看输出的完整指令中是否包含新规则。

---

### Q4: 如果不确定某条规则是否该采纳？

**A**: 保持不勾选，先观察 1-2 次后续变更，如果同类问题反复出现，再手动编辑 config.yaml 补充。

---

## 版本信息

**版本**: v1.0  
**创建日期**: 2026-07-24  
**设计哲学**: AI 生成候选清单，人工决策后自动回写，规则精确注入到对应产物生成阶段
