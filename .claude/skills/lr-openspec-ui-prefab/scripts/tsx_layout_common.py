#!/usr/bin/env python3
"""Shared TSX parsing for lr-openspec-ui-prefab scripts.

Parses the restricted TSX dialect described in
references/unity-layout-attributes.md: JSX-like tags with only static
string-literal data-* attributes (no expressions, no .map(), no template
strings for prefab-relevant tags). This lets a plain stack-based HTML-style
parser stand in for a full JSX parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

# JSX comments — {/* ... */} — are not markup, but HTMLParser has no idea and
# happily turns any `<Button>` / `<T>` mentioned inside one into a real node
# (which then shadows the sibling it was documenting). Strip them before
# feeding the parser. Non-greedy so adjacent comments stay separate; DOTALL so
# multi-line comments are covered.
_JSX_COMMENT_RE = re.compile(r"\{\s*/\*.*?\*/\s*\}", re.DOTALL)


def _blank_jsx_comments(raw: str) -> str:
    """Blank out {/* ... */} comments, keeping newlines so the line/column
    numbers HTMLParser reports still match the original file."""

    def blank(match: re.Match[str]) -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    return _JSX_COMMENT_RE.sub(blank, raw)

VOID_TAGS = {"img", "br", "hr", "input"}

# Tags that only wrap JSX/logic and never carry Unity data; skipped when
# building the layout tree but their children are re-parented to the
# nearest ancestor that does carry data-component / data-prefab-child-path.
TRANSPARENT_WRAPPER_TAGS = {"react.fragment"}


@dataclass
class TSXNode:
    tag: str
    attrs: dict[str, str]
    line: int
    column: int
    text: str = ""
    children: list["TSXNode"] = field(default_factory=list)

    def attr(self, name: str) -> str | None:
        value = self.attrs.get(name)
        if value is None:
            return None
        value = value.strip()
        return value or None

    def has_component(self) -> bool:
        return self.attr("data-component") is not None

    def has_prefab_child_path(self) -> bool:
        return self.attr("data-prefab-child-path") is not None

    def has_prefab_asset_path(self) -> bool:
        return self.attr("data-prefab-asset-path") is not None

    def has_lr_component(self) -> bool:
        return self.attr("data-lr-component") is not None

    def is_layout_relevant(self) -> bool:
        return (
            self.has_component()
            or self.has_prefab_child_path()
            or self.has_prefab_asset_path()
            or self.has_lr_component()
        )


class TSXParseError(Exception):
    pass


class _TreeBuildingParser(HTMLParser):
    """Builds a full DOM-ish tree, including wrapper tags like <main>/<div>
    without data-* markers, so callers can walk parent/child relationships
    exactly as authored.
    """

    def __init__(self, source_name: str) -> None:
        super().__init__(convert_charrefs=True)
        self.source_name = source_name
        self.root = TSXNode(tag="#root", attrs={}, line=0, column=0)
        self._stack: list[TSXNode] = [self.root]

    def _make_node(self, tag: str, attrs: list[tuple[str, str | None]]) -> TSXNode:
        line, column = self.getpos()
        attr_map = {name.lower(): (value if value is not None else "") for name, value in attrs}
        return TSXNode(tag=tag.lower(), attrs=attr_map, line=line, column=column + 1)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = self._make_node(tag, attrs)
        self._stack[-1].children.append(node)
        if tag.lower() not in VOID_TAGS:
            self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = self._make_node(tag, attrs)
        self._stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in VOID_TAGS:
            return
        for index in range(len(self._stack) - 1, 0, -1):
            if self._stack[index].tag == tag.lower():
                del self._stack[index:]
                return
        # Unmatched close tag: ignore, JSX fragments (<>...</>) are not
        # supported by this restricted dialect.

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text and len(self._stack) > 1:
            self._stack[-1].text += text


def parse_tsx(source: Path) -> TSXNode:
    """Parse a .tsx file and return the synthetic #root node.

    Raises TSXParseError on unreadable or unparsable input.
    """

    try:
        raw = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise TSXParseError(f"无法读取 {source}: {exc}") from exc

    parser = _TreeBuildingParser(str(source))
    try:
        parser.feed(_blank_jsx_comments(raw))
        parser.close()
    except Exception as exc:  # HTMLParser surfaces malformed markup as generic errors.
        raise TSXParseError(f"无法解析 {source}: {exc}") from exc
    return parser.root


def find_component_root(root: TSXNode) -> TSXNode | None:
    """Return the first descendant (depth-first) whose tag carries
    data-component -- this is the actual UI root panel, skipping any
    `export default function ...() { return ( ... ) }` wrapper tags that
    do not exist in JSX (those are stripped by the parser already since it
    only sees the returned markup... but callers should pass just the JSX
    portion; see extract_jsx_block()).
    """

    stack = list(root.children)
    while stack:
        node = stack.pop(0)
        if node.is_layout_relevant():
            return node
        stack = list(node.children) + stack
    return None


def iter_layout_nodes(node: TSXNode):
    """Depth-first iterator over nodes that carry data-component or
    data-prefab-child-path / data-prefab-asset-path (i.e. nodes the Unity
    generator actually acts on). Wrapper tags are skipped but their
    layout-relevant descendants are still visited.
    """

    for child in node.children:
        if child.is_layout_relevant():
            yield child
        yield from iter_layout_nodes(child)


def parse_number_tuple(value: str, source: str = "") -> list[float]:
    """Parse "(1, 0.85, 0.2, 1)" style attribute values into a float list."""

    trimmed = value.strip()
    if trimmed.startswith("(") and trimmed.endswith(")"):
        trimmed = trimmed[1:-1]
    parts = [part.strip() for part in trimmed.split(",") if part.strip()]
    try:
        return [float(part) for part in parts]
    except ValueError as exc:
        raise TSXParseError(f"{source}: 无法解析数值元组 '{value}'") from exc
