# 交互契约比对

## 定位

Demo 是 Web 原型，资源、字体、分辨率都和 Unity 不同。**它不提供像素标准**，提供的是**交互语义**：

> demo 里那个区域能滑，游戏里也得能滑；demo 里是单选切换，游戏里也得是单选切换。

样式可以不同（prefab 资源要适配当前项目），**交互不能不同**。UI 组件用错会静默改变代码行为：本该是 ScrollRect 的位置放了普通容器，列表就永远只显示第一屏；本该是 ToggleGroup 的地方用了独立 Toggle，就变成可多选。

这条链路的验证目标是：**demo 的每个交互点，在 prefab 与运行时都有对应的、正确的组件承接**；没有承接就是缺陷，不是“样式差异”。

---

## 一、三层契约模型

| 层 | 名称 | 问的问题 | 失败含义 |
|---|---|---|---|
| **C1** | 类型契约 | 这个位置上挂的是不是“对的那种组件”？ | `component_type_mismatch`：Toggle 挂成 Button、缺 ScrollRect、列表模板缺 ItemIcon |
| **C2** | 能力契约 | 组件配好了没？能不能真的用？ | `interaction_unavailable`：ScrollRect 没绑 content、Button 无 targetGraphic、ToggleGroup 缺失 |
| **C3** | 行为契约 | 操作一下，反馈对不对？ | `interaction_behavior_mismatch`：滑不动、点不响应、切页不换内容 |

三层是递进的，但**不能互相代替**：

- C1 通过不代表 C2 通过（有 ScrollRect 但没绑 content）
- C2 通过不代表 C3 通过（滚动组件齐全，但 `movementType` 配成了 Clamped 后 content 尺寸为 0）
- 只做 C1/C2 的面板，判定上限是 `runtime_config_only`，**不能写 passed**

---

## 二、契约的权威顺序

```
test-cases.md / design/*.md        （设计意图，最独立）
        >
demo/src/**/*.tsx + 样式            （原始交互意图）
        >
demo/unity/*.tsx / *.json          （翻译产物，只用于定位与数值校对）
        >
C# 源码                             （不定义期望交互，只用于风险分级与寻址）
```

**C# 不能作为契约来源。** 用实现去校验实现是循环论证：代码里写了 `onClick`，只能证明“它想被点”，不能证明“demo 里这里应该可点”。C# 在这一步只有两个用途：

1. **安全分级**：追 `AddListener` 到 handler，判断发了什么
2. **寻址**：定位 prefab 路径、字段名、刷新入口

`demo/unity/*.tsx` 同理只做定位辅助。当三层冲突时，以更靠上的层为准，并在报告里记录冲突。

---

## 三、从 Demo 提取交互语义

逐区域扫 `demo/src/**/*.tsx` 和样式，回答“这个区域能干什么”，而不是“长什么样”。

| 区域特征 | Demo 语义 | 来源 | Unity 等价契约（期望组件） |
|---|---|---|---|
| `overflow-y/x: auto` + 内容超出 | 滚动 | 样式/容器 | `ScrollRect` + content/viewport + 方向 + 可滚动尺寸 |
| `overflow` 但内容不超出 | **不滚动** | 样式 | 可以有 ScrollRect，也可以没有；不得据此判缺陷 |
| flex row / column | 排布 | 样式 | 布局组或手动定位，**不应有** ScrollRect |
| `.map()` 渲染 | 重复列表 | 源码 | `ScrollView`（SE 池化）或 ScrollRect + 模板；断言 `totalCount` |
| `onClick` | 可点击 | 源码 | `Button` + interactable + 已挂监听 |
| `useState` + active 类名（同组互斥） | 单选切换 | 源码 | `Toggle` + `ToggleGroup`，exclusive |
| `onChange` + 多选 | 多选 | 源码 | 独立 `Toggle`，**不应**共用 ToggleGroup |
| `<input>` | 可输入 | 源码 | `TMP_InputField`（如项目有等价能力） |
| `onScroll` / IntersectionObserver | 加载更多 | 源码 | ScrollView 刷新回调；无等价物则标 unsupported |
| hover / tooltip | 悬停提示 | 源码 | 项目能力；无等价物则标 unsupported |

---

## 四、交互契约表（每个面板必产出）

