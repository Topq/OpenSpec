using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace LRUIPrefabGen
{
    /// <summary>
    /// Loads project assets for prefab generation. If the exact path is gone,
    /// it searches Assets for assets with the same file name and accepts the
    /// repair only when the candidate is unique (after path-similarity
    /// ranking). Ambiguous repairs fail loudly instead of guessing.
    /// Every accepted repair is written to generation-report.json through
    /// LRAutoFixLog.
    /// </summary>
    public static class LRAssetResolver
    {
        public static T Load<T>(string path, string owner) where T : UnityEngine.Object
        {
            if (string.IsNullOrEmpty(path))
            {
                throw new Exception($"[LRAssetResolver] 资源路径为空（owner={owner}）");
            }

            string requestedPath = path.Replace("\\", "/");
            T asset = AssetDatabase.LoadAssetAtPath<T>(requestedPath);
            if (asset != null)
            {
                return asset;
            }

            string resolvedPath;
            string reason;
            if (!TryResolvePath<T>(requestedPath, out resolvedPath, out reason))
            {
                throw new Exception(
                    $"[LRAssetResolver] 未找到资源: {path}（owner={owner}；自动修复失败：{reason}）");
            }

            asset = AssetDatabase.LoadAssetAtPath<T>(resolvedPath);
            if (asset == null)
            {
                throw new Exception(
                    $"[LRAssetResolver] 自动修复候选无法加载为 {typeof(T).Name}: {resolvedPath}（原路径={path}, owner={owner}）");
            }

            LRAutoFixLog.Add("asset", owner, requestedPath, resolvedPath, reason);
            return asset;
        }

        static bool TryResolvePath<T>(string requestedPath, out string resolvedPath, out string reason)
            where T : UnityEngine.Object
        {
            resolvedPath = null;
            reason = null;

            string fileName = Path.GetFileName(requestedPath);
            string stem = Path.GetFileNameWithoutExtension(fileName);
            if (string.IsNullOrEmpty(fileName) || string.IsNullOrEmpty(stem))
            {
                reason = "路径没有有效文件名";
                return false;
            }

            var candidates = new List<string>();
            foreach (string guid in AssetDatabase.FindAssets(stem))
            {
                string assetPath = AssetDatabase.GUIDToAssetPath(guid);
                if (string.IsNullOrEmpty(assetPath))
                {
                    continue;
                }

                assetPath = assetPath.Replace("\\", "/");
                if (!string.Equals(Path.GetFileName(assetPath), fileName, StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }
                if (AssetDatabase.LoadAssetAtPath<T>(assetPath) == null)
                {
                    continue;
                }
                if (!candidates.Contains(assetPath))
                {
                    candidates.Add(assetPath);
                }
            }

            if (candidates.Count == 0)
            {
                reason = $"按文件名 \"{fileName}\" 在 Assets 下找不到可加载为 {typeof(T).Name} 的资源";
                return false;
            }

            if (candidates.Count == 1)
            {
                resolvedPath = candidates[0];
                reason = "原路径不存在，按唯一同名资源自动修复";
                return true;
            }

            string requestedDir = Path.GetDirectoryName(requestedPath);
            string[] requestedSegments = SplitPath(requestedDir);
            var scored = candidates
                .Select(candidate => new CandidateScore
                {
                    Path = candidate,
                    Suffix = CountCommonSuffix(requestedSegments, SplitPath(Path.GetDirectoryName(candidate))),
                    Atlas = candidate.IndexOf("/AtlasResources/", StringComparison.OrdinalIgnoreCase) >= 0 ? 1 : 0,
                    Length = candidate.Length,
                })
                .OrderByDescending(candidate => candidate.Suffix)
                .ThenByDescending(candidate => candidate.Atlas)
                .ThenBy(candidate => candidate.Length)
                .ThenBy(candidate => candidate.Path, StringComparer.Ordinal)
                .ToList();

            CandidateScore top = scored[0];
            List<CandidateScore> tied = scored
                .Where(candidate => candidate.Suffix == top.Suffix
                                    && candidate.Atlas == top.Atlas
                                    && candidate.Length == top.Length)
                .ToList();

            if (tied.Count > 1)
            {
                reason = "存在多个同优先级同名候选: " + string.Join(", ", tied.Select(candidate => candidate.Path));
                return false;
            }

            resolvedPath = top.Path;
            reason = $"原路径不存在，按同名资源+目录相近度自动修复（同名候选 {candidates.Count} 个）";
            return true;
        }

        static string[] SplitPath(string path)
        {
            if (string.IsNullOrEmpty(path))
            {
                return new string[0];
            }
            return path.Replace("\\", "/").Split(new[] { '/' }, StringSplitOptions.RemoveEmptyEntries);
        }

        static int CountCommonSuffix(string[] left, string[] right)
        {
            int count = 0;
            int i = left.Length - 1;
            int j = right.Length - 1;
            while (i >= 0 && j >= 0 && string.Equals(left[i], right[j], StringComparison.OrdinalIgnoreCase))
            {
                count++;
                i--;
                j--;
            }
            return count;
        }

        sealed class CandidateScore
        {
            public string Path;
            public int Suffix;
            public int Atlas;
            public int Length;
        }
    }
}
