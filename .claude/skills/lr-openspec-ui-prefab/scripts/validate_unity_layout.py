#!/usr/bin/env python3
"""Validate Unity-layout TSX files against unity-layout-attributes.md.

Usage:
  python validate_unity_layout.py <tsx-file-or-dir> [--csharp <script.cs> ...]

Checks performed (see references/unity-layout-attributes.md):
  - TSX parses without error
  - every data-component / data-prefab-child-path / data-prefab-asset-path
    tag has a stable data-name
  - data-component values are in the unity-ui-components.md whitelist
  - data-prefab-child-path / data-prefab-asset-path tags do not also carry
    data-component
  - required data-pos / data-size present and parse as numeric tuples on
    every data-component tag (prefab-child-path tags are exempt: they edit
    an existing node, not create one)
  - data-text-align / data-vertical-align use allowed enum values; either may
    be supplied alone (the generator preserves the other axis)
  - data-lr-style points at an existing {component}-{style}.json variant
  - data-role name is a known profile role and its target matches the role
    (text roles need a TMP target, button roles need control.button, frame
    needs RawImage, screen must be named Screen/Scene)
  - data-texture is only valid on a RawImage target and stays under Assets/
  - style overrides have a consumable target: text attrs need a TMP on the
    node or its single direct TMP child; image attrs need Image (RawImage
    only accepts data-image-color)
  - data-font/data-font-material stay under Assets/Resources/Font/,
    data-sprite stays under Assets/, colors are four 0..1 components,
    data-image-type is a valid Image.Type, data-preserve-aspect is bool
  - no `style=` attribute anywhere
  - child rects stay inside parent rects (best-effort, skipped when parent
    has no usable data-pos/data-size, e.g. layout-group children)
  - sibling rects don't overlap incoherently (skipped under
    data-layout-group parents)
  - field completeness: every *bindable* [SerializeField] in the given C#
    file(s) has a matching data-field in the TSX (hard error, not a warning).
    "Bindable" is what lr_ui_gen/LRFieldBinder.cs can actually assign through
    reflection -- see NON_BINDABLE_TYPES below. Array fields bind per element
    with data-field="m_X[0]", "m_X[1]", ... (the syntax FieldBinder
    documents), so an array field needs >= 1 indexed binding rather than
    exactly one bare name. An explicit binding to an unbindable value type,
    data class or generic collection is rejected. Static recipe checks do not
    replace MCP checks of existing prefab contents and custom inheritance.

Nested MonoBehaviour scopes (data-lr-component):
  A single TSX file may describe more than one script's fields when it
  embeds a reusable MonoBehaviour component inline (e.g. a Page that embeds
  a Row template which itself embeds two Cell instances). Each such nested
  component is marked with `data-lr-component="Namespace.ClassName"` on its
  root node; every `data-field` inside that subtree (until a deeper
  data-lr-component takes over) is scoped to that class, not to the
  page-level script. Field-completeness is checked per scope: a --csharp
  file whose class name is referenced by some data-lr-component in the TSX
  is checked against that scope; a --csharp file never referenced that way
  is treated as the implicit root/page scope. This lets two sibling Cell
  instances each have their own `m_BtnClaim` etc. without colliding.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

if __name__ == "__main__" and sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tsx_layout_common import (  # noqa: E402
    TSXNode,
    TSXParseError,
    iter_layout_nodes,
    parse_number_tuple,
    parse_tsx,
)

from layout_contract import ENUM_VALUES
from style_profile_contract import STYLE_ROLES
CANVAS_SIZE = (1920, 1080)
IMAGE_TYPE_VALUES = {"Simple", "Sliced", "Tiled", "Filled"}
FONT_ROOT = "Assets/Resources/Font/"
TEXT_STYLE_ATTRS = (
    "data-font-size", "data-color", "data-font", "data-font-material",
    "data-text-align", "data-vertical-align",
)
IMAGE_STYLE_ATTRS = (
    "data-sprite", "data-image-type", "data-image-color", "data-preserve-aspect",
)

CATALOG_ROW_PATTERN = re.compile(r"^\|\s*`([^`]+)`\s*\|")
SEMANTIC_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+$")
# One [SerializeField] declaration, capturing declared type + field name.
# Both declaration styles in this project must work:
#     [SerializeField] private Button m_BtnClose;      (attribute and field on one line)
#     [SerializeField]
#     Transform m_HeadIconRoot;                        (attribute on its own line)
# A trailing initializer (m_Level = 1;) is allowed and ignored.
SERIALIZE_FIELD_PATTERN = re.compile(
    r"(?P<attrs>(?:\[[^\[\]]*\]\s*)+)"
    r"(?:(?:public|private|protected|internal|static|readonly|volatile)[ \t]+)*"
    r"(?P<ftype>[A-Za-z_][\w<>,.\[\]]*(?:[ \t]+[A-Za-z_][\w<>,.\[\]]*)*?)[ \t]+"
    r"(?P<name>[A-Za-z_]\w*)[ \t]*(?:=[^;\n]*)?;"
)
C_SHARP_TRIVIA = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|@"(?:""|[^"])*"|"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27')
SERIALIZE_ATTRIBUTE = re.compile(r"(?:^|[\[,\s])(?:UnityEngine\.)?SerializeField(?:Attribute)?(?=\s*[,\]])")
CLASS_NAME_PATTERN = re.compile(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)")

# A plain [System.Serializable] class (e.g. GodFortTalentShapeView) is a
# value-like data holder, not a UnityEngine.Object reference, so FieldBinder
# cannot produce a value for it. Those types are exempt from completeness.
SERIALIZABLE_CLASS_PATTERN = re.compile(
    r"\[(?:System\.)?Serializable\][^\n]*\r?\n[ \t]*"
    r"(?:(?:public|private|protected|internal)[ \t]+)*"
    r"(?:(?:sealed|abstract|partial|static)[ \t]+)*class[ \t]+([A-Za-z_][A-Za-z0-9_]*)"
)

# Types FieldBinder.ResolveValue can never satisfy: it returns a value only for
# GameObject, Transform/RectTransform, or a Component found via GetComponent.
NON_BINDABLE_TYPES = {
    "bool", "byte", "sbyte", "char", "decimal", "double", "float",
    "int", "uint", "long", "ulong", "short", "ushort", "string",
    "Color", "Color32", "Vector2", "Vector3", "Vector4", "Vector2Int", "Vector3Int",
    "Quaternion", "Rect", "RectInt", "Bounds", "LayerMask", "AnimationCurve", "Gradient", "Object",
}

ARRAY_INDEX_PATTERN = re.compile(r"\[\d*\]$")


class Scope:
    """Field-binding scope for one MonoBehaviour instance inside a TSX tree.

    The implicit root scope (component_type=None) covers every data-field
    that is not nested inside a data-lr-component subtree -- this is the
    page-level script attached to the TSX's own root node. Each node that
    carries data-lr-component="Namespace.ClassName" opens a *new* scope for
    its descendants (see module docstring), so e.g. two sibling Cell
    instances each get their own independent field_hits bucket even though
    both are the same C# class.
    """

    def __init__(self, component_type: str | None, label: str) -> None:
        self.component_type = component_type
        self.label = label
        self.field_hits: dict[str, list[tuple[str, str]]] = {}
        self.field_nodes: dict[str, list[TSXNode]] = {}


def load_component_catalog(path: Path) -> set[str]:
    if not path.is_file():
        raise ValueError(f"组件白名单不存在: {path}")
    ids = {
        match.group(1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if (match := CATALOG_ROW_PATTERN.match(line)) and SEMANTIC_ID_PATTERN.fullmatch(match.group(1))
    }
    if not ids:
        raise ValueError(f"组件白名单中没有可用语义 ID: {path}")
    return ids


def extract_serialized_fields(csharp_path: Path) -> list[tuple[str, str, bool]]:
    """Return (field_name, element_type, is_array) for every [SerializeField].

    element_type has any [] stripped, so "Button[]" -> ("m_Btn", "Button", True).
    """
    try:
        text = csharp_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"无法读取 {csharp_path}: {exc}") from exc

    fields: list[tuple[str, str, bool]] = []
    # Mask strings/comments before matching attributes: examples and brackets
    # inside Header strings must not become declarations or break the matcher.
    text = C_SHARP_TRIVIA.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), text)
    for match in SERIALIZE_FIELD_PATTERN.finditer(text):
        if not SERIALIZE_ATTRIBUTE.search(match.group("attrs")):
            continue
        declared = match.group("ftype").replace(" ", "")
        is_array = declared.endswith("[]")
        element_type = declared[:-2] if is_array else declared
        fields.append((match.group("name"), element_type, is_array))
    return fields


def is_bindable(element_type: str, data_classes: set[str]) -> bool:
    """Whether FieldBinder can assign this field type at all."""
    short_type = element_type.rsplit(".", 1)[-1]
    return ("<" not in element_type and "[" not in element_type
            and short_type not in NON_BINDABLE_TYPES and short_type not in data_classes)


def extract_class_name(csharp_path: Path) -> str | None:
    """Best-effort: first `class Foo` declaration in the file. Used to match
    a --csharp file against a data-lr-component="Namespace.Foo" scope by
    its trailing segment (the TSX side doesn't know the C# namespace).
    """
    try:
        text = csharp_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    match = CLASS_NAME_PATTERN.search(text)
    return match.group(1) if match else None


def resolve_anchors(node: TSXNode) -> tuple[tuple[float, float], tuple[float, float]] | None:
    anchors = node.attr("data-anchors")
    if anchors:
        vals = parse_number_tuple(anchors)
        return (vals[0], vals[1]), (vals[2], vals[3])
    amin_attr = node.attr("data-anchor-min")
    amax_attr = node.attr("data-anchor-max")
    if amin_attr and amax_attr:
        amin = parse_number_tuple(amin_attr)[:2]
        amax = parse_number_tuple(amax_attr)[:2]
        return (amin[0], amin[1]), (amax[0], amax[1])
    return None


def rect_of(
    node: TSXNode,
    parent_rect: tuple[float, float, float, float] | None,
) -> tuple[float, float, float, float] | None:
    """Return (min_x, min_y, max_x, max_y) in absolute (canvas) space.

    Unity's anchoredPosition (data-pos) is relative to the anchor point
    *inside the parent's rect*, not an absolute canvas coordinate -- so this
    must resolve top-down through the parent chain, not treat data-pos as
    already-absolute. Point anchors (anchorMin == anchorMax) are computed
    exactly. Stretch anchors (anchorMin != anchorMax) are not precisely
    modeled here (Unity's offsetMin/offsetMax <-> anchoredPosition/sizeDelta
    relationship needs the anchor rect as a reference) -- callers get None
    for those and both containment and sibling-overlap checks are skipped
    for that node, rather than risk a wrong result.
    """

    pos = node.attr("data-pos")
    size = node.attr("data-size")
    if not pos or not size:
        return None
    try:
        px, py = parse_number_tuple(pos)[:2]
        sw, sh = parse_number_tuple(size)[:2]
        pivot_attr = node.attr("data-pivot")
        pivot = tuple(parse_number_tuple(pivot_attr)[:2]) if pivot_attr else (0.5, 0.5)
        anchors = resolve_anchors(node)
    except TSXParseError:
        return None

    sw, sh = abs(sw), abs(sh)
    amin, amax = anchors if anchors is not None else ((0.5, 0.5), (0.5, 0.5))
    if amin[0] != amax[0] or amin[1] != amax[1]:
        return None  # stretch anchor: not precisely modeled, see docstring

    if parent_rect is None:
        # Root node: data-pos is the canvas-space center of the root rect.
        x0, y0 = px - sw / 2, py - sh / 2
        return (x0, y0, x0 + sw, y0 + sh)

    ppx0, ppy0, ppx1, ppy1 = parent_rect
    parent_w, parent_h = ppx1 - ppx0, ppy1 - ppy0
    anchor_x = ppx0 + amin[0] * parent_w
    anchor_y = ppy0 + amin[1] * parent_h
    pivot_x = anchor_x + px
    pivot_y = anchor_y + py
    x0 = pivot_x - pivot[0] * sw
    y0 = pivot_y - pivot[1] * sh
    return (x0, y0, x0 + sw, y0 + sh)


def rects_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


def rect_contains(parent: tuple[float, float, float, float], child: tuple[float, float, float, float]) -> bool:
    px0, py0, px1, py1 = parent
    cx0, cy0, cx1, cy1 = child
    return px0 <= cx0 and py0 <= cy0 <= cy1 <= py1 and cx1 <= px1


def validate_file(tsx_path: Path, catalog: set[str], errors: list[str], scopes: list[Scope]) -> None:
    try:
        root = parse_tsx(tsx_path)
    except TSXParseError as exc:
        errors.append(str(exc))
        return

    # data-name uniqueness is scoped per data-lr-component instance, not
    # global to the file: two sibling Cell instances (e.g. FreeCell/PayCell)
    # legitimately both have a child named "BtnClaim" -- Unity allows two
    # GameObjects with the same name under different parents. Only names
    # within the *same* scope (page root, or one Row/Cell instance) must be
    # unique, matching what actually matters for FindDescendantByName in the
    # generator (it searches within one instantiated subtree at a time).
    seen_names_by_scope: dict[int, dict[str, tuple[int, int]]] = {}
    root_scope = Scope(component_type=None, label=f"{tsx_path} (root/page)")
    scopes.append(root_scope)

    def loc(node: TSXNode) -> str:
        return f"{tsx_path}:{node.line}:{node.column}"

    def walk(node: TSXNode, own_rect: tuple[float, float, float, float] | None, scope: Scope) -> None:
        """Recurse through node's subtree. `own_rect` is node's own absolute
        rect (already resolved by the caller against node's ancestor chain);
        it is used as the parent rect for containment/overlap checks among
        node's direct children, then each child's own absolute rect is
        resolved here (needs own_rect, since data-pos is anchor-relative) and
        passed down for the next recursion level. `scope` is the field-binding
        scope that a data-field on *this* node's direct children belongs to.
        """

        children_relevant = [c for c in node.children if c.is_layout_relevant()]
        own_layout_group = node.attr("data-layout-group") is not None
        child_rects: dict[int, tuple[float, float, float, float] | None] = {}

        for child in node.children:
            if "style" in child.attrs:
                errors.append(f"{loc(child)} <{child.tag}> 不允许 style 属性，布局只能用 data-* 表达")

            child_rect = rect_of(child, own_rect) if child.is_layout_relevant() else own_rect
            child_rects[id(child)] = child_rect

            if child.is_layout_relevant():
                # A data-field on `child` itself is bound to the *current*
                # scope (the MonoBehaviour whose subtree `child` lives in),
                # even if `child` also opens a new scope for its own
                # descendants below.
                validate_node(child, scope)

                if own_rect is not None and not own_layout_group and child_rect is not None:
                    if not rect_contains(own_rect, child_rect):
                        errors.append(
                            f"{loc(child)} <{child.tag} data-name={child.attr('data-name')}> 超出父节点边界"
                            f"（父节点 data-name={node.attr('data-name')}）"
                        )

            child_scope = scope
            lr_component = child.attr("data-lr-component")
            if lr_component:
                child_scope = Scope(
                    component_type=lr_component,
                    label=f"{tsx_path}:{child.line} data-name={child.attr('data-name')} ({lr_component})",
                )
                scopes.append(child_scope)

            walk(child, child_rect, child_scope)

        if not own_layout_group and len(children_relevant) > 1:
            # data-visible="false" nodes are intentional state-alternates
            # (e.g. a "claimed" mark stacked over its "claim button"
            # sibling) -- see unity-layout-attributes.md field-completeness
            # section. They are expected to overlap their visible
            # counterpart and are exempt from the sibling-overlap check.
            rects = [
                (c, child_rects.get(id(c)))
                for c in children_relevant
                if c.attr("data-visible") != "false" and c.attr("data-overlay") != "true"
            ]
            for i in range(len(rects)):
                node_i, rect_i = rects[i]
                if rect_i is None:
                    continue
                for j in range(i + 1, len(rects)):
                    node_j, rect_j = rects[j]
                    if rect_j is None:
                        continue
                    if rects_overlap(rect_i, rect_j):
                        errors.append(
                            f"{loc(node_i)} <{node_i.tag} data-name={node_i.attr('data-name')}> "
                            f"与 {loc(node_j)} <{node_j.tag} data-name={node_j.attr('data-name')}> 兄弟节点重叠，"
                            f"且父节点未声明 data-layout-group"
                        )

    def validate_node(node: TSXNode, scope: Scope) -> None:
        has_component = node.has_component()
        has_child_path = node.has_prefab_child_path()
        has_asset_path = node.has_prefab_asset_path()

        if has_component and (has_child_path or has_asset_path):
            errors.append(f"{loc(node)} <{node.tag}> data-component 不能与 data-prefab-child-path/data-prefab-asset-path 同时出现")

        name = node.attr("data-name")
        # Bucketed by the *identity* of `scope` -- the scope this node's
        # data-field (if any) belongs to, which is also the scope of the
        # MonoBehaviour instance this node lives directly under. Two Cell
        # instances get two distinct Scope objects (see walk()), so their
        # identically-named internal nodes (BtnClaim, ImgIcon, ...) land in
        # separate buckets and don't collide -- matching Unity, where two
        # GameObjects named "BtnClaim" under different parents are fine.
        seen_names = seen_names_by_scope.setdefault(id(scope), {})
        if not name:
            errors.append(f"{loc(node)} <{node.tag}> 缺少稳定的 data-name")
        elif name in seen_names:
            prev_line, prev_col = seen_names[name]
            errors.append(
                f"{loc(node)} <{node.tag}> data-name 重复: {name}（首次出现于 {tsx_path}:{prev_line}:{prev_col}，"
                f"同一作用域 {scope.label}）"
            )
        else:
            seen_names[name] = (node.line, node.column)

        # `data-lr-component` names a C# MonoBehaviour class in TSX (e.g.
        # LR.GodFortTalentCell). In the React prototype stage the same
        # attribute carries a semantic whitelist ID (control.button); when
        # such a value reaches TSX it means prototype markup was copied
        # verbatim -- the semantic ID belongs in data-component instead.
        lr_component = node.attr("data-lr-component")
        if lr_component is not None and lr_component in catalog:
            errors.append(
                f"{loc(node)} <{node.tag} data-name={name}> data-lr-component 的值 {lr_component} 是原型阶段的语义 ID，"
                f"TSX 中应改用 data-component；data-lr-component 只接受 C# 类型名（如 LR.GodFortTalentCell）"
            )

        if has_component:
            component = node.attr("data-component")
            if component not in catalog:
                errors.append(f"{loc(node)} <{node.tag}> 组件不在白名单: {component}")

            pos = node.attr("data-pos")
            size = node.attr("data-size")
            if not pos:
                errors.append(f"{loc(node)} <{node.tag} data-name={name}> 缺少 data-pos")
            else:
                try:
                    parse_number_tuple(pos, str(tsx_path))
                except TSXParseError as exc:
                    errors.append(str(exc))
            if not size:
                errors.append(f"{loc(node)} <{node.tag} data-name={name}> 缺少 data-size")
            else:
                try:
                    parse_number_tuple(size, str(tsx_path))
                except TSXParseError as exc:
                    errors.append(str(exc))

        for attr_name, enum_key in (("data-text-align", "textAlign"), ("data-vertical-align", "verticalAlign"),
                                   ("data-layout-group", "layoutGroup"), ("data-layout-child-alignment", "layoutChildAlignment")):
            value = node.attr(attr_name)
            allowed = ENUM_VALUES[enum_key]
            if value is not None and value not in allowed:
                errors.append(f"{loc(node)} <{node.tag} data-name={name}> {attr_name} 取值非法: {value}（允许: {sorted(allowed)}）")

        component = node.attr("data-component")
        style = node.attr("data-lr-style")
        if style:
            if not component:
                errors.append(f"{loc(node)} <{node.tag} data-name={name}> data-lr-style 只能与 data-component 一起使用")
            else:
                recipes_dir = Path(__file__).resolve().parent / "lr_ui_gen" / "ComponentRecipes"
                if not (recipes_dir / f"{component}-{style}.json").is_file():
                    errors.append(
                        f"{loc(node)} <{node.tag} data-name={name}> data-lr-style=\"{style}\" 没有对应的配方变体 "
                        f"{component}-{style}.json"
                    )

        font_size = node.attr("data-font-size")
        if font_size is not None:
            try:
                parsed_size = float(font_size)
            except ValueError:
                errors.append(f"{loc(node)} <{node.tag} data-name={name}> data-font-size 不是数值: {font_size}")
            else:
                if not math.isfinite(parsed_size) or parsed_size <= 0 or parsed_size > 200:
                    errors.append(
                        f"{loc(node)} <{node.tag} data-name={name}> data-font-size 必须在 (0, 200] 范围内: {font_size}"
                    )

        for color_attr in ("data-color", "data-image-color"):
            color_value = node.attr(color_attr)
            if color_value is None:
                continue
            try:
                color_parts = parse_number_tuple(color_value, str(tsx_path))
            except TSXParseError as exc:
                errors.append(str(exc))
                continue
            if len(color_parts) != 4 or any(not 0 <= value <= 1 for value in color_parts):
                errors.append(
                    f"{loc(node)} <{node.tag} data-name={name}> {color_attr} 必须是 4 个 0..1 的数值: {color_value}"
                )

        image_type = node.attr("data-image-type")
        if image_type is not None and image_type not in IMAGE_TYPE_VALUES:
            errors.append(
                f"{loc(node)} <{node.tag} data-name={name}> data-image-type 取值非法: {image_type}"
                f"（允许: {sorted(IMAGE_TYPE_VALUES)}）"
            )

        preserve_aspect = node.attr("data-preserve-aspect")
        if preserve_aspect is not None and preserve_aspect.lower() not in ("true", "false"):
            errors.append(
                f"{loc(node)} <{node.tag} data-name={name}> data-preserve-aspect 必须是 true/false: {preserve_aspect}"
            )

        for attr_name, prefix in (
            ("data-font", FONT_ROOT),
            ("data-font-material", FONT_ROOT),
            ("data-sprite", "Assets/"),
            ("data-texture", "Assets/"),
        ):
            asset_path = node.attr(attr_name)
            if asset_path and not asset_path.startswith(prefix):
                errors.append(
                    f"{loc(node)} <{node.tag} data-name={name}> {attr_name} 必须以 {prefix} 开头: {asset_path}"
                )

        # data-color is primarily the text color, but existing prototypes also
        # use it on Screen mask nodes (where the generator injects the Image)
        # and occasionally on image-only nodes. Resolve it against whichever
        # target exists; data-image-color stays the explicit image form.
        text_overrides = [
            attr_name for attr_name in TEXT_STYLE_ATTRS
            if attr_name != "data-color" and node.attr(attr_name) is not None
        ]
        color_override = node.attr("data-color") is not None
        image_overrides = [attr_name for attr_name in IMAGE_STYLE_ATTRS if node.attr(attr_name) is not None]
        all_style_overrides = text_overrides + (["data-color"] if color_override else []) + image_overrides

        if all_style_overrides and (node.has_prefab_asset_path() or node.has_prefab_child_path()):
            errors.append(
                f"{loc(node)} <{node.tag} data-name={name}> 样式覆盖不能作用于 data-prefab-asset-path/"
                f"data-prefab-child-path 节点；请修改源 Prefab，或在 TSX 中展开该节点"
            )

        text_target = node_has_text_target(node)
        image_target = node_has_image_target(node)
        is_screen_mask = (name or "").strip().lower() in ("screen", "scene")

        role = node.attr("data-role")
        if role:
            if role not in STYLE_ROLES:
                errors.append(
                    f"{loc(node)} <{node.tag} data-name={name}> data-role 取值非法: {role}"
                    f"（允许: {sorted(STYLE_ROLES)}）"
                )
            if node.has_prefab_asset_path() or node.has_prefab_child_path():
                errors.append(
                    f"{loc(node)} <{node.tag} data-name={name}> data-role 不能作用于 "
                    f"data-prefab-asset-path/data-prefab-child-path 节点"
                )
            if role.startswith("button.") and component != "control.button":
                errors.append(
                    f"{loc(node)} <{node.tag} data-name={name}> data-role={role} 需要 data-component=\"control.button\""
                )
            elif role in {"modal.header", "page.title", "body", "price"} and text_target is False:
                errors.append(
                    f"{loc(node)} <{node.tag} data-name={name}> data-role={role} 需要同节点或单个直接子节点的 TextMeshProUGUI"
                )
            elif role == "divider" and image_target not in ("image", None):
                errors.append(
                    f"{loc(node)} <{node.tag} data-name={name}> data-role=divider 需要 Image 组件（例如 content.divider）"
                )
            elif role == "window.frame" and image_target not in ("raw", None):
                errors.append(
                    f"{loc(node)} <{node.tag} data-name={name}> data-role=window.frame 需要 RawImage 组件（例如 content.async-image）"
                )
            elif role == "screen":
                if is_screen_mask is False:
                    errors.append(
                        f"{loc(node)} <{node.tag} data-name={name}> data-role=screen 只能用于名为 Screen/Scene 的遮罩节点"
                    )
                if image_target is False and component not in ("surface.page", "surface.panel"):
                    errors.append(
                        f"{loc(node)} <{node.tag} data-name={name}> data-role=screen 需要 Image 组件或 surface.page/panel 遮罩节点"
                    )

        texture = node.attr("data-texture")
        if texture is not None:
            if image_target == "image":
                errors.append(
                    f"{loc(node)} <{node.tag} data-name={name}> data-texture 只能作用于 RawImage（例如 content.async-image）"
                )
            elif image_target is False:
                errors.append(
                    f"{loc(node)} <{node.tag} data-name={name}> data-texture 需要同节点 RawImage 组件"
                )

        if text_overrides and text_target is False:
            errors.append(
                f"{loc(node)} <{node.tag} data-name={name}> 样式覆盖 {text_overrides} 需要同节点 TextMeshProUGUI，"
                f"或按钮/页签的单个 Text 子节点"
            )

        if color_override and text_target is not True and image_target not in ("image", "raw") and not is_screen_mask:
            errors.append(
                f"{loc(node)} <{node.tag} data-name={name}> data-color 需要同节点 TextMeshProUGUI、"
                f"Image/RawImage，或 Screen 遮罩节点"
            )

        if image_overrides:
            if image_target is False:
                errors.append(
                    f"{loc(node)} <{node.tag} data-name={name}> 样式覆盖 {image_overrides} 需要同节点 Image 或 RawImage 组件"
                )
            elif image_target == "raw":
                unsupported = [attr_name for attr_name in image_overrides if attr_name != "data-image-color"]
                if unsupported:
                    errors.append(
                        f"{loc(node)} <{node.tag} data-name={name}> RawImage 节点只支持 data-image-color，"
                        f"不支持 {unsupported}"
                    )

        field = node.attr("data-field")
        if field:
            # Keyed by *base* name so array element bindings (m_Cells[0],
            # m_Cells[1], ...) aggregate onto the field they belong to, which
            # is exactly what FieldBinder's "m_X[i]" syntax addresses. A
            # comma-separated list binds several fields at once (also a
            # documented FieldBinder feature).
            for raw in (part.strip() for part in field.split(",")):
                if not raw:
                    continue
                scope.field_hits.setdefault(ARRAY_INDEX_PATTERN.sub("", raw), []).append(
                    (raw, f"{tsx_path}:{node.line} (data-name={name})")
                )
                scope.field_nodes.setdefault(ARRAY_INDEX_PATTERN.sub("", raw), []).append(node)

    walk(root, None, root_scope)

    # Only full-screen root panels are pinned to the 1920x1080 canvas.
    # Cell/template files (e.g. a reward-cell prefab) have their own root
    # component (template.reward-cell, template.tab-item, ...) sized to the
    # cell's own dimensions, not the screen -- exempt those.
    FULLSCREEN_ROOT_COMPONENTS = {"surface.panel", "surface.modal"}
    root_component = next(iter(c for c in root.children if c.is_layout_relevant()), None)
    if root_component is not None and root_component.attr("data-component") in FULLSCREEN_ROOT_COMPONENTS:
        size = root_component.attr("data-size")
        if size:
            try:
                w, h = parse_number_tuple(size)[:2]
                if (w, h) != CANVAS_SIZE:
                    errors.append(
                        f"{tsx_path}: 根节点 data-size={size} 不是 {CANVAS_SIZE[0]}x{CANVAS_SIZE[1]} 画布尺寸"
                    )
            except TSXParseError:
                pass  # already reported above


def _format_hits(hits: list[tuple[str, str]]) -> str:
    return ", ".join(f"{raw} @ {loc}" for raw, loc in hits)


# Static assignability for the built-in types supplied by SE recipes. Custom
# inheritance and prefab references still require the MCP serialized check.
COMPONENT_BASES = {
    "LR.SingleScrollView": "LR.ScrollView",
    "LR.ScrollView": "UnityEngine.UI.ScrollRect",
    "UnityEngine.UI.ScrollRect": "UnityEngine.EventSystems.UIBehaviour",
    "UnityEngine.UI.Scrollbar": "UnityEngine.UI.Selectable",
    "UnityEngine.UI.HorizontalLayoutGroup": "UnityEngine.UI.HorizontalOrVerticalLayoutGroup",
    "UnityEngine.UI.VerticalLayoutGroup": "UnityEngine.UI.HorizontalOrVerticalLayoutGroup",
    "UnityEngine.UI.HorizontalOrVerticalLayoutGroup": "UnityEngine.UI.LayoutGroup",
    "UnityEngine.UI.LayoutGroup": "UnityEngine.EventSystems.UIBehaviour",
    "UnityEngine.UI.Button": "UnityEngine.UI.Selectable",
    "UnityEngine.UI.Toggle": "UnityEngine.UI.Selectable",
    "UnityEngine.UI.Slider": "UnityEngine.UI.Selectable",
    "UnityEngine.UI.InputField": "UnityEngine.UI.Selectable",
    "TMPro.TMP_InputField": "UnityEngine.UI.Selectable",
    "UnityEngine.UI.Selectable": "UnityEngine.EventSystems.UIBehaviour",
    "TMPro.TextMeshProUGUI": "TMPro.TMP_Text",
    "TMPro.TMP_Text": "UnityEngine.UI.MaskableGraphic",
    "UnityEngine.UI.Text": "UnityEngine.UI.MaskableGraphic",
    "UnityEngine.UI.Image": "UnityEngine.UI.MaskableGraphic",
    "UnityEngine.UI.RawImage": "UnityEngine.UI.MaskableGraphic",
    "UnityEngine.UI.MaskableGraphic": "UnityEngine.UI.Graphic",
    "UnityEngine.UI.Graphic": "UnityEngine.EventSystems.UIBehaviour",
    "UnityEngine.EventSystems.UIBehaviour": "UnityEngine.MonoBehaviour",
    "UnityEngine.MonoBehaviour": "UnityEngine.Behaviour",
    "UnityEngine.Canvas": "UnityEngine.Behaviour",
    "UnityEngine.Behaviour": "UnityEngine.Component",
    "UnityEngine.CanvasGroup": "UnityEngine.Component",
    "UnityEngine.RectTransform": "UnityEngine.Transform",
    "UnityEngine.Transform": "UnityEngine.Component",
    "UnityEngine.Component": "UnityEngine.Object",
    "UnityEngine.GameObject": "UnityEngine.Object",
}


def node_supports_type(node: TSXNode, expected: str, custom_bases: dict[str, str]) -> bool | None:
    """Check same-node components, never count a recipe's child hierarchy."""
    # Existing prefab contents cannot be inferred from TSX. The skill requires
    # MCP inspection before reuse and serialized verification after generation.
    if node.has_prefab_asset_path() or node.has_prefab_child_path():
        return True
    available = {"UnityEngine.GameObject", "UnityEngine.RectTransform"}
    component = node.attr("data-component")
    recipes = Path(__file__).resolve().parent / "lr_ui_gen" / "ComponentRecipes"
    style = node.attr("data-lr-style")
    recipe_path = recipes / f"{component}-{style}.json" if style else recipes / f"{component}.json"
    if not recipe_path.is_file():
        recipe_path = recipes / f"{component}.json"
    if recipe_path.is_file():
        recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
        available.add(recipe["componentType"])
        available.update(c["type"] for c in recipe.get("components", []))
        # These hooks create same-node components outside the JSON component
        # list. Keep aligned with LRComponentRecipes; never include children.
        available.update({
            "single-scroll-view": {"LR.SingleScrollView"},
            "grid-scroll-view": {"LR.ScrollView"},
            "input-field": {"TMPro.TMP_InputField", "UnityEngine.UI.Image"},
            "item-slot": {"UnityEngine.UI.Image"},
            "tab-item": {"UnityEngine.UI.Button", "UnityEngine.UI.Image"},
        }.get(recipe.get("postProcess"), set()))
    if node.attr("data-lr-component"):
        available.add(node.attr("data-lr-component"))
    if node.attr("data-layout-group") in ENUM_VALUES["layoutGroup"]:
        available.add("UnityEngine.UI." + node.attr("data-layout-group") + "LayoutGroup")
    bases = {**COMPONENT_BASES, **custom_bases}
    for actual in tuple(available):
        seen = set()
        while actual in bases and actual not in seen:
            seen.add(actual)
            actual = bases[actual]
            available.add(actual)
    expected = expected.removeprefix("global::")
    if expected in available or ("." not in expected and any(t.rsplit(".", 1)[-1] == expected for t in available)):
        return True
    # Even a known expected base (MonoBehaviour, Graphic, ...) can be supplied
    # by a custom subclass whose external ancestor source was not provided.
    # Do not turn lack of that source into evidence of incompatibility.
    for actual in available:
        if actual.startswith(("UnityEngine.", "TMPro.")):
            continue
        visited = set()
        while actual in bases and actual not in visited:
            visited.add(actual)
            actual = bases[actual]
        if not actual.startswith(("UnityEngine.", "TMPro.")):
            return None
    # Built-in types and catalog types have a known contract. For an unknown
    # custom base/interface, defer only if a custom same-node component exists.
    known = set(COMPONENT_BASES) | set(COMPONENT_BASES.values())
    for path in recipes.glob("*.json"):
        recipe = json.loads(path.read_text(encoding="utf-8"))
        known.add(recipe["componentType"])
        known.update(c["type"] for c in recipe.get("components", []))
        for child in recipe.get("hierarchy", []):
            known.update(c["type"] for c in child.get("components", []))
    if expected in known or ("." not in expected and any(t.rsplit(".", 1)[-1] == expected for t in known)):
        return False
    return False


def node_has_text_target(node: TSXNode) -> bool | None:
    """Whether per-node text style overrides have somewhere to land.

    Mirrors LRComponentRecipes.ApplyStyleOverrides: the node itself may carry
    TextMeshProUGUI (text.localized), or a postProcess may create a single
    direct Text/Label child (control.button / template.tab-item), or the TSX
    may declare exactly one direct text.localized child. Prefab references
    cannot be inspected statically -> None (defer to MCP/generator).
    """

    if node.has_prefab_asset_path() or node.has_prefab_child_path():
        return None
    if not node.has_component():
        return False

    supported = node_supports_type(node, "TMPro.TextMeshProUGUI", {})
    if supported is True:
        return True
    if supported is None:
        return None

    component = node.attr("data-component")
    if component == "template.tab-item":
        return True

    text_children = [
        child for child in node.children
        if (child.attr("data-component") or "").startswith("text.localized")
    ]
    if len(text_children) == 1:
        return True

    # PostProcessButton only auto-creates the Text child when the button node
    # has no explicit layout-relevant children and carries button text.
    if component == "control.button" and node.attr("data-text"):
        if not any(child.is_layout_relevant() for child in node.children):
            return True

    return False


def node_has_image_target(node: TSXNode) -> str | bool | None:
    """Return "image", "raw", False, or None (cannot decide statically)."""

    if node.has_prefab_asset_path() or node.has_prefab_child_path():
        return None
    if not node.has_component():
        return False

    image = node_supports_type(node, "UnityEngine.UI.Image", {})
    if image is True:
        return "image"

    raw_image = node_supports_type(node, "UnityEngine.UI.RawImage", {})
    if raw_image is True:
        return "raw"

    if image is None or raw_image is None:
        return None
    return False


def _check_scope_completeness(
    field_hits: dict[str, list[tuple[str, str]]],
    required: dict[str, dict],
    exempt: set[str],
    label: str,
    errors: list[str],
    field_nodes: dict[str, list[TSXNode]],
    runtime_checks: list[str],
) -> None:
    for field_name, info in required.items():
        hits = field_hits.get(field_name, [])
        if not hits:
            errors.append(f"字段绑定缺失: {field_name}（来自 {info['source']}）在 {label} 作用域内没有对应的 data-field")
            continue
        element_type = info["type"]
        if "<" in element_type or "[" in element_type:
            errors.append(f"字段绑定不支持: {field_name} 类型 {element_type}；FieldBinder 仅支持对象引用和一维数组，不支持 List<T>/嵌套集合")
            continue
        for node in field_nodes.get(field_name, []):
            supported = node_supports_type(node, element_type, info["bases"])
            if supported is False:
                errors.append(f"字段绑定类型不匹配: {field_name} 需要 {element_type}，节点 {node.attr('data-name')} 的配方/额外挂载类型不能提供该组件")
            elif supported is None:
                runtime_checks.append(f"需 MCP 验证自定义继承/接口绑定: {label} / {field_name} ({element_type}) -> {node.attr('data-name')}")
        if info["array"]:
            indices = []
            for raw, location in hits:
                match = re.fullmatch(re.escape(field_name) + r"\[(\d+)\]", raw)
                if match is None:
                    errors.append(f"数组字段绑定非法: {raw} 应使用 {field_name}[非负下标]（{location}）")
                else:
                    indices.append(int(match.group(1)))
            if len(indices) != len(set(indices)):
                errors.append(f"数组字段绑定重复: {field_name} 的同一元素被绑定多次: {_format_hits(hits)}")
            if indices and sorted(set(indices)) != list(range(len(set(indices)))):
                errors.append(f"数组字段绑定必须从 0 连续编号: {field_name}，实际下标 {sorted(set(indices))}")
            continue
        if len(hits) > 1:
            errors.append(
                f"字段绑定重复: {field_name} 在 {label} 作用域内多处出现 data-field: {_format_hits(hits)}"
            )
            continue
        if hits[0][0] != field_name:
            errors.append(
                f"字段绑定非法: data-field=\"{hits[0][0]}\" 带数组下标，"
                f"但 {field_name} 不是数组字段（来自 {info['source']}）"
            )

    for field_name, hits in field_hits.items():
        if field_name in exempt:
            errors.append(f"字段绑定不支持: {field_name} 是 FieldBinder 无法赋值的值类型/数据类/集合；不要声明 data-field，集合引用请改用一维组件数组")
            continue
        if field_name in required:
            continue
        errors.append(
            f"字段绑定多余: data-field=\"{hits[0][0]}\" 在 {label} 作用域对应的 C# 脚本中"
            f"找不到对应的 [SerializeField]"
        )


def check_field_completeness(scopes: list[Scope], csharp_files: list[Path], errors: list[str], runtime_checks: list[str] | None = None) -> int:
    """Field-completeness, scoped per nested MonoBehaviour (see module
    docstring on data-lr-component). Returns the total number of data-field
    bindings seen (for the final "N 个字段绑定" summary line).
    """
    if not csharp_files:
        return 0
    if runtime_checks is None:
        runtime_checks = []

    used_component_classes = {
        s.component_type.rsplit(".", 1)[-1] for s in scopes if s.component_type
    }

    # Plain [System.Serializable] classes declared in any provided source are
    # value-like data holders (not UnityEngine.Object references), so fields of
    # those types cannot be bound and are exempt from completeness.
    data_classes: set[str] = set()
    custom_bases: dict[str, str] = {}
    parsed: list[tuple[str | None, list[tuple[str, str, bool]], Path]] = []
    for csharp_path in csharp_files:
        try:
            text = csharp_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ValueError(f"无法读取 {csharp_path}: {exc}") from exc
        data_classes.update(SERIALIZABLE_CLASS_PATTERN.findall(text))
        code = C_SHARP_TRIVIA.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), text)
        namespace = re.search(r"\bnamespace\s+([\w.]+)", code)
        prefix = namespace.group(1) + "." if namespace else ""
        built_in = {name.rsplit(".", 1)[-1]: name for name in COMPONENT_BASES}
        for child, base in re.findall(r"\bclass\s+(\w+)\s*:\s*([\w.]+)", code):
            qualified_base = base if "." in base else built_in.get(base, prefix + base)
            custom_bases[prefix + child] = qualified_base
        parsed.append((extract_class_name(csharp_path), extract_serialized_fields(csharp_path), csharp_path))

    class_required: dict[str, dict[str, dict]] = {}
    root_required: dict[str, dict] = {}
    class_exempt: dict[str, set[str]] = {}
    root_exempt: set[str] = set()
    for class_name, fields, csharp_path in parsed:
        # A class named by some data-lr-component is checked against that
        # nested scope; every other file is the implicit page/root script.
        if class_name and class_name in used_component_classes:
            bucket = class_required.setdefault(class_name, {})
            exempt = class_exempt.setdefault(class_name, set())
        else:
            bucket = root_required
            exempt = root_exempt
        for field_name, element_type, is_array in fields:
            if not is_bindable(element_type, data_classes):
                # No node is required for non-object data. An explicit
                # data-field would be skipped at runtime, so reject that.
                exempt.add(field_name)
                continue
            bucket[field_name] = {"source": str(csharp_path), "array": is_array, "type": element_type, "bases": custom_bases}

    total_hits = 0

    merged_root_hits: dict[str, list[str]] = {}
    merged_root_nodes: dict[str, list[TSXNode]] = {}
    for scope in scopes:
        if scope.component_type is None:
            for field_name, hits in scope.field_hits.items():
                merged_root_hits.setdefault(field_name, []).extend(hits)
            for field_name, nodes in scope.field_nodes.items():
                merged_root_nodes.setdefault(field_name, []).extend(nodes)
    _check_scope_completeness(merged_root_hits, root_required, root_exempt, "根/页面", errors, merged_root_nodes, runtime_checks)
    total_hits += sum(len(hits) for hits in merged_root_hits.values())

    for scope in scopes:
        if scope.component_type is None:
            continue
        class_name = scope.component_type.rsplit(".", 1)[-1]
        required = class_required.get(class_name)
        if required is None:
            # No --csharp file was given for this nested component type;
            # nothing to check it against, but its bindings still count
            # towards the summary total.
            total_hits += sum(len(hits) for hits in scope.field_hits.values())
            continue
        _check_scope_completeness(
            scope.field_hits, required, class_exempt.get(class_name, set()), scope.label, errors, scope.field_nodes, runtime_checks
        )
        total_hits += sum(len(hits) for hits in scope.field_hits.values())

    return total_hits


