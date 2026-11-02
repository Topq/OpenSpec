# apply/config-execution.md（[Config] 任务执行规则）

> **说明**：本文档定义 `[Config]` 标签任务在 apply 阶段的执行规则。由 `openspec instructions apply` 指路，`lr-openspec-apply` SKILL 在执行 `[Config]` 任务前读取本文件。
>
> **核心约束**：配置表代码必须通过工具生成，禁止手写。

---

## 1. 前置检查

> SE 专有生成规则：先读 `schemas/lr-func-dev/rules/common/se-config-generation.md`；`need_copy` 与 `NeedParseDataMethod` 分开判断，S 字段动态解析走工具临时转换，源表必须恢复。

在开始任何配置表任务前，先确认 `design/config.md` 包含以下必需信息：

1. 字段定义表的"属性"列（S/C/A 标注）
2. "配置加载方式"说明（静态配置/动态配置）
3. "outcode_config.json 配置建议"章节

**如果缺少上述信息，输出错误并停止**：
```
❌ design/config.md 缺少 outcode_config.json 配置建议

无法判断应该配置 need_copy 还是 NeedParseDataMethod。
请先完善 design/config.md 后再执行 [Config] 任务。
```

---

## 2. 策划任务跳过逻辑

以下类型的任务由策划手动完成，AI 直接跳过，不生成代码：
- "策划填写配置表数据"类任务

只有 `[Client]` 标签的 `[Config]` 任务（客户端生成配置表代码）才由 AI 执行，见下方第 3 节。

---

## 3. 客户端生成配置表代码（前置检查通过后执行）

### 步骤 3.1：配置 outcode_config.json

- 文件：`..\develop\client\tools\table\table_config\outcode_config.json`
- 根据 `design/config.md` 的"outcode_config.json 配置建议"：
  - 如果需要 `need_copy` → 在 `need_copy` 数组末尾添加表名（逗号分隔）
  - 如果需要 `NeedParseDataMethod` → 在 `NeedParseDataMethod` 数组末尾添加表名
- 示例：
  ```json
  "need_copy": [
    ...,
    "active_fund_main",
    "activity_mix_growthfund_reward"
  ],
  "NeedParseDataMethod": [
    ...,
    "active_fund_main",
    "activity_mix_growthfund_reward"
  ]
  ```

**判断依据**（S/C/A 属性列）：
- 源表为 S 且需要客户端表类动态解析 → 判断并登记 `NeedParseDataMethod`；纯服务端表不自动加入
- 有任何字段标记为 C 或 A → 添加到 `need_copy`

---

### ⚠️ 步骤 3.2.0：生成前先做全表快照（强制，防止误改其他配置表）

`output_code_csharp.bat` 是全量工具（`outputcode.exe -i {SOURCETABLEDIR}` 扫描 `design/table/default_ios` 整个目录），`copy_csharp_code.exe` 会把生成结果整体覆盖到 `Assets/Script/Table/`。虽然实测中未涉及的表通常不会被改动（工具只对 `outcode_config.json` 名单命中的表重新生成），但**必须验证**，不能假设：

```bash
cd ../develop/client/project/Assets/Script/Table
find . -type f -name "*.cs" | xargs md5sum > /tmp/table_before.md5
```

---

### 步骤 3.2：生成配置表代码

```bash
cd ../develop/client/tools/table
# Windows 环境
cmd /c output_code_csharp.bat
# 或双击 output_code_csharp.bat
```

自动生成 4 个文件：
- `Assets/Script/Table/Generate/{模块}/{表名}/TD{表名}.cs`（数据类）
- `Assets/Script/Table/Generate/{模块}/{表名}/TD{表名}Table.cs`（表管理类）
- `Assets/Script/Table/Extend/{模块}/{表名}/TD{表名}Extend.cs`（数据扩展，首次生成空实现）
- `Assets/Script/Table/Extend/{模块}/{表名}/TD{表名}TableExtend.cs`（表扩展，含动态加载逻辑）

---

### ⚠️ 步骤 3.2.1：生成后立即比对，还原本次改动之外的文件（强制）

```bash
cd ../develop/client/project/Assets/Script/Table
find . -type f -name "*.cs" | xargs md5sum > /tmp/table_after.md5
diff /tmp/table_before.md5 /tmp/table_after.md5 | grep "^[<>]" | awk '{print $2}' | sort -u
```

- 差异列表里**只应该出现本次新增/涉及的表**（新表是纯新增文件，diff 不会显示为"改动"；如果差异列表里出现了任何与本次任务无关的表名，说明生成工具把其他表也重新生成了/覆盖了）。
- 如果发现意外改动的文件，**必须手动还原**（用备份或版本控制恢复该文件的原内容），不能留着未预期的变更进入后续编译和提交。
- 该目录不受 git 管理（客户端工程不是独立 git 仓库），无法用 `git diff` 兜底，**md5 快照比对是唯一的防线，不能省略**。

