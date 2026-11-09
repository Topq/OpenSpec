# Unity 布局数据规范（TSX → Prefab 专用）

## 定位

这份文档描述的是**给 Unity 生成器吃的精确数据格式**，不是给策划看的原型格式。

- 策划验收用的是 `changes/<id>/demo/index.html`（`lr-design` 产出，语言是玩法/视觉，不在这份文档管辖范围）。
- 本文档管辖 `changes/<id>/demo/unity/*.tsx`（`lr-openspec-ui-prefab` 产出），只在策划验收通过、C# 脚本已生成之后创建，是"把已拍板的设计重新用 Unity 语言表达一遍"，不是新的创作。
- 组件语义 ID 沿用 [unity-ui-components.md](../../lr-design/references/unity-ui-components.md) 的白名单（已通过 MCP 扫描项目真实 Prefab 生成），本文档只新增"如何精确描述位置/尺寸/绑定"这一层，不重新定义组件类型。

## 核心原则

1. **不用 CSS 表达布局**。位置、尺寸、锚点、Pivot 只能出现在 `data-*` 属性里，且必须是静态字符串字面量（生成器直接读 TSX 源文本，不执行 JSX 表达式）。
2. **不推断，只显式声明**。每个需要绑定到 C# `[SerializeField]` 字段的节点，必须显式写 `data-field`；生成器不做命名猜测。
3. **复用优先于新建**。项目已有的框架组件（`LR.SingleScrollView`、`LR.UIRedPointWatcher` 等）通过 `data-prefab-child-path` 引用其内部子节点，不重新拼层级。
4. **字段驱动，不是原型驱动**。生成 TSX 时以 C# 脚本中可由 FieldBinder 绑定的 `[SerializeField]` 对象引用为约束：普通字段唯一绑定，一维数组按连续下标逐元素绑定。数值、字符串、纯数据类和运行时集合不强求节点。demo 里没画出来的状态元素（已购买标记、锁定图标等）如果对应可绑定引用字段存在，也必须补出节点。
5. **重叠必须显式声明意图**。校验器默认认为兄弟节点重叠是排版错误，两种例外要显式标注，不能靠校验器猜：
   - **状态互斥的隐藏节点**：`data-visible="false"`（如"已领取"图标盖在"领取"按钮上，两者同一时刻只显示一个）
   - **有意的视觉分层**：`data-overlay="true"`（如背景图铺满整个区域、其上还有标题文字）
   机械排列的行列（工具条、按钮组）用 `data-layout-group` 声明在父节点上，校验器会跳过其子节点间的重叠检查（Unity 运行时/生成时才真正排列这些子节点）。
6. **样式优先复用命名变体，具体值只用于差异**。常用样式先映射到已有 `data-lr-style`（如 `title`/`body`）；命名变体表达不了、且参考 Prefab 有明确依据时，才使用节点级覆盖。具体覆盖必须在 `reference-notes.md` 记录理由，不能成为随手写死样式的通道。
7. **参考是翻译词典，不是新设计**。步骤 2.5 的参考侦察只用于回答"项目里这个角色通常用什么组件/命名/样式"，不重新做视觉决策，也不直接抄参考的渐变、阴影、圆角等美术细节。

## 属性总表

### 通用属性（每个带 `data-component` 的节点都可能用到）

| 属性 | 说明 | 示例 |
|---|---|---|
| `data-name` | 生成后的 `GameObject.name`；必须稳定，重复生成时保持不变 | `data-name="BuyButton"` |
| `data-component` | 语义组件 ID，取值见 unity-ui-components.md 白名单 | `data-component="control.button"` |
| `data-field` | 绑定到 C# 脚本的 `[SerializeField]` 字段名；只在该节点需要被代码访问时写 | `data-field="m_BuyButton"` |
| `data-prefab-child-path` | 引用父级框架组件 Prefab 内部的已有子节点路径，不新建节点，见下方"预制件内部引用"一节 | `data-prefab-child-path="Viewport/Content"` |

