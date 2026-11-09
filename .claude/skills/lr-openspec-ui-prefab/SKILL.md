---
name: lr-openspec-ui-prefab
description: 根据已验收的 React 原型 + lr-openspec-apply 生成的 UI 脚本，生成 Unity UI Prefab 的中间数据（TSX），校验字段完整性后交给临时部署的 Unity 生成器一次性构建 GameObject 树、挂载组件、绑定序列化字段。强制使用 TextMeshPro。 SE UI 优先 ai-game-developer MCP。
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

参考侦察启用时（步骤 2.5）还会额外产出 `changes/<id>/demo/unity/references.json` 和 `reference-notes.md`；没有同功能参考、使用模块级风格档案时（步骤 2.6）还会产出 `ui-style-profile.json` 和 `ui-style-profile.md`。这些是生成过程的审计/参考记录，不是新的设计输入。

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
3. ✅ 优先使用 SE 客户端的 **ai-game-developer MCP** 和已启动 Editor；只有确认不可用或能力不足时才按 CLI 兜底处理

### 执行命令

```bash
/lr-openspec-ui-prefab <change-id>
```

## 工作流程

### 步骤 0：确认 SE 工程并验证 ai-game-developer MCP（优先）

完整读取 OpenSpec 根目录的 `schemas/lr-func-dev/rules/common/unity-ui-mcp.md`。从 `config.yaml` 解析客户端路径，先查 Editor 状态，再用已发现的反射 getter 查询 `Application.dataPath`，确认连接指向 SE 的 `Assets`；不要仅凭窗口标题、Unity 版本或连接成功选择目标。

- MCP 可用且身份匹配：继续走下述 MCP 主流程；按步骤 2.5 用 MCP + 参考扫描器读取 SE 参考 Prefab/组件及截图。
- 正在编译/导入：等待后复查，不为绕过等待切换 CLI。
- 调用失败、目标不匹配或无法确认身份：记录具体错误，停止 Unity 写入；只有确实没有可用 SE MCP 或能力不支持时，才按“CLI 兜底”处理，不写入其他工程。

### 步骤 1：收集字段清单（硬约束）

从 `changes/<id>/tasks.md` 找到 UI 相关任务对应的 C# 脚本路径，**只提取继承自 AbstractPage/BasePage 的脚本**（如 `MixGrowthFundPage.cs`），读取其所有 `[SerializeField]` 字段及其类型：

```csharp
public class MixGrowthFundPage : BaseActivityPage  // ✅ 继承 Page，需要生成 Prefab
public class MixGrowthFundRewardCell : MonoBehaviour  // ❌ 普通 MonoBehaviour，不生成独立 Prefab
```

**判断规则**：
- ✅ 继承 `AbstractPage` / `BasePage` / `BaseActivityPage` 等 Page 基类 → 生成独立 Prefab，注册在 UIDataTable
- ❌ 继承 `MonoBehaviour` → 不生成独立 Prefab，作为嵌套组件在 Page 的 TSX 内部定义

产出字段清单（**每个可绑定引用字段都必须在步骤 3 生成的 TSX 中出现，数据值字段单独标注豁免**，不允许挑着画）：

```text
MixGrowthFundPage.cs (BaseActivityPage):
  m_TitleText: TextMeshProUGUI
  m_BuyButton: Button
  m_RewardRowTemplate: MixGrowthFundRewardTierRow  ← 运行时实例化的模板，在 Page TSX 内部定义
  ...
```

### 步骤 1.5：从 SE UIDataTable 确定输出路径（硬约束）

从 SE `Assets/Script/LogicModule/UIModule/Data/UIDataTable.cs` 为每个 Page 查询 `AddPanelData` 的第三个参数 `pName`。输出必须是 `Assets/Resources/PanelUI/{pName}.prefab`，保留其中的模块子目录，不能只按类名平铺。

记录每个 Page 的完整脚本类型、pName、Prefab 路径及可绑定字段清单。注册缺失时报告阻断，不猜路径、不自动跨阶段补注册。MCP 和 CLI 均复用这份逐页清单，不使用假定统一目录的批量入口。

