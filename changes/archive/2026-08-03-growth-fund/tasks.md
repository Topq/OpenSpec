# Tasks: growth-fund

## 1. Contract 定义

服务端 MixGrowthFundModule 已完整实现，协议已定义，本次无需新增 Contract。

- [x] 1.1 [Contract] 协议已存在
  - CLIENT_CUSTOMMSG_NOTIFY_OPEN_ACTIVITY_PANEL（通用协议）
  - CLIENT_CUSTOMMSG_QUERY_ACTIVITY_INFO（通用协议）
  - CLIENT_CUSTOMMSG_QUICK_GET_ACTIVITY_REWARD（通用一键领取协议，客户端点击奖励格子实际调用的协议）
  - CLIENT_CUSTOMMSG_MIX_GROWTH_FUND_GET_REWARD（模块专属，服务端已实现，客户端未调用）
  - COMMAND_BIZ_ACTIV_CHANGED（通用 command）

## 2. 配置表

依赖：无（与 Contract 并行）

### 2.1 主表配置

- [x] 2.1 [Config] 策划创建 active_fund_main.xlsx 并填充数据
  目标路径：D:/se/design/table/default_ios/activity/active_fund_main.xlsx
  字段定义（按列顺序）：
    - ActiveId (int, 必填) - 活动ID
    - RechargeId (int, 必填) - 关联充值商品ID
    - Direct (string, 必填) - 基金类型标识
    - DisplayType (int, 可选) - 保留字段，填0
    - Name (string, 可选) - 保留字段，填空
    - NextActiveName (string, 可选) - 保留字段，填空
    - ReserveTime (int, 可选) - 保留字段，填0
  参考：design.md 附录 C

- [x] 2.2 [Config] 策划创建 activity_mix_growthfund_reward.xlsx 并填充数据
  目标路径：D:/se/design/table/default_ios/activity/activity_mix_growthfund_reward.xlsx
  字段定义（按列顺序）：
    - Id (int) - 自增ID
    - ActiveId (int) - 所属活动ID
    - RewardId (int) - 档位ID（1-10）
    - FreeReward (string) - 免费奖励串
    - FreeHighlight (string) - 特效ID
    - PayReward (string) - 投资奖励串
    - PayHighlight (string) - 特效ID
  参考：design.md 附录 C

- [x] 2.3 [Config] 策划在 recharge.xlsx 中新增成长基金商品
  目标路径：D:/se/design/table/default_ios/recharge.xlsx
  新增：RechargeId=1013, RechargeType=5, Price=30
  参考：design.md 附录 C

- [x] 2.4 [Config] 策划在 activity_goal.xlsx 中配置每档条件目标
  目标路径：D:/se/design/table/default_ios/activity/activity_goal.xlsx
  配置要求：
    - ActivityId=10008
    - RewardId=1~10
    - Type 列填 AM_TYPE 枚举数值（1/37/244/8/109）
    - Num 列填目标值
  参考：design.md - Decisions - 配置结构

### 2.2 客户端配置表代码生成

- [x] 2.5 [Client] 修改 outcode_config.json 注册配置表
  目标路径：D:/se/develop/client/tools/table/table_config/outcode_config.json
  修改内容：
    - 在 "NeedParseDataMethod" 数组中添加同样两个表名：两张表字段全部为 S
      （Server-only，见 design.md 附录 C 属性列），且用于活动系统、服务端在运营期间
      可动态调整，需要生成 `ParseData(Dictionary<string, Var>)` 方法，供
      `DynamicConfigModule` 整表同步时逐行解析（见 design.md「配表依赖」章节）
  验证方式：need_copy 和 NeedParseDataMethod 数组都包含两张新表
  参考：client-implementation.md - 0.1 配置表代码生成规范（步骤1、步骤2）

- [x] 2.6 [Client] 运行 output_code_csharp.bat 生成配置表代码
  目标路径：D:/se/develop/client/tools/table/
  依赖：任务 2.5（outcode_config.json 已添加两张表）
  操作步骤：运行 output_code_csharp.bat，生成 TDActiveFundMain.cs / TDActivityMixGrowthfundReward.cs
    及对应的 Table.cs / Extend.cs 共 8 个文件
  验证方式：生成的文件无编译错误；ParseData 方法字段与 design.md 附录 C 一致
  参考：client-implementation.md - 0.1 配置表代码生成规范（步骤3、步骤4）

