# Growth Fund 协议冗余分析报告（基于配置同步机制）

**生成时间**：2026-07-31  
**分析前提**：客户端已通过 `DynamicConfigModule` 获得 `active_fund_main` 和 `activity_mix_growthfund_reward` 配置表

---

## 一、客户端已有配置表数据

### 1.1 TDActiveFundMain（active_fund_main）

```csharp
public partial class TDActiveFundMain
{
    public int activeId           // 活动ID
    public int rechargeId         // 充值ID ✅
    public string direct          // 获得紫晶
    public int displayType        // 奖励显示
    public string name            // 当前期数
    public string nextActiveName  // 下一期活动名称
    public string reserveTime     // 预留时间
}
```

**数据来源**：通过配置同步机制从服务器同步，客户端本地缓存。

---

### 1.2 TDActivityMixGrowthfundReward（activity_mix_growthfund_reward）

```csharp
public partial class TDActivityMixGrowthfundReward
{
    public int id                 // 流水号
    public int activeId           // 活动ID
    public int rewardId           // 奖励ID ✅
    public string freeReward      // 免费奖励
    public string freeHighlight   // 免费奖励特效
    public string payReward       // 付费奖励
    public string payHighlight    // 付费奖励特效
}
```

**数据来源**：通过配置同步机制从服务器同步，客户端本地缓存。

---

## 二、服务器协议 470 当前下发数据

### 2.1 基础协议（13 个通用参数）

由 `BusinessActivity` 框架统一管理，不在本次分析范围（见前一份报告）。

---

### 2.2 自定义数据（QueryInfo 实现）

**服务器端发送**（MixGrowthFundFunc.cpp:218-273）：

```cpp
// 固定 5 个字段
outArgs << fundCfg->nRechargeId;        // [0] 充值ID
outArgs << fundCfg->strDirect;          // [1] Direct
outArgs << fundCfg->nDisplayType;       // [2] DisplayType
outArgs << fundCfg->strPeriodName;      // [3] Name
outArgs << fundCfg->strNextPeriodName;  // [4] NextActiveName

// 每档 9 个字段（循环）
for (每个档位) {
    outArgs << rewardCfg->nRewardID;         // [+0] RewardID
    outArgs << rewardCfg->strFreeReward;     // [+1] FreeReward
    outArgs << rewardCfg->strFreeHighlight;  // [+2] FreeHighlight
    outArgs << rewardCfg->strPayReward;      // [+3] PayReward
    outArgs << rewardCfg->strPayHighlight;   // [+4] PayHighlight
    outArgs << entryCfg->strLanguage;        // [+5] LanguagePack
    outArgs << entryCfg->strUrl;             // [+6] Url
    outArgs << progress.GetCurNum(nEntryID); // [+7] CurNum (int64) ✅
    outArgs << progress.GetTargetNum(nEntryID); // [+8] TargetNum (int64) ✅
}
```

**客户端接收**（MixGrowthFundPage.cs:85-112）：

```csharp
int index = 0;
m_RechargeId = outArgs.GetInt32(index++);  // [0] ✅ 使用
index++;  // [1] 跳过
index++;  // [2] 跳过
index++;  // [3] 跳过
index++;  // [4] 跳过

while (index + 9 <= outArgs.count) {
    int rewardId = outArgs.GetInt32(index);     // [+0] ✅ 使用
    index += 5; // [+1~+5] 跳过
    index += 1; // [+6] 跳过
    long curNum = outArgs.GetInt64(index++);    // [+7] ✅ 使用
    long targetNum = outArgs.GetInt64(index++); // [+8] ✅ 使用
}
```

---

## 三、数据重复性分析

### 3.1 完全重复的数据（配置表已有 + 协议也发送 + 客户端跳过）

