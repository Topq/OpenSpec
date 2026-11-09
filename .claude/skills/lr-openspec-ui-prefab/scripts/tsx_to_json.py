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

if __name__ == "__main__" and sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tsx_layout_common import TSXNode, TSXParseError, parse_number_tuple, parse_tsx  # noqa: E402
from style_profile_contract import StyleProfileError, apply_style_profile  # noqa: E402

NUMERIC_ATTRS = {
    "data-pos": "pos",
    "data-size": "size",
    "data-anchors": "anchors",
    "data-anchor-min": "anchorMin",
    "data-anchor-max": "anchorMax",
    "data-pivot": "pivot",
    "data-color": "color",
    "data-image-color": "imageColor",
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
    "data-role": "role",
    "data-texture": "texture",
    "data-lr-style": "textStyle",
    "data-font": "font",
    "data-font-material": "fontMaterial",
    "data-sprite": "sprite",
    "data-image-type": "imageType",
    "data-text-align": "textAlign",
    "data-vertical-align": "verticalAlign",
    "data-layout-group": "layoutGroup",
    "data-layout-child-alignment": "layoutChildAlignment",
    "data-visible": "visible",
    "data-cell-template": "cellTemplate",
}

NUMBER_SCALAR_ATTRS = {
    "data-layout-spacing": "layoutSpacing",
    "data-font-size": "fontSize",
}

BOOL_ATTRS = {
    "data-preserve-aspect": "preserveAspect",
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

    for attr_name, key in BOOL_ATTRS.items():
        value = node.attr(attr_name)
        if value is not None:
            lowered = value.lower()
            if lowered not in ("true", "false"):
                raise TSXParseError(f"{node.tag}: {attr_name} 必须是 true 或 false，实际 {value}")
            result[key] = lowered == "true"

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


def load_profile(profile_path: Path) -> dict:
    try:
        return json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StyleProfileError(f"无法读取 style profile {profile_path}: {exc}") from exc


def convert_with_profile(tsx_path: Path, profile_path: Path, *, strict_profile: bool = False) -> tuple[dict, list[str]]:
    data = convert(tsx_path)
    profile = load_profile(profile_path)
    warnings = apply_style_profile(data, profile, strict=strict_profile)
    return data, warnings


def has_role(node: dict) -> bool:
    if node.get("role"):
        return True
    return any(has_role(child) for child in node.get("children", []) if isinstance(child, dict))


def main() -> int:
    parser = argparse.ArgumentParser(description="将 Unity 布局 TSX 转换为生成器可读的 JSON")
    parser.add_argument("tsx", type=Path, help="已通过校验的 TSX 文件")
    parser.add_argument("-o", "--output", type=Path, default=None, help="输出 JSON 路径，默认与输入同名 .json")
    parser.add_argument("--profile", type=Path, default=None, help="ui-style-profile.json；按 data-role 物化样式")
    parser.add_argument("--strict-profile", action="store_true", help="profile 缺少声明的角色时直接失败")
    args = parser.parse_args()

    tsx_path = args.tsx.resolve()
    if not tsx_path.is_file():
        print(f"文件不存在: {tsx_path}", file=sys.stderr)
        return 1

    try:
        if args.profile:
            data, warnings = convert_with_profile(tsx_path, args.profile, strict_profile=args.strict_profile)
            for warning in warnings:
                print(f"警告: {warning}", file=sys.stderr)
        else:
            data = convert(tsx_path)
            if has_role(data):
                print("警告: TSX 使用了 data-role，但未提供 --profile，角色样式未展开", file=sys.stderr)
    except (TSXParseError, StyleProfileError) as exc:
        print(f"转换失败: {exc}", file=sys.stderr)
        return 1

    output_path = args.output.resolve() if args.output else tsx_path.with_suffix(".json")
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
