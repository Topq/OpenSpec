# Design: {功能名称} - Client

## 背景与目标
[从 proposal.md 继承]

## 模块定义

**模块名称**: {XXX}Module
**文件路径**: `Assets/Script/LogicModule/{XXX}Module/`

**文件组织**:
- {XXX}Module.cs          // 主模块，实现 ILogicModule
- {XXX}Define.cs          // 常量、枚举、适配器定义
- {XXX}Module_Record.cs   // Record 操作（可选）
- {XXX}Module_Net.cs      // 协议收发（可选）
- {XXX}Module_RedPoint.cs // 红点逻辑（可选）

**UI文件组织** (如果有UI):
- `Assets/Script/UIScript/{PanelName}/`
  - {PanelName}.cs
  - {PanelName}_Item.cs (如果有列表项)

**依赖模块**:
- XXXModule (说明依赖原因)

**功能ID分配**:
- 功能模块ID: {MODULE_ID} (如 200)
- 子功能ID范围: {START}-{END} (如 200-299)

## Record 表定义

### {TABLE_NAME}_REC

**表名常量**: `{TABLE_NAME}_REC`
**用途**: [说明这个表存储什么数据]
**数据持久化**: 是/否
**同步时机**: 登录时 / 变化时推送

**列定义**:
```csharp
// {XXX}Define.cs
public const string {TABLE_NAME_REC} = "table_name_rec";

public enum {TableName}Col
{
    ColumnName1 = 0,  // int    - 字段说明
    ColumnName2 = 1,  // string - 字段说明
    ColumnName3 = 2,  // int64  - 字段说明
}
```

**数据来源**: 
- 登录时服务器推送完整数据
- 协议 S2C_XXX_YYY 增量更新

**访问方式说明**：
- 通过 `m_Kernel.FindRecord(player, {TABLE_NAME_REC})` 获取表实例
- 通过 `rec.QueryInt(row, (int){TableName}Col.ColumnName)` 查询字段值

## 协议定义

### C2S_XXX_YYY (协议号: {NUMBER})

**调用时机**: [什么时候发送这个协议]
**字段定义**:
```
int field1;  // 字段说明
string field2;  // 字段说明
```

### S2C_XXX_YYY (协议号: {NUMBER})

**接收时机**: [什么时候收到这个协议]
**字段定义**:
```
int result;  // 0=成功, 其他=错误码
```

**错误码**:
- XXX_ERR_CODE = 值: 说明

## UI Panel 结构

### {PanelName}

**文件路径**: `Assets/Script/UIScript/{PanelName}/{PanelName}.cs`

**成员变量** (从 demo 提取):
```csharp
Text m_TxtTitle;           // data-lr-bind="title"
Button m_BtnClaim;         // data-lr-action="onClaimClick"
```

**方法签名** (从 demo 提取):
```csharp
void OnClaimClick();       // data-lr-action="onClaimClick"
void RefreshUI();
```

## 状态机定义

**状态枚举**:
```csharp
enum {ModuleName}State
{
    Locked,      // 未解锁
    Unlocked,    // 已解锁，未购买
    Purchased,   // 已购买
    Claimed,     // 已领取
}
```

**状态转移**:
- Locked → Unlocked: 条件达成
- Unlocked → Purchased: 充值成功
- Purchased → Claimed: 领取成功

## 交互流程

### 打开界面
1. 用户点击入口
2. 请求 C2S_XXX_OPEN
3. 收到 S2C_XXX_OPEN，刷新 UI

### 领取奖励
1. 用户点击领取按钮
2. 请求 C2S_XXX_CLAIM
3. 收到 S2C_XXX_CLAIM，更新状态机
4. 刷新 UI

## Open Questions

### Q: [问题描述]
**Answer**: 