### 布局属性（RectTransform 的精确映射，不允许省略 `data-pos`/`data-size`）

| 属性 | Unity 对应 | 说明 |
|---|---|---|
| `data-pos="(x, y, z)"` | `anchoredPosition`（z 通常为 0） | 相对锚点的偏移，单位像素，画布基准 1920x1080 |
| `data-size="(w, h)"` | `sizeDelta` | 固定锚点下是实际尺寸；拉伸锚点下是相对父容器的收缩值（可为负） |
| `data-anchors="(minX, minY, maxX, maxY)"` | `anchorMin`/`anchorMax` 简写（四值相同用于非拉伸） | 见下方锚点选择表 |
| `data-anchor-min="(x, y)"` + `data-anchor-max="(x, y)"` | 分别设置，用于拉伸布局 | 与 `data-anchors` 二选一，不同时写 |
| `data-pivot="(x, y)"` | `pivot` | 节点自身的中心点 |

**锚点选择表**（与 UI_React_Spec 保持一致）：

| 位置 | `data-anchors` | `data-pivot` |
|---|---|---|
| 左上角固定 | `(0, 1, 0, 1)` | `(0, 1)` |
| 右上角固定 | `(1, 1, 1, 1)` | `(1, 1)` |
| 左下角固定 | `(0, 0, 0, 0)` | `(0, 0)` |
| 右下角固定 | `(1, 0, 1, 0)` | `(1, 0)` |
| 居中固定 | `(0.5, 0.5, 0.5, 0.5)` | `(0.5, 0.5)` |
| 横向拉伸铺满 | `data-anchor-min="(0, y)"` + `data-anchor-max="(1, y)"` | 按需 |
| 全部拉伸铺满 | `data-anchor-min="(0, 0)"` + `data-anchor-max="(1, 1)"` | 按需 |

### 文本属性（`data-component="text.localized"` 专用）

| 属性 | 说明 |
|---|---|
| `data-text` | 初始文案（也应作为标签内的可见文本内容，保持预览一致） |
| `data-text-align` | `Left` / `Center` / `Right` / `Justified` |
| `data-vertical-align` | `Top` / `Middle` / `Bottom` |
| `data-color` | 四值归一化 RGBA，如 `data-color="(1, 0.85, 0.2, 1)"` |
| `data-lr-style` | 命名样式（`title`/`body`），沿用 unity-ui-components.md 定义，与全局默认样式叠加规则一致 |

### 按钮属性（`data-component="control.button"` 专用）

- 用 `<button>` 标签
- 按钮文案放在标签内容里，同时写 `data-text` 保持一致
- 对齐属性复用文本属性的 `data-text-align`/`data-vertical-align`

### 列表属性（`data-component="list.scroll"` / `list.single-scroll"` 专用）

| 属性 | 说明 |
|---|---|
| `data-layout-group` | `Horizontal` 或 `Vertical`，仅用于机械排列的行/列（工具条、tab、按钮组），不用于需要手动摆位的自由布局 |
| `data-layout-spacing` | 子项间距（数值） |
| `data-layout-padding` | 四值 `(left, right, top, bottom)` |
| `data-layout-child-alignment` | Unity `TextAnchor` 命名，如 `UpperLeft`、`MiddleCenter` |

### 节点级样式覆盖（命名变体之后）

优先级：**配方默认 + postProcess < `data-lr-style` 变体 < `data-role` 角色默认 < 下列显式覆盖**。

