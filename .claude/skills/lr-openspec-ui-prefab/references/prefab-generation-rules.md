# Prefab 生成规则

## Root 节点自动注入（surface.panel 专用）

### 规则
当 TSX 根节点的 `data-component="surface.panel"` 时，生成器应在该根节点下**自动注入一个名为 `Root` 的满铺容器节点**，作为所有实际内容的父容器。

### 注入位置
```
MixGrowthFundPage (surface.panel, 根节点)
  └─ Root (自动注入，满铺拉伸)
       ├─ Header (用户编写的第一个子节点)
       ├─ ScrollRewards (用户编写的第二个子节点)
       └─ ... (其他用户编写的子节点)
```

### Root 节点规格
- **data-name**: `"Root"`
- **data-field**: 根据根节点脚本类型查找是否有 `m_Root` 字段，如果有则绑定 `"m_Root"`
- **data-pos**: `"(0, 0, 0)"`
- **data-size**: `"(0, 0)"` （拉伸锚点下 sizeDelta 为 0）
- **data-anchor-min**: `"(0, 0)"`
- **data-anchor-max**: `"(1, 1)"`
- **data-pivot**: `"(0.5, 0.5)"`
- **不带 data-component**（纯容器，只有 RectTransform）

### C# 字段绑定
项目中大部分 Page 脚本（继承 `BaseActivityPage` 或 `AbstractPage`）都有以下字段：
```csharp
[SerializeField]
GameObject m_Root;  // 或 Transform m_Root;
```

运行时用于整体显隐控制：
```csharp
protected override void OpenPageUI(object[] args)
{
    m_Root.SetActive(false);  // 初始隐藏，等数据到达
}

protected override void OnRecvActivityInfo(BActivityParamArgs args)
{
    m_Root.SetActive(true);   // 数据到达后显示
    RefreshView();
}
```

### 实施路径
**方式一（推荐）**：在 `tsx_to_json.py` 的输出阶段，检测到根节点是 `surface.panel` 时，在 JSON 的 `children` 数组前插入 Root 节点，原有 children 变成 Root 的 children。

**方式二**：在 `LRUnityLayoutPrefabGenerator.cs` 的 `BuildNode()` 阶段，构建完 `surface.panel` 根节点后，检测是否需要注入 Root（根据根脚本是否有 `m_Root` 字段判断），如果需要则创建 Root GameObject 并重新组织层级。

### 项目实证
已验证的存在 Root 节点的 Page Prefab（位于 `Assets/Resources/PanelUI/WelfareActivityPanel/`）：
- `ActivityDrawKOIPage.prefab` (3 个 Root)
- `ActivityDrawKOIRecordPanel.prefab` (1 个 Root)
- `ActivityDrawKOITicketPanel.prefab` (1 个 Root)
- `ActivityFreeRidePanel.prefab` (3 个 Root)
- `ActivityOnLineRewardPage.prefab` (1 个 Root)
- `ActivitySevenDayTaskPage.prefab` (1 个 Root)
- `MixGrowthFundPage.prefab` (1 个 Root，已生成)
- `SpecialLoginActivityPage.prefab` (1 个 Root)

### Root 节点的 RectTransform 特征
实测数据（从 MCP 读取）：
```
m_AnchorMin: {x: 0, y: 0}
m_AnchorMax: {x: 1, y: 1}
m_AnchoredPosition: {x: 0, y: 0}
m_SizeDelta: {x: 0, y: 0}
m_Pivot: {x: 0.5, y: 0.5}
```

部分 Prefab 的 Root 有非标准坐标（如 `ActivityDrawKOIPage` 的 Root 是 `sizeDelta: (666, 1080), pivot: (0.5, 0)`），但标准形式应为满铺拉伸（如上）。

### 待办
- [ ] 在 `tsx_to_json.py` 或 `LRUnityLayoutPrefabGenerator.cs` 中实现自动注入逻辑
- [ ] 更新 `validate_unity_layout.py`，当检测到 `surface.panel` 根节点且 C# 有 `m_Root` 字段时，自动期望存在 Root 子节点
- [ ] 更新 `unity-layout-attributes.md`，文档化这条隐式规则
