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
                  "layoutPadding": (4,), "color": (4,), "imageColor": (4,),
                  "outlineColor": (4,)}
IMAGE_TYPE_VALUES = {"Simple", "Sliced", "Tiled", "Filled"}
FONT_ROOT = "Assets/Resources/Font/"
STYLE_KEYS = {
    "fontSize", "color", "font", "fontMaterial", "outlineColor",
    "textAlign", "verticalAlign",
    "sprite", "imageType", "imageColor", "preserveAspect", "texture",
}

# 字体材质只提供描边宽度（_OutlineWidth），最终描边色由每个 TMP 的
# m_outlineColor 决定。粗描边材质漏写 outlineColor 会渲染成材质默认的
# 白色粗描边，字内孔被糊死。宽度从 .mat 读取，不按文件名判断
# （ssfttSDF_UI_ShadowOutLine2 名字带 OutLine2 但只有 0.201）。
OUTLINE_ERROR_WIDTH = 1.0
OUTLINE_WARN_WIDTH = 0.2
OUTLINE_WIDTH_RE = re.compile(
    r"_OutlineWidth:\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)")
_OUTLINE_WIDTH_CACHE: dict[str, float | None] = {}


def _outline_width(material_path: Path) -> float | None:
    key = material_path.as_posix()
    if key not in _OUTLINE_WIDTH_CACHE:
        width: float | None = None
        try:
            match = OUTLINE_WIDTH_RE.search(
                material_path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            match = None
        if match:
            try:
                width = float(match.group(1))
            except ValueError:
                width = None
        _OUTLINE_WIDTH_CACHE[key] = width
    return _OUTLINE_WIDTH_CACHE[key]


PAGE_ROOT_COMPONENTS = {"surface.panel", "surface.modal"}
SURFACE_VALUES = {"fullscreen", "modal", "hud"}
BG_TEXTURE_DENYLIST = ("jh_frame_08",)


def _children_by_name(node: dict) -> dict[str, dict]:
    result: dict[str, dict] = {}
    children = node.get("children", [])
    if not isinstance(children, list):
        return result
    for child in children:
        if not isinstance(child, dict):
            continue
        name = child.get("name")
        if isinstance(name, str) and name and name not in result:
            result[name] = child
    return result


def _check_bg_resource(node: dict, label: str, path: str, errors: list[str]) -> None:
    texture = node.get("texture")
    sprite = node.get("sprite")
    if not texture and not sprite:
        errors.append(
            f"{path}: {label} 必须显式写 texture 或 sprite，不能依赖配方默认占位图"
        )
        return
    for value in (texture, sprite):
        if isinstance(value, str) and any(token in value for token in BG_TEXTURE_DENYLIST):
            errors.append(
                f"{path}: {label} 使用了装饰框 {value}，不能作为背景/窗框"
            )


def _check_surface_contract(data: dict, errors: list[str]) -> None:
    if not isinstance(data, dict) or data.get("component") not in PAGE_ROOT_COMPONENTS:
        return
    children = _children_by_name(data)
    surface = data.get("surface")
    if surface is None:
        surface = "modal" if "Window" in children else ("fullscreen" if "Bg" in children else "hud")
    elif surface not in SURFACE_VALUES:
        errors.append(f"root: surface={surface!r} 非法，允许 {sorted(SURFACE_VALUES)}")
        return

    bg = children.get("Bg")
    window = children.get("Window")

    if surface == "modal":
        if bg is not None:
            errors.append("root: modal 根节点禁止整屏 Bg；背景由自动 Screen 提供，窗框放在 Window 下")
        if window is None:
            errors.append("root: modal 缺少 Window 节点")
            return
        window_children = _children_by_name(window)
        window_bg = window_children.get("WindowBg") or window_children.get("Bg")
        if window_bg is None:
            errors.append("root/Window: modal 的 Window 下缺少 WindowBg/Bg 窗框节点")
        else:
            _check_bg_resource(window_bg, "WindowBg", "root/Window/WindowBg", errors)
        return

    if surface == "fullscreen":
        if bg is None:
            errors.append("root: fullscreen 根节点缺少 Bg 全屏背景")
        else:
            _check_bg_resource(bg, "Bg", "root/Bg", errors)
        if window is not None:
            errors.append("root: fullscreen 根节点不应有 Window")
        return

    if bg is not None:
        errors.append("root: hud 根节点不应有 Bg")
    if window is not None:
        errors.append("root: hud 根节点不应有 Window")


def validate_layout_json(json_path: Path, project_root: Path | None = None,
                         warnings: list[str] | None = None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    warning_sink = warnings if warnings is not None else []
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
                    "imageType", "texture", "role", "tag", "surface"):
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

        for key in ("color", "imageColor", "outlineColor"):
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

        font_material = node.get("fontMaterial")
        if (project_root is not None and isinstance(font_material, str)
                and font_material.startswith(FONT_ROOT) and "outlineColor" not in node):
            width = _outline_width(project_root / font_material.replace("\\", "/"))
            if width is not None and width >= OUTLINE_WARN_WIDTH:
                message = (
                    f"{path}: 字体材质 {Path(font_material).name} 的 "
                    f"_OutlineWidth={width:g}，必须同时写 outlineColor"
                    f"（TSX 用 data-outline-color），否则渲染成材质默认的白色粗描边，字内孔会糊死"
                )
                if width >= OUTLINE_ERROR_WIDTH:
                    errors.append(message)
                else:
                    warning_sink.append(message)

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
    _check_surface_contract(data, errors)
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
                        help="Unity 项目根目录；提供时校验 font/fontMaterial/sprite/texture 真实存在，"
                             "并读取材质 _OutlineWidth 校验粗描边材质必须带 outlineColor")
    args = parser.parse_args()
    warnings: list[str] = []
    ok, errors = validate_layout_json(args.layout, project_root=args.project_root,
                                      warnings=warnings)
    for warning in warnings:
        print(f"警告: {warning}", file=sys.stderr)
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
