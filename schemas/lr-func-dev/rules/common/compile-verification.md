# 跨端代码编译验证规则（apply/reconcile/code-review 通用）

> **职责**：定义客户端/服务端代码修改后的编译验证标准流程，供多个 SKILL 引用，避免各自维护重复规则。
>
> **适用 SKILL**：lr-openspec-apply、lr-openspec-reconcile、lr-openspec-code-review、lr-openspec-ui-prefab

---

## 1. 客户端编译验证（Unity MCP 方式，推荐）

### 1.1 前置条件

- Unity Editor 已启动（项目路径：`../develop/client/project`）
- ai-game-developer MCP 插件已连接（http://localhost:22992）
- 检查方法：调用 `mcp__ai-game-developer__editor-application-get-state`，确认能获取响应

**如果 MCP 不可用**：回退到第2节的 `dotnet build` 兜底方案（有假阴性风险，见 2.4 限制说明）。

---

### 1.2 触发编译

Unity 会在文件修改后自动触发编译，通常无需手动触发。

**强制触发场景**：
- 批量修改后希望立即编译
- 使用 Write 工具创建了新 `.cs` 文件

**触发命令**：
```
mcp__ai-game-developer__assets-refresh
```

---

### 1.3 等待编译完成

轮询 `mcp__ai-game-developer__editor-application-get-state`，直到 `IsCompiling: false`：

**轮询参数**：
- 间隔：3秒
- 超时：180秒（3分钟）

**超时处理**：
```
⚠️ Unity 编译超过3分钟未完成

可能原因：
  1. 代码变更触发大量依赖重编译
  2. Unity Editor 卡死或崩溃
  3. 编译错误导致编译器挂起

建议：
  - 打开 Unity Editor 查看 Console 窗口
  - 如果有编译错误，跳过等待直接进入步骤 1.4
  - 如果 Editor 无响应，重启 Unity 后重试
```

---

### 1.4 检查编译错误

调用 `mcp__ai-game-developer__console-get-logs`：

**参数**：
```json
{
  "logTypeFilter": "Error",
  "lastMinutes": 5,
  "includeStackTrace": false,
  "maxEntries": 100
}
```

**错误判定**：
- **0 errors** → 编译通过，继续下一步
- **> 0 errors** → 提取错误信息，进入修复流程（见 1.5）

---

### 1.5 错误分类与修复

**如果有 `fix_compile_errors.py` 可用**（apply 阶段）：
```bash
# 将 Unity Console 错误转换为 MSBuild 格式（CS错误码 + 行号）
python fix_compile_errors.py <错误日志> --unity-format
```

脚本会输出：
- `[AUTO-FIX]` — 确定性错误（CS0506/CS0308/CS0246），直接修复
- `[NEED-GREP]` — 需要 grep 辅助（CS1503/CS0117/CS1061），先查真实签名再修复
- `[MANUAL]` — 需要人工判断的错误

**如果脚本不可用**（reconcile/code-review 阶段）：
- 直接读取错误信息，提取文件路径、行号、错误码
- 报告给调用方决策（继续/跳过/人工介入）

---

### 1.6 常见客户端编译错误速查

| 错误码 | 含义 | 优先检查 |
|-------|------|---------|
| CS0506 | 试图 override 非虚方法 | 移除 `override` 关键字，检查是否误判为重写 |
| CS0308 | 非泛型方法带了类型参数 | 移除 `<T>`，改用非泛型重载 |
| CS0246 | 类型/命名空间未找到 | 补充 `using` 语句，确认类型拼写 |
| CS1503 | 参数类型不匹配 | Grep 目标方法真实签名（常见：out int vs out long） |
| CS0117 | 类型不包含该成员 | Grep 同类型其他调用点，找真实静态/扩展方法名 |
| CS1061 | 类型不包含属性/方法 | Grep 类型定义，确认真实属性名（常见：itemID vs configID） |

---

## 2. 客户端编译验证（dotnet build 兜底方案）

### 2.1 使用场景

**仅在以下情况使用**：
- Unity Editor 未启动
- Unity MCP 连接失败
- 无 GUI 环境（CI/自动化脚本）

---

### 2.2 执行命令

```bash
cd ../develop/client/project
dotnet build Assembly-CSharp.csproj > build_output.txt 2>&1
echo $?  # 退出码 0 = 成功
```

---

### 2.3 错误分析

**如果有 `fix_compile_errors.py`**：
```bash
python {openspec_root}/.claude/skills/lr-openspec-apply/fix_compile_errors.py build_output.txt
```

按脚本输出的分类修复（同 1.5）。

**如果脚本不可用**：
直接读取 `build_output.txt`，搜索 `: error CS` 模式，提取错误码和行号。

---

### 2.4 限制说明

