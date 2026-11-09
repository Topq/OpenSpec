"""Role inference and aggregation for build_ui_style_profile."""
import json
from pathlib import Path
import re
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import build_ui_style_profile as profiler


def tmp_node(path, name, components=None, text=None, image=None, raw=None, layout=None):
    node = {"path": path, "name": name, "components": components or []}
    if text is not None:
        node["text"] = text
    if image is not None:
        node["image"] = image
    if raw is not None:
        node["rawImage"] = raw
    if layout is not None:
        node["layout"] = layout
    return node


def make_candidate(path, title_color, screen_alpha):
    return {
        "prefabPath": path,
        "nodes": [
            tmp_node(path + "/Screen", "Screen", ["UnityEngine.UI.Image"],
                     image={"sprite": "Assets/UI/bg2x2.png", "type": "Sliced",
                            "color": [0, 0, 0, screen_alpha]}),
            tmp_node(path + "/Window", "Window", ["UnityEngine.CanvasGroup"],
                     layout={"sizeDelta": [886, 515], "anchorMin": [0.5, 0.5], "anchorMax": [0.5, 0.5]}),
            tmp_node(path + "/Window/Bg/RawImage", "RawImage",
                     ["UnityEngine.UI.RawImage", "LR.AsyncTexture"],
                     raw={"texture": "Assets/UI/Texture/ty_tk_frame_06.png", "color": [1, 1, 1, 1]},
                     layout={"sizeDelta": [886, 515]}),
            tmp_node(path + "/Window/Bg/Title", "Title",
                     ["TMPro.TextMeshProUGUI"],
                     text={"fontSize": 60, "color": title_color,
                           "font": "Assets/Resources/Font/ssfttSDF.asset",
                           "fontMaterial": "Assets/Resources/Font/ssfttSDF_UI_OutLine2.mat",
                           "alignment": "Center", "text": "标题"}),
            tmp_node(path + "/Window/Root/TxtTitle", "TxtTitle",
                     ["TMPro.TextMeshProUGUI"],
                     text={"fontSize": 32, "color": [1, 0.843, 0, 1],
                           "font": "Assets/Resources/Font/fzhjtSDF.asset",
                           "fontMaterial": "Assets/Resources/Font/fzhjtSDF_UI_TitleLine.mat",
                           "alignment": "Center", "text": "页标题"}),
            tmp_node(path + "/Window/Root/TxtDesc", "TxtDesc",
                     ["TMPro.TextMeshProUGUI"],
                     text={"fontSize": 28, "color": [0.2, 0.06, 0.01, 1],
                           "font": "Assets/Resources/Font/fzhjtSDF.asset",
                           "fontMaterial": "Assets/Resources/Font/fzhjtSDF_UI_Default.mat",
                           "alignment": "Center", "text": "描述"}),
            tmp_node(path + "/Window/Root/TxtPrice", "TxtPrice",
                     ["TMPro.TextMeshProUGUI"],
                     text={"fontSize": 32, "color": [1, 0.843, 0, 1],
                           "font": "Assets/Resources/Font/fzhjtSDF.asset",
                           "fontMaterial": "Assets/Resources/Font/fzhjtSDF_UI_TitleLine.mat",
                           "alignment": "Center", "text": "¥ 30"}),
            tmp_node(path + "/Window/Root/Line", "Line", ["UnityEngine.UI.Image"],
                     image={"sprite": "Assets/UI/ty_tk_line_fgx1.png", "type": "Tiled",
                            "color": [0.76, 0.54, 0.39, 1]},
                     layout={"sizeDelta": [792, 8]}),
            tmp_node(path + "/Window/Root/BtnConfirm", "BtnConfirm", ["UnityEngine.UI.Button"],
                     layout={"sizeDelta": [245, 120], "anchorMin": [0.5, 0], "anchorMax": [0.5, 0]}),
            tmp_node(path + "/Window/Root/BtnConfirm/Graphic", "Graphic", ["UnityEngine.UI.Image"],
                     image={"sprite": "Assets/UI/ty_btn_03.png", "type": "Simple", "color": [1, 1, 1, 1]},
                     layout={"sizeDelta": [236, 76]}),
            tmp_node(path + "/Window/Root/BtnConfirm/TxtBtnConfirm", "TxtBtnConfirm",
                     ["TMPro.TextMeshProUGUI"],
                     text={"fontSize": 28, "color": [1, 1, 1, 1],
                           "font": "Assets/Resources/Font/ssfttSDF.asset", "alignment": "Center"}),
            tmp_node(path + "/Window/Root/BtnCancel", "BtnCancel", ["UnityEngine.UI.Button"],
                     layout={"sizeDelta": [245, 120], "anchorMin": [0.5, 0], "anchorMax": [0.5, 0]}),
            tmp_node(path + "/Window/Root/BtnCancel/Graphic", "Graphic", ["UnityEngine.UI.Image"],
                     image={"sprite": "Assets/UI/ty_btn_04.png", "type": "Simple", "color": [1, 1, 1, 1]},
                     layout={"sizeDelta": [236, 76]}),
            tmp_node(path + "/BtnClose", "BtnClose", ["UnityEngine.UI.Button"],
                     layout={"sizeDelta": [120, 120], "anchorMin": [1, 1], "anchorMax": [1, 1]}),
            tmp_node(path + "/BtnClose/Image", "Image", ["UnityEngine.UI.Image"],
                     image={"sprite": "Assets/UI/ty_btn_tk_btn_01.png", "type": "Simple",
                            "color": [1, 1, 1, 1]},
                     layout={"sizeDelta": [96, 96]}),
        ],
    }