---

### 步骤 3.3：验证生成结果

- 检查是否生成 4 个文件（见步骤 3.2 清单）
- 对比生成的字段列表与 `design/config.md` 的字段定义是否一致
- **确认强类型字段和动态方法**：按 SE 专有生成规则检查 `NeedParseDataMethod`、临时 S→A 包装器、生成字段、`ParseData` 及动态扩展。需要动态解析的 S 表允许保留 S，由工具在生成期间临时转换并恢复；禁止未经核对永久改 A，禁止直接手写生成文件。
- Extend 目录下的 `TableExtend.cs` 是人工填充骨架，重新生成不会覆盖已有实现——但如果之前手写过 `data.extend.GetInt(...)` 之类的兼容写法，字段变成强类型后要改回 `data.活动id`/`data.xxx` 强类型属性访问，否则会和 Generate 层新增的同名便捷方法（如自动生成的 `GetData(key)`）冲突或不一致。
- 编译验证由 apply SKILL 主流程统一触发，不在本文件重复描述。

---

### 步骤 3.4：生成期契约自检（阻断性）

与 code-review 的 config-001/002 对齐。生成完成后、返回 success 前执行：

1. 生成配置（config-001，P0）：按 SE 专有规则分别核对 `need_copy`、`NeedParseDataMethod`；需要动态解析的表必须登记并验证实际生成的强类型字段、`ParseData` 与动态扩展，不能只检查名单。
2. 三层一致（config-002，P1）：design/config.md 的 S/C/A 与实际导出 txt 表头、生成类/服务端 READ_FILE 三者一致；重导数据后必须重跑 output_code_csharp.bat，避免 Field removed 与字段恒为 0。
3. 生成边界：TD 生成文件只读；扩展只写 Extend 目录下的 partial 文件。

---

## 4. DynamicConfigModule 按同步入口核查接入（阻断性）

**背景**：步骤 3.1-3.3（`outcode_config.json` + `output_code_csharp.bat` + `TDXxxTableExtend.cs` + `DynamicConfigModule_Process.cs::RegisterTable`）只完成了**表级注册**——让框架认得这张表怎么解析。这一步做完后编译能通过，`TDXxxTable` 类也存在，很容易被误判为"已经接入完成"。

**先确认实际同步入口**：旧活动文件拉取链还需要业务 Module 实现 `IConfigSyncMethod`，在 `fileNameList` / `preFileNameList` 声明按需/提前加载的表，并在 `OnInit()` 调用 `m_DynamicConfigModule.RegisterSyncMethod(this)`。数据库配置同步则核查服务端登记/同步、首次 Ready 的数据库配置请求、版本计划和回包解析，不依赖活动级接口，不能为了接表自造活动类型。两种入口都要保留表级注册和 SE `NeedParseDataMethod` 生成验证。

**要求**：
- 走旧活动文件拉取链时，除表级注册任务外，必须包含一条独立活动级注册任务，明确写出：
  1. `XxxModule` 声明实现 `IConfigSyncMethod`
  2. 在 `string[] fileNameList`（或 `string[] preFileNameList`，视是否需要提前加载而定）中列出新增的表名；任一名单可为空，不强求两个都非空
  3. 在 `OnInit()` 中调用 `m_DynamicConfigModule.RegisterSyncMethod(this)`
- 不能把这一步隐含在"创建 XxxModule.cs 骨架"这类笼统任务描述里——必须单独列出，避免被漏掉
- 走数据库入口时，单列对应服务端登记/同步和客户端请求/解析验证任务，活动级接口标为不适用并说明依据。
- 代码模板查询：`codegraph explore "IConfigSyncMethod RegisterSyncMethod fileNameList"`，参考模块：`ActivityDrawKOIModule`、`MarblePlinkoModule`

**验证方式**：
- 编译通过；旧活动链的 `IConfigSyncMethod` 实现无缺失成员报错，数据库入口不强求该接口
- 在设计规定的加载时机（提前加载、打开活动或数据库同步完成）检查 `TDXxxTable.GetData(id)` 能读到已知测试行，不仅看“编译通过、类存在”；无配置行的合法空数据场景单独验证

---

**禁止操作**：
- ❌ 使用 Write 工具手写配置表 CS 代码
- ❌ 复制其他配置表代码后手动替换类名和字段

---

**版本**: v1（从 lr-openspec-apply/SKILL.md 及 rules/tasks/client-implementation.md 迁移合并）
**最后更新**: 2026-08-06
**维护原则**: 配置表生成流程以 `output_code_csharp.bat` 工具行为为准；md5 快照比对是唯一的安全网，不可省略
