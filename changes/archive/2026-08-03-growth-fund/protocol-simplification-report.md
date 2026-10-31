# Growth Fund 协议简化实施报告

**实施时间**：2026-07-31  
**方案**：方案 A - 激进简化  
**状态**：✅ 服务器和客户端代码已完成，协议注释需手动更新

---

## 一、已完成的修改

### 1.1 服务器端修改 ✅

**文件**：`D:\se\develop\server\project\FsGame\ActivityModule\BusinessActivity\GrowthFund\MixGrowthFundFunc.cpp`

**修改位置**：第 218-273 行 `MixGrowthFundModule::QueryInfo` 方法

**改动内容**：

```cpp
// 删除了 4 个固定字段：
- outArgs << fundCfg->strDirect;           // 删除
- outArgs << fundCfg->nDisplayType;        // 删除
- outArgs << fundCfg->strPeriodName;       // 删除
- outArgs << fundCfg->strNextPeriodName;   // 删除

// 删除了每档 6 个展示字段：
- outArgs << rewardCfg->strFreeReward;     // 删除
- outArgs << rewardCfg->strFreeHighlight;  // 删除
- outArgs << rewardCfg->strPayReward;      // 删除
- outArgs << rewardCfg->strPayHighlight;   // 删除
- outArgs << entryCfg->strLanguage;        // 删除
- outArgs << entryCfg->strUrl;             // 删除

// 删除了 entryCfg 的获取（不再需要）：
- const STActivityGoalEntry *entryCfg = g_pActivityGoalModule->GetGoalEntryConfig(...);

// 保留的 3 个必要字段：
+ outArgs << fundCfg->nRechargeId;         // 充值ID
+ outArgs << rewardCfg->nRewardID;         // 奖励ID（用于查表）
+ outArgs << progress.GetCurNum(nEntryID); // 当前进度
+ outArgs << progress.GetTargetNum(nEntryID); // 目标进度
```

**网络传输减少**：
- 原：5 + N×9 字段
- 现：1 + N×3 字段
- 假设 10 档：95 字段 → 31 字段（**减少 67%**）

---

### 1.2 客户端修改 ✅

**文件**：`D:\se\develop\client\project\Assets\Script\UISript\WelfareActivityPanel\MixGrowthFundPanel\MixGrowthFundPage.cs`

**修改位置**：第 85-112 行 `ParseQueryInfo` 方法

**改动内容**：

```csharp
// 删除了 4 个固定字段的跳过逻辑：
- index++; // Direct
- index++; // DisplayType
- index++; // Name
- index++; // NextActiveName

// 修改 fieldsPerTier 从 9 改为 3：
- const int fieldsPerTier = 9;
+ const int fieldsPerTier = 3;

// 删除了 6 个字段的跳过逻辑：
- index += 5; // FreeReward, FreeHighlight, PayReward, PayHighlight, LanguagePack
- index += 1; // Url

// 简化后的解析逻辑（直接读取 3 个字段）：
int rewardId = outArgs.GetInt32(index++);
long curNum = outArgs.GetInt64(index++);
long targetNum = outArgs.GetInt64(index++);
```

**添加注释**：
```csharp
// 协议简化：每档只发送 3 个字段（RewardId, CurNum, TargetNum）
// 展示数据从配置表 TDActivityMixGrowthfundRewardTable 读取
```

---

### 1.3 协议注释更新 ⚠️ 需手动操作

**文件**：`D:\se\develop\server\project\define\ServerCustomDefine.h`

**位置**：第 1425-1440 行 `SERVER_CUSTOMMSG_BACTIVITY_INFO (470)` 注释

**原因**：文件编码问题导致自动编辑失败，需手动添加以下注释：

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
//   [MixGrowthFund] 成长基金特殊信息：
//     int RechargeId - 充值ID
//     循环每档：int RewardId, int64 CurNum, int64 TargetNum
//     （静态配置已通过 DynamicConfigModule 同步：active_fund_main, activity_mix_growthfund_reward）
SERVER_CUSTOMMSG_BACTIVITY_INFO   = 470,
```

---

## 二、TDActiveFundMainTable 使用情况排查 ✅

### 2.1 调查结果

**文件引用情况**：
1. `TDActiveFundMainTableExtend.cs` - 表扩展代码（生成代码）
2. `TDActiveFundMainTable.cs` - 表生成代码（生成代码）
3. `DynamicConfigModule_Process.cs` - 配置同步注册

**业务代码使用情况**：**完全未使用** ❌

```csharp
// DynamicConfigModule_Process.cs:41 - 唯一的注册点
RegisterTable(TDActiveFundMainTable.metaData.tableName, 
    typeof(TDActiveFundMainTable), 
    TDActiveFundMainTable.InsertDynamicData, 
    TDActiveFundMainTable.ParseComplete, 
    TDActiveFundMainTable.ClearDynamicData);
