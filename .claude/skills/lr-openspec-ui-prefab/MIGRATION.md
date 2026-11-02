# SE UI Prefab 同步说明

来源：DL OpenSpec 3fcef71。SE 保留 ai-game-developer MCP 主流程，未切换为 CLI 默认生成。

## 本次合入

- TSX 中 JSX 注释不再被误解析为节点；cellTemplate 标记进入节点树 JSON。
- 可绑定字段按页面/嵌套组件作用域检查；数组按索引绑定，拒绝裸数组和重复元素；值字段不要求 GameObject 引用。
- JSON 校验器直接验证转换器和 C# BuildNode 使用的节点树，不使用旧 rootName/fields/hierarchy 包装契约。
- 保留 SE 的相对锚点 anchoredPosition 契约，不导入 DL 的半画布自动偏移；输出路径按 UIDataTable 的 pName，保留模块目录。
- 字体、材质、贴图与 LRComponentRecipes 保留 SE 版本。

## 默认操作链

读公共 unity-ui-mcp.md → 按 Application.dataPath 确认 SE 连接 → 读取真实 Prefab 参考 → TSX/字段校验 → JSON/结构校验 → 部署 → MCP 刷新和编译等待 → 发现并反射调用生成方法 → MCP 层级/字段/模板/Console/截图验证 → 清理。

## CLI 备用

只有 MCP 不可用或能力不足时，按 SKILL.md 的兜底章节调用 unity_cli_wrapper.py。脚本先检查 UnityLockfile、Assets 内输出路径和节点树 JSON；不会自动关闭编辑器。MCP 恢复后优先补做 Unity 内验证。

## 验证边界

Python 回归测试不等于 Unity 运行验证。MCP 连接失败时，明确报告未能进行真实 Prefab 生成、字段引用和视觉验收，不因静态检查通过声称成功。
