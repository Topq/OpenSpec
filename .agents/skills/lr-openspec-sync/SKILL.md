---
name: lr-openspec-sync
description: 同步代码改动到 design.md（可选 tasks.md），扫描协议参数/Record字段/配置字段/UI组件差异，生成回写建议供人工勾选后自动回写
---

# lr-openspec-sync

> **职责**: 扫描实际代码与 design.md 的差异，只关注"代码有但设计文档没写"的遗漏，生成回写建议清单，人工勾选后自动回写。
> **阶段**: 不绑定固定阶段，独立工具
> **推荐时机**: test-validate 阶段完成、代码已趋于稳定后
> **依赖**: apply 阶段完成（不要求 reconcile/code-review/test-validate 先跑）

---

## 使用场景

**适用于**：
- 代码在验收/测试过程中被反复修改，design.md 逐渐与实际实现脱节
- 想在归档/规则沉淀前，先确保 design.md 反映最终代码
- 只想快速核对某个范围（如协议参数）是否需要补文档，不想跑完整的 reconcile

**不做**：
- 不判断代码对错（不是 code-review 的职责）
- 不检查测试覆盖（不是 test-validate 的职责）
- 不沉淀规则到 config.yaml/schemas（那是 rule-candidates 的职责）
- 不修改代码本身，只输出"文档要不要改"的建议

**与 reconcile / rule-candidates 的关系**：

| 维度 | sync | reconcile | rule-candidates |
|-----|------|-----------|-----------------|
| 定位 | 轻量、可反复运行的文档同步工具 | 深度一致性检查（含命名风格、参数顺序等） | 归档前一次性总结（含规则沉淀、schema 优化） |
| 输出 | `sync-suggestions.md`（可回写） | `reconcile-report.md`（只读报告） | `rule-candidates.md`（可回写 design.md/config.yaml/schemas） |
| 是否自动回写 | ✅ 是 | ❌ 否，只列差异 | ✅ 是（文档补充部分） |
| 推荐频率 | 随时，可多次 | 一次（apply 后，多人协作场景） | 一次（归档前） |
| 是否必需 | 可选 | 可选 | 推荐 |

**没有强制时机**：sync 不是流程中的硬性节点，不依赖其他 SKILL，也不会被其他 SKILL 检查是否已运行。什么时候用、用不用，由使用者自行判断。

---

## 使用方式

```bash
/lr-openspec-sync growth-fund
```

可选范围（口头指定，AI 据此收窄检查范围）：
- "只同步协议参数"
- "只同步 Record 表字段"
- "同步 tasks.md"（默认只同步 design.md）

---

## 执行流程

### 步骤 1：读取输入

```
Read(changes/{change-id}/design.md)
Read(changes/{change-id}/implementation-report.md)
```

若变更目录下已有 `reconcile-report.md`，优先复用其差异发现，避免重复扫描代码：

```
Read(changes/{change-id}/reconcile-report.md)  # 若存在
```

### 步骤 2：三层扫描策略

不依赖 implementation-report.md 的完整性，直接扫描代码。从 config.yaml 读取项目路径：
- 服务端：`D:\se\develop\server\project`（从 context 里的 `../develop/server/project` 解析）
- 客户端：`D:\se\develop\client\project`（从 context 里的 `../develop/client/project` 解析）

#### 第 1 层：优先扫描 implementation-report.md 列出的文件

从 implementation-report.md 提取已知改动文件清单，对每个文件做深度 Grep 扫描：

```bash
# 示例：扫描服务端文件
Grep(
    pattern="args\\.(IntVal|StringVal)\\([0-9]+\\)",
    path="../develop/server/project/FsGame/ActivityModule/BusinessActivity/GrowthFund/MixGrowthFundEventCallBack.cpp",
    output_mode="content"
)
```

检查：
- 协议参数（**必须双向检查**，见下方"协议参数双向检查"说明）
- Record 操作：提取 `RecCol.FieldName`，对比 design.md Record 表定义
- 配置加载：提取 `txt.ReadInt/ReadString("FieldName")`，对比 design.md 配置表定义
- UI 组件（客户端）：提取 `GameObject/Button/TextMeshProUGUI m_FieldName`，对比 design.md UI 组件映射表

#### 协议参数双向检查（易漏项，必须两个方向都做）

协议参数不是单向的："客户端发给服务端"和"服务端返回/下发给客户端"是两条独立的数据流，字段数量可能完全不同，必须分别核对：

**方向 A：C→S（客户端发起，服务端解析入参）**

```bash
Grep(pattern="args\\.(IntVal|StringVal)\\([0-9]+\\)", path="<协议处理函数所在文件>", output_mode="content")
```
提取 `args.IntVal(N)` 的最大 N，对比 design.md 声明的入参数量。

**方向 B：S→C（服务端下发，含同步 RPC 的返回值，如 `OnBizActivCustomQueryInfo` 这类"调用即返回"的协议）**

不要只 Grep `outArgs <<` 的行数——如果写在循环里，Grep 单行匹配数不出"每组重复几个字段"这种结构信息。必须用 `Read` 工具完整读出该函数体，人工数清楚：
1. 循环外一次性写入的字段数（对应"一次性主配置"）
2. 循环内每次迭代写入的字段数（对应"每档/每组重复的字段"）

