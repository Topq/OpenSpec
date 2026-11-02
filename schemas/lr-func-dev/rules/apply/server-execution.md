# apply/server-execution.md（[Server] 任务执行规则）

> **说明**：本文档定义 `[Server]` 标签任务在 apply 阶段的执行规则。由 `openspec instructions apply` 指路，`lr-openspec-apply` SKILL 在执行 `[Server]` 任务前读取本文件。
>
> **设计哲学**：本文件只包含"apply 阶段服务端执行"的强制流程和判断路由；生成器命令、兼容规则等具体细节以服务端工程自己的治理文档为唯一权威来源，本文件不重复维护，避免跨仓库规则副本漂移。

---

## 0. 强制前置：读取服务端工程治理文档

进入任何 `[Server]` 任务前，必须先读取服务端工程的 AI 协作规范：

**文件路径**（绝对路径，固定）：
```
../develop/server/project/AGENTS.md
```

**读取后判断**：
1. 如果要修改/新增以下任一类内容，必须走 XML→生成器链路（详见下方"第 1 节：生成代码合规检查"）：
   - struct 属性 / record / 生成常量
   - 配置表关联枚举
   - 消息 ID / 协议字段布局
2. 如果只是业务逻辑代码（.cpp/.h 手写部分），跳过第 1 节，直接进入"第 2 节：GBK 编码安全"。
3. 任何服务端 C/C++ 代码风格问题，参考"第 3 节：服务端编码风格引用"。

**路径来源**：该路径已记录在 `config.yaml` 的 `context` 字段（`../develop/server/project`）。

---

## 1. 生成代码合规检查（阻断性）

**触发条件**（命中任一条即触发）：
- 任务涉及 struct 属性 / record 定义
- 任务涉及配置表关联枚举
- 任务涉及协议号分配 / 协议字段布局

**强制流程**：
1. 读取 `../develop/server/project/.agents/skills/lr-generated-code-workflow/SKILL.md`
2. 读取 `../develop/server/project/.agents/skills/lr-generated-code-workflow/references/generation-chains.md`
3. 判断目标文件头部是否有 "Generated from ... Do not edit." 标记，或搜索该符号是否能在下列源目录中找到源定义：
   - `cons/res/struct/**/*.xml`
   - `cons/def/configs/*.xml`
   - `cons/msg/config/*.xml`
4. 确认是生成文件后：
   - 只修改对应 XML 源文件
   - 从要求的工作目录运行匹配的生成器
   - **禁止**直接手改 `define/` 下的生成产物
5. 生成后同时检查源文件和生成文件差异；生成输出只能包含目标机械变化。

**XML→生成器链路速查**（详细命令、兼容规则、验证步骤以 `generation-chains.md` 为准，不在本文件复述）：

| 类型 | 源文件 | 生成器 | 产物 |
|-----|--------|--------|------|
| Struct/Record | `cons/res/struct/**/*.xml` | `struct_generator.py` | `define/struct/**/struct_<name>.h` |
| 配置表关联枚举 | `cons/def/configs/*.xml` | `GenerateEnums.bat`/`.ps1` | `define/enum/<name>.h` |
| 消息协议 | `cons/msg/config/*.xml`（经 `Config.json` 映射） | `gen_msg.exe`（或对应 `gen_xxx_msg.bat`） | `Config.json` 指定的 `define_file_name` |

**关键兼容约束（摘要，完整规则见 `generation-chains.md`）**：
- record 新列只能追加在末尾，禁止重排已有列；旧创建路径必须为新列提供默认值。
- 枚举禁止重新编号已被外部使用的数值；稳定契约优先显式赋值。
- 协议消息新增字段必须追加在末尾，保持已有消息 ID 不变；同时检查发送端打包顺序和接收端解包索引。

**失败处理**：
- 生成结果错误时修复 XML 或生成器，禁止补丁修改输出。
- 生成文件包含无关本地修改时，不要直接覆盖——先判断是过期手改、其他待提交源修改，还是生成器漂移。

**完成时必须提供的证据**（写入 implementation-report.md 的对应条目）：
- 修改过的 XML 源文件
- 实际执行的生成器命令
- 发生变化的生成文件
- ID / 字段顺序 / record 列的兼容决策

---

## 2. GBK 编码安全（仅当确认是业务代码、非生成文件时触发）

**触发条件**：
- 已通过第 1 节判断，确认目标文件不是生成产物
- 要 Edit/Write 含中文的 `.cpp`/`.h` 文件

