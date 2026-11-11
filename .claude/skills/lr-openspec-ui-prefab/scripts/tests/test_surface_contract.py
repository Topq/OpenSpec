'''Regression tests for the data-surface page-structure contract.'''
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import tsx_to_json
import validate_unity_layout as validator

CATALOG = {"surface.panel", "surface.page", "content.async-image", "content.icon", "text.localized"}


class SurfaceContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def validate(self, markup):
        path = self.root / "Page.tsx"
        path.write_text(markup, encoding="utf-8")
        errors, scopes, warnings = [], [], []
        validator.validate_file(path, CATALOG, errors, scopes, warnings)
        return errors, warnings

    def test_modal_root_bg_is_rejected(self):
        errors, _ = self.validate('''
        <div data-component="surface.panel" data-surface="modal" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="content.async-image" data-name="Bg" data-overlay="true" data-texture="Assets/UI/Texture/bg/sytd_bj03.png" data-pos="0,0" data-size="1920,1080"></div>
          <div data-component="surface.page" data-name="Window" data-pos="0,0" data-size="800,600">
            <div data-component="content.async-image" data-name="WindowBg" data-overlay="true" data-texture="Assets/UI/Texture/decorativeextra/ty_tk_frame_06.png" data-pos="0,0" data-size="800,600"></div>
          </div>
        </div>''')
        self.assertTrue(any("modal 根节点禁止整屏 Bg" in error for error in errors), errors)

    def test_jh_frame_as_background_is_rejected(self):
        errors, _ = self.validate('''
        <div data-component="surface.panel" data-surface="fullscreen" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="content.async-image" data-name="Bg" data-overlay="true" data-texture="Assets/UI/AtlasResources/CommonPanel/jh_frame_08.png" data-pos="0,0" data-size="1920,1080"></div>
        </div>''')
        self.assertTrue(any("装饰框" in error for error in errors), errors)

    def test_fullscreen_without_bg_is_rejected(self):
        errors, _ = self.validate('''
        <div data-component="surface.panel" data-surface="fullscreen" data-name="Page" data-pos="0,0" data-size="1920,1080"></div>''')
        self.assertTrue(any("fullscreen 根节点缺少 Bg" in error for error in errors), errors)

    def test_valid_modal_structure_passes(self):
        errors, _ = self.validate('''
        <div data-component="surface.panel" data-surface="modal" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="surface.page" data-name="Window" data-pos="0,0" data-size="800,600">
            <div data-component="content.async-image" data-name="WindowBg" data-overlay="true" data-texture="Assets/UI/Texture/decorativeextra/ty_tk_frame_06.png" data-pos="0,0" data-size="800,600"></div>
          </div>
        </div>''')
        self.assertEqual([], errors)

    def test_surface_is_carried_into_layout_json(self):
        path = self.root / "Page.tsx"
        path.write_text('''
        <div data-component="surface.panel" data-surface="modal" data-name="Page" data-pos="0,0" data-size="1920,1080"></div>''', encoding="utf-8")
        self.assertEqual("modal", tsx_to_json.convert(path).get("surface"))

    def test_required_classes_include_root_and_nested_component(self):
        path = self.root / "Page.tsx"
        path.write_text('''
        <div data-component="surface.panel" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="surface.page" data-lr-component="LR.Row" data-name="Row" data-pos="0,0" data-size="100,100"></div>
        </div>''', encoding="utf-8")
        root, classes = validator._required_classes(path)
        self.assertEqual("Page", root)
        self.assertEqual({"Page", "Row"}, classes)


if __name__ == "__main__":
    unittest.main()
