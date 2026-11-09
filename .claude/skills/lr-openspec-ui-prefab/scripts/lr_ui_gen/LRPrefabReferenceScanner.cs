using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using TMPro;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;

namespace LRUIPrefabGen
{
    /// <summary>
    /// Read-only scanner for UI reference prefabs (SKILL step 2.5).
    ///
    /// The skill uses this to answer two questions before writing TSX:
    ///   1. What hierarchy / naming / component composition do similar panels use?
    ///   2. Which concrete style values (font, size, color, sprite, material,
    ///      spacing...) does the project actually use for those roles?
    ///
    /// It returns a compact JSON summary instead of the full prefab
    /// serialization, because Prefab YAML is far too large to feed through MCP
    /// on every run. It uses PrefabUtility.LoadPrefabContents so nested prefab
    /// overrides resolve to their final values, and it never saves the asset.
    ///
    /// Invocation (via MCP reflection-method-call):
    ///   LRPrefabReferenceScanner.Scan(inputJsonPath, outputJsonPath)
    ///
    /// input JSON:
    ///   { "prefabPaths": ["Assets/Resources/PanelUI/.../Xxx.prefab"] }
    ///
    /// output JSON:
    ///   { "scannedAt": "...", "candidates": [ { prefabPath, rootName, nodes } ] }
    /// </summary>
    public static class LRPrefabReferenceScanner
    {
        public const int MaxDepth = 5; // Btn/Graphic/Text labels sit at depth 5
        public const int MaxTextLength = 64;

        static readonly HashSet<string> RelevantComponents = new HashSet<string>
        {
            "UnityEngine.Canvas",
            "UnityEngine.CanvasGroup",
            "UnityEngine.UI.Image",
            "UnityEngine.UI.RawImage",
            "UnityEngine.UI.Button",
            "UnityEngine.UI.Toggle",
            "UnityEngine.UI.ScrollRect",
            "UnityEngine.UI.HorizontalLayoutGroup",
            "UnityEngine.UI.VerticalLayoutGroup",
            "UnityEngine.UI.GridLayoutGroup",
            "TMPro.TextMeshProUGUI",
            "TMPro.TMP_InputField",
            "LR.Localizer",
            "LR.RaycastArea",
            "LR.AsyncTexture",
            "LR.AsyncIcon",
            "LR.UIRedPointWatcher",
            "LR.LRProgressBar",
            "LR.ScrollView",
            "LR.SingleScrollView",
            "PowerSaveMode",
            "LR.SwitchMainCamera",
        };

        [MenuItem("Tools/LR/Scan Reference Prefabs...")]
        public static void ScanFromMenu()
        {
            string inputJsonPath = EditorUtility.OpenFilePanel(
                "选择参考扫描输入 JSON", Application.dataPath, "json");
            if (string.IsNullOrEmpty(inputJsonPath))
            {
                return;
            }

            string directory = Path.GetDirectoryName(inputJsonPath);
            if (string.IsNullOrEmpty(directory))
            {
                directory = Application.dataPath;
            }

            string outputJsonPath = EditorUtility.SaveFilePanel(
                "保存 references.json",
                directory,
                "references.json",
                "json");
            if (string.IsNullOrEmpty(outputJsonPath))
            {
                return;
            }

            Scan(inputJsonPath, outputJsonPath);
            EditorUtility.RevealInFinder(outputJsonPath);
        }

        public static string Scan(string inputJsonPath, string outputJsonPath)
        {
            if (string.IsNullOrEmpty(inputJsonPath) || !File.Exists(inputJsonPath))
            {
                throw new FileNotFoundException("参考扫描输入 JSON 不存在", inputJsonPath);
            }

            JObject input = JObject.Parse(File.ReadAllText(inputJsonPath));
            var prefabPaths = (input["prefabPaths"] as JArray)?
                .Values<string>()
                .Where(path => !string.IsNullOrWhiteSpace(path))
                .ToList() ?? new List<string>();

            if (prefabPaths.Count == 0)
            {
                throw new Exception("prefabPaths 为空：至少提供一个 Prefab 资产路径");
            }

            var result = new JObject
            {
                ["scannedAt"] = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
                ["candidates"] = new JArray(),
            };

            var candidates = (JArray)result["candidates"];
            foreach (string prefabPath in prefabPaths)
            {
                candidates.Add(ScanOne(prefabPath));
            }

            string directory = Path.GetDirectoryName(outputJsonPath);
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
            {
                Directory.CreateDirectory(directory);
            }

            File.WriteAllText(
                outputJsonPath,
                result.ToString(Formatting.Indented),
                new System.Text.UTF8Encoding(false));

            Debug.Log($"[LRPrefabReferenceScanner] 已扫描 {candidates.Count} 个参考 Prefab: {outputJsonPath}");
            return outputJsonPath;
        }