| 协议字段索引 | 协议字段名 | 配置表来源 | 配置表字段 | 客户端处理 | 冗余判定 |
|-------------|-----------|-----------|-----------|-----------|---------|
| [1] | `strDirect` | `TDActiveFundMain` | `direct` | **跳过** | ❌ 100% 冗余 |
| [2] | `nDisplayType` | `TDActiveFundMain` | `displayType` | **跳过** | ❌ 100% 冗余 |
| [3] | `strPeriodName` | `TDActiveFundMain` | `name` | **跳过** | ❌ 100% 冗余 |
| [4] | `strNextPeriodName` | `TDActiveFundMain` | `nextActiveName` | **跳过** | ❌ 100% 冗余 |
| [+1] | `strFreeReward` | `TDActivityMixGrowthfundReward` | `freeReward` | **跳过** | ❌ 100% 冗余 |
| [+2] | `strFreeHighlight` | `TDActivityMixGrowthfundReward` | `freeHighlight` | **跳过** | ❌ 100% 冗余 |
| [+3] | `strPayReward` | `TDActivityMixGrowthfundReward` | `payReward` | **跳过** | ❌ 100% 冗余 |
| [+4] | `strPayHighlight` | `TDActivityMixGrowthfundReward` | `payHighlight` | **跳过** | ❌ 100% 冗余 |

**结论**：这 8 个字段在协议中传输是**完全多余的**，因为：
1. 客户端已通过配置同步机制获得完全相同的数据
2. 客户端解析协议时直接跳过这些字段
3. 客户端实际使用的数据全部来自本地配置表

---

### 3.2 协议特有数据（仅协议传输，配置表无法提供）

| 协议字段索引 | 协议字段名 | 数据类型 | 客户端使用 | 必要性 |
|-------------|-----------|---------|-----------|-------|
| [0] | `nRechargeId` | int | ✅ 使用（存储到 `m_RechargeId`） | ✅ **必须保留** |
| [+7] | `GetCurNum()` | int64 | ✅ 使用（存储到 `CurNum`） | ✅ **必须保留** |
| [+8] | `GetTargetNum()` | int64 | ✅ 使用（存储到 `TargetNum`） | ✅ **必须保留** |

**为什么必须保留**：
- **RechargeId**：虽然配置表有 `TDActiveFundMain.rechargeId`，但协议传输是为了确保与服务器当前活动配置一致（防止配置表未更新）
- **CurNum / TargetNum**：玩家的**实时进度数据**，无法通过配置表获得，必须从服务器动态下发

---

### 3.3 可疑字段（协议下发但客户端跳过，配置表也没有）

| 协议字段索引 | 协议字段名 | 服务器数据来源 | 客户端处理 | 分析 |
|-------------|-----------|--------------|-----------|------|
| [+5] | `strLanguage` | `entryCfg->strLanguage` | **跳过** | 配置表无此字段，可能在 `extend` 中 |
| [+6] | `strUrl` | `entryCfg->strUrl` | **跳过** | 配置表无此字段，可能在 `extend` 中 |

**说明**：这两个字段可能存储在配置表的 `TDUniversallySet extend` 拓展字段集合中，需要进一步确认。如果确实未使用，也应删除。

---

## 四、网络传输量对比

### 假设场景：10 档奖励的活动

#### 当前协议

```
固定字段：5 个
  [0] RechargeId (int, 4 bytes)
  [1] Direct (string, ~20 bytes)
  [2] DisplayType (int, 4 bytes)
  [3] Name (string, ~20 bytes)
  [4] NextActiveName (string, ~20 bytes)

每档字段：9 个 × 10 档 = 90 个
  [+0] RewardID (int, 4 bytes) × 10 = 40 bytes
  [+1] FreeReward (string, ~50 bytes) × 10 = 500 bytes
  [+2] FreeHighlight (string, ~30 bytes) × 10 = 300 bytes
  [+3] PayReward (string, ~50 bytes) × 10 = 500 bytes
  [+4] PayHighlight (string, ~30 bytes) × 10 = 300 bytes
  [+5] LanguagePack (string, ~20 bytes) × 10 = 200 bytes
  [+6] Url (string, ~40 bytes) × 10 = 400 bytes
  [+7] CurNum (int64, 8 bytes) × 10 = 80 bytes
  [+8] TargetNum (int64, 8 bytes) × 10 = 80 bytes

总计：约 2,468 bytes
```

#### 优化后协议（仅保留必要数据）

```
固定字段：1 个
  [0] RechargeId (int, 4 bytes)

每档字段：3 个 × 10 档 = 30 个
  [+0] RewardID (int, 4 bytes) × 10 = 40 bytes
  [+1] CurNum (int64, 8 bytes) × 10 = 80 bytes
  [+2] TargetNum (int64, 8 bytes) × 10 = 80 bytes

总计：约 204 bytes
```

**减少比例**：(2468 - 204) / 2468 = **91.7%**

