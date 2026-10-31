# Unity UI 组件白名单

## 使用规则

- Web 只通过 `data-lr-component` 引用下表语义 ID。
- 不把 C# 类型名、程序集名或 Prefab 路径写进 HTML。
- 转换器根据语义 ID 创建 Unity 类型、标准层级和附加组件。
- 功能专用脚本不进入公共白名单；由后续 UI 开发阶段绑定。
- 扩充白名单前必须扫描项目 Prefab、确定稳定配方，并人工评审本文件。
- **所有文本组件必须使用 TextMeshProUGUI，禁止使用 UnityEngine.UI.Text**。

## 首批白名单（快速索引）

| 语义 ID | 用途 | Unity 映射/配方 |
|---|---|---|
| `surface.panel` | 全屏或主面板根节点 | `RectTransform`，按视觉需要附加 `Image` |
| `surface.page` | 面板内页面根节点 | `RectTransform`，保留 DOM 子层级 |
| `surface.modal` | 模态弹窗根节点 | 遮罩层、弹窗容器、阻断点击区域 |
| `control.button` | 可点击按钮 | 见下方详细配置 |
| `control.toggle` | 二态选择控件 | `Toggle`、选中/未选中视觉、`LR.RaycastArea` |
| `control.input` | 文本输入控件 | 见下方详细配置 |
| `control.progress` | 进度显示 | `LR.LRProgressBar` 及前景/背景层级 |
| `list.single-scroll` | 单项复用滚动列表（推荐，性能优化） | 见下方详细配置 |
| `list.scroll` | 常规滚动列表（仅在不需要复用时使用） | `ScrollRect`、`Viewport/Content`、裁剪组件 |
| `content.async-image` | 异步加载大图（背景图、立绘等大尺寸图片） | `RawImage` 与 `LR.AsyncTexture`，见下方详细配置 |
| `content.async-icon` | 异步加载图标（非道具类图标，如头像、功能图标等） | `RawImage` 与 `LR.AsyncIcon` |
| `content.icon` | UI 状态标识和静态图标（锁定徽章、已领取遮罩、功能入口等），图片在设计期确定 | `UnityEngine.UI.Image`，默认图集贴图，`raycastTarget=false` |
| `content.item-icon-root` | 运行时 `ItemIconBase.Allocate()` 的挂载点，**专门用于道具展示**（装备、材料、货币等游戏道具） | 空 `GameObject`，只有 `RectTransform`，不挂载任何 UI 组件；字段类型必须是 `Transform` |
| `content.buff-icon-root` | 运行时 `BuffIcon.Allocate()` 的挂载点，用于动态生成 Buff/Debuff 图标（图标+层数+时间） | 空 `GameObject`，只有 `RectTransform`，不挂载任何 UI 组件；字段类型必须是 `Transform` |
| `text.localized` | 多语言文本 | 见下方详细配置 |
| `slot.item-icon` | 物品图标业务槽位 | 标准物品图标层级；业务绑定留到 UI 开发阶段 |
| `feedback.red-point` | 红点提示 | 红点节点与 `LR.UIRedPointWatcher` |
| `template.tab-item` | 页签复用模板 | 页签标准层级，配合 `data-lr-template`/`data-lr-slot` |
| `template.reward-cell` | 奖励单元复用模板 | 奖励格标准层级，配合 `data-lr-template`/`data-lr-bind` |

---

## 全局默认样式

所有 TextMeshProUGUI 组件的默认样式（无特殊指定时使用）：

```yaml
font: Assets/Resources/Font/fzhjtSDF.asset
fontSharedMaterial: Assets/Resources/Font/fzhjtSDF_UI_Default.mat
fontSize: 24
color: "#FFFFFF"
alignment: Left
```

**样式覆盖优先级**（从高到低）：
1. Web 原型 inline style（`style="font-size: 28px; color: #FF0000;"`）
2. Web 原型 data-lr-style 命名样式（`data-lr-style="title"`）
3. 组件级默认样式（下方各组件定义）
4. 全局默认样式（上方定义）