### 步骤 2：读取策划原型与组件白名单

只读，不修改：

- `changes/<id>/demo/src/**/*.tsx`——理解已验收的视觉方向、层级关系、文案（React 组件源码，包括拆分的独立组件），**但跳过 `src/components/DebugConsole.tsx`**（`lr-design` 强制产出的调试专用组件，不承载任何业务视觉或状态语义，不纳入分析）
- `changes/<id>/demo/dist/index.html`（可选）——构建后的静态 HTML，用于坐标测量
- `.claude/skills/lr-design/references/unity-ui-components.md`——语义组件 ID 白名单
- [unity-layout-attributes.md](references/unity-layout-attributes.md)——TSX 的 `data-*` 属性规范（本技能专用）

### 步骤 2.5：参考侦察（MCP 可用时强烈建议）

目的：写 TSX 前，用 SE 真实 Prefab 回答两个问题——"同类面板的骨架/命名/组件是什么"、"项目里这个角色通常用什么样式"。参考是翻译词典，不是新设计。

1. **找候选（最多 3 个）**：
   - 优先复用 `lr-design` 原型交付说明中已记录的参考 Prefab 路径；
   - 其次在步骤 1.5 的输出目录（同模块/同功能目录）下用 `assets-find`（`t:Prefab`）查找；
   - 再次从页面类名/change id 提取功能关键词，在 `Assets/Resources/PanelUI` 下搜索；
   - 只选结构/用途相近的；找不到就跳过，并记录"未做实时参考"。

2. **扫描（只读）**：
   - 写 `changes/<id>/demo/unity/reference-input.json`：
     ```json
     { "prefabPaths": ["Assets/Resources/PanelUI/.../Xxx.prefab"] }
     ```
   - 部署扫描器 + 生成器（幂等；扫描器在步骤 6 继续复用）：
     ```bash
     python .claude/skills/lr-openspec-ui-prefab/scripts/deploy_lr_ui_gen.py <SE工程根>
     ```
   - 调用 `mcp__ai-game-developer__assets-refresh`，轮询 `editor-application-get-state` 直到 `IsCompiling: false`；
   - 用 `reflection-method-find` 查找 `LRUIPrefabGen.LRPrefabReferenceScanner.Scan`，按返回的真实参数 schema 调 `reflection-method-call`；参数是输入/输出 JSON 的**绝对路径**；
   - MCP 反射不可用但编辑器可用时，部署后可从 `Tools/LR/Scan Reference Prefabs...` 菜单手动扫描；
   - 产出 `changes/<id>/demo/unity/references.json`。

3. **写结论**：`changes/<id>/demo/unity/reference-notes.md` 至少包含：
   - 候选路径、选中项、选择理由；
   - 结构结论：骨架、命名、组件组合、模板位置；
   - 样式映射：角色 → `data-lr-style` 或具体覆盖值；
   - 每个具体覆盖的理由；
   - 未决/冲突/低置信度项。

4. **置信度**：显式指定 / 同模块目录 / 名称强匹配 → 直接进入步骤 3；候选互相矛盾或只有弱匹配 → 自动选置信度最高的候选，在 `reference-notes.md` 记录冲突与低置信度，继续步骤 3，不打断。

5. **失败处理**：MCP/扫描器不可用、无候选或扫描失败 → 跳过参考侦察，继续用白名单默认值生成；在 `reference-notes.md` 记录失败原因，不阻断。

### 步骤 2.6：模块级风格档案（没有同功能参考时）

参考优先级：**同功能现网 Prefab > 模块级风格档案 > 白名单默认值**。

如果当前需求没有对应的现网 Prefab（新面板/新活动），不要直接套白名单默认值。先从同模块找 3–5 个同类界面，聚合出模块风格档案：

1. 用 `assets-find`（`t:Prefab` + 同模块目录）选 3–5 个同类面板；优先弹窗，尽量覆盖标题、按钮、窗口框。
2. 写入 `reference-input.json`，用步骤 2.5 的扫描器产出 `references.json`。
3. 运行：
   ```bash
   python .claude/skills/lr-openspec-ui-prefab/scripts/build_ui_style_profile.py \
     changes/<id>/demo/unity/references.json \
     --module <模块名> \
     -o changes/<id>/demo/unity/ui-style-profile.json \
     --markdown changes/<id>/demo/unity/ui-style-profile.md
   ```
