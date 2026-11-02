using System;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace LRUIPrefabGen
{
    /// <summary>
    /// Unity 命令行入口，用于 -executeMethod 调用。
    /// 从环境变量读取参数，避免 -executeMethod 只能调用无参方法的限制。
    ///
    /// 使用方式：
    ///   set LR_LAYOUT_JSON=<OpenSpec根目录的布局JSON绝对路径>
    ///   set LR_PREFAB_PATH=Assets/Resources/PanelUI/XxxPanel.prefab
    ///   set LR_SCRIPT_TYPE=LR.XxxPage
    ///   Unity.exe -quit -batchmode -projectPath <project> -logFile - \
    ///     -executeMethod LRUIPrefabGen.LRUnityLayoutCLI.GenerateFromEnv
    /// </summary>
    public static class LRUnityLayoutCLI
    {
        /// <summary>
        /// Unity 命令行入口。从环境变量读取参数：
        /// - LR_LAYOUT_JSON: 布局 JSON 路径（绝对路径或相对于项目根目录）
        /// - LR_PREFAB_PATH: Prefab 输出路径（Assets/... 格式）
        /// - LR_SCRIPT_TYPE: 根脚本类型名（可选，如 "LR.GrowthFundPage"）
        /// </summary>
        public static void GenerateFromEnv()
        {
            string jsonPath = Environment.GetEnvironmentVariable("LR_LAYOUT_JSON");
            string prefabPath = Environment.GetEnvironmentVariable("LR_PREFAB_PATH");
            string scriptType = Environment.GetEnvironmentVariable("LR_SCRIPT_TYPE");

            Debug.Log($"[LRUnityLayoutCLI] ========== 开始生成 Prefab ==========");
            Debug.Log($"[LRUnityLayoutCLI] 环境变量读取:");
            Debug.Log($"[LRUnityLayoutCLI]   LR_LAYOUT_JSON = {jsonPath ?? "(未设置)"}");
            Debug.Log($"[LRUnityLayoutCLI]   LR_PREFAB_PATH = {prefabPath ?? "(未设置)"}");
            Debug.Log($"[LRUnityLayoutCLI]   LR_SCRIPT_TYPE = {scriptType ?? "(未设置)"}");

            if (string.IsNullOrEmpty(jsonPath))
            {
                Debug.LogError("[LRUnityLayoutCLI] ❌ 缺少环境变量 LR_LAYOUT_JSON");
                EditorApplication.Exit(1);
                return;
            }

            if (string.IsNullOrEmpty(prefabPath))
            {
                Debug.LogError("[LRUnityLayoutCLI] ❌ 缺少环境变量 LR_PREFAB_PATH");
                EditorApplication.Exit(1);
                return;
            }

            // 如果是相对路径，转换为绝对路径（相对于项目根目录）
            if (!Path.IsPathRooted(jsonPath))
            {
                jsonPath = Path.Combine(Application.dataPath, "..", jsonPath);
                jsonPath = Path.GetFullPath(jsonPath);
            }

            if (!File.Exists(jsonPath))
            {
                Debug.LogError($"[LRUnityLayoutCLI] ❌ JSON 文件不存在: {jsonPath}");
                EditorApplication.Exit(1);
                return;
            }

            try
            {
                Debug.Log($"[LRUnityLayoutCLI] 调用生成器...");
                Debug.Log($"[LRUnityLayoutCLI]   JSON: {jsonPath}");
                Debug.Log($"[LRUnityLayoutCLI]   Prefab: {prefabPath}");
                Debug.Log($"[LRUnityLayoutCLI]   脚本类型: {scriptType ?? "(无)"}");

                string result = LRUnityLayoutPrefabGenerator.GenerateFromLayout(
                    jsonPath,
                    prefabPath,
                    scriptType
                );

                Debug.Log($"[LRUnityLayoutCLI] ✅ 生成成功");
                Debug.Log($"[LRUnityLayoutCLI]   输出: {result}");
                Debug.Log($"[LRUnityLayoutCLI] ========================================");

                EditorApplication.Exit(0);
            }
            catch (Exception e)
            {
                Debug.LogError($"[LRUnityLayoutCLI] ❌ 生成失败: {e.GetType().Name}");
                Debug.LogError($"[LRUnityLayoutCLI] 错误消息: {e.Message}");
                Debug.LogError($"[LRUnityLayoutCLI] 堆栈跟踪:\n{e.StackTrace}");
                Debug.LogError($"[LRUnityLayoutCLI] ========================================");

                EditorApplication.Exit(1);
            }
        }

        /// <summary>
        /// 批量生成入口（可选）。从环境变量 LR_BATCH_JSON_DIR 读取目录，
        /// 生成该目录下所有 *.json 文件对应的 Prefab。
        /// 约定：JSON 文件名 = Page 类名 = Prefab 名。
        /// </summary>
        public static void GenerateBatchFromEnv()
        {
            string jsonDir = Environment.GetEnvironmentVariable("LR_BATCH_JSON_DIR");
            string prefabDir = Environment.GetEnvironmentVariable("LR_BATCH_PREFAB_DIR")
                ?? "Assets/Resources/PanelUI";
            string scriptNamespace = Environment.GetEnvironmentVariable("LR_SCRIPT_NAMESPACE")
                ?? "LR";

            if (string.IsNullOrEmpty(jsonDir))
            {
                Debug.LogError("[LRUnityLayoutCLI] ❌ 批量模式缺少环境变量 LR_BATCH_JSON_DIR");
                EditorApplication.Exit(1);
                return;
            }

            if (!Directory.Exists(jsonDir))
            {
                Debug.LogError($"[LRUnityLayoutCLI] ❌ 目录不存在: {jsonDir}");
                EditorApplication.Exit(1);
                return;
            }

            string[] jsonFiles = Directory.GetFiles(jsonDir, "*.json");
            Debug.Log($"[LRUnityLayoutCLI] 批量模式：找到 {jsonFiles.Length} 个 JSON 文件");

            int successCount = 0;
            int failCount = 0;

            foreach (string jsonPath in jsonFiles)
            {
                string fileName = Path.GetFileNameWithoutExtension(jsonPath);
                string prefabPath = $"{prefabDir}/{fileName}.prefab";
                string scriptType = $"{scriptNamespace}.{fileName}";

                Debug.Log($"[LRUnityLayoutCLI] 处理: {fileName}");

                try
                {
                    LRUnityLayoutPrefabGenerator.GenerateFromLayout(
                        jsonPath,
                        prefabPath,
                        scriptType
                    );
                    successCount++;
                    Debug.Log($"[LRUnityLayoutCLI]   ✅ 成功");
                }
                catch (Exception e)
                {
                    failCount++;
                    Debug.LogError($"[LRUnityLayoutCLI]   ❌ 失败: {e.Message}");
                }
            }

            Debug.Log($"[LRUnityLayoutCLI] 批量生成完成: {successCount} 成功, {failCount} 失败");
            EditorApplication.Exit(failCount > 0 ? 1 : 0);
        }
    }
}