---

## 详细组件配置

### `control.button` - 按钮

**Unity 层级结构**：
```
Button (GameObject)
├── RectTransform
├── Button 组件
├── Image 组件
└── Text (子节点)
    ├── RectTransform
    └── TextMeshProUGUI 组件
```

**默认样式**：
```yaml
# 按钮图片 (Image 组件)
image:
  type: Sliced  # 九宫格模式，支持拉伸
  sprite: null  # 留空，由美术后续替换或从 Web 原型指定
  raycastTarget: true

# 按钮文字 (TextMeshProUGUI 组件)
text:
  font: Assets/Resources/Font/fzhjtSDF.asset
  fontSharedMaterial: Assets/Resources/Font/fzhjtSDF_UI_OutLine1Px.mat  # 按钮文字带 1px 描边
  fontSize: 24
  color: "#FFFFFF"
  alignment: Center
```

**Web 原型示例**：
```html
<!-- 基础按钮（使用默认样式） -->
<button id="btn-buy" data-lr-component="control.button">购买</button>

<!-- 覆盖字号和颜色 -->
<button id="btn-special" data-lr-component="control.button" 
        style="font-size: 28px; color: #FFD700;">
  特殊按钮
</button>
```

---

### `text.localized` - 多语言文本

**Unity 层级结构**：
```
Text (GameObject)
├── RectTransform
├── TextMeshProUGUI 组件
└── LR.Localizer 组件
```

**默认样式**（支持三种命名样式，通过 `data-lr-style` 指定）：

```yaml
# 默认样式（不指定 data-lr-style 时使用）
default:
  font: Assets/Resources/Font/fzhjtSDF.asset
  fontSharedMaterial: Assets/Resources/Font/fzhjtSDF_UI_Default.mat
  fontSize: 24
  color: "#FFFFFF"
  alignment: Left

# 标题样式（data-lr-style="title"）
title:
  font: Assets/Resources/Font/fzhjtSDF.asset
  fontSharedMaterial: Assets/Resources/Font/fzhjtSDF_UI_TitleLine.mat
  fontSize: 32
  color: "#FFD700"  # 金色
  alignment: Center

# 正文样式（data-lr-style="body"）
body:
  font: Assets/Resources/Font/ssfttSDF.asset
  fontSharedMaterial: Assets/Resources/Font/ssfttSDF_UI_NoOutLine.mat
  fontSize: 20
  color: "#E0E0E0"  # 浅灰色
  alignment: Left
```

**Web 原型示例**：
```html
<!-- 默认样式 -->
<span data-lr-component="text.localized">普通文本</span>

<!-- 标题样式 -->
<span data-lr-component="text.localized" data-lr-style="title">成长基金</span>

<!-- 正文样式 -->
<span data-lr-component="text.localized" data-lr-style="body">活动说明...</span>
```

---

### `control.input` - 文本输入框

**Unity 层级结构**：
```
InputField (GameObject)
├── RectTransform
├── TMP_InputField 组件
├── Image 组件（背景）
├── TextArea (子节点)
│   └── Text (TextMeshProUGUI)
└── Placeholder (子节点)
    └── Text (TextMeshProUGUI)
```

**默认样式**：
```yaml
# 输入文本
text:
  font: Assets/Resources/Font/ssfttSDF.asset
  fontSharedMaterial: Assets/Resources/Font/ssfttSDF_UI_NoOutLine.mat
  fontSize: 20
  color: "#FFFFFF"

# 占位文本
placeholder:
  text: "请输入..."
  font: Assets/Resources/Font/ssfttSDF.asset
  fontSharedMaterial: Assets/Resources/Font/ssfttSDF_UI_NoOutLine.mat
  fontSize: 20
  color: "#808080"  # 灰色
```

---

### `list.single-scroll` - 单项复用滚动列表

