---
name: lr-openspec-ui-prefab
description: 根据已验收的 React 原型 + lr-openspec-apply 生成的 UI 脚本，生成 Unity UI Prefab 的中间数据（TSX），校验字段完整性后交给 Unity 常驻生成器一次性构建 GameObject 树、挂载组件、绑定序列化字段。强制使用 TextMeshPro。
---

# OpenSpec UI Prefab 生成器

## 功能定位

在 `/lr-openspec-apply` 执行完客户端 UI 任务后，把已经拍板的设计**重新用 Unity 精确语言表达一遍**，再交给确定性程序生成 Prefab——本技能不做新的设计决策。

输入三样：

1. **策划已验收的 React 原型**（`changes/<id>/demo/src/**/*.tsx`，`lr-design` 产出，只读，视觉/交互基准）
2. **C# 脚本的 `[SerializeField]` 字段清单**（`lr-openspec-apply` 已生成，这是硬约束，不是参考）
3. **组件白名单**（`.claude/skills/lr-design/references/unity-ui-components.md`，已通过 MCP 扫描项目真实 Prefab 生成）

输出两样：

1. `changes/<id>/demo/unity/*.tsx`——每个需要生成 Prefab 的脚本对应一个 TSX 文件，字段驱动而非原型驱动（demo 里没画出来的状态元素，只要 C# 里有对应字段，也必须在 TSX 里补出节点）
2. Unity Prefab（`Assets/Resources/PanelUI/*.prefab`），脚本已挂载、序列化字段已绑定

## 为什么不直接生成 Prefab

Web 原型是"视觉稿"，Unity Prefab 需要的是"精确数据"（anchor/pivot/pos/size、组件类型、字段绑定），两者之间存在语义鸿沟——从 HTML/CSS 推断这些数据不可靠（命名映射会断裂、状态元素会被忽略、Cell 复用逻辑推不出来）。

参照社区已验证的方案（AI 生成 React/TSX 中间格式 → 固定程序转 Prefab，而非 AI 直接操作 Prefab 或靠 CSS 反推布局），本技能分两段：

- **AI 只做一次性的事**：把设计意图翻译成 TSX（AI 擅长生成 React/TSX，且可用于人工 review）
- **固定程序做剩下的事**：TSX → JSON → 一次 MCP 调用，在 C# 里循环建树、加组件、复用框架预制件、反射绑定字段——过程中不再有 AI 参与，结果确定，速度快，不会因节点数增多而变慢变贵

不逐节点调用 MCP 工具搭 Prefab（那等于把"AI 直接拼 Prefab"的老问题换个马甲：AI 仍然参与了 O(n) 次操作）。

## 使用方式

### 前置条件

1. ✅ 已运行 `/lr-design <id>` 生成并验收 Web 原型
2. ✅ 已运行 `/lr-openspec-apply <id> client` 生成 UI 脚本（`[SerializeField]` 字段已定稿）
3. ✅ Unity 客户端项目已安装 **ai-game-developer MCP**，且 Editor 正在运行

### 执行命令

```bash
/lr-openspec-ui-prefab <change-id>
```

## 工作流程

### 步骤 0：验证 Unity MCP 连接

调用 `mcp__ai-game-developer__editor-application-get-state`：

- ✅ 成功且 `IsCompiling: false`：继续
- ❌ 调用失败或超时：

  ```text
  ❌ Unity Editor 未连接

  请确保：
  1. Unity Editor 已启动（项目：<客户端项目路径>）
  2. ai-game-developer MCP 插件已安装并运行
  3. 没有正在进行的编译（IsCompiling 应为 false）
  ```

  停止执行，不生成任何 TSX 或 Prefab。

- ⚠️ `IsCompiling: true`：等待编译完成后重新调用，不在编译中执行后续步骤。

### 步骤 1：收集字段清单（硬约束）

从 `changes/<id>/tasks.md` 找到 UI 相关任务对应的 C# 脚本路径，**只提取继承自 AbstractPage/BasePage 的脚本**（如 `MixGrowthFundPage.cs`），读取其所有 `[SerializeField]` 字段及其类型：

```csharp
public class MixGrowthFundPage : BaseActivityPage  // ✅ 继承 Page，需要生成 Prefab
public class MixGrowthFundRewardCell : MonoBehaviour  // ❌ 普通 MonoBehaviour，不生成独立 Prefab
```

**判断规则**：
- ✅ 继承 `AbstractPage` / `BasePage` / `BaseActivityPage` 等 Page 基类 → 生成独立 Prefab，注册在 UIDataTable
- ❌ 继承 `MonoBehaviour` → 不生成独立 Prefab，作为嵌套组件在 Page 的 TSX 内部定义

产出字段清单（**每个字段都必须在步骤 3 生成的 TSX 中出现**，不允许挑着画）：