| 属性 | 说明 | 示例 |
|---|---|---|
| `data-font-size` | TMP 字号；必须 > 0 且 ≤ 200 | `data-font-size="28"` |
| `data-color` | 文本颜色；无 TMP 时作为 Image/RawImage 颜色别名；`data-name="Screen"` 遮罩节点映射到生成的 Screen Image 颜色 | `data-color="(1, 0.84, 0, 1)"` |
| `data-font` | TMP 字体资产；必须位于 `Assets/Resources/Font/` | `data-font="Assets/Resources/Font/fzhjtSDF.asset"` |
| `data-font-material` | TMP 字体材质；必须位于 `Assets/Resources/Font/` | `data-font-material="Assets/Resources/Font/fzhjtSDF_UI_TitleLine.mat"` |
| `data-text-align` | 水平对齐；可单独使用，单独使用时保留另一轴 | `Center` |
| `data-vertical-align` | 垂直对齐；可单独使用，单独使用时保留另一轴 | `Middle` |
| `data-sprite` | Image 贴图；必须以 `Assets/` 开头 | `data-sprite="Assets/UI/AtlasResources/CommonPanel/ty_btn_11.png"` |
| `data-texture` | RawImage 纹理；必须以 `Assets/` 开头，只能用于 `content.async-image` 等 RawImage 节点 | `data-texture="Assets/UI/Texture/decorativeextra/ty_tk_frame_06.png"` |
| `data-image-type` | `Simple` / `Sliced` / `Tiled` / `Filled` | `data-image-type="Sliced"` |
| `data-image-color` | **图片**颜色，四值归一化 RGBA | `data-image-color="(1, 1, 1, 1)"` |
| `data-preserve-aspect` | `true` / `false` | `data-preserve-aspect="true"` |

**目标规则**：

- 文本覆盖作用于节点自身的 TMP，或该节点唯一一个直接 TMP 子节点。`control.button` 自动生成的 `Text` 子节点、`template.tab-item` 的 `Label` 子节点都符合；有多个 TMP 子节点时必须把覆盖写到具体的文本节点上。
- 图片覆盖作用于节点自身的 `Image`。`RawImage` 支持 `data-image-color` 和 `data-texture`；写 `data-sprite`/`data-image-type`/`data-preserve-aspect` 会报错。
- `data-color` 优先作为文本颜色；节点没有 TMP 但有 Image/RawImage 时按图片颜色处理；`data-name="Screen"` 的遮罩节点由生成器注入的 Screen Image 消费。按钮同时有文本和图片时，`data-color` 是文本颜色，图片颜色请用 `data-image-color`。
- 每个覆盖必须有可消费的目标；没有目标时校验器报错，生成器也拒绝生成，不会静默忽略。
- 全屏遮罩/背景节点用 `data-overlay="true"` 标记，校验器会豁免它与兄弟节点的重叠检查（它不是普通兄弟内容）。
- 常用样式优先沉淀为 `data-lr-style` 命名变体；具体覆盖必须能在 `reference-notes.md` 解释“为什么不用命名样式”。

示例：

```tsx
<div
  data-name="Txt_Title"
  data-component="text.localized"
  data-lr-style="title"
  data-pos="(0, 300)"
  data-size="(600, 48)"
>成长基金</div>

<div
  data-name="Txt_Count"
  data-component="text.localized"
  data-font-size="24"
  data-color="(1, 1, 1, 1)"
  data-text-align="Center"
  data-vertical-align="Middle"
  data-pos="(0, 240)"
  data-size="(600, 32)"
></div>

<button
  data-name="Btn_Claim"
  data-component="control.button"
  data-sprite="Assets/UI/AtlasResources/CommonPanel/ty_btn_11.png"
  data-image-type="Sliced"
  data-image-color="(1, 1, 1, 1)"
  data-text="领取"
  data-font-size="24"
  data-pos="(0, -200)"
  data-size="(180, 56)"
>领取</button>
```

## 参考侦察（步骤 2.5）

生成 TSX 前，技能可用 MCP + 临时部署的 `LRPrefabReferenceScanner` 扫描 1–3 个同类 Prefab，产出：

- `changes/<id>/demo/unity/references.json`：扫描器输出的紧凑事实（层级、组件、TMP/Image/LayoutGroup 关键样式字段）；
- `changes/<id>/demo/unity/reference-notes.md`：AI 写的候选、选中理由、结构结论、样式映射和覆盖理由。

约束：