**假阴性风险**：项目有 321 个 asmdef，部分活动模块可能在独立 asmdef 对应的 csproj 里（不是 Assembly-CSharp）。`dotnet build Assembly-CSharp.csproj` 只编译默认程序集，**可能漏检**独立模块的错误。

**判断是否命中假阴性**：
- 如果修改的模块目录下或其父目录存在 `.asmdef` 文件 → 有假阴性风险
- 如果 `dotnet build` 通过但 Unity Editor 内实际报错 → 确认命中假阴性

**应对方式**：
- 编译通过后，仍需在 Unity Editor 内确认 Console 无错误（或等待 Unity MCP 恢复后重新验证）
- 在最终验证报告里标注"使用兜底方案，存在假阴性风险"

---

## 3. 服务端编译验证（MSBuild 方式）

### 3.1 前置条件

- Windows 环境
- Visual Studio 2019/2022 已安装（任意版本）

---

### 3.2 定位 MSBuild.exe

按以下路径顺序尝试（先到先用）：

```bash
# VS 2022 Enterprise
D:\Program Files\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\amd64\MSBuild.exe

# VS 2022 Professional
C:\Program Files\Microsoft Visual Studio\2022\Professional\MSBuild\Current\Bin\amd64\MSBuild.exe

# VS 2019 (任意版本)
C:\Program Files (x86)\Microsoft Visual Studio\2019\{Edition}\MSBuild\Current\Bin\amd64\MSBuild.exe
```

**判断方式**：
```bash
if [ -f "<路径>" ]; then
  MSBUILD="<路径>"
  break
fi
```

**如果所有路径都不存在**：
```
❌ 未找到 MSBuild.exe

请确认以下任一软件已安装：
  - Visual Studio 2022 (Enterprise/Professional/Community)
  - Visual Studio 2019 (任意版本)

或在 Windows 环境变量中设置 MSBUILD_PATH。
```

---

### 3.3 执行编译

```bash
cd ../develop/server/project

"$MSBUILD" server2017.sln \
  -t:FsGame \
  -p:Configuration=Debug \
  -p:Platform=x64 \
  -v:minimal > build.log 2>&1
```

**参数说明**：
- `-t:FsGame` — 只编译 FsGame 项目（不编译整个解决方案，节省时间）
- `-p:Configuration=Debug` — Debug 配置（与开发环境一致）
- `-p:Platform=x64` — 64位平台
- `-v:minimal` — 最小输出（只显示警告和错误）

---

### 3.4 验证通过标准

**三个条件必须同时满足**：
1. 退出码为 0：`echo $?` 输出 0
2. 无 error 关键词：`grep -i "error" build.log` 无输出（忽略 "0 Error(s)" 这种统计行）
3. 生成了目标文件：`ls Builds/FsGame/Debug/*.obj | wc -l` > 0

---

### 3.5 编码相关报错特殊处理

**如果出现以下错误模式，优先检查 GBK 编码安全**（详见 `rules/apply/server-execution.md` 第2节）：

| 错误信息 | 根因 | 处理 |
|---------|------|------|
| `error C2001: 常量中有换行符` | UTF-8 替换字符 U+FFFD 破坏了字符串常量 | `svn revert` + 重新用 Python bytes 修改 |
| `error C1057: 宏扩展中遇到意外的文件结束` | 级联错误（通常跟随 C2001） | 同上 |
| 100+ 级联错误，第一个错误在 include 附近 | 头文件被误改编码 | 检查该头文件是否被 Edit 工具碰过 |

**检测编码损坏**：
```bash
python -c "print(open('<file>', 'rb').read().count(b'\xef\xbf\xbd'))"
# 输出 > 0 → 文件已损坏，包含 U+FFFD 替换字符
```

---

### 3.6 常见服务端编译错误速查

| 错误类型 | 处理方式 |
|---------|---------|
| 头文件缺失（`fatal error: xxx.h: No such file`）| 检查 `#include` 路径，补充缺失头文件 |
| 链接错误（`undefined reference to`）| 检查 Makefile 是否包含对应模块，或函数声明与实现不匹配 |
| 未声明的标识符（`error C2065: "XXX": 未声明的标识符`）| 检查常量/宏定义是否缺失，或头文件未包含 |
| 函数参数错误（`error C2660: 函数不接受 N 个参数`）| 检查函数签名，确认参数数量和类型 |

---

## 4. 孤儿产物检查（apply 阶段必检）

### 4.1 什么是孤儿产物

**定义**：已生成、能编译通过，但运行时不起作用的代码产物。

**典型案例**：
- 配置表 `.cs` 生成了，但没在 `TableConfig.cs` 注册 → 运行时不加载，所有查询取空
- `CommandID.OnXxx` 有监听方但无发送方 → 事件永远不会触发
- `UIID.XxxPanel` 注册了但无调用方 → 界面永远打不开
- `RegisterPropHook` 注册了 hook 但无属性挂载 → 回调永远不会被调用

