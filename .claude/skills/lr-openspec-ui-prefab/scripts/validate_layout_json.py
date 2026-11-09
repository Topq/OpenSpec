#!/usr/bin/env python3
"""Validate the node tree emitted by tsx_to_json and consumed by BuildNode.

Field completeness belongs to validate_unity_layout.py (--csharp). This check
validates the serialized layout contract before invoking either MCP or CLI.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys

from layout_contract import ENUM_VALUES
from style_profile_contract import STYLE_ROLES

FIELD = re.compile(r"^[A-Za-z_]\w*(?:\[\d+\])?$")
VECTOR_LENGTHS = {"pos": (2, 3), "size": (2,), "anchors": (4,),
                  "anchorMin": (2,), "anchorMax": (2,), "pivot": (2,),
                  "layoutPadding": (4,), "color": (4,), "imageColor": (4,)}
IMAGE_TYPE_VALUES = {"Simple", "Sliced", "Tiled", "Filled"}
FONT_ROOT = "Assets/Resources/Font/"
STYLE_KEYS = {
    "fontSize", "color", "font", "fontMaterial", "textAlign", "verticalAlign",
    "sprite", "imageType", "imageColor", "preserveAspect", "texture",
}


def validate_layout_json(json_path: Path, project_root: Path | None = None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return False, [f"无法读取 Layout JSON: {exc}"]

    if project_root is not None:
        project_root = Path(project_root)
        if not (project_root / "Assets").is_dir():
            return False, [f"Unity 项目根目录无效（缺少 Assets 目录）: {project_root}"]

    catalog_dir = Path(__file__).resolve().parent / "lr_ui_gen" / "ComponentRecipes"
    catalog = {path.stem for path in catalog_dir.glob("*.json")}
    if not catalog:
        return False, [f"组件配方目录为空: {catalog_dir}"]

    scopes: list[dict[str, list[str]]] = [{}]

    def check_node(node: object, path: str, scope: dict[str, list[str]], is_root: bool = False) -> None:
        if not isinstance(node, dict):
            errors.append(f"{path}: 节点必须是对象")
            return
        selectors = [key for key in ("component", "prefabChildPath", "prefabAssetPath") if key in node]
        if is_root or selectors or "field" in node or "lrComponent" in node:
            if not isinstance(node.get("name"), str) or not node["name"].strip():
                errors.append(f"{path}: 缺少有效 name；要求根节点树，不接受 rootName/fields/hierarchy 包装格式")
        if is_root and not selectors:
            errors.append(f"{path}: 根节点缺少 component 或 Prefab 引用")
        if len(selectors) > 1:
            errors.append(f"{path}: component、prefabChildPath、prefabAssetPath 不能混用")
        if ("prefabChildPath" in node or "prefabAssetPath" in node) and (STYLE_KEYS & set(node)):
            errors.append(f"{path}: 样式覆盖不能作用于 Prefab 引用节点")
        if ("prefabChildPath" in node or "prefabAssetPath" in node) and "role" in node:
            errors.append(f"{path}: data-role 不能作用于 Prefab 引用节点")
        for key in selectors:
            if not isinstance(node[key], str) or not node[key].strip():
                errors.append(f"{path}: {key} 必须是非空字符串")
        if "component" in node and isinstance(node["component"], str) and node["component"] not in catalog:
            errors.append(f"{path}: 未知语义组件 {node['component']}")
        for key, lengths in VECTOR_LENGTHS.items():
            if key not in node:
                continue
            value = node[key]
            if (not isinstance(value, list) or len(value) not in lengths
                    or any(type(x) not in (int, float) or not math.isfinite(x) for x in value)):
                errors.append(f"{path}: {key} 必须是 {lengths} 长度之一的有限数值数组")
        for key in ("field", "lrComponent", "text", "textStyle", "textAlign", "verticalAlign",
                    "layoutGroup", "layoutChildAlignment", "font", "fontMaterial", "sprite",
                    "imageType", "texture", "role", "tag"):
            if key in node and not isinstance(node[key], str):
                errors.append(f"{path}: {key} 必须是字符串")
        for key, allowed in ENUM_VALUES.items():
            if key in node and (not isinstance(node[key], str) or node[key] not in allowed):
                errors.append(f"{path}: {key} 取值非法（允许: {sorted(allowed)}）")

        if "role" in node and (not isinstance(node["role"], str) or node["role"] not in STYLE_ROLES):
            errors.append(f"{path}: role 取值非法（允许: {sorted(STYLE_ROLES)}）")

        if "textStyle" in node and "component" not in node:
            errors.append(f"{path}: textStyle 只能与 component 一起使用")
        if "textStyle" in node and "component" in node:
            variant = f"{node['component']}-{node['textStyle']}"
            if variant not in catalog:
                errors.append(f"{path}: textStyle=\"{node['textStyle']}\" 没有对应的配方变体 {variant}.json")

        if "imageType" in node and (not isinstance(node["imageType"], str)
                                    or node["imageType"] not in IMAGE_TYPE_VALUES):
            errors.append(f"{path}: imageType 取值非法（允许: {sorted(IMAGE_TYPE_VALUES)}）")

        if "fontSize" in node:
            value = node["fontSize"]
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                errors.append(f"{path}: fontSize 必须是有限正数")

        for key in ("color", "imageColor"):
            value = node.get(key)
            if isinstance(value, list) and value and any(
                    type(x) not in (int, float) or not math.isfinite(x) or x < 0 or x > 1 for x in value):
                errors.append(f"{path}: {key} 的分量必须是 0..1 的有限数值")

        for key, prefix in (("font", FONT_ROOT), ("fontMaterial", FONT_ROOT),
                            ("sprite", "Assets/"), ("texture", "Assets/")):
            value = node.get(key)
            if isinstance(value, str) and value and not value.startswith(prefix):
                errors.append(f"{path}: {key} 必须以 {prefix} 开头")
            if (project_root is not None and isinstance(value, str)
                    and value.startswith("Assets/")):
                asset_path = project_root / value.replace("\\", "/")
                if not asset_path.is_file():
                    errors.append(f"{path}: {key} 指向的资源不存在: {value}")

        if isinstance(node.get("field"), str):
            if any(not FIELD.fullmatch(field.strip()) for field in node["field"].split(",")):
                errors.append(f"{path}: field 必须是字段名或非负数组下标，可用逗号分隔")
            else:
                for field in node["field"].split(","):
                    field = field.strip()
                    scope.setdefault(field.split("[")[0], []).append(field)
        for key in ("visible", "cellTemplate", "preserveAspect"):
            if key in node and node[key] not in (True, False, "true", "false"):
                errors.append(f"{path}: {key} 必须为 true/false")
        if "layoutSpacing" in node:
            value = node["layoutSpacing"]
            if type(value) not in (int, float) or not math.isfinite(value):
                errors.append(f"{path}: layoutSpacing 必须是有限数值")
        children = node.get("children", [])
        if not isinstance(children, list):
            errors.append(f"{path}: children 必须是数组")
            return
        child_scope = scope
        if node.get("lrComponent"):
            child_scope = {}
            scopes.append(child_scope)
        for index, child in enumerate(children):
            check_node(child, f"{path}/children[{index}]", child_scope)

    check_node(data, "root", scopes[0], is_root=True)
    for scope in scopes:
        for name, fields in scope.items():
            indexed = [field for field in fields if "[" in field]
            if not indexed:
                continue
            indices = [int(field.split("[")[1][:-1]) for field in indexed]
            if len(indexed) != len(fields) or len(indices) != len(set(indices)):
                errors.append(f"字段 {name}: 数组下标重复或混用裸字段绑定")
            if sorted(set(indices)) != list(range(len(set(indices)))):
                errors.append(f"字段 {name}: 数组下标必须从 0 连续编号，实际 {sorted(set(indices))}")
    return not errors, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("layout", type=Path, help="tsx_to_json 输出的节点树 JSON")
    parser.add_argument("--project-root", type=Path, default=None,
                        help="Unity 项目根目录；提供时校验 font/fontMaterial/sprite/texture 真实存在")
    args = parser.parse_args()
    ok, errors = validate_layout_json(args.layout, project_root=args.project_root)
    if not ok:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Layout JSON 校验通过: {args.layout}")
    return 0


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
