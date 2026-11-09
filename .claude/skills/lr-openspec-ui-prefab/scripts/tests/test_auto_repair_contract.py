"""Static contract for generator auto-repair (asset paths + serialized fields)."""
from pathlib import Path
import unittest

GEN = Path(__file__).resolve().parents[1] / "lr_ui_gen"


class AutoRepairContractTests(unittest.TestCase):
    def read(self, name):
        path = GEN / name
        self.assertTrue(path.is_file(), f"missing {name}")
        return path.read_text(encoding="utf-8")

    def test_auto_fix_log_is_collectable(self):
        source = self.read("LRAutoFix.cs")
        self.assertIn("class LRAutoFixLog", source)
        self.assertIn("public static void Add(", source)
        self.assertIn("public static IReadOnlyList<LRAutoFix> Snapshot()", source)

    def test_asset_resolver_repairs_only_unique_candidates(self):
        source = self.read("LRAssetResolver.cs")
        self.assertIn("AssetDatabase.FindAssets(stem)", source)
        self.assertIn("candidates.Count == 1", source)
        self.assertIn("存在多个同优先级同名候选", source)
        self.assertIn("LRAutoFixLog.Add(\"asset\"", source)

    def test_field_binder_repairs_only_unique_candidates(self):
        source = self.read("LRFieldBinder.cs")
        self.assertIn("ResolveFieldBySimilarity", source)
        self.assertIn("Levenshtein(", source)
        self.assertIn("存在多个同距离候选", source)
        self.assertIn("没有相似度足够的候选", source)
        self.assertIn("LRAutoFixLog.Add(\"field\"", source)
        self.assertIn("out string resolvedField", source)

    def test_generator_reports_auto_fixes(self):
        source = self.read("LRUnityLayoutPrefabGenerator.cs")
        self.assertIn("LRAutoFixLog.Clear()", source)
        self.assertIn("AppendAutoFixes(report)", source)
        self.assertIn('report["autoFixes"]', source)
        self.assertIn('entry["resolvedField"]', source)
        self.assertIn("LRAssetResolver.Load<T>(path", source)

    def test_component_recipes_use_asset_resolver(self):
        source = self.read("LRComponentRecipes.cs")
        self.assertIn("return LRAssetResolver.Load<T>(path", source)


if __name__ == "__main__":
    unittest.main()
