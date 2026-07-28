#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lr-design 下载工作流:飞书策划案 → 本地 working.md

只负责下载链路(创建会话目录、拉取文档块、下载图片、转换 Markdown)。
本 skill 不回写飞书,因此没有 update 命令。

凭据从 skill 根目录的 config.json 读取(该文件已 gitignore,不入库):
    {"app_id": "...", "app_secret": "...", "session_root": "tmp", "base_url": "..."}
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Windows GBK 控制台下强制 UTF-8 输出
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))

from feishu_api import FeishuAPI, FeishuAPIError
from document_converter import DocumentConverter, DocumentMetadata
from manage_session import clean_all_sessions, create_session

SKILL_ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    """读取 skill 根目录的 config.json"""
    config_file = SKILL_ROOT / "config.json"
    if not config_file.exists():
        raise SystemExit(
            f"错误: 找不到凭据配置 {config_file}\n"
            f"请复制 config.json.example 为 config.json 并填入飞书应用凭据。"
        )
    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)


def download_document(api: FeishuAPI, converter: DocumentConverter,
                      session_root: Path, url: str, session_name: str) -> Path:
    """下载飞书文档到本地会话目录,返回 working.md 路径"""
    print("正在下载策划案...")

    cleaned = clean_all_sessions(session_root)
    if cleaned:
        print(f"已清空 {cleaned} 个历史会话目录，避免跨任务污染")

    session_dir = create_session(session_root, session_name)
    print(f"会话目录: {session_dir}")

    doc_type, token = api.parse_document_url(url)
    docx_id = api.get_docx_from_wiki(token) if doc_type == "wiki" else token

    doc_info = api.get_document_info(docx_id)
    print(f"标题: {doc_info['title']}")

    metadata = DocumentMetadata(
        document_id=doc_info["document_id"],
        revision_id=doc_info["revision_id"],
        title=doc_info["title"],
    )

    with open(session_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump({
            "document_id": metadata.document_id,
            "revision_id": metadata.revision_id,
            "title": metadata.title,
            "downloaded_at": datetime.now().isoformat(),
            "url": url,
        }, f, ensure_ascii=False, indent=2)

    print("正在获取文档内容...")
    blocks = api.get_document_blocks(docx_id)
    print(f"获取到 {len(blocks)} 个文档块")

    # 下载图片
    image_tokens = [
        b["image"]["token"] for b in blocks
        if b.get("block_type") == 27 and b.get("image", {}).get("token")
    ]
    if image_tokens:
        print("正在下载图片...")
        images_dir = session_dir / "images"
        image_mapping = api.download_images(image_tokens, images_dir)
        print(f"下载了 {len(image_mapping)} 张图片")
        converter.image_mapping = {
            token: str(path) for token, path in image_mapping.items()
        }

    # 下载嵌入的电子表格
    sheet_tokens = [
        b["sheet"]["token"] for b in blocks
        if b.get("block_type") == 30 and b.get("sheet", {}).get("token")
    ]
    if sheet_tokens:
        print(f"发现 {len(sheet_tokens)} 个嵌入的电子表格，尝试获取内容...")
        for sheet_token in sheet_tokens:
            try:
                sheet_data = api.get_sheet_content(sheet_token)
                if sheet_data.get("rows"):
                    converter.sheet_mapping[sheet_token] = sheet_data["rows"]
            except Exception:
                # 静默跳过无法获取的sheet
                pass
        if converter.sheet_mapping:
            print(f"成功获取了 {len(converter.sheet_mapping)} 个电子表格的内容")
        else:
            print("电子表格内容无法自动导出（可能需要额外权限），将在文档中标注")

    print("正在转换为Markdown...")
    markdown = converter.blocks_to_markdown(blocks, metadata, session_dir / "images")

    working_md = session_dir / "working.md"
    working_md.write_text(markdown, encoding="utf-8")

    with open(session_dir / "blocks.json", "w", encoding="utf-8") as f:
        json.dump(blocks, f, ensure_ascii=False, indent=2)

    print("文档已下载到本地")
    print(f"工作文件: {working_md}")
    return working_md


def main() -> int:
    parser = argparse.ArgumentParser(description="lr-design 下载工作流")
    parser.add_argument("--url", required=True, help="飞书文档URL(wiki或docx)")
    parser.add_argument("--name", default="design", help="会话名称")
    args = parser.parse_args()

    config = load_config()
    session_root = SKILL_ROOT / config.get("session_root", "tmp")

    api = FeishuAPI(
        config["app_id"], config["app_secret"],
        base_url=config.get("base_url", "https://open.feishu.cn"),
    )

    try:
        download_document(api, DocumentConverter(), session_root, args.url, args.name)
    except FeishuAPIError as e:
        print(f"飞书API错误: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
