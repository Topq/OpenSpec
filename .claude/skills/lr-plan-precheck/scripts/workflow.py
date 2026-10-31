#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lr-plan-precheck 下载工作流:飞书策划案 → 本技能目录下的 tmp/(用后即弃)

与 lr-design/scripts/workflow.py 的区别:
- 不创建 changes/ 下任何会话目录,不维护多会话历史
- 下载到本技能目录下的 tmp/ 文件夹(与 lr-design 一致的模式);每次下载前先清空
  tmp/ 现有内容,避免跨任务残留污染本次判定。tmp/ 已加入 .gitignore,不会被提交。
- 提供 cleanup 子命令,供同一次对话内需要提前释放时手动调用(非必须步骤)
- 不做美术章节过滤(precheck 需要看到完整原文以判断"参考图是否提供"等项)

凭据从本 skill 根目录的 config.json 读取,格式与 lr-design 相同:
    {"app_id": "...", "app_secret": "...", "session_root": "tmp", "base_url": "..."}
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

# Windows GBK 控制台下强制 UTF-8 输出
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))

from feishu_api import FeishuAPI, FeishuAPIError
from document_converter import DocumentConverter, DocumentMetadata
from filter_art_sections import filter_art_sections

SKILL_ROOT = Path(__file__).resolve().parents[1]
MARKER_NAME = "LR_PRECHECK_TMP"


def clear_tmp_root(tmp_root: Path) -> int:
    """清空 tmp_root 下所有历史内容(避免跨任务污染),返回删除的条目数"""
    if not tmp_root.exists():
        return 0
    removed = 0
    for item in tmp_root.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
        removed += 1
    return removed


def load_config() -> dict:
    """读取 skill 根目录的 config.json"""
    config_file = SKILL_ROOT / "config.json"
    if not config_file.exists():
        raise SystemExit(
            f"错误: 找不到凭据配置 {config_file}\n"
            f"请复制 config.json.example 为 config.json 并填入飞书应用凭据。\n"
            f"(与 lr-design 用同一份飞书应用凭据即可,两个 skill 各自维护一份 config.json)"
        )
    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)


def download_document(api: FeishuAPI, converter: DocumentConverter, tmp_root: Path, url: str) -> Path:
    """下载飞书文档到本技能 tmp/ 下,返回该目录路径(内含 working.md 和 images/)

    下载前先清空 tmp_root 下所有历史内容,避免跨任务污染。
    """
    print("正在下载策划案(本地临时读取,不进入 changes/)...")

    cleared = clear_tmp_root(tmp_root)
    if cleared:
        print(f"已清空 {cleared} 项历史临时内容")

    tmp_dir = tmp_root / "session"
    tmp_dir.mkdir(parents=True)
    (tmp_dir / MARKER_NAME).touch()  # 标记文件,供 cleanup 子命令校验安全性
    images_dir = tmp_dir / "images"

    doc_type, token = api.parse_document_url(url)
    docx_id = api.get_docx_from_wiki(token) if doc_type == "wiki" else token

    doc_info = api.get_document_info(docx_id)
    print(f"标题: {doc_info['title']}")

    metadata = DocumentMetadata(
        document_id=doc_info["document_id"],
        revision_id=doc_info["revision_id"],
        title=doc_info["title"],
    )

    print("正在获取文档内容...")
    blocks = api.get_document_blocks(docx_id)
    print(f"获取到 {len(blocks)} 个文档块")

    image_tokens = [
        b["image"]["token"] for b in blocks
        if b.get("block_type") == 27 and b.get("image", {}).get("token")
    ]
    if image_tokens:
        print("正在下载图片...")
        image_mapping = api.download_images(image_tokens, images_dir)
        print(f"下载了 {len(image_mapping)} 张图片")
        converter.image_mapping = {
            token: str(path) for token, path in image_mapping.items()
        }

    sheet_tokens = [
        b["sheet"]["token"] for b in blocks
        if b.get("block_type") == 30 and b.get("sheet", {}).get("token")
    ]
    if sheet_tokens:
        print(f"发现 {len(sheet_tokens)} 个嵌入的电子表格,尝试获取内容...")
        for sheet_token in sheet_tokens:
            try:
                sheet_data = api.get_sheet_content(sheet_token)
                if sheet_data.get("rows"):
                    converter.sheet_mapping[sheet_token] = sheet_data["rows"]
            except Exception:
                pass

    print("正在转换为Markdown...")
    markdown = converter.blocks_to_markdown(blocks, metadata, images_dir)

    # 过滤美术需求章节,与 lr-design 判定范围保持一致(生产美术不算完整性阻断项)
    filtered_markdown, removed_sections = filter_art_sections(markdown)
    if removed_sections:
        markdown = filtered_markdown
        print(f"已过滤 {len(removed_sections)} 个美术需求章节:")
        for section in removed_sections:
            print(f"  - {section}")

    working_md = tmp_dir / "working.md"
    working_md.write_text(markdown, encoding="utf-8")

    print("文档已下载到临时目录(本次分析结束后会自动清理)")
    print(f"临时目录: {tmp_dir}")
    return tmp_dir


def cleanup(tmp_root: Path, tmp_dir: Path) -> None:
    """安全删除本次下载产生的临时目录(必须在 tmp_root 内且带 MARKER_NAME 标记才会删)"""
    tmp_root = tmp_root.expanduser().resolve()
    tmp_dir = tmp_dir.expanduser().resolve(strict=True)
    try:
        tmp_dir.relative_to(tmp_root)
    except ValueError:
        raise ValueError(f"拒绝清理 tmp/ 之外的路径: {tmp_dir}")
    marker = tmp_dir / MARKER_NAME
    if not marker.is_file():
        raise ValueError(f"拒绝清理未标记的目录: {tmp_dir}")
    shutil.rmtree(tmp_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="lr-plan-precheck 下载工作流")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="下载飞书文档到本技能 tmp/ 目录(先清空历史内容)")
    fetch_parser.add_argument("--url", required=True, help="飞书文档URL(wiki或docx)")

    cleanup_parser = subparsers.add_parser("cleanup", help="清理指定的临时目录(可选,非必须步骤)")
    cleanup_parser.add_argument("tmp_dir", type=Path, help="fetch 命令返回的临时目录路径")

    args = parser.parse_args()

    if args.command == "fetch":
        config = load_config()
        tmp_root = SKILL_ROOT / config.get("session_root", "tmp")
        api = FeishuAPI(
            config["app_id"], config["app_secret"],
            base_url=config.get("base_url", "https://open.feishu.cn"),
        )
        try:
            tmp_dir = download_document(api, DocumentConverter(), tmp_root, args.url)
        except FeishuAPIError as e:
            print(f"飞书API错误: {e}", file=sys.stderr)
            return 1
        print(f"WORKING_MD={tmp_dir / 'working.md'}")
        return 0

    elif args.command == "cleanup":
        config = load_config()
        tmp_root = SKILL_ROOT / config.get("session_root", "tmp")
        try:
            cleanup(tmp_root, args.tmp_dir)
            print(f"已清理: {args.tmp_dir}")
        except (OSError, ValueError) as error:
            print(f"错误: {error}", file=sys.stderr)
            return 1
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
