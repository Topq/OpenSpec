---
name: lr-openspec-apply
description: 按角色过滤执行 tasks.md 任务（前端/后端/策划）。支持多角色组合，逐个执行，实时勾选，支持中断恢复。
---

# OpenSpec Apply（角色过滤执行器）

## 与 `/opsx:apply` 的关系

| 命令 | 执行范围 | 适用场景 |
|-----|---------|---------|
| `/opsx:apply <id>` | 执行所有任务 | 全栈开发者，或技术负责人 |
| `/lr-openspec-apply <id> <role>` | 只执行指定角色任务 | 前端/后端/策划分工协作 |

**本 SKILL 是 `/opsx:apply` 的角色过滤增强版**。

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

**示例**：
```bash
/lr-openspec-apply growth-fund client
```

**输出**：
```
Growth Fund - 前端任务清单

⚠️  前置依赖（2 个任务）:
  [ ] 1.1 [Contract] 定义成长基金协议结构和常量
  [ ] 1.2 [Contract] 生成配置表解析代码骨架

✅ 可以立即开始（5 个任务）:
  [ ] 2.4 [Client] 客户端生成配置表 C# 代码
  [ ] 4.1.1 [Client] 生成 MixGrowthFundModule.cs 骨架
  [ ] 4.1.5 [Client] 在 BusinessActivityType 枚举中启用
  [ ] 4.2.1 [Client] 生成 GrowthFundPage.cs 骨架
  [ ] 4.1.6 [Client] 在 GameLauncher.cs 中注册模块

⏸️  等待依赖（22 个任务）:
  [ ] 4.1.3 [Client] 实现 Message 解析 → 依赖任务 1.2
  [ ] 4.3.2 [Client] 实现购买流程 → 依赖任务 1.1
  ...

总计: 29 个前端任务（跳过 16 个后端/策划任务）

执行代码生成？输入 'y' 继续，或直接回车取消:
```

---

### 模式 2：执行代码生成

在任务清单后，用户输入 `y`：

```
用户输入: y

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
开始执行前端任务（29 个）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1/29] 执行任务 1.1 [Contract] 定义协议结构
  📖 读取 design.md 附录 A（客户端协议定义）
  📖 读取 design.md 附录 B（服务端协议定义）
  🔍 查找现有协议号范围
  ✏️  生成协议定义文件
  ✅ 任务 1.1 完成

[2/29] 执行任务 1.2 [Contract] 生成配置表解析代码
  📖 读取 design.md 附录 C（配置表定义）
  🔍 CodeGraph 查询配置表解析模板
  ✏️  生成客户端解析代码
  ✅ 任务 1.2 完成

⏭️  跳过任务 2.1 [Config] 策划填写配置表（策划任务）
⏭️  跳过任务 2.2 [Config] 策划填写配置表（策划任务）
⏭️  跳过任务 2.3 [Config] 策划填写配置表（策划任务）

[3/29] 执行任务 2.4 [Client] 客户端生成配置表代码
  📖 读取 design/client.md 配置表章节
  🔍 CodeGraph 查询 TableConfig 注册模板
  ✏️  生成配置表 C# 代码
  ✅ 任务 2.4 完成

...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
执行完成！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 已完成: 29 个任务
⏭️  已跳过: 16 个任务
```

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

---

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

**提取逻辑**：
```python
# 伪代码示例
tasks = []
for line in tasks_md:
    match = re.match(r'- \[(.)\] (\d+\.\d+) \[(\w+)\] (.+)', line)
    if match:
        status, task_id, tag, description = match.groups()
        tasks.append({
            "id": task_id,
            "tag": tag,
            "status": status,  # " " = 未完成, "x" = 已完成
            "description": description
        })

# 解析 role 参数
if role == "dev":
    role = "client,server"
elif role == "all":
    role = "client,server,config"

# 解析多角色
roles = role.split(",")
allowed_tags = set()
for r in roles:
    if r == "client":
        allowed_tags.update(["Client", "Contract"])
    elif r == "server":
        allowed_tags.update(["Server", "Contract"])
    elif r == "config":
        allowed_tags.add("Config")

# 筛选任务（去重 Contract）
filtered = [t for t in tasks if t["tag"] in allowed_tags]

# 过滤已完成的任务
pending = [t for t in filtered if t["status"] == " "]
```

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

**输出存储**：
```
apply_instruction = Bash("openspec instructions apply --change {change-id}")
```

**注意**：这个指令包含所有任务类型的执行规则，我们会在后续步骤中按需提取。

---

### 步骤 6：循环执行任务

**对于待执行队列中的每个任务**：

#### 6.1 显示当前任务

