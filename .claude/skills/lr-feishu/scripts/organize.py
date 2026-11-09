#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把飞书转换后的 Markdown 按设计流程整理成分章文件。

输入：一份带 frontmatter 的 Markdown（document_converter 的输出）。
输出：01~07 分章 Markdown + README.md + images/。

规则见 filter_rules.py；本文件只负责解析、过滤、归类和写文件。
"""

from __future__ import annotations

import io
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

from filter_rules import (
    CATEGORY_RULES,
    DROP_H1,
    DROP_H2,
    ECONOMY_H2,
    FILE_DESCRIPTIONS,
    OUTPUT_ORDER,
    SYSTEM_ECONOMY_FILE,
    SYSTEM_H1_PATTERN,
    SYSTEM_RULES_FILE,
    TABLE_RULES,
    UNKNOWN_FILE,
)


@dataclass
class SubSection:
    heading: str
    body: str = ""


@dataclass
class Chapter:
    heading: str
    title: str
    preamble: str = ""
    subsections: list[SubSection] = field(default_factory=list)


@dataclass
class OutputEntry:
    filename: str
    title: str
    preamble: str = ""
    subsections: list[SubSection] = field(default_factory=list)


def split_frontmatter(text: str) -> tuple[dict, str]:
    """分离 converter 写入的 frontmatter。"""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip()
    body = text[end + 4 :].lstrip("\n")
    meta: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, body


def parse_chapters(body: str) -> tuple[str, list[Chapter]]:
    """按 H1/H2 解析。第一个 H1 是文档标题，其余 H1 是章节。"""
    chapters: list[Chapter] = []
    current: Chapter | None = None
    sub: SubSection | None = None
    doc_title = ""
    in_fence = False

    for line in body.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        heading_line = not in_fence

        if heading_line and line.startswith("# "):
            title = line[2:].strip()
            if not doc_title:
                doc_title = title
                continue
            current = Chapter(heading=line, title=title)
            chapters.append(current)
            sub = None
            continue

        if heading_line and line.startswith("## "):
            if current is None:
                current = Chapter(heading="# 其他", title="其他")
                chapters.append(current)
            sub = SubSection(heading=line)
            current.subsections.append(sub)
            continue

        if sub is not None:
            sub.body += line + "\n"
        elif current is not None:
            current.preamble += line + "\n"

    return doc_title, chapters


def match_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def first_cell(row: str) -> str:
    parts = row.strip().strip("|").split("|")
    if not parts:
        return ""
    return parts[0].strip().strip("*").strip()


def find_table_rule(heading: str) -> dict | None:
    for candidate in TABLE_RULES:
        if re.search(candidate["section"], heading):
            return candidate
    return None


def filter_table_rows(body: str, section_heading: str) -> str:
    """按 filter_rules.TABLE_RULES 过滤 Markdown 表格行。

    表格可能挂在 H3 下（例如 2.5.1、2.6.4），所以按“最近的 ### 标题”匹配规则；
    没有 H3 时回退到所在 H2 标题。
    """
    lines = body.splitlines()
    out: list[str] = []
    current_heading = section_heading
    i = 0

    while i < len(lines):
        line = lines[i]
        if line.startswith("### "):
            current_heading = line

        if not line.lstrip().startswith("|"):
            out.append(line)
            i += 1
            continue

        j = i
        while j < len(lines) and lines[j].lstrip().startswith("|"):
            j += 1
        table = lines[i:j]
        rule = find_table_rule(current_heading)

        if rule and len(table) >= 2 and re.match(r"^\s*\|[\s:|-]+\|\s*$", table[1]):
            header, separator, rows = table[0], table[1], table[2:]
            kept: list[str] = []
            for row in rows:
                # 关键词可能出现在任意列（例如待确认表的“问题”列），按整行匹配
                if "keep" in rule and not any(key in row for key in rule["keep"]):
                    continue
                if "drop" in rule and any(key in row for key in rule["drop"]):
                    continue
                kept.append(row)
            if kept:
                out.extend([header, separator] + kept)
        else:
            out.extend(table)

        i = j

    return "\n".join(out)


def filter_h3_blocks(body: str) -> str:
    """在二级章节内部按 ### 标题删除命中 DROP_H2 的小节（含其内容）。

    飞书的 2.5.4 / 2.7.5 这类是 H3，不是 H2；只过滤 H2 会漏掉它们。
    """
    lines = body.splitlines()
    out: list[str] = []
    dropping = False
    in_fence = False

    for line in lines:
        if line.startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("### "):
            dropping = match_any(line, DROP_H2)
        if not dropping:
            out.append(line)

    return "\n".join(out)


def filter_chapters(chapters: list[Chapter]) -> list[Chapter]:
    result: list[Chapter] = []
    for chapter in chapters:
        if match_any(chapter.title, DROP_H1):
            continue
        chapter.subsections = [
            sub for sub in chapter.subsections if not match_any(sub.heading, DROP_H2)
        ]
        for sub in chapter.subsections:
            sub.body = filter_h3_blocks(sub.body)
            sub.body = filter_table_rows(sub.body, sub.heading)
        # 附录 A 这类没有二级标题的章节，表格在 preamble 里
        chapter.preamble = filter_h3_blocks(chapter.preamble)
        chapter.preamble = filter_table_rows(chapter.preamble, chapter.title)
        result.append(chapter)
    return result


def find_category(title: str) -> tuple[str, str] | None:
    for pattern, filename, out_title in CATEGORY_RULES:
        if re.search(pattern, title):
            return filename, out_title
    if re.search(SYSTEM_H1_PATTERN, title):
        return "SYSTEM", "SYSTEM"
    return None


def categorize(chapters: list[Chapter]) -> dict[str, OutputEntry]:
    outputs: dict[str, OutputEntry] = {}

    def get(filename: str, title: str) -> OutputEntry:
        if filename not in outputs:
            outputs[filename] = OutputEntry(filename=filename, title=title)
        return outputs[filename]

    for chapter in chapters:
        category = find_category(chapter.title)
        if category is None:
            entry = get(*UNKNOWN_FILE)
            entry.subsections.extend(chapter.subsections)
            if chapter.preamble.strip():
                entry.preamble += chapter.preamble
            continue

        filename, out_title = category
        if filename == "SYSTEM":
            rules_file, rules_title = SYSTEM_RULES_FILE
            economy_file, economy_title = SYSTEM_ECONOMY_FILE
            for sub in chapter.subsections:
                if match_any(sub.heading, ECONOMY_H2):
                    get(economy_file, economy_title).subsections.append(sub)
                else:
                    get(rules_file, rules_title).subsections.append(sub)
            if chapter.preamble.strip():
                get(rules_file, rules_title).preamble += chapter.preamble
        else:
            entry = get(filename, out_title)
            entry.subsections.extend(chapter.subsections)
            if chapter.preamble.strip():
                entry.preamble += chapter.preamble

    return outputs


def render(entry: OutputEntry) -> str:
    parts = [f"# {entry.title}", ""]
    if entry.preamble.strip():
        parts.extend([entry.preamble.strip(), ""])
    for sub in entry.subsections:
        parts.append(sub.heading)
        parts.append("")
        if sub.body.strip():
            parts.extend([sub.body.strip(), ""])
    return "\n".join(parts).rstrip() + "\n"


def collect_image_links(text: str) -> list[str]:
    return re.findall(r"!\[[^\]]*\]\((images/[^)]+)\)", text)


def write_readme(out_dir: Path, meta: dict, source: str, entries: dict[str, OutputEntry]) -> None:
    lines = [f"# {meta.get('title', '未命名文档')}", ""]
    if source:
        lines.append(f"- 来源: {source}")
    if meta.get("document_id"):
        lines.append(f"- document_id: `{meta['document_id']}`")
    if meta.get("revision_id"):
        lines.append(f"- revision_id: `{meta['revision_id']}`")

    lines.extend(["", "## 阅读顺序", "", "| 文件 | 内容 |", "| --- | --- |"])
    for filename, title in OUTPUT_ORDER:
        if filename in entries:
            lines.append(f"| [{title}]({filename}) | {FILE_DESCRIPTIONS.get(filename, '')} |")

    lines.extend(
        [
            "",
            "## 处理说明",
            "",
            "已删除美术、音频、配置表、埋点、服务端实现、世界观、版本规划、设计目标等非原型内容；",
            "保留设计逻辑、页面与 UI、影响界面的待确认项。文中数值为原文示意，原型请用占位。",
            "",
        ]
    )
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def organize_document(
    markdown: str,
    out_dir: Path,
    source_images: Path | None,
    source: str,
) -> list[str]:
    meta, body = split_frontmatter(markdown)
    doc_title, chapters = parse_chapters(body)
    meta.setdefault("title", doc_title or "未命名文档")

    filtered = filter_chapters(chapters)
    entries = categorize(filtered)
    # 过滤后没有内容的分类不生成文件
    entries = {
        filename: entry
        for filename, entry in entries.items()
        if entry.subsections or entry.preamble.strip()
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    images_out = out_dir / "images"

    referenced: set[str] = set()
    for entry in entries.values():
        referenced.update(collect_image_links(render(entry)))

    if source_images and source_images.exists():
        images_out.mkdir(parents=True, exist_ok=True)
        for rel_path in referenced:
            name = Path(rel_path).name
            src = source_images / name
            dst = images_out / name
            if src.exists() and src.resolve() != dst.resolve():
                shutil.copy2(src, dst)

    written: list[str] = []
    for filename, _ in OUTPUT_ORDER:
        if filename in entries:
            (out_dir / filename).write_text(render(entries[filename]), encoding="utf-8")
            written.append(filename)

    for filename, entry in entries.items():
        if filename not in written:
            (out_dir / filename).write_text(render(entry), encoding="utf-8")
            written.append(filename)

    # 删掉没有被任何分章文件引用的图片（URL 模式会下载全部图，容易留下重复图）
    if images_out.exists():
        for image_file in images_out.iterdir():
            if image_file.is_file() and f"images/{image_file.name}" not in referenced:
                image_file.unlink()

    write_readme(out_dir, meta, source, entries)
    return written


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="把 Markdown 整理成分章文件")
    parser.add_argument("--input", type=Path, required=True, help="输入 Markdown")
    parser.add_argument("--out", type=Path, required=True, help="输出目录")
    parser.add_argument("--images", type=Path, help="图片源目录，默认输入文件旁的 images/")
    args = parser.parse_args()

    markdown = args.input.read_text(encoding="utf-8")
    source_images = args.images or (args.input.parent / "images")
    written = organize_document(markdown, args.out, source_images, str(args.input))
    print(f"已整理: {args.out}")
    for filename in written:
        print(f"  - {filename}")
    print("  - README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
