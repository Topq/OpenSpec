using System.Collections.Generic;
using System.Linq;

namespace LRUIPrefabGen
{
    /// <summary>
    /// One automatic repair performed during generation: a missing asset path
    /// resolved to a unique same-name asset, or a missing serialized field
    /// resolved to a uniquely similar field on the target type.
    /// </summary>
    public sealed class LRAutoFix
    {
        public string Kind;
        public string Owner;
        public string From;
        public string To;
        public string Reason;
    }

    /// <summary>
    /// Collects automatic repairs for the generation report. The generator
    /// clears this at the start of each run and writes the snapshot into
    /// generation-report.json, so a repair is never silent.
    /// </summary>
    public static class LRAutoFixLog
    {
        static readonly List<LRAutoFix> Fixes = new List<LRAutoFix>();

        public static void Clear()
        {
            Fixes.Clear();
        }

        public static void Add(string kind, string owner, string from, string to, string reason)
        {
            Fixes.Add(new LRAutoFix
            {
                Kind = kind,
                Owner = owner,
                From = from,
                To = to,
                Reason = reason,
            });
            UnityEngine.Debug.LogWarning(
                $"[LRAutoFix] {kind}: {from} -> {to} ({reason}, owner={owner})");
        }

        public static IReadOnlyList<LRAutoFix> Snapshot()
        {
            return Fixes.ToArray();
        }

        public static int Count
        {
            get { return Fixes.Count; }
        }
    }
}