```markdown
| # | 区域 | demo 证据 | 期望操作 | 期望反馈 | prefab 路径 | 期望组件 | 代码引用 | 安全 | C1 | C2 | C3 | 结论 |
|---|------|-----------|----------|----------|-------------|----------|----------|------|----|----|----|------|
| 1 | 卡片列表 | demo App.tsx:42 overflow-y | 上下滑动 | 内容位移，可滚到底 | Body/CardScroll | ScrollRect+ScrollView | MonthCardPage.cs:88 | safe | pass | pass | C3b pass | ok |
| 2 | 购买按钮 | demo App.tsx:71 onClick | 点击 | 打开购买弹窗 | Card[0]/BtnBuy | Button | MonthCardCell.cs:340 | unsafe(pay) | pass | pass | — | manual |
```

字段说明：

- **demo 证据**：源码路径 + 行号 / 样式属性。没有证据的交互不许进表，否则是猜的
- **安全**：见第九节。分 `safe` / `read_only_request` / `unsafe(reason)`
- **C1/C2/C3**：`pass` / `fail` / `not_applicable` / `blocked` / `inconclusive`
- **结论**：`ok` / `defect` / `manual` / `unsupported`

表里必须覆盖 demo 中**所有**交互点。做不到的，写进“未映射交互”并说明原因——**空行本身就是缺陷**。

---

## 五、覆盖率与门禁

```
safe_total      = 安全列为 safe 的交互点总数
safe_c3_done    = 其中 C3 实际执行且通过的
critical_done   = 关键交互中实际执行的
```

关键交互（critical）定义为：**该面板至少各有一个**

- 滚动类（ScrollRect / ScrollView 滑动）
- 切换类（Toggle / ToggleGroup）
- 安全按钮（关闭、切页、展开等，不含支付/领取）
- 关闭（面板能正常退出）

门禁：

| 情况 | 允许的最高判定 |
|---|---|
| `safe_c3_done == safe_total`，且无 unsafe 交互点 | 可给 `runtime_passed` / `runtime_passed_mock` |
| 存在 unsafe 交互点，其余全过 | `runtime_partial_unsafe`（不算 passed） |
| 有 safe 交互点未执行 C3 | `runtime_interaction_incomplete` |
| critical 有任一未执行 | **一律不得 passed**，最低 `runtime_interaction_incomplete` |
| 只做了 C1/C2 | `runtime_config_only` |

报告必须写出 `safe_c3_done / safe_total`、`unsafe_total`、`critical_done`。只写“通过”不写分母视为不合格。

---

## 六、C1 类型契约

判定目标：**位置上挂的组件，类型对不对。**

检查方式：

```csharp
// 期望基类/接口 → 实际组件
bool ok = typeof(Button).IsInstanceOfType(actualComponent);
```

规则：

1. **用 `IsInstanceOfType`，不用 `GetType() ==`**。子类（`ExButton`、项目自封装 Button）应当算通过
2. **区分绑定来源**，两者都要记录，结论不同：
   - `binding_source=serialized`：`[SerializeField]` 字段非空且类型可赋值
   - `binding_source=runtime`：运行时 `GetComponent<T>()` 拿到且类型正确

   serialized 为空的字段若运行时才赋值，标 `runtime_bound`，**不算绑定失败**，但要说明来源
3. **`GameObject` / `Transform` 类型字段的检查是空检查**：`typeof(GameObject).IsInstanceOfType(x)` 恒真，等于没验。这类字段必须同时断言**它身上有期望组件**：

   ```csharp
   // 错：只判非空
   if (go != null) pass;
   // 对：判它挂的是不是对的东西
   if (go != null && go.GetComponent<ScrollRect>() != null) pass;
   ```

4. **数组/列表逐元素检查**，不能只看第一个或 `Length > 0`
5. **列表模板**：模板节点上的组件也要按期望检查，模板挂了错误的 Item 类型会整列渲染错

常见 `component_type_mismatch`：

| 现象 | 期望 | 实际 |
|---|---|---|
| 能滑但滑不动 | `ScrollRect` | 普通 `RectTransform` 容器 |
| 点了没反应 | `Button` | 只有 `Image` |
| 多选变成互斥 | 独立 `Toggle` | 全组共用 `ToggleGroup` |
| 单选变成可全关 | `ToggleGroup.allowSwitchOff=false` | `true` |
| 图标空白 | `ItemIcon` | `Image` |
| 文本不换行/截断 | `TextMeshProUGUI` + `enableWordWrapping` | `Text` 或换行关闭 |

---

## 七、C2 能力契约

组件类型对了，还要能用。

### 滚动

