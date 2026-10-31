# Growth Fund 协议对齐分析报告

## 一、协议概览

### 服务器端协议定义 (ServerCustomDefine.h:1425-1440)

```cpp
// brief 运营活动数据
// param int msg id
// param int id
// param int state
// param int64 beginTime
// param int64 endTime
// param int curTurn
// param int curDay
// param int type
// param int eachTurnDays
// param int uiType
// param int showTime-展示时间(以结束时间往前的一个时间段，这段时间活动仅展示，不记录数据)
// param int taskId
// param int 赛季id
// param varlist 各类活动的特殊信息 ()
SERVER_CUSTOMMSG_BACTIVITY_INFO = 470,
```

### 客户端协议定义 (BAActivityInfoIndex)

```csharp
public enum BAActivityInfoIndex
{
    ActivityID = 0,      // id
    ActivityState,       // state
    BeginTime,           // beginTime
    EndTime,             // endTime
    CurTurn,             // curTurn
    CurDay,              // curDay
    ActivityType,        // type
    EachTurnDays,        // eachTurnDays
    UIType,              // uiType
    ShowTime,            // showTime
    TaskId,              // taskId
    SeasonId,            // 赛季id
    CustomStart,         // 自定义数据起始位置（varlist 特殊信息开始）
}
```

**✅ 结论：前后端基础协议完全对齐**，13 个参数一一对应。

---

## 二、Growth Fund 自定义数据分析

### 服务器端 QueryInfo 实现 (MixGrowthFundFunc.cpp:218-273)

```cpp
void MixGrowthFundModule::QueryInfo(IKernel *pKernel, const PERSISTID &player, 
                                     int nActivityID, IVarList &outArgs)
{
    outArgs << fundCfg->nRechargeId;        // [0] 充值ID
    outArgs << fundCfg->strDirect;          // [1] Direct
    outArgs << fundCfg->nDisplayType;       // [2] DisplayType
    outArgs << fundCfg->strPeriodName;      // [3] Name
    outArgs << fundCfg->strNextPeriodName;  // [4] NextActiveName

    // 循环添加每个档位的奖励信息（每档 9 个字段）
    for (size_t i = 0; i < goalCfg->entries.size(); ++i)
    {
        outArgs << rewardCfg->nRewardID;         // [+0] RewardID
        outArgs << rewardCfg->strFreeReward;     // [+1] FreeReward
        outArgs << rewardCfg->strFreeHighlight;  // [+2] FreeHighlight
        outArgs << rewardCfg->strPayReward;      // [+3] PayReward
        outArgs << rewardCfg->strPayHighlight;   // [+4] PayHighlight
        outArgs << entryCfg->strLanguage;        // [+5] LanguagePack
        outArgs << entryCfg->strUrl;             // [+6] Url
        outArgs << progress.GetCurNum(nEntryID); // [+7] CurNum (int64)
        outArgs << progress.GetTargetNum(nEntryID); // [+8] TargetNum (int64)
    }
}
```

### 客户端 ParseQueryInfo 实现 (MixGrowthFundPage.cs:85-112)

```csharp
void ParseQueryInfo(IVarList outArgs)
{
    int index = 0;
    m_RechargeId = outArgs.GetInt32(index++);  // [0] RechargeId ✅
    index++;  // [1] Direct - 已通过本地配表读取，跳过 ⚠️
    index++;  // [2] DisplayType - 跳过 ⚠️
    index++;  // [3] Name - 跳过 ⚠️
    index++;  // [4] NextActiveName - 跳过 ⚠️

    const int fieldsPerTier = 9;
    while (index + fieldsPerTier <= outArgs.count)
    {
        int rewardId = outArgs.GetInt32(index);     // [+0] RewardID ✅
        index += 5; // [+1~+5] FreeReward, FreeHighlight, PayReward, PayHighlight, LanguagePack - 跳过 ⚠️
        index += 1; // [+6] Url - 跳过 ⚠️
        long curNum = outArgs.GetInt64(index++);    // [+7] CurNum ✅
        long targetNum = outArgs.GetInt64(index++); // [+8] TargetNum ✅
        
        // 仅缓存 3 个字段用于 UI 显示
        m_TierDataCache.Add(new MixGrowthFundTierData
        {
            RewardId = rewardId,
            CurNum = curNum,
            TargetNum = targetNum,
        });
    }
}
```

**✅ 结论：前后端自定义数据协议对齐**，但客户端只使用了部分字段。

---

## 三、冗余参数分析

### 3.1 基础协议层（13 个参数）

这 13 个参数是 BusinessActivity 框架的**通用协议**，适用于所有运营活动类型（签到、答题、成长基金等），**不建议简化**：

- **curTurn / curDay / eachTurnDays**：多期活动需要（如赛季任务、周循环活动）
- **showTime**：预告期显示需要（活动结束前 N 天仅展示不可操作）
- **taskId / seasonId**：关联任务系统、赛季系统需要

**成长基金虽然不需要这些字段，但删除会破坏框架通用性**。

---

### 3.2 自定义数据层（Growth Fund 特有）

#### ❌ 明确冗余的字段（客户端完全不使用）

| 字段索引 | 字段名 | 服务器发送内容 | 客户端使用情况 | 建议 |
|---------|--------|---------------|--------------|------|
| [1] | `strDirect` | 策划配置的字符串 | **跳过，改用本地配表** | **可删除** |
| [2] | `nDisplayType` | 显示类型枚举 | **跳过** | **可删除** |
| [3] | `strPeriodName` | 期数名称 | **跳过** | **可删除** |
| [4] | `strNextPeriodName` | 下期名称 | **跳过** | **可删除** |

