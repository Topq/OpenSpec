"""Validate the real node-tree contract consumed by GenerateFromLayout."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tsx_to_json import convert
from validate_layout_json import validate_layout_json


class LayoutJsonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def validate(self, data):
        path = self.root / "layout.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return validate_layout_json(path)

    def test_accepts_real_converter_output(self):
        tsx = self.root / "Page.tsx"
        tsx.write_text('''<div data-component="surface.page" data-name="Page" data-size="500,500">
          <div data-component="control.button" data-name="Close" data-field="m_Close" data-pos="0,0" data-size="40,40" />
        </div>''', encoding="utf-8")
        ok, errors = self.validate(convert(tsx))
        self.assertTrue(ok, errors)

    def test_accepts_plain_layout_without_serialized_fields(self):
        self.assertTrue(self.validate({"name": "Page", "component": "surface.page"})[0])

    def test_accepts_existing_se_three_component_position(self):
        tsx = self.root / "Page.tsx"
        tsx.write_text('''<div data-component="surface.page" data-name="Page" data-pos="(0,0,0)" data-size="(1920,1080)">
          <button data-component="control.button" data-name="Close" data-pos="(0,0,0)" data-size="(40,40)" data-anchors="(0.5,0.5,0.5,0.5)" />
        </div>''', encoding="utf-8")
        data = convert(tsx)
        ok, errors = self.validate(data)
        self.assertTrue(ok, errors)
        self.assertEqual([0.0, 0.0, 0.0], data["children"][0]["pos"])

    def test_rejects_wrong_sized_anchor_vector(self):
        self.assertFalse(self.validate({"name": "Page", "component": "surface.page", "anchors": [0.5, 0.5, 0.5]})[0])

    def test_accepts_public_and_indexed_field_names(self):
        self.assertTrue(self.validate({"name": "Close", "component": "control.button", "field": "graphic,m_Buttons[0]"})[0])

    def test_rejects_legacy_wrapper(self):
        self.assertFalse(self.validate({"rootName": "Page", "rootScript": "LR.Page", "fields": [], "hierarchy": {"name": "Page"}})[0])

    def test_rejects_non_object_root_without_crashing(self):
        for value in [[], None, 12, "text"]:
            with self.subTest(value=value):
                self.assertFalse(self.validate(value)[0])

    def test_rejects_non_object_child_without_crashing(self):
        self.assertFalse(self.validate({"name": "Page", "component": "surface.page", "children": [3]})[0])

    def test_rejects_non_array_children(self):
        self.assertFalse(self.validate({"name": "Page", "component": "surface.page", "children": {}})[0])

    def test_rejects_missing_root_name(self):
        self.assertFalse(self.validate({"component": "surface.page"})[0])

    def test_rejects_unknown_semantic_component(self):
        self.assertFalse(self.validate({"name": "Page", "component": "invalid.component"})[0])

    def test_rejects_non_finite_or_wrong_sized_vectors(self):
        for vector in [[1], [1, 2, 3], [True, 2], [float("nan"), 2], ["1", 2]]:
            with self.subTest(vector=vector):
                self.assertFalse(self.validate({"name": "Page", "component": "surface.page", "size": vector})[0])

    def test_rejects_invalid_field_syntax(self):
        self.assertFalse(self.validate({"name": "Page", "component": "surface.page", "field": "m_Buttons[-1]"})[0])

    def test_malformed_or_missing_file_is_a_validation_failure(self):
        path = self.root / "broken.json"
        path.write_text("{", encoding="utf-8")
        self.assertFalse(validate_layout_json(path)[0])
        self.assertFalse(validate_layout_json(self.root / "missing.json")[0])


if __name__ == "__main__":
    unittest.main()