```
[{index}/{total}] 执行任务 {task_id} [{tag}] {description}
```

#### 6.2 提取执行规则

从 `apply_instruction` 中提取该任务类型的执行规则。

例如，如果任务是 `[Client]` 类型：
```python
# 从 apply_instruction 中查找 "### [Client] 客户端实现" 章节
# 提取该章节的执行逻辑
```

#### 6.3 执行任务

**根据任务类型执行**：

##### [Contract] 协议定义

1. 读取 `design.md` 附录 A（客户端协议定义）和附录 B（服务端协议定义）
2. 查找现有协议文件，获取最大协议号
3. 为 `{待分配}` 占位符分配新协议号
4. 生成协议定义文件

##### [Config] 配置表

**⚠️ 配置表代码必须通过工具生成，禁止手写**

**前置检查**：
1. 读取 `design/config.md`，检查是否包含以下必需信息：
   - 字段定义表的"属性"列（S/C/A 标注）
   - "配置加载方式"说明（静态配置/动态配置）
   - "outcode_config.json 配置建议"章节

2. 如果缺少上述信息，输出错误并停止：
   ```
   ❌ design/config.md 缺少 outcode_config.json 配置建议
   
   无法判断应该配置 need_copy 还是 NeedParseDataMethod。
   请先完善 design/config.md 后再执行 [Config] 任务。
   ```

**执行步骤**（仅当前置检查通过）：

1. **策划填写配置表数据**（此类任务由策划手动完成，AI 跳过）

2. **客户端生成配置表代码**（[Client] 标签的 [Config] 任务）：
   
   **步骤 2.1：配置 outcode_config.json**
   - 文件：`D:\se\develop\client\tools\table\table_config\outcode_config.json`
   - 根据 design/config.md 的"outcode_config.json 配置建议"：
     - 如果需要 need_copy → 在 `need_copy` 数组末尾添加表名（逗号分隔）
     - 如果需要 NeedParseDataMethod → 在 `NeedParseDataMethod` 数组末尾添加表名
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

   **步骤 2.2：生成配置表代码**
   ```bash
   cd D:\se\develop\client\tools\table
   双击 output_code_csharp.bat
   # 或命令行执行
   cmd /c "D:\se\develop\client\tools\table\output_code_csharp.bat"
   ```

   **步骤 2.3：验证生成结果**
   - 检查是否生成 4 个文件：
     - `Assets/Script/Table/Generate/{模块}/{表名}/TD{表名}.cs`
     - `Assets/Script/Table/Generate/{模块}/{表名}/TD{表名}Table.cs`
     - `Assets/Script/Table/Extend/{模块}/{表名}/TD{表名}Extend.cs`
     - `Assets/Script/Table/Extend/{模块}/{表名}/TD{表名}TableExtend.cs`
   - 对比生成的字段列表与 design/config.md 的字段定义是否一致
   - 进入编译验证步骤（步骤 6.5.2）

**禁止操作**：
- ❌ 使用 Write 工具手写配置表 CS 代码
- ❌ 复制其他配置表代码后手动替换类名和字段

##### [Server] 服务端实现

1. 读取 `design/server.md` 对应章节
2. 用 CodeGraph 查询服务端代码模板
3. 生成服务端代码（Record 表定义、协议处理、业务逻辑）

##### [Client] 客户端实现

1. 读取 `design/client.md` 对应章节
2. 用 CodeGraph 查询客户端代码模板（如 `ILogicModule`、`BaseActivityPage`）
3. 生成客户端代码（模块、UI Panel、协议收发）

##### [Integration] 联调验证

**不生成代码**，输出提示：
```
⚠️ Integration 任务是人工验证清单，不支持代码生成。
   请按 test-cases.md 对应的 TC 逐项验证。
```

#### 6.4 输出任务进度

```
  📖 读取 design.md 相关章节
  🔍 CodeGraph 查询代码模板
  ✏️  生成代码文件: {file_path}
```

#### 6.5 编译验证（新增 - 关键步骤）

**对于代码生成任务（[Client] 或 [Server]），必须在标记完成前验证编译**。

**编译策略：增量检查，批量编译**

**原则**：
- 每完成 1 个任务后，立即运行依赖检查（check_task_deps.py）和增量编译检查（仅检查新生成的文件）
- 每完成连续 3-5 个同类型（同 tag）任务后，或切换任务类型前，运行一次全量编译验证
- 全量编译失败且涉及旧文件时，使用 fix_compile_errors.py 分析并尝试自动修复

##### 6.5.1 依赖检查（每个任务完成后）

**在进入下一个任务前，检查队列中下一个任务的依赖是否满足**：

