#!/usr/bin/env python3
"""Convert a validated Unity-layout TSX file into the JSON structure consumed
by the Unity-side generator (Assets/Editor/LRUnityLayoutPrefabGenerator.cs).

Usage:
  python tsx_to_json.py <tsx-file> [-o output.json]

Only run this after validate_unity_layout.py passes with zero errors --
this script does not re-validate; it trusts the TSX is well-formed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tsx_layout_common import TSXNode, TSXParseError, parse_number_tuple, parse_tsx  # noqa: E402

NUMERIC_ATTRS = {
    "data-pos": "pos",
    "data-size": "size",
    "data-anchors": "anchors",
    "data-anchor-min": "anchorMin",
    "data-anchor-max": "anchorMax",
    "data-pivot": "pivot",
    "data-color": "color",
    "data-layout-padding": "layoutPadding",
}

STRING_ATTRS = {
    "data-name": "name",
    "data-component": "component",
    "data-lr-component": "lrComponent",
    "data-prefab-child-path": "prefabChildPath",
    "data-prefab-asset-path": "prefabAssetPath",
    "data-field": "field",
    "data-text": "text",
    "data-lr-style": "textStyle",
    "data-text-align": "textAlign",
    "data-vertical-align": "verticalAlign",
    "data-layout-group": "layoutGroup",
    "data-layout-child-alignment": "layoutChildAlignment",
    "data-visible": "visible",
}

NUMBER_SCALAR_ATTRS = {
    "data-layout-spacing": "layoutSpacing",
}


def node_to_dict(node: TSXNode) -> dict:
    result: dict = {}

    for attr_name, key in STRING_ATTRS.items():
        value = node.attr(attr_name)
        if value is not None:
            result[key] = value

    for attr_name, key in NUMERIC_ATTRS.items():
        value = node.attr(attr_name)
        if value is not None:
            try:
                result[key] = parse_number_tuple(value)
            except TSXParseError as exc:
                raise TSXParseError(f"{node.tag} data-name={node.attr('data-name')}: {exc}") from exc

    for attr_name, key in NUMBER_SCALAR_ATTRS.items():
        value = node.attr(attr_name)
        if value is not None:
            try:
                result[key] = float(value)
            except ValueError as exc:
                raise TSXParseError(f"{node.tag}: 无法解析数值 {attr_name}={value}") from exc

    if node.text and "text" not in result:
        result["text"] = node.text

    result["tag"] = node.tag

    children = [
        node_to_dict(child)
        for child in node.children
        if child.is_layout_relevant() or _has_relevant_descendant(child)
    ]
    if children:
        result["children"] = children

    return result


def _has_relevant_descendant(node: TSXNode) -> bool:
    for child in node.children:
        if child.is_layout_relevant() or _has_relevant_descendant(child):
            return True
    return False


def find_root_component(root: TSXNode) -> TSXNode:
    stack = list(root.children)
    while stack:
        node = stack.pop(0)
        if node.is_layout_relevant():
            return node
        stack = list(node.children) + stack
    raise TSXParseError("未找到任何带 data-component 的根节点")


def convert(tsx_path: Path) -> dict:
    root = parse_tsx(tsx_path)
    root_component = find_root_component(root)
    return node_to_dict(root_component)


def main() -> int:
    parser = argparse.ArgumentParser(description="将 Unity 布局 TSX 转换为生成器可读的 JSON")
    parser.add_argument("tsx", type=Path, help="已通过校验的 TSX 文件")
    parser.add_argument("-o", "--output", type=Path, default=None, help="输出 JSON 路径，默认与输入同名 .json")
    args = parser.parse_args()

    tsx_path = args.tsx.resolve()
    if not tsx_path.is_file():
        print(f"文件不存在: {tsx_path}", file=sys.stderr)
        return 1

    try:
        data = convert(tsx_path)
    except TSXParseError as exc:
        print(f"转换失败: {exc}", file=sys.stderr)
        return 1

    output_path = args.output.resolve() if args.output else tsx_path.with_suffix(".json")
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
