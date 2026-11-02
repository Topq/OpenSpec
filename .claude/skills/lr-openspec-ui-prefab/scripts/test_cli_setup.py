#!/usr/bin/env python3
"""测试 Unity CLI 包装脚本的基本功能（不实际调用 Unity）。

验证：
1. unity_cli_wrapper.py 可以导入和执行
2. 能正确解析 ProjectVersion.txt
3. 能正确推断 Unity 可执行文件路径（如果存在）
4. 参数验证逻辑正常工作

Usage:
  python test_cli_setup.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# 添加脚本目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent))

from unity_cli_wrapper import find_unity_executable


def test_parse_project_version():
    """测试解析 ProjectVersion.txt"""
    print("测试 1: 解析 ProjectVersion.txt")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        project_settings = project_root / "ProjectSettings"
        project_settings.mkdir()

        version_file = project_settings / "ProjectVersion.txt"
        version_file.write_text("m_EditorVersion: 2022.3.62f2\n", encoding="utf-8")

        try:
            unity_exe = find_unity_executable(project_root)
            print(f"  ✅ 推断路径: {unity_exe}")
            print(f"  ⚠️  路径存在: {unity_exe.exists()}")
        except FileNotFoundError as e:
            print(f"  ⚠️  推断路径不存在（正常，除非你有该版本 Unity）: {e}")
        except Exception as e:
            print(f"  ❌ 解析失败: {e}")
            return False

    print()
    return True


def test_invalid_project():
    """测试无效项目目录"""
    print("测试 2: 无效项目目录")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)

        try:
            find_unity_executable(project_root)
            print("  ❌ 应该抛出 FileNotFoundError")
            return False
        except FileNotFoundError:
            print("  ✅ 正确抛出 FileNotFoundError")
        except Exception as e:
            print(f"  ❌ 抛出了错误的异常: {e}")
            return False

    print()
    return True


def test_invalid_version_file():
    """测试无效的 ProjectVersion.txt"""
    print("测试 3: 无效的 ProjectVersion.txt")

    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        project_settings = project_root / "ProjectSettings"
        project_settings.mkdir()

        version_file = project_settings / "ProjectVersion.txt"
        version_file.write_text("invalid content\n", encoding="utf-8")

        try:
            find_unity_executable(project_root)
            print("  ❌ 应该抛出 ValueError")
            return False
        except ValueError:
            print("  ✅ 正确抛出 ValueError")
        except Exception as e:
            print(f"  ❌ 抛出了错误的异常: {e}")
            return False

    print()
    return True


def main() -> int:
    print("=" * 60)
    print("Unity CLI 包装脚本测试")
    print("=" * 60)
    print()

    tests = [
        test_parse_project_version,
        test_invalid_project,
        test_invalid_version_file,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ 测试异常: {e}")
            failed += 1

    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
