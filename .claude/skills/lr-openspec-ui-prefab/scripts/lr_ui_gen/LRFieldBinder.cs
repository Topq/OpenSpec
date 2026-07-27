using System;
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
    /// </summary>
    public static class FieldBinder
    {
        public static void BindField(Component target, string fieldName, GameObject source)
        {
            // 支持多字段绑定（逗号分隔）
            if (fieldName.Contains(","))
            {
                string[] fields = fieldName.Split(',');
                foreach (string f in fields)
                {
                    BindSingleField(target, f.Trim(), source);
                }
                return;
            }

            BindSingleField(target, fieldName, source);
        }

        static void BindSingleField(Component target, string fieldName, GameObject source)
        {
            Type targetType = target.GetType();

            // 支持数组索引语法: "m_TargetImages[0]"
            if (fieldName.Contains("[") && fieldName.EndsWith("]"))
            {
                int bracketIndex = fieldName.IndexOf('[');
                string arrayFieldName = fieldName.Substring(0, bracketIndex);
                string indexStr = fieldName.Substring(bracketIndex + 1, fieldName.Length - bracketIndex - 2);

                if (!int.TryParse(indexStr, out int index))
                {
                    Debug.LogWarning($"[LRFieldBinder] 无效的数组索引: {fieldName}");
                    return;
                }

                BindArrayElement(target, targetType, arrayFieldName, index, source);
                return;
            }

            // 普通字段绑定
            FieldInfo field = FindField(targetType, fieldName);
            if (field == null)
            {
                Debug.LogWarning($"[LRFieldBinder] {targetType.FullName} 上找不到字段: {fieldName}，跳过绑定");
                return;
            }

            object value = ResolveValue(field.FieldType, source);
            if (value == null)
            {
                Debug.LogWarning($"[LRFieldBinder] 无法把 {source.name} 转换为字段 {fieldName} 需要的类型 {field.FieldType.Name}，跳过绑定");
                return;
            }

            field.SetValue(target, value);
        }

        static void BindArrayElement(Component target, Type targetType, string arrayFieldName, int index, GameObject source)
        {
            FieldInfo field = FindField(targetType, arrayFieldName);
            if (field == null)
            {
                Debug.LogWarning($"[LRFieldBinder] {targetType.FullName} 上找不到数组字段: {arrayFieldName}");
                return;
            }

            // 获取数组对象
            object arrayObj = field.GetValue(target);
            if (arrayObj == null)
            {
                // 数组未初始化，创建新数组
                Type elementType = field.FieldType.GetElementType();
                if (elementType == null)
                {
                    Debug.LogWarning($"[LRFieldBinder] 字段 {arrayFieldName} 不是数组类型");
                    return;
                }

                Array newArray = Array.CreateInstance(elementType, index + 1);
                field.SetValue(target, newArray);
                arrayObj = newArray;
            }

            Array array = arrayObj as Array;
            if (array == null)
            {
                Debug.LogWarning($"[LRFieldBinder] 字段 {arrayFieldName} 不是数组类型");
                return;
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
                Debug.LogWarning($"[LRFieldBinder] 无法把 {source.name} 转换为数组元素类型 {elemType.Name}");
                return;
            }

            array.SetValue(value, index);
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
    }
}
