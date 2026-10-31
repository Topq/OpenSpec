---
name: lr-openspec-apply
description: 按角色过滤执行 tasks.md 任务（前端/后端/策划）。支持多角色组合，逐个执行，实时勾选，支持中断恢复。
---

# OpenSpec Apply（角色过滤执行器）

> ⚠️ **强制项**：步骤 10（生成实施报告）不可省略，即使执行过程中被新需求打断。恢复后必须先补完步骤 10，再视为本次 apply 结束。

## 与 `/opsx:apply` 的关系

| 命令 | 执行范围 | 适用场景 |
|-----|---------|---------|
| `/opsx:apply <id>` | 执行所有任务 | 全栈开发者，或技术负责人 |
| `/lr-openspec-apply <id> <role>` | 只执行指定角色任务 | 前端/后端/策划分工协作 |

**本 SKILL 是 `/opsx:apply` 的角色过滤增强版**。

**本 SKILL 只负责调度**（角色过滤、任务队列、勾选、编译检查点触发）。**具体怎么写代码，规则在 `schemas/lr-func-dev/rules/apply/*.md` 中**，详见步骤 6.3。

---

## 使用方式

### 模式 1：查看任务清单（默认）

```bash
/lr-openspec-apply <change-id> [role]
```

**role 选项**：
- `client` - 前端任务（[Client] + [Contract]）
- `server` - 后端任务（[Server] + [Contract]）
- `config` - 策划任务（[Config]）
- `client,server` - 多角色（逗号分隔，支持任意组合）
- `dev` - 快捷方式，等同于 `client,server`
- `all` - 快捷方式，等同于 `client,server,config`
- 不指定 - 交互式选择角色

**注意**：[Integration] 任务为人工验证阶段，不支持代码生成，会在执行完成后输出验证清单

**输出**：按优先级分组显示任务（前置依赖 → 可立即开始 → 等待依赖），统计数量，等待用户确认。具体格式见步骤3。

---

### 模式 2：执行代码生成

用户确认后，逐个执行任务，实时输出进度（[n/total] 任务ID → 读取规则 → 生成代码 → 验证 → 勾选），最后输出总结。具体格式见步骤6.4和步骤9。

---

## 前置条件检查

执行前自动检查以下文件：

| 文件 | 来源 | 检查命令 |
|-----|------|---------|
| `changes/<id>/tasks.md` | `/lr-openspec-tasks` | `ls changes/<id>/tasks.md` |
| `changes/<id>/design.md` | `/lr-openspec-tasks` | `ls changes/<id>/design.md` |

**若文件不存在**：
```
❌ 错误：缺少必要文件

代码生成依赖 tasks.md 和 design.md，但未找到这些文件。

请先运行：
  /lr-openspec-tasks <id>
```

## 执行逻辑（核心实现）

### 步骤 1：解析参数

```
输入: /lr-openspec-apply growth-fund client
  ↓
解析:
  - change-id = "growth-fund"
  - role = "client"
```

---

### 步骤 2：生成任务队列

#### 2.1 读取 tasks.md

```bash
Read(changes/{change-id}/tasks.md)
```

#### 2.2 筛选任务

**筛选规则**：

| role | 包含的任务标签 | 说明 |
|------|-------------|------|
| `client` | [Client] + [Contract] | 前端任务 + 协议任务（依赖） |
| `server` | [Server] + [Contract] | 后端任务 + 协议任务（依赖） |
| `config` | [Config] | 策划任务 |
| `client,server` | [Client] + [Server] + [Contract] | 多角色，[Contract] 自动去重 |
| `dev` | [Client] + [Server] + [Contract] | 等同于 `client,server` |
| `all` | [Client] + [Server] + [Config] + [Contract] | 所有代码生成任务 |

**注意**：[Integration] 任务不参与代码生成，仅在执行完成后输出验证清单

#### 2.3 初始化队列

```
待执行队列: [1.1, 1.2, 2.4, 4.1.1, ...]  （未完成的任务）
已完成队列: []
已跳过队列: []
```

---

### 步骤 3：显示任务清单

**分组显示**：

1. **⚠️ 前置依赖**（[Contract] 任务）
2. **✅ 可以立即开始**（无依赖或依赖已完成）
3. **⏸️ 等待依赖**（依赖未完成）

**依赖判断逻辑**：
- 从任务描述中提取"依赖任务 X.Y"字样
- 检查依赖任务是否已完成（tasks.md 中是否为 [x]）

**输出总结**：
```
Growth Fund - {role_display} 任务清单
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 任务统计:
  [Contract]: {contract_count} 个任务
  [Client]:   {client_count} 个任务
  [Server]:   {server_count} 个任务
  [Config]:   {config_count} 个任务
  总计:       {total_count} 个任务

⚠️  跳过的任务:
  [Config]:       3 个任务（策划人员负责）
  [Integration]:  8 个任务（人工验证阶段）

执行代码生成？输入 'y' 继续，或直接回车取消:
```

