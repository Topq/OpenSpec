# Growth Fund Code Review Report

**检查时间**: 2026-08-01
**检查清单**: 12 项框架约定
**项目路径**:
- 服务端: D:/se/develop/server/project
- 客户端: D:/se/develop/client/project

---

## 📊 总览

- ✅ 通过：10 项
- ⚠️ 建议优化：2 项
- ❌ 违反约定：0 项

---

## 详细发现

### ⚠️ 建议 1：错误处理模式不统一

**统计结果**:
- `return ERR_COMMON_FAIL;` 或 `return ERR_COMMON_OK;`: 14 处
- `return 0;` 静默返回: 1 处

**规则来源**: server-structure.md § 1.2 错误处理模式选择

**问题**: 项目推荐使用"模式 1：静默返回"（与现有大部分代码保持一致），但当前代码主要使用"模式 2：返回错误码"。

**分析**: 从实际代码看，`GetReward`/`SendFreeReward`/`SendPayReward` 等函数大量使用 `return ERR_COMMON_FAIL` 返回错误码，只有 `GetAllReward` 函数末尾使用 `return 0;`。这与项目中其他业务模块的主流做法（静默返回 + 内部调用 `CustomCommonErrorSysInfo` 提示错误）有一定差异。

**建议**: 
1. 如果保持现有实现（返回错误码），需确认调用方能正确处理这些错误码
2. 如果改为模式 1，需在各个校验失败点调用 `CustomCommonErrorSysInfo()` 提示错误，然后 `return 0;`

**严重程度**: ⚠️ 中（不影响功能，但代码风格不一致）

---

### ⚠️ 建议 2：红点计算在 Record 变化时触发（已正确实现，但需确认无性能问题）

**位置**: `Assets/Script/LogicModule/ActivityModule/MixGrowthFundModule/MixGrowthFundModule.cs:68-89`

**代码**:
```csharp
void OnOpenRecChanged(ObjectID self, string record)
{
    RefreshPurchasedFunds(self);
    foreach (var activityId in m_PurchasedFunds.Keys)
    {
        m_BusinessActivityModule.DirtyRedPoint(activityId, BusinessActivityType.MixGrowthFund);
        m_Kernel.CommandDynamic(CommandID.OnMixGrowthFundRefresh, VarList.AllocAutoVarList() < activityId);
    }
}

void OnRewardRecChanged(ObjectID self, string record)
{
    RefreshRewardStatuses(self);
    foreach (var key in m_RewardStatuses.Keys)
    {
        int activityId = (int)(key >> 32);
        int rewardId = (int)(key & 0xFFFFFFFF);
        m_BusinessActivityModule.DirtyRedPoint(activityId, BusinessActivityType.MixGrowthFund);
        m_Kernel.CommandDynamic(CommandID.OnMixGrowthFundRewardClaim, VarList.AllocAutoVarList() < activityId < rewardId);
        m_Kernel.CommandDynamic(CommandID.OnMixGrowthFundRefresh, VarList.AllocAutoVarList() < activityId);
    }
}
```

**规则来源**: client-structure.md "红点规则"章节

**分析**: 代码正确地在 Record Hook 回调中触发红点计算，符合框架约定。但如果 `m_RewardStatuses` 包含多个档位（最多 10 档），`OnRewardRecChanged` 会在一次 Record 变化时触发 10 次 `DirtyRedPoint` 和 20 次 `CommandDynamic`。

**建议**: 
1. 如果一次只领取一个档位的奖励，当前实现没问题
2. 如果"一键领取"会同时修改多个档位的 Record，考虑在循环后只调用一次 `DirtyRedPoint(activityId, ...)`（去重 activityId）

**严重程度**: ⚠️ 中（当前实现符合约定，但可优化性能）

---

## ✅ 通过的检查

### ✅ server-001: 协议参数起始索引

**检查结果**: 所有协议处理函数均从 `args.IntVal(1)` 开始，符合框架约定。

**检查文件**: 
- `MixGrowthFundEventCallBack.cpp:OnCustomGetReward`: `args.IntVal(1)`, `args.IntVal(2)`, `args.IntVal(3)` ✓
- `GrowthFundEventCallBack.cpp:OnPlayerRechargeMixGrowthFund`: `args.IntVal(1)` ✓

**规则来源**: server-structure.md § 1.1

---

### ✅ server-003: 配置字段名检查