        static JObject ScanOne(string prefabPath)
        {
            var entry = new JObject { ["prefabPath"] = prefabPath };

            GameObject prefabAsset = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            if (prefabAsset == null)
            {
                entry["error"] = "Prefab 不存在或路径无效";
                return entry;
            }

            GameObject root = null;
            try
            {
                // LoadPrefabContents edits a temporary copy and resolves nested
                // prefab overrides to final values; UnloadPrefabContents discards it.
                root = PrefabUtility.LoadPrefabContents(prefabPath);
                if (root == null)
                {
                    entry["error"] = "LoadPrefabContents 返回空对象";
                    return entry;
                }

                entry["rootName"] = root.name;
                var nodes = new JArray();
                Collect(root.transform, root.transform, 0, nodes);
                entry["nodes"] = nodes;
                return entry;
            }
            catch (Exception exception)
            {
                entry["error"] = exception.Message;
                return entry;
            }
            finally
            {
                if (root != null)
                {
                    PrefabUtility.UnloadPrefabContents(root);
                }
            }
        }

        static void Collect(Transform projectRoot, Transform current, int depth, JArray nodes)
        {
            if (depth > MaxDepth)
            {
                return;
            }

            nodes.Add(Describe(projectRoot, current.gameObject, depth));

            foreach (Transform child in current)
            {
                Collect(projectRoot, child, depth + 1, nodes);
            }
        }

        static JObject Describe(Transform projectRoot, GameObject gameObject, int depth)
        {
            var entry = new JObject
            {
                ["name"] = gameObject.name,
                ["path"] = GetPath(projectRoot, gameObject.transform),
                ["depth"] = depth,
                ["active"] = gameObject.activeSelf,
            };

            var components = new JArray();
            JObject text = null;
            JObject image = null;
            JObject rawImage = null;
            JObject button = null;
            JObject toggle = null;
            JObject scrollRect = null;
            JObject layoutGroup = null;
            JObject rectLayout = null;

            foreach (Component component in gameObject.GetComponents<Component>())
            {
                if (component == null)
                {
                    continue; // Missing script
                }

                Type type = component.GetType();
                if (IsRelevantComponent(type))
                {
                    components.Add(type.FullName);
                }

                if (component is TextMeshProUGUI tmp)
                {
                    text = DescribeText(tmp);
                }
                else if (component is Image uiImage)
                {
                    image = DescribeImage(uiImage);
                }
                else if (component is RawImage uiRawImage)
                {
                    rawImage = DescribeRawImage(uiRawImage);
                }
                else if (component is Button uiButton)
                {
                    button = DescribeButton(uiButton);
                }
                else if (component is Toggle uiToggle)
                {
                    toggle = DescribeToggle(uiToggle);
                }
                else if (component is ScrollRect uiScrollRect)
                {
                    scrollRect = DescribeScrollRect(uiScrollRect);
                }
                else if (component is GridLayoutGroup gridGroup)
                {
                    layoutGroup = DescribeGridLayoutGroup(gridGroup);
                }
                else if (component is HorizontalOrVerticalLayoutGroup horizontalOrVerticalGroup)
                {
                    layoutGroup = DescribeLayoutGroup(horizontalOrVerticalGroup);
                }
            }

            if (components.Count > 0)
            {
                entry["components"] = components;
            }
            if (text != null) entry["text"] = text;
            if (image != null) entry["image"] = image;
            if (rawImage != null) entry["rawImage"] = rawImage;
            if (button != null) entry["button"] = button;
            if (toggle != null) entry["toggle"] = toggle;
            if (scrollRect != null) entry["scrollRect"] = scrollRect;
            if (layoutGroup != null) entry["layoutGroup"] = layoutGroup;

            if (gameObject.transform is RectTransform rect)
            {
                rectLayout = DescribeRectTransform(rect);
            }
            if (rectLayout != null)
            {
                entry["layout"] = rectLayout;
            }

            return entry;
        }

        static bool IsRelevantComponent(Type type)
        {
            string fullName = type.FullName ?? type.Name;
            return RelevantComponents.Contains(fullName)
                || fullName.StartsWith("LR.", StringComparison.Ordinal);
        }

        static JObject DescribeText(TextMeshProUGUI text)
        {
            return new JObject
            {
                ["font"] = AssetPath(text.font),
                ["fontMaterial"] = AssetPath(text.fontSharedMaterial),
                ["fontSize"] = text.fontSize,
                ["color"] = ColorArray(text.color),
                ["alignment"] = text.alignment.ToString(),
                ["fontStyle"] = text.fontStyle.ToString(),
                ["characterSpacing"] = text.characterSpacing,
                ["lineSpacing"] = text.lineSpacing,
                ["text"] = Truncate(text.text),
            };
        }

        static JObject DescribeImage(Image image)
        {
            var entry = new JObject
            {
                ["sprite"] = AssetPath(image.sprite),
                ["type"] = image.type.ToString(),
                ["color"] = ColorArray(image.color),
                ["preserveAspect"] = image.preserveAspect,
                ["raycastTarget"] = image.raycastTarget,
                ["pixelsPerUnitMultiplier"] = image.pixelsPerUnitMultiplier,
            };
            if (image.type == Image.Type.Filled)
            {
                entry["fillMethod"] = image.fillMethod.ToString();
                entry["fillOrigin"] = image.fillOrigin;
                entry["fillAmount"] = image.fillAmount;
            }
            return entry;
        }

