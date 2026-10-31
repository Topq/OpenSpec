# Growth Fund Rule Candidates

**生成时间**: 2026-08-01
**综合来源**: code-review-report.md + test-validate-report.md + design.md + implementation-report.md + tasks.md
**说明**: 未找到 `reconcile-report.md`，本次跳过差异模式分析，仅基于 code-review / test-validate / 文档对比生成候选。

---

## 📝 本变更文档补充建议

### 建议 1：design.md 补充"售卖期结束"状态的 UI 处理

- [x] **采纳此建议**

**位置**: `design.md` 附录A「交互流程 → 打开面板」章节 / 同步更新 `design/client.md` 对应章节

**补充内容**:
```markdown
### 售卖期结束状态
- 打开面板时调用 `BusinessActivityModule.IsActivityOpen(activityId)` 判断售卖期是否已结束
- 已结束：购买按钮置灰，文案改为 "UI_MixGrowthFundPage_BtnPurchase_SaleEnded".ToLanguage()（键名待定，需补充到 Language_Keys.md）
- 未购买玩家的投资奖励列仍带锁（LockedByPurchase）；已购买玩家的投资奖励列正常显示
```

**理由**: `test-cases.md` TC-growth-fund-03 明确要求此状态（购买按钮置灰 + "售卖已结束"标签），但 design.md/design/client.md 的"交互流程"和"UI 组件映射"章节从未提及该状态如何呈现。`test-validate-report.md` 判定 TC-03 为 ❌ 未覆盖，`MixGrowthFundPage.cs:129-132` 的实际代码也证实只处理了 `isPurchased` 两种状态，没有处理售卖期结束分支——这是设计文档遗漏在先，代码照着不完整的设计实现的必然结果。

**回写目标**: `changes/growth-fund/design.md` 第 250-255 行附近（附录A「打开面板」流程之后新增小节），同步同步到 `changes/growth-fund/design/client.md` 对应位置

---

### 建议 2：design.md 补充 amType 数据来源说明

- [x] **采纳此建议**

**位置**: `design.md` 附录A「网络协议」章节末尾 / 同步更新 `design/client.md`

**补充内容**:
```markdown
### amType 数据来源（用于条件文案映射）

outArgs 中不包含 amType 字段。客户端 `amType` 应从本地已同步的 `activity_goal` 配置表读取
（`TDActivityGoalTable.GetData(goalId).Type`），`goalId` 通过 `activity_mix_growthfund_reward.xlsx`
的 `RewardId` 与 `activity_goal.xlsx` 交叉关联获得（见"配表依赖"章节）。

`MixGrowthFundRewardTierRow.SetData` 必须接收 amType 参数并传给 `GetConditionText`，
不能硬编码为固定值。
```

**理由**: design.md 只描述了"AM_TYPE → 显示文案"的映射表（Decisions 章节 + design/client.md Q3），但从未说明这个整数本身在客户端如何获取。`test-validate-report.md` Bug-1 指出实际代码 `MixGrowthFundRewardTierRow.cs:21` 把 `amType` 硬编码为 0，其"修复方向"里给出的方案（读取 `activity_goal` 本地配表的 `type` 字段）本应是设计阶段就该确定的数据流，而不是测试验证阶段才补充的猜测。

**回写目标**: `changes/growth-fund/design.md` 第 191 行之后（附录A「网络协议 → 客户端消费范围」段落之后），同步到 `changes/growth-fund/design/client.md` 第 102 行附近

---

### 建议 3：design.md 修正 HasRedPoint 伪代码，补充 activityId 过滤

- [x] **采纳此建议**

**位置**: `design.md` 附录A「红点逻辑 → 触发条件」章节 / 同步更新 `design/client.md`

**补充内容**:
```csharp
bool HasRedPoint(int activityId)
{
    bool isPurchased = m_PurchasedFunds.GetValueOrDefault(activityId);
    foreach (var (key, s) in m_RewardStatuses)
    {
        if ((int)(key >> 32) != activityId) continue;  // ← 多基金并存时必须按 activityId 过滤
        bool goalFinished = s.CurNum >= s.TargetNum;
        if (goalFinished && s.FreeStatus == 0) return true;
        if (isPurchased && goalFinished && s.PaidStatus == 0) return true;
    }
    return false;
}
```

