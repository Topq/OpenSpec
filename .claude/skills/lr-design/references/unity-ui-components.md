# Unity UI 组件白名单

## 使用规则

- Web 只通过 `data-lr-component` 引用下表语义 ID。
- 不把 C# 类型名、程序集名或 Prefab 路径写进 HTML。
- 转换器根据语义 ID 创建 Unity 类型、标准层级和附加组件。
- 功能专用脚本不进入公共白名单；由后续 UI 开发阶段绑定。
- 扩充白名单前必须扫描项目 Prefab、确定稳定配方，并人工评审本文件。

## 首批白名单

| 语义 ID | 用途 | Unity 映射/配方 |
|---|---|---|
| `surface.panel` | 全屏或主面板根节点 | `RectTransform`，按视觉需要附加 `Image` |
| `surface.page` | 面板内页面根节点 | `RectTransform`，保留 DOM 子层级 |
| `surface.modal` | 模态弹窗根节点 | 遮罩层、弹窗容器、阻断点击区域 |
| `control.button` | 可点击按钮 | `Button`、可点击图形、`LR.RaycastArea` |
| `control.toggle` | 二态选择控件 | `Toggle`、选中/未选中视觉、`LR.RaycastArea` |
| `control.input` | 文本输入控件 | TextMesh Pro 输入组件及占位文本 |
| `control.progress` | 进度显示 | `LR.LRProgressBar` 及前景/背景层级 |
| `list.scroll` | 常规滚动列表 | `ScrollRect`、`Viewport/Content`、裁剪组件 |
| `list.single-scroll` | 项目单项复用滚动列表 | `LR.SingleScrollView`、`Viewport/Content/PrefabCell`、`RectMask2D`、`LR.RaycastArea` |
| `content.async-image` | 异步加载大图 | `Image` 与 `LR.AsyncTexture` |
| `content.async-icon` | 异步加载图标 | 图标容器、`Image` 与 `LR.AsyncTexture` |
| `text.localized` | 多语言文本 | `TextMeshProUGUI` 与 `LR.Localizer` |
| `slot.item-icon` | 物品图标业务槽位 | 标准物品图标层级；业务绑定留到 UI 开发阶段 |
| `feedback.red-point` | 红点提示 | 红点节点与 `LR.UIRedPointWatcher` |
| `template.tab-item` | 页签复用模板 | 页签标准层级，配合 `data-lr-template`/`data-lr-slot` |
| `template.reward-cell` | 奖励单元复用模板 | 奖励格标准层级，配合 `data-lr-template`/`data-lr-bind` |

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
