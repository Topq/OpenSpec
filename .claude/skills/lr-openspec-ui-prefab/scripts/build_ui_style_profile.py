#!/usr/bin/env python3
"""Build a module-level UI style profile from LRPrefabReferenceScanner output.

The scanner answers "what does this one prefab look like". This script
aggregates several prefabs from the same UI module into role-based style
rules (modal header, body, price, primary/secondary button, window frame,
divider, screen mask) so a new panel can be generated in the project's
existing visual language even when it has no production prefab of its own.

Usage:
  python build_ui_style_profile.py <references.json> \
      [--module WelfareActivityPanel] \
      [-o ui-style-profile.json] \
      [--markdown ui-style-profile.md]
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

if __name__ == "__main__" and sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PRIMARY_BUTTON_PATTERN = re.compile(
    r"(confirm|buy|purchase|claim|send|gift|accept|ok|get|领取|购买|赠送|确认)", re.I
)
SECONDARY_BUTTON_PATTERN = re.compile(r"(cancel|back|no|refuse|取消|返回)", re.I)
CLOSE_BUTTON_PATTERN = re.compile(r"(close|exit|关闭)", re.I)
TITLE_PATTERN = re.compile(r"(txttitle|title|标题)", re.I)
BODY_PATTERN = re.compile(r"(desc|description|content|body|tip|rule|info|说明|描述)", re.I)
PRICE_PATTERN = re.compile(r"(price|cost|money|amount|rmb|价格)", re.I)
LINE_PATTERN = re.compile(r"(line|divider|fgx|分割线)", re.I)
FRAME_PATTERN = re.compile(r"(frame|bg|背景|底框)", re.I)

TEXT_COMPONENT = "TMPro.TextMeshProUGUI"
IMAGE_COMPONENT = "UnityEngine.UI.Image"
RAW_IMAGE_COMPONENT = "UnityEngine.UI.RawImage"
BUTTON_COMPONENT = "UnityEngine.UI.Button"


def components(node: dict) -> list[str]:
    return node.get("components") or []


def has_component(node: dict, type_name: str) -> bool:
    return type_name in components(node)


def is_tmp(node: dict) -> bool:
    return has_component(node, TEXT_COMPONENT)


def is_image(node: dict) -> bool:
    return has_component(node, IMAGE_COMPONENT)


def is_raw_image(node: dict) -> bool:
    return has_component(node, RAW_IMAGE_COMPONENT)


def is_button(node: dict) -> bool:
    return has_component(node, BUTTON_COMPONENT)


def asset_name(path: str | None) -> str:
    return (path or "").split("/")[-1]


def text_of(node: dict) -> dict:
    return node.get("text") or {}


def image_of(node: dict) -> dict:
    return node.get("image") or {}


def raw_image_of(node: dict) -> dict:
    return node.get("rawImage") or {}


def layout_of(node: dict) -> dict:
    return node.get("layout") or {}


def descendants(nodes: list[dict], parent_path: str, max_relative_depth: int = 2):
    parent = next((node for node in nodes if node.get("path") == parent_path), None)
    if parent is None:
        return []
    parent_depth = parent.get("depth", 0)
    prefix = parent_path + "/"
    return [
        node for node in nodes
        if node.get("path", "").startswith(prefix)
        and node.get("depth", 0) - parent_depth <= max_relative_depth
    ]


def button_sample(candidate: dict, node: dict) -> dict:
    nodes = candidate.get("nodes", [])
    children = descendants(nodes, node["path"], max_relative_depth=3)
    graphic = next((child for child in children if is_image(child)), None)
    if graphic is None and is_image(node):
        graphic = node
    text = next((child for child in children if is_tmp(child)), None)
    image = image_of(graphic) if graphic else {}
    text_style = text_of(text) if text else {}
    layout = layout_of(node)
    return {
        "prefab": candidate.get("prefabPath"),
        "path": node.get("path"),
        "name": node.get("name"),
        "size": layout.get("sizeDelta"),
        "anchors": [layout.get("anchorMin"), layout.get("anchorMax")],
        "sprite": image.get("sprite"),
        "imageType": image.get("type"),
        "imageColor": image.get("color"),
        "textFontSize": text_style.get("fontSize"),
        "textFont": text_style.get("font"),
        "textColor": text_style.get("color"),
        "textMaterial": text_style.get("fontMaterial"),
        "textAlignment": text_style.get("alignment"),
    }


def infer_candidate(candidate: dict) -> dict[str, dict]:
    nodes = candidate.get("nodes", [])
    if not nodes:
        return {}

    button_paths = [node["path"] for node in nodes if is_button(node)]
    inside_button = lambda path: any(path == b or path.startswith(b + "/") for b in button_paths)

    def first_text(predicate):
        matches = [
            node for node in nodes
            if is_tmp(node) and not inside_button(node["path"]) and predicate(node)
        ]
        return matches[0] if matches else None

    samples: dict[str, dict] = {}

    # Modal header: usually Bg/Title, TitleBg/Title or Bg/Text, large font.
    header_candidates = [
        node for node in nodes
        if is_tmp(node) and not inside_button(node["path"])
        and text_of(node).get("fontSize", 0) >= 50
        and (
            re.search(r"(^|/)(Bg|TitleBg)/(Title|Text)$", node.get("path", ""))
            or (node.get("name") == "Title" and "RawImage" not in node.get("path", ""))
        )
    ]
    if header_candidates:
        node = max(header_candidates, key=lambda item: text_of(item).get("fontSize", 0))
        samples["modal.header"] = {
            "prefab": candidate.get("prefabPath"),
            "path": node.get("path"),
            **{key: text_of(node).get(key) for key in ("fontSize", "color", "font", "fontMaterial", "alignment")},
        }

    # Page title: TxtTitle/Title under Root, smaller than the modal header.
    title_candidates = [
        node for node in nodes
        if is_tmp(node) and not inside_button(node["path"])
        and TITLE_PATTERN.search(node.get("name", ""))
        and text_of(node).get("fontSize", 0) < 50
    ]
    if title_candidates:
        node = max(title_candidates, key=lambda item: text_of(item).get("fontSize", 0))
        samples["page.title"] = {
            "prefab": candidate.get("prefabPath"),
            "path": node.get("path"),
            **{key: text_of(node).get(key) for key in ("fontSize", "color", "font", "fontMaterial", "alignment")},
        }

    body = first_text(lambda node: BODY_PATTERN.search(node.get("name", ""))
                      or BODY_PATTERN.search(node.get("path", "")))
    if body:
        samples["body"] = {
            "prefab": candidate.get("prefabPath"),
            "path": body.get("path"),
            **{key: text_of(body).get(key) for key in ("fontSize", "color", "font", "fontMaterial", "alignment")},
        }

    price = first_text(lambda node: PRICE_PATTERN.search(node.get("name", ""))
                       or PRICE_PATTERN.search(node.get("path", "")))
    if price is None:
        price = first_text(lambda node: "¥" in (text_of(node).get("text") or "")
                           or "￥" in (text_of(node).get("text") or ""))
    if price:
        samples["price"] = {
            "prefab": candidate.get("prefabPath"),
            "path": price.get("path"),
            **{key: text_of(price).get(key) for key in ("fontSize", "color", "font", "fontMaterial", "alignment")},
        }

    def button_role(pattern, role):
        matches = [
            node for node in nodes
            if is_button(node) and pattern.search(node.get("name", ""))
        ]
        if matches:
            samples[role] = button_sample(candidate, matches[0])

    button_role(CLOSE_BUTTON_PATTERN, "button.close")
    button_role(SECONDARY_BUTTON_PATTERN, "button.secondary")
    button_role(PRIMARY_BUTTON_PATTERN, "button.primary")

    # Window frame: prefer a RawImage under Window whose texture looks like a frame.
    frame_candidates = []
    for node in nodes:
        if not is_raw_image(node) or "Window" not in node.get("path", ""):
            continue
        texture = raw_image_of(node).get("texture")
        if not texture:
            continue
        score = 0
        if FRAME_PATTERN.search(asset_name(texture)):
            score += 2
        if "/Bg" in node.get("path", "") or node.get("path", "").endswith("/Bg"):
            score += 1
        frame_candidates.append((score, node))
    if frame_candidates:
        _, node = max(frame_candidates, key=lambda item: item[0])
        layout = layout_of(node)
        size = layout.get("sizeDelta") or [None, None]
        samples["window.frame"] = {
            "prefab": candidate.get("prefabPath"),
            "path": node.get("path"),
            "texture": raw_image_of(node).get("texture"),
            "width": size[0],
            "height": size[1],
            "color": raw_image_of(node).get("color"),
        }

    # Divider: a line-like sprite, usually Tiled and short.
    for node in nodes:
        if not is_image(node):
            continue
        if "Toggle" in node.get("path", "") or "Tab" in node.get("path", ""):
            continue
        sprite = image_of(node).get("sprite")
        image_type = image_of(node).get("type")
        size = layout_of(node).get("sizeDelta") or [None, None]
        is_line_sprite = bool(
            sprite
            and LINE_PATTERN.search(asset_name(sprite))
            and (image_type == "Tiled" or "line" in (node.get("name", "") or "").lower())
        )
        is_short_tiled = image_type == "Tiled" and size[1] is not None and size[1] <= 16
        if is_line_sprite or is_short_tiled:
            samples["divider"] = {
                "prefab": candidate.get("prefabPath"),
                "path": node.get("path"),
                "sprite": sprite,
                "imageType": image_type,
                "color": image_of(node).get("color"),
                "width": size[0],
                "height": size[1],
            }
            break

    # Screen / Scene mask.
    for node in nodes:
        if not is_image(node) or node.get("name") not in ("Screen", "Scene"):
            continue
        samples["screen"] = {
            "prefab": candidate.get("prefabPath"),
            "path": node.get("path"),
            "sprite": image_of(node).get("sprite"),
            "imageType": image_of(node).get("type"),
            "color": image_of(node).get("color"),
        }
        break

    return samples


def normalize(value):
    """Recursively freeze lists/dicts so nested sizes and colors are hashable."""
    if isinstance(value, (list, tuple)):
        return tuple(normalize(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((key, normalize(item)) for key, item in value.items()))
    if isinstance(value, float):
        return round(value, 6)
    return value


def denormalize(value):
    if isinstance(value, tuple):
        return [denormalize(item) for item in value]
    return value


def aggregate(samples: list[dict], key: str) -> dict | None:
    values = [sample.get(key) for sample in samples if sample.get(key) is not None]
    if not values:
        return None
    counter = Counter(normalize(value) for value in values)
    mode, count = counter.most_common(1)[0]
    result = {
        "value": denormalize(mode),
        "count": count,
        "total": len(values),
        "values": values,
    }
    numeric_values = [value for value in values if isinstance(value, (int, float))]
    if numeric_values:
        result["median"] = statistics.median(numeric_values)
    return result


def build_profile(references: dict, module: str) -> dict:
    candidates = [c for c in references.get("candidates", []) if not c.get("error")]
    per_role: dict[str, list[dict]] = {}
    sources = []
    for candidate in candidates:
        sources.append(candidate.get("prefabPath"))
        for role, sample in infer_candidate(candidate).items():
            per_role.setdefault(role, []).append(sample)

    roles: dict[str, dict] = {}
    for role, samples in sorted(per_role.items()):
        keys = sorted({key for sample in samples for key in sample if key not in ("prefab", "path", "name")})
        roles[role] = {
            "samples": len(samples),
            "properties": {key: aggregate(samples, key) for key in keys},
            "sampleDetails": samples,
        }

    return {
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "module": module,
        "sources": sources,
        "roles": roles,
    }


def markdown(profile: dict) -> str:
    lines = [
        f"# UI Style Profile: {profile['module']}",
        "",
        f"- Generated: {profile['generatedAt']}",
        f"- Sources: {len(profile['sources'])} prefabs",
        "",
        "## Sources",
        "",
    ]
    lines.extend(f"- `{source}`" for source in profile["sources"])
    lines.append("")

    for role, data in profile["roles"].items():
        lines.append(f"## {role}")
        lines.append("")
        lines.append(f"Samples: {data['samples']}")
        lines.append("")
        lines.append("| Property | Chosen | Hits | Values |")
        lines.append("|---|---|---|---|")
        for key, value in data["properties"].items():
            if value is None:
                continue
            chosen = value["value"]
            values = ", ".join(str(item) for item in value["values"][:6])
            lines.append(f"| {key} | `{chosen}` | {value['count']}/{value['total']} | {values} |")
        lines.append("")
        lines.append("Samples:")
        for sample in data["sampleDetails"]:
            lines.append(
                f"- `{sample.get('prefab')}` → `{sample.get('path')}`"
            )
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("references", type=Path, help="LRPrefabReferenceScanner 输出的 references.json")
    parser.add_argument("--module", default="", help="模块名，例如 WelfareActivityPanel")
    parser.add_argument("-o", "--output", type=Path, default=None, help="输出 profile JSON")
    parser.add_argument("--markdown", type=Path, default=None, help="输出人类可读 profile Markdown")
    args = parser.parse_args()

    try:
        references = json.loads(args.references.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"无法读取 references.json: {exc}", file=sys.stderr)
        return 1

    module = args.module or "UI"
    profile = build_profile(references, module)
    if not profile["roles"]:
        print("没有识别到任何 UI 角色，请检查扫描深度或参考 Prefab", file=sys.stderr)
        return 1

    output = args.output or args.references.with_name("ui-style-profile.json")
    output.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成 style profile: {output}")

    if args.markdown:
        args.markdown.write_text(markdown(profile), encoding="utf-8")
        print(f"已生成 style profile Markdown: {args.markdown}")

    for role, data in profile["roles"].items():
        print(f"- {role}: {data['samples']} samples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
