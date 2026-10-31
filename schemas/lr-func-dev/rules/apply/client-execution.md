# apply/client-execution.md（[Client] 任务执行规则）

> **说明**：本文档定义 `[Client]` 标签任务在 apply 阶段的执行规则。由 `openspec instructions apply` 指路，`lr-openspec-apply` SKILL 在执行 `[Client]` 任务前读取本文件。
>
> **设计哲学**：本文件只包含"客户端执行阶段"的强制流程和知识来源指引；具体代码模板通过 CodeGraph 查询和知识库索引获取，不在本文件重复维护。

---

## 0. 强制前置：读取客户端工程治理文档

进入任何 `[Client]` 任务前，必须先读取客户端工程自己的 AI 协作规范：

**文件路径**（绝对路径，固定）：
```
..\develop\client\project\AGENTS.md
```

**读取后处理**：
1. 如果文档中提到特定 Skill 路由（如指向 `.claude/skills/{skill-name}/SKILL.md`），读取对应文件当规则执行。
2. 如果涉及生成代码（配置表 C# 代码、UI Prefab 等），遵守该文档里的生成器调用约定，不手写生成产物。
3. 编码风格、命名规范、禁止操作清单以该文档（及其指向的 `code_review_guide.md`/`code_template_guide.md`）为准，本文件不重复维护。

**路径来源**：该路径已记录在 `D:\se\openspec\config.yaml` 的 `context` 字段（`../develop/client/project`）。

---

## 1. 知识库索引强制前置查询

**⚠️ 强制前置步骤：做任何客户端实现前，先查知识库索引**

在开始编写任何客户端代码前，**必须先读取项目知识库入口**，确认是否有相关文档：

```bash
Read ..\develop\client\project\docs\ai-core\README.md
```

**知识库结构**（ai-core 按记忆类型分三目录，先入口后索引，不递归泛读）：

| 目录 | 职责 |
|------|------|
| `knowledge/` | 长期知识：模块/系统知识卡（唯一入口 `knowledge/core-index.md`） |
| `workflows/` | 过程流程：开发、排查、验证、提交（如 `unity-compile-verification.md`） |
| `rules/` | 硬规则：编码规范 `rules/coding_standards/`、硬门禁 `rules/gates/` |

**根据任务类型，快速定位相关知识卡**（不用全读，重点看命中条目）：

| 任务类型 | 路由 | 对应文档路径（相对 `docs/ai-core/`） |
|---------|------|-----------------------------------|
| 生成 Module 骨架 | knowledge 索引 → 对应系统卡 | `knowledge/core-index.md` → `knowledge/modules/index.md`（如 `activity-system.md`、`red-blue-point-system.md`） |
| 实现 UI 脚本 | knowledge 索引 → UI 系统卡 | `knowledge/modules/index.md` → `knowledge/modules/ui-management-system.md`（UIModule/UIDataTable/Panel 生命周期） |
| 访问配置表 | knowledge 索引 → 表系统卡 | `knowledge/modules/table-loading-system.md` |
| 红点接入 | knowledge 索引 → 红点系统卡 | `knowledge/modules/red-blue-point-system.md` |
| 编码规范 | rules | `rules/coding_standards/README.md`（见本文 §5） |
| 其他任务 | 用 Grep 在 `knowledge/core-index.md`、`knowledge/modules/index.md` 里搜索关键词 | - |

**执行流程（知识库优先原则）**：

1. **找到相关知识卡** → Read 详细文档 → 确认参考模块/参考代码
2. **用 CodeGraph 查询** → 查询标准签名、调用模式（如 `query "method OnInit in MultiSevenDayLoginModule signature"`）
3. **Read 参考代码** → 读取完整实现，理解上下文和"为什么这样写"
4. **复制标准模板** → 不要凭直觉编写

**如果知识卡索引里没有相关条目**（ai-core 口径：模块存在性/粗定位本就不进知识库，直接查源码）：
- 用 CodeGraph 搜索类似功能的实现（如 `query "class implements ILogicModule in path:ActivityModule"`）
- 或用 Grep 搜索关键词（如 `grep -rn "RegisterRecLateHook" --include=*.cs`）
- 读取至少 2 个参考文件，理解项目规范后再动手
- 在 tasks.md 记录技术债务："缺少 XXX 主题的知识库文档"

