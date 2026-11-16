# 布局几何契约（4c）

> 4c 回答的是：页面在宿主里的位置、大小、比例是否与已验收 demo 一致。
> 本文是通用规则；具体测量配方见 `unity-runtime-verify.md`。

## 1. 适用范围

生成/修改过 Prefab 的页面，按 `data-surface` 分四类：

| 类型 | 典型 | 内容区 | 需要避开的宿主 chrome |
|---|---|---|---|
| fullscreen | 独立全屏面板 | canvas（有安全区则扣除） | 全局 HUD / 顶栏 / 底栏 |
| embedded | 挂在父面板 `MyRoot` 下的页面 | 父面板内容区 | 宿主页签、顶栏、底栏 |
| modal | 弹窗 | 窗框内部 | 窗框、关闭按钮 |
| hud | 常驻 HUD | 锚定区域 | 无；仅在 demo 定义了区域时查比例 |

颜色、贴图、字体风格不在 4c 范围；交互行为仍由 C1/C2/C3 与 E1/E2/E3 负责。

## 2. 坐标系与环境

- 统一用 **canvas 坐标**：`RectTransform` 四角世界坐标 → 根 Canvas 局部坐标 → 加 canvas 半尺寸。
- 报告必须记录 `canvas_size`。
- **首选设计分辨率**：Game View 切到 `Full HD (1920x1080)`（本工程设计分辨率）。
  - 此时 canvas = 1920×1080，x/y 都可与 demo 直接对照。
  - 截图也是 1920×1080，可与 demo 同尺寸并排。
- **降级路径**：环境无法切到设计分辨率时，至少 16:9、≥1280×720；此时 y 轴只做包含/相交，不拿 demo 的绝对 y 对照；布局结论记 `inconclusive`，不能给 `passed`。

## 3. 区域分类与期望值推导

### 3.1 先列区域清单

- demo 的一级区域（页面主要内容容器）与 Unity 对应节点逐一配对。
- demo 有、Unity 没有 → `missing_region`（P1）。
- Unity 有、demo 没有 → `unmapped_region`（P2 / 人工确认）。
- 配对不明确 → `expected_unknown`，进人工。

### 3.2 分类

| 类型 | 识别依据 | 期望值 |
|---|---|---|
| `fixed` | CSS 明确 `width` / `flex-basis` / 固定 px | 1:1 照抄（1920 设计宽下 CSS px = canvas 单位） |
| `percentage` | 百分比宽度/高度 | 父内容区 × 百分比 |
| `flex` | `flex:1` / 无固定宽 | 父内容区 − 已接受 fixed − 间距 |
| `replaced_by_host` | demo 有、Unity 由宿主承担（如宿主页签） | 不参与页面期望 |
| `unknown` | `calc()` / `min-width` / `max-width` / 媒体查询 / 无明确尺寸 | `expected_unknown`，人工复核 |

### 3.3 对齐方式

位置对照优先用**锚定边距离**，不要硬套绝对 x/y：

- 左对齐：左边 = 内容区左边 + padding；
- 右对齐：右边 = 内容区右边 − padding；
- 居中：中心偏移；
- 上/下对齐同理；y 仅在设计分辨率下做绝对值对照。

### 3.4 推导顺序

1. 先定 fixed 与 percentage；
2. 多个 flex 子项按 `flex-grow` 分配剩余空间；
3. gap/padding 作为中间变量参与公式，不单独报缺陷；
4. fixed 失败时，由它导致的 flex 偏差只作为**连带结果**，不重复计缺陷；
5. fixed 被用户豁免后，flex 期望按豁免后的实际值重算。

### 3.5 容差

以 canvas 单位计算，避免不同分辨率下过严或过松：

| 类型 | 容差 |
|---|---|
| fixed | `max(8px, 1% × canvas 宽)` |
| percentage | ±1.5 个百分点 |
| flex | `max(12px, 2% × canvas 宽)` |
| 文本 | 行数 0 误差；宽/高 1px |
| 媒体 fit 模式 | 必须一致；裁切框比例 ±2% |
| gap/padding | 中间量；只有导致最终区域超差或溢出时才报 |