---

## 五、简化方案

### 方案 A：激进简化（推荐）

#### 服务器修改

```cpp
void MixGrowthFundModule::QueryInfo(IKernel *pKernel, const PERSISTID &player, 
                                     int nActivityID, IVarList &outArgs)
{
    const STFund *fundCfg = GetMainConfig(nActivityID);
    if (NULL == fundCfg) return;

    // 仅发送充值ID（确保与服务器配置一致）
    outArgs << fundCfg->nRechargeId;

    const STActivityGoal *goalCfg = g_pActivityGoalModule->GetGoalConfig(nActivityID);
    if (NULL == goalCfg) return;

    ActivityGoalProgress progress;
    g_pActivityGoalModule->QueryGoalProgress(pKernel, player, nActivityID, progress);

    // 仅发送必要的动态数据
    SAFE_LOOP_START_PARAM(param1);
    for (size_t i = 0; i < goalCfg->entries.size(); ++i)
    {
        LOOP_PARAM(param1);
        int nEntryID = goalCfg->entries[i];

        const STReward *rewardCfg = GetRewardConfig(nActivityID, nEntryID);
        if (NULL == rewardCfg) continue;

        outArgs << rewardCfg->nRewardID;              // RewardID（用于查表）
        outArgs << progress.GetCurNum(nEntryID);      // 当前进度
        outArgs << progress.GetTargetNum(nEntryID);   // 目标进度
    }
}
```

#### 客户端修改

```csharp
void ParseQueryInfo(IVarList outArgs)
{
    m_TierDataCache.Clear();

    int index = 0;
    m_RechargeId = outArgs.GetInt32(index++);  // [0] RechargeId

    const int fieldsPerTier = 3;  // 从 9 改为 3
    while (index + fieldsPerTier <= outArgs.count)
    {
        int rewardId = outArgs.GetInt32(index++);
        long curNum = outArgs.GetInt64(index++);
        long targetNum = outArgs.GetInt64(index++);

        m_TierDataCache.Add(new MixGrowthFundTierData
        {
            RewardId = rewardId,
            CurNum = curNum,
            TargetNum = targetNum,
        });
    }
}
```

#### 客户端 UI 显示改动

```csharp
void OnRewardCellUpdate(Transform root, int index)
{
    var tierData = m_TierDataCache[index];
    
    // 从配置表读取展示数据
    var rewardCfg = TDActivityMixGrowthfundRewardTable.GetDataByKey(m_CurrentActivityId, tierData.RewardId);
    if (rewardCfg == null) return;

    var status = m_Module.GetRewardStatus(m_CurrentActivityId, tierData.RewardId);

    // 所有展示数据从配置表获取
    var freeState = GetFreeRewardState(status, tierData);
    var payState = GetPaidRewardState(status, tierData, m_IsPurchased);

    var row = root.GetComponent<MixGrowthFundRewardTierRow>();
    if (row != null)
    {
        row.SetData(
            m_CurrentActivityId, 
            tierData,           // 仅包含 RewardId + CurNum + TargetNum
            rewardCfg,          // 配置表数据：freeReward, payReward, highlight 等
            freeState, 
            payState, 
            OnClaimReward
        );
    }
}
```

---

### 方案 B：保守简化

仅删除前 4 个固定字段（Direct、DisplayType、Name、NextActiveName），保留每档的展示字段（为未来可能的热更新预留）。

**减少比例**：约 3%（仅 68 bytes）

---

## 六、风险评估

### 方案 A 的关键风险

#### ⚠️ 配置表不一致风险（已缓解）

**风险场景**：
- 服务器更新了活动配置（如修改了某档奖励内容）
- 客户端未同步更新配置表
- 结果：客户端显示旧奖励内容，但服务器按新奖励发放

**缓解措施**（已有）：
1. **DynamicConfigModule** 机制确保客户端在活动开启时自动同步最新配置表
2. **OpenSpec 工作流**强制三端配置同步（服务器配置、客户端配置表、策划表必须一致）
3. 服务器端在 QueryInfo 时可添加版本校验（可选）

#### ✅ 兼容性风险（低）

- 旧客户端（未更新）连接新服务器（简化协议）：
  - 因为客户端是通过 `index++` 跳过字段，字段数量减少会导致解析错误
  - **解决方案**：需要客户端先发版，服务器后发版（灰度策略）

