#!/usr/bin/env python3
"""Validate LR HTML/TSX annotations in a Web demo."""

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
    def __init__(self, source: Path, catalog: set[str], global_ids: dict[str, str]) -> None:
        super().__init__(convert_charrefs=True)
        self.source = source
        self.catalog = catalog
        self.errors: list[str] = []
        self.global_ids = global_ids  # 跨文件共享的 id 记录

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
        elif node_id in self.global_ids:
            previous_location = self.global_ids[node_id]
            self.errors.append(
                f"{location} <{tag}> id 重复: {node_id} "
                f"(首次出现于 {previous_location})"
            )
        else:
            self.global_ids[node_id] = location

        if not component:
            self.errors.append(f"{location} <{tag}> LR 节点缺少非空 data-lr-component")
        elif not SEMANTIC_ID_PATTERN.fullmatch(component):
            self.errors.append(f"{location} <{tag}> 组件不是稳定语义 ID: {component}")
        elif component not in self.catalog:
            self.errors.append(f"{location} <{tag}> 组件不在白名单: {component}")

        for name in lr_names:
            if name in ALLOWED_LR_ATTRIBUTES and not (values.get(name) or "").strip():
                self.errors.append(f"{location} <{tag}> 属性值不能为空: {name}")


def find_demo_files(target: Path) -> list[Path]:
    """
    查找需要校验的文件。

    - 如果 target 是文件：直接返回
    - 如果 target 是目录：
      1. React 项目（有 src/ 目录）：扫描 src/**/*.tsx（排除 main.tsx）
         标注只在源码中以字符串字面量存在，必须读源码，不能读构建产物
         （CSR 应用的 dist/index.html 只有空的 <div id="root">）
      2. 否则：查找所有 .html 文件（兼容旧版 HTML demo）
    """
    if target.is_file():
        return [target]

    # 检查是否为 React 项目
    src_dir = target / "src"
    if src_dir.is_dir():
        tsx_files = [
            f for f in src_dir.rglob("*.tsx")
            if f.name != "main.tsx"
        ]
        if tsx_files:
            return sorted(tsx_files)

    # 回退：查找所有 HTML 文件（兼容旧版 HTML demo）
    return sorted(
        path
        for path in target.rglob("*")
        if path.is_file() and path.suffix.lower() in {".html", ".htm"}
    )


def extract_attr_value(attrs_str: str, attr_name: str) -> str | None:
    """
    提取属性值，支持两种形式：
    - 字符串字面量：attr="value"
    - JSX 表达式：attr={expr}，包括含嵌套花括号的模板字符串（如 `id={`fund-${fundType}`}`）
      —— 列表渲染场景下 id 必须动态生成，这是 React 的常规写法，不是特例。
    花括号形式按深度计数找到匹配的右括号，避免被表达式内部的 `}`（如 `${x}` 的收尾）提前截断。
    """
    attr_match = re.search(rf'\b{re.escape(attr_name)}=', attrs_str)
    if not attr_match:
        return None
    pos = attr_match.end()
    if pos >= len(attrs_str):
        return None
    if attrs_str[pos] == '"':
        end = attrs_str.find('"', pos + 1)
        return attrs_str[pos + 1:end] if end != -1 else None
    if attrs_str[pos] == '{':
        depth = 0
        for i in range(pos, len(attrs_str)):
            if attrs_str[i] == '{':
                depth += 1
            elif attrs_str[i] == '}':
                depth -= 1
                if depth == 0:
                    return attrs_str[pos + 1:i]
        return None
    return None