## 4. 五类判定

GL1 只检查一级内容容器（列表 / 详情栏 / 内容根 / 页签条等）。全屏 `Bg`、弹窗 `WindowBg` / `Screen` 遮罩 / dimmer、滚动条、红点与装饰层天然覆盖或紧贴宿主边缘，**不参与 GL1 相交判定**。

| 检查 | 通用规则 | 典型失败 | 严重度 |
|---|---|---|---|
| **GL1 宿主边界** | 页面一级内容容器与宿主 chrome 不相交；内容起点 = 宿主内容区 + 声明内边距 | 内容压在宿主页签下 | P1 |
| **GL2 区域几何** | fixed/percentage/flex 按第 3 节推导；先做区域清单比对 | 详情栏 860 vs demo 628 | fixed/percentage P1；纯 flex 连带 P2 |
| **GL3 文本适配** | 按 demo 的 CSS 意图判：`nowrap` → 必须 1 行且不裁切；正常换行 → 行数可变但不溢出；`ellipsis` → 允许截断但要有省略号 | 收窄后副标题折行 | nowrap 折行/裁切 P1；省略号不符 P2 |
| **GL4 元素适配** | 行/列/网格由父区域和 gap 推导；图标/格子比例；整行是否放得下 | 34px 图标塞进 56px 格子；行溢出 | 溢出/重叠/裁切 P1；纯高度差 P2 |
| **GL5 媒体适配** | 按 demo 的 `object-fit` / SVG `preserveAspectRatio` 判 fit 模式 | 应裁切却全图拉伸 | 应裁切/留白却拉伸 P1；裁切框略偏 P2 |

### 4.1 文本（GL3）

- `white-space: nowrap` 或明确的单行标签 → `TMP.textInfo.lineCount == 1`，且文本框宽度按第 3 节容差与 demo 一致（把文本容器当作一个 fixed/percentage/flex 区域推导）；宽度超差时 GL3 不能单独写 pass（缺陷只在 GL2 计一次）。
- 正常换行 → 不裁切：`preferredHeight <= rect.height + 1`，或滚动容器可滚。
- `text-overflow: ellipsis` / 固定高度 + `overflow:hidden` → 允许截断，检查省略号与不溢出。
- 读之前先 `ForceMeshUpdate()`。
- **不要用 `preferredWidth <= 自身 rect.width` 判单行**：开启换行时 TMP 按当前宽度折行后再算 `preferredWidth`，这条接近恒真，不能作为通过依据。

### 4.2 媒体（GL5）

**先定 demo 意图，再判实测模式；只有模式与意图一致才通过。** 不能只看单个组件参数就放行。

| demo | 期望模式 |
|---|---|
| `object-fit: fill` / 无 fit | stretch（拉伸） |
| `object-fit: cover` / SVG `slice` | crop（居中裁切） |
| `object-fit: contain` / SVG `meet` | contain（留白保持比例） |

实测模式识别（按优先级）：

1. **crop（uvRect 裁切）**：`RawImage.uvRect` 非全图，且 `(texW × uvW) / (texH × uvH)` 与显示宽高比接近（±2%）。
2. **crop（父级遮罩）**：`uvRect` 为全图，但图像 Rect 被放大到覆盖父容器，且父容器有 `Mask` / `RectMask2D`。这是合法的 cover 实现，**不是 stretch**。
3. **contain**：`Image.preserveAspect = true`，或图像按贴图比例缩小并留白。
4. **stretch**：`uvRect` 全图、无父级遮罩裁切，且显示宽高比 ≠ 贴图宽高比。

按意图对号：

- 意图 fill → 只接受 stretch；
- 意图 cover → 接受 1 或 2；全图 uv 且无遮罩 → stretch，fail；
- 意图 contain → 接受 3；demo 要 cover 时 `preserveAspect=true` 反而 fail。