```

**查询结果**：
- ✅ 配置表通过 `DynamicConfigModule` 正常同步
- ❌ 业务代码中无任何读取操作
- ❌ `TDActiveFundMainTable.GetData()` 从未被调用
- ❌ `TDActiveFundMain.rechargeId` 等字段从未被访问

### 2.2 为什么未使用？

**原因**：客户端直接从**协议 470** 获取 `RechargeId`（第 90 行）：

```csharp
m_RechargeId = outArgs.GetInt32(index++);  // 从协议读取
```

**而不是从配置表**：
```csharp
// 从未出现过的代码：
var fundCfg = TDActiveFundMainTable.GetData(m_CurrentActivityId);
m_RechargeId = fundCfg.rechargeId;
```

### 2.3 影响分析

1. **配置表完全冗余**：`TDActiveFundMainTable` 虽然同步了，但从未被使用
2. **数据双重传输**：RechargeId 既通过配置表同步，又通过协议 470 下发
3. **本次简化后**：协议仍下发 RechargeId（确保一致性），但删除了其他 4 个未使用字段

### 2.4 未来优化建议

**可选优化**（需评估风险）：

1. **删除配置表同步**：
   ```csharp
   // DynamicConfigModule_Process.cs
   - RegisterTable(TDActiveFundMainTable.metaData.tableName, ...);  // 删除注册
   ```

2. **删除配置表生成代码**：
   - 移除 `TDActiveFundMain.cs`
   - 移除 `TDActiveFundMainTable.cs`
   - 移除 `TDActiveFundMainTableExtend.cs`

3. **服务器端删除配置表定义**（如果其他模块也未使用）

**不建议删除的原因**：
- RechargeId 需要从协议获取（确保与服务器当前活动一致）
- 其他字段（Direct、DisplayType、Name、NextActiveName）虽然未使用，但可能为未来功能预留
- 配置表同步机制已经存在，删除需要确认无其他隐藏依赖

---

## 三、优化效果

### 3.1 网络传输优化

假设 10 档奖励的活动：

| 项目 | 修改前 | 修改后 | 优化 |
|------|--------|--------|------|
| 固定字段 | 5 个 (68 bytes) | 1 个 (4 bytes) | -64 bytes |
| 每档字段 | 9 个 (~240 bytes/档) | 3 个 (20 bytes/档) | -220 bytes/档 |
| **总传输量** | **~2,468 bytes** | **~204 bytes** | **-91.7%** |

### 3.2 代码简洁性

**客户端解析代码**：
- 修改前：27 行（包含 7 个 `index++` 跳过逻辑）
- 修改后：23 行（直接读取 3 个字段）
- 减少：**4 行无用代码**

**服务器发送代码**：
- 修改前：55 行（包含 10 个字段的发送逻辑）
- 修改后：41 行（只发送 3 个字段）
- 减少：**14 行冗余代码**

### 3.3 维护性提升

- ✅ 协议更简洁，易于理解
- ✅ 避免协议与配置表数据不一致的风险
- ✅ 减少字段同步维护成本
- ✅ 符合「静态数据用配置表、动态数据用协议」的架构原则

---

## 四、兼容性与风险

### 4.1 兼容性分析

**新客户端 + 旧服务器**：
- ❌ 不兼容：新客户端期待 3 字段/档，旧服务器发送 9 字段/档
- 结果：解析错误，读取到错误的字段位置

**旧客户端 + 新服务器**：
- ❌ 不兼容：旧客户端期待 9 字段/档，新服务器发送 3 字段/档
- 结果：解析错误，越界或读取到错误的字段

**结论**：**需要灰度发布策略**

### 4.2 灰度发布建议

**阶段 1：客户端先发版（1 周）**
- 发布新客户端（本次修改）
- 确保新客户端在线率 > 95%

**阶段 2：服务器灰度（1 周）**
- 服务器发布新版本（本次修改）
- 通过灰度开关控制新协议比例（0% → 50% → 100%）
- 监控指标：
  - 客户端解析错误率
  - 奖励领取成功率
  - 购买成功率

**阶段 3：全量切换**
- 新协议 100% 生效
- 监控稳定 3 天后，移除旧代码

### 4.3 风险缓解措施

1. **配置表同步保障**：
   - `DynamicConfigModule` 在活动开启时自动同步配置表
   - OpenSpec 工作流强制三端配置一致

2. **监控告警**：
   - 客户端添加协议解析错误日志
   - 服务器监控 QueryInfo 调用次数和耗时
   - 监控奖励领取失败率

3. **回滚预案**：
   - 保留旧版本代码分支
   - 准备服务器热更新回滚方案
   - 客户端紧急热更新预案

---

## 五、后续工作清单

### 5.1 立即执行

- [x] 修改服务器 `MixGrowthFundFunc.cpp:QueryInfo`
- [x] 修改客户端 `MixGrowthFundPage.cs:ParseQueryInfo`
- [ ] **手动更新协议注释** `ServerCustomDefine.h:1439`（编码问题导致自动编辑失败）
- [ ] 同步更新客户端协议注释 `ServerCustomID.cs`

### 5.2 测试验证

- [ ] 服务器编译验证
- [ ] 客户端编译验证
- [ ] 单元测试：10 档奖励的协议序列化/反序列化
- [ ] 集成测试：购买基金、领取奖励、进度刷新

### 5.3 灰度发布

- [ ] Week 1: 发布新客户端，监控解析错误率
- [ ] Week 2: 服务器灰度 50%，监控领取成功率
- [ ] Week 3: 服务器灰度 100%，监控稳定性

### 5.4 文档更新

- [ ] 更新技术文档：协议 470 的 MixGrowthFund 部分
- [ ] 更新 OpenSpec 规范：静态数据与动态数据的边界
- [ ] 记录本次优化的经验教训

---

## 六、相关文档

1. `changes/growth-fund/protocol-alignment-analysis.md` - 初步协议对齐分析
2. `changes/growth-fund/protocol-redundancy-analysis.md` - 基于配置表的冗余分析
3. `changes/growth-fund/implementation-report.md` - 实施报告

---

**修改人员**：AI Code Assistant  
**审核状态**：待人工审核  
**预计上线时间**：3 周后（灰度发布完成）
