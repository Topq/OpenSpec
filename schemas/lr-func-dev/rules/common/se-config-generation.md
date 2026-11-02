# SE 配置代码生成约定

本文件中的路径均相对于 OpenSpec 根目录。`NeedParseDataMethod` 是 SE 专有机制，不随 DL 工作流更新删除。

## 两个配置维度独立判断

配置文件：`../develop/client/tools/table/table_config/outcode_config.json`。

| 项 | 判断依据 | 必须验证 |
|---|---|---|
| `need_copy` | 客户端静态配置/代码复制需求；含 C/A 字段的表按现有工具配置加入 | 生成文件实际落入 SE 工程，字段存在 |
| `NeedParseDataMethod` | 客户端需要通过生成的表类动态解析此表，例如动态配置整表同步；不是仅凭字段标 S 就加入 | 表名已登记；生成强类型字段和 `ParseData`；动态扩展方法完整 |

- 动态配置且需要客户端本地表解析：判断并登记 `NeedParseDataMethod`，无论原始归属行为 S、C 还是 A；`need_copy` 另按静态用途判断。
- 纯静态客户端表：按 C/A 判断 `need_copy`，不自动加入 `NeedParseDataMethod`。
- 数据只用于服务端或通过独立协议业务字段传给客户端、不使用生成表类动态解析：不因“全 S”自动加入 `NeedParseDataMethod`。
- 每张表都必须给出两项独立、已勾选的结论；不适用写明理由。

## SE 实际生成链

入口：`../develop/client/tools/table/output_code_csharp.bat`。维护前先读实际脚本，不手写替代生成产物。

1. `output_code_csharp_s_to_a.py` 读取 `NeedParseDataMethod`，对命中表在生成期间临时将归属行 S 改为 A，调用 `outputcode.exe`，在 `finally` 中恢复源表原始字节。
2. `add_dynamic_methods.py` 读取同一名单，为生成的表扩展补充动态加载方法。
3. `copy_csharp_code.exe` 按配置复制生成结果。

**不能因为源表标 S 就把 NeedParseDataMethod 表判为非法，也不能为修复 ParseData 而永久将源表全部改 A。** 字段真实归属保留设计结论，生成期临时转换必须恢复。

## 设计、实施和审查的共同验收

- 对照设计、源表归属、实际导出表、生成 C# 和服务端加载代码；SE 动态生成的临时 S→A 是明确例外，不按普通静态表反向规则误报。
- 验证 `ParseData` 与动态扩展实际存在且包含需要的字段；名单登记不等于已生成成功。
- 先区分 SE 数据库配置同步与旧活动文件拉取链：两者都核查 `DynamicConfigModule` 表级适配及对应服务端同步入口；仅旧活动文件拉取链再核查 `IConfigSyncMethod` 活动级注册与 `READ_SYNC_FILE`。数据库入口按实际登记、首次 Ready 请求、版本计划与回包解析验证，不强求活动级接口；仅通过独立业务协议下发的功能也按真实链路判断。
- 执行全量工具前后按 `compile-verification.md`/配置执行规则记录快照；验证源 xlsx 归属及无关表未被意外改动。不要为了验证本次 OpenSpec 文档同步而执行全量导表。
- 实际 bat 含 `pause`，自动化调用须先核对并显式处理交互/等待；不要将“文件存在”写成“可无交互运行”。