**role_display 映射**：
- `client` → "前端"
- `server` → "后端"
- `config` → "策划"
- `client,server` → "前端 + 后端"
- `dev` → "开发（前端 + 后端）"
- `all` → "全部"

---

### 步骤 4：等待用户确认

**用户输入 `y`** → 继续执行
**用户输入其他或回车** → 退出

---

### 步骤 5：调用 openspec 获取执行规则

```bash
openspec instructions apply --change {change-id}
```

**输出会包含**（详见 `schemas/lr-func-dev/schema.yaml` 的 `apply:` instruction）：
- `rules/apply/{role}-execution.md` 的文件路径指引（按任务分类）
- `config.yaml` 里配置的 `rules.apply` 硬约束（一句话提醒）

**注意**：这个指令只是入口指引，具体执行规则在步骤 6.3 里按任务 tag 读取对应的 `rules/apply/*.md` 文件。

### 步骤 6：循环执行任务

**执行模式**：主agent调度，每个任务派发给一个子agent执行。

**循环流程**：
```
for task in 待执行队列:
  6.1 显示当前任务
  6.2 派发子agent执行任务
  6.3 接收子agent结果
  6.4 编译验证（主agent负责，保留编译检查点逻辑）
  6.5 勾选checkbox（验证通过后）
  6.6 更新队列
```

---

#### 6.1 显示当前任务

```
[{index}/{total}] 执行任务 {task_id} [{tag}] {description}
```

---

#### 6.2 派发子agent执行任务

**调用Agent工具，派发子agent执行当前任务**：

```javascript
Agent({
  description: "执行任务 {task_id}",
  prompt: `
你的任务是执行 OpenSpec apply 阶段的一个具体任务。

**任务信息**：
- 任务ID: ${task_id}
- 任务描述: ${description}
- 任务类型: [${tag}]
- Change: ${change_id}

**执行规则文件**（必读）：
${根据tag映射到对应的rules文件路径，见下方映射表}

**你的职责**：
1. 完整阅读上述规则文件（包含第0节的强制前置检查）
2. 读取 changes/${change_id}/design.md 对应章节
3. 按规则文件执行代码生成（调用CodeGraph、生成文件等）
4. 返回结果（JSON格式，见下方）

**禁止行为**：
- 不要执行编译验证（编译由主agent负责）
- 不要勾选 tasks.md 的 checkbox（勾选由主agent负责）
- 不要读取其他任务的内容

**返回格式**（你的最后一条消息必须是纯JSON，不包含其他文字）：
{
  "status": "success" | "failed" | "skipped",
  "taskId": "${task_id}",
  "files": ["生成的文件路径1", "生成的文件路径2"],
  "error": "错误描述（仅在failed时）",
  "message": "提示信息（仅在skipped时）"
}

**[Integration] 任务特殊处理**：
如果任务类型是 [Integration]，直接返回：
{
  "status": "skipped",
  "taskId": "${task_id}",
  "message": "Integration 任务是人工验证清单，不支持代码生成"
}
  `,
  run_in_background: false  // 同步等待子agent完成
})
```

**规则文件映射表**：

| 任务 tag | 规则文件路径 |
|---------|-------------|
| `[Client]` | `schemas/lr-func-dev/rules/apply/client-execution.md` |
| `[Server]` | `schemas/lr-func-dev/rules/apply/server-execution.md` |
| `[Contract]` | `schemas/lr-func-dev/rules/apply/server-execution.md` |
| `[Config]` | `schemas/lr-func-dev/rules/apply/config-execution.md` |
| `[Integration]` | 无（直接返回skipped） |

---

#### 6.3 接收子agent结果

**解析子agent的最后一条消息，提取JSON结果**：

```python
# 伪代码
result = parse_json(子agent最后一条消息)

if result["status"] == "success":
    print(f"  ✅ 任务 {result['taskId']} 完成")
    print(f"  📄 生成文件: {', '.join(result['files'])}")
    当前任务.files = result["files"]
    当前任务.status = "success"
    
elif result["status"] == "failed":
    print(f"  ❌ 任务 {result['taskId']} 失败: {result['error']}")
    # 进入失败处理流程（场景1）
    用户选择: skip / retry / abort
    
elif result["status"] == "skipped":
    print(f"  ⏭️  {result['message']}")
    当前任务.status = "skipped"
```

---

#### 6.4 编译验证（主agent负责，关键步骤不可跳过）

**仅当任务类型为 [Client]、[Server]、[Contract] 且状态为 success 时执行编译验证**。

**编译检查点策略**（跨任务协调，保留批量编译逻辑）：