| 检查项 | 规则 |
|---|---|
| content / viewport | 都非空，且 content 是 viewport 的子节点 |
| 方向 | `horizontal` / `vertical` 与 demo 语义一致；不得两个都开（除非 demo 明确双向） |
| movementType | `Elastic` 或 `Unrestricted`；`Clamped` 需确认内容不超界 |
| 可滚动性 | **条件断言**：仅当 `content.size > viewport.size` 时才要求可滚动。数据不足导致滚不动是正确行为，不是缺陷 |
| SE `ScrollView`（池化） | 断言 `totalCount == 期望条数`，**不要数子节点实例数**（分帧创建，`m_MaxCreateCountPerFrame=1`，第一次读必然偏少） |
| 子节点可见 | `content` 的 `anchoredPosition` 初始值不应导致内容跑出 viewport |

### 点击

| 检查项 | 规则 |
|---|---|
| `interactable` | 与期望状态一致（置灰态要 false） |
| `targetGraphic` | 非空 |
| 监听 | `GetPersistentEventCount()` **不能**用来证明有监听。运行时 `AddListener` 不落 persistent 列表，0 是常态 |
| 射线可达 | 见第十一节 |
| 遮罩 | 上层没有意外 `<Image raycastTarget=true>` 覆盖按钮 |

### 切换

| 检查项 | 规则 |
|---|---|
| ToggleGroup | 单选组必须存在且 `allowSwitchOff=false` |
| 初始选中 | 有且仅有一个 `isOn=true`（单选组） |
| 绑定 | `graphic` / `targetGraphic` 非空 |

### 面板级

| 检查项 | 规则 |
|---|---|
| `CanvasGroup` | 打开态 `alpha>0`、`blocksRaycasts=true`、`interactable=true` |
| `GraphicRaycaster` | Canvas 上有，否则整个面板点不到 |
| `EventSystem` | 场景里有且 active；缺了所有点击验证都作废 → `runtime_blocked_tooling` |

---

## 八、C3 行为契约

C2 通过后实际打一下。**必须走 UI 事件链，不能直接调 handler。**

### 铁律：不要 `onClick.Invoke()`

```csharp
// 禁止：跳过 raycast、跳过 interactable 判定，等于伪造
button.onClick.Invoke();

// 正确：走真实事件
var handler = ExecuteEvents.GetEventHandler<IPointerClickHandler>(target);
var data = new PointerEventData(EventSystem.current) { position = screenPos, button = PointerEventData.InputButton.Left };
ExecuteEvents.Execute(handler, data, ExecuteEvents.pointerDownHandler);
ExecuteEvents.Execute(handler, data, ExecuteEvents.pointerUpHandler);
ExecuteEvents.Execute(handler, data, ExecuteEvents.pointerClickHandler);
```

理由：`Invoke()` 会绕过 `interactable=false`、被遮罩挡住、raycast 不可达等真实失败。这些恰恰是最常见的 UI 缺陷。

### 点击配方

1. 用 `RectTransformUtility.WorldToScreenPoint` 取元素中心
2. `EventSystem.current.RaycastAll` 取命中栈
3. `GetEventHandler<IPointerClickHandler>(hitTop)` 解析出真正接收点击的对象——**不要求命中最上层本身就是按钮**，按钮的子图标挡住是正常的
4. 逐层执行 down / up / click
5. 断言反馈

### 滚动配方（拆两种）

| 子项 | 做法 | 断言 | 强制 |
|---|---|---|---|
| **C3a** | 直接设 `scrollRect.normalizedPosition`（或 `verticalNormalizedPosition`）在 0 / 1 之间切换，等一帧 | `content.anchoredPosition` 变化量 > 阈值 | 每个滚动点必做 |
| **C3b** | 构造 `PointerEventData` + `ExecuteEvents.dragHandler` / `initializePotentialDrag`，模拟真实拖动 | 同上 + 无异常 | **每个面板至少一次** |

只做 C3a 不足以证明“用户能拖动”（C3a 绕过了 drag 判定和 `draggable` 配置）。`safe_total` 覆盖统计以 C3b 为准，C3a 只算预检。

SE 池化 `ScrollView`：滚动后断言 `totalCount` 不变、可见 cell 的索引变化；不要期待固定实例数。

### 其他配方

| 交互 | 做法 | 断言 |
|---|---|---|
| 单选切换 | 点击目标 Toggle，等一帧 | 目标 `isOn=true`，同组其他全 false |
| 多选切换 | 点击 | 只翻转目标，其他不变 |
| 展开/收起 | 点击表头 | 目标区域 `active` 翻转 / 高度变化 |
| 列表刷新 | 切页或改数据后调刷新入口 | `totalCount` 与数据条数一致 |
| 关闭 | 点击关闭按钮 | 面板 GameObject inactive 或从 UIModule 打开列表消失 |
| 输入 | 设 `TMP_InputField.text` + `onEndEdit` | 业务侧收到值（注意：这不等于真实键入，标 `mock` 输入） |