**理由**: design.md 现有伪代码本身遍历 `m_RewardStatuses` 时未按 `activityId` 过滤，这不是实现阶段引入的偏差，而是设计伪代码原样就缺这一步——`test-validate-report.md` Bug-4 指出的问题（TC-20 多基金并存时基金 B 的记录会影响基金 A 的红点判断）是把设计里不完整的伪代码原样抄进了实现。而 proposal 和 TC-20 都明确要求多基金并存场景，设计阶段本该覆盖这个过滤逻辑。

**回写目标**: `changes/growth-fund/design.md` 第 266-282 行（附录A「红点逻辑」章节），同步到 `changes/growth-fund/design/client.md` 第 204-221 行

---

## 🔧 规则沉淀候选（写入 config.yaml）

### 规则 1：客户端状态缓存的派生字段必须标注赋值时机和数据来源

- [x] **采纳此规则**

**适用阶段**: `design-client`

**规则内容**:
```
客户端状态缓存结构体（如 XxxStatus）中，若字段不是直接从 Record/协议原始字段 1:1 映射
（例如需要额外计算、或来自另一个模块的查询结果），设计文档必须在"交互流程"或"数据同步"
章节明确指出该字段在哪个回调/方法中被赋值，不能只在结构体定义处声明字段而不说明写入路径。
```

**严重程度**: 高

**证据来源**:
- test-validate-report.md Bug-2（高）：`MixGrowthFundRewardStatus.CurNum/TargetNum` 在结构体定义中声明，但 `RefreshRewardStatuses` 实际只写入了 FreeStatus/PaidStatus，两个字段从未被赋值，导致红点逻辑恒为 true
- design.md 的"客户端状态缓存"章节定义了 CurNum/TargetNum 字段并注明"来自 ActivityGoalProgress"，但"交互流程"章节没有指出这两个字段具体在哪次协议响应处理时被写入 `m_RewardStatuses`

**回写目标**: `config.yaml` → `rules.design-client` 数组

**预期效果**: 下一次生成 design-client.md 时，AI 会在描述带派生字段的状态缓存结构体时，强制补充"赋值时机"说明，减少"字段声明了但没人写"的漏洞

---

### 规则 2：多活动实例场景下的状态遍历/红点判断必须显式按 activityId 过滤

- [x] **采纳此规则**

**适用阶段**: `design-client`

**规则内容**:
```
若同一个 BusinessActivityType 允许同时存在多个活动实例（activityId 不同），设计文档中涉及
遍历状态缓存字典（如 m_RewardStatuses）的判断逻辑（红点计算、进度汇总等）必须在伪代码中
显式包含 activityId 过滤条件，不能假设"字典里只有当前活动的数据"。
```

**严重程度**: 高

**证据来源**:
- test-validate-report.md Bug-4（中）：`HasRedPoint` 遍历 `m_RewardStatuses` 未过滤 activityId，多基金并存时会互相污染
- proposal 与 test-cases.md TC-20 明确要求"多基金并存"场景，但 design.md 的 HasRedPoint 伪代码本身就没有覆盖这个过滤

**回写目标**: `config.yaml` → `rules.design-client` 数组

**预期效果**: 下一次涉及多实例活动（同类 BusinessActivityType 可配置多个 activityId）的设计，AI 会主动在状态遍历逻辑中加上过滤条件，避免设计阶段就留下跨实例污染的隐患

---

### 规则 3：配置表字段若需客户端强类型访问，属性不能标 S，即使业务语义完全属于服务端

- [ ] **采纳此规则**

**适用阶段**: `design-config`

**规则内容**:
```
判断配置表字段属性（S/C/A）时，若客户端需要通过 DynamicConfigModule 整表同步以强类型对象
形式访问该字段（如 TDXxxTable.GetData().FieldName），属性必须标 A，即使字段的业务语义
100% 属于服务端（如活动ID、充值商品ID等）。S 属性会导致客户端生成的数据类不包含该字段的
强类型成员，只能退化为 extend.GetInt("FieldName") 弱类型访问。
"业务语义归属"和"是否需要强类型代码生成"是两个独立维度，不能用前者替代后者的判断。
```

**严重程度**: 高

**证据来源**:
- tasks.md 第 311 行技术债务记录："design/config.md 的'属性建议 S'结论被实践推翻（S 属性导致字段不生成强类型，已全改为 A）"
- design/config.md 两张表的全部字段最初都标注为 S（Server-only），理由是"字段语义完全属于服务端业务"，但同一段落又要求客户端"以强类型对象形式使用这些值"——这两个要求本身自相矛盾，实施时才发现 S 属性无法满足强类型访问需求