### 4.3 列表/网格（GL4）

- 一行 n 个等宽元素，gap g：`itemWidth = (contentWidth − (n−1) × g) / n`。
- 网格 c 列：`cellWidth = (contentWidth − (c−1) × g) / c`，行高同理。
- 检查：单格宽、整行总宽、图标/格子比例、是否溢出或重叠。
- 高度差异默认 P2；只有导致裁切、重叠或滚动异常时才升 P1。

## 5. 截图与证据

- 默认 **1920×1080**、`debugpage 0`、`ui-list-opened-panels` 确认无无关面板。
- 与 demo 同尺寸并排留证；报告记录 `view_resolution`、`view_aspect`、`canvas_size`。
- 比例判定以 canvas 实测为准；截图用于人工比对，不用于替代 GL2。
- 降级环境（非设计分辨率）下，截图只作参考，报告需注明降级。

## 6. 豁免与未知项

- `waived` 必须用户确认并写理由；fixed 被豁免后，flex 期望按豁免后的值重算。
- `expected_unknown`（demo 布局不确定）→ 人工复核，不放行 `passed`。
- `missing_region` → 缺陷（P1）；`unmapped_region` → P2 或人工确认。
- 未豁免的 fail 仍使 change `not_passed`；“这轮只改 SKILL/不改 prefab”不能成为判过的理由。

## 7. 4.5 布局契约表模板

| 区域 | 类型 | demo 证据 | 期望表达式 | 期望(canvas) | 实测(canvas) | 偏差 | 容差 | 严重度 | 结论 |
|---|---|---|---|---|---|---|---|---|---|
| 详情栏 | fixed | `.tc-detail width:628` | 右对齐：内容右 − 628 | 1252~1880 | 1252~1880 | 0 | 19px | P1 | pass |
| 副本列表 | fixed | `.tc-dungeon-list width:112` | 左对齐：内容左 + 112 | 354~466 | 354~524 | +58 | 19px | P1 | fail |
| 立绘 | flex | `.tc-art flex:1` | 内容区 − fixed − gap | 478~1240 | 540~1236 | 连带 | 31px | P2 | 连带，不单列 |

## 8. 四类页面示例

- **全屏页**：内容区 = canvas（或安全区）；自有 header/footer 按 fixed 区域检查；全局 HUD 只做 GL1。
- **嵌入页**：内容区 = 宿主页签之后；demo 的导航 tab 标 `replaced_by_host`；固定区 1:1，flex 吃剩余。
- **弹窗**：内容区 = 窗框内部；demo 的窗口宽高是 fixed；内部区域相对窗口内容区推导。
- **HUD**：只查锚定边/角、是否出屏、是否互相遮挡；没有确定比例时不硬判。

## 9. 实测示例：team-challenge（嵌入页）

设计分辨率 1920×1080 下：

| 区域 | 类型 | demo | 期望 | 实测 | 结论 |
|---|---|---|---|---|---|
| 宿主页签 | host | — | 13~333 | 13~333 | GL1 通过（页面从 354 起） |
| 详情栏 | fixed | 628 | 1252~1880 | 1252~1880 | GL2 pass |
| 副本列表 | fixed | 112 | 354~466 | 354~524（170） | GL2 fail（+58） |
| 立绘 | flex | flex:1 | 478~1240 | 540~1236（696） | 列表偏差的连带 |
| 副标题 | text | nowrap | 1 行，240 ≤ 360 | 1 行 | GL3 pass |
| 难度格 | grid | 约 56×66 | 56×66 | 56×88 | GL4 高度偏差，P2 |
| 立绘贴图 | media | `slice`（裁切） | 居中裁切 | 2048×1024 全图拉伸到 696×880 | GL5 fail |

该示例用于说明推导方式，不是固定规则；其他页面按第 1~6 节推导。
