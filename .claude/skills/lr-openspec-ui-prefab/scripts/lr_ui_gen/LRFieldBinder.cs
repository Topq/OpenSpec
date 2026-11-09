using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using UnityEngine;
using UnityEngine.UI;

namespace LRUIPrefabGen
{
    /// <summary>
    /// Binds a GameObject (or the component type its data-field target expects)
    /// to a [SerializeField] field on a MonoBehaviour instance, via reflection.
    /// This is the step that replaces manual drag-and-drop in the Inspector.
    ///
    /// 扩展语法:
    /// - "m_TargetImages[0]" - 绑定到数组/列表的第 0 个元素
    /// - "graphic,m_ActiveContentRoot" - 同时绑定到多个字段（逗号分隔）
    ///
    /// 字段名写错时，会在目标类型上找唯一一个类型兼容、名称最相近的字段
    /// 自动修复，并把修复记录写入 generation-report.json；存在多个同分
    /// 候选时仍然失败，避免静默绑错对象。
    /// </summary>
    public static class FieldBinder
    {
        public static bool BindField(Component target, string fieldName, GameObject source)
        {
            string resolvedField;
            return BindField(target, fieldName, source, out resolvedField);
        }

        public static bool BindField(Component target, string fieldName, GameObject source, out string resolvedField)
        {
            resolvedField = fieldName;

            // 支持多字段绑定（逗号分隔）
            if (fieldName.Contains(","))
            {
                bool allBound = true;
                var resolvedFields = new List<string>();
                foreach (string f in fieldName.Split(','))
                {
                    string oneResolved;
                    allBound &= BindSingleField(target, f.Trim(), source, out oneResolved);
                    resolvedFields.Add(oneResolved);
                }
                resolvedField = string.Join(",", resolvedFields);
                return allBound;
            }

            return BindSingleField(target, fieldName, source, out resolvedField);
        }

        static bool BindSingleField(Component target, string fieldName, GameObject source, out string resolvedField)
        {
            resolvedField = fieldName;
            Type targetType = target.GetType();

            // 支持数组索引语法: "m_TargetImages[0]"
            if (fieldName.Contains("[") && fieldName.EndsWith("]"))
            {
                int bracketIndex = fieldName.IndexOf('[');
                string arrayFieldName = fieldName.Substring(0, bracketIndex);
                string indexStr = fieldName.Substring(bracketIndex + 1, fieldName.Length - bracketIndex - 2);

                if (!int.TryParse(indexStr, out int index))
                {
                    throw new Exception($"[LRFieldBinder] 无效的数组索引: {fieldName}");
                }

                string resolvedArrayField;
                bool bound = BindArrayElement(target, targetType, arrayFieldName, index, source, out resolvedArrayField);
                resolvedField = $"{resolvedArrayField}[{index}]";
                return bound;
            }

            // 普通字段绑定
            FieldInfo field = FindField(targetType, fieldName);
            if (field == null)
            {
                string reason;
                field = ResolveFieldBySimilarity(targetType, fieldName, source, false, out reason);
                if (field == null)
                {
                    throw new Exception(
                        $"[LRFieldBinder] {targetType.FullName} 上找不到字段: {fieldName}（自动修复失败：{reason}）");
                }
                resolvedField = field.Name;
                LRAutoFixLog.Add("field", targetType.FullName, fieldName, field.Name, reason);
            }

            object value = ResolveValue(field.FieldType, source);
            if (value == null)
            {
                throw new Exception(
                    $"[LRFieldBinder] 无法把 {source.name} 转换为字段 {resolvedField} 需要的类型 {field.FieldType.Name}");
            }

            field.SetValue(target, value);
            return true;
        }

        static bool BindArrayElement(
            Component target,
            Type targetType,
            string arrayFieldName,
            int index,
            GameObject source,
            out string resolvedField)
        {
            resolvedField = arrayFieldName;
            FieldInfo field = FindField(targetType, arrayFieldName);
            if (field == null)
            {
                string reason;
                field = ResolveFieldBySimilarity(targetType, arrayFieldName, source, true, out reason);
                if (field == null)
                {
                    throw new Exception(
                        $"[LRFieldBinder] {targetType.FullName} 上找不到数组字段: {arrayFieldName}（自动修复失败：{reason}）");
                }
                resolvedField = field.Name;
                LRAutoFixLog.Add("field", targetType.FullName, arrayFieldName, field.Name, reason);
            }

            // 获取数组对象
            object arrayObj = field.GetValue(target);
            if (arrayObj == null)
            {
                // 数组未初始化，创建新数组
                Type elementType = field.FieldType.GetElementType();
                if (elementType == null)
                {
                    throw new Exception($"[LRFieldBinder] 字段 {resolvedField} 不是数组类型");
                }

                Array newArray = Array.CreateInstance(elementType, index + 1);
                field.SetValue(target, newArray);
                arrayObj = newArray;
            }

            Array array = arrayObj as Array;
            if (array == null)
            {
                throw new Exception($"[LRFieldBinder] 字段 {resolvedField} 不是数组类型");
            }

            // 扩展数组（如果索引超出当前长度）
            if (index >= array.Length)
            {
                Type elementType = field.FieldType.GetElementType();
                Array newArray = Array.CreateInstance(elementType, index + 1);
                Array.Copy(array, newArray, array.Length);
                field.SetValue(target, newArray);
                array = newArray;
            }

            // 解析元素值
            Type elemType = field.FieldType.GetElementType();
            object value = ResolveValue(elemType, source);

            if (value == null)
            {
                throw new Exception($"[LRFieldBinder] 无法把 {source.name} 转换为数组元素类型 {elemType.Name}");
            }

            array.SetValue(value, index);
            return true;
        }

