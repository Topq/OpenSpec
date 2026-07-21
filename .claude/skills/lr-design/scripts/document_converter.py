#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""飞书文档块与Markdown格式互转"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class DocumentMetadata:
    """文档元信息"""
    document_id: str
    revision_id: int
    title: str


class DocumentConverter:
    """文档格式转换器"""

    def __init__(self):
        self.image_mapping: Dict[str, str] = {}  # file_token -> local_path
        self.sheet_mapping: Dict[str, List[List]] = {}  # sheet_token -> rows

    def blocks_to_markdown(
        self,
        blocks: List[Dict],
        metadata: DocumentMetadata,
        image_dir: Optional[Path] = None
    ) -> str:
        """
        将飞书文档块转换为Markdown

        Args:
            blocks: 飞书文档块列表
            metadata: 文档元信息
            image_dir: 图片目录（用于生成相对路径）

        Returns:
            Markdown字符串
        """
        lines = []

        # Frontmatter
        lines.append("---")
        lines.append(f"document_id: {metadata.document_id}")
        lines.append(f"revision_id: {metadata.revision_id}")
        lines.append(f"title: {metadata.title}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {metadata.title}")
        lines.append("")

        # 构建块ID到块的映射
        block_map = {block["block_id"]: block for block in blocks}

        # 找到根块：只取 parent_id 为空的块（即 page 块本身）
        # 其余块通过递归遍历 children 处理，不放入顶层循环，否则会重复输出
        root_blocks = [b for b in blocks if not b.get("parent_id")]

        # 递归转换
        for block in root_blocks:
            self._convert_block_recursive(block, block_map, lines, level=0, image_dir=image_dir)

        return "\n".join(lines)

    def _convert_block_recursive(
        self,
        block: Dict,
        block_map: Dict[str, Dict],
        lines: List[str],
        level: int,
        image_dir: Optional[Path]
    ):
        """递归转换块"""
        # 飞书API返回的块包含数字类型和对应的字段名
        # 通过检查字段名来判断块类型
        block_type = None
        for key in block.keys():
            if key not in ['block_id', 'block_type', 'parent_id', 'children']:
                block_type = key
                break

        if not block_type:
            # 没有内容字段，可能是空块
            pass

        elif block_type == "page":
            # 跳过page块，直接处理子块
            pass

        elif block_type == "heading1":
            text = self._extract_text(block, block_type)
            lines.append(f"# {text}")
            lines.append("")

        elif block_type == "heading2":
            text = self._extract_text(block, block_type)
            lines.append(f"## {text}")
            lines.append("")

        elif block_type == "heading3":
            text = self._extract_text(block, block_type)
            lines.append(f"### {text}")
            lines.append("")

        elif block_type == "heading4":
            text = self._extract_text(block, block_type)
            lines.append(f"#### {text}")
            lines.append("")

        elif block_type == "heading5":
            text = self._extract_text(block, block_type)
            lines.append(f"##### {text}")
            lines.append("")

        elif block_type == "text":
            text = self._extract_text(block, block_type)
            if text.strip():
                lines.append(text)
                lines.append("")

        elif block_type == "bullet":
            text = self._extract_text(block, block_type)
            indent = "  " * level
            lines.append(f"{indent}- {text}")

        elif block_type == "ordered":
            text = self._extract_text(block, block_type)
            indent = "  " * level
            lines.append(f"{indent}1. {text}")

        elif block_type == "table":
            self._convert_table(block, block_map, lines)
            return  # table的子块由_convert_table内部处理，不再递归

        elif block_type == "table_cell":
            return  # table_cell由_convert_table处理，跳过自身及子块

        elif block_type == "image":
            self._convert_image(block, lines, image_dir)

        elif block_type == "sheet":
            self._convert_sheet(block, lines)

        elif block_type == "code":
            self._convert_code(block, block_type, lines)

        elif block_type == "quote":
            text = self._extract_text(block, block_type)
            lines.append(f"> {text}")
            lines.append("")

        elif block_type == "divider":
            lines.append("---")
            lines.append("")

        # 处理子块
        children = block.get("children", [])
        for child_id in children:
            if child_id in block_map:
                child_block = block_map[child_id]
                next_level = level + 1 if block_type in ["bullet", "ordered"] else level
                self._convert_block_recursive(child_block, block_map, lines, next_level, image_dir)

    def _extract_text(self, block: Dict, block_type: str) -> str:
        """提取块的文本内容"""
        content = block.get(block_type, {})

        # 处理富文本元素
        elements = content.get("elements", [])
        if not elements:
            return ""

        text_parts = []
        for elem in elements:
            text_run = elem.get("text_run", {})
            text = text_run.get("content", "")

            # 应用样式
            style = text_run.get("text_element_style", {})
            if style.get("bold"):
                text = f"**{text}**"
            if style.get("italic"):
                text = f"*{text}*"
            if style.get("strikethrough"):
                text = f"~~{text}~~"
            if style.get("inline_code"):
                text = f"`{text}`"

            # 处理链接
            link = text_run.get("link", {})
            if link.get("url"):
                text = f"[{text}]({link['url']})"

            text_parts.append(text)

        return "".join(text_parts)

    def _convert_table(self, block: Dict, block_map: Dict[str, Dict], lines: List[str]):
        """转换表格：从table.property获取列数，从cell子块提取实际文本"""
        table = block.get("table", {})
        prop = table.get("property", {})
        column_size = prop.get("column_size", 0)

        # cells 字段直接列出所有单元格的 block_id（行优先排列）
        cell_ids = table.get("cells", [])
        if not cell_ids:
            return

        if column_size == 0:
            column_size = max(1, len(cell_ids))

        # 每个 cell 的文本从其子块递归提取
        cells_text = [self._extract_cell_text(cid, block_map) for cid in cell_ids]

        # 按列数切分成行
        rows = [cells_text[i:i + column_size] for i in range(0, len(cells_text), column_size)]

        if not rows:
            return

        # 第一行作为表头（prop.header_row == true 时）
        header = rows[0]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        for row in rows[1:]:
            # 补齐不足列
            while len(row) < column_size:
                row.append("")
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    def _extract_cell_text(self, cell_id: str, block_map: Dict[str, Dict]) -> str:
        """递归提取 table_cell 子块中的所有文本，拼接成单个字符串"""
        cell_block = block_map.get(cell_id)
        if not cell_block:
            return ""

        parts = []
        for child_id in cell_block.get("children", []):
            child = block_map.get(child_id)
            if not child:
                continue
            # 找内容字段（非系统字段的第一个 key）
            for key in child.keys():
                if key not in ("block_id", "block_type", "parent_id", "children"):
                    text = self._extract_text(child, key)
                    if text.strip():
                        parts.append(text)
                    break
        return " ".join(parts)

    def _convert_image(self, block: Dict, lines: List[str], image_dir: Optional[Path]):
        """转换图片"""
        image = block.get("image", {})
        file_token = image.get("token", "")

        # 查找本地路径
        local_path = self.image_mapping.get(file_token)

        if local_path and image_dir:
            # 生成相对路径
            try:
                rel_path = Path(local_path).relative_to(image_dir.parent)
                lines.append(f"![图片]({rel_path.as_posix()})")
            except ValueError:
                lines.append(f"![图片](images/{file_token}.png)")
        else:
            lines.append(f"![图片](images/{file_token}.png)")

        lines.append("")

    def _convert_sheet(self, block: Dict, lines: List[str]):
        """转换嵌入的电子表格"""
        sheet = block.get("sheet", {})
        sheet_token = sheet.get("token", "")

        # 从缓存中查找sheet数据
        rows = self.sheet_mapping.get(sheet_token, [])

        if not rows:
            lines.append(f"> **注意**: 此处嵌入了外部电子表格 (token: {sheet_token[:20]}...)，")
            lines.append(f"> 内容无法自动导出。请查看原飞书文档或联系策划提供配表详情。")
            lines.append("")
            return

        # 转换为Markdown表格
        if len(rows) > 0:
            # 第一行作为表头
            header = rows[0]
            lines.append("| " + " | ".join(str(cell) for cell in header) + " |")
            lines.append("| " + " | ".join(["---"] * len(header)) + " |")

            # 后续行作为数据
            for row in rows[1:]:
                # 补齐列数
                while len(row) < len(header):
                    row.append("")
                lines.append("| " + " | ".join(str(cell) for cell in row) + " |")

        lines.append("")

    def _convert_code(self, block: Dict, block_type: str, lines: List[str]):
        """转换代码块"""
        code = block.get("code", {})
        language = code.get("language", "")
        content = self._extract_text(block, block_type)

        lines.append(f"```{language}")
        lines.append(content)
        lines.append("```")
        lines.append("")

    def markdown_to_blocks(self, markdown: str, metadata: DocumentMetadata) -> List[Dict]:
        """
        将Markdown转换为飞书文档块

        这是一个简化实现，主要用于更新文档
        """
        blocks = []
        lines = markdown.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i]

            # 跳过frontmatter（首行为 --- 时，跳到下一个 --- 之后）
            if i == 0 and line.strip() == "---":
                i += 1  # 先跳过起始的 ---
                while i < len(lines) and lines[i].strip() != "---":
                    i += 1
                i += 1  # 跳过结束的 ---
                continue

            # 标题
            if line.startswith("# "):
                # 跳过文档标题
                i += 1
                continue
            elif line.startswith("## "):
                blocks.append(self._create_heading_block(1, line[3:].strip()))
            elif line.startswith("### "):
                blocks.append(self._create_heading_block(2, line[4:].strip()))
            elif line.startswith("#### "):
                blocks.append(self._create_heading_block(3, line[5:].strip()))
            elif line.startswith("##### "):
                blocks.append(self._create_heading_block(4, line[6:].strip()))
            elif line.startswith("###### "):
                blocks.append(self._create_heading_block(5, line[7:].strip()))

            # 列表
            elif line.strip().startswith("- "):
                blocks.append(self._create_bullet_block(line.strip()[2:]))

            elif line.strip().startswith("1. "):
                blocks.append(self._create_ordered_block(line.strip()[3:]))

            # 代码块
            elif line.strip().startswith("```"):
                language = line.strip()[3:].strip()
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                blocks.append(self._create_code_block("\n".join(code_lines), language))

            # 表格（连续的 | 开头行）
            elif line.strip().startswith("|"):
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i].strip())
                    i += 1
                blocks.extend(self._create_table_blocks(table_lines))
                continue  # i 已前进，不再 +1

            # 分隔线
            elif line.strip() == "---":
                blocks.append(self._create_divider_block())

            # 普通文本
            elif line.strip():
                blocks.append(self._create_text_block(line.strip()))

            i += 1

        return blocks

    def _create_table_blocks(self, table_lines: List[str]) -> List[Dict]:
        """
        将Markdown表格行转换为飞书table块结构
        返回 [table块, cell块1, cell块2, ...]，通过children关联
        """
        # 解析每行的单元格（去掉首尾的 |，按 | 分割）
        rows = []
        for line in table_lines:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.append(cells)

        # 过滤掉分隔行（| --- | --- |）
        data_rows = [r for r in rows if not all(set(c) <= set("-: ") and c for c in r)]
        if not data_rows:
            return []

        column_size = max(len(r) for r in data_rows)
        row_size = len(data_rows)

        # 生成 cell 块（每个 cell 内含一个 text 子块）
        cell_blocks = []
        cell_ids = []
        for r_idx, row in enumerate(data_rows):
            for c_idx in range(column_size):
                content = row[c_idx] if c_idx < len(row) else ""
                cell_id = f"tmp_cell_{r_idx}_{c_idx}"
                text_id = f"tmp_text_{r_idx}_{c_idx}"
                cell_ids.append(cell_id)
                # cell 块
                cell_blocks.append({
                    "block_id": cell_id,
                    "block_type": "table_cell",
                    "table_cell": {},
                    "children": [text_id],
                })
                # cell 内的 text 块
                cell_blocks.append({
                    "block_id": text_id,
                    "block_type": "text",
                    "text": {
                        "elements": [{"text_run": {"content": content}}],
                        "style": {}
                    },
                    "parent_id": cell_id,
                })

        # table 块（block_type=31），cell 块（block_type=32）
        table_block = {
            "block_type": 31,
            "table": {
                "cells": cell_ids,
                "property": {
                    "row_size": row_size,
                    "column_size": column_size,
                    "header_row": True,
                }
            },
            "children": cell_ids,
        }
        # 更新cell和text块的block_type为数字
        for cb in cell_blocks:
            if "table_cell" in cb:
                cb["block_type"] = 32
            elif "text" in cb:
                cb["block_type"] = 2

        return [table_block] + cell_blocks

    def _create_heading_block(self, level: int, text: str) -> Dict:
        """创建标题块（飞书 heading1=3, heading2=4, ... heading9=11）"""
        block_type_num = level + 2  # heading1→3, heading2→4, ...
        block_type_name = f"heading{level}"
        return {
            "block_type": block_type_num,
            block_type_name: {
                "elements": [{"text_run": {"content": text}}],
                "style": {}
            }
        }

    def _create_text_block(self, text: str) -> Dict:
        """创建文本块（block_type=2）"""
        return {
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {"content": text}}],
                "style": {}
            }
        }

    def _create_bullet_block(self, text: str) -> Dict:
        """创建无序列表块（block_type=12）"""
        return {
            "block_type": 12,
            "bullet": {
                "elements": [{"text_run": {"content": text}}],
                "style": {}
            }
        }

    def _create_ordered_block(self, text: str) -> Dict:
        """创建有序列表块（block_type=13）"""
        return {
            "block_type": 13,
            "ordered": {
                "elements": [{"text_run": {"content": text}}],
                "style": {}
            }
        }

    def _create_code_block(self, code: str, language: str = "") -> Dict:
        """创建代码块（block_type=14）"""
        return {
            "block_type": 14,
            "code": {
                "language": language,
                "elements": [{"text_run": {"content": code}}]
            }
        }

    def _create_divider_block(self) -> Dict:
        """创建分隔线块（block_type=22）"""
        return {
            "block_type": 22,
            "divider": {}
        }