4. review `ui-style-profile.md` 的角色值：
   - `modal.header`（弹窗标题）
   - `page.title`（页面标题）
   - `body`（正文/描述）
   - `price`（价格）
   - `button.primary` / `button.secondary` / `button.close`
   - `window.frame`（窗口框）
   - `divider`（分割线）
   - `screen`（遮罩）
5. 在步骤 3 中按角色套用：结构/命名以参考 Prefab 为准；同功能参考与模块档案冲突时，**同功能参考优先**；仍无法解释的差异写进 `reference-notes.md`。

风格档案是参考，不是硬约束；某个角色的高频值不一定适合当前面板，最终以已验收原型 + 同功能参考为准。

### 步骤 3：生成 TSX

**只为继承 Page 基类的脚本生成 TSX 文件**。产出位置：`changes/<id>/demo/unity/<PageClassName>.tsx`（如 `MixGrowthFundPage.tsx`）。

**MonoBehaviour 组件（如 Cell/Row）不生成独立 TSX**，而是在 Page 的 TSX 内部直接定义其层级结构（作为模板节点，运行时通过 `Instantiate` 复用）。

生成规则：

1. 严格遵守 [unity-layout-attributes.md](references/unity-layout-attributes.md)——布局只用 `data-pos`/`data-size`/`data-anchors`/`data-pivot`，不用 CSS。
2. **以步骤 1 的字段清单为清单式约束**：每个可绑定的对象引用生成一个带 `data-field` 的节点，一维数组使用从 0 开始的连续下标。数值、字符串、纯数据类和运行时集合不生成绑定节点；不能把 `List<T>` 或 `UnityEngine.Object` 直接写成 `data-field`，当前 FieldBinder 不支持它们。demo 里没有对应视觉元素的引用字段（如"已购买标记"），补一个节点，可标 `data-visible="false"`，但节点和 `data-field` 必须存在。
3. 组件类型只能用白名单里的语义 ID，找不到合适 ID 时停下来问，不要发明新 ID。
4. 需要复用项目已有框架组件内部结构（如 `list.single-scroll` 的 `Viewport/Content`）时用 `data-prefab-child-path`。
5. **MonoBehaviour 组件字段（如 `MixGrowthFundRewardTierRow m_RewardRowTemplate`）**：在 Page TSX 内部展开该组件的完整层级结构，绑定其所有可绑定引用字段到对应节点，作为运行时实例化的模板。展开时同样要对照 demo 里对应组件（如 `MonthCard.tsx`）的完整视觉内容，不能只按字段清单画节点——字段清单保证"有引用字段的节点不缺"，但 demo 里存在、没有对应字段的纯展示文案（如分组小标题）依然要画出来，不能因为找不到 `data-field` 就跳过。
6. 视觉细节（图片、圆角、渐变、阴影）不翻译；配套 CSS 只用于基础预览识别。
7. **只有 Page 根节点**画布尺寸固定 `data-size="(1920, 1080)"`；嵌套组件容器根据实际需要设置尺寸。
8. **先读步骤 2.5/2.6 的 `reference-notes.md` 和 `ui-style-profile.md`**：结构、命名、组件组合以参考 Prefab 为依据；样式优先同功能参考，其次模块档案的角色值，最后 `data-lr-style`/白名单默认值。模块档案存在时，给标题/正文/价格/按钮/窗口框/分割线/遮罩节点写 `data-role`（角色白名单见 [unity-layout-attributes.md](references/unity-layout-attributes.md)），不要手工抄 profile 数值。
   - 弹窗底框单独画：在 `Window` 下增加一个 `Bg` 节点，`data-component="content.async-image"` + `data-role="window.frame"`，由 profile 提供 texture；不要把 `Window` 容器本身当作底框。底框节点已有 RawImage 时生成器不会再注入深色占位 Image。
   - 参考 Prefab 有分割线时，画 `data-component="content.divider"` + `data-role="divider"` 节点；不要省略。
