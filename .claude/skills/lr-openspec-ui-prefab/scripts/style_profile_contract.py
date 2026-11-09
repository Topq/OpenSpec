#!/usr/bin/env python3
"""Merge role-based UI style defaults from ui-style-profile.json into layout JSON.

The profile is produced by build_ui_style_profile.py from real prefab scans.
It only contributes *visual* properties. Geometry (pos/size/anchors/pivot) is
owned by the TSX and is deliberately ignored here.

Precedence implemented by this module:

    recipe default + postProcess < data-lr-style < profile role < explicit data-*

Only properties the TSX did not set explicitly are filled from the profile.
Every applied value is recorded in the node's ``_styleSources`` map so the
generation report can explain where a style came from.
"""

from __future__ import annotations

from typing import Any

STYLE_ROLES = {
    "modal.header",
    "page.title",
    "body",
    "price",
    "button.primary",
    "button.secondary",
    "button.close",
    "window.frame",
    "divider",
    "screen",
}

TEXT_ROLE_PROPERTIES = {
    "fontSize": "fontSize",
    "color": "color",
    "font": "font",
    "fontMaterial": "fontMaterial",
    "alignment": "textAlign",
}

BUTTON_ROLE_PROPERTIES = {
    "sprite": "sprite",
    "imageType": "imageType",
    "imageColor": "imageColor",
    "textFontSize": "fontSize",
    "textFont": "font",
    "textColor": "color",
    "textMaterial": "fontMaterial",
    "textAlignment": "textAlign",
}

IMAGE_ROLE_PROPERTIES = {
    "sprite": "sprite",
    "imageType": "imageType",
    "color": "imageColor",
}

ROLE_PROPERTY_MAP: dict[str, dict[str, str]] = {
    "modal.header": TEXT_ROLE_PROPERTIES,
    "page.title": TEXT_ROLE_PROPERTIES,
    "body": TEXT_ROLE_PROPERTIES,
    "price": TEXT_ROLE_PROPERTIES,
    "button.primary": BUTTON_ROLE_PROPERTIES,
    "button.secondary": BUTTON_ROLE_PROPERTIES,
    "button.close": BUTTON_ROLE_PROPERTIES,
    "window.frame": {
        "texture": "texture",
        "color": "imageColor",
    },
    "divider": IMAGE_ROLE_PROPERTIES,
    "screen": IMAGE_ROLE_PROPERTIES,
}

# For image roles, data-color is a documented alias for the Image tint. If the
# TSX wrote the alias explicitly, do not overwrite it with the profile value.
ROLE_PROPERTY_ALIASES: dict[tuple[str, str], tuple[str, ...]] = {
    ("window.frame", "color"): ("color",),
    ("divider", "color"): ("color",),
    ("screen", "color"): ("color",),
}

STYLE_KEYS = {
    "fontSize", "color", "font", "fontMaterial", "textAlign", "verticalAlign",
    "sprite", "imageType", "imageColor", "preserveAspect", "texture",
}

GEOMETRY_KEYS = {"pos", "size", "anchors", "anchorMin", "anchorMax", "pivot"}


class StyleProfileError(ValueError):
    """Raised when the profile or a role declaration is structurally invalid."""


def _profile_value(entry: Any) -> Any:
    """Unwrap the {value, count, total} envelope produced by the profiler."""
    if isinstance(entry, dict) and "value" in entry:
        return entry.get("value")
    return entry


def _is_supported_value(value: Any) -> bool:
    return isinstance(value, (str, int, float, list, tuple)) and not isinstance(value, bool)


def _normalize_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_normalize_value(item) for item in value]
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    return value


def _node_label(node: dict[str, Any], path: str) -> str:
    name = node.get("name")
    return f"{path} ({name})" if name else path