**回写目标**: `config.yaml` → `rules.design-config` 数组

**预期效果**: 下一次设计涉及 DynamicConfigModule 整表同步的配置表时，AI 会先确认客户端访问方式（强类型 vs 弱类型 GetInt），再决定属性标注，避免"业务语义判断"和"代码生成需求判断"混用导致的属性标注错误

---

## 🏗️ Schema 优化建议（写入 schemas/lr-func-dev/）

### 优化 1：design-client-structure.md 补充"派生状态字段赋值时机"设计要求

- [x] **采纳此优化**

**修改文件**: `schemas/lr-func-dev/rules/design/client-structure.md`

**修改位置**: 新增小节，建议放在现有 Record 相关章节（约第 90-100 行 Record 驱动模式说明之后）

**补充内容**:
```markdown
### 派生状态字段的赋值时机（强制）

若客户端状态缓存结构体中的字段不是 Record/协议原始字段的直接映射（如需要跨模块查询、
或由多个来源组合得到），设计文档必须明确指出：
1. 该字段在哪个回调函数中被赋值（如 `ParseQueryInfo`、`OnXxxRecChanged`）
2. 赋值的数据来源（如"来自 ActivityGoalModule.QueryGoalProgress 返回的进度数据"）

**检查方法**：对比"客户端状态缓存"章节声明的字段列表 与 "交互流程"/"协议解析"章节提到的
赋值语句，若某字段只在结构体定义处出现、在流程描述中找不到对应的赋值来源，视为设计缺口，
必须补充说明后才能合并。
```

**理由**: growth-fund 的 `CurNum`/`TargetNum` 字段在设计的结构体定义中声明并注明来源，但流程章节没有说明具体赋值路径，导致实施时遗漏赋值代码（test-validate Bug-2），且 code-review/design 阶段均未发现此缺口。补充此检查项后，reconcile/code-review 可以按"结构体字段 ↔ 流程赋值语句"逐项核对

**预期效果**: 下一次生成 design-client.md 时，涉及派生字段的状态缓存会强制补充赋值时机说明；code-review 阶段可以据此检查实现是否真的写入了每个声明的字段

---

### 优化 2：design-config-structure.md 澄清 S/A 属性标注需同时满足"业务语义"与"客户端访问方式"两个条件

- [ ] **采纳此优化**

**修改文件**: `schemas/lr-func-dev/rules/design/config-structure.md`

**修改位置**: 「属性列说明（强制）」章节（约第 280-299 行），S 属性定义之后

**补充内容**:
```markdown
**⚠️ S 属性与客户端强类型访问的冲突（必读）**：

字段的"业务语义归属服务端"不等于"客户端不需要强类型访问该字段"。若该配置表会通过
`DynamicConfigModule` 整表同步给客户端，且客户端业务代码需要用 `TDXxxTable.GetData().FieldName`
这种强类型方式访问某字段，即使这个字段的业务含义 100% 属于服务端，属性也必须标 **A**，
不能标 S——S 属性会导致生成的数据类不包含该字段的强类型成员，客户端只能退化为
`extend.GetInt("FieldName")` 弱类型访问，与"接入 DynamicConfigModule 整表同步获得强类型对象"
的设计意图相矛盾。

**判断顺序**（比"业务语义判断"优先）：
1. 先确认客户端访问该字段的方式：强类型属性访问 or 完全不读取
2. 若客户端需要强类型访问 → 标 A（无论业务语义归属哪一端）
3. 若客户端完全不读取该字段 → 才按业务语义标 S
```

**理由**: growth-fund 的两张配置表全部字段最初标 S，同段落又要求客户端强类型访问，自相矛盾，实施时才发现问题并全部改为 A（tasks.md 技术债务记录）。现有规则文件的判断依据（第 287-292 行）没有覆盖这种"业务语义是服务端、但客户端要强类型访问"的场景，容易重复踩坑

**预期效果**: 下一次设计涉及 DynamicConfigModule 同步的配置表时，AI 会先判断客户端访问方式再决定属性标注，避免 S/A 标注和实际代码生成需求脱节

---

## 📊 统计

- 本变更文档补充建议：3 项
- 规则沉淀候选（config.yaml）：3 项
- Schema 优化建议：2 项
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