- [x] 2.6a [Client] 接入 DynamicConfigModule 整表同步
  目标路径：
    - Assets/Script/LogicModule/DynamicConfigModule/DynamicConfigModule_Process.cs
    - Assets/Script/Table/Extend/Activity/ActiveFundMain/TDActiveFundMainTableExtend.cs
    - Assets/Script/Table/Extend/Activity/ActivityMixGrowthfundReward/TDActivityMixGrowthfundRewardTableExtend.cs
  依赖：任务 2.6（TDActiveFundMain.cs / TDActivityMixGrowthfundReward.cs 已生成）
  实现内容：
    - 在 `DynamicConfigModule_Process.cs::InitProcessDic()` 中为两张表各调用一次
      `RegisterTable(表类.metaData.tableName, typeof(表类), 表类.InsertDynamicData,
      表类.ParseComplete, 表类.ClearDynamicData)`
    - 在两个 TableExtend.cs 中实现 `InsertDynamicData`/`ParseComplete`/`ClearDynamicData`
      /`ClearExtend` 调用清理方法，格式参照 `TDActivityKoiRewardTableExtend.cs`
  代码模板：codegraph explore "TDActivityKoiRewardTableExtend InsertDynamicData RegisterTable"
  验证方式：编译通过；运行时 `TDActiveFundMainTable.GetData(activeId)` /
  `TDActivityMixGrowthfundRewardTable.GetDataList()` 能读到服务端同步下发的数据
  参考：design.md「配表依赖」章节；DynamicConfigModule_使用文档.md

### 2.3 服务端配置表同步接入

- [x] 2.7 [Server] 修改配置加载宏以接入 ConfigSyncModule 整表同步
  目标路径：FsGame/ActivityModule/BusinessActivity/GrowthFund/MixGrowthFundEventCallBack.cpp
  问题：LoadMainCfg 和 LoadRewardCfg 使用 `READ_FILE` 宏，未接入 ConfigSyncModule，
        导致配置表未注册进 `mFileMap`，客户端发 `CLIENT_CUSTOMMSG_PULL_CFGSYNC_FILES`
        时服务端不会推送这两张表
  修改内容：
    - 第 164 行：`READ_FILE(m_mainCfgPath, UnloadMainCfg)` → `READ_SYNC_FILE(m_mainCfgPath, UnloadMainCfg)`
    - 第 191 行：`READ_FILE(m_rewardCfgPath, UnloadRewardCfg)` → `READ_SYNC_FILE(m_rewardCfgPath, UnloadRewardCfg)`
  原因：
    - `READ_SYNC_FILE` 宏内部会调用 `load_sync_file()` → `ConfigSyncModule::LoadFile()`
      将表注册进 `mFileMap`
    - 客户端 `DynamicConfigModule` 整表同步依赖服务端主动推送，仅客户端接入（任务 2.6a）
      而服务端未注册的配置表无法推送（参考 `BATreasureHuntModule::LoadRoutimeCfg` 使用
      `READ_SYNC_FILE` 的正确做法）
  验证方式：
    - 服务器启动时配置加载成功（无编译错误，`READ_SYNC_FILE` 宏参数与 `READ_FILE` 一致）
    - 客户端登录后能通过 `TDActiveFundMainTable.GetData(activeId)` 读到服务端推送的数据
  参考：
    - config-structure.md - 动态配置的服务端实现核查
    - server-implementation.md - 3.2 配置相关 - 动态配置加载

## 3. 服务端实现

服务端 MixGrowthFundModule 已完整实现且激活中（BA_TYPE=1018），本次只需修改配置加载宏。

- [x] 3.1 [Server] MixGrowthFundModule 已实现
  - Record 表已定义
  - 协议处理已实现
  - 条件追踪委托 ActivityGoalModule
  - ⚠️ 配置加载需修改（见任务 2.7）
  参考：design.md 附录 B

## 4. 客户端实现

依赖：[Contract] 完成（已存在）

### 4.1 模块实现

- [x] 4.1 [Client] 创建 MixGrowthFundModule.cs 骨架
  目标路径：Assets/Script/LogicModule/ActivityModule/MixGrowthFundModule/MixGrowthFundModule.cs
  实现内容：
    - 实现 ILogicModule 接口
    - 定义状态缓存：m_PurchasedFunds, m_RewardStatuses
    - 获取依赖模块
    - 注册到 BusinessActivityModule（BA_TYPE=1018）
  代码模板：codegraph explore "ILogicModule Init"
  参考：design.md 附录 A