**重要原则**：
- **知识库文档 > CodeGraph 查询 > 直接读代码**
- 先看有没有文档总结，再去查代码细节
- 如果发现知识库与实际代码冲突，**以真实代码为准**，并在 tasks.md 记录文档过期问题

---

## 2. 活动模块目录规约

**⚠️ 强制前置步骤：新建活动功能模块前先确认目录规约**

如果任务是"生成 XXXModule.cs 骨架"这类**新建活动业务模块**（`ILogicModule` 实现类，代表某个具体活动/玩法功能，如成长基金、锦鲤抽奖、成长计划），**先查一遍项目里同类模块放在哪，不要凭直觉放进 `BusinessActivityModule/` 目录**：

```bash
find /d/se/develop/client/project/Assets/Script/LogicModule/ActivityModule -maxdepth 1 -type d
```

1. **目录位置**：具体活动功能模块统一放在 `LogicModule/ActivityModule/{FuncName}Module/` 下（参照 `ActivityDrawKOIModule`、`DevelopPlanModule`、`MarblePlinkoModule`），**不要**放进 `LogicModule/BusinessActivityModule/` —— 那个目录是通用框架本身（`BusinessActivityModule.cs`、`BusinessActivityDefine.cs` 等），不装具体活动的实现。判断标准：如果这个模块要 `m_Kernel.GetModule<BusinessActivityModule>()` 去调用通用框架的方法（红点、进度、菜单），它就是"框架的使用者"，该放 `ActivityModule/` 下，不是"框架本身"。

2. **常量/枚举/数据结构必须独立成 `{FuncName}Define.cs`**，不要塞在 Module 类文件底部或类内部。参照 `MarblePlinkoDefine.cs`、`ActivityDrawKOIDefine.cs` 的结构：
   ```csharp
   namespace LR
   {
       public static class {FuncName}Define
       {
           // 条件类型 / 业务枚举值等常量
           public const int XXX_TYPE_A = 1;
       }

       public enum {FuncName}XxxState { ... }   // 命名空间级别的枚举
       public struct {FuncName}XxxData { ... }  // 命名空间级别的数据结构
   }
   ```
   Module 类里引用时用 `{FuncName}Define.XXX_TYPE_A`，不要在 Module 类内部用 `const int XXX_TYPE_A` 私有声明。

3. **不要迁移的部分**：如果某些常量本来就属于 `BusinessActivityModule` 通用框架（比如 Record 表名 `BA_XXX_REC`、Record 列枚举 `BAXxxRecCol`，这些定义在 `BusinessActivityDefine.cs` 里，是所有活动类型共享的通用结构），不要往下搬到 `{FuncName}Define.cs`——只搬**这个功能专属**的常量/枚举/结构体。

4. **如果任务执行到一半才发现目录放错了**：用 `mv` 移动 `.cs` 文件到正确目录，**同时删除旧位置的 `.meta` 文件**（不要一起 mv，Unity 会在新位置自动生成新 `.meta`；如果该脚本还没有被拖到任何 prefab 上，直接删旧 `.meta` 是安全的）。移动后要检查 design 文档（`design.md`/`design/client.md`/`tasks.md`）里是否也写了旧路径，一并用 `sed` 批量替换掉，不要留着不一致的文档。

---

## 3. demo 组件映射与 UI 文案 key 化

**⚠️ 强制前置步骤：检查 demo 定义（UI 相关任务）**

如果任务涉及 UI 脚本（路径包含 `UISript/`、`Panel`、`Page`），**必须先检查 `{功能}/demo/` 目录**：

1. **查找 demo 文件**
   ```bash
   find "changes/{change-id}/demo" -iname "*.tsx" -o -iname "*.prefab"
   ls -la "changes/{change-id}/demo/unity/"
   ```

