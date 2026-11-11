using System;
using System.IO;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using UnityEditor;
using UnityEngine;

namespace LRUIPrefabGen
{
    /// <summary>
    /// Applies every ComponentRecipes JSON once to a temporary GameObject and
    /// reports property/component/post-process errors. This catches recipe
    /// mistakes (wrong component type, string-to-int property, private base
    /// field, unknown post-process hook) before a real panel is generated.
    ///
    /// Menu: Tools/LR/Recipe Smoke Test
    /// MCP:  reflection-method-call LRUIPrefabGen.LRRecipeSmokeTest.Run(outputJsonPath)
    /// </summary>
    public static class LRRecipeSmokeTest
    {
        [MenuItem("Tools/LR/Recipe Smoke Test")]
        public static void RunMenu()
        {
            string outputPath = Path.Combine(Path.GetTempPath(), "lr-recipe-smoke-test.json");
            string json = Run(outputPath);
            Debug.Log("[LRRecipeSmokeTest] " + json);
        }

        public static string Run(string outputJsonPath)
        {
            ComponentRecipeLoader.ClearCache();
            var recipes = ComponentRecipeLoader.LoadAll();
            var failures = new JArray();
            int passed = 0;

            foreach (var recipe in recipes.Values)
            {
                GameObject go = null;
                try
                {
                    go = new GameObject("Smoke_" + recipe.semanticId, typeof(RectTransform));
                    ComponentRecipes.Apply(go, recipe.semanticId, new JObject(), true);
                    passed++;
                }
                catch (Exception ex)
                {
                    failures.Add(new JObject
                    {
                        ["semanticId"] = recipe.semanticId,
                        ["error"] = ex.GetType().Name + ": " + ex.Message,
                    });
                }
                finally
                {
                    if (go != null)
                    {
                        UnityEngine.Object.DestroyImmediate(go);
                    }
                }
            }

            var report = new JObject
            {
                ["total"] = recipes.Count,
                ["passed"] = passed,
                ["failed"] = failures.Count,
                ["failures"] = failures,
            };
            string json = report.ToString(Formatting.Indented);
            if (!string.IsNullOrEmpty(outputJsonPath))
            {
                File.WriteAllText(outputJsonPath, json);
            }
            Debug.Log($"[LRRecipeSmokeTest] total={recipes.Count} passed={passed} failed={failures.Count}");
            return json;
        }
    }
}
