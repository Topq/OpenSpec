#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lr-feishu 工作流：飞书文档 → 分章整理后的 Markdown。

用法:
  python scripts/workflow.py --url <飞书链接> --out <输出目录>
  python scripts/workflow.py --input <本地.md> --out <输出目录> [--images <图片目录>]

复用 lr-design 的 feishu_api / document_converter，避免复制第三份飞书链路。
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = SKILL_ROOT.parent
LR_DESIGN_SCRIPTS = SKILLS_DIR / "lr-design" / "scripts"

if not LR_DESIGN_SCRIPTS.exists():
    raise SystemExit(
        f"找不到 lr-design 的 scripts 目录: {LR_DESIGN_SCRIPTS}\n"
        "本 skill 复用 lr-design 的飞书下载与 Markdown 转换代码。"
    )

sys.path.insert(0, str(LR_DESIGN_SCRIPTS))
sys.path.insert(0, str(Path(__file__).parent))

from feishu_api import FeishuAPI
from document_converter import DocumentConverter, DocumentMetadata

from organize import organize_document


def load_config() -> dict:
    """优先读本 skill 的 config.json，其次复用 lr-design 的。"""
    candidates = [
        SKILL_ROOT / "config.json",
        SKILLS_DIR / "lr-design" / "config.json",
    ]
    for path in candidates:
        if path.exists():
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
    raise SystemExit(
        "找不到飞书凭据。请创建 lr-feishu/config.json，或确保 lr-design/config.json 存在。"
    )


def download(url: str, out_dir: Path) -> tuple[str, str]:
    config = load_config()
    api = FeishuAPI(
        config["app_id"],
        config["app_secret"],
        base_url=config.get("base_url", "https://open.feishu.cn"),
    )

    doc_type, token = api.parse_document_url(url)
    docx_id = api.get_docx_from_wiki(token) if doc_type == "wiki" else token
    info = api.get_document_info(docx_id)
    print(f"文档: {info['title']} (revision {info['revision_id']})")

    blocks = api.get_document_blocks(docx_id)
    print(f"文档块: {len(blocks)}")

    images_dir = out_dir / "images"
    converter = DocumentConverter()

    image_tokens = [
        block["image"]["token"]
        for block in blocks
        if block.get("block_type") == 27 and block.get("image", {}).get("token")
    ]
    if image_tokens:
        print(f"下载图片: {len(image_tokens)} 张")
        mapping = api.download_images(image_tokens, images_dir)
        converter.image_mapping = {token: str(path) for token, path in mapping.items()}

    sheet_tokens = [
        block["sheet"]["token"]
        for block in blocks
        if block.get("block_type") == 30 and block.get("sheet", {}).get("token")
    ]
    for sheet_token in sheet_tokens:
        try:
            sheet_data = api.get_sheet_content(sheet_token)
            if sheet_data.get("rows"):
                converter.sheet_mapping[sheet_token] = sheet_data["rows"]
        except Exception as exc:  # noqa: BLE001
            print(f"表格 {sheet_token} 获取失败: {exc}")

    metadata = DocumentMetadata(
        document_id=info["document_id"],
        revision_id=info["revision_id"],
        title=info["title"],
    )
    markdown = converter.blocks_to_markdown(blocks, metadata, images_dir)
    return markdown, str(images_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="飞书策划案整理")
    parser.add_argument("--url", help="飞书 wiki / docx 链接")
    parser.add_argument("--input", type=Path, help="本地 Markdown（跳过下载）")
    parser.add_argument("--images", type=Path, help="本地 Markdown 的图片目录")
    parser.add_argument("--out", type=Path, required=True, help="输出目录")
    args = parser.parse_args()

    out_dir = args.out.resolve()

    if args.url and args.input:
        parser.error("--url 与 --input 只能给一个")

    if args.url:
        out_dir.mkdir(parents=True, exist_ok=True)
        markdown, images_dir = download(args.url, out_dir)
        source = args.url
        source_images = Path(images_dir)
    elif args.input:
        markdown = args.input.read_text(encoding="utf-8")
        source = str(args.input)
        source_images = args.images or (args.input.parent / "images")
    else:
        parser.error("需要 --url 或 --input")

    written = organize_document(markdown, out_dir, source_images, source)
    print(f"\n已整理到: {out_dir}")
    for filename in written:
        print(f"  - {filename}")
    print("  - README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
