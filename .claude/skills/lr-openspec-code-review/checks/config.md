# 配置表检查项（config 组，共 2 项）

> **SE 适配说明**：GodFort/神域防线及其返工频次是 DL 来源案例，不是 SE 当前文件或接口的证据。实际审查先读 SE `config.yaml` 路由的 ai-core，再用 SE CodeGraph/源码复验；来源案例和缺失的历史附件仅作说明，不作为必读依赖或通过依据。


> 由 `lr-openspec-code-review` 步骤 3 读取，只对本轮涉及配置表变更的变更执行。
> 规则来源：`design/config-structure.md`。
> 档位：**P0 阻断（权重 10）** / **P1 结构契约（权重 5）**。

---

## config-001 outcode_config.json 配置完整性（P0 / 权重 10 / GodFort 实证 0）

**目标**：新增/扩展的配置表已正确加入客户端代码生成配置，客户端能拿到生成代码。

**实际路径**（以工程为准）：`../develop/client/tools/table/table_config/outcode_config.json`。
> 先读 `schemas/lr-func-dev/rules/common/se-config-generation.md`；所有相对工程路径以 OpenSpec 根目录为基准。

**检查点**：

- `design/config.md` 字段表标注了 **C** 或 **A** 的表，必须出现在 `need_copy` 数组；
- `NeedParseDataMethod` 是 SE 专有配置：需要客户端表类动态解析时必须登记，检查生成的 `ParseData`、强类型字段及动态扩展；源表全 S 不自动豁免或自动命中；
- `need_copy` 按静态需求判断，与动态解析名单分开；
- 表名与 `design/config.md` 的表文件名一致（大小写、下划线）；
- 核对实施阶段的生成记录及实际生成文件；没有证据则报告待验证。审查默认只读，不运行全量 `output_code_csharp.bat`，不修改配置或源表。

**检查方法**：

```
Read(../develop/client/tools/table/table_config/outcode_config.json)
```

**违反示例**：

本次新增的 `sanctumbulwark_stage` 含 C 字段，却不在 `need_copy` 中 -> 客户端没有生成类，`GetData()` 编译失败或永远为空。

**报告格式**：

```
❌ config-001: 配置生成配置不完整（need_copy / SE NeedParseDataMethod）
表: <表名>（含 C/A 字段）
文件: tools/table/table_config/outcode_config.json
建议: 在获准的实施/修复阶段补充相应生成配置并运行工具；本次审查只报告，不直接导表
```

**说明**：完全机械可判定，建议在 apply 的 [Config] 任务里同时做成脚本门禁；code-review 保留复核。

---

## config-002 字段 S/C/A 与三层一致性（P1 / 权重 5 / GodFort 实证 5）

**目标**：`design/config.md` 的 S/C/A 标注与**实际导出 txt 表头**、生成类/服务端加载代码三者一致；没有漏标、错标或某一层漂移。

**三层基准（缺一不可）**：

1. `design/config.md` 的“完整字段定义”表（意图）；
2. **实际导出 txt 表头**（数据层，权威）：客户端 `BuildRes/config/*.txt`，服务端 `cons/res/ini/<模块>/*.txt`；
3. 生成代码 / 加载代码：客户端 `Assets/Script/Table/Generate/<分类>/TD<表名>.cs`，服务端 `ST<Table>Config` + `READ_FILE`。

**检查点**：

- 标 **C/A** 的字段出现在客户端生成类中；
- 标 **S/A** 的字段出现在服务端加载结构与 `READ_FILE` 中；
- 反向检查须识别 SE 的 `NeedParseDataMethod` 临时 S→A 生成例外：原始 S 字段按该链路生成客户端字段不判违规；核对源表已恢复。普通静态表再按 S/C/A 判断；标 C 的字段不应被服务端无依据读取；
- **导出层**：设计/生成类里有、但实际导出 txt 没有的字段（或反之）必须报告；
- 重导数据后必须重跑代码生成；否则运行时会出现 `Field :Xxx removed` 的 LogError，客户端字段恒为 0（GodFort 的 `BuildCount` 即为实例）。
- 生成边界：`TD*.cs` 只读不写；需要扩展只能改 `Assets/Script/Table/Extend/TD<表名>Extend.cs`（partial）。

**检查方法**：

```
Read(<客户端工程>/Assets/Script/Table/Generate/<分类>/TD<表名>.cs)
codegraph_explore("ST<Table>Config READ_FILE <模块名>", projectPath: "<服务端工程>")
```

```bash
rg -n "<字段名>" <客户端工程>/BuildRes/config/<表名>.txt
rg -n "<字段名>" <服务端工程>/cons/res/ini/<模块>/<表名>.txt
```

**判定口径**：

- 属性列缺失或写“待定” -> 报“标注缺失”，P1；
- 标注与两端实现不一致，且会导致某端缺字段/多解析 -> 升为 P0；
- 三层任意一层缺字段（设计有、txt 无；txt 有、生成类无；生成类有、txt 无）-> 报“层间漂移”，P1；
- 字段确实双端都不使用 -> 报“疑似冗余字段”，建议人工确认删除。

**违反示例**：

```
| 字段名 | 属性 | 说明 |
|---|---|---|
| BuildCount | A | 建造数量 |

实际情况：导出 txt 已无 BuildCount，生成类仍要求；运行时 LogError，字段恒为 0。
```

**报告格式**：

```
⚠️ config-002: 字段属性/三层不一致
表: <表名>
字段: <字段名>（标注 C/A/S）
问题: 设计有但导出 txt 无 / txt 有但生成类无 / 服务端读了标 C 字段 / 标注缺失
影响: 字段恒为 0 / 解析报错 / 某端缺数据
建议: <修正 design/config.md / 重导 txt / 重跑生成 / 补 Extend>
```