##### 6.4.1 依赖检查（每个任务完成后）

```bash
python check_task_deps.py changes/{change-id}/tasks.md --check {next_task_id}
```

- `[OK]` → 继续
- `[BLOCKED]` → 跳过该任务，移到"等待依赖"列表

##### 6.4.2 客户端增量编译检查（每个 [Client] 任务完成后）

**推荐方式**：Unity MCP（详见 `schemas/lr-func-dev/rules/common/compile-verification.md` 第1节）
- 等待 `IsCompiling: false`
- 调用 `console-get-logs` 检查错误

**兜底方式**：`dotnet build Assembly-CSharp.csproj`（详见第2节）

**增量检查特征**：只关注新生成文件的错误（从 result["files"] 提取文件名关键词）

如果有编译错误，使用 `fix_compile_errors.py` 自动修复（最多3轮，见 6.4.4）。

##### 6.4.3 客户端批量编译验证（每 3-5 个 [Client] 任务后，或角色切换前）

**触发时机**：
- 连续完成5个 [Client] 任务
- 或即将切换到 [Server]/[Config] 任务前
- 或所有 [Client] 任务完成

**执行方式**：同 6.4.2，但不带 `--filter`（检查所有编译错误）。

##### 6.4.4 自动修复编译错误

**如果编译验证失败，按 fix_compile_errors.py 输出的分类，尝试自动修复（最多 3 轮）**：

脚本运行时会打印错误分类和修复建议（详见 `schemas/lr-func-dev/rules/common/compile-verification.md` 第1.6节常见错误速查），按其输出执行：
- `[AUTO-FIX]` — 确定性错误，直接修复
- `[NEED-GREP]` — 需要 grep 辅助，先查真实签名再修复

**修复失败（3轮后仍有错误）**：进入失败处理流程（场景3：manual/skip/abort）

##### 6.4.5 服务端编译验证（强制，无环境豁免）

**Windows 环境执行**：详见 `schemas/lr-func-dev/rules/common/compile-verification.md` 第3节。

**关键步骤摘要**：
1. 定位 MSBuild.exe（按 VS 2022 Enterprise/Professional、VS 2019 顺序尝试）
2. 编译：`MSBuild server2017.sln -t:FsGame -p:Configuration=Debug -p:Platform=x64`
3. 验证：退出码0 + `grep "error" build.log` 无输出 + 生成 `.obj` 文件

**编码相关报错特殊处理**（C2001、C1057、100+级联错误）：
→ 优先检查 GBK 编码安全，详见 `rules/apply/server-execution.md` 第2节。

**如果编译失败**：
- 不允许以"环境限制"为由跳过验证直接标记完成（第3节已提供 Windows 下可用方案）
- 必须在 tasks.md 标记"⚠️ 待验证"并在 implementation-report.md 记录

##### 6.4.6 配置表验证

**对于 [Config] 任务，验证配置表格式**：

```bash
python validate_config_table.py changes/{change-id}/config/{table_name}.txt
```

**验证项**：
- 必填字段是否完整
- 数据类型是否正确
- 外键引用是否有效

---

#### 6.5 立即勾选 checkbox（验证通过后）

**重要**：只有编译验证通过（或配置表验证通过）后，才勾选 checkbox。

```bash
Edit(changes/{change-id}/tasks.md):
  将 "- [ ] {task_id}" 改为 "- [x] {task_id}"
```

**输出确认**：
```
  ✅ 任务 {task_id} 完成（编译验证通过）
```

**重要**：使用精确匹配，避免误勾选其他任务。

#### 6.7 验证勾选成功

```bash
Read(changes/{change-id}/tasks.md)
→ 确认该行已变为 "- [x] {task_id}"
```

**如果验证失败**：
```
❌ 警告: 任务 {task_id} 勾选失败，请手动检查 tasks.md
```

#### 6.8 同步到 sync_tasks.py（可选）

**更新 sync_tasks.py 中的已完成任务列表**：

```python
# 自动将 task_id 添加到 get_completed_tasks_from_tool() 返回值中
Edit(changes/{change-id}/sync_tasks.py):
  在 completed_tasks 列表中添加: '{task_id}',  # {task_description}
```

这样下次运行 `python sync_tasks.py` 时，进度统计会自动同步。

#### 6.9 更新队列

```python
待执行队列.remove(task_id)
已完成队列.append(task_id)
```

#### 6.10 继续下一个任务

回到步骤 6.1

### 步骤 7：处理跳过的任务

**对于不在筛选列表中的任务**：

```
⏭️  跳过任务 {task_id} [{tag}] {description}（{role_name}任务）
```

**不执行代码生成，不勾选 checkbox**。

---

### 步骤 8：输出 Integration 验证清单

