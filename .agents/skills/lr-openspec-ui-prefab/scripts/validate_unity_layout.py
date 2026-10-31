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
  - data-text-align / data-vertical-align use allowed enum values
  - no `style=` attribute anywhere
  - child rects stay inside parent rects (best-effort, skipped when parent
    has no usable data-pos/data-size, e.g. layout-group children)
  - sibling rects don't overlap incoherently (skipped under
    data-layout-group parents)
  - field completeness: every [SerializeField] in the given C# file(s) has
    exactly one matching data-field in the TSX (hard error, not a warning)

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
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tsx_layout_common import (  # noqa: E402
    TSXNode,
    TSXParseError,
    iter_layout_nodes,
    parse_number_tuple,
    parse_tsx,
)

TEXT_ALIGN_VALUES = {"Left", "Center", "Right", "Justified"}
VERTICAL_ALIGN_VALUES = {"Top", "Middle", "Bottom"}
CANVAS_SIZE = (1920, 1080)

CATALOG_ROW_PATTERN = re.compile(r"^\|\s*`([^`]+)`\s*\|")
SEMANTIC_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+$")
SERIALIZE_FIELD_PATTERN = re.compile(
    r"\[SerializeField\][^\n]*\n\s*(?:(?:public|private|protected|internal)\s+)?"
    r"[\w<>\[\],. ]+?\s+(m_[A-Za-z0-9_]+)\s*;"
)
CLASS_NAME_PATTERN = re.compile(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)")


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
        self.field_hits: dict[str, list[str]] = {}


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


def extract_serialized_fields(csharp_path: Path) -> list[str]:
    try:
        text = csharp_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"无法读取 {csharp_path}: {exc}") from exc
    return SERIALIZE_FIELD_PATTERN.findall(text)


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

            for attr_name, allowed in (
                ("data-text-align", TEXT_ALIGN_VALUES),
                ("data-vertical-align", VERTICAL_ALIGN_VALUES),
            ):
                value = node.attr(attr_name)
                if value is not None and value not in allowed:
                    errors.append(f"{loc(node)} <{node.tag} data-name={name}> {attr_name} 取值非法: {value}（允许: {sorted(allowed)}）")

        field = node.attr("data-field")
        if field:
            scope.field_hits.setdefault(field, []).append(f"{tsx_path}:{node.line} (data-name={name})")

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


def _check_scope_completeness(
    field_hits: dict[str, list[str]],
    required: dict[str, str],
    label: str,
    errors: list[str],
) -> None:
    for field_name, source in required.items():
        hits = field_hits.get(field_name, [])
        if not hits:
            errors.append(f"字段绑定缺失: {field_name}（来自 {source}）在 {label} 作用域内没有对应的 data-field")
        elif len(hits) > 1:
            errors.append(f"字段绑定重复: {field_name} 在 {label} 作用域内多处出现 data-field: {', '.join(hits)}")

    for field_name in field_hits:
        if field_name not in required:
            errors.append(
                f"字段绑定多余: data-field=\"{field_name}\" 在 {label} 作用域对应的 C# 脚本中找不到对应的 [SerializeField]"
            )


def check_field_completeness(scopes: list[Scope], csharp_files: list[Path], errors: list[str]) -> int:
    """Field-completeness, scoped per nested MonoBehaviour (see module
    docstring on data-lr-component). Returns the total number of data-field
    bindings seen (for the final "N 个字段绑定" summary line).
    """
    if not csharp_files:
        return 0

    used_component_classes = {
        s.component_type.rsplit(".", 1)[-1] for s in scopes if s.component_type
    }

    class_required: dict[str, dict[str, str]] = {}
    root_required: dict[str, str] = {}
    for csharp_path in csharp_files:
        class_name = extract_class_name(csharp_path)
        fields = extract_serialized_fields(csharp_path)
        if class_name and class_name in used_component_classes:
            bucket = class_required.setdefault(class_name, {})
            for field_name in fields:
                bucket[field_name] = str(csharp_path)
        else:
            # Not referenced by any data-lr-component in the TSX: treat as
            # the page/root script (matches the pre-nesting behavior where
            # every --csharp file was checked against one global field set).
            for field_name in fields:
                root_required[field_name] = str(csharp_path)

    total_hits = 0

    merged_root_hits: dict[str, list[str]] = {}
    for scope in scopes:
        if scope.component_type is None:
            for field_name, hits in scope.field_hits.items():
                merged_root_hits.setdefault(field_name, []).extend(hits)
    _check_scope_completeness(merged_root_hits, root_required, "根/页面", errors)
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
        _check_scope_completeness(scope.field_hits, required, scope.label, errors)
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

    try:
        total_hits = check_field_completeness(scopes, [p.resolve() for p in args.csharp], errors)
    except ValueError as exc:
        errors.append(str(exc))
        total_hits = 0

    if errors:
        print(f"校验失败，共 {len(errors)} 项:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"校验通过: {target}（{len(tsx_files)} 个文件，{total_hits} 个字段绑定）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
