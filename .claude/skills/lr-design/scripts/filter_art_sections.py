#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""过滤 working.md 中的美术需求章节并清理未引用的图片

识别规则：
- 标题包含"美术需求""美术资源""美术设计"关键词
- 或章节内容主要是对美术团队的素材要求

过滤动作：
- 移除整个章节（标题行 + 内容 + 挂在该标题下的图片引用）
- 在移除位置插入占位符："[已过滤：美术需求章节，不参与策划规则审查]"
- 删除 working.md 中未引用的 images/ 目录下的图片文件
"""

import re
import os
from pathlib import Path
from typing import List, Tuple, Set


# 美术需求章节的标题关键词
ART_KEYWORDS = ["美术需求", "美术资源", "美术设计", "美术素材"]


def is_art_section_title(line: str) -> bool:
    """判断标题行是否属于美术需求章节"""
    if not line.startswith("#"):
        return False
    title = line.lstrip("#").strip()
    return any(keyword in title for keyword in ART_KEYWORDS)


def get_heading_level(line: str) -> int:
    """获取标题级别（如 ## 返回 2）"""
    if not line.startswith("#"):
        return 0
    match = re.match(r"^(#+)\s", line)
    return len(match.group(1)) if match else 0


def filter_art_sections(markdown: str) -> Tuple[str, List[str]]:
    """过滤美术需求章节

    Returns:
        (过滤后的markdown, 被移除的章节标题列表)
    """
    lines = markdown.split("\n")
    filtered_lines = []
    removed_sections = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # 检查是否是美术需求章节标题
        if is_art_section_title(line):
            section_title = line.lstrip("#").strip()
            removed_sections.append(section_title)
            current_level = get_heading_level(line)

            # 插入占位符
            filtered_lines.append(f"[已过滤：{section_title}，不参与策划规则审查]")
            filtered_lines.append("")

            # 跳过该章节的所有内容，直到遇到同级或更高级标题
            i += 1
            while i < len(lines):
                next_line = lines[i]
                next_level = get_heading_level(next_line)

                # 遇到任意标题（无论级别），都停止跳过
                # 原因：飞书文档中标题级别可能不规范（5.1是三级，5.2是四级）
                # 为了避免误杀平级章节，遇到任何标题都停止
                if next_level > 0:
                    break

                # 只有非标题行才继续跳过
                i += 1
            continue

        # 保留非美术需求章节的内容
        filtered_lines.append(line)
        i += 1

    return "\n".join(filtered_lines), removed_sections


def get_referenced_images(markdown: str) -> Set[str]:
    """提取 markdown 中引用的所有图片文件名

    匹配格式: ![...](images/xxx.jpg) 或 ![...](images/xxx.png)
    """
    pattern = r'!\[.*?\]\(images/([^)]+)\)'
    matches = re.findall(pattern, markdown)
    return set(matches)


def clean_unreferenced_images(working_md_path: Path, images_dir: Path) -> List[str]:
    """删除未被 working.md 引用的图片文件

    Returns:
        被删除的图片文件名列表
    """
    if not images_dir.exists():
        return []

    markdown_content = working_md_path.read_text(encoding="utf-8")
    referenced = get_referenced_images(markdown_content)

    deleted = []
    for img_file in images_dir.iterdir():
        if img_file.is_file() and img_file.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
            if img_file.name not in referenced:
                img_file.unlink()
                deleted.append(img_file.name)

    return deleted


def filter_working_md(working_md_path: Path) -> None:
    """过滤 working.md 中的美术需求章节并清理未引用图片（原地修改）"""
    if not working_md_path.exists():
        raise FileNotFoundError(f"找不到文件: {working_md_path}")

    original_content = working_md_path.read_text(encoding="utf-8")
    filtered_content, removed_sections = filter_art_sections(original_content)

    if removed_sections:
        working_md_path.write_text(filtered_content, encoding="utf-8")
        print(f"已过滤 {len(removed_sections)} 个美术需求章节:")
        for section in removed_sections:
            print(f"  - {section}")
    else:
        print("未发现美术需求章节，无需过滤")

    # 清理未引用的图片
    images_dir = working_md_path.parent / "images"
    deleted_images = clean_unreferenced_images(working_md_path, images_dir)

    if deleted_images:
        print(f"\n已删除 {len(deleted_images)} 个未引用的图片:")
        for img in deleted_images:
            print(f"  - {img}")
    else:
        print("\n未发现未引用的图片，无需清理")


if __name__ == "__main__":
    import sys
    import io

    # Windows GBK 控制台下强制 UTF-8 输出
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

    if len(sys.argv) < 2:
        print("用法: python filter_art_sections.py <working.md路径>")
        sys.exit(1)

    filter_working_md(Path(sys.argv[1]))
