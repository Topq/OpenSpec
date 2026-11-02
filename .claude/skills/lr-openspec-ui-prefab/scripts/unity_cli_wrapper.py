#!/usr/bin/env python3
"""调用 Unity 命令行生成 Prefab 的包装脚本。

绕过 ai-game-developer MCP，直接使用 Unity 的 -executeMethod 参数调用
LRUnityLayoutCLI.GenerateFromEnv。

使用方式：
  python unity_cli_wrapper.py <unity-project> <json-path> <prefab-path> [script-type]

示例：
  python unity_cli_wrapper.py \
    ../develop/client/project \
    changes/growth-fund/demo/unity/GrowthFundPage.json \
    Assets/Resources/PanelUI/GrowthFundPanel.prefab \
    LR.GrowthFundPage

环境变量：
  UNITY_EXECUTABLE: Unity 可执行文件路径（可选，自动推断）
  LR_UNITY_TIMEOUT: 超时秒数（默认 300）

退出码：
  0 = 成功
  1 = 参数错误或 Unity 执行失败
  124 = 超时
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path, PurePosixPath

from validate_layout_json import validate_layout_json

if __name__ == "__main__" and sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def find_unity_executable(project_root: Path) -> Path:
    """从 ProjectVersion.txt 读取版本，推断 Unity 可执行文件路径。"""
    version_file = project_root / "ProjectSettings" / "ProjectVersion.txt"
    if not version_file.exists():
        raise FileNotFoundError(
            f"找不到 {version_file}\n"
            f"请确认 {project_root} 是有效的 Unity 项目根目录"
        )

    version_text = version_file.read_text(encoding="utf-8")
    version = None

    # 解析 "m_EditorVersion: 2020.3.48f1"
    for line in version_text.splitlines():
        if line.startswith("m_EditorVersion:"):
            version = line.split(":", 1)[1].strip()
            break

    if not version:
        raise ValueError(f"无法从 {version_file} 解析版本号")

    print(f"[unity_cli] 检测到 Unity 版本: {version}", file=sys.stderr)

    # 推断路径（Unity Hub 标准安装位置）
    if sys.platform == "win32":
        unity_exe = Path(f"C:/Program Files/Unity/Hub/Editor/{version}/Editor/Unity.exe")
    elif sys.platform == "darwin":
        unity_exe = Path(
            f"/Applications/Unity/Hub/Editor/{version}/Unity.app/Contents/MacOS/Unity"
        )
    else:  # Linux
        unity_exe = Path(f"~/Unity/Hub/Editor/{version}/Editor/Unity").expanduser()

    if not unity_exe.exists():
        raise FileNotFoundError(
            f"推断的 Unity 路径不存在: {unity_exe}\n"
            f"请手动设置环境变量 UNITY_EXECUTABLE 指向 Unity 可执行文件"
        )

    return unity_exe


def generate_prefab(
    unity_project: Path,
    json_path: Path,
    prefab_path: str,
    script_type: str | None = None,
    timeout: int = 300,
) -> int:
    """调用 Unity 生成 Prefab，返回退出码。

    Args:
        unity_project: Unity 项目根目录
        json_path: 布局 JSON 文件路径（绝对路径）
        prefab_path: Prefab 输出路径（Assets/... 格式）
        script_type: 根脚本类型名（可选，如 "LR.GrowthFundPage"）
        timeout: 超时秒数

    Returns:
        0 = 成功, 非 0 = 失败
    """
    # The CLI is an explicit fallback; never compete with an open Editor.
    if (unity_project / "Temp" / "UnityLockfile").exists():
        print("[unity_cli] 工程存在 UnityLockfile；优先使用已连接的 MCP，不启动第二个 Unity 实例", file=sys.stderr)
        return 1
    output = PurePosixPath(prefab_path.replace("\\", "/"))
    if (output.is_absolute() or not output.parts or output.parts[0] != "Assets"
            or ".." in output.parts or output.suffix.lower() != ".prefab"):
        print("[unity_cli] Prefab 路径必须是 Assets/ 内的 .prefab 相对路径", file=sys.stderr)
        return 1
    valid, errors = validate_layout_json(json_path)
    if not valid:
        print("[unity_cli] Layout JSON 无效: " + "; ".join(errors), file=sys.stderr)
        return 1

    # 优先使用环境变量指定的 Unity 路径，否则自动推断
    if os.getenv("UNITY_EXECUTABLE"):
        unity_exe = Path(os.getenv("UNITY_EXECUTABLE"))
        if not unity_exe.exists():
            print(
                f"[unity_cli] ❌ 环境变量 UNITY_EXECUTABLE 指向的文件不存在: {unity_exe}",
                file=sys.stderr,
            )
            return 1
    else:
        try:
            unity_exe = find_unity_executable(unity_project)
        except (FileNotFoundError, ValueError) as e:
            print(f"[unity_cli] ❌ {e}", file=sys.stderr)
            return 1

    # 设置环境变量（传递给 Unity 进程）
    env = os.environ.copy()
    env["LR_LAYOUT_JSON"] = str(json_path.resolve())
    env["LR_PREFAB_PATH"] = prefab_path
    if script_type:
        env["LR_SCRIPT_TYPE"] = script_type
    else:
        env.pop("LR_SCRIPT_TYPE", None)

    # 构建命令行
    cmd = [
        str(unity_exe),
        "-quit",  # 执行完毕后退出
        "-batchmode",  # 批处理模式（无 GUI）
        "-projectPath",
        str(unity_project.resolve()),
        "-logFile",
        "-",  # 日志输出到 stdout
        "-executeMethod",
        "LRUIPrefabGen.LRUnityLayoutCLI.GenerateFromEnv",
    ]

    print(f"[unity_cli] 调用 Unity 生成器", file=sys.stderr)
    print(f"[unity_cli]   Unity: {unity_exe}", file=sys.stderr)
    print(f"[unity_cli]   项目: {unity_project}", file=sys.stderr)
    print(f"[unity_cli]   JSON: {json_path.name}", file=sys.stderr)
    print(f"[unity_cli]   Prefab: {prefab_path}", file=sys.stderr)
    print(f"[unity_cli]   脚本: {script_type or '(无)'}", file=sys.stderr)
    print(f"[unity_cli]   超时: {timeout}s", file=sys.stderr)
    print(f"[unity_cli] ----------------------------------------", file=sys.stderr)

    try:
        # 执行 Unity（捕获输出）
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )

        # 打印 Unity 日志（stdout）
        if result.stdout:
            print(result.stdout)

        # 打印 Unity 错误（stderr，Unity 有时会把正常日志也输出到 stderr）
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        # 检查退出码
        if result.returncode == 0:
            print(f"[unity_cli] ✅ 生成成功", file=sys.stderr)
        else:
            print(f"[unity_cli] ❌ Unity 退出码: {result.returncode}", file=sys.stderr)

        return result.returncode

    except subprocess.TimeoutExpired:
        print(f"[unity_cli] ❌ 超时（{timeout}s）", file=sys.stderr)
        return 124
    except Exception as e:
        print(f"[unity_cli] ❌ 调用失败: {e}", file=sys.stderr)
        return 1


def main() -> int:
    if len(sys.argv) < 4:
        print(
            "用法: python unity_cli_wrapper.py <unity-project> <json-path> <prefab-path> [script-type]",
            file=sys.stderr,
        )
        print(
            "\n示例:",
            file=sys.stderr,
        )
        print(
            "  python unity_cli_wrapper.py \\",
            file=sys.stderr,
        )
        print(
            "    ../develop/client/project \\",
            file=sys.stderr,
        )
        print(
            "    changes/growth-fund/demo/unity/GrowthFundPage.json \\",
            file=sys.stderr,
        )
        print(
            "    Assets/Resources/PanelUI/GrowthFundPanel.prefab \\",
            file=sys.stderr,
        )
        print(
            "    LR.GrowthFundPage",
            file=sys.stderr,
        )
        return 1

    unity_project = Path(sys.argv[1])
    json_path = Path(sys.argv[2])
    prefab_path = sys.argv[3]
    script_type = sys.argv[4] if len(sys.argv) > 4 else None

    # 验证参数
    if not unity_project.is_dir():
        print(f"[unity_cli] ❌ Unity 项目目录不存在: {unity_project}", file=sys.stderr)
        return 1

    if not json_path.exists():
        print(f"[unity_cli] ❌ JSON 文件不存在: {json_path}", file=sys.stderr)
        return 1

    # 读取超时设置
    timeout = int(os.getenv("LR_UNITY_TIMEOUT", "300"))

    # 调用生成器
    return generate_prefab(unity_project, json_path, prefab_path, script_type, timeout)


if __name__ == "__main__":
    raise SystemExit(main())