class StyleProfileTests(unittest.TestCase):
    def test_role_inference_and_aggregation(self):
        references = {
            "candidates": [
                make_candidate("A/Panel.prefab", [0.137, 0.071, 0.016, 1], 0.7),
                make_candidate("B/Panel.prefab", [0.137, 0.071, 0.016, 1], 0.7),
            ]
        }
        profile = profiler.build_profile(references, "Module")
        roles = profile["roles"]

        self.assertEqual(2, roles["modal.header"]["samples"])
        self.assertEqual(60, roles["modal.header"]["properties"]["fontSize"]["value"])
        self.assertEqual("Assets/Resources/Font/ssfttSDF_UI_OutLine2.mat",
                         roles["modal.header"]["properties"]["fontMaterial"]["value"])

        self.assertEqual(32, roles["page.title"]["properties"]["fontSize"]["value"])
        self.assertEqual(28, roles["body"]["properties"]["fontSize"]["value"])
        self.assertEqual([1, 0.843, 0, 1], roles["price"]["properties"]["color"]["value"])

        self.assertEqual("Assets/UI/ty_btn_03.png",
                         roles["button.primary"]["properties"]["sprite"]["value"])
        self.assertEqual("Assets/Resources/Font/ssfttSDF.asset",
                         roles["button.primary"]["properties"]["textFont"]["value"])
        self.assertEqual([245, 120], roles["button.primary"]["properties"]["size"]["value"])
        self.assertEqual("Assets/UI/ty_btn_04.png",
                         roles["button.secondary"]["properties"]["sprite"]["value"])
        self.assertEqual("Assets/UI/ty_btn_tk_btn_01.png",
                         roles["button.close"]["properties"]["sprite"]["value"])

        self.assertEqual("Assets/UI/Texture/ty_tk_frame_06.png",
                         roles["window.frame"]["properties"]["texture"]["value"])
        self.assertEqual(886, roles["window.frame"]["properties"]["width"]["value"])
        self.assertEqual("Assets/UI/ty_tk_line_fgx1.png",
                         roles["divider"]["properties"]["sprite"]["value"])
        self.assertEqual("Tiled", roles["divider"]["properties"]["imageType"]["value"])
        self.assertEqual("Assets/UI/bg2x2.png", roles["screen"]["properties"]["sprite"]["value"])
        self.assertEqual("Sliced", roles["screen"]["properties"]["imageType"]["value"])
        self.assertEqual(0.7, roles["screen"]["properties"]["color"]["value"][3])

    def test_reference_scanner_reaches_button_labels(self):
        source = (SCRIPTS / "lr_ui_gen" / "LRPrefabReferenceScanner.cs").read_text(encoding="utf-8")
        match = re.search(r"MaxDepth\s*=\s*(\d+)", source)
        self.assertIsNotNone(match, "MaxDepth 常量未找到")
        self.assertGreaterEqual(
            int(match.group(1)),
            5,
            "生产 Prefab 的按钮标签位于 Btn/Graphic/Text（depth 5），扫描深度不足会导致按钮文字样式全为 null",
        )

    def test_markdown_contains_roles_and_sources(self):
        references = {"candidates": [make_candidate("A/Panel.prefab", [0.1, 0.1, 0.1, 1], 0.7)]}
        profile = profiler.build_profile(references, "Module")
        text = profiler.markdown(profile)
        self.assertIn("## modal.header", text)
        self.assertIn("## button.primary", text)
        self.assertIn("A/Panel.prefab", text)

    def test_skips_candidates_with_errors(self):
        references = {"candidates": [{"prefabPath": "Broken.prefab", "error": "not found"}]}
        profile = profiler.build_profile(references, "Module")
        self.assertEqual({}, profile["roles"])
        self.assertEqual([], profile["sources"])


if __name__ == "__main__":
    unittest.main()
