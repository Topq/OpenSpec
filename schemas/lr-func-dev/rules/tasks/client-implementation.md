# tasks/client-implementation.md 生成规则（精简版 v2）

> **说明**: 本文档定义客户端实施任务（tasks/*.md）的生成规则。
> 
> **设计哲学**: 规则文件只包含"任务拆分的质量标准"，所有代码模板通过 CodeGraph 查询获取。

---

## 0. 代码规范（强制）

**生成客户端 C# 代码前，必须阅读并遵守项目编码规范：**

规范文件目录（相对于客户端工程根目录）：
```
.claude/skills/common/csharp_code/
```

**必读文件清单：**
- `csharp_spec.md` — 33 条具体命名/格式/结构规则（如 `m_` 前缀、类内成员排列顺序、数据结构类的公有变量原则等）
- `csharp_gc.md` — GC 优化规则（如避免 foreach 装箱、慎用 LINQ、字符串拼接用 StringBuilder 等）
- `csharp_safe.md` — 安全编码规则（如判空、生命周期管理、避免野指针等）

**关键规则摘要（详细规则以原文件为准）：**
1. **命名约定**：
   - 私有/保护成员变量：`m_` 前缀，首字母大写（如 `m_SkillID`）
   - 静态成员变量：`s_` 前缀，首字母大写（如 `s_CacheItemList`）
   - 常量：全大写下划线分隔（如 `INVALID_REQUEST_ID`）
   - 公共属性/成员：首字母小写（如 `skillID`）
   - 类/函数/枚举：大小混排，首字母大写（如 `GrowthFundModule`、`RequestBuyGrowthFund()`）

2. **类内成员排列顺序（必须严格遵守）**：
   ```
   私有成员变量 → 保护成员变量 → 公共成员变量 → 公共属性接口 →
   公共函数 → 保护函数 → Unity系统回调函数 → 自定义回调函数 → 私有函数
   ```

3. **数据结构类原则**：
   纯数据类（只承载存储，无或极少函数）可使用公有成员变量；
   逻辑类必须使用私有成员变量 + 公共属性接口。

4. **不要猜测 API**：
   - 生成代码前，先用 `codegraph explore` 或 `grep` 查找项目中现有的真实 API 调用点。
   - 禁止根据"常识"猜测静态方法/扩展方法的存在（如 `ItemGroup.Parse()`、泛型 `GetOrAllocate<T>()`）。
   - 优先查找同模块/同类型的其他文件作为模板（如实现 `XXXModule` 时先查 `AccumulateModule`、`ActivityDrawKOIModule` 等）。

5. **编译后验证**：
   生成代码后，立即运行 `dotnet build` 检查编译错误（详见后续"编译验证"章节）。

6. **UI 文本组件强制使用 TextMeshPro**：
   - ❌ 禁止使用 Unity 原生的 `Text` 组件（`UnityEngine.UI.Text`）
   - ✅ 必须使用 `TextMeshProUGUI`（命名空间 `TMPro`）
   - 变量命名：`m_TxtTitle`（Text 前缀 + 大小混排）
   - 类型声明：`TextMeshProUGUI m_TxtTitle;`
   - 原因：项目已全面迁移到 TextMeshPro，使用旧 Text 组件会导致字体/排版不一致

**违反规范的后果**：
- 编译错误（如 CS0117、CS1061、CS0308 等）— 通常是猜测了不存在的 API
- 代码审查不通过 — 命名/排列顺序不符合项目约定
- 运行时 GC 压力 — 未遵守 GC 优化规则

**何时查规范**：
- ✅ 每次生成新的 C# 文件前，重新确认命名约定和排列顺序
- ✅ 遇到编译错误时，先 grep 真实 API 用法，再修复
- ✅ 实现涉及循环/字符串拼接/集合操作的代码时，检查 GC 优化规则

---

## 0.1 配置表代码生成规范（强制）

**禁止手写配置表 CS 代码**，必须通过工具生成。

### 配置表代码生成流程

**步骤 1：注册配置表名**
- 文件：`D:\se\develop\client\tools\table\table_config\outcode_config.json`
- 在 `need_copy` 数组中添加表名（不含 `.txt` 后缀，小写+下划线格式）
- 示例：`"active_fund_main"`, `"activity_mix_growthfund_reward"`

**步骤 2：检查是否需要 NeedParseDataMethod 配置**
- 如果配置表字段属性为 **纯S（Server only）** 且用于活动系统，需额外配置
- 在 `NeedParseDataMethod` 数组中添加同样的表名
- **判断依据**：查看 `design/config.md` 中字段定义表的"属性"列
  - 所有字段都标记为 S → 需要添加到 `NeedParseDataMethod`
  - 有任何字段标记为 C 或 A → 不需要添加

**步骤 3：生成代码**
- 双击运行 `D:\se\develop\client\tools\table\output_code_csharp.bat`
- 自动生成 4 个文件：
  - `Assets/Script/Table/Generate/Activity/{TableName}/TD{TableName}.cs` （数据类）
  - `Assets/Script/Table/Generate/Activity/{TableName}/TD{TableName}Table.cs` （表管理类）
  - `Assets/Script/Table/Extend/Activity/{TableName}/TD{TableName}Extend.cs` （数据扩展，首次生成空实现）
  - `Assets/Script/Table/Extend/Activity/{TableName}/TD{TableName}TableExtend.cs` （表扩展，含动态加载逻辑）

**步骤 4：验证生成结果**
- 检查 Generate 目录下的文件是否包含所有字段（对比 design/config.md 的字段定义）
- 检查字段类型是否正确（int/string/float）
- 检查 `ParseData` 方法是否正确解析每个字段

**违反规范的后果**：
- 手写配置表代码可能遗漏字段、类型不匹配、`ParseData` 逻辑错误
- 后续策划修改配置表字段时，手写代码不会自动同步，导致运行时解析失败

---

## 0.2 UI 脚本注册规范（强制）

**继承 AbstractPage（或其子类如 BaseActivityPage）的 UI 脚本必须注册到 UIDataTable**。

### UI 注册流程

**步骤 1：添加 UIID 枚举**
- 文件：`D:\se\develop\client\project\Assets\Script\Table\Data\Define\UIDefine.cs`
- 在 `enum UIID` 中添加新的 UI ID（按功能模块分组，插入到相似 UI 附近）
- 命名规则：UI 类名去掉 `.cs` 后缀，保持大小写一致
- 示例：
  ```csharp
  // 运营活动
  SpecialLoginActivityPage,          // 七日登陆活动(通用模板)
  ActivitySevenDayTaskPage,           // 七日任务活动
  ActivityDevelopPlanPage,            // 成长计划活动
  GrowthFundPage,                     // 成长基金活动（新增）
  ActivityDrawKOIPage,                // 锦鲤活动
  ```

**步骤 2：注册 UI 到 UIDataTable**
- 文件：`D:\se\develop\client\project\Assets\Script\LogicModule\UIModule\Data\UIDataTable.cs`
- 在 `InitUIDataTable()` 方法中添加 `AddPanelData` 调用（按功能模块分组，插入到相似 UI 附近）
- API 格式：
  ```csharp
  AddPanelData(UIID.{UI类名}, typeof({UI类名}), "{Prefab相对路径}");
  ```
- Prefab 路径规则：
  - 只需要相对路径片段，不需要 `Assets/Prefab/UI/` 前缀和 `.prefab` 后缀
  - 一般按功能模块分目录：`"WelfareActivityPanel/GrowthFundPage"`
- 示例：
  ```csharp
  // 运营活动
  AddPanelData(UIID.SpecialLoginActivityPage, typeof(SpecialLoginActivityPage), "WelfareActivityPanel/SpecialLoginActivityPage");
  AddPanelData(UIID.ActivitySevenDayTaskPage, typeof(ActivitySevenDayTaskPage), "WelfareActivityPanel/ActivitySevenDayTaskPage");
  AddPanelData(UIID.ActivityDevelopPlanPage, typeof(ActivityDevelopPlanPage), "WelfareActivityPanel/ActivityDevelopPlanPage");
  AddPanelData(UIID.GrowthFundPage, typeof(GrowthFundPage), "WelfareActivityPanel/GrowthFundPage");
  ```

**步骤 3：验证注册**
- 编译通过（`UIID.GrowthFundPage` 和 `typeof(GrowthFundPage)` 无报错）
- 运行时通过 `UIModule.OpenPage(UIID.GrowthFundPage)` 能正常打开 UI

**违反规范的后果**：
- 未注册 UIID：`UIID.GrowthFundPage` 编译错误（CS0117）
- 未注册 UIDataTable：运行时调用 `OpenPage(UIID.GrowthFundPage)` 无反应或报空引用错误
- Prefab 路径错误：UI 能打开但显示为空或加载失败

---

## 一、任务拆分粒度规则

### 1.1 粒度标准（阻断性）

**合格的任务粒度**：

| 标准 | 要求 | 检查方式 |
|-----|------|---------|
| **实现时间** | 30 分钟 ~ 2 小时 | 估算单个任务的代码量 |
| **代码行数** | 50 ~ 200 行 | 统计任务涉及的代码行数 |
| **独立验证** | 可独立运行验证 | 任务完成后能否单独测试 |
| **单一职责** | 只做一件事 | 任务描述是否包含"和""以及" |

---

### 1.2 禁止的任务类型（阻断性）

❌ **过于宽泛**：
- "实现 XXXModule 全部功能"
- "完成 UI 开发"
- "实现客户端逻辑"

❌ **过于细碎**：
- "定义 XXX 变量"
- "添加 using 语句"
- "修改缩进"

---

### 1.3 合格的任务示例

✅ **模块初始化**：
```
任务：实现 GrowthFundModule 初始化
内容：获取依赖模块、注册协议回调、注册红点回调
估算：1 小时，约 80 行代码
验证：模块加载无报错，协议回调能触发
```

✅ **协议发送**：
```
任务：实现购买请求协议发送
内容：构造 C2S_GROWTH_FUND_PURCHASE 协议参数，调用 Custom 发送
估算：30 分钟，约 50 行代码
验证：抓包看到协议发送，参数正确
```

✅ **UI 刷新**：
```
任务：实现 UI Panel 的奖励列表刷新逻辑
内容：监听 Record 变化，刷新列表 UI，更新按钮状态
估算：1.5 小时，约 150 行代码
验证：修改 Record 数据，UI 自动刷新
```

---

## 二、任务生成指南

### 2.1 从 design 文档生成任务

**生成流程**：
```
读取 design/client.md 的"关键功能说明"章节
  ↓
每个功能拆分为 1-3 个任务
  ↓
每个任务包含：文件路径、实现内容、代码模板查询、验证方式
```

**示例**（基于 design 文档的"模块初始化"功能）：
```markdown
### 任务 1：实现 GrowthFundModule 初始化

**文件**: `Assets/Script/LogicModule/GrowthFundModule/GrowthFundModule.cs`

**实现内容**:
- 获取依赖模块（BusinessActivityModule、RedPointModule）
- 注册协议回调（C2S_GROWTH_FUND_PURCHASE、C2S_GROWTH_FUND_CLAIM）
- 注册红点回调（RegisterRedPointCallback）

**代码模板获取**:
```
CodeGraph 查询：LogicModule OnInit 协议注册 红点注册
参考模块：AccumulateModule, GrowthFundModule（若已存在）
```

**验证方式**:
- 运行客户端，检查模块加载无报错
- 触发购买操作，检查协议回调能正常触发
```

---

### 2.2 任务文件结构

```markdown
# Tasks: {功能名称} - Client

## 任务列表

### 任务 1：{任务名称}
**文件**: {文件路径}
**实现内容**: {箭头列表}
**代码模板获取**: {CodeGraph 查询}
**验证方式**: {验证步骤}

### 任务 2：{任务名称}
（重复上述结构）

## 任务依赖关系

```mermaid
graph TD
  任务1 --> 任务2
  任务2 --> 任务3
```

## 验收标准

- [ ] 所有任务完成
- [ ] 代码编译通过
- [ ] 功能验证通过（见各任务验证方式）
- [ ] 代码审查通过
```

---

## 三、特殊任务类型

### 3.1 手工任务（非代码实现）

**标注方式**：
```markdown
### 任务 X：运行 output_code_csharp.bat 生成配置表代码

**任务类型**: ⚠️ 手工任务（非代码实现）

**操作步骤**:
1. 打开终端，进入 `D:\se\develop\client\tools\table\`
2. 执行 `output_code_csharp.bat`
3. 检查 `Assets/Script/Table/Data/` 下是否生成 `TDGrowthFundTable.cs`

**验证方式**:
- 生成的文件无编译错误
```

---

### 3.2 配置任务（修改配置文件）

**标注方式**：
```markdown
### 任务 X：在 TableConfig.cs 中注册新配置表

**任务类型**: ⚠️ 配置任务（修改配置文件）

**文件**: `Assets/Script/Table/TableConfig.cs`

**修改内容**:
在 `delayLoadTableArray` 数组中添加：
```csharp
TDGrowthFundTable.metaData,
```

**验证方式**:
- 运行客户端，检查配置表能正常加载
```

---

## 四、代码模板查询指南

所有代码模板通过 CodeGraph 查询获取，不在规则文件中硬编码。

### 4.1 模块相关

| 任务类型 | CodeGraph 查询 | 参考模块 |
|---------|---------------|---------|
| 模块初始化 | `LogicModule OnInit 协议注册` | AccumulateModule |
| 依赖模块获取 | `GetModule BusinessActivityModule` | - |
| 事件注册 | `AddEventHook OnMainPlayerReady` | - |

---

### 4.2 协议相关

| 任务类型 | CodeGraph 查询 | 参考模块 |
|---------|---------------|---------|
| 协议发送 | `Custom CLIENT_CUSTOMMSG IVarList` | - |
| 协议接收 | `AddCustomHook SERVER_CUSTOMMSG` | - |

---

### 4.3 UI 相关

| 任务类型 | CodeGraph 查询 | 参考模块 | 特别注意 |
|---------|---------------|---------|---------|
| Panel 结构 | `AbstractPanel OnOpen OnClose` | - | UI 文本必须用 TextMeshProUGUI（变量名 `m_TxtXxx`），禁用 UnityEngine.UI.Text |
| 列表刷新 | `OnCellUpdated Transform index` | - | - |
| 文本赋值 | `TextMeshProUGUI.text` | - | 引用命名空间 `using TMPro;` |

---

### 4.4 红点相关

| 任务类型 | CodeGraph 查询 | 参考模块 |
|---------|---------------|---------|
| 红点注册 | `RegisterRedPointCallback BusinessActivityType` | BusinessActivityModule_RedPoint.cs |
| 红点刷新 | `DirtyRedPoint` | - |

---

### 4.5 配置表相关（重要）

**⚠️ 配置表代码必须通过工具生成，禁止手写**

| 任务类型 | 前置检查 | 操作步骤 |
|---------|---------|---------|
| 生成配置表代码 | 1. 确认 design/config.md 已标注字段 S/C/A 属性<br>2. 确认 design/config.md 已标注配置加载方式（静态/动态）<br>3. 确认 design/config.md 已给出 outcode_config.json 配置建议 | 1. 修改 `outcode_config.json` 添加表名<br>2. 运行 `output_code_csharp.bat` 生成代码<br>3. 验证生成的文件字段完整性 |

**配置前置检查详细步骤**：

1. **检查 design/config.md 是否完整**：
   ```bash
   # 检查字段属性列是否标注（S/C/A）
   grep "属性.*S/C/A" design/config.md
   
   # 检查 outcode_config 配置建议是否存在
   grep "outcode_config.json 配置建议" design/config.md
   ```

2. **根据 design/config.md 的建议修改 outcode_config.json**：
   - 文件位置：`D:\se\develop\client\tools\table\table_config\outcode_config.json`
   - 如果包含 C 或 A 字段 → 添加到 `need_copy` 数组
   - 如果是动态活动配置 → 添加到 `NeedParseDataMethod` 数组

3. **生成代码**：
   ```bash
   cd D:\se\develop\client\tools\table
   双击 output_code_csharp.bat
   ```

4. **验证生成结果**：
   - 检查 `Assets/Script/Table/Generate/{模块}/{表名}/` 下是否生成 4 个文件
   - 对比生成的字段列表与 design/config.md 是否一致
   - 运行 `dotnet build` 检查是否有编译错误

**常见错误**：
- ❌ 手写配置表代码 → 字段遗漏、类型不匹配、ParseData 逻辑错误
- ❌ 未检查 design/config.md → 不知道应该配置 need_copy 还是 NeedParseDataMethod
- ❌ 配置表名拼写错误 → bat 脚本找不到对应的 xlsx 文件，生成失败

**CodeGraph 查询参考**（用于验证生成结果）：
```
# 查询现有配置表的结构
TDActivityKoiReward ParseData activeId rewardId

# 查询配置表的访问方式
TDActivityKoiRewardTable GetData InsertDynamicData
```

---

## 五、常见问题 FAQ

### Q1: 如何判断任务拆分是否合理？

**A**: 检查以下标准：
- 任务描述是否清晰（无"等""以及"等模糊词）
- 任务是否可独立验证（不依赖其他任务完成）
- 任务是否符合粒度标准（30 分钟 ~ 2 小时）

---

### Q2: 如果任务过大怎么办？

**A**: 按职责拆分：
- 过大任务："实现 XXXModule 全部功能"
- 拆分后：
  - 任务 1：实现 XXXModule 初始化
  - 任务 2：实现协议发送
  - 任务 3：实现 UI 刷新逻辑

---

### Q3: 如何处理任务依赖？

**A**: 在"任务依赖关系"章节使用 Mermaid 图标注依赖：
```mermaid
graph TD
  任务1[模块初始化] --> 任务2[协议发送]
  任务2 --> 任务3[UI刷新]
```

---

**版本**: v2 (精简版)  
**最后更新**: 2026-07-22  
**维护原则**: 只包含"任务拆分的质量标准"，代码模板通过 CodeGraph 查询