9. **具体样式覆盖只用于 `data-role`/命名变体表达不了的差异**：使用 `data-font-size`/`data-color`/`data-font`/`data-font-material`/`data-sprite`/`data-image-type`/`data-texture`/`data-image-color`/`data-preserve-aspect` 时，必须在 `reference-notes.md` 记录理由；每个覆盖属性必须能作用于真实组件（见 [unity-layout-attributes.md](references/unity-layout-attributes.md) 的目标规则）。
10. **`data-color` 优先作为文本颜色**；无文本目标时作为图片颜色别名，`data-name="Screen"` 的遮罩节点映射到生成的 Screen Image 颜色；图片颜色仍优先显式写 `data-image-color`。`data-text-align` 与 `data-vertical-align` 可以单独使用（单独使用时保留另一轴），同时写则两者都覆盖；`RawImage` 支持 `data-image-color` 和 `data-texture`。

发现 React 原型与 C# 字段之间存在结构性矛盾时（比如脚本要三个领取按钮但原型只有一个入口），停止生成，回报使用者，不静默拍板改设计。参考 Prefab 之间、或参考与原型之间的**样式**冲突无法用命名样式解释时，不阻断：按同功能参考 > 模块档案 > 白名单默认值取舍，并把冲突和取舍写进 `reference-notes.md`。

### 步骤 4：校验

```bash
python .claude/skills/lr-openspec-ui-prefab/scripts/validate_unity_layout.py \
  changes/<id>/demo/unity \
  --csharp <path/to/GrowthFundPage.cs> \
  --csharp <path/to/GrowthFundRewardCell.cs>
```

校验内容（详见脚本头部注释）：TSX 解析、`data-name` 唯一性、组件白名单、必填 `data-pos`/`data-size`、枚举值合法性、越界与重叠检测、**字段完整性**（每个可由 FieldBinder 绑定的引用字段都必须有对应 `data-field`；普通字段只能绑定一次，数组逐元素绑定，重复 Cell 在各自作用域检查；数值、字符串及纯数据类不强求 GameObject 绑定），以及**样式覆盖契约**：`data-lr-style` 变体必须存在、文本/图片覆盖必须有可消费目标、字体/材质/贴图路径前缀合法、颜色为 4 个 0..1 分量、`data-text-align`/`data-vertical-align` 成对出现、`RawImage` 只接受 `data-image-color`。

字段解析支持附加/合并 attribute 及非 `m_` 名称。数组在 TSX、JSON 两级均拒绝空洞和重复下标；类型核对只认同节点的配方组件、后处理产物和显式挂载组件，不把子节点组件当作根节点组件。`List<T>` 等不支持的集合显式绑定报错。提供的 C# 可用于解析自定义继承；输出“需 MCP 验证”的项目，以及已有 Prefab 引用、未提供完整继承链的类型，必须在步骤 7.5 核对真实对象类型与磁盘序列化引用，不能将静态通过当成绑定已完成。

有错误就回到步骤 3 修，直到零错误。**字段完整性错误不允许绕过**——这是本技能与知乎/UI_React_Spec 方案的关键差异点：那些方案没有对接固定的 `[SerializeField]` 清单，本项目有，所以补上这条硬校验。

### 步骤 5：转换为 JSON

```bash
python .claude/skills/lr-openspec-ui-prefab/scripts/tsx_to_json.py \n  changes/<id>/demo/unity/GrowthFundPanel.tsx \n  --profile changes/<id>/demo/unity/ui-style-profile.json
```

只有步骤 2.6 产出 `ui-style-profile.json` 时才传 `--profile`；没有 profile 且 TSX 写了 `data-role` 时转换器会给警告，角色样式不展开。转换产物是含 `name` / `component` / `children` 的节点树，与 C# 生成器一致；不是 `rootName/fields/hierarchy` 包装对象。带 profile 时每个角色节点还会写 `_styleSources`，标明样式键来自 `tsx` 还是 `profile:<role>`；生成器忽略这些元数据，只读已物化的显式键。