def validate_tsx_file(tsx_path: Path, catalog: set[str], global_ids: dict) -> list[str]:
    """校验 TSX 文件中的 data-lr-* 属性（使用正则）"""
    content = tsx_path.read_text(encoding="utf-8")
    errors = []

    # 提取所有带 data-lr-component 的标签
    # 匹配：<tag ... data-lr-component="xxx" ... >
    # 属性部分用 (?:=>|[^>])*? 而不是单纯 [^>]*：onClick={() => ...} 这类箭头函数
    # 本身含有 '>' 字符，若不特殊处理会被误判为标签结束，导致后续属性漏检。
    tag_pattern = re.compile(
        r'<(\w+)\s+((?:=>|[^>])*?data-lr-component="[^"]+"(?:=>|[^>])*?)(?:>|/>)',
        re.DOTALL
    )

    for match in tag_pattern.finditer(content):
        tag = match.group(1)
        attrs_str = match.group(2)
        line_num = content[:match.start()].count('\n') + 1
        location = f"{tsx_path}:{line_num}"

        # 提取 id（支持字符串字面量和 JSX 表达式）
        node_id = extract_attr_value(attrs_str, 'id')
        if node_id is not None:
            node_id = node_id.strip()

        # 检查 id 非空
        if not node_id:
            errors.append(f"{location} <{tag}> LR 节点缺少非空 id")
        elif node_id in global_ids:
            prev_loc = global_ids[node_id]
            errors.append(f"{location} <{tag}> id 重复: {node_id} (首次出现于 {prev_loc})")
        else:
            global_ids[node_id] = location

        # 提取 data-lr-component
        comp_match = re.search(r'data-lr-component="([^"]+)"', attrs_str)
        component = comp_match.group(1) if comp_match else ""

        if not component:
            errors.append(f"{location} <{tag}> LR 节点缺少非空 data-lr-component")
        elif not SEMANTIC_ID_PATTERN.fullmatch(component):
            errors.append(f"{location} <{tag}> 组件不是稳定语义 ID: {component}")
        elif component not in catalog:
            errors.append(f"{location} <{tag}> 组件不在白名单: {component}")

        # 检查所有 data-lr-* 属性
        for attr_match in re.finditer(r'(data-lr-\w+)="([^"]*)"', attrs_str):
            attr_name = attr_match.group(1)
            attr_value = attr_match.group(2)

            if attr_name not in ALLOWED_LR_ATTRIBUTES:
                errors.append(f"{location} <{tag}> 禁止的属性: {attr_name}")
            if not attr_value.strip():
                errors.append(f"{location} <{tag}> 属性值不能为空: {attr_name}")

    return errors


def validate(target: Path, catalog_path: Path) -> list[str]:
    if not target.exists():
        return [f"Demo 路径不存在: {target}"]

    is_react_project = target.is_dir() and (target / "src").is_dir()

    if is_react_project:
        package_json = target / "package.json"
        if not package_json.is_file():
            return [f"React 项目缺少 package.json: {target}"]
        # 标注校验直接读 TSX 源码，不依赖构建产物：
        # Vite/React 的 dist/index.html 只有空的 <div id="root">，
        # data-lr-* 属性在打包后的 JS 里执行时才会挂到 DOM 上，
        # 扫描构建产物会导致"零节点 = 零错误"的假阳性。
        # 是否能构建成功（npm run build）是独立的检查项，与标注校验无关。
    elif target.is_dir() and not (target / "index.html").is_file():
        return [f"Demo 根目录缺少 index.html: {target}"]

    try:
        catalog = load_catalog(catalog_path)
    except (OSError, UnicodeError, ValueError) as exc:
        return [str(exc)]

    # 查找需要校验的文件
    files = find_demo_files(target)
    if not files:
        return [f"未找到可校验的文件: {target}"]

    # 校验所有文件（跨文件检查 id 唯一性）
    errors = []
    global_ids = {}  # 跨文件的 id 记录

    for file in files:
        try:
            if file.suffix.lower() in {".html", ".htm"}:
                # HTML 文件：用 HTMLParser
                parser = AnnotationParser(file, catalog, global_ids)
                parser.feed(file.read_text(encoding="utf-8"))
                parser.close()
                errors.extend(parser.errors)
            elif file.suffix == ".tsx":
                # TSX 文件：用正则提取
                file_errors = validate_tsx_file(file, catalog, global_ids)
                errors.extend(file_errors)
        except (OSError, UnicodeError) as exc:
            errors.append(f"无法读取 {file}: {exc}")
        except Exception as exc:
            errors.append(f"无法解析 {file}: {exc}")

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