**检查结果**: 配置加载代码中的字段名与 design.md 附录 C 完全一致（大小写敏感）。

**检查文件**: `MixGrowthFundEventCallBack.cpp:164-203`

**对比结果**:
- `ActiveId` ✓
- `RechargeId` ✓
- `Direct` ✓
- `DisplayType` ✓
- `Name` ✓
- `NextActiveName` ✓
- `ReserveTime` ✓
- `RewardId` ✓
- `FreeReward` ✓
- `FreeHighlight` ✓
- `PayReward` ✓
- `PayHighlight` ✓

**规则来源**: server-structure.md § 2.1

---

### ✅ server-004: Record 查询 null 保护检查

**检查结果**: 所有 `GetRecord` 调用后均有 `!rec.Exist()` 检查。

**检查文件**:
- `MixGrowthFundFunc.cpp:53`: `IRecord& rec = pKernel->GetRecord(...)` → `if (!rec.Exist())` ✓
- `MixGrowthFundFunc.cpp:105`: `IRecord &rec = pKernel->GetRecord(...)` → `if (!rec.Exist())` ✓
- `MixGrowthFundFunc.cpp:113`: `IRecord &rec = pKernel->GetRecord(...)` → `if (!rec.Exist())` ✓

**规则来源**: 隐含规则（Record 操作安全性）

---

### ✅ client-001/002: UI 方法签名检查

**检查结果**: 未找到 `OnCellUpdated` 或 `DettachPage` 方法，本项目使用回调模式（`m_ScrollRewards.onCellUpdate = OnRewardCellUpdate`），不涉及这些方法签名。

**检查文件**: 
- `MixGrowthFundPage.cs`: 使用 `SingleScrollView.onCellUpdate` 回调模式 ✓
- `MixGrowthFundRewardCell.cs`: 不继承框架基类，无需实现这些方法 ✓

**规则来源**: client-structure.md § 2.1

**说明**: 本功能 UI 实现采用了不同的架构模式，不涉及这些方法，因此该检查项不适用。

---

### ✅ client-003: 红点计算触发时机检查

**检查结果**: 红点计算只在 Record 表变化时触发，未在刷新循环中调用。

**检查文件**: `MixGrowthFundModule.cs:68-89`

**代码模式**:
```csharp
// ✓ 在 Record Hook 回调中触发
void OnOpenRecChanged(ObjectID self, string record) {
    m_BusinessActivityModule.DirtyRedPoint(activityId, BusinessActivityType.MixGrowthFund);
}

void OnRewardRecChanged(ObjectID self, string record) {
    m_BusinessActivityModule.DirtyRedPoint(activityId, BusinessActivityType.MixGrowthFund);
}
```

**规则来源**: client-structure.md "红点规则"章节

---

### ✅ client-004: BusinessActivityModule 接入检查

**检查结果**: 活动模块正确接入 BA 框架。

**检查文件**: `MixGrowthFundModule.cs:40-42`

**必需调用**:
- `RegisterSeverActivityParamArgs(BusinessActivityType.MixGrowthFund, OnRecvActivityInfo)` ✓ (行 40)
- `RegisterRedPointCallback(BusinessActivityType.MixGrowthFund, OnRedChanged)` ✓ (行 41)

**规则来源**: client-structure.md § 1.1

---

### ✅ client-005: 原始协议解析起始索引检查

**检查结果**: 本功能使用 BusinessActivity 框架统一协议，不涉及原始协议（`AddCustomHook` 注册），该检查项不适用。

**分析**: 客户端通过 `RegisterSeverActivityParamArgs` 注册回调，由 BA 框架统一处理协议解析，业务模块接收到的是已解析的 `IVarList args`，不需要从索引 0 开始手动解析。

**规则来源**: client-structure.md § 1.3.1

---

### ✅ client-006: BusinessActivity 协议解析起始索引检查

**检查结果**: 使用 `BActivityCommonParamArgs.ParamArgs(args)` 框架方法，内部自动从 `BAActivityInfoIndex.CustomStart` 开始解析。

**检查文件**: `MixGrowthFundModule_Net.cs:42-46`

**代码**:
```csharp
BActivityParamArgs OnRecvActivityInfo(IVarList args)
{
    var data = new BActivityCommonParamArgs();
    data.ParamArgs(args);  // ✓ 框架方法内部处理索引偏移
    return data;
}
```

**规则来源**: client-structure.md § 1.3.2