随后运行 `python .claude/skills/lr-openspec-ui-prefab/scripts/validate_layout_json.py <输出.json> --project-root <unity-project-root>`（项目根取自步骤 1 的 `config.yaml`）；失败先修复，不部署或调用 Unity。提供项目根时，门禁还会检查 `font`/`fontMaterial`/`sprite`/`texture` 指向的资源真实存在，错误目录不再拖到 Unity 里才由自动修复兜底。

### 步骤 6：部署生成器脚本到 Unity 项目

生成器源码（以 `scripts/lr_ui_gen/` 实际清单为准，包含参考扫描器、可选 CLI 入口）平时不常驻 Unity 项目，只在参考侦察/生成 Prefab 时临时部署，用完即删——源码始终以 `.claude/skills/lr-openspec-ui-prefab/scripts/lr_ui_gen/` 为唯一真相源，不要直接改 Unity 项目里部署出来的副本。步骤 2.5 已部署过时，本步骤可跳过或幂等重跑。

```bash
python .claude/skills/lr-openspec-ui-prefab/scripts/deploy_lr_ui_gen.py <unity-project-root>
```

部署脚本是幂等的：如果目标目录 `Assets/Editor/LRUIPrefabGen/` 已存在（比如上次执行中断留下的残留），会先删除再重新复制，不会合并冲突。

部署完成后：

1. 调用 `mcp__ai-game-developer__assets-refresh` 让 Unity 感知新文件
2. 轮询 `mcp__ai-game-developer__editor-application-get-state` 直到 `IsCompiling: false`（不要在编译中调用步骤 7 的生成器，会拿到未编译完成的旧类型或直接调用失败）

### 步骤 7：调用 Unity 生成器

保持步骤 0 已确认的 SE 连接。先用 `reflection-method-find` 查找 `LRUIPrefabGen.LRUnityLayoutPrefabGenerator.GenerateFromLayout`，按返回的真实参数 schema 调 `reflection-method-call`，不要复制旧的 filter 或猜测参数。

三个参数分别为：
- `jsonPath`：从 OpenSpec 根目录解析得到的 JSON **绝对路径**（Unity 的工作目录不同）。
- `prefabPath`：步骤 1.5 从 UIDataTable 查到的 `Assets/Resources/PanelUI/{pName}.prefab`。
- `rootScriptTypeName`：步骤 1 收集的完整 C# 类型名。

一个 Prefab 一次调用，内部循环建树、加组件、绑字段全部在这一次 C# 执行里完成，AI 不逐节点操作。`rootScriptTypeName` 传 `null` 表示只生成层级不挂脚本（用于 Cell 类不需要挂根脚本的场景，字段绑定改为在父 Prefab 生成时通过 `data-prefab-asset-path` 整体引用）。

### 步骤 7.5：验证结果（优先 MCP）

生成 Prefab 后，必须执行以下验证步骤：

#### 7.1 层级结构验证

使用 `mcp__ai-game-developer__gameobject-find` 检查 Prefab 层级：

**检查项**：
- ✅ 根节点名称正确（与类名一致，如 `MonthCardGiftPanel`）
- ✅ 根节点有 Canvas + GraphicRaycaster + 脚本组件
- ✅ 符合项目标准结构（对于 Panel）：
  ```
  XxxPanel (根节点)
  ├── Screen (遮罩层)
  └── Window (弹窗容器)
      └── Root (内容容器)
          └── 实际UI元素
  ```
- ✅ 所有命名节点（data-name）都存在

**示例命令**：
```javascript
mcp__ai-game-developer__gameobject-find({
  gameObjectRef: {assetPath: "Assets/Resources/PanelUI/.../XxxPanel.prefab"},
  hierarchyDepth: 3,
  includeComponents: true
})
```

**常见问题**：
- Screen 节点缺失 → TSX 中使用了自闭合标签 `<div ... />`，改为 `<div ...></div>`
- 根节点名称错误 → Unity SaveAsPrefabAsset 强制改名，检查文件名是否与 TSX 根节点一致

#### 7.2 字段绑定完整性验证

