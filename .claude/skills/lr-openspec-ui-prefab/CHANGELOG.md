# SE UI Prefab 更新记录

## 2026-11-02

- 合入 DL 3fcef71 的注释解析、模板标记、作用域字段校验和输出路径改进。
- 保留 SE ai-game-developer MCP 主流程和素材；新增 SE 工程身份核验、只读参考与运行验证要求。
- 修正来源 JSON 校验契约及 Windows 导入时重绑标准流的问题。
- 增加数组绑定、JSON 契约和 CLI 兜底保护的行为回归测试。
- CLI 仅为备用调用，不替代可用 MCP，不将静态文件检查当作 Unity 验收。
