"""CLI is an explicit fallback and must reject unsafe inputs before launch."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unity_cli_wrapper as cli


class CliFallbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.layout = self.root / "layout.json"
        self.layout.write_text(json.dumps({"name": "Page", "component": "surface.page"}), encoding="utf-8")
        self.exe = self.root / "Unity.exe"
        self.exe.touch()
        self.env = patch.dict("os.environ", {"UNITY_EXECUTABLE": str(self.exe)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def run_fallback(self, prefab="Assets/Resources/PanelUI/Feature/Page.prefab"):
        return cli.generate_prefab(self.root, self.layout, prefab, "LR.Page", timeout=10)

    @patch("unity_cli_wrapper.subprocess.run")
    def test_editor_lock_prevents_launch(self, run):
        lock = self.root / "Temp" / "UnityLockfile"
        lock.parent.mkdir()
        lock.touch()
        self.assertNotEqual(0, self.run_fallback())
        self.assertEqual(0, run.call_count)

    @patch("unity_cli_wrapper.subprocess.run")
    def test_invalid_layout_prevents_launch(self, run):
        self.layout.write_text("{}", encoding="utf-8")
        self.assertNotEqual(0, self.run_fallback())
        self.assertEqual(0, run.call_count)

    @patch("unity_cli_wrapper.subprocess.run")
    def test_output_cannot_escape_assets(self, run):
        self.assertNotEqual(0, self.run_fallback("../outside.prefab"))
        self.assertNotEqual(0, self.run_fallback("Assets/../../outside.prefab"))
        self.assertEqual(0, run.call_count)

    @patch("unity_cli_wrapper.subprocess.run")
    def test_explicit_fallback_uses_exact_project_and_layout(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, stdout="generated", stderr="")
        self.assertEqual(0, self.run_fallback())
        args, kwargs = run.call_args
        command = args[0]
        self.assertEqual(str(self.root.resolve()), command[command.index("-projectPath") + 1])
        self.assertEqual("LRUIPrefabGen.LRUnityLayoutCLI.GenerateFromEnv", command[command.index("-executeMethod") + 1])
        self.assertEqual(str(self.layout.resolve()), kwargs["env"]["LR_LAYOUT_JSON"])
        self.assertEqual("Assets/Resources/PanelUI/Feature/Page.prefab", kwargs["env"]["LR_PREFAB_PATH"])


if __name__ == "__main__":
    unittest.main()