然后对比客户端的解析逻辑（通常是 `outArgs.GetInt32/GetInt64(index++)` 或固定步长的 while 循环），确认客户端预期的字段数与服务端实际写入的字段数一致，同时对比 design.md 声明的字段数与两端是否一致。

**判断一个协议是否需要检查方向 B**：只要 design.md 的协议表格里该协议的"方向"标注包含 S→C，或标注为"同步RPC"（outArgs 即返回值），就必须做方向 B 检查，不能只查方向 A 就跳过。

**优点**：快速（只扫描 10-20 个已知文件），准确度高

#### 第 2 层：扫描 design.md 提到的模块目录

扫描整个模块目录（不局限于 implementation-report.md）：

```bash
# 服务端模块目录
Grep(
    pattern="args\\.IntVal\\([0-9]+\\)",
    path="../develop/server/project/FsGame/ActivityModule/BusinessActivity/GrowthFund/",
    output_mode="content"
)

# 客户端模块目录
Grep(
    pattern="BAMixGrowthFundRewardRecCol\\.(\\w+)",
    path="../develop/client/project/Assets/Script/LogicModule/ActivityModule/MixGrowthFundModule/",
    output_mode="content"
)
```

**优点**：覆盖整个模块，不会因 implementation-report.md 遗漏某个文件而漏检

#### 第 3 层：回退到全局搜索（可选）

仅在前两层无结果或怀疑有跨模块改动时执行：

```bash
Grep(
    pattern="MixGrowthFund|BA_TYPE_MIX_GROWFUND",
    path="../develop/server/project/FsGame",
    glob="*.cpp",
    output_mode="files_with_matches"
)
```

检查范围（四类差异，只关注"代码有但 design.md 没写"的方向）：
1. **协议参数**：design.md 声明的参数数量 vs 代码实际解析/写入的参数数量（C→S 和 S→C 两个方向都要查，见上方"协议参数双向检查"）
2. **Record 表字段**：design.md 列出的列 vs 代码实际使用的列（`GetInt`/`SetInt` 等）
3. **配置表字段**：design.md 字段定义表 vs 代码实际加载的字段（`ReadInt`/`ReadString` 等）
4. **UI 组件**（客户端专属）：design.md「UI 组件映射」表 vs 代码实际声明的组件字段（`m_` 前缀）

**只关注"代码有但 design.md 没写"的方向**（即遗漏）。命名风格不一致、参数顺序等问题不在本 SKILL 处理范围，交给 `/lr-openspec-reconcile`。

### 步骤 3：生成 sync-suggestions.md

格式参考 `rule-candidates.md` 的"本变更文档补充建议"区块，人工打勾确认：

```markdown
# {变更名} Sync Suggestions

**生成时间**: {时间}
**对比范围**: design.md vs 实际代码（implementation-report.md 列出的文件）

---

## 📝 design.md 回写建议

### 建议 1：补充协议第 4 个参数 goodId

- [ ] **采纳此建议**

**位置**: design.md 附录A「网络协议」

**代码依据**: `MixGrowthFundEventCallBack.cpp:156` 使用了 `args.IntVal(4)`，但 design.md 只声明了 3 个参数

**补充内容**:
\`\`\`markdown
4. goodId (int) - 基金商品ID（多基金并存时区分）
\`\`\`

---

## 📊 统计
- design.md 回写建议：N 项
- 总计：N 项

---

## 使用说明
1. 编辑此文件，勾选需要采纳的建议
2. 保存文件
3. 回复 'continue'，AI 按勾选结果自动回写 design.md
```

若未发现差异，直接输出"✅ design.md 与代码一致，无需回写"，不生成文件。

### 步骤 4：人工确认后回写

用户回复 'continue' 后：
- 用 `Edit` 工具做精确匹配回写（`old_string`/`new_string`），不使用正则或模糊替换
- 回写前展示完整 diff
- 若匹配失败，报错并要求人工介入定位（不强行插入）

---

## 常见问题

### Q1: sync 和 reconcile 有什么区别？

**A**: `reconcile` 做深度一致性检查（含命名风格、参数顺序、类型是否兼容），只出报告不回写，适合多人协作场景下的一次性核查。`sync` 更轻量，只关注"代码有但设计文档没写"的遗漏，并直接生成可回写的建议，可以在整个变更周期内反复运行。

### Q2: 什么时候该用 sync？

**A**: 没有强制时机。经验上，test-validate 阶段结束、代码逻辑已经稳定后运行一次收益最大，因为此时改动量已经收敛，不会重复生成建议。但也可以在策划验收、code-review 发现设计漏项后随时运行。

### Q3: 已经运行过 rule-candidates 了，还需要 sync 吗？

**A**: 不冲突。`rule-candidates` 的"本变更文档补充建议"覆盖的是类似需求，如果那部分已经覆盖了当前差异，`sync` 会发现"无差异"直接结束。`sync` 存在的意义是可以在 `rule-candidates` 之前多次独立运行，尽早让 design.md 保持最新。

### Q4: 如果发现的差异其实是代码写错了（不该回写到设计），怎么处理？

**A**: 不勾选对应建议即可。`sync` 只列出"疑似遗漏"，不判断对错，人工确认后再决定是回写文档还是回去改代码。

---

## 版本信息

**版本**: v1.0
**创建日期**: 2026-08-01
**设计哲学**: 独立、轻量、可反复运行的文档同步工具，不绑定任何流程阶段，不依赖其他 SKILL
