# design-client.md 生成规则（精简版 v2）

> **说明**: 本文档定义 design-client.md 的生成规则。
> 该文档从 proposal.md 和 specs/*.md 生成，用于客户端工程师技术评审。
> 
> **设计哲学**: 规则文件只包含"无法从代码推理的知识"，所有代码模板通过 CodeGraph 查询获取。

---

## 零、Pre-flight Check（代码库调查）

在生成 design-client.md 之前，**必须先执行代码库调查**，避免基于错误假设设计。

### 调查清单

使用 CodeGraph 查询以下内容（优先），或使用 Grep/Glob 作为备选：

| 调查项 | CodeGraph 查询示例 | 目的 |
|-------|------------------|------|
| **功能是否已实现** | `<功能名> Module Panel` | 避免重复设计 |
| **是否需接入 BA 框架** | `BusinessActivityModule BusinessActivityDefine <功能关键词>` | 判断是否复用活动框架 |
| **UI 组件是否存在** | `<功能名>Panel AbstractPanel` | 判断是新建还是修改 |

**项目路径**: `D:/se/develop/client/project`

### 调查结果的文档体现

调查结果必须体现在 design-client.md 的以下位置：

1. **`## ⚠️ 当前状态` 章节**（若发现与 proposal 假设冲突）
   - 说明现有实现概况
   - 说明本次设计调整范围

2. **`## 背景与目标`**（简要说明是新增还是修改）

3. **`## 模块定义`**（使用实际路径，不要猜测）

---

## 一、架构决策规则

以下规则定义了**无法从代码推理的架构决策标准**。

### 1.1 BusinessActivityModule 接入判断

**判断标准**（阻断性）：

```
IF `BusinessActivityDefine.cs` 中存在相关功能 ID 枚举值
THEN 必须接入 BusinessActivityModule
     - 复用 Panel 管理
     - 复用红点系统
     - 复用时间配置
     禁止设计独立的活动体系
ELSE 可设计独立模块
```

**检查方式**：
```
CodeGraph 查询：BusinessActivityModule BusinessActivityDefine <功能关键词>
若查询结果包含功能 ID → 必须接入
```

**文档体现**（在 design-client.md 的"依赖模块"章节）：
```markdown
**依赖模块**:
- BusinessActivityModule（必须接入）- 活动框架，提供 Panel 管理、红点注册、时间配置
```

---

### 1.2 Record 驱动 vs 传统协议模式选择

**选择标准**（架构决策）：

| 条件 | 选择模式 | 协议定义 |
|-----|---------|---------|
| 数据需要持久化（如购买记录、领取状态） | **Record 驱动** | 只需 C2S，无 S2C |
| 数据需要在多个 UI 界面共享 | **Record 驱动** | 只需 C2S，无 S2C |
| 一次性操作，需要立即反馈（如领取奖励显示特效） | **传统 C2S/S2C** | 需要 C2S + S2C |
| 需要返回临时数据（如奖励详情） | **传统 C2S/S2C** | 需要 C2S + S2C |

**Record 驱动模式工作流程**：
```
客户端发送 C2S 请求
  ↓
服务器更新 Record 表
  ↓
Record 自动同步到客户端（框架机制）
  ↓
UI 监听 Record 变化，自动刷新
```

**文档体现**（在 design-client.md 的"协议定义"章节顶部）：
```markdown
**返回机制**：无 S2C 协议，服务器直接更新 `XXX_REC`，客户端通过 Record 监听刷新 UI
```
或
```markdown
### S2C 协议
（定义返回协议）
```

---

### 1.3 红点系统注册方式

**注册方式选择**（框架约定）：

| 场景 | 注册方法 | 回调签名 |
|-----|---------|---------|
| 活动框架内 | `BusinessActivityModule.RegisterRedPointCallback` | `bool callback(int activityId)` |
| 独立功能 | `RedPointModule.Register` | `bool callback(RedPointType type)` |

**注册时机**：模块初始化时（`OnInit()` 方法）

**红点刷新**：
- 活动框架内：`m_BizActivityModule.DirtyRedPoint(activityId, activityType)`
- 独立功能：`m_RedPointModule.SetDirty(redPointType)`

**代码模板获取**：
```
CodeGraph 查询：RegisterRedPointCallback BusinessActivityModule
CodeGraph 查询：RedPointModule Register 红点注册
```

---

## 二、框架特殊约定

以下约定是**框架的特殊限制**，AI 无法从代码推理，必须明确告知。

### 2.1 UI 方法签名约定

**重要约定**（框架 API 限制）：

| 方法名 | 签名 | 特别注意 |
|-------|------|---------|
| `OnCellUpdated` | `(Transform root, int index)` | ⚠️ 第一个参数是 `Transform`，不是 `GameObject` |
| `AttachPage` | `(AbstractPage page, Transform parent)` | ⚠️ 参数顺序不能颠倒 |
| `DettachPage` | `(AbstractPage page)` | ⚠️ 拼写是两个 `t`（历史遗留） |

**错误示例**（编译失败）：
```csharp
void OnCellUpdated(GameObject root, int index)  // ❌ 第一个参数类型错误
void DettachPage(AbstractPage page)            // ❌ 拼写错误，框架找不到回调
```

**代码模板获取**：
```
CodeGraph 查询：OnCellUpdated AbstractPanel
CodeGraph 查询：AttachPage DettachPage Panel
```

---

### 2.2 配置表访问约定

**DynamicConfigModule 接入判断**（架构决策）：

```
IF 满足以下任一条件
   - 客户端需要在协议下发前访问配置
   - 客户端需要根据配置做本地业务判断
   - 配置数据量大，协议推送不经济
THEN 必须走 DynamicConfigModule 同步流程
ELSE 协议实时下发即可
```

**接入步骤**（固定流程）：
1. 修改 `D:\se\develop\public\table_config\outcode_config.json`
2. 执行 `output_code_csharp.bat` 重新生成代码
3. 实现 `TDXxxTableExtend.cs`（3 个方法：`InsertDynamicData`, `ParseComplete`, `ClearDynamicData`）
4. 在 `DynamicConfigModule_Process.cs` 注册

**详细说明**：参考 `tmp/design-client-implementation-details.md`（若存在）

---

## 三、Open Questions 质量标准

<!-- 来源：schema.yaml design instruction lines 313-327 -->

**回答质量检查**（设计合并门禁）：

### 3.1 禁止模糊词汇（阻断性）

❌ **不合格词汇**："看情况""暂时这样""应该可以""先按现在的做""待定""后续再说"

✅ **处理方式**：若发现模糊词汇 → 阻断合并，要求重新回答

---

### 3.2 技术问题必须包含类型定义（阻断性）

❌ **不合格示例**："需要这个字段"（缺少类型）

✅ **合格示例**："int, 0=不显示 1=显示"

✅ **处理方式**：若缺少类型定义 → 阻断合并，要求补充类型

---

### 3.3 业务逻辑问题必须包含具体处理策略（阻断性）

❌ **不合格示例**："按常规处理"（什么是常规？）

✅ **合格示例**："活动结束后，已购买未领取的奖励发邮件补发，有效期 30 天"

✅ **处理方式**：若缺少具体策略 → 阻断合并，要求明确处理方式

---

## 四、文档结构模板

### 4.1 必需章节

```markdown
# Design: {功能名称} - Client

## ⚠️ 当前状态（若 Pre-flight Check 发现既有实现）

## 背景与目标

## 模块定义
- 模块名称
- 文件路径（使用 Pre-flight Check 发现的实际路径）
- 依赖模块（必须明确是否接入 BusinessActivityModule）

## Record 表定义
（必须与服务端完全对齐）

## 配置表数据获取决策
（说明是否需要 DynamicConfigModule）

## UI 设计
（从 demo/*.html 提取结构）

## 协议定义
（说明是 Record 驱动还是传统模式）

## 红点规则
（说明注册方式）

## 关键功能说明
（职责和设计决策，不包含代码实现）

## 异常处理

## Open Questions
（必须全部解决且回答质量合格）
```

---

## 五、代码模板查询指南

所有代码模板通过 CodeGraph 查询获取，不在规则文件中硬编码。

### 5.1 模块相关

| 需求 | CodeGraph 查询 | 参考模块 |
|-----|---------------|---------|
| 模块初始化 | `LogicModule OnInit 协议注册` | GrowthFundModule, AccumulateModule |
| 模块文件组织 | `<类似功能>Module 文件结构` | - |
| 依赖模块获取 | `GetModule BusinessActivityModule` | - |

---

### 5.2 Record 相关

| 需求 | CodeGraph 查询 | 参考模块 |
|-----|---------------|---------|
| Record 表定义 | `Define.cs Record 表常量 enum` | BusinessActivityDefine.cs |
| Record 访问 | `FindRecord QueryInt GetInt` | - |
| Record 监听 | `AddRecordHook Record 监听` | - |

---

### 5.3 协议相关

| 需求 | CodeGraph 查询 | 参考模块 |
|-----|---------------|---------|
| 协议发送 | `Custom CLIENT_CUSTOMMSG IVarList` | - |
| 协议接收 | `AddCustomHook SERVER_CUSTOMMSG` | - |
| 协议参数构造 | `CVarList << 协议参数` | - |

---

### 5.4 UI 相关

| 需求 | CodeGraph 查询 | 参考模块 |
|-----|---------------|---------|
| Panel 结构 | `AbstractPanel OnOpen OnClose` | - |
| Page 结构 | `AbstractPage OnShow OnHide` | - |
| 列表刷新 | `OnCellUpdated Transform index` | - |

---

### 5.5 红点相关

| 需求 | CodeGraph 查询 | 参考模块 |
|-----|---------------|---------|
| 活动红点注册 | `RegisterRedPointCallback BusinessActivityType` | BusinessActivityModule_RedPoint.cs |
| 独立红点注册 | `RedPointModule Register RedPointType` | RedPointModule.cs |
| 红点刷新 | `DirtyRedPoint SetDirty` | - |

---

## 六、常见问题 FAQ

### Q1: 为什么规则文件不包含代码示例？

**A**: 代码示例容易过时。当项目重构 API 时，规则文件中的示例会失效，导致 AI 生成错误代码。通过 CodeGraph 查询，AI 永远获取最新的代码模板。

---

### Q2: 如果 CodeGraph 查询不到怎么办？

**A**: 使用 Grep/Glob 作为备选：
```bash
# 搜索模块初始化模式
grep -r "class.*Module.*ILogicModule" Assets/Script/LogicModule/

# 搜索协议注册模式
grep -r "AddCustomHook.*CLIENT_CUSTOMMSG" Assets/Script/LogicModule/
```

---

### Q3: 哪些内容必须在规则文件中？

**A**: 只有以下 3 类内容：
1. **架构决策标准**（如何判断是否接入 BA 框架）
2. **框架特殊约定**（如 `DettachPage` 的拼写错误）
3. **质量门禁规则**（Open Questions 回答标准）

其他内容（代码模板、文件路径、字段定义）都应该从代码库获取。

---

## 附录：精简前后对比

| 内容类型 | 精简前 | 精简后 | 变化 |
|---------|-------|-------|------|
| **架构决策规则** | 分散在示例中 | 集中在"架构决策规则"章节 | ✅ 更清晰 |
| **代码模板** | 50+ 行代码示例 × 10 处 | 改为 CodeGraph 查询指南 | ✅ 不会过时 |
| **具体项目内容** | 20+ 个字段定义 | 删除 | ✅ 减少冗余 |
| **文件总行数** | ~753 行 | ~300 行 | ✅ -60% |

---

**版本**: v2 (精简版)  
**最后更新**: 2026-07-22  
**维护原则**: 只包含"无法从代码推理的知识"
