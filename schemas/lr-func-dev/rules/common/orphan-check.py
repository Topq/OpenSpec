#!/usr/bin/env python3
"""
孤儿产物检查脚本 - 检测已生成但未接线的代码产物

使用场景：apply 阶段 6.4 编译门禁后调用，捕获"能编译但运行时无效"的产物

检查项：
1. Generate/**/TD*Table.cs → TableConfig.cs 注册
2. UIDefine.cs 新增 UIID → UIDataTable.cs 注册 + 至少一个 OpenPanel 调用
3. CommandID.cs 新增事件 → 既有发送方又有监听方
4. RegisterPropHook 的 hook 名 → 至少一个 AddPropHook 使用

运行模式：
  --change <change-id>   以 change 为单位，从 tasks.md 提取产物清单（apply 阶段推荐）
  --diff <git-ref>       以 git diff 为单位，只查增量修改（CI/CR 阶段用，待实现）

输出：警告列表（允许合法例外，不硬阻断）
返回码：0=无孤儿 / 1=发现孤儿 / 2=脚本错误
"""

import os
import re
import sys
import glob
import argparse
from pathlib import Path
from collections import defaultdict

# 项目根路径（从环境变量或相对路径推断）
CLIENT_ROOT = os.environ.get('CLIENT_ROOT') or Path(__file__).resolve().parents[5] / 'develop/client/project'
OPENSPEC_ROOT = os.environ.get('OPENSPEC_ROOT') or Path(__file__).resolve().parents[4]  # orphan-check.py 在 rules/common/，往上 4 层到 openspec/

if not CLIENT_ROOT.exists():
    print(f"ERROR: CLIENT_ROOT not found at {CLIENT_ROOT}", file=sys.stderr)
    sys.exit(2)

CLIENT_ROOT = Path(CLIENT_ROOT)
OPENSPEC_ROOT = Path(OPENSPEC_ROOT)
ASSETS = CLIENT_ROOT / 'Assets/Script'

# 全局：当前检查的产物清单（通过 --change 或 --diff 填充）
ARTIFACTS = {
    'tables': set(),       # TDWeddingConditionTable
    'uiids': set(),        # MarriageProposePanel
    'command_ids': set(),  # OnMarriageRelationChanged
    'modules': set(),      # MarriageModule
}


# ============ 产物清单提取（--change 模式）============