2. **对照 demo 定义编写代码**
   - **⚠️ 优先级：`data-component` 属性 > 注释**。demo 文件顶部的注释可能过期，字段类型以实际 `data-component` 属性为准。
     ```tsx
     // 示例：注释写 Slider，但实际是 LRProgressBar
     // 注释：m_ConditionBar: Slider  ❌ 过期信息
     <div data-component="control.progress" data-field="m_ConditionBar" />  ✅ 实际组件
     ```
   - **组件类型**：demo 里的 `data-component="list.single-scroll"` 对应项目封装 `SingleScrollView`，不是原生 `ScrollRect`
   - **字段名和类型**：demo 里的 `data-field="m_ScrollRewards"` 必须和 C# 里的 `[SerializeField]` 字段名完全一致
   - **嵌套组件结构**：demo 里的 `data-field="m_FreeCell"` 指向的子组件，其内部字段（如 `m_BtnClaim`）在该子组件的 C# 脚本里声明，不在父组件里
   - **模板克隆模式**：demo 里 `data-visible="false"` 的模板节点，`Instantiate` 克隆后必须手动 `SetActive(true)`

3. **禁止行为**
   - ❌ 跳过 demo 直接根据 `design/ui.md` 的文字描述写代码（ui.md 是抽象描述，demo 才是可执行的具体配置）
   - ❌ 看到 `list.scroll` 就写 `ScrollRect`，看到 `list.single-scroll` 也写 `ScrollRect`（必须查项目源码确认对应的封装类型）
   - ❌ 照抄其他页面的字段名（每个 prefab 的序列化字段名可能不同，以 demo 为准）

**常见组件映射表**（通过 demo 里的 `data-component` 属性识别）：

| demo 标签 | 项目组件类型 | 继承关系 | 备注 |
|----------|------------|---------|------|
| `list.scroll` | `ScrollView` | 继承 `ScrollRect` | 通用滚动列表基类 |
| `list.single-scroll` | `SingleScrollView` | 继承 `ScrollView` | 单列/单行滚动列表（项目封装） |
| `control.progress` | `LRProgressBar` | `MonoBehaviour` | 项目进度条组件，用 `.progress` 属性（0-1）设置进度 |
| `content.async-image` | `AsyncImage` | 继承 `Image` | 异步加载图片组件 |
| `feedback.red-point` | `RedPoint` | 自定义组件 | 红点提示组件 |

**如果 demo 目录不存在或为空**，说明该功能的 UI prefab 已由策划/美术在 Unity Editor 里手工搭建完成，你需要：
1. 在客户端工程 `../develop/client/project/Assets/Resources/` 下搜索对应 prefab
2. 用 Unity Editor 打开 prefab，查看已序列化的字段名和组件类型
3. 或参考同类型功能的已有实现（用 CodeGraph 查询 `BaseActivityPage` 的子类）

---

**⚠️ 强制规则：UI 文案必须走语言表 key，禁止硬编码字符串（生成时就地替换）**

生成/修改 UI 脚本代码时，任何形如 `m_TxtXxx.text = "中文文案"` 的硬编码字符串赋值，必须在生成阶段直接替换为语言表 key 调用，不写完代码后再扫描修复。

1. **API 选择**
   - 无参文案：`"{key}".ToLanguage()`（对应 `HelperExtend.cs`，底层 `TDLanguageTable.Get(key)`）
   - 带参文案（文案里有变量，如"需要达到{0}级"）：`"{key}".ToLanguageF(arg1, arg2, ...)`
     参考 `ItemUseBtnData.cs:184`：
     ```csharp
     FloatMessage.S.ShowError("Msg_ItemUse_LevelNotFit".ToLanguageF(itemData.levelLimit));
     ```
   - 不要用 `TableToLanguage()` / `TableToLanguageF()`（`TableUseHelperExtend.cs` 里的旧版本，功能相同但项目里优先用 `HelperExtend.cs` 的 `ToLanguage`/`ToLanguageF`）

