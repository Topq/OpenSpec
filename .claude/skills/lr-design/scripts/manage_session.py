#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""会话管理 - 创建和清理临时工作区"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path
from datetime import datetime


MARKER_NAME = "LR_DESIGN_SESSION"


def safe_name(value: str) -> str:
    """生成安全的目录名"""
    normalized = re.sub(r"[^0-9A-Za-z_-]+", "-", value.strip()).strip("-")
    return normalized[:48] or "design"


def create_session(root: Path, name: str) -> Path:
    """
    创建临时会话目录

    结构:
        session-{name}-{timestamp}/
            LR_DESIGN_SESSION/  (标记文件)
            source.md           (首次下载的文档)
            working.md          (工作副本)
            images/             (下载的图片)
            demo.zip            (打包的Demo)
            metadata.json       (会话元信息)
    """
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    session_name = f"session-{safe_name(name)}-{timestamp}"
    session = root / session_name
    session.mkdir()

    # 创建标记
    (session / MARKER_NAME).mkdir()

    # 创建子目录
    (session / "images").mkdir()

    return session


def cleanup_session(root: Path, session: Path) -> None:
    """
    安全删除临时会话目录

    检查:
    1. 必须在root目录内
    2. 必须有LR_DESIGN_SESSION标记
    """
    root = root.expanduser().resolve()
    session = session.expanduser().resolve(strict=True)

    # 检查是否在root内
    try:
        session.relative_to(root)
    except ValueError:
        raise ValueError(f"拒绝清理临时根目录之外的路径: {session}")

    # 检查标记
    marker = session / MARKER_NAME
    if not marker.is_dir():
        raise ValueError(f"拒绝清理未标记的目录: {session}")

    # 删除整个会话目录
    shutil.rmtree(session)

    # 尝试删除空的root目录
    try:
        root.rmdir()
    except OSError:
        pass  # 不为空，保留


def list_sessions(root: Path) -> list[Path]:
    """列出所有会话目录"""
    root = root.expanduser().resolve()
    if not root.exists():
        return []

    sessions = []
    for item in root.iterdir():
        if item.is_dir() and (item / MARKER_NAME).is_dir():
            sessions.append(item)

    return sorted(sessions, key=lambda p: p.stat().st_mtime, reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="lr-design会话管理工具")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).parent.parent / "tmp",
        help="临时工作区根目录"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # create命令
    create_parser = subparsers.add_parser("create", help="创建临时会话目录")
    create_parser.add_argument("--name", default="design", help="会话名称")

    # cleanup命令
    cleanup_parser = subparsers.add_parser("cleanup", help="安全删除会话目录")
    cleanup_parser.add_argument("session", type=Path, help="会话目录路径")

    # list命令
    list_parser = subparsers.add_parser("list", help="列出所有会话")

    args = parser.parse_args()

    try:
        if args.command == "create":
            session = create_session(args.root, args.name)
            print(session)

        elif args.command == "cleanup":
            cleanup_session(args.root, args.session)
            print(f"已清理: {args.session}")

        elif args.command == "list":
            sessions = list_sessions(args.root)
            if not sessions:
                print("没有找到会话目录")
            else:
                print(f"找到 {len(sessions)} 个会话:")
                for session in sessions:
                    mtime = datetime.fromtimestamp(session.stat().st_mtime)
                    print(f"  {session.name} (修改于 {mtime.strftime('%Y-%m-%d %H:%M:%S')})")

    except (OSError, ValueError) as error:
        print(f"错误: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
