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

FIELD = re.compile(r"^[A-Za-z_]\w*(?:\[\d+\])?$")
VECTOR_LENGTHS = {"pos": (2, 3), "size": (2,), "anchors": (4,),
                  "anchorMin": (2,), "anchorMax": (2,), "pivot": (2,),
                  "layoutPadding": (4,)}


def validate_layout_json(json_path: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return False, [f"无法读取 Layout JSON: {exc}"]

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
        for key in ("field", "lrComponent", "text", "textStyle", "textAlign", "verticalAlign", "layoutGroup", "layoutChildAlignment", "tag"):
            if key in node and not isinstance(node[key], str):
                errors.append(f"{path}: {key} 必须是字符串")
        for key, allowed in ENUM_VALUES.items():
            if key in node and (not isinstance(node[key], str) or node[key] not in allowed):
                errors.append(f"{path}: {key} 取值非法（允许: {sorted(allowed)}）")
        if isinstance(node.get("field"), str):
            if any(not FIELD.fullmatch(field.strip()) for field in node["field"].split(",")):
                errors.append(f"{path}: field 必须是字段名或非负数组下标，可用逗号分隔")
            else:
                for field in node["field"].split(","):
                    field = field.strip()
                    scope.setdefault(field.split("[")[0], []).append(field)
        for key in ("visible", "cellTemplate"):
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
    args = parser.parse_args()
    ok, errors = validate_layout_json(args.layout)
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