**为什么编译抓不到**：编译只检查"引用了不存在的东西"，孤儿产物是反向的"存在但没人引用"。

---

### 4.2 检查时机

**apply 阶段 6.4 编译门禁后立即执行**，与编译验证并列（不是替代）：

```
[Client] 任务完成 → 增量编译验证（本文件第 1/2 节）→ 孤儿检查（本节）→ 勾选 checkbox
[Server] 任务完成 → 服务端编译验证（本文件第 3 节）→ 孤儿检查（本节）→ 勾选 checkbox
```

**为什么不能跳过**：Integration 阶段（TC-xxx 人工验证）能发现孤儿产物，但那是最慢最贵的关卡。在 apply 阶段机械检查，成本几乎为零。

---

### 4.3 执行命令

**脚本路径**：`schemas/lr-func-dev/rules/common/orphan-check.py`

**推荐用法（apply 阶段）**：
```bash
python orphan-check.py --change <change-id>
# 示例：检查 marriage-func 变更的产物
python orphan-check.py --change marriage-func
```

**工作原理**：
- 从 `changes/<change-id>/tasks.md` 和 `design.md` 提取产物清单（配置表/UI/CommandID/模块）
- 只检查清单里声明的产物是否生成 + 注册 + 接线
- 能检出"声明但未生成"（如 `TDWeddingSkillTable` tasks 里写了但没导表）

**CI/CR 阶段用法（待实现）**：
```bash
python orphan-check.py --diff origin/main...HEAD
```

---

### 4.4 检查项清单

| 检查项 | 孤儿模式 | 处理 |
|-------|---------|------|
| **配置表注册** | `Generate/**/TD*Table.cs` 已生成但未在 `TableConfig.cs` 注册 | 补注册到 `delayLoadTableArray` |
| **UI 面板接线** | `UIDefine.cs` 定义 `UIID.XxxPanel` 但未在 `UIDataTable.cs` 注册 | 补 `AddPanelData` 注册 |
| | `UIDataTable.cs` 已注册但无任何 `OpenPanel` 调用方 | 核查是否通过父 Panel 间接打开（Page 合法），否则补调用方 |
| **CommandID 事件接线** | 有监听方（`AddDynamicCommand`）但无发送方（`CommandDynamic`） | 补发送方，或确认从 Lua 发送 |
| | 有发送方但无监听方 | 补监听方，或确认为内部通知无需外部监听 |
| **属性监听 Hook** | `RegisterPropHook` 注册了 hook 名但无任何 `AddPropHook` 挂载 | 补属性挂载，或删除无用 hook |

---

### 4.5 输出解读

**退出码**：
- `0` = 未发现孤儿
- `1` = 发现孤儿（警告列表输出到 stdout）
- `2` = 脚本执行错误

**警告格式**：
```
TABLE: TDWeddingConditionTable 已生成但未在 TableConfig.cs 注册（运行时不会加载）
UI: UIID.MarriageProposeReceivePanel 已注册但无任何 OpenPanel 调用方（可能是孤儿）
CMD: CommandID.OnMarriageAffectionChanged 有 1 个监听方但无任何发送方
HOOK: "MarriageModule:OnWeddingPropertyChanged" 在 MarriageModule.cs 中注册但无任何属性挂载
```

**合法例外（不需要修复）**：
- UI Page 通过父 Panel 的页签切换打开，不是 `OpenPanel` 直接调用
- CommandID 从 Lua 发送（如 `OnLuaXxx`）
- CommandID 为协议回包内部通知，不需要外部监听方
- 编辑器专用表（如 `TDGmListTable`，只在 `#if UNITY_EDITOR` 中注册）

**处理建议**：
- 警告数 = 0 → 通过，继续
- 警告数 > 0 → 人工核查每条警告，确认是否为合法例外
  - 合法例外 → 在 implementation-report.md 注明"已核查，为合法例外"
  - 真孤儿 → 立即修复（补注册/补调用/删产物），重新编译验证

---

### 4.6 apply 阶段集成示例

**步骤 6.4 编译验证后追加**：

```markdown
#### 6.4.6 孤儿产物检查（apply 阶段必检）

对于 [Client]/[Server]/[Config] 任务，编译通过后立即执行孤儿检查：

\```bash
python schemas/lr-func-dev/rules/common/orphan-check.py --scope <模块名>
\```

**退出码 0** → 无孤儿，继续勾选 checkbox

**退出码 1** → 发现警告，人工核查：
- 合法例外（Page 通过父 Panel 打开、Lua 驱动的 CommandID 等）→ 在 implementation-report.md 记录"已核查"
- 真孤儿 → 立即修复（补注册/补调用），重新编译+孤儿检查，通过后再勾选

**退��码 2** → 脚本执行错误，检查 `CLIENT_ROOT` 环境变量或相对路径推断是否正确
```