def main():
    """测试入口"""
    import argparse

    parser = argparse.ArgumentParser(description="文档格式转换工具")
    parser.add_argument("command", choices=["to-md", "to-blocks"], help="转换方向")
    parser.add_argument("--input", type=Path, required=True, help="输入文件")
    parser.add_argument("--output", type=Path, required=True, help="输出文件")
    parser.add_argument("--title", default="文档", help="文档标题")
    parser.add_argument("--document-id", default="", help="文档ID")
    parser.add_argument("--revision-id", type=int, default=0, help="修订ID")

    args = parser.parse_args()

    converter = DocumentConverter()
    metadata = DocumentMetadata(
        document_id=args.document_id,
        revision_id=args.revision_id,
        title=args.title
    )

    if args.command == "to-md":
        with open(args.input, "r", encoding="utf-8") as f:
            blocks = json.load(f)

        markdown = converter.blocks_to_markdown(blocks, metadata)

        with open(args.output, "w", encoding="utf-8") as f:
            f.write(markdown)

        print(f"已转换为Markdown: {args.output}")

    elif args.command == "to-blocks":
        with open(args.input, "r", encoding="utf-8") as f:
            markdown = f.read()

        blocks = converter.markdown_to_blocks(markdown, metadata)

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(blocks, f, ensure_ascii=False, indent=2)

        print(f"已转换为文档块: {args.output}")


if __name__ == "__main__":
    main()