def extract_artifacts_from_tasks(change_id):
    """从 tasks.md 提取当前 change 声明的产物清单"""
    tasks_path = OPENSPEC_ROOT / f'changes/{change_id}/tasks.md'

    if not tasks_path.exists():
        print(f"ERROR: tasks.md not found at {tasks_path}", file=sys.stderr)
        sys.exit(2)

    with open(tasks_path, encoding='utf-8') as f:
        content = f.read()

    artifacts = {
        'tables': set(),
        'uiids': set(),
        'command_ids': set(),
        'modules': set(),
    }

    # 1. 配置表：只从 [Config]/[Client] 任务的"生成文件"或"目标路径"提取
    # 匹配 TDXxxTable.cs 或 TDXxx.cs（后者自动补 Table 后缀）
    # 格式：Assets/Script/Table/Generate/.../TDWeddingCondition.cs / TDWeddingSkill.cs / ...
    for match in re.finditer(r'\b(TD\w+?)(?:Table)?\.cs\b', content):
        table_name = match.group(1)  # 已含 TD 前缀
        # 过滤掉非表类（如 TDTableMetaData）
        if 'TableMetaData' in table_name or table_name == 'TDTableBase':
            continue
        if not table_name.endswith('Table'):
            table_name += 'Table'
        artifacts['tables'].add(table_name)

    # 2. UI 面板：从 [Client] UI 任务的"目标路径"或代码树提取
    # 匹配格式：
    #   - 完整路径：Assets/Script/UISript/.../XxxPanel.cs
    #   - UIID 引用：UIID.XxxPanel
    #   - 代码树形式：Assets/Script/UISript/XxxPanel/ 后跟文件列表
    # 排除通用词：OpenPanel/FindPanel 等（这些是 API 不是 UIID）
    exclude_uiids = {'OpenPanel', 'FindPanel', 'ClosePanel', 'RefreshPanel', 'HidePanel'}

    # 提取完整路径和 UIID 引用形式
    for match in re.finditer(r'(?:UISript/\w+/|UIID\.)([A-Z]\w+(?:Panel|Page))(?:\.cs)?\b', content):
        uiid = match.group(1)
        if uiid not in exclude_uiids:
            artifacts['uiids'].add(uiid)

    # 提取代码树形式：查找 "Assets/Script/UISript/XxxPanel/" 后的文件列表
    # 使用两步匹配：先找目录声明行，再找后续的 ├── 或 └── 开头的 .cs 文件
    for dir_match in re.finditer(r'Assets/Script/UISript/\w+/\s*\n', content):
        # 从目录行后开始，收集所有 ├── 或 └── 开头的 Panel/Page 文件
        start = dir_match.end()
        for file_match in re.finditer(r'^[├└]── ([A-Z]\w+(?:Panel|Page))\.cs', content[start:], re.MULTILINE):
            uiid = file_match.group(1)
            if uiid not in exclude_uiids:
                artifacts['uiids'].add(uiid)
            # 只扫描到第一个空行或非树形符号行为止
            if start + file_match.end() >= len(content) or content[start + file_match.end():start + file_match.end() + 100].startswith('\n\n'):
                break

    # 3. CommandID：只从 design.md 的"数据流"章节或 tasks.md 的 CommandID 定义提取
    # 排除通用生命周期方法：OnInit/OnOpen/OnClose/OnUpdate/OnDestroy 等
    exclude_cmds = {
        'OnInit', 'OnOpen', 'OnClose', 'OnUpdate', 'OnDestroy', 'OnCreate', 'OnReset',
        'OnEnable', 'OnDisable', 'OnStart', 'OnLogin', 'OnLogout', 'OnHeartBeat',
        'OnPlayerDelete', 'OnServerMerge',  # 全局事件，不是 change 特有
    }
    # 从 tasks.md 提取明确的 CommandID 枚举定义（通常在 CommandID.cs 添加行附近）
    for match in re.finditer(r'CommandID\.((On[A-Z]\w+))\b', content):
        cmd = match.group(1)
        if cmd not in exclude_cmds:
            artifacts['command_ids'].add(cmd)

    # 也从 design.md 提取（数据流设计里会明确写 CommandDynamic/AddDynamicCommand）
    design_path = OPENSPEC_ROOT / f'changes/{change_id}/design.md'
    if design_path.exists():
        with open(design_path, encoding='utf-8') as f:
            design_content = f.read()
        # 只提取明确调用 CommandDynamic 的地方
        for match in re.finditer(r'CommandDynamic\(CommandID\.((On[A-Z]\w+))\)', design_content):
            cmd = match.group(1)
            if cmd not in exclude_cmds:
                artifacts['command_ids'].add(cmd)

    # 4. 模块：从任务的"目标路径"提取 Module 目录名
    # 匹配格式：Assets/Script/LogicModule/XxxModule/
    for match in re.finditer(r'Assets/Script/LogicModule/(\w+Module)/', content):
        module = match.group(1)
        artifacts['modules'].add(module)

    return artifacts


# ============ 检查项 1: 配置表注册 ============

def check_table_registration():
    """检查 Generate 目录下实际生成的表是否在 TableConfig.cs 注册（仅检查本 change 相关的表）"""
    warnings = []

    # 如果 tasks.md 没提取到任何表，说明本 change 不涉及配置表，跳过检查
    if not ARTIFACTS['tables']:
        return []

    # 从 tasks.md 提取的表名推断目录范围（例如 TDWeddingXxxTable → Table/Generate/Wedding/）
    # 提取表名前缀（TD 后的第一个单词，如 TDWedding → Wedding）
    prefixes = set()
    for table in ARTIFACTS['tables']:
        match = re.match(r'TD([A-Z][a-z]+)', table)
        if match:
            prefixes.add(match.group(1))

    if not prefixes:
        # 无法推断范围，检查所有 tasks.md 声明的表
        target_tables = ARTIFACTS['tables']
    else:
        # 扫描推断范围内的所有表
        target_tables = set()
        for prefix in prefixes:
            pattern = ASSETS / f'Table/Generate/{prefix}/*Table.cs'
            for cs_file in glob.glob(str(pattern)):
                try:
                    with open(cs_file, encoding='utf-8-sig') as f:
                        src = f.read()
                        match = re.search(r'\bclass\s+(TD\w+Table)\b', src)
                        if match and 'metaData' in src:
                            target_tables.add(match.group(1))
                except:
                    pass

    if not target_tables:
        return []  # 范围内没有生成任何表

    # 读取 TableConfig.cs 注册情况
    config_path = ASSETS / 'Table/TableConfig.cs'
    if not config_path.exists():
        return [f"CRITICAL: TableConfig.cs not found at {config_path}"]

    with open(config_path, encoding='utf-8-sig') as f:
        config_src = f.read()

    registered_tables = set(re.findall(r'\b(TD\w+Table)\.metaData\b', config_src))

    # 检查范围内的表
    for table in sorted(target_tables):
        if table not in registered_tables:
            warnings.append(f"TABLE: {table} 已生成但未在 TableConfig.cs 注册（运行时不会加载）")
        else:
            # 检查是否重复注册
            count = len(re.findall(rf'\b{table}\.metaData\b', config_src))
            if count > 1:
                warnings.append(f"TABLE: {table} 在 TableConfig.cs 重复注册 {count} 次")

    return warnings