**检查项**：
- ✅ 逐作用域的可绑定引用全部有值；数组按元素核对，值类型及纯数据类不计入引用绑定总数
- ✅ 包括主 Panel 的所有字段
- ✅ 包括所有内嵌组件（XXXCell、XXXRow）的字段

**验证方法**：

1. 按步骤 1 的清单逐个核对根页面与每个嵌套实例的字段，验证对象类型和引用非空；数组按实际元素核对。保存后通过 `PrefabUtility.LoadPrefabContents` 重新打开，使用 `SerializedObject` 核对实际目标，完成后卸载；不能只看生成日志中的计数或保存前内存对象
   生成器会自动执行同一检查：`verification-report.json.bindings` 逐个用 `SerializedObject` 核对保存后的字段引用；任何一项失败都会把 `generation-report.status` 置为 `failed`，不再出现“报告 success 但引用丢失”。人工复核仍按本清单执行。
2. 检查生成日志或校验报告中的绑定数量
3. 如果数量不一致，回到步骤 1 检查是否漏掉内嵌组件

**自动修复**：字段名拼写错误时，生成器会在目标脚本上找唯一一个类型兼容、名称最相近的字段自动绑定，并在 `generation-report.json` 的 `autoFixes` 和对应 binding 的 `resolvedField` 中记录；存在多个同分候选或没有相似候选时仍然失败，不会静默绑错对象。

**常见问题**：
- 字段数量少于预期 → 漏掉了某个内嵌组件（如 `XXXCell m_CellTemplate` 指向的 Cell 脚本）
- 字段数量多于预期 → TSX 中有多余的 data-field 绑定

#### 7.3 内嵌组件模板验证

对于包含内嵌组件的 Prefab，必须检查模板节点是否存在：

**检查项**：
- ✅ 每个可绑定的模板字段（如 `XXXCell m_CellTemplate`）对应的容器下有模板节点；运行时维护的 `List<XXXCell>` 由业务代码填充，不直接进行 `data-field` 绑定
- ✅ 模板节点包含 `data-lr-component="LR.XXXCell"` 对应的组件
- ✅ 模板节点包含该组件的所有字段
- ✅ 模板的初始显隐与设计一致；同时核对 activeSelf 和父节点影响，不能将根节点未激活造成的隐藏误当作模板已设置隐藏

**示例**：检查容器下是否有模板子节点
```javascript
mcp__ai-game-developer__gameobject-find({
  gameObjectRef: {
    assetPath: "Assets/Resources/.../XxxPanel.prefab",
    path: "XxxPanel/.../ContainerRoot/XxxCell"
  },
  includeComponents: true
})
```

**预期结果**：找到节点、有对应组件、字段完整

**常见问题**：
- 模板节点不存在 → 回到步骤 3，在容器下添加模板节点（data-visible="false"）
- 模板节点的字段不全 → 回到步骤 1，检查该 Cell 的 C# 字段清单是否完整

#### 7.4 与 React 原型对比验证

**检查项**：
- ✅ 原型中的关键 UI 元素都存在于 Prefab 中
- ✅ 特别是：按钮、输入框、列表、模板 Cell
- ✅ 动态列表有对应的模板节点

**常见问题**：
- 原型有但 Prefab 没有 → 回到步骤 1/3 补充
- 按钮、输入框等交互元素缺失 → 可能是内嵌组件字段遗漏

#### 7.5 Unity Console 检查

使用 `mcp__ai-game-developer__console-get-logs` 检查是否有错误或警告：

**检查项**：
- ❌ 不应该有 `未找到类型: LR.xxx` 错误
- ❌ 不应该有 `未找到字段: m_xxx` 警告
- ⚠️ `未找到组件配方: xxx` 必须核查；涉及本次必需节点时视为阻断，不能仅记录警告后声称生成成功

#### 7.6 与参考 Prefab 对比（步骤 2.5 做过侦察时）

- **结构**：节点命名、组件集合、模板位置是否与 `reference-notes.md` 的结构结论一致；差异用 `gameobject-find` 核对，warn 不阻断。
- **样式**：关键角色（标题/按钮/奖励行）的字段是否与参考一致，或是否有 `reference-notes.md` 记录的显式覆盖理由。
- 不一致且没有理由 → 回到步骤 3 修正或补记录；参考本身弱匹配时，以原型和白名单默认值为准。