**Unity 层级结构**：
```
ScrollView (GameObject)
├── RectTransform
├── ScrollRect 组件
├── LR.SingleScrollView 组件
└── Viewport (子节点)
    ├── RectMask2D 组件
    └── Content (子节点)
        └── Cell (子节点，模板)
```

**默认样式**：
```yaml
scrollSensitivity: 1.0
movementType: Elastic  # 弹性滚动
scrollbar:
  visibility: AutoHide  # 自动隐藏滚动条
```

---

### `content.async-image` - 异步加载大图

**Unity 层级结构**：
```
AsyncImage (GameObject)
├── RectTransform
├── RawImage 组件
└── LR.AsyncTexture 组件
```

**用途**：
- **专门用于异步加载大尺寸图片**：背景图、立绘、宣传图等
- 使用 `RawImage` 和 `AsyncTexture` 实现异步加载
- 区别于 `content.async-icon`（用于非道具图标）和 `content.icon`（静态小图标）

**默认样式**：
```yaml
raycastTarget: false  # 不响应点击（纯展示图片）
```

**注意**：
- `LR.AsyncTexture` 的 `m_RawImage` 字段序列化的是 `RawImage`，不是 `Image`
- `RawImage` 没有 `preserveAspect` 属性（这是 `Image` 独有的）
- 异步加载后的宽高比由 `AsyncTexture.isSetNativeSize` 或业务代码控制

---

### `content.async-icon` - 异步加载图标（非道具）

**Unity 层级结构**：
```
AsyncIcon (GameObject)
├── RectTransform
├── RawImage 组件
└── LR.AsyncIcon 组件
```

**用途**：
- **用于异步加载非道具类图标**：玩家头像、公会徽章、功能图标等
- 使用 `RawImage` 和 `AsyncIcon` 实现异步加载
- 区别于 `content.item-icon-root`（道具专用，动态实例化完整组件）

**默认样式**：
```yaml
raycastTarget: false  # 不响应点击
```

**典型场景**：
- 玩家头像框
- 公会/联盟徽章
- 动态加载的功能图标

---

### `content.icon` - 静态图标和 UI 状态标识

**Unity 层级结构**：
```
Icon (GameObject)
├── RectTransform
└── Image 组件
```

**用途**：
- **UI 状态标识**：锁定徽章（LockBadge）、已领取遮罩（ClaimedMask）、完成标记等
- **静态功能图标**：固定的入口图标、装饰图标等
- 图片在设计期确定，不需要运行时加载
- 使用图集贴图，性能最优

**默认样式**：
```yaml
raycastTarget: false  # 不响应点击（通常由父节点响应）
sprite: null  # 留空，由美术后续替换或从原型指定
```

**典型场景**：
- 状态徽章：锁定、已完成、已领取、新内容提示
- 装饰图标：标题图标、分隔符、背景装饰
- 静态功能入口（不需要动态加载的）

**对比其他图标类型**：
- `content.icon`：静态 `Image`，设计期确定，字段类型 `Image` 或 `GameObject`
- `content.async-icon`：异步 `RawImage`，运行时加载，字段类型 `RawImage` 或 `GameObject`
- `content.item-icon-root`：动态容器，运行时实例化完整组件，字段类型 `Transform`


---

### `control.progress` - 进度条

**Unity 层级结构**：
```
ProgressBar (GameObject)
├── RectTransform
├── LR.LRProgressBar 组件
├── Bg (子节点，可选)
│   ├── RectTransform
│   └── Image 组件
└── Fill (子节点，必须)
    ├── RectTransform
    └── Image 组件
```

**默认样式**：
```yaml
# Fill 前景节点 (Image 组件)
fill:
  type: Filled
  fillMethod: Horizontal
  fillOrigin: Left
  fillAmount: 1.0
  raycastTarget: false
  
# LRProgressBar 组件默认值
progress: 0.0
widths: [120.0]
```