# ============ 检查项 2: UI 面板接线 ============

def check_ui_panels():
    """检查本 change 相关的已注册 UIID 是否有调用方"""
    warnings = []

    # 如果 tasks.md 没提取到任何 UI，说明本 change 不涉及 UI，跳过检查
    if not ARTIFACTS['uiids']:
        return []

    # 读取 UIDataTable.cs 注册情况
    data_table_path = ASSETS / 'LogicModule/UIModule/Data/UIDataTable.cs'
    if not data_table_path.exists():
        return [f"CRITICAL: UIDataTable.cs not found"]

    with open(data_table_path, encoding='utf-8-sig') as f:
        data_src = f.read()

    registered = set(re.findall(r'AddPanelData\s*\(\s*UIID\.(\w+)', data_src))

    # 只检查 tasks.md 声明的 UI（而不是整个代码库的所有 UI）
    target_uiids = ARTIFACTS['uiids'] & registered  # 交集：声明了且已注册的

    if not target_uiids:
        return []  # 本 change 的 UI 都未注册或未生成

    # 扫描所有 OpenPanel / OpenDependPanel / AttachPage 调用
    open_calls = defaultdict(int)
    for cs_file in glob.glob(str(ASSETS / '**/*.cs'), recursive=True):
        try:
            with open(cs_file, encoding='utf-8-sig') as f:
                src = f.read()
                # OpenPanel 直接调用
                for match in re.finditer(r'OpenPanel\s*\(\s*UIID\.(\w+)', src):
                    open_calls[match.group(1)] += 1
                # OpenDependPanel 间接调用（Page 被父 Panel 打开的常见模式）
                for match in re.finditer(r'OpenDependPanel\s*\(\s*UIID\.(\w+)', src):
                    open_calls[match.group(1)] += 1
                # AttachPage 调用（Page 被 Panel 动态加载的模式）
                for match in re.finditer(r'AttachPage\s*\(\s*UIID\.(\w+)', src):
                    open_calls[match.group(1)] += 1
        except:
            pass

    # 检查本 change 的 UI
    for uiid in sorted(target_uiids):
        if open_calls.get(uiid, 0) == 0:
            # Page 通过父 Panel 间接打开是合法的，标记为"可能孤儿"
            if 'Page' in uiid:
                warnings.append(f"UI: UIID.{uiid} 已注册但无 OpenPanel/OpenDependPanel 直接调用（Page 通过父 Panel 打开属于合法例外）")
            else:
                warnings.append(f"UI: UIID.{uiid} 已注册但无任何 OpenPanel/OpenDependPanel 调用方（可能是孤儿）")

    return warnings


# ============ 检查项 3: CommandID 事件接线 ============

def check_command_events():
    """检查本 change 相关的 CommandID 是否既有发送方又有监听方"""
    warnings = []

    # 如果 tasks.md 没提取到任何 CommandID，说明本 change 不涉及事件，跳过检查
    if not ARTIFACTS['command_ids']:
        return []

    # 读取 CommandID.cs
    cmd_path = ASSETS / 'Define/CommandID.cs'
    if not cmd_path.exists():
        return [f"CRITICAL: CommandID.cs not found"]

    with open(cmd_path, encoding='utf-8-sig') as f:
        cmd_src = f.read()

    defined_cmds = set(re.findall(r'^\s+(\w+),\s*//.*$', cmd_src, re.MULTILINE))

    # 扫描发送方和监听方
    senders = defaultdict(int)
    listeners = defaultdict(int)

    for cs_file in glob.glob(str(ASSETS / '**/*.cs'), recursive=True):
        try:
            with open(cs_file, encoding='utf-8-sig') as f:
                src = f.read()
                for match in re.finditer(r'CommandDynamic\s*\(\s*CommandID\.(\w+)', src):
                    senders[match.group(1)] += 1
                for match in re.finditer(r'AddDynamicCommand\s*\(\s*CommandID\.(\w+)', src):
                    listeners[match.group(1)] += 1
        except:
            pass

    # 只检查 tasks.md 声明的 CommandID
    target_cmds = ARTIFACTS['command_ids'] & defined_cmds  # 交集：声明了且已定义的

    for cmd in sorted(target_cmds):
        s_count = senders.get(cmd, 0)
        l_count = listeners.get(cmd, 0)

        if s_count == 0 and l_count > 0:
            warnings.append(f"CMD: CommandID.{cmd} 有 {l_count} 个监听方但无任何发送方（事件永远不会触发）")
        elif s_count > 0 and l_count == 0:
            # 允许例外：协议回包内部通知、Lua 驱动的事件
            if 'Lua' in cmd or 'Notify' in cmd or 'Received' in cmd:
                # 这些通常是协议回包的内部通知，不需要外部监听方
                pass
            else:
                warnings.append(f"CMD: CommandID.{cmd} 有 {s_count} 个发送方但无任何监听方（事件无人处理）")

    return warnings


