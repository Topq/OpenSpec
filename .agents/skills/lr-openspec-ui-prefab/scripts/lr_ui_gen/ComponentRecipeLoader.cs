using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using UnityEngine;

namespace LRUIPrefabGen
{
    /// <summary>
    /// 组件配方数据结构（对应 JSON 文件格式）
    /// </summary>
    [Serializable]
    public class ComponentRecipe
    {
        public string semanticId;
        public string componentType;
        public string description;
        public string scanSource;
        public List<ComponentSpec> components;  // 根节点额外挂载的组件（如 AsyncTexture）
        public List<HierarchyNode> hierarchy;
        public Dictionary<string, object> defaultValues;
        public List<string> notes;
        public string postProcess;  // 后处理钩子名称（如 "button"）
    }

    [Serializable]
    public class HierarchyNode
    {
        public string nodeName;
        public bool isRequired = true;
        public string position;  // "last-child" 等特殊位置标记
        public List<ComponentSpec> components;
        public string bindToField;  // 支持 "m_TargetImages[0]" 数组索引语法
        public LayoutDefaults layoutDefaults;
    }

    [Serializable]
    public class ComponentSpec
    {
        public string type;  // 组件类型全名，如 "UnityEngine.UI.Image"
        public Dictionary<string, object> properties;  // 组件属性默认值
    }

    [Serializable]
    public class LayoutDefaults
    {
        public float[] anchorMin;
        public float[] anchorMax;
        public float[] anchoredPosition;
        public float[] sizeDelta;
        public float[] pivot;
    }

    /// <summary>
    /// 从 Assets/Editor/LRUIPrefabGen/ComponentRecipes/*.json 加载所有配方
    /// </summary>
    public static class ComponentRecipeLoader
    {
        static Dictionary<string, ComponentRecipe> _cache;

        /// <summary>
        /// 加载所有 JSON 配方文件，返回 semanticId → ComponentRecipe 映射
        /// </summary>
        public static Dictionary<string, ComponentRecipe> LoadAll()
        {
            if (_cache != null)
                return _cache;

            _cache = new Dictionary<string, ComponentRecipe>();
            string recipeDir = "Assets/Editor/LRUIPrefabGen/ComponentRecipes";

            if (!Directory.Exists(recipeDir))
            {
                Debug.LogWarning($"[ComponentRecipeLoader] 配方目录不存在: {recipeDir}");
                return _cache;
            }

            string[] jsonFiles = Directory.GetFiles(recipeDir, "*.json", SearchOption.TopDirectoryOnly);

            foreach (string filePath in jsonFiles)
            {
                try
                {
                    string json = File.ReadAllText(filePath);
                    var recipe = JsonConvert.DeserializeObject<ComponentRecipe>(json);

                    if (recipe == null || string.IsNullOrEmpty(recipe.semanticId))
                    {
                        Debug.LogWarning($"[ComponentRecipeLoader] 无效配方: {filePath}");
                        continue;
                    }

                    if (_cache.ContainsKey(recipe.semanticId))
                    {
                        Debug.LogWarning($"[ComponentRecipeLoader] 重复的 semanticId: {recipe.semanticId} (文件: {filePath})");
                        continue;
                    }

                    _cache[recipe.semanticId] = recipe;
                    Debug.Log($"[ComponentRecipeLoader] 加载配方: {recipe.semanticId} <- {Path.GetFileName(filePath)}");
                }
                catch (Exception ex)
                {
                    Debug.LogError($"[ComponentRecipeLoader] 加载失败: {filePath}\n{ex.Message}");
                }
            }

            Debug.Log($"[ComponentRecipeLoader] 共加载 {_cache.Count} 个配方");
            return _cache;
        }

        /// <summary>
        /// 获取指定语义 ID 的配方
        /// </summary>
        public static ComponentRecipe Get(string semanticId)
        {
            var recipes = LoadAll();
            recipes.TryGetValue(semanticId, out var recipe);
            return recipe;
        }

        /// <summary>
        /// 清空缓存（测试用）
        /// </summary>
        public static void ClearCache()
        {
            _cache = null;
        }
    }
}
