using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text;
using TMPro;
using UnityEditor;
using UnityEngine;
using UnityEngine.UI;

namespace LRUIPrefabGen
{
    /// <summary>
    /// 扫描项目 Prefab，统计 control.progress/toggle/feedback.red-point 的高频结构模式，
    /// 产出候选配方报告（JSON 格式），供人工审核后生成 ComponentRecipes/*.json。
    ///
    /// 使用方式：从 OpenSpec skill 通过 MCP reflection-method-call 调用 ScanAndReport()。
    /// </summary>
    public static class LRComponentRecipeScanner
    {
        // 扫描配置：对齐 unity-ui-components.md 原始扫描范围
        const string SCAN_ROOT = "Assets/Resources/PanelUI";

        // 目标组件映射：语义 ID → C# 类型全名
        static readonly Dictionary<string, string> TARGET_COMPONENTS = new Dictionary<string, string>
        {
            { "control.progress", "LR.LRProgressBar" },
            { "control.toggle", "UnityEngine.UI.Toggle" },
            { "feedback.red-point", "LR.UIRedPointWatcher" }
        };

        /// <summary>
        /// 主入口：扫描所有目标组件，返回 JSON 格式的候选报告。
        /// 调用示例（从 MCP）：
        ///   reflection-method-call
        ///     filter: { typeName: "LRComponentRecipeScanner", methodName: "ScanAndReport" }
        ///     executeInMainThread: true
        /// </summary>
        public static string ScanAndReport()
        {
            var report = new StringBuilder();
            report.AppendLine("{");
            report.AppendLine("  \"scanTimestamp\": \"" + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + "\",");
            report.AppendLine("  \"scanRoot\": \"" + SCAN_ROOT + "\",");
            report.AppendLine("  \"components\": [");

            bool firstComponent = true;
            foreach (var kvp in TARGET_COMPONENTS)
            {
                if (!firstComponent) report.AppendLine(",");
                firstComponent = false;

                string semanticId = kvp.Key;
                string typeName = kvp.Value;
                report.Append(ScanComponent(semanticId, typeName));
            }

            report.AppendLine();
            report.AppendLine("  ]");
            report.AppendLine("}");

            string result = report.ToString();
            Debug.Log("[LRComponentRecipeScanner] 扫描完成，报告长度: " + result.Length + " 字符");
            return result;
        }

        static string ScanComponent(string semanticId, string typeName)
        {
            Type componentType = FindType(typeName);
            if (componentType == null)
            {
                return $"    {{ \"semanticId\": \"{semanticId}\", \"error\": \"类型未找到: {typeName}\" }}";
            }

            // 1. 找到所有挂载了该组件的 Prefab
            List<GameObject> instances = FindAllInstances(componentType);

            if (instances.Count == 0)
            {
                return $"    {{ \"semanticId\": \"{semanticId}\", \"totalInstances\": 0, \"groups\": [] }}";
            }

            // 2. 按结构指纹分组
            var groups = GroupByStructureFingerprint(instances, componentType);

            // 3. 按实例数从高到低排序，取 Top 3
            var topGroups = groups.OrderByDescending(g => g.Instances.Count).Take(3).ToList();

            // 4. 生成 JSON
            var sb = new StringBuilder();
            sb.AppendLine($"    {{");
            sb.AppendLine($"      \"semanticId\": \"{semanticId}\",");
            sb.AppendLine($"      \"componentType\": \"{typeName}\",");
            sb.AppendLine($"      \"totalInstances\": {instances.Count},");
            sb.AppendLine($"      \"groups\": [");

            for (int i = 0; i < topGroups.Count; i++)
            {
                if (i > 0) sb.AppendLine(",");
                sb.Append(SerializeGroup(topGroups[i], i + 1, instances.Count));
            }

            sb.AppendLine();
            sb.AppendLine($"      ]");
            sb.Append($"    }}");

            return sb.ToString();
        }

        static List<GameObject> FindAllInstances(Type componentType)
        {
            var result = new List<GameObject>();
            string[] prefabGuids = AssetDatabase.FindAssets("t:Prefab", new[] { SCAN_ROOT });

            foreach (string guid in prefabGuids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (prefab == null) continue;

                // 包含未激活节点（避免漏掉"领取后隐藏"这类状态节点）
                var components = prefab.GetComponentsInChildren(componentType, true);
                foreach (var comp in components)
                {
                    result.Add(comp.gameObject);
                }
            }

            return result;
        }