# ============ 检查项 4: 属性监听 Hook 接线 ============

def check_prop_hooks():
    """检查声明模块中 RegisterPropHook 注册的 hook 是否有 AddPropHook 使用"""
    warnings = []

    if not ARTIFACTS['modules']:
        return []

    # 扫描声明模块中的所有 RegisterPropHook 调用
    registered_hooks = defaultdict(list)  # hook_name -> [file, ...]

    for module_name in ARTIFACTS['modules']:
        module_dir = ASSETS / f'LogicModule/{module_name}'
        if not module_dir.exists():
            warnings.append(f"HOOK: 模块目录 {module_dir} 不存在（tasks.md 声明但未创建）")
            continue

        for cs_file in glob.glob(str(module_dir / '*.cs')):
            try:
                with open(cs_file, encoding='utf-8-sig') as f:
                    src = f.read()
                    for match in re.finditer(r'RegisterPropHook\s*\(\s*"([^"]+)"\s*,', src):
                        hook_name = match.group(1)
                        registered_hooks[hook_name].append(Path(cs_file).name)
            except:
                pass

    if not registered_hooks:
        return []  # 模块没有注册 Hook，跳过

    # 扫描所有 AddPropHook 调用
    used_hooks = set()

    for cs_file in glob.glob(str(ASSETS / '**/*.cs'), recursive=True):
        try:
            with open(cs_file, encoding='utf-8-sig') as f:
                src = f.read()
                # 字符串形式：AddPropHook(self, prop, "hook_name")
                for match in re.finditer(r'AddPropHook\s*\([^,]+,\s*[^,]+,\s*"([^"]+)"\s*\)', src):
                    used_hooks.add(match.group(1))
                # 常量形式：AddPropHook(self, prop, HOOK_NAME)
                for match in re.finditer(r'AddPropHook\s*\([^,]+,\s*[^,]+,\s*(\w+)\s*\)', src):
                    const_name = match.group(1)
                    if const_name.startswith('HOOK_'):
                        # 尝试反查常量值
                        const_match = re.search(rf'const\s+string\s+{const_name}\s*=\s*"([^"]+)"', src)
                        if const_match:
                            used_hooks.add(const_match.group(1))
        except:
            pass

    # 检查：注册了但无人使用
    for hook_name, files in sorted(registered_hooks.items()):
        if hook_name not in used_hooks:
            warnings.append(f"HOOK: \"{hook_name}\" 在 {', '.join(files)} 中注册但无任何属性挂载")

    return warnings


# ============ 主流程 ============

def main():
    global ARTIFACTS

    # 强制 UTF-8 输出（Windows 兼容）
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(description='孤儿产物检查脚本')
    parser.add_argument('--change', help='以 change 为单位，从 tasks.md 提取产物清单（apply 阶段推荐）')
    parser.add_argument('--diff', help='以 git diff 为单位，只查增量修改（CI/CR 阶段用，待实现）')
    args = parser.parse_args()

    if args.change:
        mode_desc = f"change: {args.change}"
        ARTIFACTS = extract_artifacts_from_tasks(args.change)
    elif args.diff:
        print("ERROR: --diff 模式尚未实现，请使用 --change", file=sys.stderr)
        sys.exit(2)
    else:
        print("ERROR: 必须指定 --change <change-id> 或 --diff <git-ref>", file=sys.stderr)
        parser.print_help()
        sys.exit(2)

    print(f"=== 孤儿产物检查 ({mode_desc}) ===\n")
    print(f"产物清单：")
    print(f"  - 配置表: {len(ARTIFACTS['tables'])} 张")
    print(f"  - UI 面板: {len(ARTIFACTS['uiids'])} 个")
    print(f"  - CommandID: {len(ARTIFACTS['command_ids'])} 个")
    print(f"  - 模块: {len(ARTIFACTS['modules'])} 个")
    print()

    all_warnings = []

    print("1. 检查配置表注册...")
    all_warnings.extend(check_table_registration())

    print("2. 检查 UI 面板接线...")
    all_warnings.extend(check_ui_panels())

    print("3. 检查 CommandID 事件接线...")
    all_warnings.extend(check_command_events())

    print("4. 检查属性监听 Hook 接线...")
    all_warnings.extend(check_prop_hooks())

    print("\n=== 检查结果 ===\n")

    if not all_warnings:
        print("[OK] 未发现孤儿产物")
        return 0

    print(f"[WARNING] 发现 {len(all_warnings)} 个潜在孤儿产物：\n")
    for w in all_warnings:
        print(f"  - {w}")

    print("\n注意：部分警告可能是合法例外（如 Page 通过父 Panel 打开、协议回包内部通知）")
    print("请人工核查后决定是否需要修复\n")

    return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f"ERROR: 脚本执行失败 - {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)



