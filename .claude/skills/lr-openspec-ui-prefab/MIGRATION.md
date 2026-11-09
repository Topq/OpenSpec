# SE UI Prefab 同步说明

来源：DL OpenSpec 3fcef71。SE 保留 ai-game-developer MCP 主流程，未切换为 CLI 默认生成。

## 本次合入

- TSX 中 JSX 注释不再被误解析为节点；cellTemplate 标记进入节点树 JSON。
- 可绑定字段按页面/嵌套组件作用域检查；数组按索引绑定，拒绝裸数组和重复元素；值字段不要求 GameObject 引用。
- JSON 校验器直接验证转换器和 C# BuildNode 使用的节点树，不使用旧 rootName/fields/hierarchy 包装契约。
- 保留 SE 的相对锚点 anchoredPosition 契约，不导入 DL 的半画布自动偏移；输出路径按 UIDataTable 的 pName，保留模块目录。
- 字体、材质、贴图与 LRComponentRecipes 保留 SE 版本。

## 默认操作链

读公共 unity-ui-mcp.md → 按 Application.dataPath 确认 SE 连接 → 找同类 Prefab 并用扫描器产出 references.json/reference-notes.md；没有同功能参考时再用 3–5 个同模块界面聚合 ui-style-profile.json/.md → TSX/字段/样式校验 → `tsx_to_json.py --profile` 物化角色样式 → JSON/结构校验 → 部署 → MCP 刷新和编译等待 → 发现并反射调用生成方法 → 读取 generation-report.json/verification-report.json（含 autoFixes）→ MCP 层级/字段/模板/Console/截图验证 → 与参考 Prefab/风格档案对比 → 清理。

## CLI 备用

只有 MCP 不可用或能力不足时，按 SKILL.md 的兜底章节调用 unity_cli_wrapper.py。脚本先检查 UnityLockfile、Assets 内输出路径和节点树 JSON；不会自动关闭编辑器。MCP 恢复后优先补做 Unity 内验证。

## 2026-11-06 增量
## 2026-11-08 增量

- 生成器新增资源与字段自动修复：资源按文件名找唯一同名候选，字段按类型兼容 + 名称相似度找唯一候选；多候选并列时仍然失败。修复写入 `generation-report.json.autoFixes`，binding 记录新增 `resolvedField`。
- 视觉验证改用真实场景相机方案：`screenshot-isolated` 对 UI Prefab 无效（无 Renderer、Overlay 不进相机）；用临时 additive 场景 + `ScreenSpaceCamera` Canvas + `screenshot-camera`，验证后卸载场景并删除临时资产。

## 2026-11-07 增量

- 新增 `data-role` 角色化样式消费：`tsx_to_json.py --profile ui-style-profile.json` 在转换期物化角色默认值，写 `_styleSources`；profile 不覆盖 `data-pos`/`data-size`/`data-anchors`/`data-pivot`。
- 新增 `data-texture`（仅 RawImage）与 Screen/Scene 的 Sprite/Type/ImageColor；`content.divider` 加入组件白名单。
- 生成器改为 fail-closed：脚本/组件/配方/资源/字段/绑定目标缺失直接抛错；新增 `generation-report.json` 和 `verification-report.json`。
- 角色白名单：`modal.header`、`page.title`、`body`、`price`、`button.primary/secondary/close`、`window.frame`、`divider`、`screen`。


- 新增参考侦察：步骤 2.5 用 MCP 找同类 Prefab，临时部署 `LRPrefabReferenceScanner` 输出 `references.json`；参考结果只用于结构/命名/样式映射，不重新做设计。
- 新增模块级风格档案：没有同功能参考时，扫描 3–5 个同模块同类界面，用 `build_ui_style_profile.py` 聚合出角色化 `ui-style-profile.json`/`.md`；优先级为同功能参考 > 模块档案 > 白名单默认值。
- 新增节点级样式覆盖（`data-font-size`、`data-color`、`data-font`、`data-font-material`、`data-sprite`、`data-image-type`、`data-image-color`、`data-preserve-aspect`），优先级低于命名样式、高于配方默认值。
- 行为变化：
  - `data-lr-style` 指向不存在的 `{component}-{style}.json` 时改为**报错**（原为静默回退基础配方）。
  - `data-text-align` 与 `data-vertical-align` 可以单独使用；单独使用时保留配方/后处理里的另一轴，避免破坏已有 TSX。
  - `data-color` 优先作为文本颜色；无文本目标时作为图片颜色别名，`Screen` 节点映射到生成的遮罩 Image；图片颜色仍优先用 `data-image-color`；`RawImage` 只支持 `data-image-color`。
- 部署目录不变：扫描器与生成器同在 `Assets/Editor/LRUIPrefabGen/`，步骤 8 统一清理。

## 验证边界

Python 回归测试不等于 Unity 运行验证。MCP 连接失败时，明确报告未能进行真实 Prefab 生成、字段引用和视觉验收，不因静态检查通过声称成功。