- 参考是翻译词典，不是新设计；原型仍决定视觉意图。
- 样式优先映射到已有 `data-lr-style`；命名变体不够时才用节点级覆盖。
- 布局度量（anchors/pivot/size）只做 sanity check，不直接抄。
- 参考扫描失败/无候选 → 继续用白名单默认值，不阻断。
- 扫描器只读，使用 `PrefabUtility.LoadPrefabContents` 读取嵌套 Prefab 的最终值，不保存资产。

## 模块级风格档案（步骤 2.6）

没有同功能现网 Prefab 时，不要直接套白名单默认值。找 3–5 个同模块同类界面，扫描后用 `build_ui_style_profile.py` 聚合出角色化风格档案：

```bash
python .claude/skills/lr-openspec-ui-prefab/scripts/build_ui_style_profile.py \
  changes/<id>/demo/unity/references.json \
  --module <模块名> \
  -o changes/<id>/demo/unity/ui-style-profile.json \
  --markdown changes/<id>/demo/unity/ui-style-profile.md
```

角色：

| 角色 | 聚合内容 |
|---|---|
| `modal.header` | 弹窗标题字号/颜色/字体/材质/对齐 |
| `page.title` | 页面标题字号/颜色/字体/材质/对齐 |
| `body` | 正文/描述字号/颜色/字体/材质/对齐 |
| `price` | 价格字号/颜色/字体/材质/对齐 |
| `button.primary` | 主按钮 Sprite/Type/ImageColor/文字样式（尺寸/锚点只作参考，不自动套用） |
| `button.secondary` | 次按钮 Sprite/Type/ImageColor/文字样式（尺寸/锚点只作参考，不自动套用） |
| `button.close` | 关闭按钮 Sprite/Type/ImageColor（尺寸/锚点只作参考，不自动套用） |
| `window.frame` | 窗口框 Texture/颜色（宽高只作参考，不自动套用） |
| `divider` | 分割线 Sprite/Type/颜色（宽高只作参考，不自动套用） |
| `screen` | 遮罩 Sprite/Type/颜色 |

优先级：**同功能现网 Prefab > 模块风格档案 > 白名单默认值**。风格档案是参考，不是硬约束；高频值不一定适合当前面板，最终以已验收原型 + 同功能参考为准。

### 角色样式（`data-role`）

给承载样式的节点写 `data-role`，转换时用 `--profile` 把角色默认值物化进 JSON：

```tsx
<div data-component="text.localized" data-name="TxtTitle" data-role="modal.header" />
<button data-component="control.button" data-name="BtnConfirm" data-role="button.primary" />
<div data-component="content.async-image" data-name="Bg" data-role="window.frame" />
<div data-component="surface.page" data-name="Screen" data-role="screen" />
```

规则：

- 角色只能是上表白名单；`button.*` 必须用于 `control.button`，文本角色必须有 TMP 目标，`window.frame` 必须有 RawImage 目标，`screen` 必须名为 `Screen`/`Scene`。
- profile 只提供视觉属性；`data-pos`/`data-size`/`data-anchors`/`data-pivot` 永远以 TSX 为准。
- TSX 显式 `data-*` 覆盖优先于 profile；profile 缺少角色时转换器给警告并保留配方/显式样式。
- `tsx_to_json.py --profile ...` 会写 `_styleSources`，标明每个样式键来自 `tsx` 还是 `profile:<role>`。
- `screen` 角色需要显式声明名为 `Screen`/`Scene` 的节点；`surface.panel` 自动注入的 Screen 没有对应 JSON 节点，无法消费 profile 样式。

## 预制件内部引用（`data-prefab-child-path`）

用于引用**已存在的框架组件 Prefab 内部子节点**，不新建 GameObject，只在生成时定位并可能设置该子节点的绑定：

```tsx
<div
  data-name="RewardsList"
  data-component="list.single-scroll"
  data-pos="(0, -100)"
  data-size="(800, 600)"
  data-field="m_RewardListRoot"
>
  <div data-prefab-child-path="Viewport/Content" data-name="Content" />
</div>
```