**说明**: `BActivityCommonParamArgs` 是 BA 框架提供的基类，其 `ParamArgs` 方法内部已正确处理索引偏移，业务代码无需关心。

---

### ✅ config-001: outcode_config.json 配置完整性检查

**检查结果**: 配置表已正确配置代码生成。

**检查内容**:
- `need_copy` 包含 `active_fund_main` ✓
- `need_copy` 包含 `activity_mix_growthfund_reward` ✓
- `NeedParseDataMethod` 包含两张表（动态配置） ✓

**检查文件**: `D:/se/develop/client/tools/table/table_config/outcode_config.json`

**规则来源**: config-structure.md "代码生成配置"

---

### ✅ config-002: 字段属性标注完整性检查

**检查结果**: 根据 tasks.md § 2.1，配置表字段原本标注为 S（Server-only），但在实施过程中发现该属性导致字段不生成强类型，已全部改为 A（All）。这是合理的修正决策。

**技术债务记录**: tasks.md 第 311 行已记录："design/config.md 的'属性建议 S'结论被实践推翻（S 属性导致字段不生成强类型，已全改为 A）"。

**规则来源**: config-structure.md "字段定义"

**说明**: 配置表实施过程中根据实际情况调整了属性标注，这种灵活调整是合理的。

---

## 📋 完整性检查

### ✅ 服务端模块存在性

**检查结果**: `MixGrowthFundModule` 已完整实现。

**检查文件**:
- `MixGrowthFundModule.h` ✓
- `MixGrowthFundModule.cpp` (或 MixGrowthFundEventCallBack.cpp) ✓
- `MixGrowthFundFunc.cpp` ✓

---

### ✅ 客户端模块存在性

**检查结果**: `MixGrowthFundModule` 已完整实现。

**检查文件**:
- `MixGrowthFundModule.cs` ✓
- `MixGrowthFundModule_Net.cs` ✓
- `MixGrowthFundDefine.cs` ✓

---

### ✅ 客户端 UI 存在性

**检查结果**: UI 脚本已完整实现。

**检查文件**:
- `MixGrowthFundPage.cs` ✓
- `MixGrowthFundRewardCell.cs` ✓
- `MixGrowthFundRewardTierRow.cs` ✓

---

## 🔍 已修正项（对比 tasks.md 记录）

### ✅ 服务端配置加载宏修正

**位置**: `MixGrowthFundEventCallBack.cpp:164, 191`

**修正内容**:
- 第 164 行：`READ_SYNC_FILE(m_mainCfgPath, UnloadMainCfg)` ✓
- 第 191 行：`READ_SYNC_FILE(m_rewardCfgPath, UnloadRewardCfg)` ✓

**问题**: 原代码使用 `READ_FILE` 宏，未接入 ConfigSyncModule，导致配置表未注册进 `mFileMap`，客户端无法拉取。

**规则来源**: config-structure.md "动态配置的服务端实现核查"、tasks.md § 2.7

---

### ✅ 客户端 DynamicConfigModule 接入

**位置**: `MixGrowthFundModule.cs:6, 17-27, 49`

**修正内容**:
- 实现 `IConfigSyncMethod` 接口 ✓
- `fileNameList` 返回两张表名 ✓
- `OnInit()` 调用 `RegisterSyncMethod(this)` ✓

**问题**: tasks.md § 2.6a 记录，若只完成"表级注册"（RegisterTable）而缺少"活动级注册"（IConfigSyncMethod），查表接口会一直返回空。

**规则来源**: config-structure.md "动态配置的服务端实现核查"、tasks.md § 4.1a

---

## 📌 后续步骤

1. **人工评审建议项**（2 项），决定是否修复
2. **运行下一阶段**: `/lr-openspec-test-validate growth-fund` 检查测试覆盖

---

## 📊 检查方法说明

- **服务端检查**: 使用 Read/Grep 工具直接读取 .cpp/.h 文件
- **客户端检查**: 使用 Read/Grep 工具直接读取 .cs 文件
- **配置表检查**: 读取 outcode_config.json 文件
- **CodeGraph**: 原计划使用 CodeGraph 但查询未返回结果，已退化到 Grep/Read 工具

---

## 版本信息

**检查工具版本**: lr-openspec-code-review v1.0  
**执行时间**: 2026-08-01  
**检查范围**: 服务端 2 个 .cpp 文件，客户端已提交的实现代码