### 异常处理

每次实际交互 try/catch。handler 抛异常记 `inconclusive` 并带堆栈，不打断整批，也不自动归因为缺陷（可能是 mock 数据不满足前置）。

---

## 九、安全分级：按 handler，默认拒绝

**不能按面板分级，也不能按按钮名字分级。** 同一面板里“关闭”是安全的、“购买”是危险的。必须追到 handler。

### 追踪方法

从目标元素的绑定反查：

```csharp
var btn = target.GetComponent<Button>();
// 运行时监听
var field = typeof(Button).GetField("m_OnClick", BindingFlags.NonPublic | BindingFlags.Instance);
var evt = (UnityEvent)field.GetValue(btn);
int n = evt.GetPersistentEventCount();   // 可能为 0，不代表没有监听
```

persistent 为 0 时，回到 C# 源码读 `AddListener(...)` 实际传的方法名，再用 `reflection-method-find` 定位。**追不到就判 unsafe**，不做乐观假设。

### 危险信号（命中任一 → unsafe）

| 类别 | 例子 |
|---|---|
| 支付 | `RechargeHelper.DoPay`、任何 SDK 购买入口 |
| 发请求 | `Send*`、`Request*`、`*Module.*Request`、RPC / Service 调用 |
| 消耗 | `UseItem`、扣积分/钻石、`Cost*` |
| 写 Record | 任何 `Record` 写入、领奖、状态落库 |
| 写本地存档 | `LocalPlayerConfig.SetDictionary` / `GetDictionary` 写入、`PlayerPrefs.Set*`、红点 `RecordRedPoint` |
| 改持久状态 | 切账号、重置、删档 |

### 分级结果

| 值 | 含义 | 处理 |
|---|---|---|
| `safe` | 纯本地且不改任何持久状态（滚动、切页、展开、关闭、纯 UI 显隐） | 必须 C3 |
| `read_only_request` | 只读请求（刷新数据、查询），不发写操作 | 可执行，标 `mock`；失败不判缺陷 |
| `unsafe(reason)` | 命中上表任一 | **禁止执行**，进人工清单 |

### 混合元素的处理

一个元素只要**任一**监听是 unsafe，整个元素判 unsafe。不能“只测安全的那个监听”。若一个父容器下混有安全子按钮和 unsafe 子按钮，按子元素分别判，父容器本身的点击判 unsafe。

### 一个反直觉的点

`GetPersistentEventCount() == 0` **不代表安全**，也不代表没绑定。它只说明没用 Inspector 拖拽绑定。大量 SE 代码是运行时 `AddListener`，此值为 0 且 handler 可能是支付。

---

## 十、反向扫描（P1，人工复核）

正向表只覆盖“demo 画了什么”。prefab 上还可能多挂了 demo 没有的交互——多出来的按钮、误加的 ToggleGroup、错误的 ScrollRect。

用运行时扫描比对：

```csharp
var selectables = panel.GetComponentsInChildren<Selectable>(true);
var scrolls    = panel.GetComponentsInChildren<ScrollRect>(true);
// 逐个与契约表比对：表里没有的 → unmapped_interaction
```

对 prefab 资产（不在 Play 中）：

```csharp
var go = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
```

差异分类：

| 情况 | 判定 |
|---|---|
| 表里没有、prefab 有可交互组件 | `unmapped_interaction`（P1，需人工确认是否有意为之） |
| 表里有、prefab 没有 | `component_missing`（P0 缺陷） |
| 表里期望 A 类型，prefab 是 B 类型 | `component_type_mismatch`（P0 缺陷） |

反向扫描默认只跑 `Selectable` + `ScrollRect` + 实现 `IPointerClickHandler`/`IDragHandler` 的 `MonoBehaviour`。全量扫描开销大，非必要不做。

---

## 十一、射线可达性

C2 的射线检查是本层的核心价值：**组件都对但点不到**，是最难发现的缺陷。

步骤：

1. 元素中心 `WorldToScreenPoint` → `EventSystem.current.RaycastAll`
2. 取命中最上层（`results[0]`）
3. `ExecuteEvents.GetEventHandler<IPointerClickHandler>(results[0].gameObject)` 解析接收者
4. 判定：