#### 7.7 截图验证（复杂 UI 优先）

`mcp__ai-game-developer__screenshot-isolated` 不能直接截 UI Prefab：UI 只有 `CanvasRenderer`、没有 `Renderer`，无法计算 bounds；Screen Space Overlay 也不会进入相机。可靠做法：

1. 新建一个 additive 临时场景，场景内放一台 Camera（正交，正交尺寸 540，对应 1280×720）。
2. 实例化目标 Prefab，把根 `Canvas.renderMode` 改为 `ScreenSpaceCamera`，`worldCamera` 指向该相机；根 RectTransform 固定为 1920×1080 以便布局。
3. 用 `screenshot-camera` 指定该相机截图。
4. 验证完成后卸载临时场景、删除场景资产和测试 Prefab；不要保存原场景。

**注意**：Prefab 截图只能看到静态结构，动态内容（如列表项）需要运行时才能看到。占位图标、运行时异步加载的图片在截图中显示为默认占位图是预期行为。

#### 7.8 验证结果报告

生成器会在 JSON 同目录写 `generation-report.json`（尝试绑定/实际绑定、错误、自动修复）和 `verification-report.json`（Prefab 实际样式快照：Screen/文本/按钮/RawImage）。先看两个报告的 `status`：`generation-report.json` 为 `failed` 时不得声称生成成功；`verification-report.json` 的文本字号/颜色/字体、按钮 Sprite、Screen Sprite/颜色应与 profile 角色或 TSX 覆盖一致。

`generation-report.json` 的 `autoFixCount`/`autoFixes` 列出本次自动修复：
- `asset`：原路径不存在，按文件名在 `Assets/` 下找到唯一同名资源（多个同类候选时按目录相近度、AtlasResources 优先、路径长度排序；仍并列则失败并列出候选）。
- `field`：字段名不存在，在目标脚本上找唯一类型兼容、名称最相近的字段（规范化匹配优先，其次编辑距离；多候选并列则失败）。
自动修复不是失败，但必须在报告和最终汇报中列出，便于人工抽查。

向用户报告验证结果：

**成功示例**：
```
✅ 验证通过
- 生成 Prefab: MonthCardGiftPanel.prefab
- 层级结构: Panel + Screen + Window + Root ✅
- 字段绑定: 12 个字段全部绑定 ✅
  - MonthCardGiftPanel: 5 个
  - MonthCardGiftFriendCell: 4 个
  - MonthCardGiftCardCell: 3 个
- 内嵌组件模板: 2 个模板节点存在 ✅
- Unity Console: 无错误 ✅
```

**失败示例**：
```
❌ 验证失败
- Screen 节点缺失
- 字段绑定: 预期 12 个，实际 9 个（缺少 MonthCardGiftCardCell 的 3 个字段）
- 建议：回到步骤 1，检查是否漏掉 MonthCardGiftCardCell.cs
```

### 步骤 8：清理部署的生成器脚本

生成和验证完成后，删除步骤 2.5/6 部署到 Unity 项目的临时脚本（参考扫描器与生成器在同一目录），恢复项目干净状态：

```bash
python .claude/skills/lr-openspec-ui-prefab/scripts/cleanup_lr_ui_gen.py <unity-project-root>
```

清理完成后调用 `mcp__ai-game-developer__assets-refresh`，让 Unity 感知删除。

如果执行过程中断（AI 会话被压缩/用户中止/MCP 超时），下次运行步骤 6 时部署脚本会自动清理上次残留，所以不需要专门手动清理孤儿文件。

## CLI 兜底（MCP 不可用或能力不足时）

默认仍执行步骤 0–8 的 ai-game-developer MCP 主流程。先记录 MCP 失败/不支持的事实；禁止因为批处理方便或新版使用 CLI 就跳过可用的 MCP。

