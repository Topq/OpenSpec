using System;
using Newtonsoft.Json.Linq;
using TMPro;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;

namespace LRUIPrefabGen
{
    /// <summary>
    /// Applies the Unity component recipe for a semantic data-component ID.
    /// Mirrors .claude/skills/lr-design/references/unity-ui-components.md --
    /// that document is the source of truth; keep this switch in sync with it
    /// whenever the whitelist changes.
    /// </summary>
    public static class ComponentRecipes
    {
        // Global default text style (unity-ui-components.md "全局默认样式").
        const string DefaultFont = "Assets/Resources/Font/fzhjtSDF.asset";

        public static void Apply(GameObject go, string componentId, JObject node, bool isRoot = false)
        {
            // 处理样式变体（如 text.localized 的 title/body 样式）
            // 注意：JSON 布局节点里的键名是 "textStyle"（tsx_to_json.py 把 TSX 的
            // data-lr-style 属性转换成这个键），不是 "data-lr-style" 原始属性名。
            string semanticId = componentId;
            string style = (string)node?["textStyle"];
            if (!string.IsNullOrEmpty(style))
            {
                // 尝试加载 componentId-style 配方（如 text.localized-title）
                var variantRecipe = ComponentRecipeLoader.Get($"{componentId}-{style}");
                if (variantRecipe != null)
                {
                    semanticId = $"{componentId}-{style}";
                }
            }

            // 优先从 JSON 配方加载（新架构）
            var recipe = ComponentRecipeLoader.Get(semanticId);
            if (recipe != null)
            {
                ApplyFromRecipe(go, recipe, node, isRoot);
                return;
            }

            // 所有白名单语义 ID 现在都有 JSON 配方（见 ComponentRecipes/*.json），
            // 走不到这里就说明 ID 未识别或配方加载失败。
            Debug.LogWarning($"[LRComponentRecipes] 未识别的语义组件 ID: {componentId}（GameObject={go.name}），只创建了 RectTransform");
            ApplyLayoutGroup(go, node);
        }

        static void ApplyLayoutGroup(GameObject go, JObject node)
        {
            string layoutGroup = (string)node["layoutGroup"];
            if (string.IsNullOrEmpty(layoutGroup))
            {
                return;
            }

            HorizontalOrVerticalLayoutGroup group = layoutGroup == "Horizontal"
                ? (HorizontalOrVerticalLayoutGroup)go.AddComponent<HorizontalLayoutGroup>()
                : go.AddComponent<VerticalLayoutGroup>();

            var spacingToken = node["layoutSpacing"];
            if (spacingToken != null)
            {
                group.spacing = (float)spacingToken;
            }

            var paddingArr = node["layoutPadding"] as JArray;
            if (paddingArr != null && paddingArr.Count >= 4)
            {
                group.padding = new RectOffset(
                    (int)paddingArr[0], (int)paddingArr[1], (int)paddingArr[2], (int)paddingArr[3]);
            }

            string childAlignment = (string)node["layoutChildAlignment"];
            if (!string.IsNullOrEmpty(childAlignment) && Enum.TryParse(childAlignment, out TextAnchor anchor))
            {
                group.childAlignment = anchor;
            }
        }

        /// <summary>
        /// 反射挂载组件，并补齐依赖组件。
        ///
        /// 必须走这个方法而不是直接 go.AddComponent(type)，有两类依赖要补：
        ///
        /// 1. [RequireComponent] 声明的依赖。Unity 只在编辑器里通过菜单/Inspector 添加
        ///    组件时才自动补，用反射 AddComponent(Type) 不会触发。
        ///
        /// 2. Graphic 子类需要的 CanvasRenderer。注意 Graphic 上只有
        ///    [RequireComponent(typeof(RectTransform))]，并没有声明 CanvasRenderer——
        ///    那是编辑器 GraphicEditor 添加组件时补的，所以第 1 条覆盖不到，必须显式判断。
        ///    缺了 CanvasRenderer 运行时会在 RectMask2D.PerformClipping 里抛
        ///    MissingComponentException（"There is no 'CanvasRenderer' attached to ..."），
        ///    而且只有 ScrollView 裁剪到该节点时才炸，生成期完全看不出来。
        ///    工程现状印证了这个约定：真实 Prefab 里 RaycastArea 带 CanvasRenderer 的 865 个，
        ///    不带的只有 15 个。
        /// </summary>
        static Component AddComponentWithRequirements(GameObject go, Type type)
        {
            foreach (RequireComponent req in type.GetCustomAttributes(typeof(RequireComponent), true))
            {
                foreach (Type dep in new[] { req.m_Type0, req.m_Type1, req.m_Type2 })
                {
                    if (dep != null && go.GetComponent(dep) == null)
                    {
                        go.AddComponent(dep);
                    }
                }
            }

            if (typeof(Graphic).IsAssignableFrom(type) && go.GetComponent<CanvasRenderer>() == null)
            {
                go.AddComponent<CanvasRenderer>();
            }

            return go.AddComponent(type);
        }

        static void AddLRComponent(GameObject go, string fullTypeName)
        {
            Type type = FindType(fullTypeName);
            if (type == null)
            {
                Debug.LogWarning($"[LRComponentRecipes] 未找到类型: {fullTypeName}（GameObject={go.name}），跳过挂载");
                return;
            }
            if (go.GetComponent(type) == null)
            {
                AddComponentWithRequirements(go, type);
            }
        }

