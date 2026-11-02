# SE Unity UI：ai-game-developer MCP 优先

适用于 `lr-design` 的真实 UI 参考采集、`lr-openspec-ui-prefab` 的生成与验证。本文只定义工具选择和工程身份，不触发任何 OpenSpec 阶段。

## 1. 连接身份是前置条件

1. 从 OpenSpec 根目录 `config.yaml` 解析 `../develop/client/project`，取得本次 SE 客户端绝对路径。不要从 Unity 窗口标题或同名 `project` 推断工程。
2. 发现当前可用的 ai-game-developer MCP 工具；工具前缀可能带服务标识，不能固定使用某个旧连接 ID。
3. 先查 `editor-application-get-state`。使用该连接的 `reflection-method-find` 查 `UnityEngine.Application` 的 `get_dataPath`，再按返回的真实方法 schema 调 `reflection-method-call`，核对返回值是否等于 SE 工程的 `Assets` 目录。必要时同法查询 `get_unityVersion`。
4. 多个连接必须分别核对；只有路径匹配的连接能用于后续 UI 读写。`ApplicationPath` 是 Unity 安装位置，不能证明工程身份。
5. 编译或导入期间等待并重新读取状态。身份不匹配、无法确认身份或没有 SE 连接时，不对其他工程写入，不把另一工程的成功响应当作 SE 验证通过。

## 2. UI 参考和能力优先级

- MCP 已连接且身份匹配时，优先通过资产/Prefab 查询、GameObject 层级与组件、序列化字段、Console 和截图取得当前 SE 实证。工具名和参数先从当前 schema 发现，不猜测调用结构。
- `lr-design` 仍产出 React 原型；先用 MCP 读取相关 SE 真实 Prefab、组件和素材作为参考，再按策划规则制作原型，不在策划阶段生成正式 Unity Prefab。
- `lr-openspec-ui-prefab` 先校验 TSX/JSON、解析 UIDataTable 的输出路径，部署确定性生成器，再通过 MCP 刷新、等待编译，调用一次 `GenerateFromLayout` 生成一个 Prefab。不要逐节点调用 MCP 拼装 UI。
- 生成后通过同一 SE 连接检查层级、脚本和字段引用、模板、Console；复杂布局优先截图对照原型。文件存在或日志绑定数量不能代替逐字段与引用非空验证。
- 不清空用户已有 Console 记录；按本次操作时间和目标路径区分新增错误。

## 3. 兜底必须有事实依据

- MCP 不可用或所需能力确实不支持时，记录失败工具、错误和未验证范围，再考虑本地 Prefab/YAML/脚本只读检查或 CLI。不能因为 CLI 更新或调用更方便跳过可用的 MCP。
- 策划原型可使用已核对的 SE 静态白名单继续制作，但必须标注“未通过实时 MCP 复验”；组件能力无依据时不虚构。
- CLI 只作为生成兜底。先核对 SE 的 `ProjectVersion.txt`、Unity 可执行文件和工程是否已被编辑器占用；不要并行启动同一工程，不强制关闭用户编辑器。
- CLI 的文件/日志检查属于静态或批处理验证；无法通过 MCP 或实际 Unity 验证的层级、引用、视觉结果必须写为待验证，不声称全部通过。

## 4. 本阶段完成即停止

`lr-design` 的原型、提案和规范以及 `lr-openspec-ui-prefab` 的生成与验证各按自己的流程结束，不自动启动后续技能。维护这些说明时不得调用 `openspec instructions`。
