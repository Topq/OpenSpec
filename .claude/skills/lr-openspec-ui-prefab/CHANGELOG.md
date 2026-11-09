# SE UI Prefab 更新记录

## 2026-11-08

- 生成器新增资源自动修复：原路径不存在时按文件名在 `Assets/` 下查找唯一同名资源；多个候选按目录相近度、`AtlasResources` 优先、路径长度排序，仍并列则失败并列出候选。修复记录写入 `generation-report.json.autoFixes`。
- 生成器新增字段自动修复：`data-field` 拼写错误时，在目标脚本上找唯一类型兼容、名称最相近的字段（规范化匹配优先，其次编辑距离，阈值保守）；多候选并列或没有相似候选时仍然失败。binding 记录新增 `resolvedField`。
- 实测：故意写错字体路径、按钮图片路径和字段名，生成成功且 `autoFixCount=3`，6/6 字段绑定；写成完全无法匹配的资源/字段时仍然 `status=failed`，错误原因明确。
- 补充 UI Prefab 视觉验证方法：`screenshot-isolated` 对 UI 无效（无 Renderer、Overlay 不进相机）；改用临时 additive 场景 + 相机 + `ScreenSpaceCamera` Canvas + `screenshot-camera`。
- 修复 `InjectWindowImageNode`：Window 已有显式 RawImage（`content.async-image` + `window.frame`）时不再注入深色占位 Image，避免盖住真实底框。
- 视觉对照：不画底框/分割线时生成结果是“结构正确但视觉扁平”；按参考补上 `window.frame` 底框和 `divider` 后，生成结果与生产 `MonthCardBuyPanel.prefab` 的框体、标题、正文、分割线、价格、按钮布局基本一致。
- SKILL 版本更新到 v2.4。
- 资源存在性检查前移到 Python 门禁：`validate_layout_json.py --project-root <unity-project-root>` 校验 `font`/`fontMaterial`/`sprite`/`texture` 真实存在，错误目录不再拖到 Unity 才由 auto-fix 兜底（`CommonPanels` 这类路径现在转换后立即报错）。
- 修复按钮文字样式链路：参考扫描 `MaxDepth` 4→5（生产按钮标签位于 `Btn/Graphic/Text`，depth 5）；profile 的 `textFontSize`/`textFont`/`textColor`/`textMaterial`/`textAlignment` 改为路由到按钮的文本子节点，TSX 显式样式仍然优先；profile 聚合新增 `textFont`。
- 生成器新增保存后字段引用核验：binding 记录 `componentType`/`componentPath`，`verification-report.json.bindings` 用 `SerializedObject` 逐项确认字段可序列化、引用非空、目标路径正确；核验失败时 `generation-report.status=failed`。路径比较已兼容 `SaveAsPrefabAsset` 用输出文件名重命名根节点的情况。
- 回归：102 个 Python 测试通过；真实 Unity 生成验证 `boundFieldCount=6`、`bindingCount=6` 全 `ok`；字段拼写错误仍能自动修复（`autoFixCount=1`）并通过保存后核验。
- SKILL 版本更新到 v2.5。

## 2026-11-07

- 新增 `data-role` 与 `tsx_to_json.py --profile`：转换期把 `ui-style-profile.json` 的角色默认样式物化进 JSON，优先级为配方默认 < `data-lr-style` < profile 角色 < TSX 显式覆盖；profile 只提供视觉属性，几何始终以 TSX 为准。
- 新增 `_styleSources`/`_styleProfile` 来源标记；新增 `style_profile_contract.py`，role 缺失给警告，未知 role 直接失败。
- 新增 `data-texture`（仅 `RawImage`）和 `Screen`/`Scene` 的 Sprite/Type/ImageColor 应用；补充 `content.divider` 白名单。
- 生成器改为 fail-closed：缺少脚本类型、组件类型、配方、资源、字段、绑定目标时直接失败，不再 warning 后继续生成。
- 生成器新增 `generation-report.json`（绑定尝试/结果、错误）和 `verification-report.json`（Screen/文本/按钮/RawImage 实际样式快照）。
- 修复 `content.async-icon` 的 `async-texture` 后处理只识别 `LR.AsyncTexture` 的问题，同时支持 `LR.AsyncIcon` 的 `m_RawImage` 绑定。
- 新增 `test_style_role_profile.py`；已有 90 个 Python 回归测试通过，并用真实 profile 在 Unity 中验证角色样式与 6/6 字段绑定。

## 2026-11-06

- 新增步骤 2.5「参考侦察」：MCP 找 1–3 个同类 Prefab，临时部署只读 `LRPrefabReferenceScanner` 输出紧凑 `references.json`，AI 写 `reference-notes.md` 记录选择理由与样式映射。扫描器同时提供 `Tools/LR/Scan Reference Prefabs...` 菜单，便于 MCP 反射不可用时手动验证。
- 新增步骤 2.6「模块级风格档案」：没有同功能参考时，扫描 3–5 个同模块同类界面，用 `build_ui_style_profile.py` 聚合出 `modal.header`/`body`/`price`/`button.*`/`window.frame`/`divider`/`screen` 等角色化样式，生成 `ui-style-profile.json` + `.md`；优先级为同功能参考 > 模块档案 > 白名单默认值。
- 新增节点级样式覆盖：`data-font-size`/`data-color`/`data-font`/`data-font-material`/`data-text-align`/`data-vertical-align`/`data-sprite`/`data-image-type`/`data-image-color`/`data-preserve-aspect`，优先级为配方默认 < 命名样式 < 显式覆盖。
- 修复 `data-color`/`data-text-align`/`data-vertical-align` 解析但未应用的问题；`data-lr-style` 找不到变体时改为报错，不再静默回退基础配方。
- 校验器新增样式目标匹配、路径前缀、颜色范围、对齐成对、RawImage 限制等检查；新增 `test_style_overrides.py`。

## 2026-11-02

- 合入 DL 3fcef71 的注释解析、模板标记、作用域字段校验和输出路径改进。
- 保留 SE ai-game-developer MCP 主流程和素材；新增 SE 工程身份核验、只读参考与运行验证要求。
- 修正来源 JSON 校验契约及 Windows 导入时重绑标准流的问题。
- 增加数组绑定、JSON 契约和 CLI 兜底保护的行为回归测试。
- CLI 仅为备用调用，不替代可用 MCP，不将静态文件检查当作 Unity 验收。