def _text_label_child(node: dict[str, Any]) -> dict[str, Any] | None:
    """Return the button's single direct text child, if it has one.

    Text properties of a button role belong on the label, not on the Button
    GameObject. The generator resolves a button's text target only after the
    child exists; keeping the values on the button would either be ignored or
    (with explicit children) rejected. Explicit TSX values on the label still
    win because they are already present on the target.
    """
    children = node.get("children")
    if not isinstance(children, list):
        return None
    labels = [
        child for child in children
        if isinstance(child, dict)
        and isinstance(child.get("component"), str)
        and child["component"].startswith("text.")
    ]
    return labels[0] if len(labels) == 1 else None


def _apply_node(
    node: dict[str, Any],
    path: str,
    roles: dict[str, Any],
    warnings: list[str],
    strict: bool,
) -> None:
    role = node.get("role")
    sources: dict[str, str] = {}

    # Record explicit TSX style values even when a role is missing, so a
    # reviewer can tell "this was intentional" from "the profile was absent".
    for key in STYLE_KEYS:
        # A key may already carry "_styleSources" when a parent button role
        # routed it onto this label child; only unmarked keys are TSX-explicit.
        if key in node and key not in node.get("_styleSources", {}):
            sources[key] = "tsx"

    if role:
        if not isinstance(role, str) or role not in STYLE_ROLES:
            raise StyleProfileError(f"{_node_label(node, path)}: 未知 data-role: {role}")
        role_data = roles.get(role)
        if not isinstance(role_data, dict):
            message = f"{_node_label(node, path)}: profile 中没有角色 {role}，保留 TSX/配方样式"
            if strict:
                raise StyleProfileError(message)
            warnings.append(message)
        else:
            properties = role_data.get("properties")
            if not isinstance(properties, dict):
                warnings.append(f"{_node_label(node, path)}: 角色 {role} 没有 properties，跳过")
            else:
                label = _text_label_child(node) if role.startswith("button.") else None
                for profile_key, target_key in ROLE_PROPERTY_MAP[role].items():
                    if profile_key not in properties:
                        continue
                    value = _profile_value(properties[profile_key])
                    if value is None:
                        continue
                    if not _is_supported_value(value):
                        warnings.append(
                            f"{_node_label(node, path)}: 角色 {role} 的 {profile_key} 值类型不支持，跳过"
                        )
                        continue
                    target = label if label is not None and profile_key.startswith("text") else node
                    if target_key in target:
                        # Explicit TSX value already recorded on the target.
                        continue
                    aliases = ROLE_PROPERTY_ALIASES.get((role, profile_key), ())
                    if any(alias in target for alias in aliases):
                        target.setdefault("_styleSources", {})[target_key] = "tsx"
                        continue
                    target[target_key] = _normalize_value(value)
                    target.setdefault("_styleSources", {})[target_key] = f"profile:{role}"

    if sources:
        # Merge instead of replacing: button-role text properties may already
        # have written profile sources onto this node or its label child.
        node.setdefault("_styleSources", {}).update(sources)

    children = node.get("children")
    if isinstance(children, list):
        for index, child in enumerate(children):
            if isinstance(child, dict):
                _apply_node(child, f"{path}/children[{index}]", roles, warnings, strict)


def apply_style_profile(
    root: dict[str, Any],
    profile: dict[str, Any],
    *,
    strict: bool = False,
) -> list[str]:
    """Fill role defaults into ``root`` in place and return soft warnings."""
    if not isinstance(root, dict):
        raise StyleProfileError("布局根节点必须是对象")
    if not isinstance(profile, dict):
        raise StyleProfileError("profile 必须是 JSON 对象")
    roles = profile.get("roles")
    if not isinstance(roles, dict):
        raise StyleProfileError("profile 缺少 roles 对象")

    root["_styleProfile"] = {
        "module": profile.get("module", ""),
        "generatedAt": profile.get("generatedAt", ""),
        "sources": profile.get("sources", []),
        "roles": sorted(roles.keys()),
    }

    warnings: list[str] = []
    _apply_node(root, "root", roles, warnings, strict)
    return warnings
