"""Review counterexamples: declarations, real recipe types and enum contracts."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import validate_unity_layout as validator
from validate_layout_json import validate_layout_json
import unity_cli_wrapper as cli


class ReviewRegressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, text):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return path

    def fields(self, source):
        return validator.extract_serialized_fields(self.write("Page.cs", source))

    def validate(self, declaration, component="control.button", field="m_Close", extra=""):
        tsx = self.write("Page.tsx", f'''<div data-component="surface.page" data-name="Page" data-pos="0,0" data-size="500,500">
          <div data-component="{component}" data-name="Close" data-field="{field}" data-pos="0,0" data-size="40,40" {extra}/>
        </div>''')
        cs = self.write("Page.cs", "public class Page { " + declaration + " }")
        errors, scopes = [], []
        validator.validate_file(tsx, {"surface.page", "control.button", "text.localized"}, errors, scopes)
        validator.check_field_completeness(scopes, [cs], errors)
        return errors

    def test_attributes_and_non_prefixed_names(self):
        for attr in ('[SerializeField] [Header("Close")]', '[SerializeField, HideInInspector]',
                     '[Header("[Close]")]\n[UnityEngine.SerializeField]'):
            with self.subTest(attr=attr):
                self.assertEqual([("closeButton", "Button", False)], self.fields(attr + " private Button closeButton;"))

    def test_commented_declarations_are_not_fields(self):
        self.assertEqual([], self.fields('''// [SerializeField] private Button m_Fake;
        /* [SerializeField] private Button m_Other; */
        const string example = "[SerializeField] private Button m_String;";'''))

    def test_extra_attributes_do_not_hide_missing_binding(self):
        errors = self.validate('[SerializeField] [Header("Close")] private Button m_Other;')
        self.assertTrue(any("字段绑定缺失: m_Other" in e for e in errors), errors)

    def test_non_prefixed_field_binds(self):
        self.assertEqual([], self.validate('[SerializeField, HideInInspector] private Button closeButton;', field="closeButton"))

    def test_sparse_array_is_rejected(self):
        errors = self.validate('[SerializeField] private Button[] m_Close;', field="m_Close[2]")
        self.assertTrue(any("连续" in e for e in errors), errors)

    def test_recipe_component_type_mismatch_is_rejected(self):
        errors = self.validate('[SerializeField] private Button m_Close;', component="text.localized")
        self.assertTrue(any("类型" in e for e in errors), errors)

    def test_array_element_type_mismatch_is_rejected(self):
        errors = self.validate('[SerializeField] private Button[] m_Close;', component="text.localized", field="m_Close[0]")
        self.assertTrue(any("类型" in e for e in errors), errors)

    def test_generic_collections_cannot_be_bound(self):
        for declared in ("List<Button>", "System.Collections.Generic.List<Button>"):
            with self.subTest(declared=declared):
                errors = self.validate(f'[SerializeField] private {declared} m_Close;')
                self.assertTrue(any("不支持" in e for e in errors), errors)

    def test_explicit_value_binding_is_not_silently_skipped(self):
        errors = self.validate('[SerializeField] private int m_Close;')
        self.assertTrue(any("不支持" in e for e in errors), errors)

    def test_recipe_child_component_does_not_satisfy_parent_binding(self):
        errors = self.validate('[SerializeField] private RaycastArea m_Close;')
        self.assertTrue(any("类型" in e for e in errors), errors)

    def test_unity_object_is_not_bindable_by_field_binder(self):
        errors = self.validate('[SerializeField] private UnityEngine.Object m_Close;')
        self.assertTrue(any("不支持" in e or "类型" in e for e in errors), errors)

    def test_custom_base_type_is_resolved_from_provided_source(self):
        source = '''namespace LR { public class Page { [SerializeField] private BaseCell m_Close; }
        public class Cell : BaseCell {} public class BaseCell : UnityEngine.MonoBehaviour {} }'''
        self.assertEqual([], self.validate(source, extra='data-lr-component="LR.Cell"'))

    def test_unknown_custom_inheritance_is_marked_for_mcp(self):
        node = self.write("Page.tsx", '<div data-component="surface.page" data-name="Cell" data-lr-component="LR.Cell" data-field="m_Cell" data-pos="0,0" data-size="100,100"/>')
        cs = self.write("Page.cs", 'public class Page { [SerializeField] private BaseCell m_Cell; }')
        errors, scopes, pending = [], [], []
        validator.validate_file(node, {"surface.page"}, errors, scopes)
        validator.check_field_completeness(scopes, [cs], errors, pending)
        self.assertEqual([], errors)
        self.assertTrue(any("MCP" in item for item in pending), pending)

    def test_known_expected_base_with_missing_custom_ancestor_requires_mcp(self):
        tsx = self.write("Page.tsx", '<div data-component="surface.page" data-name="Cell" data-lr-component="LR.Cell" data-field="m_Cell" data-pos="0,0" data-size="100,100"/>')
        cs = self.write("Page.cs", 'namespace LR { public class Page { [SerializeField] private MonoBehaviour m_Cell; } public class Cell : ExternalBaseCell {} }')
        errors, scopes, pending = [], [], []
        validator.validate_file(tsx, {"surface.page"}, errors, scopes)
        validator.check_field_completeness(scopes, [cs], errors, pending)
        self.assertEqual([], errors)
        self.assertTrue(pending)

    def test_complete_custom_chain_does_not_mask_known_mismatch(self):
        tsx = self.write("Page.tsx", '<div data-component="surface.page" data-name="Cell" data-lr-component="LR.Cell" data-field="m_Cell" data-pos="0,0" data-size="100,100"/>')
        cs = self.write("Page.cs", 'namespace LR { public class Page { [SerializeField] private Button m_Cell; } public class Cell : UnityEngine.MonoBehaviour {} }')
        errors, scopes, pending = [], [], []
        validator.validate_file(tsx, {"surface.page"}, errors, scopes)
        validator.check_field_completeness(scopes, [cs], errors, pending)
        self.assertTrue(any("类型" in error for error in errors), errors)
        self.assertEqual([], pending)

    def test_json_arrays_reject_gaps_duplicates_and_mixed_bare_binding(self):
        for fields in (("m_Items[2]",), ("m_Items[0]", "m_Items[0]"), ("m_Items", "m_Items[0]")):
            with self.subTest(fields=fields):
                data = {"name": "Page", "component": "surface.page", "children": [
                    {"name": f"Item{i}", "component": "control.button", "field": field} for i, field in enumerate(fields)]}
                self.assertFalse(validate_layout_json(self.write("layout.json", json.dumps(data)))[0])

    def test_json_sibling_scripts_have_independent_array_scopes(self):
        data = {"name": "Page", "component": "surface.page", "children": [
            {"name": f"Cell{i}", "component": "surface.page", "lrComponent": "LR.Cell", "children": [
                {"name": "Action", "component": "control.button", "field": "m_Items[0]"}]} for i in range(2)]}
        self.assertTrue(validate_layout_json(self.write("layout.json", json.dumps(data)))[0])

    def test_known_base_types_accept_recipe_components(self):
        for declared in ("Button", "UnityEngine.UI.Button", "Image", "Graphic", "Selectable", "Component", "GameObject", "Transform", "RectTransform"):
            with self.subTest(declared=declared):
                self.assertEqual([], self.validate(f'[SerializeField] private {declared} m_Close;'))

    def test_nested_script_can_supply_exact_custom_type(self):
        self.assertEqual([], self.validate('[SerializeField] private Cell m_Close;', extra='data-lr-component="LR.Cell"'))

    def test_post_process_components_are_available_on_same_node(self):
        for component, declared in (("list.single-scroll", "SingleScrollView"), ("list.scroll", "ScrollRect"),
                                    ("control.input", "TMP_InputField"), ("template.tab-item", "Button")):
            with self.subTest(component=component):
                catalog = {"surface.page", component}
                tsx = self.write("Hook.tsx", f'<div data-component="{component}" data-name="Hook" data-pos="0,0" data-size="100,100" data-field="m_Close"/>')
                cs = self.write("Page.cs", f'public class Page {{ [SerializeField] private {declared} m_Close; }}')
                errors, scopes = [], []
                validator.validate_file(tsx, catalog, errors, scopes)
                validator.check_field_completeness(scopes, [cs], errors)
                self.assertEqual([], errors)

    def test_bad_layout_enum_rejected_in_tsx(self):
        for attr, value in (("data-layout-group", "Horiontal"), ("data-layout-child-alignment", "MidleCenter")):
            with self.subTest(attr=attr):
                errors = self.validate('[SerializeField] private Button m_Close;', extra=f'{attr}="{value}"')
                self.assertTrue(any(attr in e for e in errors), errors)

    def test_bad_enums_rejected_in_json(self):
        for key, value in (("layoutGroup", "Horiontal"), ("layoutChildAlignment", "MidleCenter"),
                           ("textAlign", "centre"), ("verticalAlign", "Midle")):
            with self.subTest(key=key):
                path = self.write("layout.json", json.dumps({"name": "Page", "component": "surface.page", key: value}))
                self.assertFalse(validate_layout_json(path)[0])

    def test_valid_enums_still_pass(self):
        path = self.write("layout.json", json.dumps({"name": "Page", "component": "surface.page",
            "layoutGroup": "Horizontal", "layoutChildAlignment": "MiddleCenter", "textAlign": "Center", "verticalAlign": "Middle"}))
        self.assertTrue(validate_layout_json(path)[0])

    @patch("unity_cli_wrapper.subprocess.run")
    def test_omitted_root_script_clears_inherited_environment(self, run):
        layout = self.write("layout.json", '{"name":"Page","component":"surface.page"}')
        exe = self.write("Unity.exe", "")
        run.return_value = subprocess.CompletedProcess([], 0, stdout="generated", stderr="")
        for script_type in (None, ""):
            with self.subTest(script_type=script_type), patch.dict(os.environ, {"UNITY_EXECUTABLE": str(exe), "LR_SCRIPT_TYPE": "LR.StalePage"}):
                self.assertEqual(0, cli.generate_prefab(self.root, layout, "Assets/Test.prefab", script_type, timeout=10))
                self.assertFalse("LR_SCRIPT_TYPE" in run.call_args.kwargs["env"], "Inherited script type must be removed")


if __name__ == "__main__":
    unittest.main()