# ============ 检查项 1: 配置表注册 ============

def check_table_registration():
    """检查 Generate/**/TD*Table.cs 是否在 TableConfig.cs 中注册"""
    warnings = []

    # 扫描所有生成的配置表类
    gen_tables = set()
    for cs_file in glob.glob(str(ASSETS / 'Table/Generate/**/*Table.cs'), recursive=True):
        with open(cs_file, encoding='utf-8-sig') as f:
            src = f.read()
            # 匹配 "public class TDXxxTable"
            match = re.search(r'\bclass\s+(TD\w+Table)\b', src)
            if match and 'metaData' in src:  # 确认有 metaData 字段
                table_name = match.group(1)
                if matches_scope(table_name):
                    gen_tables.add(table_name)

    if not gen_tables:
        return []  # 无生成表，跳过检查

    # 读取 TableConfig.cs
    config_path = ASSETS / 'Table/TableConfig.cs'
    if not config_path.exists():
        return [f"CRITICAL: TableConfig.cs not found at {config_path}"]

    with open(config_path, encoding='utf-8-sig') as f:
        config_src = f.read()

    # 检查每个表的注册次数
    for table in sorted(gen_tables):
        pattern = rf'\b{table}\.metaData\b'
        matches = re.findall(pattern, config_src)
        count = len(matches)

        if count == 0:
            warnings.append(f"TABLE: {table} 已生成但未在 TableConfig.cs 注册（运行时不会加载）")
        elif count > 1:
            warnings.append(f"TABLE: {table} 在 TableConfig.cs 重复注册 {count} 次")

    return warnings


# ============ 检查项 2: UI 面板接线 ============

def check_ui_panels():
    """检查 UIDefine 新增 UIID 是否在 UIDataTable 注册 + 有调用方"""
    warnings = []

    # 读取 UIDefine.cs 所有 UIID 枚举
    define_path = ASSETS / 'Define/UIDefine.cs'
    if not define_path.exists():
        return []

    with open(define_path, encoding='utf-8-sig') as f:
        define_src = f.read()

    uiids = set(re.findall(r'^\s+(\w+),\s*//.*$', define_src, re.MULTILINE))
    uiids = {u for u in uiids if matches_scope(u)}

    if not uiids:
        return []

    # 读取 UIDataTable.cs 注册情况
    data_table_path = ASSETS / 'LogicModule/UIModule/Data/UIDataTable.cs'
    if not data_table_path.exists():
        return [f"CRITICAL: UIDataTable.cs not found"]

    with open(data_table_path, encoding='utf-8-sig') as f:
        data_src = f.read()

    registered = set(re.findall(r'AddPanelData\s*\(\s*UIID\.(\w+)', data_src))

    # 扫描所有 OpenPanel 调用
    open_calls = defaultdict(int)
    for cs_file in glob.glob(str(ASSETS / '**/*.cs'), recursive=True):
        try:
            with open(cs_file, encoding='utf-8-sig') as f:
                src = f.read()
                for match in re.finditer(r'OpenPanel\s*\(\s*UIID\.(\w+)', src):
                    open_calls[match.group(1)] += 1
        except:
            pass

    # 启发式判断：以 "Panel" 结尾或包含 "Page" 的 UIID 为面板
    for uiid in sorted(uiids):
        if not ('Panel' in uiid or 'Page' in uiid):
            continue

        if uiid not in registered:
            warnings.append(f"UI: UIID.{uiid} 定义了但未在 UIDataTable 注册（无法打开）")
        elif open_calls.get(uiid, 0) == 0:
            warnings.append(f"UI: UIID.{uiid} 已注册但无任何 OpenPanel 调用方（可能是孤儿）")

    return warnings


# ============ 检查项 3: CommandID 事件接线 ============