def find_tsx_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if target.suffix.lower() == ".tsx" else []
    return sorted(p for p in target.rglob("*.tsx") if p.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 Unity 布局 TSX 文件")
    parser.add_argument("target", type=Path, help="TSX 文件或目录")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "lr-design" / "references" / "unity-ui-components.md",
        help="Unity UI 组件白名单文档",
    )
    parser.add_argument(
        "--csharp",
        type=Path,
        action="append",
        default=[],
        help="对应的 C# 脚本路径，用于字段完整性检查（可重复传入）",
    )
    args = parser.parse_args()

    target = args.target.resolve()
    if not target.exists():
        print(f"路径不存在: {target}", file=sys.stderr)
        return 1

    try:
        catalog = load_component_catalog(args.catalog.resolve())
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    tsx_files = find_tsx_files(target)
    if not tsx_files:
        print(f"没有找到 TSX 文件: {target}", file=sys.stderr)
        return 1

    errors: list[str] = []
    scopes: list[Scope] = []
    for tsx_file in tsx_files:
        validate_file(tsx_file, catalog, errors, scopes)

    runtime_checks: list[str] = []
    try:
        total_hits = check_field_completeness(scopes, [p.resolve() for p in args.csharp], errors, runtime_checks)
    except ValueError as exc:
        errors.append(str(exc))
        total_hits = 0

    if errors:
        print(f"校验失败，共 {len(errors)} 项:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"校验通过: {target}（{len(tsx_files)} 个文件，{total_hits} 个字段绑定）")
    for item in runtime_checks:
        print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
