"""Behavioral regressions for the TSX -> layout -> field-binding pipeline."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
_initial_streams = (sys.stdout, sys.stderr)
import tsx_to_json
_converter_streams = (sys.stdout, sys.stderr)
import validate_unity_layout as validator


class LayoutPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, text):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_imports_preserve_standard_streams(self):
        self.assertIs(_initial_streams[0], sys.stdout)
        self.assertIs(_initial_streams[1], sys.stderr)

    def validate_fields(self, markup, **scripts):
        path = self.write("Page.tsx", markup)
        errors, scopes = [], []
        validator.validate_file(path, {"surface.page", "control.button", "text.localized"}, errors, scopes)
        csharp = [self.write(name + ".cs", source) for name, source in scripts.items()]
        validator.check_field_completeness(scopes, csharp, errors)
        return errors

    def test_jsx_comment_does_not_create_a_fake_component(self):
        path = self.write("Page.tsx", '''
        {/* example: <div data-component="control.button" data-name="Fake" /> */}
        <div data-component="surface.page" data-name="Real" data-pos="0,0" data-size="500,500" />
        ''')
        self.assertEqual("Real", tsx_to_json.convert(path)["name"])

    def test_cell_template_marker_survives_conversion(self):
        path = self.write("Page.tsx", '<div data-component="surface.page" data-name="Page" data-cell-template="true" />')
        self.assertEqual("true", tsx_to_json.convert(path).get("cellTemplate"))

    def test_value_fields_do_not_require_gameobject_bindings(self):
        errors = self.validate_fields(
            '<div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="500,500" />',
            Page='public class Page { [SerializeField] private int m_Count; }',
        )
        self.assertEqual([], errors)

    def test_array_elements_bind_individually(self):
        errors = self.validate_fields('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="500,500">
          <div data-component="control.button" data-name="First" data-field="m_Buttons[0]" data-pos="0,0" data-size="40,40" />
          <div data-component="control.button" data-name="Second" data-field="m_Buttons[1]" data-pos="60,0" data-size="40,40" />
        </div>''', Page='public class Page { [SerializeField] private Button[] m_Buttons; }')
        self.assertEqual([], errors)

    def test_missing_reference_field_is_rejected(self):
        errors = self.validate_fields(
            '<div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="500,500" />',
            Page='public class Page { [SerializeField] private Button m_Close; }',
        )
        self.assertTrue(any("字段绑定缺失" in error for error in errors), errors)

    def test_array_requires_indexed_binding(self):
        errors = self.validate_fields(
            '<div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="500,500" data-field="m_Buttons" />',
            Page='public class Page { [SerializeField] private Button[] m_Buttons; }',
        )
        self.assertTrue(any("数组" in error for error in errors), errors)

    def test_same_array_element_cannot_be_bound_twice(self):
        errors = self.validate_fields('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="500,500">
          <div data-component="control.button" data-name="First" data-field="m_Buttons[0]" data-pos="0,0" data-size="40,40" />
          <div data-component="control.button" data-name="Second" data-field="m_Buttons[0]" data-pos="60,0" data-size="40,40" />
        </div>''', Page='public class Page { [SerializeField] private Button[] m_Buttons; }')
        self.assertTrue(any("重复" in error for error in errors), errors)

    def test_unknown_field_is_rejected(self):
        errors = self.validate_fields(
            '<div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="500,500" data-field="m_Unknown" />',
            Page='public class Page { }',
        )
        self.assertTrue(any("字段绑定多余" in error for error in errors), errors)

    def test_sibling_components_have_independent_field_scopes(self):
        errors = self.validate_fields('''
        <div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="500,500">
          <div data-component="control.button" data-name="First" data-lr-component="LR.Cell" data-field="m_First" data-pos="0,0" data-size="100,100">
            <div data-component="text.localized" data-name="Title" data-field="m_Title" data-pos="0,0" data-size="30,30" />
          </div>
          <div data-component="control.button" data-name="Second" data-lr-component="LR.Cell" data-field="m_Second" data-pos="120,0" data-size="100,100">
            <div data-component="text.localized" data-name="Title" data-field="m_Title" data-pos="0,0" data-size="30,30" />
          </div>
        </div>''',
            Page='public class Page { [SerializeField] private Cell m_First; [SerializeField] private Cell m_Second; }',
            Cell='public class Cell { [SerializeField] private TextMeshProUGUI m_Title; }',
        )
        self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
