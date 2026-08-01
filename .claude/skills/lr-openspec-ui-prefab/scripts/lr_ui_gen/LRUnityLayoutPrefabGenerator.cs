using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using TMPro;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;

namespace LRUIPrefabGen
{
    /// <summary>
    /// Reads the JSON layout produced by lr-openspec-ui-prefab/scripts/tsx_to_json.py
    /// and builds the corresponding Unity UI prefab: GameObject tree, RectTransform,
    /// components per the unity-ui-components.md whitelist, and [SerializeField]
    /// binding via reflection. No AI participates in this step; same JSON always
    /// produces the same prefab.
    /// </summary>
    public static class LRUnityLayoutPrefabGenerator
    {
        [MenuItem("Tools/LR/Generate Prefab From Layout JSON...")]
        public static void GenerateFromMenu()
        {
            string jsonPath = EditorUtility.OpenFilePanel("选择布局 JSON", Application.dataPath, "json");
            if (string.IsNullOrEmpty(jsonPath))
            {
                return;
            }

            string prefabPath = EditorUtility.SaveFilePanelInProject(
                "保存 Prefab",
                "GeneratedPanel",
                "prefab",
                "选择 Prefab 输出路径");
            if (string.IsNullOrEmpty(prefabPath))
            {
                return;
            }

            GenerateFromLayout(jsonPath, prefabPath, null);
        }

        /// <summary>
        /// Main entry point. jsonPath: absolute or project-relative path to the
        /// layout JSON. prefabPath: project-relative path (Assets/...) for the
        /// output prefab. rootScriptTypeName: optional full type name (e.g.
        /// "LR.GrowthFundPage") to attach to the root and receive field bindings.
        /// </summary>
        public static string GenerateFromLayout(string jsonPath, string prefabPath, string rootScriptTypeName)
        {
            string jsonText = File.ReadAllText(jsonPath);
            JObject root = JObject.Parse(jsonText);

            // BuildNode already attaches nested data-lr-component scripts
            // (e.g. a Row/Cell MonoBehaviour) as it builds the tree, via
            // ComponentRecipes.AddLRComponentPublic. Only the *page-level*
            // root script (rootScriptTypeName) needs attaching here.
            GameObject rootGo = BuildNode(root, null);

            Component rootComponent = null;
            if (!string.IsNullOrEmpty(rootScriptTypeName))
            {
                Type rootType = FindType(rootScriptTypeName);
                if (rootType == null)
                {
                    Debug.LogWarning($"[LRUnityLayoutPrefabGenerator] 未找到脚本类型: {rootScriptTypeName}，跳过挂载和绑定");
                }
                else
                {
                    rootComponent = rootGo.GetComponent(rootType) ?? rootGo.AddComponent(rootType);
                }
            }

            // Recursively bind data-field to the *nearest enclosing* script
            // component -- the page root component, or a nested Row/Cell
            // component if the field's ancestor chain crosses a
            // data-lr-component boundary. See CollectAndBindScoped.
            int boundFieldCount = 0;
            CollectAndBindScoped(root, rootGo, rootComponent, ref boundFieldCount);

            string fullPrefabPath = prefabPath.EndsWith(".prefab") ? prefabPath : prefabPath + ".prefab";
            string dir = Path.GetDirectoryName(fullPrefabPath);
            if (!string.IsNullOrEmpty(dir) && !AssetDatabase.IsValidFolder(dir))
            {
                CreateFolderRecursive(dir);
            }

            // Phase 1: 写出基础 Prefab（层级 + RectTransform + 组件 + 根脚本字段绑定）。
            GameObject savedPrefab = PrefabUtility.SaveAsPrefabAsset(rootGo, fullPrefabPath, out bool success);
            UnityEngine.Object.DestroyImmediate(rootGo);

            if (!success)
            {
                throw new Exception($"保存 Prefab 失败: {fullPrefabPath}");
            }

            // Phase 2: 通过 AssetDatabase.LoadAssetAtPath 重新加载为真正的磁盘资产，
            // 直接在这个资产对象上用 AddComponent / SerializedObject 打补丁，
            // 再用 PrefabUtility.SavePrefabAsset（不是 SaveAsPrefabAsset）落盘。
            // 这是 Unity 官方推荐的"修改已存在 Prefab 资产序列化字段"的方式，
            // 之前用 EditPrefabContentsScope 重新进入编辑模式的方案有状态没对齐，改用这个更直接的路径。
            PostProcessSavedPrefabAsset(root, fullPrefabPath);

            Debug.Log($"[LRUnityLayoutPrefabGenerator] 生成完成: {fullPrefabPath}，字段绑定 {boundFieldCount} 个");
            return fullPrefabPath;
        }

