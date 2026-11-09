# Role-based style profile materialization and validation.
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
from style_profile_contract import StyleProfileError

CATALOG = {
    "surface.page",
    "surface.panel",
    "text.localized",
    "control.button",
    "content.divider",
    "content.async-image",
}


def role(**properties):
    return {
        "samples": 1,
        "properties": {
            key: {"value": value, "count": 1, "total": 1}
            for key, value in properties.items()
        },
    }


def make_profile(**roles):
    return {
        "module": "TestModule",
        "generatedAt": "2026-11-07 00:00:00",
        "sources": ["Assets/Resources/PanelUI/Test/Ref.prefab"],
        "roles": roles,
    }


class StyleRoleProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, text):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path

    def convert(self, markup, profile):
        tsx = self.write("Page.tsx", markup)
        profile_path = self.write("ui-style-profile.json", json.dumps(profile))
        return tsx_to_json.convert_with_profile(tsx, profile_path)

    def validate(self, markup):
        path = self.write("Page.tsx", markup)
        errors, scopes = [], []
        validator.validate_file(path, CATALOG, errors, scopes)
        return errors

    def test_text_role_materializes_visuals_but_not_geometry(self):
        data, warnings = self.convert('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="text.localized" data-name="Title" data-role="modal.header"
               data-pos="0,100" data-size="560,44" />
        </div>
        ''', make_profile(**{
            "modal.header": role(
                fontSize=60,
                color=[0.137, 0.071, 0.016, 1],
                font="Assets/Resources/Font/ssfttSDF.asset",
                fontMaterial="Assets/Resources/Font/ssfttSDF_UI_OutLine2.mat",
                alignment="Center",
                width=999,
                height=999,
            )
        }))
        self.assertEqual([], warnings)
        title = data["children"][0]
        self.assertEqual(60, title["fontSize"])
        self.assertEqual([0.137, 0.071, 0.016, 1], title["color"])
        self.assertEqual("Assets/Resources/Font/ssfttSDF.asset", title["font"])
        self.assertEqual("Assets/Resources/Font/ssfttSDF_UI_OutLine2.mat", title["fontMaterial"])
        self.assertEqual("Center", title["textAlign"])
        self.assertEqual([0, 100], title["pos"])
        self.assertEqual([560, 44], title["size"])
        self.assertEqual("profile:modal.header", title["_styleSources"]["fontSize"])
        self.assertEqual("TestModule", data["_styleProfile"]["module"])

    def test_explicit_tsx_style_wins_over_profile(self):
        data, _ = self.convert('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="text.localized" data-name="Title" data-role="modal.header"
               data-pos="0,100" data-size="560,44" data-font-size="28" data-color="(1,0,0,1)" />
        </div>
        ''', make_profile(**{
            "modal.header": role(fontSize=60, color=[0, 1, 0, 1])
        }))
        title = data["children"][0]
        self.assertEqual(28, title["fontSize"])
        self.assertEqual([1, 0, 0, 1], title["color"])
        self.assertEqual("tsx", title["_styleSources"]["fontSize"])
        self.assertEqual("tsx", title["_styleSources"]["color"])

    def test_image_role_respects_explicit_color_alias(self):
        data, _ = self.convert('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="content.divider" data-name="Line" data-role="divider"
               data-pos="0,0" data-size="792,8" data-color="(1,0,0,1)" />
        </div>
        ''', make_profile(**{
            "divider": role(sprite="Assets/UI/line.png", imageType="Tiled", color=[0, 1, 0, 1])
        }))
        line = data["children"][0]
        self.assertEqual([1, 0, 0, 1], line["color"])
        self.assertNotIn("imageColor", line)
        self.assertEqual("Assets/UI/line.png", line["sprite"])
        self.assertEqual("Tiled", line["imageType"])
        self.assertEqual("tsx", line["_styleSources"]["imageColor"])

    def test_button_role_maps_image_and_text_properties(self):
        data, _ = self.convert('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <button data-component="control.button" data-name="Buy" data-role="button.primary"
                  data-pos="0,0" data-size="245,120" />
        </div>
        ''', make_profile(**{
            "button.primary": role(
                sprite="Assets/UI/btn03.png",
                imageType="Simple",
                imageColor=[1, 1, 1, 1],
                textFontSize=28,
                textColor=[1, 1, 1, 1],
                textMaterial="Assets/Resources/Font/fzhjtSDF_UI_OutLine1Px.mat",
                textAlignment="Center",
                size=[245, 120],
            )
        }))
        button = data["children"][0]
        self.assertEqual("Assets/UI/btn03.png", button["sprite"])
        self.assertEqual("Simple", button["imageType"])
        self.assertEqual([1, 1, 1, 1], button["imageColor"])
        self.assertEqual(28, button["fontSize"])
        self.assertEqual([1, 1, 1, 1], button["color"])
        self.assertEqual("Assets/Resources/Font/fzhjtSDF_UI_OutLine1Px.mat", button["fontMaterial"])
        self.assertEqual("Center", button["textAlign"])
        self.assertEqual("profile:button.primary", button["_styleSources"]["sprite"])

    def test_button_role_routes_text_properties_to_label(self):
        data, _ = self.convert('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <button data-component="control.button" data-name="Buy" data-role="button.primary"
                  data-pos="0,0" data-size="245,120">
            <div data-component="text.localized" data-name="Label"
                 data-pos="0,0" data-size="200,60" />
          </button>
        </div>
        ''', make_profile(**{
            "button.primary": role(
                sprite="Assets/UI/btn03.png",
                imageType="Simple",
                textFontSize=46,
                textColor=[1, 0.9725, 0.898, 1],
                textFont="Assets/Resources/Font/ssfttSDF.asset",
                textMaterial="Assets/Resources/Font/ssfttSDF_UI_OutLine2.mat",
                textAlignment="Center",
            )
        }))
        button = data["children"][0]
        label = button["children"][0]
        self.assertEqual("Assets/UI/btn03.png", button["sprite"])
        self.assertEqual("Simple", button["imageType"])
        self.assertNotIn("fontSize", button)
        self.assertNotIn("color", button)
        self.assertNotIn("fontMaterial", button)
        self.assertNotIn("textAlign", button)
        self.assertEqual(46, label["fontSize"])
        self.assertEqual([1, 0.9725, 0.898, 1], label["color"])
        self.assertEqual("Assets/Resources/Font/ssfttSDF.asset", label["font"])
        self.assertEqual("Assets/Resources/Font/ssfttSDF_UI_OutLine2.mat", label["fontMaterial"])
        self.assertEqual("Center", label["textAlign"])
        self.assertEqual("profile:button.primary", label["_styleSources"]["fontSize"])

    def test_button_label_explicit_style_wins_over_role(self):
        data, _ = self.convert('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <button data-component="control.button" data-name="Buy" data-role="button.primary"
                  data-pos="0,0" data-size="245,120">
            <div data-component="text.localized" data-name="Label"
                 data-pos="0,0" data-size="200,60"
                 data-font-size="24" data-color="(0.36,0.26,0.07,1)" />
          </button>
        </div>
        ''', make_profile(**{
            "button.primary": role(
                sprite="Assets/UI/btn03.png",
                textFontSize=46,
                textColor=[1, 1, 1, 1],
            )
        }))
        label = data["children"][0]["children"][0]
        self.assertEqual(24, label["fontSize"])
        self.assertEqual([0.36, 0.26, 0.07, 1], label["color"])
        self.assertEqual("tsx", label["_styleSources"]["fontSize"])
        self.assertEqual("tsx", label["_styleSources"]["color"])

    def test_missing_profile_role_is_a_warning(self):
        data, warnings = self.convert('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <button data-component="control.button" data-name="Close" data-role="button.close"
                  data-pos="0,0" data-size="96,96" />
        </div>
        ''', make_profile(**{"modal.header": role(fontSize=60)}))
        self.assertTrue(any("button.close" in warning for warning in warnings), warnings)
        close = data["children"][0]
        self.assertNotIn("_styleSources", close)

    def test_unknown_role_raises(self):
        with self.assertRaises(StyleProfileError):
            self.convert('''
            <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
              <div data-component="text.localized" data-name="Title" data-role="not.a.role"
                   data-pos="0,0" data-size="100,20" />
            </div>
            ''', make_profile(**{"modal.header": role(fontSize=60)}))

    def test_validator_accepts_role_targets(self):
        errors = self.validate('''
        <div data-component="surface.panel" data-name="Panel" data-pos="0,0" data-size="1920,1080">
          <div data-component="surface.page" data-name="Screen" data-role="screen" data-overlay="true"
               data-pos="0,0" data-size="1920,1080" data-color="(0,0,0,0.6)" />
          <div data-component="content.async-image" data-name="Bg" data-role="window.frame"
               data-pos="-500,0" data-size="200,200" data-texture="Assets/UI/frame.png" />
          <div data-component="text.localized" data-name="Title" data-role="modal.header"
               data-pos="0,0" data-size="200,40" />
          <button data-component="control.button" data-name="Buy" data-role="button.primary"
                  data-pos="300,0" data-size="245,120" />
          <div data-component="content.divider" data-name="Line" data-role="divider"
               data-pos="0,-500" data-size="792,8" />
        </div>''')
        self.assertEqual([], errors)

    def test_validator_rejects_unknown_role(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="text.localized" data-name="Title" data-role="bad.role"
               data-pos="0,0" data-size="200,40" />
        </div>''')
        self.assertTrue(any("data-role" in error for error in errors), errors)

    def test_validator_rejects_button_role_on_text(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="text.localized" data-name="Title" data-role="button.primary"
               data-pos="0,0" data-size="200,40" />
        </div>''')
        self.assertTrue(any("control.button" in error for error in errors), errors)

    def test_validator_rejects_texture_on_image(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="content.divider" data-name="Line" data-texture="Assets/UI/frame.png"
               data-pos="0,0" data-size="200,8" />
        </div>''')
        self.assertTrue(any("data-texture" in error for error in errors), errors)

    def test_validator_rejects_text_role_without_text_target(self):
        errors = self.validate('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="surface.page" data-name="Header" data-role="modal.header"
               data-pos="0,0" data-size="200,40" />
        </div>''')
        self.assertTrue(any("TextMeshProUGUI" in error for error in errors), errors)

    def test_window_frame_role_materializes_texture_without_geometry(self):
        data, _ = self.convert('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="content.async-image" data-name="Bg" data-role="window.frame"
               data-pos="0,0" data-size="720,460" />
        </div>
        ''', make_profile(**{
            "window.frame": role(
                texture="Assets/UI/Texture/frame.png",
                color=[1, 1, 1, 1],
                width=999,
                height=999,
            )
        }))
        bg = data["children"][0]
        self.assertEqual("Assets/UI/Texture/frame.png", bg["texture"])
        self.assertEqual([1, 1, 1, 1], bg["imageColor"])
        self.assertEqual([0, 0], bg["pos"])
        self.assertEqual([720, 460], bg["size"])
        self.assertNotIn("width", bg)
        self.assertNotIn("height", bg)

    def test_converter_maps_explicit_texture_attribute(self):
        data, _ = self.convert('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="1920,1080">
          <div data-component="content.async-image" data-name="Bg" data-role="window.frame"
               data-pos="0,0" data-size="720,460"
               data-texture="Assets/UI/Texture/explicit.png" />
        </div>
        ''', make_profile(**{
            "window.frame": role(texture="Assets/UI/Texture/profile.png")
        }))
        bg = data["children"][0]
        self.assertEqual("Assets/UI/Texture/explicit.png", bg["texture"])
        self.assertEqual("tsx", bg["_styleSources"]["texture"])

    def test_json_validator_accepts_role_and_texture(self):
        data = {
            "name": "Page",
            "component": "surface.page",
            "children": [
                {"name": "Title", "component": "text.localized", "role": "modal.header"},
                {"name": "Bg", "component": "content.async-image", "role": "window.frame",
                 "texture": "Assets/UI/frame.png"},
            ],
        }
        path = self.write("layout.json", json.dumps(data))
        ok, errors = validate_layout_json(path)
        self.assertTrue(ok, errors)

    def test_json_validator_rejects_bad_role_and_texture_path(self):
        cases = [
            {"name": "Title", "component": "text.localized", "role": "bad.role"},
            {"name": "Bg", "component": "content.async-image", "texture": "Other/frame.png"},
            {"name": "Reused", "prefabAssetPath": "Assets/X.prefab", "role": "modal.header"},
        ]
        for case in cases:
            with self.subTest(case=case):
                data = {"name": "Page", "component": "surface.page", "children": [case]}
                path = self.write("layout.json", json.dumps(data))
                self.assertFalse(validate_layout_json(path)[0], case)


if __name__ == "__main__":
    unittest.main()