        static List<StructureGroup> GroupByStructureFingerprint(List<GameObject> instances, Type componentType)
        {
            var groupDict = new Dictionary<string, StructureGroup>();

            foreach (var go in instances)
            {
                var comp = go.GetComponent(componentType);
                if (comp == null) continue;

                string fingerprint = ComputeFingerprint(comp);

                if (!groupDict.TryGetValue(fingerprint, out var group))
                {
                    group = new StructureGroup
                    {
                        Fingerprint = fingerprint,
                        Instances = new List<GameObject>()
                    };
                    groupDict[fingerprint] = group;
                }

                group.Instances.Add(go);
            }

            return groupDict.Values.ToList();
        }

        /// <summary>
        /// 计算组件的结构指纹：字段名 → 位置关系（"自己身上的 X 组件" / "第 N 个子节点，挂了 Y" / "null"）
        /// </summary>
        static string ComputeFingerprint(Component comp)
        {
            var parts = new List<string>();
            Type type = comp.GetType();

            // 获取所有 [SerializeField] 和 public 字段
            var fields = type.GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic)
                .Where(f => f.IsPublic || f.GetCustomAttribute<SerializeField>() != null)
                .OrderBy(f => f.Name)
                .ToList();

            foreach (var field in fields)
            {
                object value = field.GetValue(comp);

                if (value == null)
                {
                    parts.Add($"{field.Name}=null");
                }
                else if (field.FieldType.IsArray)
                {
                    // 数组字段：按元素展开
                    Array arr = (Array)value;
                    for (int i = 0; i < arr.Length; i++)
                    {
                        object elem = arr.GetValue(i);
                        string elemDescriptor = DescribeTarget(elem, comp.gameObject);
                        parts.Add($"{field.Name}[{i}]={elemDescriptor}");
                    }
                }
                else
                {
                    string descriptor = DescribeTarget(value, comp.gameObject);
                    parts.Add($"{field.Name}={descriptor}");
                }
            }

            return string.Join(";", parts);
        }

        /// <summary>
        /// 描述一个字段值的位置关系（用于指纹计算）
        /// </summary>
        static string DescribeTarget(object target, GameObject ownerGo)
        {
            if (target == null) return "null";

            GameObject targetGo = null;
            string componentTypeSuffix = "";

            if (target is GameObject go)
            {
                try
                {
                    targetGo = go;
                    // 访问 transform 触发 Unity 的赋值检查
                    _ = go.transform;
                }
                catch (UnityEngine.UnassignedReferenceException)
                {
                    return "null";
                }
            }
            else if (target is Component comp)
            {
                // Unity 对未赋值的 SerializeField 引用，访问 gameObject 会抛 UnassignedReferenceException
                try
                {
                    targetGo = comp.gameObject;
                    componentTypeSuffix = $":{comp.GetType().Name}";
                }
                catch (UnityEngine.UnassignedReferenceException)
                {
                    return "null";
                }
            }
            else
            {
                // 基础类型（float/int 等）
                return $"value:{target}";
            }

            if (targetGo == null) return "null";

            if (targetGo == ownerGo)
            {
                return $"self{componentTypeSuffix}";
            }

            // 判断是否为直接子节点
            int childIndex = -1;
            for (int i = 0; i < ownerGo.transform.childCount; i++)
            {
                if (ownerGo.transform.GetChild(i).gameObject == targetGo)
                {
                    childIndex = i;
                    break;
                }
            }

            if (childIndex >= 0)
            {
                // 直接子节点：记录索引 + 组件类型组合
                var compTypes = string.Join(",", targetGo.GetComponents<Component>()
                    .Select(c => c.GetType().Name)
                    .OrderBy(n => n));
                return $"child[{childIndex}]({compTypes}){componentTypeSuffix}";
            }

            // 更深层级的子孙节点：记录相对路径
            string path = GetRelativePath(ownerGo.transform, targetGo.transform);
            return path != null ? $"desc:{path}{componentTypeSuffix}" : "unknown";
        }

        static string GetRelativePath(Transform from, Transform to)
        {
            if (to == null || from == null) return null;
            if (!to.IsChildOf(from)) return null;

            var parts = new List<string>();
            Transform current = to;
            while (current != from && current != null)
            {
                parts.Insert(0, current.name);
                current = current.parent;
            }

            return string.Join("/", parts);
        }