        // 公开给 LRUnityLayoutPrefabGenerator 调用（处理 data-lr-component 属性）
        public static void AddLRComponentPublic(GameObject go, string fullTypeName)
        {
            AddLRComponent(go, fullTypeName);
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

        static T LoadAsset<T>(string path) where T : UnityEngine.Object
        {
            T asset = AssetDatabase.LoadAssetAtPath<T>(path);
            if (asset == null)
            {
                Debug.LogWarning($"[LRComponentRecipes] 未找到资源: {path}");
            }
            return asset;
        }

        /// <summary>
        /// 根据 Button 节点名称返回默认 sprite 路径。
        /// 调研报告：按钮通常设置默认按钮图。
        /// </summary>
        static string GetDefaultSpriteForButton(string nodeName)
        {
            if (string.IsNullOrEmpty(nodeName))
                return null;

            string lowerName = nodeName.ToLower();

            // 关闭按钮
            if (lowerName.Contains("close") || lowerName.Contains("exit"))
            {
                return "Assets/UI/AtlasResources/CommonPanel/ty_btn_tk_btn_01.png";
            }

            // 普通按钮默认图（已在配方里设置，这里返回 null 避免覆盖）
            return null;
        }

        /// <summary>
        /// 从 JSON 配方应用组件配置（新架构）
        /// </summary>
        static void ApplyFromRecipe(GameObject go, ComponentRecipe recipe, JObject node, bool isRoot)
        {
            // 1. 挂载主组件
            Type componentType = FindType(recipe.componentType);
            if (componentType == null)
            {
                Debug.LogWarning($"[ComponentRecipes] 配方 {recipe.semanticId} 的组件类型未找到: {recipe.componentType}");
                return;
            }

            Component mainComponent = null;
            if (componentType != typeof(GameObject))
            {
                mainComponent = go.GetComponent(componentType);
                if (mainComponent == null)
                {
                    mainComponent = AddComponentWithRequirements(go, componentType);
                }
            }

            // 1.5. 挂载根节点额外组件（如 AsyncTexture）
            // **重要修复**：surface.panel 的 Canvas/GraphicRaycaster/Animator 只应在根节点添加
            if (recipe.components != null)
            {
                foreach (var compSpec in recipe.components)
                {
                    // 如果是 surface.panel 配方且不是根节点，跳过 Canvas/GraphicRaycaster/Animator
                    if (recipe.semanticId == "surface.panel" && !isRoot
                        && (compSpec.type == "UnityEngine.Canvas"
                            || compSpec.type == "UnityEngine.UI.GraphicRaycaster"
                            || compSpec.type == "UnityEngine.Animator"))
                    {
                        Debug.Log($"[ComponentRecipes] 跳过非根节点的 {compSpec.type} 组件: {go.name}");
                        continue;
                    }

                    Type compType = FindType(compSpec.type);
                    if (compType == null)
                    {
                        Debug.LogWarning($"[ComponentRecipes] 根节点组件类型未找到: {compSpec.type}");
                        continue;
                    }

                    Component comp = AddComponentWithRequirements(go, compType);

                    // 应用组件属性
                    if (compSpec.properties != null)
                    {
                        ApplyComponentProperties(comp, compSpec.properties);
                    }
                }
            }

            // 2. 创建子节点层级
            if (recipe.hierarchy != null)
            {
                foreach (var hierarchyNode in recipe.hierarchy)
                {
                    // 跳过可选且不需要的节点（未来可根据 node 里的属性判断）
                    if (!hierarchyNode.isRequired)
                    {
                        // TODO: 根据 JObject node 判断是否需要创建可选节点
                        // 目前简化处理：可选节点也创建，由后续业务代码决定是否使用
                    }

                    GameObject childGo = new GameObject(hierarchyNode.nodeName, typeof(RectTransform));
                    childGo.transform.SetParent(go.transform, false);

                    // 处理特殊位置标记
                    if (!string.IsNullOrEmpty(hierarchyNode.position))
                    {
                        if (hierarchyNode.position == "last-child")
                        {
                            childGo.transform.SetAsLastSibling();
                        }
                        // 未来可扩展: "first-child", "after:xxx" 等
                    }

                    // 应用 RectTransform 默认值
                    if (hierarchyNode.layoutDefaults != null)
                    {
                        ApplyLayoutDefaults(childGo.GetComponent<RectTransform>(), hierarchyNode.layoutDefaults);
                    }

                    // 挂载子节点组件
                    if (hierarchyNode.components != null)
                    {
                        foreach (var compSpec in hierarchyNode.components)
                        {
                            Type compType = FindType(compSpec.type);
                            if (compType == null)
                            {
                                Debug.LogWarning($"[ComponentRecipes] 组件类型未找到: {compSpec.type}");
                                continue;
                            }

                            Component comp = AddComponentWithRequirements(childGo, compType);

                            // 应用组件属性
                            if (compSpec.properties != null)
                            {
                                ApplyComponentProperties(comp, compSpec.properties);
                            }
                        }
                    }

                    // 绑定到主组件的字段
                    if (!string.IsNullOrEmpty(hierarchyNode.bindToField))
                    {
                        FieldBinder.BindField(mainComponent, hierarchyNode.bindToField, childGo);
                    }
                }
            }

            // 3. 应用主组件默认值
            if (recipe.defaultValues != null)
            {
                ApplyComponentProperties(mainComponent, recipe.defaultValues);
            }

            // 4. 执行后处理钩子（启发式逻辑）
            if (!string.IsNullOrEmpty(recipe.postProcess))
            {
                switch (recipe.postProcess)
                {
                    case "button":
                        PostProcessButton(go, node);
                        break;
                    case "async-texture":
                        PostProcessAsyncTexture(go);
                        break;
                    case "single-scroll-view":
                        PostProcessSingleScrollView(go, node);
                        break;
                    case "grid-scroll-view":
                        PostProcessGridScrollView(go, node);
                        break;
                    case "input-field":
                        PostProcessInputField(go, node);
                        break;
                    case "item-slot":
                        PostProcessItemSlot(go, node);
                        break;
                    case "modal":
                        PostProcessModal(go, node);
                        break;
                    case "reward-cell":
                        PostProcessRewardCell(go, node);
                        break;
                    case "tab-item":
                        PostProcessTabItem(go, node);
                        break;
                    default:
                        Debug.LogWarning($"[ComponentRecipes] 未知的后处理钩子: {recipe.postProcess}");
                        break;
                }
            }

            // 5. 应用 JSON layout 节点上的 "text" 字段（如果组件是 TextMeshProUGUI）
            // 注意：这里检查的是根节点挂载的所有组件，不只是 mainComponent
            if (recipe.components != null)
            {
                foreach (var comp in recipe.components)
                {
                    if (comp.type == "TMPro.TextMeshProUGUI")
                    {
                        var tmp = go.GetComponent<TextMeshProUGUI>();
                        if (tmp != null)
                        {
                            string textValue = (string)node?["text"];
                            if (!string.IsNullOrEmpty(textValue))
                            {
                                tmp.text = textValue;
                            }
                        }
                        break;
                    }
                }
            }

            // 6. 应用 JSON layout 节点上的 layoutGroup 系列属性（Horizontal/VerticalLayoutGroup）
            // 注意：这一步之前只在 switch fallback 路径末尾调用，新架构走 ApplyFromRecipe
            // 直接 return，导致所有已配方化组件都无法应用 data-layout-group 等属性，这里补上。
            ApplyLayoutGroup(go, node);
        }

        static void ApplyLayoutDefaults(RectTransform rectTransform, LayoutDefaults layout)
        {
            if (layout.anchorMin != null && layout.anchorMin.Length == 2)
            {
                rectTransform.anchorMin = new Vector2(layout.anchorMin[0], layout.anchorMin[1]);
            }
            if (layout.anchorMax != null && layout.anchorMax.Length == 2)
            {
                rectTransform.anchorMax = new Vector2(layout.anchorMax[0], layout.anchorMax[1]);
            }
            if (layout.anchoredPosition != null && layout.anchoredPosition.Length == 2)
            {
                rectTransform.anchoredPosition = new Vector2(layout.anchoredPosition[0], layout.anchoredPosition[1]);
            }
            if (layout.sizeDelta != null && layout.sizeDelta.Length == 2)
            {
                rectTransform.sizeDelta = new Vector2(layout.sizeDelta[0], layout.sizeDelta[1]);
            }
            if (layout.pivot != null && layout.pivot.Length == 2)
            {
                rectTransform.pivot = new Vector2(layout.pivot[0], layout.pivot[1]);
            }
        }

        static void ApplyComponentProperties(Component comp, System.Collections.Generic.Dictionary<string, object> properties)
        {
            Type type = comp.GetType();

            foreach (var kvp in properties)
            {
                string propName = kvp.Key;
                object value = kvp.Value;

                // 优先查找属性
                var prop = type.GetProperty(propName, System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public);
                if (prop != null && prop.CanWrite)
                {
                    object convertedValue = ConvertValue(value, prop.PropertyType);
                    if (convertedValue != null)
                    {
                        prop.SetValue(comp, convertedValue);
                        continue;
                    }
                }

                // Fallback 到字段
                var field = type.GetField(propName, System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic);
                if (field != null)
                {
                    object convertedValue = ConvertValue(value, field.FieldType);
                    if (convertedValue != null)
                    {
                        field.SetValue(comp, convertedValue);
                    }
                }
            }
        }

        static object ConvertValue(object value, Type targetType)
        {
            if (value == null) return null;

            // 处理 Sprite 资源路径
            if (targetType == typeof(Sprite) && value is string spritePath)
            {
                return LoadAsset<Sprite>(spritePath);
            }

            // 处理 Texture/Texture2D 资源路径
            if ((targetType == typeof(Texture2D) || targetType == typeof(Texture)) && value is string texturePath)
            {
                return LoadAsset<Texture2D>(texturePath);
            }

            // 处理 TMP_FontAsset 资源路径
            if (targetType == typeof(TMP_FontAsset) && value is string fontPath)
            {
                return LoadAsset<TMP_FontAsset>(fontPath);
            }

            // 处理 Material 资源路径
            if (targetType == typeof(Material) && value is string materialPath)
            {
                return LoadAsset<Material>(materialPath);
            }

            // 处理枚举
            if (targetType.IsEnum)
            {
                if (value is string strValue)
                {
                    try
                    {
                        return Enum.Parse(targetType, strValue, true);
                    }
                    catch
                    {
                        Debug.LogWarning($"[ComponentRecipes] 无法将 '{strValue}' 转换为枚举 {targetType.Name}");
                        return null;
                    }
                }
            }

            // 处理颜色字符串 "#FFFFFF"
            if (targetType == typeof(Color) && value is string colorStr)
            {
                if (ColorUtility.TryParseHtmlString(colorStr, out Color color))
                {
                    return color;
                }
            }

            // 处理数组（JSON 反序列化后可能是 JArray 或 List）
            if (targetType.IsArray && value is Newtonsoft.Json.Linq.JArray jArray)
            {
                Type elemType = targetType.GetElementType();
                Array array = Array.CreateInstance(elemType, jArray.Count);
                for (int i = 0; i < jArray.Count; i++)
                {
                    array.SetValue(Convert.ChangeType(jArray[i].ToObject<object>(), elemType), i);
                }
                return array;
            }

            // 基础类型转换
            try
            {
                return Convert.ChangeType(value, targetType);
            }
            catch
            {
                Debug.LogWarning($"[ComponentRecipes] 无法将 {value.GetType().Name} 转换为 {targetType.Name}");
                return null;
            }
        }

        /// <summary>
        /// Button 组件的后处理钩子：推断默认图片、条件生成 Text 子节点
        /// </summary>
        static void PostProcessButton(GameObject go, JObject node)
        {
            var image = go.GetComponent<Image>();
            var button = go.GetComponent<Button>();

            if (image == null || button == null)
            {
                Debug.LogWarning($"[ComponentRecipes] PostProcessButton 失败：GameObject {go.name} 缺少 Image 或 Button 组件");
                return;
            }

            // 1. 绑定 Button.targetGraphic
            button.targetGraphic = image;

            // 2. 根据节点名推断默认 sprite（关闭按钮使用特殊图片，覆盖配方默认值）
            if (node != null)
            {
                string nodeName = (string)node["name"];
                string defaultSpritePath = GetDefaultSpriteForButton(nodeName);
                if (!string.IsNullOrEmpty(defaultSpritePath))
                {
                    image.sprite = LoadAsset<Sprite>(defaultSpritePath);
                }
            }

            // 3. 条件自动生成 Text 子节点
            if (node != null)
            {
                bool hasExplicitChildren = node["children"] is JArray childrenArr && childrenArr.Count > 0;
                string text = (string)node["text"];
                if (!hasExplicitChildren && !string.IsNullOrEmpty(text))
                {
                    GameObject textGo = new GameObject("Text", typeof(RectTransform));
                    textGo.transform.SetParent(go.transform, false);
                    var textRect = textGo.GetComponent<RectTransform>();
                    textRect.anchorMin = Vector2.zero;
                    textRect.anchorMax = Vector2.one;
                    textRect.sizeDelta = Vector2.zero;

                    var tmp = textGo.AddComponent<TextMeshProUGUI>();
                    tmp.text = text;
                    tmp.fontSize = 24f;
                    tmp.color = Color.white;
                    tmp.alignment = TextAlignmentOptions.Center;
                    tmp.font = LoadAsset<TMP_FontAsset>(DefaultFont);
                    tmp.fontSharedMaterial = LoadAsset<Material>("Assets/Resources/Font/fzhjtSDF_UI_OutLine1Px.mat");
                }
            }
        }

        /// <summary>
        /// AsyncTexture 组件的后处理钩子：绑定 m_RawImage 到同节点的 RawImage 组件
        /// </summary>
        static void PostProcessAsyncTexture(GameObject go)
        {
            var asyncTexture = go.GetComponent(FindType("LR.AsyncTexture"));
            var rawImage = go.GetComponent<RawImage>();

            if (asyncTexture == null || rawImage == null)
            {
                Debug.LogWarning($"[ComponentRecipes] PostProcessAsyncTexture 失败：GameObject {go.name} 缺少 AsyncTexture 或 RawImage 组件");
                return;
            }

            // 使用 SerializedObject 绑定 m_RawImage 字段
            var serializedObject = new SerializedObject(asyncTexture);
            serializedObject.Update();
            var rawImageProp = serializedObject.FindProperty("m_RawImage");
            if (rawImageProp != null)
            {
                rawImageProp.objectReferenceValue = rawImage;
                serializedObject.ApplyModifiedProperties();
            }
            else
            {
                Debug.LogWarning($"[ComponentRecipes] PostProcessAsyncTexture: AsyncTexture 上未找到 m_RawImage 字段");
            }
        }

        /// <summary>
        /// SingleScrollView 组件的后处理钩子：创建完整的滚动列表层级结构
        /// 包括 LR.SingleScrollView（根节点）、Viewport（遮罩）、Content 和 Scrollbar
        /// </summary>
        static void PostProcessSingleScrollView(GameObject go, JObject node)
        {
            // 1. 添加 LR.SingleScrollView 组件（继承自 ScrollRect）
            Type singleScrollViewType = FindType("LR.SingleScrollView");
            ScrollRect scrollRect;

            if (singleScrollViewType != null && typeof(ScrollRect).IsAssignableFrom(singleScrollViewType))
            {
                scrollRect = (ScrollRect)AddComponentWithRequirements(go, singleScrollViewType);
            }
            else
            {
                Debug.LogWarning($"[ComponentRecipes] 未找到 LR.SingleScrollView 类型，退化为普通 ScrollRect");
                scrollRect = go.AddComponent<ScrollRect>();
            }

            scrollRect.horizontal = false;
            scrollRect.vertical = true;
            scrollRect.scrollSensitivity = 1f;
            scrollRect.movementType = ScrollRect.MovementType.Elastic;

            // 2. 创建 Viewport（遮罩容器）
            GameObject viewport = new GameObject("Viewport", typeof(RectTransform));
            viewport.transform.SetParent(go.transform, false);
            var viewportRect = viewport.GetComponent<RectTransform>();
            viewportRect.anchorMin = Vector2.zero;
            viewportRect.anchorMax = Vector2.one;
            viewportRect.sizeDelta = Vector2.zero;
            viewportRect.pivot = new Vector2(0.5f, 0.5f);

            var viewportMask = viewport.AddComponent<RectMask2D>();
            scrollRect.viewport = viewportRect;

            // 3. 创建 Content（内容容器）
            GameObject content = new GameObject("Content", typeof(RectTransform));
            content.transform.SetParent(viewport.transform, false);
            var contentRect = content.GetComponent<RectTransform>();
            contentRect.anchorMin = new Vector2(0f, 1f);
            contentRect.anchorMax = new Vector2(1f, 1f);
            contentRect.sizeDelta = new Vector2(0f, 300f); // 默认高度
            contentRect.pivot = new Vector2(0.5f, 1f);

            scrollRect.content = contentRect;

            // 4. 创建 Scrollbar Vertical
            GameObject scrollbar = new GameObject("Scrollbar Vertical", typeof(RectTransform));
            scrollbar.transform.SetParent(go.transform, false);
            var scrollbarRect = scrollbar.GetComponent<RectTransform>();
            scrollbarRect.anchorMin = new Vector2(1f, 0f);
            scrollbarRect.anchorMax = new Vector2(1f, 1f);
            scrollbarRect.sizeDelta = new Vector2(12f, 0f);
            scrollbarRect.pivot = new Vector2(1f, 0.5f);

            var scrollbarImage = scrollbar.AddComponent<Image>();
            scrollbarImage.color = new Color(0f, 0f, 0f, 0.25f);
            var scrollbarComponent = scrollbar.AddComponent<Scrollbar>();
            scrollbarComponent.direction = Scrollbar.Direction.BottomToTop;

            // 5. 创建 Scrollbar/Sliding Area
            GameObject slidingArea = new GameObject("Sliding Area", typeof(RectTransform));
            slidingArea.transform.SetParent(scrollbar.transform, false);
            var slidingRect = slidingArea.GetComponent<RectTransform>();
            slidingRect.anchorMin = Vector2.zero;
            slidingRect.anchorMax = Vector2.one;
            slidingRect.sizeDelta = Vector2.zero;

            // 6. 创建 Scrollbar/Sliding Area/Handle
            GameObject handle = new GameObject("Handle", typeof(RectTransform));
            handle.transform.SetParent(slidingArea.transform, false);
            var handleRect = handle.GetComponent<RectTransform>();
            handleRect.sizeDelta = new Vector2(12f, 12f);
            var handleImage = handle.AddComponent<Image>();
            handleImage.color = new Color(1f, 1f, 1f, 0.5f);

            scrollbarComponent.handleRect = handleRect;
            scrollbarComponent.targetGraphic = handleImage;

            // 7. 绑定 Scrollbar 到 ScrollRect
            scrollRect.verticalScrollbar = scrollbarComponent;
            scrollRect.verticalScrollbarVisibility = ScrollRect.ScrollbarVisibility.AutoHideAndExpandViewport;
        }

        /// <summary>
        /// InputField 组件的后处理钩子：创建完整的输入框层级并绑定引用
        /// </summary>
        static void PostProcessInputField(GameObject go, JObject node)
        {
            // 1. 添加背景 Image
            var image = go.AddComponent<Image>();
            image.raycastTarget = true;
            var bgSprite = LoadAsset<Sprite>("Assets/UI/AtlasResources/CommonUI/input_bg.png");
            if (bgSprite != null)
            {
                image.sprite = bgSprite;
            }

            // 2. 添加 TMP_InputField
            var inputField = go.AddComponent<TMP_InputField>();

            // 3. 创建 Text Area（遮罩容器）
            GameObject textArea = new GameObject("Text Area", typeof(RectTransform));
            textArea.transform.SetParent(go.transform, false);
            var textAreaRect = textArea.GetComponent<RectTransform>();
            textAreaRect.anchorMin = Vector2.zero;
            textAreaRect.anchorMax = Vector2.one;
            textAreaRect.sizeDelta = new Vector2(-20f, -6f);
            textAreaRect.pivot = new Vector2(0.5f, 0.5f);

            var rectMask = textArea.AddComponent<RectMask2D>();

            // 4. 创建 Placeholder
            GameObject placeholder = new GameObject("Placeholder", typeof(RectTransform));
            placeholder.transform.SetParent(textArea.transform, false);
            var placeholderRect = placeholder.GetComponent<RectTransform>();
            placeholderRect.anchorMin = Vector2.zero;
            placeholderRect.anchorMax = Vector2.one;
            placeholderRect.sizeDelta = Vector2.zero;

            var placeholderTmp = placeholder.AddComponent<TextMeshProUGUI>();
            // 优先读 node["placeholder"]，否则回退到 node["text"]（TSX 的 data-text 用作占位符提示）
            string placeholderText = (string)node?["placeholder"];
            if (string.IsNullOrEmpty(placeholderText))
            {
                placeholderText = (string)node?["text"];
            }
            placeholderTmp.text = string.IsNullOrEmpty(placeholderText) ? "请输入..." : placeholderText;
            placeholderTmp.fontSize = 20f;
            placeholderTmp.color = new Color(0.67f, 0.67f, 0.67f, 1f); // #AAAAAA
            placeholderTmp.alignment = TextAlignmentOptions.Left;
            placeholderTmp.font = LoadAsset<TMP_FontAsset>("Assets/Resources/Font/ssfttSDF.asset");
            placeholderTmp.fontSharedMaterial = LoadAsset<Material>("Assets/Resources/Font/ssfttSDF_UI_NoOutLine.mat");

            // 5. 创建 Text
            GameObject text = new GameObject("Text", typeof(RectTransform));
            text.transform.SetParent(textArea.transform, false);
            var textRect = text.GetComponent<RectTransform>();
            textRect.anchorMin = Vector2.zero;
            textRect.anchorMax = Vector2.one;
            textRect.sizeDelta = Vector2.zero;

            var textTmp = text.AddComponent<TextMeshProUGUI>();
            textTmp.text = "";
            textTmp.fontSize = 20f;
            textTmp.color = Color.white;
            textTmp.alignment = TextAlignmentOptions.Left;
            textTmp.font = LoadAsset<TMP_FontAsset>("Assets/Resources/Font/ssfttSDF.asset");
            textTmp.fontSharedMaterial = LoadAsset<Material>("Assets/Resources/Font/ssfttSDF_UI_NoOutLine.mat");

            // 6. 绑定引用
            inputField.textViewport = textAreaRect;
            inputField.textComponent = textTmp;
            inputField.placeholder = placeholderTmp;
        }

        /// <summary>
        /// ItemSlot 组件的后处理钩子：创建物品图标插槽的完整层级
        /// </summary>
        static void PostProcessItemSlot(GameObject go, JObject node)
        {
            // 1. 添加背景 Image
            // 注意：slot.item-icon 从未有过真实扫描依据（低置信度启发式组件）。
            // 默认贴图仅用于占位可视化验证（复用其他配方已验证存在的通用素材），
            // 正式接入时应替换为业务专属美术图。
            var bgImage = go.AddComponent<Image>();
            bgImage.raycastTarget = true;
            var bgSprite = LoadAsset<Sprite>("Assets/UI/AtlasResources/CommonPanel/ty_tk_frame_07.png");
            if (bgSprite != null)
            {
                bgImage.sprite = bgSprite;
            }

            // 2. 创建 Icon（居中，80x80）
            GameObject icon = new GameObject("Icon", typeof(RectTransform));
            icon.transform.SetParent(go.transform, false);
            var iconRect = icon.GetComponent<RectTransform>();
            iconRect.anchorMin = new Vector2(0.5f, 0.5f);
            iconRect.anchorMax = new Vector2(0.5f, 0.5f);
            iconRect.sizeDelta = new Vector2(80f, 80f);
            iconRect.pivot = new Vector2(0.5f, 0.5f);

            var rawImage = icon.AddComponent<RawImage>();
            rawImage.raycastTarget = false;
            var iconTexture = LoadAsset<Texture2D>("Assets/UI/AtlasResources/CommonPanel/jh_frame_08.png");
            if (iconTexture != null)
            {
                rawImage.texture = iconTexture;
            }

            Type asyncTextureType = FindType("LR.AsyncTexture");
            if (asyncTextureType != null)
            {
                var asyncTexture = icon.AddComponent(asyncTextureType);

                // 绑定 m_RawImage
                var serializedObject = new SerializedObject(asyncTexture);
                serializedObject.Update();
                var rawImageProp = serializedObject.FindProperty("m_RawImage");
                if (rawImageProp != null)
                {
                    rawImageProp.objectReferenceValue = rawImage;
                    serializedObject.ApplyModifiedProperties();
                }
            }

            // 3. 创建 Count（右下角）
            GameObject count = new GameObject("Count", typeof(RectTransform));
            count.transform.SetParent(go.transform, false);
            var countRect = count.GetComponent<RectTransform>();
            countRect.anchorMin = new Vector2(1f, 0f);
            countRect.anchorMax = new Vector2(1f, 0f);
            countRect.sizeDelta = new Vector2(60f, 30f);
            countRect.pivot = new Vector2(1f, 0f);
            countRect.anchoredPosition = new Vector2(-5f, 5f);

            var countTmp = count.AddComponent<TextMeshProUGUI>();
            countTmp.text = "";
            countTmp.fontSize = 20f;
            countTmp.color = Color.white;
            countTmp.alignment = TextAlignmentOptions.BottomRight;
            countTmp.font = LoadAsset<TMP_FontAsset>("Assets/Resources/Font/fzhjtSDF.asset");
            countTmp.fontSharedMaterial = LoadAsset<Material>("Assets/Resources/Font/fzhjtSDF_UI_OutLine1Px.mat");

            // 4. 创建 QualityFrame（全覆盖）
            GameObject qualityFrame = new GameObject("QualityFrame", typeof(RectTransform));
            qualityFrame.transform.SetParent(go.transform, false);
            var frameRect = qualityFrame.GetComponent<RectTransform>();
            frameRect.anchorMin = Vector2.zero;
            frameRect.anchorMax = Vector2.one;
            frameRect.sizeDelta = Vector2.zero;

            // QualityFrame 复用同一张边框图占位；正式品质颜色/图案由业务运行时根据物品品质设置。
            var frameImage = qualityFrame.AddComponent<Image>();
            frameImage.raycastTarget = false;
            var frameSprite = LoadAsset<Sprite>("Assets/UI/AtlasResources/CommonPanel/ty_tk_frame_07.png");
            if (frameSprite != null)
            {
                frameImage.sprite = frameSprite;
            }
        }

        /// <summary>
        /// Modal 组件的后处理钩子：创建模态弹窗的完整层级
        /// </summary>
        static void PostProcessModal(GameObject go, JObject node)
        {
            // 1. 创建 Mask（全屏半透明遮罩）
            GameObject mask = new GameObject("Mask", typeof(RectTransform));
            mask.transform.SetParent(go.transform, false);
            var maskRect = mask.GetComponent<RectTransform>();
            maskRect.anchorMin = Vector2.zero;
            maskRect.anchorMax = Vector2.one;
            maskRect.sizeDelta = Vector2.zero;

            var maskImage = mask.AddComponent<Image>();
            maskImage.color = new Color(0f, 0f, 0f, 0.5f); // #00000080
            maskImage.raycastTarget = true;

            var maskButton = mask.AddComponent<Button>();

            // 2. 创建 Container（弹窗内容容器，居中）
            GameObject container = new GameObject("Container", typeof(RectTransform));
            container.transform.SetParent(go.transform, false);
            var containerRect = container.GetComponent<RectTransform>();
            containerRect.anchorMin = new Vector2(0.5f, 0.5f);
            containerRect.anchorMax = new Vector2(0.5f, 0.5f);
            containerRect.sizeDelta = new Vector2(600f, 400f);
            containerRect.pivot = new Vector2(0.5f, 0.5f);

            var containerImage = container.AddComponent<Image>();
            containerImage.color = Color.white;
            containerImage.raycastTarget = true;
            var containerSprite = LoadAsset<Sprite>("Assets/UI/AtlasResources/CommonPanel/bg2x2.png");
            if (containerSprite != null)
            {
                containerImage.sprite = containerSprite;
            }
        }

        /// <summary>
        /// RewardCell 组件的后处理钩子：创建奖励单元格的完整层级
        /// 注意：背景 Image 已由配方 components 数组挂载，这里不重复添加
        /// </summary>
        static void PostProcessRewardCell(GameObject go, JObject node)
        {
            // 2. 创建 Icon（居中上方，使用简化的 slot 样式）
            GameObject icon = new GameObject("Icon", typeof(RectTransform));
            icon.transform.SetParent(go.transform, false);
            var iconRect = icon.GetComponent<RectTransform>();
            iconRect.anchorMin = new Vector2(0.5f, 0.5f);
            iconRect.anchorMax = new Vector2(0.5f, 0.5f);
            iconRect.sizeDelta = new Vector2(80f, 80f);
            iconRect.pivot = new Vector2(0.5f, 0.5f);
            iconRect.anchoredPosition = new Vector2(0f, 15f);

            var rawImage = icon.AddComponent<RawImage>();
            rawImage.raycastTarget = false;
            var iconTexture = LoadAsset<Texture2D>("Assets/UI/AtlasResources/CommonPanel/jh_frame_08.png");
            if (iconTexture != null)
            {
                rawImage.texture = iconTexture;
            }

            Type asyncTextureType = FindType("LR.AsyncTexture");
            if (asyncTextureType != null)
            {
                var asyncTexture = icon.AddComponent(asyncTextureType);
                var serializedObject = new SerializedObject(asyncTexture);
                serializedObject.Update();
                var rawImageProp = serializedObject.FindProperty("m_RawImage");
                if (rawImageProp != null)
                {
                    rawImageProp.objectReferenceValue = rawImage;
                    serializedObject.ApplyModifiedProperties();
                }
            }

            // 3. 创建 Name（居中下方）
            GameObject name = new GameObject("Name", typeof(RectTransform));
            name.transform.SetParent(go.transform, false);
            var nameRect = name.GetComponent<RectTransform>();
            nameRect.anchorMin = new Vector2(0f, 0f);
            nameRect.anchorMax = new Vector2(1f, 0f);
            nameRect.sizeDelta = new Vector2(0f, 30f);
            nameRect.pivot = new Vector2(0.5f, 0f);
            nameRect.anchoredPosition = new Vector2(0f, 5f);

            var nameTmp = name.AddComponent<TextMeshProUGUI>();
            nameTmp.text = "";
            nameTmp.fontSize = 18f;
            nameTmp.color = Color.white;
            nameTmp.alignment = TextAlignmentOptions.Center;
            nameTmp.font = LoadAsset<TMP_FontAsset>("Assets/Resources/Font/fzhjtSDF.asset");
            nameTmp.fontSharedMaterial = LoadAsset<Material>("Assets/Resources/Font/fzhjtSDF_UI_NoOutLine.mat");
        }

        /// <summary>
        /// TabItem 组件的后处理钩子：创建标签页按钮的完整层级
        /// </summary>
        static void PostProcessTabItem(GameObject go, JObject node)
        {
            // 1. 添加 Button 和 Image
            // 注意：template.tab-item 从未有过真实扫描依据（低置信度启发式组件）。
            // 默认贴图仅用于占位可视化验证，正式接入时应替换为业务专属页签样式（选中/未选中态）。
            var button = go.AddComponent<Button>();

            var image = go.AddComponent<Image>();
            image.raycastTarget = true;
            var bgSprite = LoadAsset<Sprite>("Assets/UI/AtlasResources/CommonPanel/ty_btn_11.png");
            if (bgSprite != null)
            {
                image.sprite = bgSprite;
            }

            button.targetGraphic = image;

            // 2. 创建 Icon（左侧，可选）
            GameObject icon = new GameObject("Icon", typeof(RectTransform));
            icon.transform.SetParent(go.transform, false);
            var iconRect = icon.GetComponent<RectTransform>();
            iconRect.anchorMin = new Vector2(0f, 0.5f);
            iconRect.anchorMax = new Vector2(0f, 0.5f);
            iconRect.sizeDelta = new Vector2(32f, 32f);
            iconRect.pivot = new Vector2(0f, 0.5f);
            iconRect.anchoredPosition = new Vector2(10f, 0f);

            var iconImage = icon.AddComponent<Image>();
            iconImage.raycastTarget = false;
            var iconSprite = LoadAsset<Sprite>("Assets/UI/AtlasResources/FuncMenuListIcon/zjm_icon_07.png");
            if (iconSprite != null)
            {
                iconImage.sprite = iconSprite;
            }

            // 3. 创建 Label（居中或偏右）
            GameObject label = new GameObject("Label", typeof(RectTransform));
            label.transform.SetParent(go.transform, false);
            var labelRect = label.GetComponent<RectTransform>();
            labelRect.anchorMin = new Vector2(0f, 0f);
            labelRect.anchorMax = new Vector2(1f, 1f);
            labelRect.sizeDelta = Vector2.zero;

            var labelTmp = label.AddComponent<TextMeshProUGUI>();
            string text = (string)node?["text"];
            labelTmp.text = string.IsNullOrEmpty(text) ? "Tab" : text;
            labelTmp.fontSize = 24f;
            labelTmp.color = Color.white;
            labelTmp.alignment = TextAlignmentOptions.Center;
            labelTmp.font = LoadAsset<TMP_FontAsset>("Assets/Resources/Font/fzhjtSDF.asset");
            labelTmp.fontSharedMaterial = LoadAsset<Material>("Assets/Resources/Font/fzhjtSDF_UI_NoOutLine.mat");
        }

        /// <summary>
        /// GridScrollView 组件的后处理钩子：创建多列网格滚动列表层级结构
        /// 包括 LR.ScrollView（根节点）、Viewport（遮罩）、Content（GridLayoutGroup）和 Scrollbar
        /// </summary>
        static void PostProcessGridScrollView(GameObject go, JObject node)
        {
            // 1. 添加 LR.ScrollView 组件（继承自 ScrollRect）
            Type scrollViewType = FindType("LR.ScrollView");
            ScrollRect scrollRect;

            if (scrollViewType != null && typeof(ScrollRect).IsAssignableFrom(scrollViewType))
            {
                scrollRect = (ScrollRect)AddComponentWithRequirements(go, scrollViewType);
            }
            else
            {
                Debug.LogWarning($"[ComponentRecipes] 未找到 LR.ScrollView 类型，退化为普通 ScrollRect");
                scrollRect = go.AddComponent<ScrollRect>();
            }

            scrollRect.horizontal = false;
            scrollRect.vertical = true;
            scrollRect.scrollSensitivity = 1f;
            scrollRect.movementType = ScrollRect.MovementType.Elastic;

            // 2. 创建 Viewport（遮罩容器）
            GameObject viewport = new GameObject("Viewport", typeof(RectTransform));
            viewport.transform.SetParent(go.transform, false);
            var viewportRect = viewport.GetComponent<RectTransform>();
            viewportRect.anchorMin = Vector2.zero;
            viewportRect.anchorMax = Vector2.one;
            viewportRect.sizeDelta = Vector2.zero;
            viewportRect.pivot = new Vector2(0.5f, 0.5f);

            var viewportMask = viewport.AddComponent<RectMask2D>();
            scrollRect.viewport = viewportRect;

            // 3. 创建 Content（内容容器）
            // 不加 GridLayoutGroup：LR.ScrollView 自己算行列（OnRefreshSize 用
            // m_CellWidth/m_CellHeight 求 m_ColCount，OnGetPos 直接写 anchoredPosition），
            // 挂 LayoutGroup 会和它抢位置。项目里 400 个用 LR.ScrollView 的 Prefab
            // 没有一个在 Content 上挂 GridLayoutGroup。
            GameObject content = new GameObject("Content", typeof(RectTransform));
            content.transform.SetParent(viewport.transform, false);
            var contentRect = content.GetComponent<RectTransform>();
            contentRect.anchorMin = new Vector2(0f, 1f);
            contentRect.anchorMax = new Vector2(1f, 1f);
            contentRect.sizeDelta = new Vector2(0f, 600f); // 默认高度
            contentRect.pivot = new Vector2(0.5f, 1f);

            scrollRect.content = contentRect;

            // 4. 创建 Scrollbar Vertical
            GameObject scrollbar = new GameObject("Scrollbar Vertical", typeof(RectTransform));
            scrollbar.transform.SetParent(go.transform, false);
            var scrollbarRect = scrollbar.GetComponent<RectTransform>();
            scrollbarRect.anchorMin = new Vector2(1f, 0f);
            scrollbarRect.anchorMax = new Vector2(1f, 1f);
            scrollbarRect.sizeDelta = new Vector2(12f, 0f);
            scrollbarRect.pivot = new Vector2(1f, 0.5f);

            var scrollbarImage = scrollbar.AddComponent<Image>();
            scrollbarImage.color = new Color(0f, 0f, 0f, 0.25f);
            var scrollbarComponent = scrollbar.AddComponent<Scrollbar>();
            scrollbarComponent.direction = Scrollbar.Direction.BottomToTop;

            // 5. 创建 Scrollbar/Sliding Area
            GameObject slidingArea = new GameObject("Sliding Area", typeof(RectTransform));
            slidingArea.transform.SetParent(scrollbar.transform, false);
            var slidingRect = slidingArea.GetComponent<RectTransform>();
            slidingRect.anchorMin = Vector2.zero;
            slidingRect.anchorMax = Vector2.one;
            slidingRect.sizeDelta = Vector2.zero;

            // 6. 创建 Scrollbar/Sliding Area/Handle
            GameObject handle = new GameObject("Handle", typeof(RectTransform));
            handle.transform.SetParent(slidingArea.transform, false);
            var handleRect = handle.GetComponent<RectTransform>();
            handleRect.sizeDelta = new Vector2(12f, 12f);
            var handleImage = handle.AddComponent<Image>();
            handleImage.color = new Color(1f, 1f, 1f, 0.5f);

            scrollbarComponent.handleRect = handleRect;
            scrollbarComponent.targetGraphic = handleImage;

            // 7. 绑定 Scrollbar 到 ScrollRect
            scrollRect.verticalScrollbar = scrollbarComponent;
            scrollRect.verticalScrollbarVisibility = ScrollRect.ScrollbarVisibility.AutoHideAndExpandViewport;
        }
    }
}