2. **key 命名规则**：`UI_<PanelName>_<NodeName>`
   - `PanelName` = 当前 UI 脚本类名（如 `MixGrowthFundPage`）
   - `NodeName` = 字段名去掉 `m_Txt`/`m_Lbl` 等前缀（如 `m_TxtBtnPurchase` → `BtnPurchase`）
   - **NodeName 太长时按寓意缩写**，不要死板保留全名。例如 `m_TxtRewardConditionDescription` 不要写成 `UI_XXX_RewardConditionDescription`，缩写成 `UI_XXX_CondDesc` 或 `UI_XXX_Condition`（取能表达含义的最短形式）
   - 一个字段有多个文案分支（三元表达式/switch）时，每个分支单独一个 key，NodeName 加状态后缀：
     ```csharp
     // ❌ 错误：硬编码
     m_TxtBtnPurchase.text = isPurchased ? "已购买" : "购买";

     // ✅ 正确：分支各自建 key
     m_TxtBtnPurchase.text = isPurchased
         ? "UI_MixGrowthFundPage_BtnPurchase_Purchased".ToLanguage()
         : "UI_MixGrowthFundPage_BtnPurchase_Buy".ToLanguage();
     ```

3. **去重规则（范围限定在本次 change 内，不扫全项目语言表）**
   - 生成前先读取 `changes/{change-id}/Language_Keys.md`（如果不存在则视为空表）
   - 新文案先按 **Default Text 全字匹配** 检查是否已有相同文案的 key，命中则直接复用该 key，不新建
   - 未命中才按上面规则生成新 key
   - **不要跨 change 扫描项目已有语言表**去重（避免误判：文案偶然相同但业务语义不同的两个 key 被错误合并）

4. **`Language_Keys.md` 记录格式**：
   ```markdown
   | Key | Default Text |
   |-----|---------------|
   | UI_MixGrowthFundPage_BtnPurchase_Buy | 购买 |
   | UI_MixGrowthFundPage_BtnPurchase_Purchased | 已购买 |
   ```
   - 每替换一处硬编码文案，立即追加一行并写回文件（不要攒到最后一次性写，防止 apply 中断丢失记录）
   - 这份文件是**待导入语言表的清单**，交给策划/美术后续导入 `language.xlsx`，不是最终生效的语言配置

---

## 4. 客户端代码执行主流程

1. 读取 `design/client.md` 对应章节
2. 用 CodeGraph 查询客户端代码模板（如 `ILogicModule`、`BaseActivityPage`）
3. 生成客户端代码（模块、UI Panel、协议收发）

---

## 5. 客户端编码规范引用

**生成客户端 C# 代码前，必须阅读并遵守项目编码规范：**

规范入口（相对于客户端工程根目录）：
```
docs/ai-core/rules/coding_standards/README.md
```

**必读文件清单**（相对 `docs/ai-core/rules/coding_standards/`，以各原文件为准）：
- `csharp_spec.md` — 基础编码规范（如 `m_` 前缀、类内成员排列顺序、数据结构类的公有变量原则等）
- `csharp_safe.md` — 保护规范（如判空、越界、生命周期管理）
- `csharp_gc.md` — GC 优化规则（如避免 foreach 装箱、慎用 LINQ、字符串拼接用 StringBuilder 等）
- `csharp_comment.md` — 注释规范（尤其 UI 面板 `OnOpen` 参数注释）
- `csharp_self.md` — 个人代码风格（参数命名、partial 拆分、模块门面、Define 等）
- 通用 UI/逻辑要求见 `csharp_func_dev.md`

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
   生成代码后，立即运行 `dotnet build` 检查编译错误（由 apply SKILL 主流程统一触发，不在本文件重复描述）。

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

---

## 6. [Integration] 联调验证

**不生成代码**，输出提示：
```
⚠️ Integration 任务是人工验证清单，不支持代码生成。
   请按 test-cases.md 对应的 TC 逐项验证。
```

---

**版本**: v1（从 lr-openspec-apply/SKILL.md 迁移）
**最后更新**: 2026-08-06
**维护原则**: 只包含"apply 阶段客户端执行"的强制流程；代码模板通过 CodeGraph/知识库索引获取；外部工程规范以 `develop/client/project/AGENTS.md` 为唯一权威来源，本文件不重复维护其内容