        static string SerializeGroup(StructureGroup group, int rank, int totalInstances)
        {
            var sb = new StringBuilder();
            int count = group.Instances.Count;
            float percentage = (float)count / totalInstances * 100f;

            sb.AppendLine($"        {{");
            sb.AppendLine($"          \"rank\": {rank},");
            sb.AppendLine($"          \"instanceCount\": {count},");
            sb.AppendLine($"          \"percentage\": {percentage:F1},");
            sb.AppendLine($"          \"fingerprint\": \"{EscapeJson(group.Fingerprint)}\",");

            // 示例 Prefab 路径（取前 3 个）
            var examplePaths = group.Instances.Take(3)
                .Select(go => AssetDatabase.GetAssetPath(go))
                .Where(p => !string.IsNullOrEmpty(p))
                .Select(p => p.Replace("\\", "/"))
                .ToList();

            sb.AppendLine($"          \"examplePrefabs\": [");
            for (int i = 0; i < examplePaths.Count; i++)
            {
                sb.Append($"            \"{examplePaths[i]}\"");
                if (i < examplePaths.Count - 1) sb.AppendLine(",");
                else sb.AppendLine();
            }
            sb.AppendLine($"          ],");

            // 详细字段统计（从指纹反推）
            sb.Append(SerializeFieldStats(group));

            sb.Append($"        }}");
            return sb.ToString();
        }

        static string SerializeFieldStats(StructureGroup group)
        {
            // 从第一个实例提取字段信息（同组内结构一致）
            if (group.Instances.Count == 0) return "\"fields\": []";

            GameObject sampleGo = group.Instances[0];
            var comp = sampleGo.GetComponent(FindTypeFromFingerprint(group.Fingerprint));
            if (comp == null) return "\"fields\": []";

            var sb = new StringBuilder();
            sb.AppendLine("\"fields\": [");

            var fields = comp.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic)
                .Where(f => f.IsPublic || f.GetCustomAttribute<SerializeField>() != null)
                .OrderBy(f => f.Name)
                .ToList();

            bool firstField = true;
            foreach (var field in fields)
            {
                object value = field.GetValue(comp);
                if (value == null) continue;  // 跳过 null 字段

                if (!firstField) sb.AppendLine(",");
                firstField = false;

                sb.AppendLine($"            {{");
                sb.AppendLine($"              \"fieldName\": \"{field.Name}\",");
                sb.AppendLine($"              \"fieldType\": \"{field.FieldType.Name}\",");

                if (field.FieldType.IsArray)
                {
                    Array arr = (Array)value;
                    sb.AppendLine($"              \"arrayLength\": {arr.Length},");

                    // 统计数组元素指向的节点的常见命名
                    var elementNames = new List<string>();
                    for (int i = 0; i < arr.Length; i++)
                    {
                        object elem = arr.GetValue(i);
                        if (elem is Component c) elementNames.Add(c.gameObject.name);
                        else if (elem is GameObject g) elementNames.Add(g.name);
                    }
                    sb.AppendLine($"              \"elementNames\": [{string.Join(", ", elementNames.Select(n => $"\"{n}\""))}]");
                }
                else if (value is Component c)
                {
                    sb.AppendLine($"              \"targetNodeName\": \"{c.gameObject.name}\",");
                    sb.AppendLine($"              \"targetComponentType\": \"{c.GetType().Name}\"");
                }
                else if (value is GameObject g)
                {
                    sb.AppendLine($"              \"targetNodeName\": \"{g.name}\"");
                }
                else
                {
                    sb.AppendLine($"              \"value\": \"{value}\"");
                }

                sb.Append($"            }}");
            }

            sb.AppendLine();
            sb.Append($"          ]");
            return sb.ToString();
        }

        static Type FindTypeFromFingerprint(string fingerprint)
        {
            // 从指纹推断类型（简化版：假设指纹里能找到关键类型信息）
            foreach (var kvp in TARGET_COMPONENTS)
            {
                Type t = FindType(kvp.Value);
                if (t != null) return t;
            }
            return null;
        }

        static Type FindType(string fullName)
        {
            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type t = assembly.GetType(fullName);
                if (t != null) return t;
            }
            return null;
        }

        static string EscapeJson(string str)
        {
            return str.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n").Replace("\r", "\\r");
        }

        class StructureGroup
        {
            public string Fingerprint;
            public List<GameObject> Instances;
        }
    }
}