        static FieldInfo FindField(Type type, string fieldName)
        {
            const BindingFlags flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
            for (Type t = type; t != null; t = t.BaseType)
            {
                FieldInfo field = t.GetField(fieldName, flags);
                if (field != null)
                {
                    return field;
                }
            }
            return null;
        }

        /// <summary>
        /// Finds the unique type-compatible field whose normalized name is
        /// closest to the requested one. A normalized exact match wins; a
        /// Levenshtein match is accepted only when it is unique and within a
        /// conservative threshold. Ambiguity returns null, never a guess.
        /// </summary>
        static FieldInfo ResolveFieldBySimilarity(
            Type type,
            string fieldName,
            GameObject source,
            bool arrayField,
            out string reason)
        {
            reason = null;
            var fields = new List<FieldInfo>();
            for (Type current = type; current != null; current = current.BaseType)
            {
                fields.AddRange(current.GetFields(
                    BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly));
            }

            List<FieldInfo> compatible = fields
                .Where(field => IsCompatible(field, source, arrayField))
                .ToList();

            if (compatible.Count == 0)
            {
                reason = "没有类型兼容的候选字段";
                return null;
            }

            string normalizedTarget = NormalizeName(fieldName);
            List<FieldInfo> normalizedMatches = compatible
                .Where(field => NormalizeName(field.Name) == normalizedTarget)
                .ToList();

            if (normalizedMatches.Count == 1)
            {
                reason = $"字段名规范化后匹配（{fieldName} -> {normalizedMatches[0].Name}）";
                return normalizedMatches[0];
            }
            if (normalizedMatches.Count > 1)
            {
                reason = "规范化后存在多个候选: " +
                         string.Join(", ", normalizedMatches.Select(field => field.Name));
                return null;
            }

            int threshold = Math.Max(2, Math.Min(4, fieldName.Length / 4));
            List<FieldCandidate> ranked = compatible
                .Select(field => new FieldCandidate
                {
                    Field = field,
                    Distance = Levenshtein(NormalizeName(field.Name), normalizedTarget),
                })
                .OrderBy(candidate => candidate.Distance)
                .ThenBy(candidate => candidate.Field.Name, StringComparer.Ordinal)
                .ToList();

            if (ranked.Count == 0 || ranked[0].Distance > threshold)
            {
                int best = ranked.Count == 0 ? -1 : ranked[0].Distance;
                reason = $"没有相似度足够的候选（最小编辑距离 {best}，阈值 {threshold}）";
                return null;
            }

            if (ranked.Count > 1 && ranked[1].Distance == ranked[0].Distance)
            {
                reason = "存在多个同距离候选: " + string.Join(", ", ranked
                    .Where(candidate => candidate.Distance == ranked[0].Distance)
                    .Select(candidate => candidate.Field.Name));
                return null;
            }

            reason = $"按名称相似度自动修复（{fieldName} -> {ranked[0].Field.Name}, 编辑距离={ranked[0].Distance}）";
            return ranked[0].Field;
        }

        static bool IsCompatible(FieldInfo field, GameObject source, bool arrayField)
        {
            if (arrayField)
            {
                return field.FieldType.IsArray
                       && ResolveValue(field.FieldType.GetElementType(), source) != null;
            }
            return ResolveValue(field.FieldType, source) != null;
        }

        static string NormalizeName(string name)
        {
            if (string.IsNullOrEmpty(name))
            {
                return string.Empty;
            }
            return new string(name.Where(char.IsLetterOrDigit).ToArray()).ToLowerInvariant();
        }

        static int Levenshtein(string left, string right)
        {
            if (left == null) left = string.Empty;
            if (right == null) right = string.Empty;

            var distance = new int[left.Length + 1, right.Length + 1];
            for (int i = 0; i <= left.Length; i++) distance[i, 0] = i;
            for (int j = 0; j <= right.Length; j++) distance[0, j] = j;

            for (int i = 1; i <= left.Length; i++)
            {
                for (int j = 1; j <= right.Length; j++)
                {
                    int cost = left[i - 1] == right[j - 1] ? 0 : 1;
                    distance[i, j] = Math.Min(
                        Math.Min(distance[i - 1, j] + 1, distance[i, j - 1] + 1),
                        distance[i - 1, j - 1] + cost);
                }
            }
            return distance[left.Length, right.Length];
        }

        static object ResolveValue(Type fieldType, GameObject source)
        {
            if (fieldType == typeof(GameObject))
            {
                return source;
            }
            if (fieldType == typeof(Transform) || fieldType == typeof(RectTransform))
            {
                return source.transform;
            }
            if (typeof(Component).IsAssignableFrom(fieldType))
            {
                Component component = source.GetComponent(fieldType);
                if (component == null && fieldType == typeof(Image))
                {
                    // Buttons commonly expose the Image as targetGraphic only;
                    // fall back to any Graphic on the same object.
                    component = source.GetComponent<Graphic>();
                }
                return component;
            }
            return null;
        }

        sealed class FieldCandidate
        {
            public FieldInfo Field;
            public int Distance;
        }
    }
}
