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
        const string DefaultTextMaterial = "Assets/Resources/Font/fzhjtSDF_UI_Default.mat";
        const float DefaultFontSize = 32f;  // 调研报告：实际项目中默认32号字体，不是24

        public static void Apply(GameObject go, string componentId, JObject node)
        {
            // 处理样式变体（如 text.localized 的 title/body 样式）
            string semanticId = componentId;
            if (node != null && node["data-lr-style"] != null)
            {
                string style = (string)node["data-lr-style"];
                if (!string.IsNullOrEmpty(style))
                {
                    // 尝试加载 componentId-style 配方（如 text.localized-title）
                    var variantRecipe = ComponentRecipeLoader.Get($"{componentId}-{style}");
                    if (variantRecipe != null)
                    {
                        semanticId = $"{componentId}-{style}";
                    }
                }
            }

            // 优先从 JSON 配方加载（新架构）
            var recipe = ComponentRecipeLoader.Get(semanticId);
            if (recipe != null)
            {
                ApplyFromRecipe(go, recipe, node);
                return;
            }

            // Fallback 到硬编码 switch（旧架构，逐步迁移）
            switch (componentId)
            {
                case "surface.panel":
                case "surface.page":
                    // RectTransform only; children carry the actual visuals.
                    break;

                case "surface.modal":
                    go.AddComponent<CanvasGroup>();
                    break;

                case "control.button":
                    ApplyButton(go, node);
                    break;

                case "control.toggle":
                    go.AddComponent<Toggle>();
                    AddRaycastArea(go);
                    break;

                case "control.input":
                    ApplyInput(go, node);
                    break;

                case "control.progress":
                    AddLRComponent(go, "LR.LRProgressBar");
                    break;

                case "list.scroll":
                    ApplyScrollView(go, node, "LR.ScrollView");
                    break;

                case "list.single-scroll":
                    ApplyScrollView(go, node, "LR.SingleScrollView");
                    break;

                case "content.async-image":
                    ApplyImage(go, node, raycastTarget: false);
                    AddLRComponent(go, "LR.AsyncTexture");
                    break;

                case "content.async-icon":
                    ApplyImage(go, node, raycastTarget: false);
                    AddLRComponent(go, "LR.AsyncTexture");
                    break;

                case "text.localized":
                    ApplyLocalizedText(go, node);
                    break;

                case "slot.item-icon":
                    // Standard item-icon hierarchy is business-bound later;
                    // generator only creates the RectTransform placeholder.
                    break;

                case "feedback.red-point":
                    AddLRComponent(go, "LR.UIRedPointWatcher");
                    break;

                case "template.tab-item":
                case "template.reward-cell":
                    // Pure layout template; no component beyond RectTransform.
                    break;

                default:
                    Debug.LogWarning($"[LRComponentRecipes] 未识别的语义组件 ID: {componentId}（GameObject={go.name}），只创建了 RectTransform");
                    break;
            }

            ApplyLayoutGroup(go, node);
        }

        static void ApplyButton(GameObject go, JObject node)
        {
            var image = go.AddComponent<Image>();
            // 调研报告: Button 的 Image 关闭 raycastTarget，点击响应由 RaycastArea 子节点负责
            image.raycastTarget = false;
            // unity-ui-components.md control.button 默认样式: image.type = Sliced（九宫格，支持拉伸）。
            image.type = Image.Type.Sliced;

            // 按钮默认图（调研报告：按钮通常设置默认 sprite）
            string nodeName = (string)node["name"];
            string defaultSpritePath = GetDefaultSpriteForButton(nodeName);
            if (!string.IsNullOrEmpty(defaultSpritePath))
            {
                image.sprite = LoadAsset<Sprite>(defaultSpritePath);
            }

            var button = go.AddComponent<Button>();
            button.targetGraphic = image;

            // Only auto-generate the label from data-text when the author
            // did not supply explicit JSX children. When a label needs its
            // own [SerializeField] binding (e.g. m_BuyButtonText), it must
            // be authored as an explicit text.localized child instead --
            // an auto-generated child has no JSON node, so CollectBindings
            // (which matches by data-name in the JSON tree) could never
            // find it.
            bool hasExplicitChildren = node["children"] is JArray childrenArr && childrenArr.Count > 0;
            string text = (string)node["text"];
            if (!hasExplicitChildren && !string.IsNullOrEmpty(text))
            {
                GameObject textGo = new GameObject("Text", typeof(RectTransform));
                textGo.transform.SetParent(go.transform, false);
                var rect = textGo.GetComponent<RectTransform>();
                rect.anchorMin = Vector2.zero;
                rect.anchorMax = Vector2.one;
                rect.sizeDelta = Vector2.zero;
                rect.anchoredPosition = Vector2.zero;

                var tmp = textGo.AddComponent<TextMeshProUGUI>();
                tmp.text = text;
                tmp.fontSize = DefaultFontSize;
                tmp.alignment = TextAlignmentOptions.Center;
                tmp.fontSharedMaterial = LoadAsset<Material>("Assets/Resources/Font/fzhjtSDF_UI_OutLine1Px.mat");
                tmp.color = Color.white;
            }

            // 调研报告规则: Button 必须添加 RaycastArea 子节点负责点击响应
            GameObject raycastAreaGo = new GameObject("RaycastArea", typeof(RectTransform));
            raycastAreaGo.transform.SetParent(go.transform, false);
            var raycastRect = raycastAreaGo.GetComponent<RectTransform>();
            raycastRect.anchorMin = Vector2.zero;
            raycastRect.anchorMax = Vector2.one;
            raycastRect.sizeDelta = Vector2.zero;
            raycastRect.anchoredPosition = Vector2.zero;
            AddLRComponent(raycastAreaGo, "LR.RaycastArea");
        }

        static void ApplyInput(GameObject go, JObject node)
        {
            var image = go.AddComponent<Image>();
            var inputField = go.AddComponent<TMP_InputField>();

            GameObject textArea = new GameObject("TextArea", typeof(RectTransform));
            textArea.transform.SetParent(go.transform, false);
            var textAreaRect = textArea.GetComponent<RectTransform>();
            textAreaRect.anchorMin = Vector2.zero;
            textAreaRect.anchorMax = Vector2.one;
            textAreaRect.sizeDelta = Vector2.zero;

            GameObject textGo = new GameObject("Text", typeof(RectTransform));
            textGo.transform.SetParent(textArea.transform, false);
            var tmp = textGo.AddComponent<TextMeshProUGUI>();
            tmp.fontSize = 20f;
            tmp.color = Color.white;
            tmp.font = LoadAsset<TMP_FontAsset>("Assets/Resources/Font/ssfttSDF.asset");
            tmp.fontSharedMaterial = LoadAsset<Material>("Assets/Resources/Font/ssfttSDF_UI_NoOutLine.mat");

            inputField.textViewport = textAreaRect;
            inputField.textComponent = tmp;

            string placeholder = (string)node["placeholder"];
            GameObject placeholderGo = new GameObject("Placeholder", typeof(RectTransform));
            placeholderGo.transform.SetParent(textArea.transform, false);
            var placeholderTmp = placeholderGo.AddComponent<TextMeshProUGUI>();
            placeholderTmp.text = string.IsNullOrEmpty(placeholder) ? "请输入..." : placeholder;
            placeholderTmp.fontSize = 20f;
            placeholderTmp.color = new Color(0.5f, 0.5f, 0.5f, 1f);
            placeholderTmp.font = tmp.font;
            placeholderTmp.fontSharedMaterial = tmp.fontSharedMaterial;
            inputField.placeholder = placeholderTmp;
        }

        static void ApplyScrollView(GameObject go, JObject node, string lrScrollTypeName)
        {
            // LR.ScrollView / LR.SingleScrollView derive from ScrollRect
            // (ScrollView : ScrollRect), they don't sit alongside a plain
            // ScrollRect as a sibling component -- Unity only allows one
            // ScrollRect-derived component per GameObject. Add the LR type
            // directly and treat the returned Component as the ScrollRect.
            Type lrType = FindType(lrScrollTypeName);
            ScrollRect scrollRect;
            if (lrType != null && typeof(ScrollRect).IsAssignableFrom(lrType))
            {
                scrollRect = (ScrollRect)go.AddComponent(lrType);
            }
            else
            {
                Debug.LogWarning($"[LRComponentRecipes] 未找到类型或不是 ScrollRect 派生类: {lrScrollTypeName}（GameObject={go.name}），退化为普通 ScrollRect");
                scrollRect = go.AddComponent<ScrollRect>();
            }

            GameObject viewport = new GameObject("Viewport", typeof(RectTransform));
            viewport.transform.SetParent(go.transform, false);
            var viewportRect = viewport.GetComponent<RectTransform>();
            viewportRect.anchorMin = Vector2.zero;
            viewportRect.anchorMax = Vector2.one;
            viewportRect.sizeDelta = Vector2.zero;
            viewport.AddComponent<RectMask2D>();

            GameObject content = new GameObject("Content", typeof(RectTransform));
            content.transform.SetParent(viewport.transform, false);
            var contentRect = content.GetComponent<RectTransform>();
            contentRect.anchorMin = new Vector2(0f, 1f);
            contentRect.anchorMax = new Vector2(1f, 1f);
            contentRect.pivot = new Vector2(0.5f, 1f);

            scrollRect.viewport = viewportRect;
            scrollRect.content = contentRect;
            scrollRect.horizontal = false;
            scrollRect.vertical = true;
            scrollRect.movementType = ScrollRect.MovementType.Elastic;
            // unity-ui-components.md list.scroll/list.single-scroll 默认样式: scrollSensitivity=1.0, scrollbar=AutoHide。
            scrollRect.scrollSensitivity = 1.0f;

            Scrollbar verticalScrollbar = BuildVerticalScrollbar(go.transform);
            scrollRect.verticalScrollbar = verticalScrollbar;
            scrollRect.verticalScrollbarVisibility = ScrollRect.ScrollbarVisibility.AutoHideAndExpandViewport;
        }

        static Scrollbar BuildVerticalScrollbar(Transform parent)
        {
            GameObject scrollbarGo = new GameObject("Scrollbar Vertical", typeof(RectTransform));
            scrollbarGo.transform.SetParent(parent, false);
            var scrollbarRect = scrollbarGo.GetComponent<RectTransform>();
            scrollbarRect.anchorMin = new Vector2(1f, 0f);
            scrollbarRect.anchorMax = new Vector2(1f, 1f);
            scrollbarRect.pivot = new Vector2(1f, 1f);
            scrollbarRect.sizeDelta = new Vector2(12f, 0f);

            var scrollbarImage = scrollbarGo.AddComponent<Image>();
            scrollbarImage.color = new Color(0f, 0f, 0f, 0.25f);
            var scrollbar = scrollbarGo.AddComponent<Scrollbar>();
            scrollbar.direction = Scrollbar.Direction.BottomToTop;

            GameObject slidingArea = new GameObject("Sliding Area", typeof(RectTransform));
            slidingArea.transform.SetParent(scrollbarGo.transform, false);
            var slidingRect = slidingArea.GetComponent<RectTransform>();
            slidingRect.anchorMin = Vector2.zero;
            slidingRect.anchorMax = Vector2.one;
            slidingRect.sizeDelta = Vector2.zero;

            GameObject handle = new GameObject("Handle", typeof(RectTransform));
            handle.transform.SetParent(slidingArea.transform, false);
            var handleRect = handle.GetComponent<RectTransform>();
            handleRect.sizeDelta = new Vector2(12f, 12f);
            var handleImage = handle.AddComponent<Image>();
            handleImage.color = new Color(1f, 1f, 1f, 0.6f);

            scrollbar.handleRect = handleRect;
            scrollbar.targetGraphic = handleImage;
            return scrollbar;
        }

        static void ApplyImage(GameObject go, JObject node, bool raycastTarget)
        {
            var image = go.AddComponent<Image>();
            // 调研报告: Image 默认关闭 raycastTarget（除非明确需要响应点击）
            image.raycastTarget = raycastTarget;
            image.preserveAspect = true;

            var colorArr = node["color"] as JArray;
            if (colorArr != null && colorArr.Count >= 4)
            {
                image.color = new Color((float)colorArr[0], (float)colorArr[1], (float)colorArr[2], (float)colorArr[3]);
            }

            // 根据节点名称判断职能，设置默认 sprite（调研报告：大部分 Image 在 prefab 中都设置了默认图）
            string nodeName = (string)node["name"];
            string defaultSpritePath = GetDefaultSpriteForImage(nodeName);
            if (!string.IsNullOrEmpty(defaultSpritePath))
            {
                image.sprite = LoadAsset<Sprite>(defaultSpritePath);
            }
        }

        static void ApplyLocalizedText(GameObject go, JObject node)
        {
            var tmp = go.AddComponent<TextMeshProUGUI>();

            // Localizer 的挂载（对无 data-field 的静态文本节点）由生成流程的后处理阶段
            // 统一负责：LRUnityLayoutPrefabGenerator.PostProcessSavedPrefabAsset 在 Prefab
            // 保存为磁盘资产后，通过 AssetDatabase.LoadAssetAtPath 重新加载再挂载，
            // 这样才能确保序列化生效，这里不重复处理。

            string style = (string)node["textStyle"];
            ApplyTextStylePreset(tmp, style);

            string text = (string)node["text"];
            if (!string.IsNullOrEmpty(text))
            {
                tmp.text = text;
            }

            var colorArr = node["color"] as JArray;
            if (colorArr != null && colorArr.Count >= 4)
            {
                tmp.color = new Color((float)colorArr[0], (float)colorArr[1], (float)colorArr[2], (float)colorArr[3]);
            }

            ApplyTextAlignment(tmp, node);
        }

        static void ApplyTextStylePreset(TextMeshProUGUI tmp, string style)
        {
            // 统一使用 fzhjtSDF_UI_Default.mat，不再区分 title/body 的材质
            tmp.font = LoadAsset<TMP_FontAsset>(DefaultFont);
            tmp.fontSharedMaterial = LoadAsset<Material>(DefaultTextMaterial);

            switch (style)
            {
                case "title":
                    tmp.fontSize = 32f;
                    tmp.color = new Color(1f, 0.843f, 0f, 1f);
                    tmp.alignment = TextAlignmentOptions.Center;
                    break;

                case "body":
                    tmp.fontSize = 20f;
                    tmp.color = new Color(0.878f, 0.878f, 0.878f, 1f);
                    tmp.alignment = TextAlignmentOptions.Left;
                    break;

                default:
                    tmp.fontSize = DefaultFontSize;
                    tmp.color = Color.white;
                    tmp.alignment = TextAlignmentOptions.Left;
                    break;
            }
        }

        static void ApplyTextAlignment(TextMeshProUGUI tmp, JObject node)
        {
            string textAlign = (string)node["textAlign"];
            string verticalAlign = (string)node["verticalAlign"];
            if (string.IsNullOrEmpty(textAlign) && string.IsNullOrEmpty(verticalAlign))
            {
                return;
            }

            HorizontalAlignmentOptions h = ParseHorizontal(textAlign, tmp.alignment);
            VerticalAlignmentOptions v = ParseVertical(verticalAlign, tmp.alignment);
            tmp.alignment = (TextAlignmentOptions)((int)h | (int)v);
        }

        static HorizontalAlignmentOptions ParseHorizontal(string value, TextAlignmentOptions fallback)
        {
            switch (value)
            {
                case "Left": return HorizontalAlignmentOptions.Left;
                case "Center": return HorizontalAlignmentOptions.Center;
                case "Right": return HorizontalAlignmentOptions.Right;
                case "Justified": return HorizontalAlignmentOptions.Justified;
                default: return (HorizontalAlignmentOptions)((int)fallback & 0xF);
            }
        }

        static VerticalAlignmentOptions ParseVertical(string value, TextAlignmentOptions fallback)
        {
            switch (value)
            {
                case "Top": return VerticalAlignmentOptions.Top;
                case "Middle": return VerticalAlignmentOptions.Middle;
                case "Bottom": return VerticalAlignmentOptions.Bottom;
                default: return (VerticalAlignmentOptions)((int)fallback & 0xF0);
            }
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

        static void AddRaycastArea(GameObject go)
        {
            AddLRComponent(go, "LR.RaycastArea");
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
                go.AddComponent(type);
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
        /// 根据 Image 节点名称判断职能，返回对应的默认 sprite 路径。
        /// 调研报告：背景、按钮、图标等不同职能的 Image 使用不同的默认图。
        /// </summary>
        static string GetDefaultSpriteForImage(string nodeName)
        {
            if (string.IsNullOrEmpty(nodeName))
                return null;

            string lowerName = nodeName.ToLower();

            // 背景类：Bg, Background, FundBackground 等
            if (lowerName.Contains("bg") || lowerName.Contains("background"))
            {
                return "Assets/UI/AtlasResources/CommonUI/bg2x2.png";
            }

            // 图标类：Icon
            if (lowerName.Contains("icon"))
            {
                return "Assets/UI/AtlasResources/FuncMenuListIcon/zjm_icon_07.png";
            }

            // 装饰/分割线类：Line, Divider
            if (lowerName.Contains("line") || lowerName.Contains("divider"))
            {
                return "Assets/UI/AtlasResources/CommonUI/farme_08.png";
            }

            // 其他默认返回 null（由代码运行时设置）
            return null;
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
        static void ApplyFromRecipe(GameObject go, ComponentRecipe recipe, JObject node)
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
                    mainComponent = go.AddComponent(componentType);
                }
            }

            // 1.5. 挂载根节点额外组件（如 AsyncTexture）
            if (recipe.components != null)
            {
                foreach (var compSpec in recipe.components)
                {
                    Type compType = FindType(compSpec.type);
                    if (compType == null)
                    {
                        Debug.LogWarning($"[ComponentRecipes] 根节点组件类型未找到: {compSpec.type}");
                        continue;
                    }

                    Component comp = go.AddComponent(compType);

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

                            Component comp = childGo.AddComponent(compType);

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
                    default:
                        Debug.LogWarning($"[ComponentRecipes] 未知的后处理钩子: {recipe.postProcess}");
                        break;
                }
            }
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
    }
}
