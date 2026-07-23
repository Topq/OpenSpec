# Design: {功能名称} - Server

## 背景与目标
[从 proposal.md 继承]

## 模块定义

**模块名称**: {XXX}Module
**文件路径**: `FsGame/{YYY}Module/{XXX}Module/`

**文件组织**:
- {XXX}Module.h              // 模块定义、接口声明、配置结构体
- {XXX}Func.cpp              // 业务逻辑实现
- {XXX}EventCallBack.cpp     // 事件监听回调（可选）
- {XXX}Define.h              // 宏定义、枚举、常量

**依赖模块**:
- XXXModule (说明依赖原因)

## Record 表定义

### {TABLE_NAME}_REC

**表名宏**: `#define {TABLE_NAME}_REC "table_name_rec"`
**用途**: [说明这个表存储什么数据]
**数据持久化**: 是/否
**索引字段**: player_id (必须)

**列定义**:
```cpp
// {XXX}Define.h
enum E{TableName}Col
{
    COL_COLUMN_NAME_1 = 0,  // int    - 字段说明
    COL_COLUMN_NAME_2 = 1,  // string - 字段说明
    COL_COLUMN_NAME_3 = 2,  // int64  - 字段说明
    COL_{TABLE_NAME}_MAX,
};
```

**创建表**:
```cpp
// {XXX}Module.h
bool Create{TableName}Rec(IKernel *pKernel, const PERSISTID &player);
```

**访问方式**:
- 通过 `pKernel->GetRecord(player, {TABLE_NAME}_REC)` 获取表实例
- 通过 `rec->QueryInt(row, COL_COLUMN_NAME)` 查询字段值

## 配置表定义

### {ConfigName} - `{table_name}.txt`

**配置文件路径**: `ini/activity/{table_name}.txt`

**字段定义**:
| 字段名 | 类型 | 说明 | 示例值 | 必填/可选 |
|--------|------|------|--------|-----------|
| ActiveId | int | 活动ID，唯一标识 | 1001 | 是 |
| Name | string | 名称 | "成长基金" | 是 |

**配置结构体**:
```cpp
// {XXX}Module.h
struct ST{ConfigName}
{
    int nActiveId;              // 活动ID
    fast_string strName;        // 名称
};
```

**加载实现**:
```cpp
// {XXX}EventCallBack.cpp
void {XXX}Module::Load{Config}Cfg(IKernel *pKernel)
{
    READ_FILE_BEGIN(pKernel, m_{config}CfgPath, i)
        int nActiveId = txt.ReadInt(i, "ActiveId");
        LogicAssert(m_{config}Cfgs.find(nActiveId) == m_{config}Cfgs.end());
        
        ST{ConfigName} &cfg = m_{config}Cfgs[nActiveId];
        cfg.nActiveId = nActiveId;
        cfg.strName = txt.ReadString(i, "Name");
    READ_FILE_END
}
```

## 协议定义

### C2S_XXX_YYY (协议号: {NUMBER})

**处理函数**: `int {XXX}Module::OnC2SXxxYyy(IKernel *pKernel, const PERSISTID &player, const IVarList &msg)`

**字段定义**:
```cpp
int nField1 = msg.IntVal(0);      // 字段说明
const char* szField2 = msg.StringVal(1);  // 字段说明
```

**处理流程**:
1. 参数校验
2. 业务逻辑
3. 发送响应

### S2C_XXX_YYY (协议号: {NUMBER})

**发送时机**: [什么时候发送这个协议]

**字段定义**:
```cpp
CVarList msgResult;
msgResult << S2C_XXX_YYY;
msgResult << nResult;              // 0=成功, 其他=错误码
```

**错误码**:
```cpp
// {XXX}Define.h
#define XXX_ERR_CODE 值  // 说明
```

## 业务逻辑流程

### 领取奖励流程

**函数签名**: `int {XXX}Module::ClaimReward(IKernel *pKernel, const PERSISTID &player, int nRewardId)`

**流程**:
1. 校验条件是否达成
2. 校验是否已领取
3. 发放奖励
4. 更新 Record 表
5. 推送客户端

**校验规则**:
- 条件1: [具体判断逻辑]
- 条件2: [具体判断逻辑]

**事务边界**:
[说明哪些操作必须原子性完成]

## Open Questions

### Q: [问题描述]
**Answer**: 