#### ⚠️ 每档奖励的冗余字段（客户端跳过但配表依赖）

| 字段索引 | 字段名 | 服务器发送内容 | 客户端使用情况 | 建议 |
|---------|--------|---------------|--------------|------|
| [+1] | `strFreeReward` | 免费奖励字符串 | **跳过，改用配表** | **可删除** ✅ |
| [+2] | `strFreeHighlight` | 免费奖励高亮 | **跳过，改用配表** | **可删除** ✅ |
| [+3] | `strPayReward` | 付费奖励字符串 | **跳过，改用配表** | **可删除** ✅ |
| [+4] | `strPayHighlight` | 付费奖励高亮 | **跳过，改用配表** | **可删除** ✅ |
| [+5] | `strLanguage` | 语言包 key | **跳过，改用配表** | **可删除** ✅ |
| [+6] | `strUrl` | 图片 URL | **跳过，改用配表** | **可删除** ✅ |

---

## 四、简化方案

### 方案 A：激进简化（推荐）

#### 简化后协议

```cpp
void MixGrowthFundModule::QueryInfo(IKernel *pKernel, const PERSISTID &player, 
                                     int nActivityID, IVarList &outArgs)
{
    outArgs << fundCfg->nRechargeId;  // [0] 充值ID（必需，客户端用于支付跳转）

    // 每档奖励只发送 3 个字段
    for (size_t i = 0; i < goalCfg->entries.size(); ++i)
    {
        outArgs << rewardCfg->nRewardID;              // [+0] RewardID
        outArgs << progress.GetCurNum(nEntryID);      // [+1] CurNum (int64)
        outArgs << progress.GetTargetNum(nEntryID);   // [+2] TargetNum (int64)
    }
}
```

#### 客户端改动

```csharp
void ParseQueryInfo(IVarList outArgs)
{
    int index = 0;
    m_RechargeId = outArgs.GetInt32(index++);  // [0]

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

#### 效果

- **减少网络传输**：原 1 + N×9 字段 → 简化为 1 + N×3 字段
- **假设 10 档奖励**：91 字段 → 31 字段（**减少 66%**）
- **避免数据不一致**：所有展示数据从本地配表读取，策划修改配置后无需服务器更新

---

### 方案 B：保守简化

仅删除前 4 个明确未使用的字段（Direct、DisplayType、PeriodName、NextPeriodName），保留每档的 6 个展示字段（为未来功能预留）。

#### 简化效果

- 原 5 + N×9 字段 → 简化为 1 + N×9 字段（仅减少 4 个固定字段）
- **减少幅度较小**，但**兼容性更好**

---

## 五、风险评估

### 方案 A 风险

1. **配表同步风险**：如果服务器配置与客户端配表不一致（例如热更新服务器配置但客户端未更新），会导致：
   - 奖励展示错误（从配表读取的 RewardID 在服务器可能不存在）
   - 进度条显示正常但点击领取失败

   **缓解措施**：
   - 使用 OpenSpec 强制三端配置同步（已有机制）
   - 服务器端在 QueryInfo 时校验 RewardID 是否在配表中存在

2. **已上线版本兼容性**：如果该功能已上线，需要：
   - 评估旧客户端是否会因协议字段数量不匹配而崩溃
   - 考虑分批灰度发布或保留兼容代码

### 方案 B 风险

- **几乎无风险**，仅删除客户端完全不读取的前 4 个字段
- 旧客户端通过 `index++` 跳过这些字段，协议向后兼容

---

## 六、推荐行动

### 立即执行（安全）

1. **删除前 4 个冗余字段**（Direct、DisplayType、PeriodName、NextPeriodName）
   - 修改：`MixGrowthFundFunc.cpp:227-231`
   - 修改：`MixGrowthFundPage.cs:91-94`（删除 3 个 `index++`）

2. **更新协议注释**
   ```cpp
   // param int 充值ID
   // param varlist 档位数据 (int rewardId, string freeReward, ...)
   ```

### 技术评审后执行（需评估）

如果团队同意「配表优先于协议传输」的架构原则：

1. **删除每档的 6 个展示字段**（FreeReward 到 Url）
2. **测试覆盖**：
   - 服务器配置与客户端配表不一致的场景
   - 多档位奖励的领取流程
   - 购买基金后的付费档位解锁

3. **灰度发布**：
   - 先发布新客户端（兼容旧协议）
   - 再更新服务器协议（新客户端已就位）

---

## 七、补充建议

### 架构层面

当前设计存在**「配表 + 协议双重传输」**的冗余模式：

- **奖励内容**（FreeReward、PayReward）→ 客户端从配表读取
- **奖励进度**（CurNum、TargetNum）→ 从协议读取（正确）
- **展示配置**（Highlight、LanguagePack、Url）→ 客户端从配表读取

**建议**：制定明确的「配表 vs 协议」边界规范：
- **静态数据**（奖励内容、UI 配置）→ 仅存在于配表
- **动态数据**（进度、状态、时间）→ 仅通过协议传输
- **避免重复传输**：协议只发送配表中的 key（如 RewardID），由客户端自行查表

### 验证建议

如果决定简化，建议在 `implementation-report.md` 补充：
- [ ] 服务器修改 `MixGrowthFundFunc.cpp:QueryInfo`
- [ ] 客户端修改 `MixGrowthFundPage.cs:ParseQueryInfo`
- [ ] 更新协议文档注释
- [ ] 添加单元测试（10 档奖励的协议序列化/反序列化）
- [ ] 灰度测试（观察领取成功率、错误日志）

---

**生成时间**：2026-07-31  
**分析范围**：growth-fund 功能的 SERVER_CUSTOMMSG_BACTIVITY_INFO (470) 协议