def check_command_events():
    """检查 CommandID 新增事件是否既有发送方又有监听方"""
    warnings = []

    # 读取 CommandID.cs
    cmd_path = ASSETS / 'Define/CommandID.cs'
    if not cmd_path.exists():
        return []

    with open(cmd_path, encoding='utf-8-sig') as f:
        cmd_src = f.read()

    # 提取所有 CommandID（以 On 开头的事件居多）
    cmd_ids = set(re.findall(r'^\s+(On\w+),\s*//.*$', cmd_src, re.MULTILINE))
    cmd_ids = {c for c in cmd_ids if matches_scope(c)}

    if not cmd_ids:
        return []

    # 扫描发送方和监听方
    senders = defaultdict(int)
    listeners = defaultdict(int)

    for cs_file in glob.glob(str(ASSETS / '**/*.cs'), recursive=True):
        try:
            with open(cs_file, encoding='utf-8-sig') as f:
                src = f.read()
                for match in re.finditer(r'CommandDynamic\s*\(\s*CommandID\.(\w+)', src):
                    senders[match.group(1)] += 1
                for match in re.finditer(r'AddDynamicCommand\s*\(\s*CommandID\.(\w+)', src):
                    listeners[match.group(1)] += 1
        except:
            pass

    # 检查：有 CommandID 但无发送方或无监听方
    for cmd in sorted(cmd_ids):
        s_count = senders.get(cmd, 0)
        l_count = listeners.get(cmd, 0)

        if s_count == 0 and l_count > 0:
            warnings.append(f"CMD: CommandID.{cmd} 有 {l_count} 个监听方但无任何发送方")
        elif s_count > 0 and l_count == 0:
            # 允许例外：某些 CommandID 从 Lua 发送
            if cmd.startswith('OnLua') or 'Lua' in cmd:
                continue
            warnings.append(f"CMD: CommandID.{cmd} 有 {s_count} 个发送方但无任何监听方")

    return warnings


# ============ 检查项 4: 属性监听 Hook 接线 ============

def check_prop_hooks():
    """检查 RegisterPropHook 注册的 hook 名是否有 AddPropHook 使用"""
    warnings = []

    # 扫描所有 RegisterPropHook 调用
    registered_hooks = defaultdict(list)  # hook_name -> [file, ...]

    for cs_file in glob.glob(str(ASSETS / '**/*.cs'), recursive=True):
        # 范围过滤：只检查文件名匹配的模块
        if SCOPE_FILTER and not matches_scope(Path(cs_file).stem):
            continue

        try:
            with open(cs_file, encoding='utf-8-sig') as f:
                src = f.read()
                for match in re.finditer(r'RegisterPropHook\s*\(\s*"([^"]+)"\s*,', src):
                    hook_name = match.group(1)
                    registered_hooks[hook_name].append(Path(cs_file).name)
        except:
            pass

    if not registered_hooks:
        return []  # 无新增 hook，跳过

    # 扫描所有 AddPropHook 调用
    used_hooks = set()

    for cs_file in glob.glob(str(ASSETS / '**/*.cs'), recursive=True):
        try:
            with open(cs_file, encoding='utf-8-sig') as f:
                src = f.read()
                for match in re.finditer(r'AddPropHook\s*\([^,]+,\s*[^,]+,\s*"([^"]+)"\s*\)', src):
                    used_hooks.add(match.group(1))
                # 也支持常量形式：AddPropHook(self, prop, HOOK_NAME)
                for match in re.finditer(r'AddPropHook\s*\([^,]+,\s*[^,]+,\s*(\w+)\s*\)', src):
                    const_name = match.group(1)
                    if const_name.startswith('HOOK_'):
                        # 尝试反查常量值
                        const_match = re.search(rf'const\s+string\s+{const_name}\s*=\s*"([^"]+)"', src)
                        if const_match:
                            used_hooks.add(const_match.group(1))
        except:
            pass

    # 检查：注册了但无人使用
    for hook_name, files in sorted(registered_hooks.items()):
        if hook_name not in used_hooks:
            warnings.append(f"HOOK: \"{hook_name}\" 在 {', '.join(files)} 中注册但无任何属性挂载")

    return warnings


# ============ 主流程 ============

def main():
    global SCOPE_FILTER

    # 强制 UTF-8 输出（Windows 兼容）
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(description='孤儿产物检查脚本')
    parser.add_argument('--scope', help='只检查包含该关键词的产物（如 Marriage）')
    parser.add_argument('--full', action='store_true', help='检查全仓库（默认）')
    args = parser.parse_args()

    SCOPE_FILTER = args.scope

    scope_desc = f" (范围: {SCOPE_FILTER})" if SCOPE_FILTER else " (全仓库)"
    print(f"=== 孤儿产物检查{scope_desc} ===\n")

    all_warnings = []

    print("1. 检查配置表注册...")
    all_warnings.extend(check_table_registration())

    print("2. 检查 UI 面板接线...")
    all_warnings.extend(check_ui_panels())

    print("3. 检查 CommandID 事件接线...")
    all_warnings.extend(check_command_events())

    print("4. 检查属性监听 Hook 接线...")
    all_warnings.extend(check_prop_hooks())

    print("\n=== 检查结果 ===\n")

    if not all_warnings:
        print("[OK] 未发现孤儿产物")
        return 0

    print(f"[WARNING] 发现 {len(all_warnings)} 个潜在孤儿产物：\n")
    for w in all_warnings:
        print(f"  - {w}")

    if not SCOPE_FILTER:
        print("\n提示：使用 --scope <关键词> 缩小检查范围（如 --scope Marriage）")
    print("注意：部分警告可能是合法例外（如编辑器专用表、Lua 驱动的 CommandID、Page 通过父 Panel 打开）")
    print("请人工核查后决定是否需要修复\n")

    return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f"ERROR: 脚本执行失败 - {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)