```text
MixGrowthFundPage.cs (BaseActivityPage):
  m_TitleText: TextMeshProUGUI
  m_BuyButton: Button
  m_RewardRowTemplate: MixGrowthFundRewardTierRow  ← 运行时实例化的模板，在 Page TSX 内部定义
  ...
```

### 步骤 2：读取策划原型与组件白名单

只读，不修改：

- `changes/<id>/demo/src/**/*.tsx`——理解已验收的视觉方向、层级关系、文案（React 组件源码，包括拆分的独立组件），**但跳过 `src/components/DebugConsole.tsx`**（`lr-design` 强制产出的调试专用组件，不承载任何业务视觉或状态语义，不纳入分析）
- `changes/<id>/demo/dist/index.html`（可选）——构建后的静态 HTML，用于坐标测量
- `.claude/skills/lr-design/references/unity-ui-components.md`——语义组件 ID 白名单
- [unity-layout-attributes.md](references/unity-layout-attributes.md)——TSX 的 `data-*` 属性规范（本技能专用）

### 步骤 3：生成 TSX

**只为继承 Page 基类的脚本生成 TSX 文件**。产出位置：`changes/<id>/demo/unity/<PageClassName>.tsx`（如 `MixGrowthFundPage.tsx`）。

**MonoBehaviour 组件（如 Cell/Row）不生成独立 TSX**，而是在 Page 的 TSX 内部直接定义其层级结构（作为模板节点，运行时通过 `Instantiate` 复用）。

生成规则：

1. 严格遵守 [unity-layout-attributes.md](references/unity-layout-attributes.md)——布局只用 `data-pos`/`data-size`/`data-anchors`/`data-pivot`，不用 CSS。
2. **以步骤 1 的字段清单为清单式约束**：每个字段生成一个带 `data-field` 的节点。demo 里没有对应视觉元素的字段（如"已购买标记"），补一个节点，可标 `data-visible="false"`，但节点和 `data-field` 必须存在。
3. 组件类型只能用白名单里的语义 ID，找不到合适 ID 时停下来问，不要发明新 ID。
4. 需要复用项目已有框架组件内部结构（如 `list.single-scroll` 的 `Viewport/Content`）时用 `data-prefab-child-path`。
5. **MonoBehaviour 组件字段（如 `MixGrowthFundRewardTierRow m_RewardRowTemplate`）**：在 Page TSX 内部展开该组件的完整层级结构，绑定其所有字段到对应节点，作为运行时实例化的模板。
6. 视觉细节（图片、圆角、渐变、阴影）不翻译；配套 CSS 只用于基础预览识别。
7. **只有 Page 根节点**画布尺寸固定 `data-size="(1920, 1080)"`；嵌套组件容器根据实际需要设置尺寸。

发现 React 原型与 C# 字段之间存在结构性矛盾时（比如脚本要三个领取按钮但原型只有一个入口），停止生成，回报使用者，不静默拍板改设计。

### 步骤 4：校验

```bash
python .claude/skills/lr-openspec-ui-prefab/scripts/validate_unity_layout.py \
  changes/<id>/demo/unity \
  --csharp <path/to/GrowthFundPage.cs> \
  --csharp <path/to/GrowthFundRewardCell.cs>
```

校验内容（详见脚本头部注释）：TSX 解析、`data-name` 唯一性、组件白名单、必填 `data-pos`/`data-size`、枚举值合法性、越界与重叠检测、**字段完整性**（每个 `[SerializeField]` 字段必须有且只有一个 `data-field` 对应，缺一个报错，不是警告）。

有错误就回到步骤 3 修，直到零错误。**字段完整性错误不允许绕过**——这是本技能与知乎/UI_React_Spec 方案的关键差异点：那些方案没有对接固定的 `[SerializeField]` 清单，本项目有，所以补上这条硬校验。

### 步骤 5：转换为 JSON

```bash
python .claude/skills/lr-openspec-ui-prefab/scripts/tsx_to_json.py changes/<id>/demo/unity/GrowthFundPanel.tsx
```

只在步骤 4 零错误后执行；此脚本不重新校验，信任输入已经是合法的。

### 步骤 6：部署生成器脚本到 Unity 项目

生成器源码（5 个 `.cs` + 11 个配方 `.json`）平时不常驻 Unity 项目，只在生成 Prefab 时临时部署，用完即删——源码始终以 `.claude/skills/lr-openspec-ui-prefab/scripts/lr_ui_gen/` 为唯一真相源，不要直接改 Unity 项目里部署出来的副本。

```bash
python .claude/skills/lr-openspec-ui-prefab/scripts/deploy_lr_ui_gen.py <unity-project-root>
```