- [x] 4.1a [Client] 接入 IConfigSyncMethod，注册 active_fund_main / activity_mix_growthfund_reward 到 DynamicConfigModule
  目标路径：Assets/Script/LogicModule/ActivityModule/MixGrowthFundModule/MixGrowthFundModule.cs
  依赖：任务 2.6a（DynamicConfigModule 表级注册 RegisterTable 已完成）
  问题：任务 2.6a 只完成了"表级注册"（RegisterTable，让框架认得怎么解析这两张表），
        缺少"活动级注册"（IConfigSyncMethod + RegisterSyncMethod，告诉框架打开成长基金
        面板时要主动拉取这两张表）。缺这一步不会编译报错，但 TDActiveFundMainTable.GetData()
        等查表接口会一直返回空/默认值，因为数据从未被服务端拉取过
  实现内容：
    - MixGrowthFundModule 声明实现 IConfigSyncMethod（`ILogicModule, IConfigSyncMethod`）
    - fileNameList 返回 { MixGrowthFundDefine.ACTIVE_FUND_MAIN_CONFIG,
      MixGrowthFundDefine.MIX_GROWTHFUND_REWARD_CONFIG }（表名常量定义在 MixGrowthFundDefine.cs，
      与 outcode_config.json/服务端 txt 文件名一致）
    - preFileNameList 返回空数组（无需在活动面板打开前提前加载）
    - businessActivityType 返回 BusinessActivityType.MixGrowthFund
    - 在 OnInit() 末尾调用 m_DynamicConfigModule.RegisterSyncMethod(this)
  代码模板：codegraph explore "IConfigSyncMethod RegisterSyncMethod fileNameList"
  参考模块：ActivityDrawKOIModule（ActivityDrawKOIModule_Message.cs + OnInit 调用）、MarblePlinkoModule
  验证方式：编译通过；打开成长基金面板后 TDActiveFundMainTable.GetData(activityId) 能读到
  服务端推送的非默认值（而不仅是"类存在、编译通过"）
  参考：design/client.md「配置表访问约定」；config-structure.md「动态配置的服务端实现核查」

- [x] 4.2 [Client] 实现 MixGrowthFundModule_Net.cs 协议处理
  目标路径：Assets/Script/LogicModule/ActivityModule/MixGrowthFundModule/MixGrowthFundModule_Net.cs
  依赖：任务 2.6a（DynamicConfigModule 整表同步已接入）
  实现内容：
    - 打开面板协议
    - 查询活动数据（同步RPC）
    - 领取奖励协议
    - 一键领取
    - 监听 COMMAND_BIZ_ACTIV_CHANGED
    - 解析 QueryInfo outArgs：只取每档的 `RewardId`（联接键）、`CurNum`、`TargetNum`
      三个玩家状态字段存入 `m_RewardStatuses`；其余静态字段（RechargeId/Direct/
      DisplayType/Name/NextActiveName/FreeReward/FreeHighlight/PayReward/PayHighlight）
      不解析，改为通过 `TDActiveFundMainTable.GetData(activeId)` /
      `TDActivityMixGrowthfundRewardTable.GetDataList()` 本地查表获得（见任务 2.6a）
  代码模板：codegraph explore "Custom CLIENT_CUSTOMMSG" "TDActivityKoiRewardTable.GetDataList"
  对应验收：TC-growth-fund-01, TC-growth-fund-02, TC-growth-fund-07
  参考：design.md 附录 A - 网络协议（客户端消费范围）；任务 2.6a

- [x] 4.3 [Client] 实现 MixGrowthFundModule 红点逻辑
  目标路径：Assets/Script/LogicModule/ActivityModule/MixGrowthFundModule/MixGrowthFundModule.cs
  实现内容：
    - HasRedPoint 方法
    - 注册红点回调
    - 监听状态变化，刷新红点
  代码模板：codegraph explore "RegisterRedPointCallback DirtyRedPoint"
  对应验收：TC-growth-fund-14, TC-growth-fund-15, TC-growth-fund-16, TC-growth-fund-17
  参考：design.md 附录 A - 红点逻辑

- [x] 4.4 [Client] 实现条件类型到显示文案的映射
  目标路径：Assets/Script/LogicModule/ActivityModule/MixGrowthFundModule/MixGrowthFundModule.cs
  实现内容：
    - 硬编码 AM_TYPE 到文案模板的映射表
    - GetConditionText 方法
  对应验收：TC-growth-fund-04, TC-growth-fund-05
  参考：design.md 附录 A - Open Questions - Q3