# ============ 检查项 1: 配置表注册 ============

def check_table_registration():
    """检查 Generate/**/TD*Table.cs 是否在 TableConfig.cs 中注册"""
    warnings = []

    # 扫描所有生成的配置表类
    gen_tables = set()
    for cs_file in glob.glob(str(ASSETS / 'Table/Generate/**/*Table.cs'), recursive=True):
        with open(cs_file, encoding='utf-8-sig') as f:
            src = f.read()
            # 匹配 "public class TDXxxTable"
            match = re.search(r'\bclass\s+(TD\w+Table)\b', src)
            if match and 'metaData' in src:  # 确认有 metaData 字段
                gen_tables.add(match.group(1))

    if not gen_tables:
        return []  # 无生成表，跳过检查

    # 读取 TableConfig.cs
    config_path = ASSETS / 'Table/TableConfig.cs'
    if not config_path.exists():
        return [f"CRITICAL: TableConfig.cs not found at {config_path}"]

    with open(config_path, encoding='utf-8-sig') as f:
        config_src = f.read()

    # 检查每个表的注册次数
    for table in sorted(gen_tables):
        pattern = rf'\b{table}\.metaData\b'
        matches = re.findall(pattern, config_src)
        count = len(matches)

        if count == 0:
            warnings.append(f"TABLE: {table} 已生成但未在 TableConfig.cs 注册（运行时不会加载）")
        elif count > 1:
            warnings.append(f"TABLE: {table} 在 TableConfig.cs 重复注册 {count} 次")

    return warnings


# ============ 检查项 2: UI 面板接线 ============

def check_ui_panels():
    """检查 UIDefine 新增 UIID 是否在 UIDataTable 注册 + 有调用方"""
    warnings = []

    # 读取 UIDefine.cs 所有 UIID 枚举
    define_path = ASSETS / 'Define/UIDefine.cs'
    if not define_path.exists():
        return []

    with open(define_path, encoding='utf-8-sig') as f:
        define_src = f.read()

    uiids = set(re.findall(r'^\s+(\w+),\s*//.*$', define_src, re.MULTILINE))

    # 读取 UIDataTable.cs 注册情况
    data_table_path = ASSETS / 'LogicModule/UIModule/Data/UIDataTable.cs'
    if not data_table_path.exists():
        return [f"CRITICAL: UIDataTable.cs not found"]

    with open(data_table_path, encoding='utf-8-sig') as f:
        data_src = f.read()

    registered = set(re.findall(r'AddPanelData\s*\(\s*UIID\.(\w+)', data_src))

    # 扫描所有 OpenPanel 调用
    open_calls = defaultdict(int)
    for cs_file in glob.glob(str(ASSETS / '**/*.cs'), recursive=True):
        try:
            with open(cs_file, encoding='utf-8-sig') as f:
                src = f.read()
                for match in re.finditer(r'OpenPanel\s*\(\s*UIID\.(\w+)', src):
                    open_calls[match.group(1)] += 1
        except:
            pass

    # 启发式判断：以 "Panel" 结尾或包含 "Page" 的 UIID 为面板
    for uiid in sorted(uiids):
        if not ('Panel' in uiid or 'Page' in uiid):
            continue

        if uiid not in registered:
            warnings.append(f"UI: UIID.{uiid} 定义了但未在 UIDataTable 注册（无法打开）")
        elif open_calls.get(uiid, 0) == 0:
            warnings.append(f"UI: UIID.{uiid} 已注册但无任何 OpenPanel 调用方（可能是孤儿）")

    return warnings


# ============ 检查项 3: CommandID 事件接线 ============

