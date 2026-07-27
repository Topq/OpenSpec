#!/usr/bin/env python3
"""Remove the deployed Assets/Editor/LRUIPrefabGen/ directory from the Unity
project after prefab generation is verified (SKILL step 7).

This only deletes the deployed copy; the source of truth in this skill's
scripts/lr_ui_gen/ directory is untouched. Safe to call even if the target
directory does not exist (e.g. already cleaned up, or deploy never ran).

After running this script, the caller should trigger an AssetDatabase
refresh (mcp__ai-game-developer__assets-refresh) so Unity notices the
deletion and recompiles without the generator types.

Usage:
  python cleanup_lr_ui_gen.py <unity-project-root>

Example:
  python cleanup_lr_ui_gen.py D:/se/develop/client/project
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

TARGET_SUBPATH = Path("Assets/Editor/LRUIPrefabGen")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python cleanup_lr_ui_gen.py <unity-project-root>", file=sys.stderr)
        return 1

    project_root = Path(sys.argv[1]).resolve()
    target_dir = project_root / TARGET_SUBPATH

    if not target_dir.exists():
        print(f"目标目录不存在，无需清理: {target_dir}")
        return 0

    shutil.rmtree(target_dir)
    meta_file = target_dir.with_suffix(".meta")
    if meta_file.exists():
        meta_file.unlink()

    print(f"已删除: {target_dir}")
    print("下一步：调用 assets-refresh 让 Unity 感知删除并重新编译。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