        static JObject DescribeRawImage(RawImage image)
        {
            return new JObject
            {
                ["texture"] = AssetPath(image.texture),
                ["color"] = ColorArray(image.color),
                ["raycastTarget"] = image.raycastTarget,
            };
        }

        static JObject DescribeButton(Button button)
        {
            return new JObject
            {
                ["transition"] = button.transition.ToString(),
                ["interactable"] = button.interactable,
                ["targetGraphic"] = button.targetGraphic != null ? button.targetGraphic.name : null,
                ["colors"] = new JObject
                {
                    ["normalColor"] = ColorArray(button.colors.normalColor),
                    ["highlightedColor"] = ColorArray(button.colors.highlightedColor),
                    ["pressedColor"] = ColorArray(button.colors.pressedColor),
                    ["selectedColor"] = ColorArray(button.colors.selectedColor),
                    ["disabledColor"] = ColorArray(button.colors.disabledColor),
                    ["colorMultiplier"] = button.colors.colorMultiplier,
                },
            };
        }

        static JObject DescribeToggle(Toggle toggle)
        {
            return new JObject
            {
                ["isOn"] = toggle.isOn,
                ["interactable"] = toggle.interactable,
                ["targetGraphic"] = toggle.targetGraphic != null ? toggle.targetGraphic.name : null,
            };
        }

        static JObject DescribeScrollRect(ScrollRect scrollRect)
        {
            return new JObject
            {
                ["horizontal"] = scrollRect.horizontal,
                ["vertical"] = scrollRect.vertical,
                ["movementType"] = scrollRect.movementType.ToString(),
                ["scrollSensitivity"] = scrollRect.scrollSensitivity,
                ["viewport"] = scrollRect.viewport != null ? scrollRect.viewport.name : null,
                ["content"] = scrollRect.content != null ? scrollRect.content.name : null,
            };
        }

        static JObject DescribeLayoutGroup(HorizontalOrVerticalLayoutGroup group)
        {
            return new JObject
            {
                ["type"] = group.GetType().Name,
                ["spacing"] = group.spacing,
                ["padding"] = new JArray(group.padding.left, group.padding.right, group.padding.top, group.padding.bottom),
                ["childAlignment"] = group.childAlignment.ToString(),
                ["childForceExpandWidth"] = group.childForceExpandWidth,
                ["childForceExpandHeight"] = group.childForceExpandHeight,
            };
        }

        static JObject DescribeGridLayoutGroup(GridLayoutGroup group)
        {
            return new JObject
            {
                ["type"] = group.GetType().Name,
                ["cellSize"] = Vector2Array(group.cellSize),
                ["spacing"] = Vector2Array(group.spacing),
                ["padding"] = new JArray(group.padding.left, group.padding.right, group.padding.top, group.padding.bottom),
                ["childAlignment"] = group.childAlignment.ToString(),
                ["constraint"] = group.constraint.ToString(),
                ["constraintCount"] = group.constraintCount,
            };
        }

        static JObject DescribeRectTransform(RectTransform rect)
        {
            return new JObject
            {
                ["anchorMin"] = Vector2Array(rect.anchorMin),
                ["anchorMax"] = Vector2Array(rect.anchorMax),
                ["pivot"] = Vector2Array(rect.pivot),
                ["anchoredPosition"] = Vector2Array(rect.anchoredPosition),
                ["sizeDelta"] = Vector2Array(rect.sizeDelta),
                ["localScale"] = Vector3Array(rect.localScale),
            };
        }

        static string AssetPath(UnityEngine.Object asset)
        {
            return asset == null ? null : AssetDatabase.GetAssetPath(asset);
        }

        static JArray ColorArray(Color color)
        {
            return new JArray(color.r, color.g, color.b, color.a);
        }

        static JArray Vector2Array(Vector2 value)
        {
            return new JArray(value.x, value.y);
        }

        static JArray Vector3Array(Vector3 value)
        {
            return new JArray(value.x, value.y, value.z);
        }

        static string Truncate(string value)
        {
            if (string.IsNullOrEmpty(value))
            {
                return value;
            }
            string singleLine = value.Replace("\r", " ").Replace("\n", " ");
            return singleLine.Length <= MaxTextLength
                ? singleLine
                : singleLine.Substring(0, MaxTextLength) + "...";
        }

        static string GetPath(Transform root, Transform current)
        {
            var segments = new List<string>();
            Transform cursor = current;
            while (cursor != null)
            {
                segments.Add(cursor.name);
                if (cursor == root)
                {
                    break;
                }
                cursor = cursor.parent;
            }
            segments.Reverse();
            return string.Join("/", segments);
        }
    }
}