def check_command_events():
    """检查 CommandID 新增事件是否既有发送方又有监听方"""
    warnings = []

    # 读取 CommandID.cs
    cmd_path = ASSETS / 'Define/CommandID.cs'
    if not cmd_path.exists():
        return []

    with open(cmd_path, encoding='utf-8-sig') as f:
        cmd_src = f.read()

    # 提取所有 CommandID（以 On 开头的事件居多）
    cmd_ids = set(re.findall(r'^\s+(On\w+),\s*//.*$', cmd_src, re.MULTILINE))

    # 扫描发送方和监听方
    senders = defaultdict(int)
    listeners = defaultdict(int)

    for cs_file in glob.glob(str(ASSETS / '**/*.cs'), recursive=True):
        try:
            with open(cs_file, encoding='utf-8-sig') as f:
                src = f.read()
                for match in re.finditer(r'CommandDynamic\s*\(\s*CommandID\.(\w+)', src):
                    senders[match.group(1)] += 1
                for match in re.finditer(r'AddDynamicCommand\s*\(\s*CommandID\.(\w+)', src):
                    listeners[match.group(1)] += 1
        except:
            pass

    # 检查：有 CommandID 但无发送方或无监听方
    for cmd in sorted(cmd_ids):
        s_count = senders.get(cmd, 0)
        l_count = listeners.get(cmd, 0)

        if s_count == 0 and l_count > 0:
            warnings.append(f"CMD: CommandID.{cmd} 有 {l_count} 个监听方但无任何发送方")
        elif s_count > 0 and l_count == 0:
            # 允许例外：某些 CommandID 从 Lua 发送
            if cmd.startswith('OnLua') or 'Lua' in cmd:
                continue
            warnings.append(f"CMD: CommandID.{cmd} 有 {s_count} 个发送方但无任何监听方")

    return warnings


# ============ 检查项 4: 属性监听 Hook 接线 ============

def check_prop_hooks():
    """检查 RegisterPropHook 注册的 hook 名是否有 AddPropHook 使用"""
    warnings = []

    # 扫描所有 RegisterPropHook 调用
    registered_hooks = defaultdict(list)  # hook_name -> [file, ...]

    for cs_file in glob.glob(str(ASSETS / '**/*.cs'), recursive=True):
        try:
            with open(cs_file, encoding='utf-8-sig') as f:
                src = f.read()
                for match in re.finditer(r'RegisterPropHook\s*\(\s*"([^"]+)"\s*,', src):
                    hook_name = match.group(1)
                    registered_hooks[hook_name].append(Path(cs_file).name)
        except:
            pass

    if not registered_hooks:
        return []  # 无新增 hook，跳过

    # 扫描所有 AddPropHook 调用
    used_hooks = set()

    for cs_file in glob.glob(str(ASSETS / '**/*.cs'), recursive=True):
        try:
            with open(cs_file, encoding='utf-8-sig') as f:
                src = f.read()
                for match in re.finditer(r'AddPropHook\s*\([^,]+,\s*[^,]+,\s*"([^"]+)"\s*\)', src):
                    used_hooks.add(match.group(1))
                # 也支持常量形式：AddPropHook(self, prop, HOOK_NAME)
                for match in re.finditer(r'AddPropHook\s*\([^,]+,\s*[^,]+,\s*(\w+)\s*\)', src):
                    const_name = match.group(1)
                    if const_name.startswith('HOOK_'):
                        # 尝试反查常量值
                        const_match = re.search(rf'const\s+string\s+{const_name}\s*=\s*"([^"]+)"', src)
                        if const_match:
                            used_hooks.add(const_match.group(1))
        except:
            pass

    # 检查：注册了但无人使用
    for hook_name, files in sorted(registered_hooks.items()):
        if hook_name not in used_hooks:
            warnings.append(f"HOOK: \"{hook_name}\" 在 {', '.join(files)} 中注册但无任何属性挂载")

    return warnings


# ============ 主流程 ============

def main():
    # 强制 UTF-8 输出（Windows 兼容）
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    print("=== 孤儿产物检查（Orphan Check）===\n")

    all_warnings = []

    print("1. 检查配置表注册...")
    all_warnings.extend(check_table_registration())

    print("2. 检查 UI 面板接线...")
    all_warnings.extend(check_ui_panels())

    print("3. 检查 CommandID 事件接线...")
    all_warnings.extend(check_command_events())

    print("4. 检查属性监听 Hook 接线...")
    all_warnings.extend(check_prop_hooks())

    print("\n=== 检查结果 ===\n")

    if not all_warnings:
        print("[OK] 未发现孤儿产物")
        return 0

    print(f"[WARNING] 发现 {len(all_warnings)} 个潜在孤儿产物：\n")
    for w in all_warnings:
        print(f"  - {w}")

    print("\n注意：部分警告可能是合法例外（如编辑器专用表、Lua 驱动的 CommandID）")
    print("请人工核查后决定是否需要修复\n")

    return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f"ERROR: 脚本执行失败 - {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)