**配方依据**：基于 2026-07-27 扫描 770 个 Prefab，178 个 LRProgressBar 实例，所有实例均为单段进度条（`m_TargetImages` 数组长度 = 1）。配方详见 `Assets/Editor/ComponentRecipes/control.progress.json`。

---

### `control.toggle` - 二态切换

**Unity 层级结构**：
```
Toggle (GameObject)
├── RectTransform
├── Toggle 组件（项目扩展版，含 m_ActiveContentRoot/m_UnActiveContentRoot 字段）
├── Unselected (子节点)
│   ├── RectTransform
│   └── Image 组件
└── Selected (子节点)
    ├── RectTransform
    └── Image 组件
```

**默认样式**：
```yaml
# Toggle 组件
isOn: false  # 默认未选中
toggleTransition: Fade  # 淡入淡出动画
interactable: true

# 两态子节点
unselected:  # 未选中状态显示
  raycastTarget: false
selected:    # 选中状态显示
  raycastTarget: false
```

**配方依据**：基于 2026-07-27 扫描 770 个 Prefab，564 个 Toggle 实例，Rank 1 配方占 24.5%（结构高度统一）。项目使用扩展 Toggle，增加了 `m_ActiveContentRoot`/`m_UnActiveContentRoot` 字段。配方详见 `Assets/Editor/ComponentRecipes/control.toggle.json`。

---

### `feedback.red-point` - 红点提示

**Unity 层级结构**：
```
RedPointWatcher (GameObject)
├── RectTransform
├── LR.UIRedPointWatcher 组件
└── RedPoint (子节点，追加到最后)
    ├── RectTransform
    └── Image 组件
```

**默认样式**：
```yaml
# RedPoint 子节点 (Image 组件)
redPoint:
  raycastTarget: false
  color: "#FF0000"
  
# UIRedPointWatcher 组件默认值
updateInterval: 0.2
redPointType: None  # 运行时动态设置
```

**配方依据**：基于 2026-07-27 扫描 770 个 Prefab，245 个 UIRedPointWatcher 实例，Rank 1 配方占 29.0%。红点节点位置不固定（取决于父节点其他子节点数量），新配方采用追加模式（`position: last-child`）。配方详见 `Assets/Editor/ComponentRecipes/feedback.red-point.json`。

---

### `content.item-icon-root` - 物品图标动态挂载点（用于道具展示）

**Unity 层级结构**：
```
ItemIconRoot (GameObject)
└── RectTransform
```

**用途**：
- **专门用于显示游戏道具**（装备、材料、货币、消耗品等）的动态容器
- 运行时通过 `ItemIconBase.Allocate(Transform parent)` 动态实例化完整的物品图标 Prefab
- 该 Prefab 包含图片、数量文本、点击事件、选中框等完整功能
- 不在生成阶段挂载任何 UI 组件，仅作为占位容器

**字段类型要求**：
```csharp
[SerializeField] Transform m_ItemIconRoot;  // 或 RectTransform
```

**运行时调用示例**：
```csharp
void ShowReward(int itemId, int count)
{
    ItemIconBase itemIcon = ItemIconBase.Allocate(m_ItemIconRoot);
    itemIcon.SetInfo(itemId, count);
}
```

**使用频率**：142 次（项目中最高频的动态 UI 组件），远超 BuffIcon(14)、GoodsIcon(5)、CommonIcon(3)。

**对比其他图标类型**：
- `content.icon`：静态 `Image` 组件，用于 UI 状态标识（如 LockBadge/ClaimedMask），字段类型 `Image` 或 `GameObject`
- `content.async-icon`：异步加载非道具图标（如头像），使用 `RawImage` + `AsyncIcon`，字段类型 `RawImage` 或 `GameObject`
- `content.item-icon-root`：道具专用动态容器，运行时实例化完整组件，字段类型 `Transform`

---

### `content.buff-icon-root` - Buff 图标动态挂载点（用于战斗状态显示）

**Unity 层级结构**：
```
BuffIconRoot (GameObject)
└── RectTransform
```

