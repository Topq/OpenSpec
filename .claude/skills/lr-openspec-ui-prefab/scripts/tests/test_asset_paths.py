"""Asset existence checks for layout JSON.

Wrong-directory asset paths used to pass the Python gate and only fail (or
get silently auto-fixed) inside Unity. When a Unity project root is supplied,
the gate now rejects paths that do not exist on disk.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from validate_layout_json import validate_layout_json


class AssetPathValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "Assets/Resources/Font").mkdir(parents=True)
        (self.root / "Assets/UI/Texture").mkdir(parents=True)
        (self.root / "Assets/UI/Atlas").mkdir(parents=True)
        (self.root / "Assets/Resources/Font/ok.asset").write_text("x", encoding="utf-8")
        (self.root / "Assets/UI/Texture/ok.png").write_text("x", encoding="utf-8")
        (self.root / "Assets/UI/Atlas/ok.png").write_text("x", encoding="utf-8")

    def write_layout(self, paths: dict) -> Path:
        layout = {
            "name": "Page",
            "component": "surface.page",
            "children": [
                {
                    "name": "Title",
                    "component": "text.localized",
                    "font": paths["font"],
                    "fontMaterial": paths["fontMaterial"],
                },
                {
                    "name": "Bg",
                    "component": "content.async-image",
                    "texture": paths["texture"],
                },
                {
                    "name": "ButtonBg",
                    "component": "content.background",
                    "sprite": paths["sprite"],
                },
            ],
        }
        path = self.root / "layout.json"
        path.write_text(json.dumps(layout), encoding="utf-8")
        return path

    def valid_paths(self) -> dict:
        return {
            "font": "Assets/Resources/Font/ok.asset",
            "fontMaterial": "Assets/Resources/Font/ok.asset",
            "texture": "Assets/UI/Texture/ok.png",
            "sprite": "Assets/UI/Atlas/ok.png",
        }

    def test_existing_assets_pass_with_project_root(self):
        path = self.write_layout(self.valid_paths())
        ok, errors = validate_layout_json(path, project_root=self.root)
        self.assertTrue(ok, errors)

    def test_missing_assets_fail_with_project_root(self):
        paths = {
            "font": "Assets/Resources/Fonts/ok.asset",
            "fontMaterial": "Assets/Resources/Fonts/ok.asset",
            "texture": "Assets/UI/Textures/ok.png",
            "sprite": "Assets/UI/AtlasResources/ok.png",
        }
        path = self.write_layout(paths)
        ok, errors = validate_layout_json(path, project_root=self.root)
        self.assertFalse(ok)
        self.assertTrue(any("font" in error and "不存在" in error for error in errors), errors)
        self.assertTrue(any("texture" in error and "不存在" in error for error in errors), errors)
        self.assertTrue(any("sprite" in error and "不存在" in error for error in errors), errors)

    def test_without_project_root_keeps_prefix_only_behavior(self):
        path = self.write_layout(self.valid_paths())
        ok, errors = validate_layout_json(path)
        self.assertTrue(ok, errors)

    def test_invalid_project_root_is_rejected(self):
        path = self.write_layout(self.valid_paths())
        ok, errors = validate_layout_json(path, project_root=self.root / "NotUnity")
        self.assertFalse(ok)
        self.assertTrue(any("Unity 项目根" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