        static void CreateFolderRecursive(string path)
        {
            string[] parts = path.Split('/');
            string current = parts[0];
            for (int i = 1; i < parts.Length; i++)
            {
                string next = current + "/" + parts[i];
                if (!AssetDatabase.IsValidFolder(next))
                {
                    AssetDatabase.CreateFolder(current, parts[i]);
                }
                current = next;
            }
        }

        // ------------------------------------------------------------------
        // Node construction
        // ------------------------------------------------------------------

        static GameObject BuildNode(JObject node, Transform parent)
        {
            string prefabAssetPath = (string)node["prefabAssetPath"];
            if (!string.IsNullOrEmpty(prefabAssetPath))
            {
                return InstantiatePrefabAsset(node, parent, prefabAssetPath);
            }

            string name = (string)node["name"] ?? "UnnamedNode";
            var go = new GameObject(name, typeof(RectTransform));
            if (parent != null)
            {
                go.transform.SetParent(parent, false);
            }

            ApplyRectTransform(go.GetComponent<RectTransform>(), node);

            string component = (string)node["component"];
            if (!string.IsNullOrEmpty(component))
            {
                ComponentRecipes.Apply(go, component, node);
            }

            // 处理 data-lr-component: 显式指定额外挂载的 LR 自定义组件（如 Cell 脚本）
            string lrComponent = (string)node["lrComponent"];
            if (!string.IsNullOrEmpty(lrComponent))
            {
                ComponentRecipes.AddLRComponentPublic(go, lrComponent);
            }

            var childrenToken = node["children"] as JArray;
            if (childrenToken != null)
            {
                foreach (JObject child in childrenToken.OfType<JObject>())
                {
                    BuildChildOrPrefabRef(child, go.transform);
                }
            }

            return go;
        }

        static void BuildChildOrPrefabRef(JObject child, Transform parent)
        {
            string prefabChildPath = (string)child["prefabChildPath"];
            if (!string.IsNullOrEmpty(prefabChildPath))
            {
                // Edits an existing node inside the parent's already-instantiated
                // recipe hierarchy (e.g. list.single-scroll's Viewport/Content);
                // it does not create a new GameObject.
                Transform existing = parent.Find(prefabChildPath);
                if (existing == null)
                {
                    Debug.LogWarning($"[LRUnityLayoutPrefabGenerator] data-prefab-child-path 未找到: {prefabChildPath} (parent={parent.name})");
                    return;
                }

                string childName = (string)child["name"];
                if (!string.IsNullOrEmpty(childName))
                {
                    existing.name = childName;
                }

                var nested = child["children"] as JArray;
                if (nested != null)
                {
                    foreach (JObject grandChild in nested.OfType<JObject>())
                    {
                        BuildChildOrPrefabRef(grandChild, existing);
                    }
                }
                return;
            }

            BuildNode(child, parent);
        }

        static GameObject InstantiatePrefabAsset(JObject node, Transform parent, string prefabAssetPath)
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabAssetPath);
            if (prefab == null)
            {
                throw new Exception($"data-prefab-asset-path 指向的 Prefab 不存在: {prefabAssetPath}");
            }

            GameObject instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
            string name = (string)node["name"];
            if (!string.IsNullOrEmpty(name))
            {
                instance.name = name;
            }