**用途**：
- **专门用于显示战斗 Buff/Debuff 状态图标**（增益、减益、时限效果等）
- 运行时通过 `BuffIcon.Allocate(Transform parent)` 动态实例化完整的 Buff 图标 Prefab
- 该 Prefab 包含图标、层数文本、倒计时、呼吸光效等完整功能
- 不在生成阶段挂载任何 UI 组件，仅作为占位容器

**字段类型要求**：
```csharp
[SerializeField] Transform m_BuffIconRoot;  // 或 RectTransform
```

**运行时调用示例**：
```csharp
void ShowBuffIcon(int buffId)
{
    BuffIcon buffIcon = BuffIcon.Allocate(m_BuffIconRoot);
    buffIcon.SetData(buffShowData, startTime);
}
```

**使用频率**：14 次（次高频动态 UI 组件）。

**典型场景**：
- 角色状态栏（显示增益/减益效果列表）
- 技能面板（显示技能附带的 Buff）
- 战斗结算（显示触发的 Buff 记录）

---

### 状态 UI 组件说明

**LockBadge / ClaimedMask 等状态指示器**：
- 这类组件用于显示"锁定""已领取""已完成"等状态
- 字段类型通常是 `GameObject`（通过 `SetActive` 控制显示/隐藏）
- **不需要挂载 `AsyncTexture` 或 `AsyncIcon`**，因为它们的图片是静态的（设计期确定）
- 生成时使用 `content.icon`（会添加 `Image` 组件）

**区分原则**：
- 需要**运行时异步加载大图**（背景、立绘） → `content.async-image`（挂载 `AsyncTexture`）
- 需要**运行时异步加载非道具图标**（头像、徽章） → `content.async-icon`（挂载 `AsyncIcon`）
- 需要**运行时动态实例化完整道具组件** → `content.item-icon-root`（空容器，道具专用）
- 需要**运行时动态实例化完整 Buff 组件** → `content.buff-icon-root`（空容器，Buff 专用）
- **静态图片**（设计期确定，如状态徽章） → `content.icon`（`Image` 组件）
- **纯状态控制**（只需 SetActive，不显示图片） → 空 GameObject（不使用任何 content 组件）

## HTML 属性语义

| 属性 | 用途 |
|---|---|
| `id` | 当前 HTML 文档内稳定且唯一的节点标识 |
| `data-lr-component` | 本文档白名单中的 Unity UI 语义组件 ID |
| `data-lr-template` | 可复用模板的稳定名称或组件所使用的模板名称 |
| `data-lr-slot` | 组件配方中的命名子槽位 |
| `data-lr-bind` | 展示数据的业务绑定键 |
| `data-lr-action` | 点击、切换等交互的业务动作键 |
| `data-lr-visible-when` | 业务可见条件，不承载 CSS 布局信息 |
| `data-lr-bake` | 转换阶段的烘焙控制值，具体值由转换器约定 |

锚点、Pivot、布局、方向、尺寸和层级不新增属性表达。DOM 层级表示 Unity 层级；CSS 与浏览器计算结果表示视觉布局；转换器据此生成 RectTransform。

## 扫描依据

白名单初版来自 Unity 2022.3.62f2 项目 `Assets/Resources/PanelUI` 的 755 个 Prefab，并抽查 30 个通用弹窗、活动、奖励、通行证、背包、商店和列表 Prefab。高频组件包括：

- `RectTransform` 754
- `Image` 711
- `TextMeshProUGUI` 658
- `LR.RaycastArea` 590
- `Button` 567
- `LR.Localizer` 539
- `LR.AsyncTexture` 419
- `ScrollRect` 162
- `LR.ScrollView` 129
- `LR.SingleScrollView` 97
- `LR.UIRedPointWatcher` 83
- `LR.LRProgressBar` 76

多数 UI 是展开层级而非公共嵌套 Prefab，因此语义 ID 必须映射“能力 + 层级配方”，不能只映射单个 MonoBehaviour 类名。