**背景**：服务端代码库存在 GBK/UTF-8 混编文件，直接使用 Read/Edit 工具会导致编码损坏。

### 2.1 识别高风险文件（修改前必查）

```bash
# 检查文件编码
file <path>

# 验证是否为 GBK
python -c "open('file', 'rb').read().decode('gbk')" 2>&1 | head -1
# 成功 → GBK 编码
# UnicodeDecodeError → 可能是 UTF-8 或二进制

# 快速检测是否含中文字符串常量
grep -P '[\x80-\xff]{2,}' <file> | head -5
# 有输出 → 含非 ASCII 字符（可能是中文）
```

### 2.2 安全操作规则

| 文件类型 | 允许的工具 | 禁止的工具 | 原因 |
|---------|-----------|----------|------|
| **纯 ASCII C++ 文件**（无中文注释/字符串）| Read, Edit, Write | - | 无编码风险 |
| **GBK 编码 C++ 文件**（含中文）| Python bytes 操作 | ❌ Read/Edit/Write | 会按 UTF-8 误解码，破坏中文字节 |
| **UTF-8 with BOM**（罕见）| Read, Edit, Write | - | 工具默认 UTF-8，安全 |

### 2.3 GBK 文件的安全修改方法（Python bytes 模板）

```python
# 模板 1：在文件特定位置后插入代码
with open('file.cpp', 'rb') as f:
    data = f.read()

# 定义锚点（必须是纯 ASCII，如 #include 行）
marker = b'#include "BusinessActivity/MonthCardFunc.h"'
insert_code = b'\n#include "../CommonModule/ILuaExtModule.h"'

# 插入
data = data.replace(marker, marker + insert_code, 1)  # 只替换第一次出现

with open('file.cpp', 'wb') as f:
    f.write(data)
```

```python
# 模板 2：在文件末尾追加代码
with open('file.cpp', 'rb') as f:
    data = f.read()

append_code = b'''
int MonthCardModule::nx_month_card_active(void* state) {
    // ...
}
'''

with open('file.cpp', 'wb') as f:
    f.write(data + append_code)
```

```python
# 模板 3：替换函数体（锚点必须是纯 ASCII）
with open('file.cpp', 'rb') as f:
    data = f.read()

old_func = b'int MonthCardModule::OldFunc() {\n    return 0;\n}'
new_func = b'int MonthCardModule::OldFunc() {\n    return DoSomething();\n}'

data = data.replace(old_func, new_func)

with open('file.cpp', 'wb') as f:
    f.write(data)
```

**⚠️ 关键约束**：
- **锚点字符串必须是纯 ASCII**（不能用中文注释作锚点）
- **插入/替换的代码必须是纯 ASCII 或用 GBK 编码的中文**
  ```python
  # ❌ 错误：插入 UTF-8 中文到 GBK 文件
  insert = '// 月卡激活'.encode('utf-8')  # 会乱码

  # ✅ 正确：使用英文注释
  insert = b'// Month card activation'

  # ✅ 正确：如果必须用中文，用 GBK 编码
  insert = '// 月卡激活'.encode('gbk')
  ```

### 2.4 行尾符保持（防止 SVN diff 噪音）

```python
# 检测原文件行尾符
with open('file.cpp', 'rb') as f:
    sample = f.read(1024)
    has_crlf = b'\r\n' in sample
    has_lf = b'\n' in sample and not has_crlf

# 修改后恢复原行尾符
with open('file.cpp', 'rb') as f:
    data = f.read()

if has_crlf and b'\r\n' not in data:
    # 被工具改成了 LF，恢复 CRLF
    data = data.replace(b'\n', b'\r\n')

with open('file.cpp', 'wb') as f:
    f.write(data)
```

### 2.5 损坏检测（修改后立即验证）

```bash
# 检查是否出现 UTF-8 替换字符（U+FFFD = EF BF BD）
python -c "print(open('file.cpp', 'rb').read().count(b'\xef\xbf\xbd'))"
# 输出 > 0 → 文件已损坏

# 如果损坏，立即回退
svn revert file.cpp
```

### 2.6 紧急恢复流程

```bash
# 1. 立即回退损坏的文件
svn revert <file>

# 2. 检查是否有其他文件也被损坏
svn status | grep "^M"

# 3. 如果多个文件损坏，批量回退
svn revert -R .

# 4. 重新用 Python bytes 方式修改
```