```bash
python check_task_deps.py changes/{change-id}/tasks.md --check {next_task_id}
```

**输出**：
- `[OK]` → 继续执行
- `[BLOCKED]` → 跳过该任务，从队列中移到"等待依赖"列表

##### 6.5.2 客户端增量编译检查（每个 [Client] 任务完成后）

```bash
cd D:/se/develop/client/project
dotnet build Assembly-CSharp.csproj > build_output.txt 2>&1
python {openspec_root}/.claude/skills/lr-openspec-apply/fix_compile_errors.py build_output.txt --filter {新生成的文件名关键词}
```

**示例**：
```bash
# 刚生成了 GrowthFundPage.cs
python fix_compile_errors.py build_output.txt --filter GrowthFund
```

**判断逻辑**：
- 脚本 exit code 0 → 增量检查通过，继续
- 脚本 exit code 1 → 新文件有错误，进入自动修复流程（步骤 6.5.4）

##### 6.5.3 客户端批量编译验证（每 3-5 个 [Client] 任务后，或角色切换前）

```bash
cd D:/se/develop/client/project
dotnet build Assembly-CSharp.csproj > build_output.txt 2>&1
python {openspec_root}/.claude/skills/lr-openspec-apply/fix_compile_errors.py build_output.txt
```

**不带 --filter**，检查所有编译错误（包括可能被新代码影响的旧文件）。

**输出**：
- `[OK]` → 批量验证通过
- `[FAIL]` → 输出分类后的错误清单，进入自动修复流程（步骤 6.5.4）

##### 6.5.4 自动修复编译错误

**如果编译验证失败，按 fix_compile_errors.py 输出的分类，尝试自动修复（最多 3 轮）**：

```
❌ Compile errors detected:
  [AUTO-FIX] 2 deterministic errors (CS0506, CS0308)
  [NEED-GREP] 2 grep-assisted errors (CS1503, CS0117)

🔧 Fix attempt 1/3:
  1. For [AUTO-FIX] errors: apply deterministic fixes directly
  2. For [NEED-GREP] errors: grep the real API signature, then edit
  3. Re-run fix_compile_errors.py to check result
```

**常见错误自动修复策略（来自 fix_compile_errors.py 的 ERROR_RULES）**：

| 错误类型 | 分类 | 修复策略 |
|---------|------|---------|
| `CS0506: cannot override non-virtual` | AUTO-FIX | 移除 `override` 关键字（并移除对应 base.Method() 调用） |
| `CS0308: non-generic method ... cannot be used with type arguments` | AUTO-FIX | 移除 `<T>` 类型参数，改用非泛型重载或 GetComponent/AddComponent 组合 |
| `CS0246: type or namespace not found` | AUTO-FIX | 补充缺失的 using 语句 |
| `CS1503: argument type mismatch` | NEED-GREP | Grep 目标方法签名，确认真实参数类型（常见坑：out int vs out long） |
| `CS0117: type does not contain member` | NEED-GREP | Grep 同类型在项目里的其他调用点，找到真实的静态/扩展方法名称后替换 |
| `CS1061: type does not contain property/method` | NEED-GREP | Grep 类型定义文件，确认真实的属性/方法名（常见坑：itemID vs configID） |
| `CS0029: implicit conversion failed` | NEED-GREP | Grep 两侧类型定义，确认是否需要显式转换或修改字段类型 |

**修复成功**：
```
✅ All errors fixed, re-compile passed (0 errors)
```

**修复失败（3 轮后仍有错误）**：
```
❌ Auto-fix failed after 3 attempts, {N} errors remain

**Recovery options**:
  - Type 'manual' to fix manually and continue
  - Type 'skip' to skip this task and continue with next
  - Type 'abort' to stop execution
```

##### 6.5.5 服务端编译验证

```bash
cd D:/se/develop/server/SourceModule
make 2>&1 | tee build_output.txt
```

**注意**：服务端编译需要 Linux 环境。如果在 Windows 环境执行 lr-openspec-apply，跳过服务端编译验证，但在任务输出中标注：

```
⚠️  Warning: Server tasks require Linux environment for compile verification
```

**如果在 Linux 环境**：
- 编译通过 → 继续
- 编译失败 → 手动分析（C++ 错误类型复杂，暂不支持自动修复脚本）

##### 6.5.6 配置表验证

**对于 [Config] 任务，验证配置表格式**：

```bash
python validate_config_table.py changes/{change-id}/config/{table_name}.txt
```

**验证项**：
- 必填字段是否完整
- 数据类型是否正确
- 外键引用是否有效

#### 6.6 立即勾选 checkbox（验证通过后）

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