---

## 5. 调用方集成指南

### 5.1 apply 阶段（lr-openspec-apply）

**引用位置**：
- 步骤 6.4.2 客户端增量编译检查 → 本文件第 1 节（Unity MCP 优先）或第 2 节（兜底）
- 步骤 6.4.3 客户端批量编译验证 → 同 6.4.2
- 步骤 6.4.5 服务端编译验证 → 本文件第 3 节
- 步骤 6.4.6 孤儿产物检查 → 本文件第 4 节（编译通过后立即执行）

**保留 apply 特有逻辑**：
- `fix_compile_errors.py` 自动修复流程（最多3轮）
- 编译检查点机制（Contract+Config 完成、Server 完成、Client 完成各触发一次）
- 增量 vs 批量检查的区分

---

### 5.2 reconcile 阶段（lr-openspec-reconcile）

**引用时机**：在"修复不一致"后，**立即触发**一次编译验证（不能等到下个阶段）

**客户端修复**：
- 推荐：本文件第 1 节（Unity MCP）
- 兜底：本文件第 2 节（dotnet build）

**服务端修复**：
- 本文件第 3 节（MSBuild）

**编译失败处理**：
- 如果是自动修复引入的新错误 → 回退修复，输出"无法自动修复，需人工判定"
- 如果是原代码已有的错误 → 记录到报告，标记"代码库存在编译问题，不是本次修复引入"

---

### 5.3 code-review 阶段（lr-openspec-code-review）

**引用时机**：如果审查过程中修复了代码，建议立即编译验证（可选）

**客户端**：本文件第 1 节（Unity MCP 优先）
**服务端**：本文件第 3 节

**注意**：code-review 主要是审查不是修复，所以编译验证是可选的。如果只输出审查报告不动代码，跳过此步骤。

---

### 5.4 ui-prefab 阶段（lr-openspec-ui-prefab）

**引用位置**：
- 步骤 6 部署完成后 → 本文件第 1.2 节（`assets-refresh` 触发编译）
- 步骤 6 继续前 → 本文件第 1.3 节（轮询 `IsCompiling: false`，避免在编译中调用生成器）
- 步骤 7.5 Unity Console 检查 → 本文件第 1.4 节（`console-get-logs` 检查错误）

ui-prefab 已经在用 Unity MCP 做编译状态检测，当前 SKILL.md 的实现可以直接引用本文件而不是重复维护相同逻辑。

---

## 6. 设计原则

### 6.1 Unity MCP 优于 dotnet build（客户端）

**原因**：
1. **覆盖真实依赖图**：Unity MCP 走的是 Unity Editor 自己的编译管线，自动覆盖所有 321 个 asmdef，不需要猜"这个模块归哪个 csproj 管"
2. **平台条件一致**：Unity 内部编译会处理 `#if UNITY_EDITOR` 等宏定义，`dotnet build` 走的是 MSBuild/Roslyn 独立编译，两边对同一份代码的宏解析可能不同
3. **无假阴性风险**：`dotnet build Assembly-CSharp.csproj` 只编译默认程序集，独立 asmdef 模块的错误会被漏检

### 6.2 MSBuild 路径枚举是必要兜底（服务端）

**为什么不能封装成一个 bat 脚本**：
- 服务端现有的 `build.bat` 依赖不可靠的 `%VS2022_HOME%` 环境变量（当前环境未设置）
- 它编译的是整个 `server2017.sln`，不是 apply 需要的 `-t:FsGame` 单目标（编译时间差3-5倍）
- 它用的是 `devenv.exe`（VS IDE），不是 `MSBuild.exe`（命令行工具），依赖 GUI 环境

**多路径枚举的价值**：
- 适配不同开发者的 VS 版本（2022 Enterprise/Professional、2019）
- 不依赖环境变量配置（路径探测是幂等的、可预测的）
- 是没有统一封装脚本时的唯一可靠方案

### 6.3 本文件只定义"怎么验证"，不定义"什么时候验证"

**触发时机由各 SKILL 自行决定**：
- apply 有编译检查点机制（批次边界触发），适合大规模代码生成
- reconcile 是修复后立即验证，适合单点修复
- code-review 是可选验证，适合人工审查为主的场景

本文件只提供标准化的验证流程，不强制所有 SKILL 在同一时机调用。

---

**版本**: v1（提炼自 lr-openspec-apply/SKILL.md 6.5 编译验证章节）
**最后更新**: 2026-08-06
**维护原则**: 这是 `lr-func-dev` schema 下所有会修改代码的 SKILL 共享的编译验证规范，唯一来源，不在各 SKILL.md 里重复维护
