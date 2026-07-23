# design-server.md 生成规则（精简版 v2）

> **说明**: 本文档定义 design-server.md 的生成规则。
> 该文档从 proposal.md 和 specs/*.md 生成，用于服务端工程师技术评审。
> 
> **设计哲学**: 规则文件只包含"无法从代码推理的知识"，所有代码模板通过 CodeGraph 查询获取。

---

## 零、Pre-flight Check（代码库调查）

在生成 design-server.md 之前，**必须先执行代码库调查**，避免基于错误假设设计。

### 调查清单

使用 CodeGraph 查询以下内容（优先），或使用 Grep/Glob 作为备选：

| 调查项 | CodeGraph 查询示例 | 目的 |
|-------|------------------|------|
| **功能是否已实现** | `<功能名> Module Record 表名` | 避免重复设计 |
| **Record 表是否已定义** | `#define <TABLE_NAME>_REC` | 判断是扩展还是新建 |
| **协议是否已定义** | `CLIENT_CUSTOMMSG_<KEYWORD>` | 判断是复用还是新建 |

**项目路径**: `D:/se/develop/server/project`

### 调查结果的文档体现

调查结果必须体现在 design-server.md 的以下位置：

1. **`## ⚠️ 当前状态` 章节**（若发现与 proposal 假设冲突）
2. **`## 背景与目标`**（简要说明是新增还是修改）
3. **`## 模块定义`**（使用实际路径，不要猜测）

---

## 一、架构决策规则

以下规则定义了**无法从代码推理的架构决策标准**。

### 1.1 协议处理函数标准结构

**标准结构**（框架约定）：

```cpp
int XXXModule::OnCustomXXX(const PERSISTID& player, const PERSISTID& sender, const IVarList& args)
{
    // 第 1 步：解析参数
    int activityID = args.IntVal(1);      // ⚠️ 参数从索引 1 开始（索引 0 是协议号）
    int rewardID = args.IntVal(2);
    
    // 第 2 步：参数校验
    if (!CheckCanGetReward(player, activityID, rewardID))
    {
        // 校验失败直接返回，CheckCanGetReward 内部已发送错误提示
        return 0;
    }
    
    // 第 3 步：执行业务逻辑
    DoGetReward(player, activityID, rewardID);
    
    return 0;
}
```

**⚠️ 关键约定**（框架限制）：
- 参数从 `args.IntVal(1)` 开始，索引 0 是协议号
- 不要写成 `args.IntVal(0)`，会导致参数错位

**注册方式**：
```cpp
// 在 XXXModule::Init() 中注册
ADD_INT_CUSTOM_HOOK(player, CLIENT_CUSTOMMSG_XXX_GET_REWARD, OnCustomGetReward, KERNELTYPE_LOCAL);
```

**代码模板获取**：
```
CodeGraph 查询：OnClientEquipCard OnCustomGetReward protocol handler
参考模块：CardModule, AccrueRechargeModule
```

---

### 1.2 错误处理模式选择

**模式选择**（架构决策）：

| 模式 | 使用场景 | 协议回调返回值 | 错误提示方式 |
|-----|---------|--------------|------------|
| **模式 1：静默返回** | 大部分场景（推荐） | `return 0;` | 校验函数内部调用 `CustomCommonErrorSysInfo()` |
| **模式 2：返回错误码** | 客户端需要细粒度错误处理 | `return ERR_COMMON_OK/FAIL;` | 协议框架统一处理 |

**推荐**: 使用模式 1，与现有大部分模块保持一致。

**代码模板获取**：
```
模式 1：CodeGraph 查询 "CardModule OnClientEquipCard CheckCanEquipCard"
模式 2：CodeGraph 查询 "FirstRechargeModule OnCustomGetReward ERR_COMMON"
```

---

### 1.3 Record 表列枚举命名约定

<!-- 来源：从真实代码归纳（EquipSuitRecastDefine.h, AIDefine.h, AccFirstRechargeDefine.h） -->

**命名规则**（从现有代码归纳）：

#### 规则 1：表名宏定义

```cpp
#define {TABLE_NAME}_REC "table_name_rec"
```

---

#### 规则 2：列枚举前缀（两种模式）

**模式 A：缩写模式**（表名较长时使用）
- 取每个单词的首字母大写，去掉 `_REC` 后缀
- 示例：
  ```cpp
  #define EQUIP_RECAST_BACKUP_ID_REC "equip_recast_backup_id_rec"
  enum
  {
      ERBIR_SUIT_ID,  // EQUIP RECAST BACKUP ID REC → ERBIR_
  };
  ```

**模式 B：完整单词模式**（表名较短或语义重要时使用）
- 保留完整单词，追加 `_COL_` 或 `_REC_COL_`
- 示例：
  ```cpp
  #define RELEVANT_MONSTER_REC "relevant_monster"
  enum
  {
      RELEVANT_MONSTER_COL_ID,      // 完整单词 + COL
      RELEVANT_MONSTER_COL_OBJECT,
  };

  #define AI_TIME_METER_REC "ai_time_meter_rec"
  enum
  {
      AI_TIME_METER_REC_COL_NAME,        // 完整单词 + REC + COL
      AI_TIME_METER_REC_COL_START_TIME,
  };

  #define ACC_FIRST_RECHARGE_GIFT_REC "acc_first_recharge_gift_rec"
  enum
  {
      AFR_GIFT_REC_ID,     // ACC FIRST RECHARGE → AFR_
      AFR_GIFT_REC_STATE,
  };
  ```

---

#### 如何选择模式？

| 表名长度 | 推荐模式 | 示例 |
|---------|---------|------|
| ≤ 3 个单词 | 模式 B（完整单词） | `AI_TIME_METER_REC` |
| ≥ 4 个单词 | 模式 A（缩写） | `EQUIP_RECAST_BACKUP_ID_REC` |
| 语义重要（如核心表） | 模式 B（完整单词） | `RELEVANT_MONSTER_REC` |

**注意**：实际项目中两种模式都存在，选择时参考同一模块的其他 Record 表命名风格保持一致。

**代码模板获取**：
```
CodeGraph 查询：#define REC enum COL Record 表定义
参考文件：define/AIDefine.h, define/AccFirstRechargeDefine.h, define/EquipSuitRecastDefine.h
```

---

## 二、框架特殊约定

以下约定是**框架的特殊限制**，AI 无法从代码推理，必须明确告知。

### 2.1 配置加载约定

**加载流程**（固定模式）：

```cpp
// 在 XXXModule.h 中定义配置结构体
struct ST{ConfigName}
{
    int nActiveId;
    fast_string strName;
    // ... 其他字段
};

// 在 XXXModule::LoadResource() 中加载
void XXXModule::LoadXXXConfig(IKernel *pKernel)
{
    READ_FILE(m_ConfigPath, UnloadXXXConfig)
        int nActiveId = txt.ReadInt(i, "ActiveId");  // ⚠️ 字段名必须与 Excel 列名完全一致（大小写敏感）
        
        ST{ConfigName}& cfg = m_ConfigMap[nActiveId];
        cfg.nActiveId = nActiveId;
        cfg.strName = txt.ReadString(i, "Name");
        
        LogicAssert(cfg.nActiveId > 0);  // 检查主键有效性
    READ_FILE_END
}
```

**⚠️ 关键约定**（框架限制）：
- `txt.ReadInt(i, "FieldName")` 的字段名必须与 Excel 列名完全一致（大小写敏感）
- 使用 `LogicAssert` 检查主键不重复

**代码模板获取**：
```
CodeGraph 查询：READ_FILE LoadResource 配置加载
参考模块：AccrueRechargeModule, CardModule
```

---

### 2.2 事务边界和回滚策略

<!-- 来源：代码查询结果 - 未发现显式事务控制代码 -->

**🔍 项目实际情况**：
当前未在协议处理代码中发现显式的事务控制逻辑（如 `BeginTransaction`, `Commit`, `Rollback`）。

这可能意味着：
1. 项目使用隐式事务（框架自动处理）
2. 事务逻辑在数据库层或底层框架中
3. 部分协议确实没有事务保护

**临时指导**：
- 参考现有协议处理函数的错误处理模式（通过 CodeGraph 查询）
- 若协议涉及多表修改，咨询数据库架构师确认事务策略
- 优先保证数据一致性：若操作失败，确保已修改的数据能回滚或补偿

**代码模板获取**：
```
CodeGraph 查询：OnCustom protocol handler 错误处理
参考模块：CardModule, AccrueRechargeModule
```

**建议**：在实际生成 design 文档时，基于 CodeGraph 查询现有协议的处理模式，而非盲目添加事务代码。

---

## 三、Open Questions 质量标准

**回答质量检查**（设计合并门禁）：

### 3.1 禁止模糊词汇（阻断性）

❌ **不合格词汇**："看情况""暂时这样""应该可以""先按现在的做""待定""后续再说"

✅ **处理方式**：若发现模糊词汇 → 阻断合并，要求重新回答

---

### 3.2 技术问题必须包含类型定义（阻断性）

❌ **不合格示例**："需要这个字段"（缺少类型）

✅ **合格示例**："int, 0=不显示 1=显示"

---

### 3.3 业务逻辑问题必须包含具体处理策略（阻断性）

❌ **不合格示例**："按常规处理"（什么是常规？）

✅ **合格示例**："活动结束后，已购买未领取的奖励发邮件补发，有效期 30 天"

---

## 四、文档结构模板

### 4.1 必需章节

```markdown
# Design: {功能名称} - Server

## ⚠️ 当前状态（若 Pre-flight Check 发现既有实现）

## 背景与目标

## 模块定义
- 模块名称
- 文件路径（使用 Pre-flight Check 发现的实际路径）
- 依赖模块

## Record 表定义
（必须与客户端完全对齐）

## 配置表定义
（完整字段、配置结构体、加载流程）

## 协议定义
（C2S 处理、S2C 下发、错误码）

## 业务逻辑流程
（状态机、校验规则、奖励发放）

## 关键功能说明
（职责和设计决策，不包含代码实现）

## 事件监听

## 性能考虑

## Open Questions
（必须全部解决且回答质量合格）
```

---

## 五、代码模板查询指南

所有代码模板通过 CodeGraph 查询获取。

### 5.1 模块相关

| 需求 | CodeGraph 查询 | 参考模块 |
|-----|---------------|---------|
| 模块初始化 | `ILogicModule Init LoadResource` | CardModule, AccrueRechargeModule |
| 模块文件组织 | `<类似功能>Module.h .cpp` | - |

---

### 5.2 Record 相关

| 需求 | CodeGraph 查询 | 参考模块 |
|-----|---------------|---------|
| Record 表定义 | `#define REC enum COL` | BusinessActivityDefine.h |
| Record 访问 | `GetRecord QueryInt FindInt` | - |

---

### 5.3 配置相关

| 需求 | CodeGraph 查询 | 参考模块 |
|-----|---------------|---------|
| 配置结构体 | `struct ST 配置结构体` | AccrueRechargeModule.h |
| 配置加载 | `READ_FILE LoadResource txt.ReadInt` | - |

---

### 5.4 协议相关

| 需求 | CodeGraph 查询 | 参考模块 |
|-----|---------------|---------|
| 协议处理 | `OnCustom PERSISTID IVarList` | CardModule, FirstRechargeModule |
| 协议下发 | `Custom CVarList SERVER_CUSTOMMSG` | - |
| 错误码定义 | `#define ERR_ 错误码` | ErrorCodeDefine.h |

---

## 六、常见问题 FAQ

### Q1: 如何确定协议参数的索引起点？

**A**: 参数从索引 1 开始（索引 0 是协议号）。这是框架约定，不要写成 `args.IntVal(0)`。

---

### Q2: 如何选择错误处理模式？

**A**: 优先使用模式 1（静默返回），除非客户端需要根据错误码做细粒度处理。

---

### Q3: 配置字段名如何与 Excel 对齐？

**A**: `txt.ReadInt(i, "FieldName")` 的字段名必须与 Excel 列名完全一致（大小写敏感）。

---

**版本**: v2 (精简版)  
**最后更新**: 2026-07-22  
**维护原则**: 只包含"无法从代码推理的知识"
