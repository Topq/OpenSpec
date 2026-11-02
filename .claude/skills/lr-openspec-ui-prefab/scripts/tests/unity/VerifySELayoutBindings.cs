// Execute via ai-game-developer script_execute after the two fixtures compile.
using System;
using Newtonsoft.Json.Linq;
using UnityEngine;
using UnityEngine.UI;
using UnityEditor;
using TMPro;
using SEOpenSpecValidation;

public static class VerifySELayoutBindings
{
    static void Require(bool condition, string message)
    {
        if (!condition) throw new Exception("SE layout regression: " + message);
    }

    static void CheckReference(Component owner, string property, UnityEngine.Object expected, JArray checks)
    {
        Require(owner != null && expected != null, "missing owner or expected target: " + property);
        var serialized = new SerializedObject(owner);
        serialized.Update();
        var value = serialized.FindProperty(property);
        Require(value != null, "not serialized: " + property);
        Require(value.objectReferenceValue != null, "null reference: " + property);
        Require(value.objectReferenceValue == expected, "wrong target/scope: " + property);
        checks.Add(owner.gameObject.name + "." + property + " -> " + expected.name);
    }

    public static string Run()
    {
        Require(Application.dataPath.Replace("\\", "/") == "D:/se/develop/client/project/Assets", "wrong Unity project");
        const string path = "Assets/SEOpenSpecValidation_20261102/Result.prefab";
        var cycles = new JArray();
        // Unload and reopen twice: this tests serialized disk references,
        // rather than the in-memory tree passed to SaveAsPrefabAsset.
        for (int cycle = 0; cycle < 2; cycle++)
        {
            var root = PrefabUtility.LoadPrefabContents(path);
            try
            {
                var checks = new JArray();
                var page = root.GetComponent<SELayoutValidationPage>();
                var wrap = root.transform.Find("Root");
                Require(wrap != null, "SE surface.page Root wrapper missing");
                CheckReference(page, "closeButton", wrap.Find("Close").GetComponent<Button>(), checks);
                var serialized = new SerializedObject(page);
                Require(serialized.FindProperty("m_Buttons").arraySize == 2, "array size");
                CheckReference(page, "m_Buttons.Array.data[0]", wrap.Find("FirstButton").GetComponent<Button>(), checks);
                CheckReference(page, "m_Buttons.Array.data[1]", wrap.Find("SecondButton").GetComponent<Button>(), checks);
                var title = wrap.Find("Title").GetComponent<TextMeshProUGUI>();
                CheckReference(page, "m_Title", title, checks);
                CheckReference(page, "m_TitleObject", title.gameObject, checks);
                var first = wrap.Find("FirstCell").GetComponent<SELayoutValidationCell>();
                var second = wrap.Find("SecondCell").GetComponent<SELayoutValidationCell>();
                Require(first != second, "sibling component instances collapsed");
                CheckReference(page, "m_First", first, checks);
                CheckReference(page, "m_Second", second, checks);
                CheckReference(first, "m_Action", first.transform.Find("Action").GetComponent<Button>(), checks);
                CheckReference(second, "m_Action", second.transform.Find("Action").GetComponent<Button>(), checks);
                Require(title.font != null && AssetDatabase.GetAssetPath(title.font) == "Assets/Resources/Font/fzhjtSDF.asset", "SE font lost");
                var group = wrap.Find("HorizontalGroup").GetComponent<HorizontalLayoutGroup>();
                Require(group != null && group.childAlignment == TextAnchor.MiddleCenter, "layout enum application");
                foreach (var button in root.GetComponentsInChildren<Button>(true))
                    Require(button.targetGraphic != null, "button targetGraphic: " + button.name);
                foreach (var script in root.GetComponentsInChildren<MonoBehaviour>(true))
                    Require(script != null, "missing script");
                var cellRect = first.GetComponent<RectTransform>();
                Require(cellRect.anchoredPosition == new Vector2(-100, -20), "SE anchored position changed");
                cycles.Add(new JObject {
                    ["cycle"] = cycle + 1, ["references"] = checks, ["referenceCount"] = checks.Count,
                    ["font"] = AssetDatabase.GetAssetPath(title.font), ["layout"] = group.GetType().FullName,
                    ["missingScripts"] = 0, ["passed"] = true
                });
            }
            finally { PrefabUtility.UnloadPrefabContents(root); }
        }
        return new JObject {
            ["dataPath"] = Application.dataPath, ["unityVersion"] = Application.unityVersion,
            ["prefabPath"] = path, ["cycles"] = cycles, ["passed"] = true
        }.ToString();
    }
}