规则：

- 只能引用 unity-ui-components.md 白名单组件配方里**文档化的内部路径**（如 `list.single-scroll` 配方里的 `Viewport/Content`），不得凭空引用未扫描到的路径。
- 带 `data-prefab-child-path` 的标签不得同时带 `data-component`——它编辑的是已有节点，不创建新节点。
- 路径格式是相对该组件 Prefab 根节点的 Transform 名称链，用 `/` 连接，与 Unity `Transform.Find()` 语义一致。

## Cell 模板引用（复用现有 Prefab 作为子节点）

当 `list.single-scroll` 的 Cell 已经存在独立 Prefab（如 `GrowthFundRewardCell.prefab`）时，用 `data-prefab-asset-path` 声明整体实例化，而不是在 TSX 里重新展开 Cell 内部结构：

```tsx
<div
  data-name="RewardCellTemplate"
  data-prefab-asset-path="Assets/Resources/PanelUI/GrowthFundRewardCell.prefab"
  data-field="m_RewardCellTemplate"
/>
```

生成器行为：`PrefabUtility.InstantiatePrefab` 实例化整个 Prefab 作为子节点，`data-field` 绑定该实例的根 Transform。这与 `data-prefab-child-path`（编辑父级组件内部已有节点）是两个不同的机制，不要混用。

## 字段完整性约束（本项目特有，UI_React_Spec 没有这条）

生成 TSX 前，先列出目标 C# 脚本的完整 `[SerializeField]` 字段清单并区分可绑定引用和数据。每个可绑定引用必须有对应 `data-field`，缺一个就是生成失败，不是警告；一维数组使用 `[0]`、`[1]` 等连续下标，不允许重复或空洞：

- 校验器（见 `scripts/validate_unity_layout.py`）强制检查这条，不允许"部分绑定后放行"。
- 字段名称不要求 `m_` 前缀；允许 `[SerializeField] [Header(...)]` 和 `[SerializeField, HideInInspector]`。绑定类型必须由同节点配方或额外挂载组件提供，不能用文本节点绑定 Button，也不能把配方子节点的组件当作父节点组件。
- `List<T>`、值类型、纯数据类及 `UnityEngine.Object` 不能显式绑定；当前 FieldBinder 仅支持 GameObject、Transform/RectTransform、Component 及它们的一维数组。运行时 List 由业务代码填充，模板使用独立组件引用。
- `layoutGroup` 只接受 `Horizontal` / `Vertical`；文本对齐和子节点对齐也校验枚举拼写，TSX 与 JSON 共用枚举约定。
- 静态检查会解析提供的 C# 自定义继承；未提供完整继承链、已有 Prefab 内容必须通过 MCP 继续验证。生成后重载 Prefab，用 SerializedObject 检查类型、引用非空和逐实例作用域。
- 如果某个字段在策划 demo（`index.html`）中找不到视觉对应物（比如"已购买标记"这种状态元素，demo 只画了默认态），仍必须在 TSX 里补出对应节点——可以是隐藏状态（`data-visible="false"`）的占位节点，但节点必须存在且携带 `data-field`。
- 图片资源（`sprite`/`data-image`）允许留空，交给美术后续替换；但节点本身、绑定关系不允许留空。

## 与 index.html（策划原型）的关系

- `unity/*.tsx` 是 `index.html` 的"翻译"，不是替代。翻译时的行为基准是已冻结的 `changes/<id>/specs/` delta 和已验收的 `index.html`，不重新做设计决策。
- 视觉细节（图片、圆角、渐变、阴影）不翻译，`unity/*.tsx` 的配套 CSS 只用于基础预览识别，不得还原视觉效果——这些交给美术在 Unity 里后续处理。
- 如果翻译过程中发现 `index.html` 与 C# 脚本字段之间存在结构性矛盾（比如脚本需要三个领取按钮但 demo 只有一个统一入口），停止生成，回报给使用者，不静默拍板改设计。

