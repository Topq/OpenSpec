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
4. **字段驱动，不是原型驱动**。生成 TSX 时以 C# 脚本的 `[SerializeField]` 字段清单为清单式约束——每个字段必须在 TSX 中有且只有一个对应节点，而不是"demo 里有什么就画什么"。demo 里没画出来的状态元素（已购买标记、锁定图标等）如果对应字段存在，也必须补出节点。
5. **重叠必须显式声明意图**。校验器默认认为兄弟节点重叠是排版错误，两种例外要显式标注，不能靠校验器猜：
   - **状态互斥的隐藏节点**：`data-visible="false"`（如"已领取"图标盖在"领取"按钮上，两者同一时刻只显示一个）
   - **有意的视觉分层**：`data-overlay="true"`（如背景图铺满整个区域、其上还有标题文字）
   机械排列的行列（工具条、按钮组）用 `data-layout-group` 声明在父节点上，校验器会跳过其子节点间的重叠检查（Unity 运行时/生成时才真正排列这些子节点）。

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

生成 TSX 前，先列出目标 C# 脚本的完整 `[SerializeField]` 字段清单。TSX 中每个字段必须能找到唯一对应的 `data-field`，缺一个就是生成失败，不是警告：

- 校验器（见 `scripts/validate_unity_layout.py`）强制检查这条，不允许"部分绑定后放行"。
- 如果某个字段在策划 demo（`index.html`）中找不到视觉对应物（比如"已购买标记"这种状态元素，demo 只画了默认态），仍必须在 TSX 里补出对应节点——可以是隐藏状态（`data-visible="false"`）的占位节点，但节点必须存在且携带 `data-field`。
- 图片资源（`sprite`/`data-image`）允许留空，交给美术后续替换；但节点本身、绑定关系不允许留空。

## 与 index.html（策划原型）的关系

- `unity/*.tsx` 是 `index.html` 的"翻译"，不是替代。翻译时的行为基准是已冻结的 `changes/<id>/specs/` delta 和已验收的 `index.html`，不重新做设计决策。
- 视觉细节（图片、圆角、渐变、阴影）不翻译，`unity/*.tsx` 的配套 CSS 只用于基础预览识别，不得还原视觉效果——这些交给美术在 Unity 里后续处理。
- 如果翻译过程中发现 `index.html` 与 C# 脚本字段之间存在结构性矛盾（比如脚本需要三个领取按钮但 demo 只有一个统一入口），停止生成，回报给使用者，不静默拍板改设计。