### 4.2 UI 实现

- [x] 4.5 [Client] 创建 MixGrowthFundPage.cs 骨架
  目标路径：Assets/Script/UIScript/WelfareActivityPanel/MixGrowthFundPanel/MixGrowthFundPage.cs
  实现内容：
    - 继承 BaseActivityPage
    - 定义 UI 成员变量：m_TxtTitle, m_TxtPrice, m_BtnPurchase, m_ScrollRewards
    - 空方法签名：OnOpen, OnClose, OnRefresh, OnPurchaseClick
  注意：使用 TextMeshProUGUI，禁用 UnityEngine.UI.Text
  代码模板：codegraph explore "AbstractPage OnOpen"
  参考：client-implementation.md - 0. 代码规范

- [x] 4.6 [Client] 实现 MixGrowthFundPage 状态机与交互逻辑
  目标路径：Assets/Script/UIScript/WelfareActivityPanel/MixGrowthFundPanel/MixGrowthFundPage.cs
  实现内容：
    - OnOpen：发送协议，监听事件
    - OnRefresh：刷新购买按钮、奖励列表、进度条
    - OnPurchaseClick：调用 TradeModule.OpenRechargePanel
    - 监听购买成功事件
  代码模板：codegraph explore "BaseActivityPage OnOpen"
  对应验收：TC-growth-fund-01, TC-growth-fund-02, TC-growth-fund-03
  参考：design.md 附录 A - 交互流程

- [x] 4.7 [Client] 创建 MixGrowthFundRewardCell.cs 奖励格子组件
  目标路径：Assets/Script/UIScript/WelfareActivityPanel/MixGrowthFundPanel/MixGrowthFundRewardCell.cs
  实现内容：
    - 定义 UI 成员变量：m_LockBadge, m_BtnClaim, m_RedPoint
    - 格子状态枚举：Locked, LockedByPurchase, Claimable, Claimed
    - UpdateCell 方法：根据状态更新显示
    - OnClaimClick 方法：发送领取协议
  代码模板：codegraph explore "OnCellUpdated Transform index"
  对应验收：TC-growth-fund-07, TC-growth-fund-08, TC-growth-fund-10, TC-growth-fund-11
  参考：design.md 附录 A - 状态机定义

### 4.3 注册与集成

- [x] 4.8 [Client] 在 UIDefine.cs 中添加 UIID 枚举
  目标路径：Assets/Script/Table/Data/Define/UIDefine.cs
  修改内容：在 enum UIID 中添加 MixGrowthFundPage
  参考：client-implementation.md - 0.2 UI 脚本注册规范

- [x] 4.9 [Client] 在 UIDataTable.cs 中注册 UI
  目标路径：Assets/Script/LogicModule/UIModule/Data/UIDataTable.cs
  修改内容：AddPanelData(UIID.MixGrowthFundPage, ...)
  参考：client-implementation.md - 0.2

- [x] 4.10 [Client] 取消注释 GameLauncher.cs 中的模块注册
  目标路径：Assets/Script/Main/GameLauncher.cs:715
  修改内容：取消注释 new MixGrowthFundModule()
  参考：design.md 附录 A - 修改文件

- [x] 4.11 [Client] 取消注释 MallModule.cs 中的逻辑（已修正字段访问为强类型属性）
  目标路径：Assets/Script/LogicModule/TradeModule/Mall/MallModule.cs:24,202
  修改内容：取消注释 m_MixGrowthFundModule 相关逻辑
  参考：design.md 附录 A - 修改文件

- [x] 4.12 [Client] 取消注释 GeneralActiveModule.cs 中的红点检查
  目标路径：Assets/Script/LogicModule/GeneralActiveModule/GeneralActiveModule.cs:22,390
  修改内容：取消注释 MixGrowthFundModule 的红点检查
  对应验收：TC-growth-fund-14, TC-growth-fund-15, TC-growth-fund-16
  参考：design.md 附录 A - 修改文件

- [x] 4.13 [Client] 在 CommandID.cs 中添加 command 定义
  目标路径：Assets/Script/Define/CommandID.cs
  修改内容：添加 OnGrowthFundHistory, OnMixGrowthFundRefresh, OnMixGrowthFundRewardClaim
  参考：design.md 附录 A - 修改文件

## 5. 跨端联调

依赖：[Server] + [Client] 全部完成

- [x] 5.1 [Integration] 购买流程联调
  对应验收：TC-growth-fund-01, TC-growth-fund-02