#### 6.8 继续下一个任务

回到步骤 6.1

---

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
[ ] 5.3 [Integration] 测试配置表加载
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
  [x] 1.2 [Contract] 生成配置表解析代码
  [x] 2.4 [Client] 客户端生成配置表代码
  ...

**已跳过的任务**:
  [ ] 2.1 [Config] 策划填写配置表
  [ ] 2.5 [Server] 服务端验证配置加载
  ...
```

---

## 失败处理机制

### 场景 1：任务执行失败

```
[5/29] 执行任务 4.3.2 [Client] 实现购买流程
  📖 读取 design/client.md 购买流程章节
  ❌ 错误: design/client.md 中未找到"购买流程"章节

**失败处理**:
  - 输入 'skip' 跳过此任务，继续执行下一个
  - 输入 'retry' 重新执行此任务
  - 输入 'abort' 终止执行

用户输入:
```

**用户选择 `skip`**：
```
⏭️  跳过任务 4.3.2（用户手动跳过）
已跳过队列.append("4.3.2")
```

**用户选择 `retry`**：
```
[5/29] 重试任务 4.3.2 [Client] 实现购买流程
  ...
```

**用户选择 `abort`**：
```
⚠️ 用户终止执行

已完成: 4 个任务
已跳过: 0 个任务
待执行: 25 个任务（可重新运行 SKILL 继续）
```

---

### 场景 2：中断恢复

**假设执行到第 15 个任务时手动中断（Ctrl+C）**：

```
tasks.md 的状态:
  [x] 1.1 完成 ✅
  [x] 1.2 完成 ✅
  ...
  [x] 4.3.1 完成 ✅
  [ ] 4.3.2 未开始
  [ ] 4.3.3 未开始
  ...
```

**重新运行 SKILL**：
```bash
/lr-openspec-apply growth-fund client
```

**SKILL 自动检测**：
```
检测到 15 个任务已完成，跳过这些任务。

待执行: 14 个任务
  [ ] 4.3.2 [Client] 实现购买流程
  [ ] 4.3.3 [Client] 实现购买确认弹窗
  ...

继续执行？输入 'y' 继续:
```

---

## Integration 任务的特殊处理

```bash
/lr-openspec-apply growth-fund integration
```

**输出**：
```
Growth Fund - 联调任务清单（8 个任务）

[ ] 5.1 [Integration] 客户端联调购买流程
    对应验收: TC-growth-fund-purchase-03, TC-growth-fund-purchase-04
[ ] 5.2 [Integration] 客户端联调领取流程
    对应验收: TC-growth-fund-claim-01, TC-growth-fund-claim-04
...

⚠️ Integration 任务是人工验证清单，不支持代码生成。

验证流程:
  1. 启动客户端 + 服务端测试环境
  2. 按 TC 步骤逐项验证
  3. 验证通过后手动勾选 tasks.md 中的 checkbox
```

**不执行代码生成，不调用 `openspec instructions apply`**。

---

## 常见问题 FAQ

### Q1: 为什么要逐个执行任务，而不是一次性执行？

**A**: 逐个执行提供了：
- ✅ 实时进度反馈（知道执行到哪个任务）
- ✅ 立即勾选机制（tasks.md 始终反映真实进度）
- ✅ 中断恢复（可以随时停止，下次继续）
- ✅ 失败隔离（某个任务失败不影响其他任务）

---

### Q2: 为什么前端任务包含 [Contract] 任务？

**A**: [Contract] 任务是前后端共同依赖的基础（协议定义），前端必须等这些任务完成才能继续。所以前端视图会包含 [Contract] 任务作为"前置依赖"。

---

### Q3: 如果我只想执行部分任务怎么办？

**A**: 有两种方式：
1. 手动勾选不想执行的任务（在 tasks.md 中改为 [x]），SKILL 会自动跳过
2. 执行时遇到不想执行的任务，输入 'skip' 跳过

---

### Q4: 与 `/opsx:apply` 的区别？

**A**:
- `/opsx:apply growth-fund` - 执行所有 47 个任务
- `/lr-openspec-apply growth-fund client` - 只执行 29 个前端任务（跳过 3 个策划 + 5 个后端 + 8 个联调任务）

两者都调用 `openspec instructions apply`，区别在于执行范围。

---

## 版本信息

**版本**: v2.0（逐个勾选机制）  
**创建日期**: 2026-07-23  
**设计哲学**: 角色过滤 + 逐个执行 + 实时勾选 + 中断恢复  
**依赖 SKILL**: lr-openspec-tasks（生成 tasks.md）  
**依赖命令**: openspec instructions apply（获取执行规则）