**执行完成后，输出人工验证清单**：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Integration 验证清单（需人工验证）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

以下任务需要人工验证，完成后请手动勾选 tasks.md：

[ ] 5.1 [Integration] 前端验证购买流程
[ ] 5.2 [Integration] 后端验证奖励发放逻辑
...

共 {integration_count} 个验证任务
```

---

### 步骤 9：执行总结

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
执行完成！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 已完成: {N} 个任务
⏭️  已跳过: {M} 个任务
❌ 失败: {K} 个任务（如果有）

**已完成的任务**:
  [x] 1.1 [Contract] 定义协议结构
  [x] 2.4 [Client] 客户端生成配置表代码
  ...

**已跳过的任务**:
  [ ] 2.1 [Config] 策划填写配置表
  ...
```

---

### 步骤 10：生成实施报告

执行完成后，自动生成 `changes/{change-id}/implementation-report.md`，记录实施情况供后续验证使用。

#### 报告内容

1. **任务执行摘要** - 已完成/跳过/失败任务统计（按 tag 分类）
2. **生成文件清单** - 按类型分类（协议/配置表/客户端/服务端）
3. **编译验证结果** - 客户端/服务端/配置表验证状态
4. **语言表 key 清单** - 从 `Language_Keys.md` 提取，待导入 `language.xlsx`
5. **跳过原因说明** - 策划任务、Integration 任务的跳过原因
6. **问题记录** - 自动修复的编译错误和待人工处理的问题
7. **后续步骤建议** - 下一步操作清单

#### 输出确认

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
执行完成！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 已完成: 29 个任务
⏭️  已跳过: 16 个任务

📄 实施报告已生成: changes/{change-id}/implementation-report.md
```

---

## 失败处理机制

### 场景 1：任务执行失败

**触发条件**：design.md 缺少对应章节、CodeGraph 查询失败、生成代码语法错误等

**处理选项**：
- `skip` — 跳过此任务，继续下一个
- `retry` — 重新执行此任务
- `abort` — 终止执行，已完成任务已勾选

---

### 场景 2：中断恢复

**触发条件**：执行过程中手动中断（Ctrl+C）或 AI 会话被压缩

**恢复机制**：重新运行 `/lr-openspec-apply <change-id> <role>`，SKILL 自动检测 tasks.md 中已勾选的任务，从第一个未完成任务继续执行（幂等恢复）。

---

### 场景 3：编译验证失败（3轮自动修复后仍有错误）

**触发条件**：6.5.4 自动修复流程失败（3轮后仍有编译错误）

**处理选项**：
- `manual` — 暂停执行，用户手动修复后输入 'continue'
- `skip` — 跳过此任务（标记"待人工验证"），由其他开发者补充
- `abort` — 终止执行

**禁止行为**：不允许以"环境限制"为由跳过编译验证直接标记完成（6.5.5 已提供 Windows 下可用方案）。

---

## Integration 任务的特殊处理

```bash
/lr-openspec-apply growth-fund integration
```

**输出**：联调任务清单（不执行代码生成）+ 验证流程说明（启动测试环境 → 按 TC 逐项验证 → 手动勾选 tasks.md）

---

## 常见问题 FAQ

**Q1-Q4（核心设计理念）**：
- **逐个执行 vs 批量**：实时进度反馈、立即勾选、中断恢复、失败隔离
- **前端任务包含 [Contract]**：协议定义是前后端共同依赖的前置任务
- **部分任务执行**：手动勾选不想执行的任务，或执行时输入 'skip'
- **与 `/opsx:apply` 的区别**：本 SKILL 支持角色过滤（client/server/config），适合分工协作

**Q5：具体的执行规则去哪里查？**

本 SKILL 只负责调度（角色过滤、队列、勾选、编译检查点）。具体执行细节全部在：
- `schemas/lr-func-dev/rules/apply/client-execution.md` — 客户端任务（含 `AGENTS.md` 引用、知识库索引、demo映射、文案key化）
- `schemas/lr-func-dev/rules/apply/server-execution.md` — 服务端/协议任务（含生成代码合规检查、GBK编码安全）
- `schemas/lr-func-dev/rules/apply/config-execution.md` — 配置表任务（含md5快照比对）

步骤6.2会指引按任务tag读取对应文件，执行前必须完整阅读。

---

## 版本信息

**版本**: v3.0（规则归位 + SKILL 精简）
**创建日期**: 2026-07-23
**最后重构**: 2026-08-06
**设计哲学**: 角色过滤 + 逐个执行 + 实时勾选 + 中断恢复；本 SKILL 只做调度，具体执行规则委托给 `rules/apply/*.md`
**依赖 SKILL**: lr-openspec-tasks（生成 tasks.md）
**依赖命令**: openspec instructions apply（获取执行规则入口）