部署脚本是幂等的：如果目标目录 `Assets/Editor/LRUIPrefabGen/` 已存在（比如上次执行中断留下的残留），会先删除再重新复制，不会合并冲突。

部署完成后：

1. 调用 `mcp__ai-game-developer__assets-refresh` 让 Unity 感知新文件
2. 轮询 `mcp__ai-game-developer__editor-application-get-state` 直到 `IsCompiling: false`（不要在编译中调用步骤 7 的生成器，会拿到未编译完成的旧类型或直接调用失败）

### 步骤 7：调用 Unity 生成器

用 `mcp__ai-game-developer__reflection-method-call` 调用刚部署的 Editor 脚本 `LRUIPrefabGen.LRUnityLayoutPrefabGenerator.GenerateFromLayout`：

```json
{
  "filter": {
    "typeName": "LRUIPrefabGen.LRUnityLayoutPrefabGenerator",
    "methodName": "GenerateFromLayout"
  },
  "knownNamespace": true,
  "inputParameters": [
    {"name": "jsonPath", "typeName": "System.String", "value": "D:/se/openspec/changes/growth-fund/demo/unity/GrowthFundPanel.json"},
    {"name": "prefabPath", "typeName": "System.String", "value": "Assets/Resources/PanelUI/GrowthFundPanel.prefab"},
    {"name": "rootScriptTypeName", "typeName": "System.String", "value": "LR.GrowthFundPage"}
  ]
}
```

一个 Prefab 一次调用，内部循环建树、加组件、绑字段全部在这一次 C# 执行里完成，AI 不逐节点操作。`rootScriptTypeName` 传 `null` 表示只生成层级不挂脚本（用于 Cell 类不需要挂根脚本的场景，字段绑定改为在父 Prefab 生成时通过 `data-prefab-asset-path` 整体引用）。

### 步骤 7：验证结果

1. 用 `mcp__ai-game-developer__gameobject-find` 或打开 Prefab 检查层级是否符合预期。
2. 用 `mcp__ai-game-developer__screenshot-isolated` 截图确认视觉效果。
3. 检查 Unity Console 是否有 `LRComponentRecipes`/`LRFieldBinder` 的 Warning（说明某个语义 ID 或字段没找到对应实现，需要回头修 TSX 或补白名单/生成器逻辑）。
4. 向使用者报告：生成了哪些 Prefab、绑定了多少字段、有哪些遗留 Warning。

### 步骤 8：清理部署的生成器脚本

生成和验证完成后，删除步骤 6 部署到 Unity 项目的临时脚本，恢复项目干净状态：

```bash
python .claude/skills/lr-openspec-ui-prefab/scripts/cleanup_lr_ui_gen.py <unity-project-root>
```

清理完成后调用 `mcp__ai-game-developer__assets-refresh`，让 Unity 感知删除。

如果执行过程中断（AI 会话被压缩/用户中止/MCP 超时），下次运行步骤 6 时部署脚本会自动清理上次残留，所以不需要专门手动清理孤儿文件。

## 常见问题处理

### Unity Console 出现 `未找到类型: LR.xxx`

说明 `unity-ui-components.md` 里记录的 LR 组件类名与项目实际类名不一致（比如命名空间变了）。回头核实真实类名，更新 `LRComponentRecipes.cs` 里对应的 `AddLRComponent` 调用参数，而不是改 TSX。

### 校验器报字段绑定缺失

说明 TSX 里少画了一个节点。回到步骤 3，为该字段补一个节点（哪怕是隐藏占位），不要绕过校验。

### 图片资源

`sprite`/图片路径允许留空，交给美术后续在 Unity 里替换；节点本身和字段绑定不允许因为"没有图片"而省略。

### 需要新增语义组件 ID

不在本技能范围内直接扩充。回到 `lr-design` 的 `unity-ui-components.md` 维护流程：先用 MCP 扫描确认真实 Prefab 配方，再人工评审加入白名单，然后同步更新 `LRComponentRecipes.cs` 里的 `switch` 分支。

## 版本信息

**版本**: v2.0（TSX 中间格式 + 固定程序生成）

**依赖 SKILL**：
  - `/lr-design`——生成并验收 Web 原型，产出 `unity-ui-components.md` 白名单
  - `/lr-openspec-apply`——生成 UI 脚本（`[SerializeField]` 字段清单来源）

**依赖工具**：
  - ai-game-developer MCP（Unity 插件）
  - 项目常驻脚本：`Assets/Editor/LRUnityLayoutPrefabGenerator.cs`、`LRComponentRecipes.cs`、`LRFieldBinder.cs`（namespace `LRUIPrefabGen`）

**依赖配置**：
  - `.claude/skills/lr-design/references/unity-ui-components.md`——组件映射 + 默认样式
  - [references/unity-layout-attributes.md](references/unity-layout-attributes.md)——TSX 布局属性规范
