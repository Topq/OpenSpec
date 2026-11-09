"""Node-level style override contract (named style + explicit values)."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import tsx_to_json
import validate_unity_layout as validator
from validate_layout_json import validate_layout_json

CATALOG = {
    "surface.page",
    "text.localized",
    "control.button",
    "content.async-image",
    "content.icon",
}


class StyleOverrideTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, text):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path

    def validate(self, markup, catalog=None):
        path = self.write("Page.tsx", markup)
        errors, scopes = [], []
        validator.validate_file(path, catalog or CATALOG, errors, scopes)
        return errors

    def test_reference_scanner_is_deployable(self):
        scanner = Path(__file__).resolve().parents[1] / "lr_ui_gen" / "LRPrefabReferenceScanner.cs"
        self.assertTrue(scanner.is_file())
        source = scanner.read_text(encoding="utf-8")
        self.assertIn("public static string Scan(string inputJsonPath, string outputJsonPath)", source)
        self.assertIn("PrefabUtility.LoadPrefabContents", source)

    def test_converter_maps_text_and_image_overrides(self):
        path = self.write("Page.tsx", '''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="text.localized" data-name="Title" data-pos="0,0" data-size="200,40"
               data-lr-style="title" data-font-size="28" data-color="(1, 0.84, 0, 1)"
               data-font="Assets/Resources/Font/fzhjtSDF.asset"
               data-font-material="Assets/Resources/Font/fzhjtSDF_UI_TitleLine.mat"
               data-text-align="Center" data-vertical-align="Middle">标题</div>
          <button data-component="control.button" data-name="Claim" data-pos="0,-100" data-size="120,40"
               data-sprite="Assets/UI/AtlasResources/CommonPanel/ty_btn_11.png"
               data-image-type="Sliced" data-image-color="(1,1,1,1)"
               data-preserve-aspect="true" data-text="领取">领取</button>
        </div>
        ''')
        data = tsx_to_json.convert(path)
        title, claim = data["children"]

        self.assertEqual("title", title["textStyle"])
        self.assertEqual(28.0, title["fontSize"])
        self.assertEqual([1.0, 0.84, 0.0, 1.0], title["color"])
        self.assertEqual("Assets/Resources/Font/fzhjtSDF.asset", title["font"])
        self.assertEqual("Assets/Resources/Font/fzhjtSDF_UI_TitleLine.mat", title["fontMaterial"])
        self.assertEqual("Center", title["textAlign"])
        self.assertEqual("Middle", title["verticalAlign"])

        self.assertEqual("Assets/UI/AtlasResources/CommonPanel/ty_btn_11.png", claim["sprite"])
        self.assertEqual("Sliced", claim["imageType"])
        self.assertEqual([1.0, 1.0, 1.0, 1.0], claim["imageColor"])
        self.assertIs(True, claim["preserveAspect"])

    def test_accepts_text_overrides_on_text_and_button(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="text.localized" data-name="Title" data-pos="0,0" data-size="200,40"
               data-lr-style="title" data-font-size="28" data-color="(1,0.84,0,1)"
               data-text-align="Center" data-vertical-align="Middle" />
          <button data-component="control.button" data-name="Claim" data-pos="0,-100" data-size="120,40"
               data-text="领取" data-font-size="24" data-color="(1,1,1,1)" />
        </div>''')
        self.assertEqual([], errors)

    def test_accepts_color_on_screen_mask(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="surface.page" data-name="Screen" data-pos="0,0" data-size="1920,1080"
               data-color="(0, 0, 0, 0.5)"></div>
        </div>''')
        self.assertEqual([], errors)

    def test_accepts_color_as_image_alias(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="content.icon" data-name="Logo" data-pos="0,0" data-size="100,100"
               data-color="(1, 0, 0, 1)" />
        </div>''')
        self.assertEqual([], errors)

    def test_rejects_color_without_any_target(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="surface.page" data-name="Header" data-pos="0,0" data-size="100,100"
               data-color="(1, 0, 0, 1)" />
        </div>''')
        self.assertTrue(any("data-color" in error for error in errors), errors)

    def test_accepts_image_color_on_raw_image(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="content.async-image" data-name="Bg" data-pos="0,0" data-size="400,300"
               data-image-color="(1,1,1,0.5)" />
        </div>''')
        self.assertEqual([], errors)

    def test_rejects_style_override_on_componentless_node(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-name="Cell" data-lr-component="LR.Cell" data-pos="0,0" data-size="100,100"
               data-font-size="24" />
        </div>''')
        self.assertTrue(any("TextMeshProUGUI" in error for error in errors), errors)

    def test_rejects_text_override_without_text_target(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080"
             data-font-size="28" />
        ''')
        self.assertTrue(any("TextMeshProUGUI" in error for error in errors), errors)

    def test_rejects_image_sprite_on_raw_image(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="content.async-image" data-name="Bg" data-pos="0,0" data-size="400,300"
               data-sprite="Assets/UI/a.png" />
        </div>''')
        self.assertTrue(any("RawImage" in error and "data-image-color" in error for error in errors), errors)

    def test_accepts_single_alignment_override(self):
        # Existing prototypes commonly set only data-text-align; the generator
        # preserves the other axis from the recipe/postProcess value.
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="text.localized" data-name="Title" data-pos="0,0" data-size="200,40"
               data-lr-style="title" data-text-align="Left" />
        </div>''')
        self.assertEqual([], errors)

    def test_rejects_unknown_named_style_variant(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="text.localized" data-name="Title" data-pos="0,0" data-size="200,40"
               data-lr-style="missing" />
        </div>''')
        self.assertTrue(any("配方变体" in error for error in errors), errors)

    def test_rejects_font_outside_font_root(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="text.localized" data-name="Title" data-pos="0,0" data-size="200,40"
               data-font="Assets/Other/font.asset" />
        </div>''')
        self.assertTrue(any("data-font" in error and "Assets/Resources/Font/" in error for error in errors), errors)

    def test_rejects_invalid_color_component_range(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="text.localized" data-name="Title" data-pos="0,0" data-size="200,40"
               data-color="(1,2,3,4)" />
        </div>''')
        self.assertTrue(any("0..1" in error for error in errors), errors)

    def test_rejects_invalid_image_type(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <button data-component="control.button" data-name="Claim" data-pos="0,0" data-size="120,40"
               data-image-type="Bogus" />
        </div>''')
        self.assertTrue(any("data-image-type" in error for error in errors), errors)

    def test_rejects_style_override_on_prefab_reference(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-name="Reused" data-prefab-asset-path="Assets/Resources/PanelUI/X.prefab"
               data-pos="0,0" data-size="100,100" data-image-color="(1,1,1,1)" />
        </div>''')
        self.assertTrue(any("prefab-asset-path" in error for error in errors), errors)

    def test_rejects_invalid_preserve_aspect(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <button data-component="control.button" data-name="Claim" data-pos="0,0" data-size="120,40"
               data-preserve-aspect="yes" />
        </div>''')
        self.assertTrue(any("data-preserve-aspect" in error for error in errors), errors)

    def test_json_contract_accepts_style_keys(self):
        data = {
            "name": "Page",
            "component": "surface.page",
            "children": [{
                "name": "Title",
                "component": "text.localized",
                "textStyle": "title",
                "fontSize": 28,
                "color": [1, 0.84, 0, 1],
                "font": "Assets/Resources/Font/fzhjtSDF.asset",
                "fontMaterial": "Assets/Resources/Font/fzhjtSDF_UI_TitleLine.mat",
                "textAlign": "Center",
                "verticalAlign": "Middle",
            }],
        }
        path = self.write("layout.json", json.dumps(data))
        ok, errors = validate_layout_json(path)
        self.assertTrue(ok, errors)

    def test_json_contract_accepts_single_alignment(self):
        data = {
            "name": "Page",
            "component": "surface.page",
            "children": [{
                "name": "Title",
                "component": "text.localized",
                "textAlign": "Left",
            }],
        }
        path = self.write("layout.json", json.dumps(data))
        ok, errors = validate_layout_json(path)
        self.assertTrue(ok, errors)

    def test_json_contract_rejects_bad_style_values(self):
        base = {"name": "Page", "component": "surface.page"}
        cases = [
            {"name": "Title", "component": "text.localized", "fontSize": -1},
            {"name": "Title", "component": "text.localized", "fontSize": "28"},
            {"name": "Title", "component": "text.localized", "color": [1, 2, 3]},
            {"name": "Title", "component": "text.localized", "color": [1, 0, 0, 2]},
            {"name": "Title", "component": "text.localized", "font": "Other/font.asset"},
            {"name": "Title", "component": "text.localized", "textStyle": "missing"},
            {"name": "Title", "textStyle": "title"},
            {"name": "Claim", "component": "control.button", "imageType": "Bogus"},
            {"name": "Claim", "component": "control.button", "preserveAspect": "yes"},
            {"name": "Reused", "prefabAssetPath": "Assets/X.prefab", "imageColor": [1, 1, 1, 1]},
        ]
        for case in cases:
            with self.subTest(case=case):
                data = {**base, "children": [case]}
                path = self.write("layout.json", json.dumps(data))
                self.assertFalse(validate_layout_json(path)[0], case)


if __name__ == "__main__":
    unittest.main()
