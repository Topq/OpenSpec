#!/usr/bin/env python3
"""Validate LR HTML annotations in a Web demo."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

# Windows GBK 控制台下强制 UTF-8 输出,避免中文乱码
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")



ALLOWED_LR_ATTRIBUTES = {
    "data-lr-component",
    "data-lr-template",
    "data-lr-slot",
    "data-lr-bind",
    "data-lr-action",
    "data-lr-visible-when",
    "data-lr-bake",
}
SEMANTIC_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+$")
CATALOG_ROW_PATTERN = re.compile(r"^\|\s*`([^`]+)`\s*\|")


def load_catalog(path: Path) -> set[str]:
    if not path.is_file():
        raise ValueError(f"组件白名单不存在: {path}")

    component_ids = {
        match.group(1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if (match := CATALOG_ROW_PATTERN.match(line))
        and SEMANTIC_ID_PATTERN.fullmatch(match.group(1))
    }
    if not component_ids:
        raise ValueError(f"组件白名单中没有可用语义 ID: {path}")
    return component_ids


class AnnotationParser(HTMLParser):
    def __init__(self, source: Path, catalog: set[str]) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.catalog = catalog
        self.errors: list[str] = []
        self.ids: dict[str, tuple[int, int]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._validate_tag(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._validate_tag(tag, attrs)

    def _validate_tag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        line, column = self.getpos()
        location = f"{self.source}:{line}:{column + 1}"
        names = [name.lower() for name, _ in attrs]
        values = {name.lower(): value for name, value in attrs}

        duplicates = sorted({name for name in names if names.count(name) > 1})
        for name in duplicates:
            self.errors.append(f"{location} <{tag}> 属性重复: {name}")

        lr_names = [name for name in names if name.startswith("data-lr-")]
        for name in sorted(set(lr_names) - ALLOWED_LR_ATTRIBUTES):
            self.errors.append(f"{location} <{tag}> 禁止的属性: {name}")

        if not lr_names:
            return

        node_id = (values.get("id") or "").strip()
        component = (values.get("data-lr-component") or "").strip()
        if not node_id:
            self.errors.append(f"{location} <{tag}> LR 节点缺少非空 id")
        elif node_id in self.ids:
            previous_line, previous_column = self.ids[node_id]
            self.errors.append(
                f"{location} <{tag}> id 重复: {node_id} "
                f"(首次出现于 {previous_line}:{previous_column})"
            )
        else:
            self.ids[node_id] = (line, column + 1)

        if not component:
            self.errors.append(f"{location} <{tag}> LR 节点缺少非空 data-lr-component")
        elif not SEMANTIC_ID_PATTERN.fullmatch(component):
            self.errors.append(f"{location} <{tag}> 组件不是稳定语义 ID: {component}")
        elif component not in self.catalog:
            self.errors.append(f"{location} <{tag}> 组件不在白名单: {component}")

        for name in lr_names:
            if name in ALLOWED_LR_ATTRIBUTES and not (values.get(name) or "").strip():
                self.errors.append(f"{location} <{tag}> 属性值不能为空: {name}")


def find_html_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix.lower() in {".html", ".htm"} else []
    return sorted(
        path
        for path in target.rglob("*")
        if path.is_file() and path.suffix.lower() in {".html", ".htm"}
    )


def validate(target: Path, catalog_path: Path) -> list[str]:
    if not target.exists():
        return [f"Demo 路径不存在: {target}"]
    if target.is_dir() and not (target / "index.html").is_file():
        return [f"Demo 根目录缺少 index.html: {target}"]

    try:
        catalog = load_catalog(catalog_path)
    except (OSError, UnicodeError, ValueError) as exc:
        return [str(exc)]

    html_files = find_html_files(target)
    if not html_files:
        return [f"没有找到 HTML 文件: {target}"]

    errors: list[str] = []
    for html_file in html_files:
        parser = AnnotationParser(html_file, catalog)
        try:
            parser.feed(html_file.read_text(encoding="utf-8"))
            parser.close()
        except (OSError, UnicodeError) as exc:
            errors.append(f"无法读取 {html_file}: {exc}")
        except Exception as exc:  # HTMLParser may report malformed declarations.
            errors.append(f"无法解析 {html_file}: {exc}")
        errors.extend(parser.errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 LR Web Demo 的 HTML 标识协议")
    parser.add_argument("target", type=Path, help="demo 目录或单个 HTML 文件")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "references" / "unity-ui-components.md",
        help="Unity UI 组件白名单文档",
    )
    args = parser.parse_args()

    errors = validate(args.target.resolve(), args.catalog.resolve())
    if errors:
        print(f"校验失败，共 {len(errors)} 项:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"校验通过: {args.target.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
