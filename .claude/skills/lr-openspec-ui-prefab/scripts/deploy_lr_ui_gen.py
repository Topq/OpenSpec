#!/usr/bin/env python3
"""Deploy lr_ui_gen/ (Unity Editor generator scripts + JSON recipes) into the
client project's Assets/Editor/LRUIPrefabGen/ directory, so
LRUnityLayoutPrefabGenerator can be invoked via MCP reflection-method-call.

Source of truth for this code is this skill's scripts/lr_ui_gen/ directory,
not the Unity project -- do not edit the deployed copy in-place.

Idempotent: if the target directory already exists (e.g. left over from an
interrupted previous run), it is removed and replaced rather than merged.

After running this script, the caller must trigger an AssetDatabase refresh
(mcp__ai-game-developer__assets-refresh) and then poll
mcp__ai-game-developer__editor-application-get-state until IsCompiling is
false before invoking the generator -- this script only touches the
filesystem and cannot wait on Unity's compiler itself.

Usage:
  python deploy_lr_ui_gen.py <unity-project-root>

Example:
  python deploy_lr_ui_gen.py ../develop/client/project
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

SOURCE_DIR = Path(__file__).resolve().parent / "lr_ui_gen"
TARGET_SUBPATH = Path("Assets/Editor/LRUIPrefabGen")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python deploy_lr_ui_gen.py <unity-project-root>", file=sys.stderr)
        return 1

    project_root = Path(sys.argv[1]).resolve()
    if not project_root.is_dir():
        print(f"项目根目录不存在: {project_root}", file=sys.stderr)
        return 1

    if not SOURCE_DIR.is_dir():
        print(f"源码目录不存在: {SOURCE_DIR}", file=sys.stderr)
        return 1

    target_dir = project_root / TARGET_SUBPATH

    if target_dir.exists():
        print(f"目标目录已存在（可能是上次中断残留），先清理: {target_dir}")
        shutil.rmtree(target_dir)

    shutil.copytree(SOURCE_DIR, target_dir)

    deployed = sorted(p.name for p in target_dir.rglob("*") if p.is_file())
    print(f"已部署 {len(deployed)} 个文件: {SOURCE_DIR} -> {target_dir}")
    print("下一步：调用 assets-refresh，再轮询 editor-application-get-state 直到 IsCompiling=false。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