### 2.7 编译错误特征识别（编码问题导致的典型错误）

| 错误信息 | 根因 | 处理 |
|---------|------|------|
| `error C2001: 常量中有换行符` | UTF-8 替换字符 U+FFFD 破坏了字符串常量 | `svn revert` + 重新用 bytes 修改 |
| `error C1057: 宏扩展中遇到意外的文件结束` | 级联错误（通常跟随 C2001） | 同上 |
| 报错位置在中文字符串附近 | 编码不匹配 | 改用英文字符串，或确保文件有 UTF-8 BOM |
| 100+ 级联错误，第一个错误在 include 附近 | 头文件损坏 | 检查该头文件是否被误改编码 |

### 2.8 预防性检查清单（修改服务端代码前）

- [ ] 运行 `file <path>` 确认编码
- [ ] 如果是 GBK，准备 Python bytes 脚本，不用 Read/Edit
- [ ] 修改后立即检查 U+FFFD 出现次数
- [ ] 修改后运行 `svn diff` 确认改动范围符合预期
- [ ] 编译验证通过后再标记任务完成

---

## 3. 服务端编码风格引用

**参考文档**：
```
../develop/server/project/.agents/skills/lr-server-code-style/SKILL.md
```

**关键规则摘要（详细规则以原文件为准）**：
- `if` 后的语句必须另起一行，并始终使用 `{}`
- `switch` 中每个非空 `case` 的执行代码必须放在 `{}` 块中
- 除 `true`/`false` 外不要使用魔法数字，协议字段/偏移量/返回值应定义为枚举或具名常量
- 公共接口、事件回调、模块 `Init`、注册函数中，不要直接写 `return SomeFunction(...)`，先保存到具名变量再返回
- 修改已有源码前检测文件编码/BOM/换行符，保持原文件风格不变（呼应第 2 节）

---

## 4. 主执行流程

1. 读取 `design/server.md` 对应章节
2. 先完成第 0 节（读 AGENTS.md）和第 1 节（生成代码合规检查，如命中）
3. 用 CodeGraph 查询服务端代码模板
4. 生成服务端代码（Record 表定义、协议处理、业务逻辑）
5. 涉及业务代码手写时按第 2 节编码安全规则操作，按第 3 节风格规范书写

---

## 5. 生成期契约自检（阻断性）

与 `lr-openspec-code-review` 对齐、且能在生成期确定的契约自检：P0 项全部纳入，另含生成期成本最低的 P1 项。命中任一项，先修复再返回 `success`。

1. **协议契约**（server-001，P0）：C2S 从 `args.IntVal(1)` 起；S2C 字段数/顺序/类型与本变更 `design.md` 的协议附录一致（独立 protocol-contract.md 如存在则一并核对），可选尾按 `count` 分支；新增协议 ID 同时出现在 `cons/msg/config/client_msg.xml（按 cons/msg/Config.json 与生成链复核）`、`define/ClientCustomDefine.h` 与客户端定义中；处理函数已在 `Init()` 中 `ADD_INT_CUSTOM_HOOK` 注册且未被覆盖。
2. **配置字段名与列结构**（server-003，P0）：`txt.ReadInt/ReadString` 的字段名与**实际导出 txt 表头**逐字一致；不存在的列、大小写不符都要修。
3. **Record 访问保护**（server-004，P0）：`GetRecord`/`FindRecord` 后判 `Exist()`；列索引用 `*Define.h` 枚举；列数与 `cons/res/struct/*.xml` 的 `cols` 一致。
4. **错误反馈完整性**（server-002，P1）：业务失败不能只 `LogError` + `ERR_COMMON_FAIL`，要映射到通用错误码/提示接口。

检查命令：

```bash
rg -n "args.IntVal|ReadInt|ReadString|GetRecord|FindRecord|Exist\(\)|QueryInt" <本次改动的服务端文件>
```

---

**版本**: v1（从 lr-openspec-apply/SKILL.md 迁移，新增第 0/1/3 节）
**最后更新**: 2026-10-31（新增 §5 生成期契约自检；标题去掉 P0 字样，条目标注检查项等级（P0/P1））
**维护原则**: 生成器命令、兼容规则以 `develop/server/project/AGENTS.md` 及其路由的 Skill（`lr-generated-code-workflow`、`lr-server-code-style`）为唯一权威来源，本文件只做路由指引，不复制其内容
