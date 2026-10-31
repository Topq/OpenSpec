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

            // 坐标转换公式的初始值：根节点的pos作为第一层的"括号公式值"
            var rootPos = ReadVector2(root["pos"]);
            Vector2 initialFormulaValue = rootPos.HasValue ? rootPos.Value : Vector2.zero;

            GameObject rootGo = BuildNode(root, null, null, initialFormulaValue);

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

            // 结构约定注入（Phase 0.5）：在保存 Prefab 前，对内存中的 GameObject 树进行
            // 约定性结构补全，不依赖 TSX 中的显式声明。
            string rootComponentId = (string)root["component"];

            // surface.page 根节点（内嵌页面，无 Canvas）：自动注入 Root 满铺容器，包裹所有子节点。
            // 参考：MixGrowthFundPage.prefab 中 MixGrowthFundPage/Root/...
            if (rootComponentId == "surface.page")
            {
                InjectRootWrapper(rootGo);
            }

            // surface.panel 根节点（独立弹窗/全屏面板，有 Canvas）：自动创建 Screen/PowerSaveMode 节点
            if (rootComponentId == "surface.panel")
            {
                InjectScreenNode(rootGo);
                InjectPowerSaveModeNode(rootGo);
                InjectWindowImageNode(rootGo);
            }

            string fullPrefabPath = prefabPath.EndsWith(".prefab") ? prefabPath : prefabPath + ".prefab";
            fullPrefabPath = fullPrefabPath.Replace("\\", "/");

            // AssetDatabase 的所有路径 API 只认正斜杠，而 Path.GetDirectoryName 在 Windows
            // 上返回反斜杠路径——不归一化会让 IsValidFolder 永远返回 false、
            // CreateFolderRecursive 又拆不出层级，导致目标目录建不出来，
            // 最终 SaveAsPrefabAsset 抛 "Given path does not exist"。
            string dir = Path.GetDirectoryName(fullPrefabPath).Replace("\\", "/");
            if (!string.IsNullOrEmpty(dir) && !AssetDatabase.IsValidFolder(dir))
            {
                CreateFolderRecursive(dir);
                AssetDatabase.Refresh();
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
            PostProcessSavedPrefabAsset(root, fullPrefabPath, jsonPath);

            Debug.Log($"[LRUnityLayoutPrefabGenerator] 生成完成: {fullPrefabPath}，字段绑定 {boundFieldCount} 个");
            return fullPrefabPath;
        }

        static void CreateFolderRecursive(string path)
        {
            // 防御：AssetDatabase 只认正斜杠，调用方可能传入 Windows 反斜杠路径
            string[] parts = path.Replace("\\", "/").Split('/');
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

        /// <summary>
        /// 布局容器类组件：它们建立新的坐标原点，后代的 pos 直接就是相对自己的偏移，
        /// 所以要把嵌套括号链清零。其它组件（按钮、文本、图标、列表…）不是容器，
        /// 后代的 pos 仍以上一层容器为原点，链条继续累积。
        /// </summary>
        static readonly HashSet<string> LayoutContainerComponents = new HashSet<string>
        {
            "surface.page",
            "surface.panel",
            "surface.modal",
        };

        static GameObject BuildNode(JObject node, Transform parent, JObject parentNode, Vector2 formulaRightPart)
        {
            bool isRoot = (parent == null);

            string prefabAssetPath = (string)node["prefabAssetPath"];
            if (!string.IsNullOrEmpty(prefabAssetPath))
            {
                return InstantiatePrefabAsset(node, parent, parentNode, formulaRightPart, prefabAssetPath);
            }

            string name = (string)node["name"] ?? "UnnamedNode";
            var go = new GameObject(name, typeof(RectTransform));
            if (parent != null)
            {
                go.transform.SetParent(parent, false);
            }

            ApplyRectTransform(go.GetComponent<RectTransform>(), node, parentNode, formulaRightPart);

            string component = (string)node["component"];
            if (!string.IsNullOrEmpty(component))
            {
                ComponentRecipes.Apply(go, component, node, isRoot);
            }

            // Canvas 组件添加时会重置 RectTransform 属性，根节点需要在此之后再次强制设置
            if (isRoot)
            {
                var rect = go.GetComponent<RectTransform>();
                rect.anchorMin = Vector2.zero;
                rect.anchorMax = Vector2.one;
                rect.pivot = new Vector2(0.5f, 0.5f);
                rect.localScale = Vector3.one;
                Debug.Log($"[BuildNode] 根节点 RectTransform 在添加组件后重新设置: {go.name}");
            }

            // 处理 data-lr-component: 显式指定额外挂载的 LR 自定义组件（如 Cell 脚本）
            string lrComponent = (string)node["lrComponent"];
            if (!string.IsNullOrEmpty(lrComponent))
            {
                ComponentRecipes.AddLRComponentPublic(go, lrComponent);
            }

            // data-visible="false"：状态互斥的隐藏占位节点（"已领取"标记等）。
            // 列表 Cell 模板不需要显式写这个属性——ConfigureSingleScrollView 会统一关掉，
            // 与项目里现有 Prefab 的 m_CellTemplate 一致（模板节点始终 m_IsActive: 0）。
            if (string.Equals((string)node["visible"], "false", StringComparison.OrdinalIgnoreCase))
            {
                go.SetActive(false);
            }

            var childrenToken = node["children"] as JArray;
            if (childrenToken != null)
            {
                // 计算传递给"子节点"的括号公式值。当前节点自身的 anchoredPosition 上面
                // ApplyRectTransform 已经用传入的 formulaRightPart 算过了，这里只决定后代怎么算：
                //
                // - 布局容器（LayoutContainerComponents）：建立新原点，给后代清零，
                //   于是容器内所有后代的 pos 都直接作为 anchoredPosition
                // - 其它节点（根节点、按钮、文本、图标、列表…）：不建立新原点，原样透传。
                //   非容器节点如果在这里推进链条（pos - formulaRightPart），容器的清零就只能
                //   生效一层——孙节点会再以父节点的偏移为原点算一遍而被顶走，
                //   例如 Cell 里的文本、按钮上的红点角标。透传才能让清零一路传到深层后代。
                Vector2 childFormulaRightPart = formulaRightPart;

                if (!isRoot && LayoutContainerComponents.Contains((string)node["component"]))
                {
                    childFormulaRightPart = Vector2.zero;
                }

                foreach (JObject child in childrenToken.OfType<JObject>())
                {
                    BuildChildOrPrefabRef(child, go.transform, node, childFormulaRightPart);
                }
            }

            return go;
        }

        static void BuildChildOrPrefabRef(JObject child, Transform parent, JObject parentNode, Vector2 formulaRightPart)
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
                        BuildChildOrPrefabRef(grandChild, existing, child, formulaRightPart);
                    }
                }
                return;
            }

            BuildNode(child, parent, parentNode, formulaRightPart);
        }

        static GameObject InstantiatePrefabAsset(JObject node, Transform parent, JObject parentNode, Vector2 formulaRightPart, string prefabAssetPath)
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
                ApplyRectTransform(rect, node, parentNode, formulaRightPart);
            }
            return instance;
        }

        static void ApplyRectTransform(RectTransform rect, JObject node, JObject parentNode, Vector2 formulaRightPart)
        {
            // Prefab 根节点默认值：满铺锚点 + 居中 pivot + 正常缩放
            // 参考所有现有 Panel Prefab（SeasonMainPanel0、AdventureBlendEntryPanel 等）
            bool isRoot = rect.parent == null;
            if (isRoot)
            {
                // 根节点强制满铺锚点（忽略 JSON 中的 anchors 字段）
                rect.anchorMin = Vector2.zero;
                rect.anchorMax = Vector2.one;
                rect.pivot = new Vector2(0.5f, 0.5f);
                rect.localScale = Vector3.one;
                Debug.Log($"[ApplyRectTransform] 根节点默认值已设置: {rect.name}, anchorMax={rect.anchorMax}, pivot={rect.pivot}, localScale={rect.localScale}");
            }

            // 非根节点才应用 JSON 中的 anchors/anchorMin/anchorMax
            if (!isRoot)
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
            }

            // pivot 允许 JSON 覆盖（根节点和非根节点都一样）
            var pivot = ReadVector2(node["pivot"]);
            if (pivot.HasValue && !isRoot)  // 根节点 pivot 已在上面设置，不覆盖
            {
                rect.pivot = pivot.Value;
            }

            // 坐标转换公式（嵌套括号形式），沿 surface.panel 链展开：
            // 根节点：anchoredPosition = (0, 0)
            // 第2层：anchoredPosition = 当前pos - 根pos
            // 第3层：anchoredPosition = 当前pos - (第2层pos - 根pos)
            // 第4层：anchoredPosition = 当前pos - (第3层pos - (第2层pos - 根pos))
            //
            // formulaRightPart 传递的是"括号内的公式值"：
            // - 对于根节点的子节点：formulaRightPart = 根pos
            // - 对于 surface.panel 的后代：formulaRightPart = 该 panel 的 anchoredPosition
            // - 对于 surface.page 的后代：formulaRightPart = (0,0)，
            //   page 下的 pos 已经是相对父节点的偏移，直接作为 anchoredPosition
            var pos = ReadVector2(node["pos"]);
            if (pos.HasValue)
            {
                if (isRoot)
                {
                    // 根节点：满铺锚点下，anchoredPosition 必须是 (0,0)
                    rect.anchoredPosition = Vector2.zero;
                }
                else
                {
                    // 非根节点：当前pos - formulaRightPart
                    rect.anchoredPosition = pos.Value - formulaRightPart;
                }
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

        static void PostProcessSavedPrefabAsset(JObject jsonRoot, string prefabPath, string jsonPath)
        {
            GameObject prefabAsset = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            if (prefabAsset == null)
            {
                Debug.LogWarning($"[LRUnityLayoutPrefabGenerator] 无法加载 Prefab 资产用于后处理: {prefabPath}");
                return;
            }

            // Phase 2.1: 修复根节点 RectTransform（SaveAsPrefabAsset 时 Unity 会重置 Canvas 根节点的 RectTransform）
            var rootRect = prefabAsset.GetComponent<RectTransform>();
            if (rootRect != null)
            {
                rootRect.anchorMin = Vector2.zero;
                rootRect.anchorMax = Vector2.one;
                rootRect.pivot = new Vector2(0.5f, 0.5f);
                rootRect.anchoredPosition = Vector2.zero;
                rootRect.sizeDelta = Vector2.zero;  // 满铺锚点下 sizeDelta 必须是 (0,0)
                rootRect.localScale = Vector3.one;
                Debug.Log($"[PostProcessSavedPrefabAsset] 根节点 RectTransform 已修复: {prefabAsset.name}");
            }

            int localizerCount = 0;
            int scrollViewCount = 0;
            var localizerEntries = new System.Collections.Generic.List<(string key, string defaultText, string path)>();
            PostProcessNode(jsonRoot, prefabAsset, ref localizerCount, ref scrollViewCount, localizerEntries);

            // Phase 2.5: 已移除 FixWindowNodePosition 调用
            // 坐标应该在 ApplyRectTransform 中根据父节点正确转换

            // Phase 2.6: 设置所有节点 Layer 为 UI
            SetLayerRecursively(prefabAsset, LayerMask.NameToLayer("UI"));

            EditorUtility.SetDirty(prefabAsset);
            PrefabUtility.SavePrefabAsset(prefabAsset);
            AssetDatabase.SaveAssets();

            Debug.Log($"[LRUnityLayoutPrefabGenerator] 后处理完成: {prefabPath}，Localizer +{localizerCount}，SingleScrollView 配置 {scrollViewCount} 个");

            // 写入 Language_Keys.md
            if (localizerEntries.Count > 0)
            {
                WriteLanguageKeysMarkdown(jsonPath, localizerEntries);
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

            // list.single-scroll / list.scroll -> 配置 CellTemplate/CellWidth/CellHeight。
            // m_CellTemplate 是基类 LR.ScrollView 的字段，多列网格列表同样需要模板
            // （项目里 400 个用 LR.ScrollView 的 Prefab 有 393 个 m_CellTemplate 非空）。
            if (component == "list.single-scroll" || component == "list.scroll")
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
        /// or list.scroll node's ScrollView component via SerializedObject, per the
        /// standard pattern: SerializedObject -> FindProperty -> set value ->
        /// ApplyModifiedProperties. These three fields are declared on the base
        /// LR.ScrollView, so both recipes go through here.
        /// Returns true if a template was found and fields were applied.
        /// </summary>
        static bool ConfigureSingleScrollView(JObject node, GameObject go)
        {
            Component scrollView = go.GetComponent("LR.SingleScrollView");
            if (scrollView == null)
            {
                scrollView = go.GetComponent("LR.ScrollView");
            }

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

            // 模板节点本身不参与显示，运行时由 ObjectCache 复制出真正的 Cell。
            // 项目里所有现有 Prefab 的 m_CellTemplate 都是 m_IsActive: 0，这里对齐。
            templateTransform.gameObject.SetActive(false);

            Debug.Log($"[LRUnityLayoutPrefabGenerator] 配置 SingleScrollView {go.name}: CellTemplate={templateTransform.name}, CellWidth={cellWidth}, CellHeight={cellHeight}");
            return true;
        }

        /// <summary>
        /// Walks a list.single-scroll JSON node's children in lockstep with the real
        /// Transform hierarchy, looking for the first descendant that marks itself as
        /// the reusable cell template, and returns its actual Transform. A node marks
        /// itself as the template in one of three ways:
        ///   - data-cell-template="true" -- the explicit marker, needed when the cell
        ///     has neither its own MonoBehaviour nor a [SerializeField] on the page
        ///     script (the page's onCellUpdate just does root.Find("TxtXxx"))
        ///   - data-lr-component -- the cell has its own MonoBehaviour, e.g.
        ///     data-lr-component="LR.MixGrowthFundRewardTierRow"
        ///   - a data-field name containing "Template" -- backwards compatibility with
        ///     TSX written before the two attributes above existed
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
                bool markedAsCellTemplate = string.Equals((string)child["cellTemplate"], "true", StringComparison.OrdinalIgnoreCase);
                if (markedAsCellTemplate
                    || !string.IsNullOrEmpty(lrComponent)
                    || (!string.IsNullOrEmpty(fieldName) && fieldName.Contains("Template")))
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
        /// surface.page 根节点的 Root 满铺容器注入。
        /// 在内存中的 rootGo 下创建名为 "Root" 的满铺子节点，把所有原有直接子节点移入其中。
        /// </summary>
        static void InjectRootWrapper(GameObject rootGo)
        {
            if (rootGo.transform.childCount == 0) return;

            // 收集现有所有直接子节点
            var children = new System.Collections.Generic.List<Transform>();
            for (int i = 0; i < rootGo.transform.childCount; i++)
                children.Add(rootGo.transform.GetChild(i));

            // 创建 Root 满铺容器
            var rootNode = new GameObject("Root", typeof(RectTransform));
            rootNode.transform.SetParent(rootGo.transform, false);

            // [注释] 不再强制设置 Root 的 RectTransform 属性，让它按 TSX 定义来
            /*
            var rt = rootNode.GetComponent<RectTransform>();
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.anchoredPosition = Vector2.zero;
            rt.sizeDelta = Vector2.zero;
            rt.pivot = new Vector2(0.5f, 0.5f);
            */

            // 把所有原有子节点移入 Root
            foreach (var child in children)
                child.SetParent(rootNode.transform, false);

            Debug.Log($"[LRUnityLayoutPrefabGenerator] InjectRootWrapper: {rootGo.name} → Root 注入完成，{children.Count} 个子节点移入");
        }

        /// <summary>
        /// 递归设置 GameObject 及其所有子节点的 Layer
        /// </summary>
        static void SetLayerRecursively(GameObject go, int layer)
        {
            go.layer = layer;
            foreach (Transform child in go.transform)
            {
                SetLayerRecursively(child.gameObject, layer);
            }
        }

        /// <summary>
        /// Phase 0.5: surface.panel 根节点自动注入 Screen 遮罩节点。
        /// 在 TSX 子节点之前插入，作为最底层的半透明背景遮罩。
        /// </summary>
        static void InjectScreenNode(GameObject rootGo)
        {
            GameObject screenGo = null;
            bool needCreate = false;

            // 检查是否已经有 Screen 节点
            var screenTransform = rootGo.transform.Find("Screen");
            if (screenTransform != null)
            {
                screenGo = screenTransform.gameObject;
                Debug.Log($"[LRUnityLayoutPrefabGenerator] InjectScreenNode: Screen 节点已存在，检查组件完整性");
            }
            else
            {
                // 创建 Screen 节点（满铺、半透明遮罩）
                screenGo = new GameObject("Screen", typeof(RectTransform));
                screenGo.transform.SetParent(rootGo.transform, false);
                screenGo.transform.SetAsFirstSibling();  // 放在最底层
                needCreate = true;

                var screenRect = screenGo.GetComponent<RectTransform>();
                screenRect.anchorMin = Vector2.zero;
                screenRect.anchorMax = Vector2.one;
                screenRect.anchoredPosition = Vector2.zero;
                screenRect.sizeDelta = Vector2.zero;
                screenRect.pivot = new Vector2(0.5f, 0.5f);
            }

            // 确保有 Image 组件（遮罩底色 #0000009A = rgba(0,0,0,0.6)）
            var image = screenGo.GetComponent<Image>();
            if (image == null)
            {
                image = screenGo.AddComponent<Image>();
                image.color = new Color(0f, 0f, 0f, 0.6f);
                image.raycastTarget = true;
                Debug.Log($"[LRUnityLayoutPrefabGenerator] InjectScreenNode: {screenGo.name} 添加 Image 组件");
            }

            // 确保有 CanvasGroup 组件（控制整体透明度和交互屏蔽）
            if (screenGo.GetComponent<CanvasGroup>() == null)
            {
                screenGo.AddComponent<CanvasGroup>();
                Debug.Log($"[LRUnityLayoutPrefabGenerator] InjectScreenNode: {screenGo.name} 添加 CanvasGroup 组件");
            }

            if (needCreate)
            {
                Debug.Log($"[LRUnityLayoutPrefabGenerator] InjectScreenNode: {rootGo.name} → Screen 节点已注入");
            }
        }

        /// <summary>
        /// Phase 0.5: surface.panel 根节点自动注入 PowerSaveMode 节点。
        /// 放在 Screen 之后，用于控制相机渲染模式。
        /// </summary>
        static void InjectPowerSaveModeNode(GameObject rootGo)
        {
            // 如果已经有 PowerSaveMode 节点，跳过
            if (rootGo.transform.Find("PowerSaveMode") != null)
            {
                Debug.Log($"[LRUnityLayoutPrefabGenerator] InjectPowerSaveModeNode: PowerSaveMode 节点已存在，跳过创建");
                return;
            }

            // 创建 PowerSaveMode 节点（满铺、不可见）
            var pmGo = new GameObject("PowerSaveMode", typeof(RectTransform));
            pmGo.transform.SetParent(rootGo.transform, false);

            // 放在 Screen 之后（索引 1）
            int screenIndex = -1;
            for (int i = 0; i < rootGo.transform.childCount; i++)
            {
                if (rootGo.transform.GetChild(i).name == "Screen")
                {
                    screenIndex = i;
                    break;
                }
            }
            if (screenIndex >= 0)
            {
                pmGo.transform.SetSiblingIndex(screenIndex + 1);
            }

            var pmRect = pmGo.GetComponent<RectTransform>();
            pmRect.anchorMin = Vector2.zero;
            pmRect.anchorMax = Vector2.one;
            pmRect.anchoredPosition = Vector2.zero;
            pmRect.sizeDelta = Vector2.zero;
            pmRect.pivot = new Vector2(0.5f, 0.5f);

            // 添加 LR.SwitchMainCamera
            Type switchCamType = FindType("LR.SwitchMainCamera");
            if (switchCamType != null)
            {
                pmGo.AddComponent(switchCamType);
            }

            // 添加 PowerSaveMode
            Type powerSaveType = FindType("PowerSaveMode");
            if (powerSaveType != null)
            {
                pmGo.AddComponent(powerSaveType);
            }

            Debug.Log($"[LRUnityLayoutPrefabGenerator] InjectPowerSaveModeNode: {rootGo.name} → PowerSaveMode 节点已注入");
        }

        /// <summary>
        /// Phase 0.5: surface.panel 根节点下的 Window 节点自动添加 Image 组件作为底框。
        /// 在生成 Panel 时，为 Window 节点添加白色 Image 组件，确保至少有一个可见的底框。
        /// </summary>
        static void InjectWindowImageNode(GameObject rootGo)
        {
            // 查找 Window 节点（通常在根节点下第一层）
            Transform windowTransform = rootGo.transform.Find("Window");
            if (windowTransform == null)
            {
                Debug.Log($"[LRUnityLayoutPrefabGenerator] InjectWindowImageNode: 未找到 Window 节点，跳过添加 Image");
                return;
            }

            GameObject windowGo = windowTransform.gameObject;

            // 检查是否已经有 Image 组件
            var existingImage = windowGo.GetComponent<Image>();
            if (existingImage != null)
            {
                Debug.Log($"[LRUnityLayoutPrefabGenerator] InjectWindowImageNode: Window 节点已有 Image 组件，跳过添加");
                return;
            }

            // 添加 Image 组件
            var image = windowGo.AddComponent<Image>();
            image.color = new Color(1f / 255f, 1f / 255f, 1f / 255f, 204f / 255f);  // RGB(1,1,1) Alpha=204
            image.raycastTarget = true;

            Debug.Log($"[LRUnityLayoutPrefabGenerator] InjectWindowImageNode: Window 节点已添加 Image 组件（颜色: #010101, Alpha=204）");
        }

        /// <summary>
        /// 确保 Screen 节点存在，如果不存在则创建，然后补全组件。
        /// </summary>
        static void EnsureAndPatchScreenNode(GameObject rootGo)
        {
            var screenTransform = rootGo.transform.Find("Screen");
            GameObject screenGo;

            if (screenTransform == null)
            {
                // 使用 Prefab 编辑上下文创建节点（确保能保存到 Prefab 资产）
                string prefabPath = PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(rootGo);
                if (string.IsNullOrEmpty(prefabPath))
                {
                    // rootGo 本身就是 Prefab 资产，需要在其根下创建
                    screenGo = new GameObject("Screen", typeof(RectTransform));
                    screenGo.transform.SetParent(rootGo.transform, false);
                }
                else
                {
                    // rootGo 是 Prefab 实例，直接创建即可
                    screenGo = new GameObject("Screen", typeof(RectTransform));
                    screenGo.transform.SetParent(rootGo.transform, false);
                }

                screenGo.transform.SetAsFirstSibling();  // 放在最底层

                var screenRect = screenGo.GetComponent<RectTransform>();
                screenRect.anchorMin = Vector2.zero;
                screenRect.anchorMax = Vector2.one;
                screenRect.anchoredPosition = Vector2.zero;
                screenRect.sizeDelta = Vector2.zero;
                screenRect.pivot = new Vector2(0.5f, 0.5f);

                Debug.Log($"[LRUnityLayoutPrefabGenerator] EnsureAndPatchScreenNode: 自动创建 Screen 节点");
            }
            else
            {
                screenGo = screenTransform.gameObject;
            }

            // 添加 Image（遮罩底色）
            var image = screenGo.GetComponent<Image>();
            if (image == null)
            {
                image = screenGo.AddComponent<Image>();
                image.color = new Color(0f, 0f, 0f, 0.6f);
                image.raycastTarget = true;
                Debug.Log($"[LRUnityLayoutPrefabGenerator] EnsureAndPatchScreenNode: {screenGo.name} 添加 Image（#0000009A）");
            }

            // 添加 CanvasGroup（控制整体透明度和交互屏蔽）
            if (screenGo.GetComponent<CanvasGroup>() == null)
            {
                screenGo.AddComponent<CanvasGroup>();
                Debug.Log($"[LRUnityLayoutPrefabGenerator] EnsureAndPatchScreenNode: {screenGo.name} 添加 CanvasGroup");
            }
        }

        /// <summary>
        /// 确保 PowerSaveMode 节点存在，如果不存在则创建，然后补全组件。
        /// </summary>
        static void EnsureAndPatchPowerSaveModeNode(GameObject rootGo)
        {
            var pmTransform = rootGo.transform.Find("PowerSaveMode");
            GameObject pmGo;

            if (pmTransform == null)
            {
                // 创建 PowerSaveMode 节点（满铺、不可见）
                pmGo = new GameObject("PowerSaveMode", typeof(RectTransform));
                pmGo.transform.SetParent(rootGo.transform, false);
                pmGo.transform.SetSiblingIndex(1);  // 放在 Screen 后面

                var pmRect = pmGo.GetComponent<RectTransform>();
                pmRect.anchorMin = Vector2.zero;
                pmRect.anchorMax = Vector2.one;
                pmRect.anchoredPosition = Vector2.zero;
                pmRect.sizeDelta = Vector2.zero;
                pmRect.pivot = new Vector2(0.5f, 0.5f);

                Debug.Log($"[LRUnityLayoutPrefabGenerator] EnsureAndPatchPowerSaveModeNode: 自动创建 PowerSaveMode 节点");
            }
            else
            {
                pmGo = pmTransform.gameObject;
            }

            // 添加 LR.SwitchMainCamera
            Type switchCamType = FindType("LR.SwitchMainCamera");
            if (switchCamType != null && pmGo.GetComponent(switchCamType) == null)
            {
                pmGo.AddComponent(switchCamType);
                Debug.Log($"[LRUnityLayoutPrefabGenerator] EnsureAndPatchPowerSaveModeNode: {pmGo.name} 添加 LR.SwitchMainCamera");
            }

            // 添加 PowerSaveMode
            Type powerSaveType = FindType("PowerSaveMode");
            if (powerSaveType != null && pmGo.GetComponent(powerSaveType) == null)
            {
                pmGo.AddComponent(powerSaveType);
                Debug.Log($"[LRUnityLayoutPrefabGenerator] EnsureAndPatchPowerSaveModeNode: {pmGo.name} 添加 PowerSaveMode");
            }
        }

        /// <summary>
        /// surface.panel 根节点的 Screen 遮罩节点组件补全。
        /// 为名为 "Screen" 的直接子节点添加 Image（#00000080）+ CanvasGroup，使其成为有效的半透明遮罩。
        /// 参考：AdventureBlendEntryPanel.prefab/Screen
        /// </summary>
        static void PatchScreenNode(GameObject rootGo)
        {
            var screenTransform = rootGo.transform.Find("Screen");
            if (screenTransform == null) return;
            var screenGo = screenTransform.gameObject;

            // Image（遮罩底色）
            var image = screenGo.GetComponent<Image>();
            if (image == null)
            {
                image = screenGo.AddComponent<Image>();
                image.color = new Color(0f, 0f, 0f, 0.6f);
                image.raycastTarget = true;
                Debug.Log($"[LRUnityLayoutPrefabGenerator] PatchScreenNode: {screenGo.name} 添加 Image（#0000009A）");
            }

            // CanvasGroup（控制整体透明度和交互屏蔽）
            if (screenGo.GetComponent<CanvasGroup>() == null)
            {
                screenGo.AddComponent<CanvasGroup>();
                Debug.Log($"[LRUnityLayoutPrefabGenerator] PatchScreenNode: {screenGo.name} 添加 CanvasGroup");
            }
        }

        /// <summary>
        /// surface.panel 根节点的 PowerSaveMode 节点组件补全。
        /// 为名为 "PowerSaveMode" 的直接子节点添加 LR.SwitchMainCamera + PowerSaveMode。
        /// 参考：SeasonMainPanel0.prefab/PowerSaveMode
        /// </summary>
        static void PatchPowerSaveModeNode(GameObject rootGo)
        {
            var pmTransform = rootGo.transform.Find("PowerSaveMode");
            if (pmTransform == null) return;
            var pmGo = pmTransform.gameObject;

            Type switchCamType = FindType("LR.SwitchMainCamera");
            if (switchCamType != null && pmGo.GetComponent(switchCamType) == null)
            {
                pmGo.AddComponent(switchCamType);
                Debug.Log($"[LRUnityLayoutPrefabGenerator] PatchPowerSaveModeNode: {pmGo.name} 添加 LR.SwitchMainCamera");
            }

            Type powerSaveType = FindType("PowerSaveMode");
            if (powerSaveType != null && pmGo.GetComponent(powerSaveType) == null)
            {
                pmGo.AddComponent(powerSaveType);
                Debug.Log($"[LRUnityLayoutPrefabGenerator] PatchPowerSaveModeNode: {pmGo.name} 添加 PowerSaveMode");
            }
        }

        /// <summary>
        /// 写入 Language_Keys.md 到 changes/{change-id}/ 目录。
        /// change-id 从 prefabPath 提取：Assets/Editor/{Name}_Demo.prefab 中提取小写 kebab-case。
        /// 如果是非 Demo prefab（正式生成路径在 Assets/Resources/PanelUI），则不生成 md。
        /// </summary>
        static void WriteLanguageKeysMarkdown(string jsonPath, System.Collections.Generic.List<(string key, string defaultText, string path)> entries)
        {
            // jsonPath 形如：D:/se/openspec/changes/month-card-activity/demo/unity/XXX.json
            // 直接从路径中提取 changes/ 所在的目录和 change-id，不依赖 prefabPath 或 Application.dataPath
            string normalized = jsonPath.Replace("\\", "/");
            int changesIdx = normalized.IndexOf("/changes/");
            if (changesIdx < 0)
            {
                Debug.LogWarning($"[LRUnityLayoutPrefabGenerator] jsonPath 中未找到 /changes/ 目录，跳过 Language_Keys.md 生成: {jsonPath}");
                return;
            }

            string openspecRoot = normalized.Substring(0, changesIdx); // D:/se/openspec
            string afterChanges = normalized.Substring(changesIdx + "/changes/".Length); // month-card-activity/demo/unity/XXX.json
            int nextSlash = afterChanges.IndexOf('/');
            string changeId = nextSlash >= 0 ? afterChanges.Substring(0, nextSlash) : afterChanges; // month-card-activity

            string changesDir = Path.Combine(openspecRoot, "changes", changeId);
            if (!Directory.Exists(changesDir))
            {
                Debug.LogWarning($"[LRUnityLayoutPrefabGenerator] changes/{changeId} 目录不存在，跳过 Language_Keys.md 生成");
                return;
            }

            string mdPath = Path.Combine(changesDir, "Language_Keys.md");

            // 读取已有内容，合并去重后回写（避免覆盖 lr-openspec-apply 写入的其他 key）
            var existingKeys = new System.Collections.Generic.HashSet<string>();
            var existingLines = new System.Collections.Generic.List<string>();
            if (File.Exists(mdPath))
            {
                foreach (var line in File.ReadAllLines(mdPath, System.Text.Encoding.UTF8))
                {
                    existingLines.Add(line);
                    // 提取已有 key（表格行格式：| key | ... |）
                    if (line.StartsWith("| ") && !line.StartsWith("| Key ") && !line.StartsWith("|---"))
                    {
                        var parts = line.Split('|');
                        if (parts.Length >= 2)
                        {
                            existingKeys.Add(parts[1].Trim());
                        }
                    }
                }
            }
            else
            {
                existingLines.Add("| Key | Default Text |");
                existingLines.Add("|-----|--------------|");
            }

            int newCount = 0;
            foreach (var (key, text, goPath) in entries)
            {
                if (existingKeys.Contains(key)) continue;
                string escapedText = text.Replace("|", "\\|").Replace("\n", " ").Replace("\r", "");
                existingLines.Add($"| {key} | {escapedText} |");
                newCount++;
            }

            File.WriteAllLines(mdPath, existingLines, System.Text.Encoding.UTF8);
            Debug.Log($"[LRUnityLayoutPrefabGenerator] 写入 Language_Keys.md: {mdPath}（新增 {newCount} 条，已有 {existingKeys.Count} 条）");
        }
    }
}