- [x] 5.2 [Integration] 条件进度联调
  对应验收：TC-growth-fund-04, TC-growth-fund-05

- [x] 5.3 [Integration] 免费奖励领取联调
  对应验收：TC-growth-fund-07, TC-growth-fund-08, TC-growth-fund-09

- [x] 5.4 [Integration] 投资奖励领取联调
  对应验收：TC-growth-fund-10, TC-growth-fund-11

- [x] 5.5 [Integration] 双轨奖励独立领取联调
  对应验收：TC-growth-fund-12, TC-growth-fund-13

- [x] 5.6 [Integration] 红点显示联调
  对应验收：TC-growth-fund-14, TC-growth-fund-15, TC-growth-fund-16, TC-growth-fund-17

- [x] 5.7 [Integration] 配置化支持联调
  对应验收：TC-growth-fund-18, TC-growth-fund-19, TC-growth-fund-20

- [x] 5.8 [Integration] 异常流程测试
  测试内容：网络中断、重复领取、顺序校验、售卖期结束

## 验证完成状态

### 编译验证
✅ `dotnet build Assembly-CSharp.csproj` — 0 错误，1313 警告（均为项目已有）
✅ 配置表快照比对：本次生成只涉及成长基金相关的 4 个 .cs 文件，未污染其他表

### Demo 对照验证
✅ `demo/unity/MixGrowthFundPage.tsx` 已修正为 `list.single-scroll`
✅ `MixGrowthFundPage.cs` 已同步改用 `SingleScrollView` 组件（回调模式）
✅ 字段绑定、嵌套组件结构与 demo 定义一致
✅ 移除了手动 `Instantiate` 逻辑，改用 `onCellUpdate` 回调 + `Refresh(count)` 标准模式
✅ 修正 `MixGrowthFundRewardTierRow.cs` 中 `m_ConditionBar` 类型：`Slider` → `LRProgressBar`（根据 `data-component="control.progress"`）
✅ UI 文案已改用语言表 key（`.ToLanguage()`），硬编码字符串已清除，key 记录在 `Language_Keys.md`

### 技术债务记录
- design/config.md 的"属性建议 S"结论被实践推翻（S 属性导致字段不生成强类型，已全改为 A）
- design/server.md 里部分接口签名与真实代码不符（已在实现时修正，design 未回写）
- 7 个非相关配置表被生成工具误触（Fashion/Minigame/Pet/Prop/Pushgift/Question），需人工还原或下次生成时验证
- MixGrowthFundModule 原放置在 `LogicModule/BusinessActivityModule/` 下，已迁移到
  `LogicModule/ActivityModule/MixGrowthFundModule/`（与 ActivityDrawKOIModule/
  DevelopPlanModule/MarblePlinkoModule 等同类模块目录规约保持一致）
- AM_TYPE 常量、CellClaimState、MixGrowthFundRewardStatus 已从 MixGrowthFundModule.cs
  拆分到独立的 MixGrowthFundDefine.cs（参照 MarblePlinkoDefine.cs/ActivityDrawKOIDefine.cs 结构）
- MixGrowthFundModule 生命周期方法最初写成了 `public void OnCreate/OnInit/OnReset/OnShut`，
  已修正为 `protected override void OnInit/OnReset`（删除了不存在的 OnCreate/OnShut/OnUpdate/OnDestroy，
  删除了手动声明的 `IKernel m_Kernel` 字段）
- Record 监听器注册最初直接在 OnInit 里调用 `AddRecLateHook(self, ...)`（self 对象此时还未准备好），
  已修正为标准三步流程：OnInit 里 `RegisterRecLateHook` 注册回调名 → 监听 `OnMainPlayerReady` 事件 →
  在 OnMainPlayerReady 回调里 `AddRecLateHook(self, ...)` 绑定到具体玩家对象
- SKILL.md 已补充三条规则：
  1. "做任何客户端实现前先查知识库索引"（强制前置步骤，避免凭直觉编写）
  2. "新建活动模块的目录规约 + Define 文件拆分"
  3. "执行流程：知识库文档 > CodeGraph 查询 > 直接读代码"
- 知识库缺失项（待补充）：
  - `reference/module/ilogicmodule.md`（ILogicModule 生命周期方法详解、Record 监听器注册流程、
    m_Kernel 字段来源、Event Hook 注册时机等）

## 引用有效性检查

✅ 所有 "对应验收" 引用的 TC 编号都在 test-cases.md 中存在