确认目标是 SE 项目、工程未被编辑器占用、`ProjectVersion.txt` 为 SE 实际版本，按需用环境变量 `UNITY_EXECUTABLE` 指定正确 Unity。不要强制关闭用户编辑器，不并行启动相同工程。

部署步骤 6 的生成器后，逐页调用：

```bash
python .claude/skills/lr-openspec-ui-prefab/scripts/unity_cli_wrapper.py <SE工程绝对路径> <JSON绝对路径> <步骤1.5的Prefab路径> <完整脚本类型>
```

该脚本只负责兜底调用，不替代字段和视觉验收。复核退出码、生成日志、Prefab 文件；待 MCP 恢复后仍优先检查层级、字段引用、Console 和截图。无法完成的项目写为待验证，不宣称全部通过。结束后按步骤 8 清理。

## 常见问题处理

### Unity Console 出现 `未找到类型: LR.xxx`

先通过 SE 的 ai-game-developer MCP 核实真实类名与命名空间，再按报错来源定位维护位置：

- JSON 配方声明的类型：检查 `scripts/lr_ui_gen/ComponentRecipes/<semanticId>.json` 中的 `componentType`、`components[].type` 和子层级组件类型，修正对应配方。
- `postProcess` 后处理创建的类型：检查 `LRComponentRecipes.cs` 中实际命中的钩子（如滚动列表或输入框），修正该钩子的类型引用。
- TSX 的 `data-lr-component` 显式挂载类型：核对其声明与 SE 脚本类型是否一致。

修改原始配方或生成器后重新临时部署，通过 MCP 检查编译、组件类型和序列化引用；部署副本仍以本技能源码为准。

### 校验器报字段绑定缺失

说明 TSX 里少画了一个节点。回到步骤 3，为该字段补一个节点（哪怕是隐藏占位），不要绕过校验。

### 图片资源

`sprite`/图片路径允许留空，交给美术后续在 Unity 里替换；节点本身和字段绑定不允许因为"没有图片"而省略。

### 需要新增语义组件 ID

不在本技能范围内直接扩充。回到 `lr-design` 的 `unity-ui-components.md` 维护流程：先用 MCP 扫描确认 SE 真实 Prefab 配方，再人工评审加入白名单，然后在 `scripts/lr_ui_gen/ComponentRecipes/` 下按 `semanticId` 新增对应 `.json` 配方。配方声明组件类型、属性与层级；确需新增或修改 `postProcess` 时，再维护 `LRComponentRecipes.cs` 中对应的后处理钩子并验证。

## 版本信息

**版本**: v2.5（SE：MCP 优先，CLI 可选兜底）（TSX 中间格式 + 参考侦察 + 角色化 style profile + 命名/节点级样式覆盖 + 资源/字段自动修复 + 保存后字段引用核验 + fail-closed 生成与核验报告）

**依赖 SKILL**：
  - `/lr-design`——生成并验收 Web 原型，产出 `unity-ui-components.md` 白名单
  - `/lr-openspec-apply`——生成 UI 脚本（`[SerializeField]` 字段清单来源）

**依赖工具**：
  - ai-game-developer MCP（Unity 插件）
  - 临时部署的生成器源码：`LRUnityLayoutPrefabGenerator.cs`、`LRUnityLayoutCLI.cs`、`LRComponentRecipes.cs`、`LRFieldBinder.cs`、`ComponentRecipeLoader.cs`、`LRPrefabReferenceScanner.cs`（namespace `LRUIPrefabGen`）。唯一真相源是本技能的 `scripts/lr_ui_gen/`，参考侦察/生成时部署至 `Assets/Editor/LRUIPrefabGen/`，完成后按步骤 8 清理。
  - `LRUnityLayoutCLI.cs` 是可选 CLI 备用入口；默认仍通过 ai-game-developer MCP 调用生成器。

**依赖配置**：
  - `.claude/skills/lr-design/references/unity-ui-components.md`——组件映射 + 默认样式
  - [references/unity-layout-attributes.md](references/unity-layout-attributes.md)——TSX 布局属性规范
  - `scripts/build_ui_style_profile.py`——把多个参考 Prefab 的扫描结果聚合为模块级角色化风格档案（步骤 2.6）