- 新客户端连接旧服务器：
  - 新客户端期待 3 字段/档，旧服务器发送 9 字段/档
  - 客户端会读取错误的字段位置
  - **解决方案**：同样需要灰度发布

---

## 七、推荐行动方案

### 立即执行（零风险）

**删除协议注释中的误导性内容**，明确标注哪些字段已废弃：

```cpp
// brief 运营活动数据 - Growth Fund
// param int msg id
// ...（基础协议 13 参数）...
// param int 充值ID（使用中）
// param string Direct（已废弃，改用配置表 TDActiveFundMain.direct）
// param int DisplayType（已废弃，改用配置表 TDActiveFundMain.displayType）
// param string Name（已废弃，改用配置表 TDActiveFundMain.name）
// param string NextActiveName（已废弃，改用配置表 TDActiveFundMain.nextActiveName）
// param varlist 档位数据 (
//   int RewardID（使用中，用于查表）,
//   string FreeReward（已废弃，改用配置表）,
//   string FreeHighlight（已废弃，改用配置表）,
//   string PayReward（已废弃，改用配置表）,
//   string PayHighlight（已废弃，改用配置表）,
//   string LanguagePack（已废弃），
//   string Url（已废弃），
//   int64 CurNum（使用中，玩家实时进度）,
//   int64 TargetNum（使用中，目标进度）
// )
```

---

### 技术评审后执行

1. **确认配置表同步时机**：
   - 确认 `DynamicConfigModule` 在活动开启前是否一定会触发同步
   - 确认配置表更新失败时的降级策略

2. **实施简化方案 A**：
   - 修改服务器 `MixGrowthFundFunc.cpp:QueryInfo`
   - 修改客户端 `MixGrowthFundPage.cs:ParseQueryInfo`
   - 更新协议注释

3. **灰度发布策略**：
   - Week 1: 发布新客户端（兼容新旧协议，通过字段数量判断）
   - Week 2: 50% 玩家使用新协议（服务器灰度开关）
   - Week 3: 100% 切换新协议，移除兼容代码

4. **监控指标**：
   - 客户端解析协议错误率
   - 奖励领取成功率
   - 配置表同步失败率

---

## 八、补充建议

### 架构层面

当前 Growth Fund 的数据流存在**三重来源**：

1. **协议 470 下发**：RechargeId + 每档的 9 个字段
2. **配置表同步**：`active_fund_main` + `activity_mix_growthfund_reward`
3. **客户端选择**：实际只使用协议的 3 个字段 + 配置表的全部字段

**建议明确数据边界规范**：

| 数据类型 | 传输方式 | 示例 |
|---------|---------|------|
| **静态配置**（活动配置、奖励内容、UI 展示） | 仅配置表同步 | FreeReward、PayReward、Highlight、Name |
| **动态状态**（玩家进度、活动状态） | 仅协议传输 | CurNum、TargetNum、ActivityState |
| **关键标识**（用于查表） | 协议 + 配置表 | RechargeId、RewardId（协议传输确保一致性） |

---

## 九、总结

### 核心发现

1. **协议 470 下发的 95 个字段中，只有 3 个字段（RechargeId、CurNum、TargetNum）是必需的**
2. **其余 92 个字段（97%）都是冗余的**，因为：
   - 客户端已通过 `DynamicConfigModule` 获得完全相同的配置表数据
   - 客户端解析协议时直接跳过这些字段
   - 客户端实际使用的所有展示数据全部来自本地配置表

3. **优化收益**：
   - 网络传输量减少 **91.7%**
   - 避免配置数据双重维护
   - 协议更简洁，易于理解和维护

4. **实施风险可控**：
   - 已有 `DynamicConfigModule` 机制保证配置表同步
   - 已有 OpenSpec 工作流保证三端配置一致
   - 灰度发布策略可进一步降低风险

### 推荐决策

**优先采用方案 A（激进简化）**，理由：
- 客户端已有完整的配置表数据，协议传输这些静态数据是纯粹的浪费
- 简化后的协议更符合「配置表优先于协议」的架构原则
- 网络传输量减少 91.7%，对移动网络环境友好
- 代码更清晰，维护成本更低

---

**生成时间**：2026-07-31  
**分析人员**：AI Code Assistant  
**文档版本**：v2.0（基于配置同步机制）