            var rect = instance.GetComponent<RectTransform>();
            if (rect != null)
            {
                ApplyRectTransform(rect, node);
            }
            return instance;
        }

        static void ApplyRectTransform(RectTransform rect, JObject node)
        {
            var anchorMin = ReadVector2(node["anchorMin"]);
            var anchorMax = ReadVector2(node["anchorMax"]);
            var anchors = ReadVector4(node["anchors"]);
            if (anchors.HasValue)
            {
                rect.anchorMin = new Vector2(anchors.Value.x, anchors.Value.y);
                rect.anchorMax = new Vector2(anchors.Value.z, anchors.Value.w);
            }
            else
            {
                if (anchorMin.HasValue) rect.anchorMin = anchorMin.Value;
                if (anchorMax.HasValue) rect.anchorMax = anchorMax.Value;
            }

            var pivot = ReadVector2(node["pivot"]);
            if (pivot.HasValue)
            {
                rect.pivot = pivot.Value;
            }

            var pos = ReadVector2(node["pos"]);
            if (pos.HasValue)
            {
                rect.anchoredPosition = pos.Value;
            }

            var size = ReadVector2(node["size"]);
            if (size.HasValue)
            {
                rect.sizeDelta = size.Value;
            }
        }

        static Vector2? ReadVector2(JToken token)
        {
            if (token is JArray arr && arr.Count >= 2)
            {
                return new Vector2((float)arr[0], (float)arr[1]);
            }
            return null;
        }

        static Vector4? ReadVector4(JToken token)
        {
            if (token is JArray arr && arr.Count >= 4)
            {
                return new Vector4((float)arr[0], (float)arr[1], (float)arr[2], (float)arr[3]);
            }
            return null;
        }

        static Color? ReadColor(JToken token)
        {
            if (token is JArray arr && arr.Count >= 4)
            {
                return new Color((float)arr[0], (float)arr[1], (float)arr[2], (float)arr[3]);
            }
            return null;
        }

        // ------------------------------------------------------------------
        // Field binding
        // ------------------------------------------------------------------

        /// <summary>
        /// Recursively walks the JSON tree and binds each node's data-field
        /// to whichever script component "owns" it. Ownership is scoped by
        /// data-lr-component boundaries: a node's data-field binds to
        /// `currentTarget` (the nearest enclosing script), which starts as
        /// the page root and switches to a freshly-attached component
        /// whenever a descendant node carries data-lr-component (e.g. a Row
        /// or Cell MonoBehaviour). This is what lets two sibling Cell
        /// instances each bind their own m_BtnClaim etc. without colliding --
        /// each gets bound against its own component instance rather than a
        /// single global dictionary keyed by field name.
        /// </summary>
        static void CollectAndBindScoped(JObject node, GameObject go, Component currentTarget, ref int boundFieldCount)
        {
            string lrComponent = (string)node["lrComponent"];
            Component scopeTarget = currentTarget;
            if (!string.IsNullOrEmpty(lrComponent))
            {
                // BuildNode already added this component while constructing
                // the tree; fetch the same instance here so bindings land on
                // this node's own script rather than the enclosing scope's.
                Type scopeType = FindType(lrComponent);
                if (scopeType != null)
                {
                    scopeTarget = go.GetComponent(scopeType);
                    if (scopeTarget == null)
                    {
                        Debug.LogWarning($"[LRUnityLayoutPrefabGenerator] {lrComponent} 组件未挂载到 {go.name}，字段绑定将回退到外层作用域");
                        scopeTarget = currentTarget;
                    }
                }
            }

            // A node's OWN data-field belongs to the *enclosing* scope
            // (currentTarget), not the new scope it may itself open via
            // data-lr-component -- e.g. FreeCell carries both
            // data-lr-component="LR.MixGrowthFundRewardCell" (for its
            // children's fields) and data-field="m_FreeCell" (a field on the
            // *parent* Row's script, pointing at this Cell instance). Only
            // descendants use scopeTarget; see the recursive call below.
            string field = (string)node["field"];
            if (!string.IsNullOrEmpty(field))
            {
                if (currentTarget == null)
                {
                    Debug.LogWarning($"[LRUnityLayoutPrefabGenerator] data-field=\"{field}\" 没有可绑定的脚本作用域（未指定根脚本或 data-lr-component），跳过绑定");
                }
                else
                {
                    FieldBinder.BindField(currentTarget, field, go);
                    boundFieldCount++;
                }
            }

            var childrenToken = node["children"] as JArray;
            if (childrenToken == null)
            {
                return;
            }

            // GameObject children were created in the same order as the JSON
            // children array by BuildNode/BuildChildOrPrefabRef, except that
            // prefab-child-path entries reuse an existing Transform found by
            // name rather than appending a new one. Re-resolve by data-name
            // to stay correct regardless of ordering.
            foreach (JObject child in childrenToken.OfType<JObject>())
            {
                string childName = (string)child["name"];
                Transform childTransform = string.IsNullOrEmpty(childName) ? null : FindDescendantByName(go.transform, childName);
                if (childTransform != null)
                {
                    CollectAndBindScoped(child, childTransform.gameObject, scopeTarget, ref boundFieldCount);
                }
            }
        }

        static Transform FindDescendantByName(Transform root, string name)
        {
            foreach (Transform child in root)
            {
                if (child.name == name)
                {
                    return child;
                }
            }
            // fall back to recursive search (covers prefab-child-path nodes
            // that live deeper than one level, e.g. Viewport/Content)
            foreach (Transform child in root)
            {
                Transform found = FindDescendantByName(child, name);
                if (found != null)
                {
                    return found;
                }
            }
            return null;
        }

        // ------------------------------------------------------------------
        // Post-processing: configure special components (SingleScrollView, Localizer, etc.)
        //
        // Key fix: Phase 1 (GenerateFromLayout above) writes the base prefab via
        // PrefabUtility.SaveAsPrefabAsset(tempGameObject, path) -- that call takes an
        // in-memory scene object and snapshots it to a new prefab file. It is NOT the
        // same as "the prefab asset". To reliably add components / set fields on an
        // *existing* prefab asset afterwards, the correct sequence is:
        //   1. AssetDatabase.LoadAssetAtPath<GameObject>(path) -- get the real asset object
        //   2. Mutate it directly (AddComponent, SerializedObject+ApplyModifiedProperties)
        //   3. PrefabUtility.SavePrefabAsset(loadedAsset) -- NOT SaveAsPrefabAsset again
        // This mirrors the standard Editor-scripting workflow for patching prefab
        // serialized fields and is what actually persists to disk.
        // ------------------------------------------------------------------

        static void PostProcessSavedPrefabAsset(JObject jsonRoot, string prefabPath)
        {
            GameObject prefabAsset = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            if (prefabAsset == null)
            {
                Debug.LogWarning($"[LRUnityLayoutPrefabGenerator] 无法加载 Prefab 资产用于后处理: {prefabPath}");
                return;
            }

            int localizerCount = 0;
            int scrollViewCount = 0;
            var localizerEntries = new System.Collections.Generic.List<(string key, string defaultText, string path)>();
            PostProcessNode(jsonRoot, prefabAsset, ref localizerCount, ref scrollViewCount, localizerEntries);

            EditorUtility.SetDirty(prefabAsset);
            PrefabUtility.SavePrefabAsset(prefabAsset);
            AssetDatabase.SaveAssets();

            Debug.Log($"[LRUnityLayoutPrefabGenerator] 后处理完成: {prefabPath}，Localizer +{localizerCount}，SingleScrollView 配置 {scrollViewCount} 个");

            // 写入 Language_Keys.md
            if (localizerEntries.Count > 0)
            {
                WriteLanguageKeysMarkdown(prefabPath, localizerEntries);
            }
        }

        static void PostProcessNode(JObject node, GameObject go, ref int localizerCount, ref int scrollViewCount, System.Collections.Generic.List<(string key, string defaultText, string path)> localizerEntries)
        {
            string component = (string)node["component"];
            string field = (string)node["field"];

            // text.localized* 系列的 Localizer 挂载规则：
            // - 有 field 绑定：移除 Localizer（由 C# 脚本控制文本内容）
            // - 无 field 绑定：确保有 Localizer 并设置 m_Key（运行时多语言切换）
            if (!string.IsNullOrEmpty(component) && component.StartsWith("text.localized"))
            {
                Type localizerType = FindType("LR.Localizer");
                if (localizerType != null)
                {
                    Component existingLocalizer = go.GetComponent(localizerType);

                    if (!string.IsNullOrEmpty(field))
                    {
                        // 有 field 绑定：移除 Localizer（如果存在）
                        if (existingLocalizer != null)
                        {
                            UnityEngine.Object.DestroyImmediate(existingLocalizer, true);
                        }
                    }
                    else
                    {
                        // 无 field 绑定：确保有 Localizer 并设置 m_Key
                        Component localizer = existingLocalizer;
                        if (localizer == null)
                        {
                            localizer = go.AddComponent(localizerType);
                            localizerCount++;
                        }

                        // 设置 m_Key 字段：格式为 UI_<PanelName>_<NodeName>
                        string pageName = GetPageNameFromRoot(go);
                        string nodeName = (string)node["name"];
                        string defaultText = (string)node["text"] ?? "";
                        if (!string.IsNullOrEmpty(pageName) && !string.IsNullOrEmpty(nodeName))
                        {
                            string key = $"UI_{pageName}_{nodeName}";
                            var serializedObject = new SerializedObject(localizer);
                            serializedObject.Update();
                            var keyProp = serializedObject.FindProperty("m_Key");
                            if (keyProp != null)
                            {
                                keyProp.stringValue = key;
                                serializedObject.ApplyModifiedProperties();
                            }

                            // 记录到 Language_Keys.md 待写入列表（增加 path 信息）
                            string path = GetGameObjectPath(go);
                            localizerEntries.Add((key, defaultText, path));
                        }
                    }
                }
            }

            // list.single-scroll -> 配置 CellTemplate/CellWidth/CellHeight
            if (component == "list.single-scroll")
            {
                if (ConfigureSingleScrollView(node, go))
                {
                    scrollViewCount++;
                }
            }

            var childrenToken = node["children"] as JArray;
            if (childrenToken == null)
            {
                return;
            }

            foreach (JObject childNode in childrenToken.OfType<JObject>())
            {
                // prefabChildPath 节点不是新建的 GameObject，只是已有子路径的挂载点指示；
                // 它自己不需要后处理，但要继续深入它的 children（真正的模板节点在里面）。
                string prefabChildPath = (string)childNode["prefabChildPath"];
                if (!string.IsNullOrEmpty(prefabChildPath))
                {
                    Transform targetParent = go.transform.Find(prefabChildPath);
                    if (targetParent == null)
                    {
                        continue;
                    }

                    var grandChildren = childNode["children"] as JArray;
                    if (grandChildren == null)
                    {
                        continue;
                    }

                    foreach (JObject grandChild in grandChildren.OfType<JObject>())
                    {
                        string grandChildName = (string)grandChild["name"];
                        if (string.IsNullOrEmpty(grandChildName))
                        {
                            continue;
                        }

                        Transform grandChildTransform = targetParent.Find(grandChildName);
                        if (grandChildTransform != null)
                        {
                            PostProcessNode(grandChild, grandChildTransform.gameObject, ref localizerCount, ref scrollViewCount, localizerEntries);
                        }
                    }
                    continue;
                }

                string childName = (string)childNode["name"];
                if (string.IsNullOrEmpty(childName))
                {
                    continue;
                }

                Transform childTransform = go.transform.Find(childName);
                if (childTransform != null)
                {
                    PostProcessNode(childNode, childTransform.gameObject, ref localizerCount, ref scrollViewCount, localizerEntries);
                }
            }
        }

        /// <summary>
        /// Configures m_CellTemplate / m_CellWidth / m_CellHeight on a list.single-scroll
        /// node's ScrollView component via SerializedObject, per the standard pattern:
        /// SerializedObject -> FindProperty -> set value -> ApplyModifiedProperties.
        /// Returns true if a template was found and fields were applied.
        /// </summary>
        static bool ConfigureSingleScrollView(JObject node, GameObject go)
        {
            Component scrollView = go.GetComponent("LR.SingleScrollView");
            if (scrollView == null)
            {
                scrollView = go.GetComponent<ScrollRect>();
            }

            if (scrollView == null)
            {
                Debug.LogWarning($"[LRUnityLayoutPrefabGenerator] list.single-scroll 节点 {go.name} 没有找到 ScrollView 组件");
                return false;
            }

            Transform templateTransform = FindCellTemplateTransform(node, go.transform);
            if (templateTransform == null)
            {
                Debug.LogWarning($"[LRUnityLayoutPrefabGenerator] SingleScrollView {go.name}: 未找到带 Template 字段的模板节点");
                return false;
            }

            var templateRect = templateTransform.GetComponent<RectTransform>();
            if (templateRect == null)
            {
                return false;
            }

            int cellWidth = Mathf.RoundToInt(templateRect.sizeDelta.x);
            int cellHeight = Mathf.RoundToInt(templateRect.sizeDelta.y);

            var serializedObject = new SerializedObject(scrollView);
            serializedObject.Update();

            var templateProp = serializedObject.FindProperty("m_CellTemplate");
            var widthProp = serializedObject.FindProperty("m_CellWidth");
            var heightProp = serializedObject.FindProperty("m_CellHeight");

            if (templateProp == null || widthProp == null || heightProp == null)
            {
                Debug.LogWarning($"[LRUnityLayoutPrefabGenerator] SingleScrollView {go.name}: 未找到 m_CellTemplate/m_CellWidth/m_CellHeight 序列化字段");
                return false;
            }

            templateProp.objectReferenceValue = templateTransform.gameObject;
            widthProp.intValue = cellWidth;
            heightProp.intValue = cellHeight;
            serializedObject.ApplyModifiedProperties();

            Debug.Log($"[LRUnityLayoutPrefabGenerator] 配置 SingleScrollView {go.name}: CellTemplate={templateTransform.name}, CellWidth={cellWidth}, CellHeight={cellHeight}");
            return true;
        }

        /// <summary>
        /// Walks a list.single-scroll JSON node's children in lockstep with the real
        /// Transform hierarchy, looking for the first descendant that marks itself as
        /// the reusable cell template, and returns its actual Transform. A node marks
        /// itself as the template either by carrying data-lr-component (the preferred
        /// way once the cell has its own MonoBehaviour, e.g. data-lr-component=
        /// "LR.MixGrowthFundRewardTierRow") or, for backwards compatibility with TSX
        /// written before that attribute existed, by a data-field name containing
        /// "Template".
        ///
        /// Important: a data-prefab-child-path wrapper (e.g. "Viewport/Content") does
        /// not create a new GameObject -- BuildChildOrPrefabRef finds the *existing*
        /// child at that path and renames it to the wrapper's own data-name (see
        /// GrowthFundPage.tsx's "ViewportContentAnchor" wrapping "Viewport/Content").
        /// So the on-disk name is the wrapper's JSON name, not the literal path segment
        /// ("Content") -- we must resolve child GameObjects by name, not assume a fixed
        /// path string.
        /// </summary>
        static Transform FindCellTemplateTransform(JObject node, Transform current)
        {
            var childrenToken = node["children"] as JArray;
            if (childrenToken == null)
            {
                return null;
            }

            foreach (JObject child in childrenToken.OfType<JObject>())
            {
                string prefabChildPath = (string)child["prefabChildPath"];
                if (!string.IsNullOrEmpty(prefabChildPath))
                {
                    // prefabChildPath (e.g. "Viewport/Content") is the ORIGINAL path used
                    // to locate the existing child; BuildChildOrPrefabRef then renamed that
                    // found Transform to the wrapper's own JSON "name". So: resolve the
                    // parent-chain portion of the path normally, then look for the child
                    // under it by either the new (post-rename) name or the original last
                    // path segment (covers the case where no rename happened, e.g. name
                    // matched already, or this wrapper has no "name").
                    int lastSlash = prefabChildPath.LastIndexOf('/');
                    string parentPath = lastSlash >= 0 ? prefabChildPath.Substring(0, lastSlash) : null;
                    string originalLeafName = lastSlash >= 0 ? prefabChildPath.Substring(lastSlash + 1) : prefabChildPath;

                    Transform parentTransform = string.IsNullOrEmpty(parentPath) ? current : current.Find(parentPath);
                    if (parentTransform == null)
                    {
                        continue;
                    }

                    string wrapperName = (string)child["name"];
                    Transform wrapperTransform = (!string.IsNullOrEmpty(wrapperName) ? parentTransform.Find(wrapperName) : null)
                        ?? parentTransform.Find(originalLeafName);
                    if (wrapperTransform == null)
                    {
                        continue;
                    }

                    Transform found = FindCellTemplateTransform(child, wrapperTransform);
                    if (found != null)
                    {
                        return found;
                    }
                    continue;
                }

                string childName = (string)child["name"];
                if (string.IsNullOrEmpty(childName))
                {
                    continue;
                }

                Transform childTransform = current.Find(childName);
                if (childTransform == null)
                {
                    continue;
                }

                string lrComponent = (string)child["lrComponent"];
                string fieldName = (string)child["field"];
                if (!string.IsNullOrEmpty(lrComponent) || (!string.IsNullOrEmpty(fieldName) && fieldName.Contains("Template")))
                {
                    return childTransform;
                }

                Transform foundInGrandChildren = FindCellTemplateTransform(child, childTransform);
                if (foundInGrandChildren != null)
                {
                    return foundInGrandChildren;
                }
            }

            return null;
        }

        static Type FindType(string fullName)
        {
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type t = assembly.GetType(fullName);
                if (t != null)
                {
                    return t;
                }
            }
            return null;
        }

        /// <summary>
        /// 从 GameObject 向上查找根节点，提取 Page 名称（去掉 "Page" 后缀）。
        /// 例如：GrowthFundPage -> GrowthFund
        /// </summary>
        static string GetPageNameFromRoot(GameObject go)
        {
            Transform root = go.transform.root;
            string rootName = root.name;
            if (rootName.EndsWith("Page"))
            {
                return rootName.Substring(0, rootName.Length - 4);
            }
            return rootName;
        }

        /// <summary>
        /// 获取 GameObject 的完整路径（从根节点开始）。
        /// 例如：GrowthFundPage_Demo/FundHeader/FundName
        /// </summary>
        static string GetGameObjectPath(GameObject go)
        {
            if (go == null) return "";

            var path = new System.Collections.Generic.List<string>();
            Transform current = go.transform;
            while (current != null)
            {
                path.Insert(0, current.name);
                current = current.parent;
            }
            return string.Join("/", path);
        }

        /// <summary>
        /// 写入 Language_Keys.md 到 changes/{change-id}/ 目录。
        /// change-id 从 prefabPath 提取：Assets/Editor/{Name}_Demo.prefab 中提取小写 kebab-case。
        /// 如果是非 Demo prefab（正式生成路径在 Assets/Resources/PanelUI），则不生成 md。
        /// </summary>
        static void WriteLanguageKeysMarkdown(string prefabPath, System.Collections.Generic.List<(string key, string defaultText, string path)> entries)
        {
            // 只为 Demo prefab 生成（路径包含 Assets/Editor 且文件名包含 _Demo）
            if (!prefabPath.Contains("Assets/Editor") || !prefabPath.Contains("_Demo"))
            {
                return;
            }

            // 从 prefabPath 提取 change-id：Assets/Editor/GrowthFundPage_Demo.prefab -> growth-fund
            string fileName = Path.GetFileNameWithoutExtension(prefabPath); // GrowthFundPage_Demo
            if (fileName.EndsWith("_Demo"))
            {
                fileName = fileName.Substring(0, fileName.Length - 5); // GrowthFundPage
            }
            if (fileName.EndsWith("Page"))
            {
                fileName = fileName.Substring(0, fileName.Length - 4); // GrowthFund
            }

            // 转小写 kebab-case：GrowthFund -> growth-fund
            string changeId = System.Text.RegularExpressions.Regex.Replace(fileName, "([a-z])([A-Z])", "$1-$2").ToLower();

            // 构造 changes/{change-id}/Language_Keys.md 路径
            string projectRoot = Path.GetDirectoryName(Path.GetDirectoryName(Application.dataPath)); // 从 Assets 向上两级到 D:/se/openspec
            string changesDir = Path.Combine(projectRoot, "changes", changeId);
            if (!Directory.Exists(changesDir))
            {
                Debug.LogWarning($"[LRUnityLayoutPrefabGenerator] changes/{changeId} 目录不存在，跳过 Language_Keys.md 生成");
                return;
            }

            string mdPath = Path.Combine(changesDir, "Language_Keys.md");
            var lines = new System.Collections.Generic.List<string>
            {
                "# Language Keys",
                "",
                "| Key | Default Text | Path |",
                "|-----|--------------|------|"
            };

            foreach (var (key, text, path) in entries)
            {
                // Markdown 表格转义：| 和换行符
                string escapedText = text.Replace("|", "\\|").Replace("\n", " ").Replace("\r", "");
                string escapedPath = path.Replace("|", "\\|");
                lines.Add($"| {key} | {escapedText} | {escapedPath} |");
            }

            File.WriteAllLines(mdPath, lines, System.Text.Encoding.UTF8);
            Debug.Log($"[LRUnityLayoutPrefabGenerator] 写入 Language_Keys.md: {mdPath}（{entries.Count} 条）");
        }
    }
}