| 情况 | 结论 |
|---|---|
| 解析结果 == 目标或其子节点 | 可达 |
| 命中的是目标的后代 | 可达（子图标挡住是正常的） |
| 被无关节点挡住 | `unreachable_interaction`，报告里写出最上层节点路径 |
| 元素在 viewport 外（滚动区域未滚到） | `not_applicable`，先滚进视野再测 |
| `interactable=false` 且期望 false | `not_applicable` |
| 无 `EventSystem` / 无 `GraphicRaycaster` | `runtime_blocked_tooling` |

稳定性：raycast 结果受布局刷新时机影响。失败时等一帧重试，最多 2 次；仍失败记 `inconclusive`，不直接判缺陷。

---

## 十二、语义替换（P1，人工）

组件对、行为对，但语义变了。自动判定不可靠，列为人工复核项：

| 现象 | 例子 |
|---|---|
| 应该“打开新界面”变成了“原地展开” | 购买按钮直接展开详情，而不是打开 `MonthCardBuyPanel` |
| 应该“单选”变成了“点击累加” | 卡池切换变成了多选叠加 |
| 应该“即时生效”变成了“刷新后生效” | 勾选后要重开面板才变 |
| 应该“关闭弹窗”变成了“关闭整个活动” | 关闭层级错 |

这类问题在 C3 里表现为“技术上通过但看着不对”，报告结论写 `manual_review_required`，说明差异点。

---

## 十三、Demo 没画的状态

以 `test-cases.md` 为准，例如：

- 未达成置灰
- 空列表 / 空态
- 已领取 / 已购买
- 满级 / 长文本溢出

Demo 在这里只作视觉参考，不作断言源。需要造状态时走 `mock-data-shim.md`。这些状态下的交互同样要过 C1/C2/C3，不能只截图。

---

## 十四、能力缺口

Demo 有、项目没有等价组件的交互（hover tooltip、拖拽排序、长按预览）：

- 标 `interaction_unsupported`
- 说明缺什么、建议人工或策划确认降级
- **不算失败**，但也不能悄悄当成“已覆盖”，要从 `safe_total` 里扣除并写明

---

## 十五、断点定位

| 断在哪 | 表现 | 责任段 |
|---|---|---|
| demo 有滚动，TSX 没写滚动组件 | 翻译丢失 | 建议用户显式触发 `/lr-openspec-ui-prefab` 重生成 |
| TSX 写了，Prefab 没组件 | 生成失败 | 生成器 / 配方 |
| Prefab 有组件，类型不对 | `component_type_mismatch` | 生成器 / 配方 |
| Prefab 有组件，content/viewport 没绑或参数错 | 滚不动 | 生成配置 |
| Prefab 全对，首次打开正常、刷新后失效 | 运行时覆盖 | 运行时代码 |
| Prefab 全对，但被遮罩挡住 | 射线不可达 | prefab 层级顺序 |
| 组件行为都对，语义不同 | 语义替换 | 设计 / 代码实现 |

断点比“通过/失败”更有价值，报告里必须写清。

> 发现断点在 prefab 生成侧时，**只在报告里给建议，不要自动串到 `lr-openspec-ui-prefab`**。是否重生成由用户显式触发。

---

## 十六、输出

每个面板一张交互契约表（第四节格式），外加：

```
覆盖率: safe_c3_done=6/8  unsafe_total=2  critical_done=4/4
未映射: 2（Card[1] 上的角标点击，demo 无对应交互）
unsupported: 0
manual_review: 1（购买按钮预期打开弹窗，实际原地展开）
```

再附每个 C1/C2/C3 项的证据（组件实例、断言值、截图路径）。**没有证据的 pass 不算 pass。**

---

## 十七、入口 / 页签不是 demo 交互，但同样要验

demo 只画页面内容，画不出“这个页签会不会被父面板过滤掉”。所以页面内契约（C1/C2/C3）再全，也只能证明“用户已经站在这个页面上之后，页面是对的”。

新增/修改页签或入口的 change 还要单独过入口链路：

| 层 | 检查 | 不在这一层验的后果 |
|---|---|---|
| E1 配置 | 入口/页签 func 的 `isOpen` 与开放条件 | 页签被父面板静默过滤 |
| E2 父面板 | 父面板页签列表包含目标 funcID | 目标页根本无法从 UI 到达 |
| E3 真实点击 | 入口卡片 → 页签 → 目标页 active | 卡片 handler / 页签点击断链 |

`ui-open` 目标页会把 E1~E3 全部绕过。入口类 change 的 `entry_verified=false` 是阻断项，不是人工清单条目。配方见 `unity-runtime-verify.md` 的“页签 / 入口类 change：父面板链路”。
