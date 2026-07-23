#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parse dotnet build / make compile output, extract error info, and give
fix suggestions for known deterministic error codes.

Usage:
    dotnet build Assembly-CSharp.csproj > build_output.txt 2>&1
    python fix_compile_errors.py build_output.txt

    # only errors from a specific newly-generated file
    python fix_compile_errors.py build_output.txt --filter GrowthFund

Design principle (maps to the "auto-fix" P1 item in OPTIMIZATION_SUMMARY.md):
- This script does NOT guess-and-replace code. It only does
  "classify + locate + suggest". The actual Edit is done by the caller
  (the Agent running the lr-openspec-apply flow).
- Two categories:
  1. Deterministic: fix strategy is unique, safe to apply directly.
     e.g. CS0506 (wrongly added override), CS0308 (wrong generic overload).
  2. Grep-assisted: must find the real API usage in the project first,
     cannot guess. e.g. CS1503 (arg type mismatch), CS0117 (member not
     found), CS1061 (property/method not found).

Note: all console output is plain ASCII on purpose — Windows GBK consoles
mangle Unicode (emoji, CJK) written via print(), so keep this script's
stdout ASCII-only. Put any CJK explanation only in comments/docstrings.
"""

import re
import sys
import argparse
from collections import defaultdict

# error code -> (category, deterministic fix?, advice)
ERROR_RULES = {
    "CS0506": {
        "category": "cannot override non-virtual inherited member",
        "deterministic": True,
        "advice": "Remove the 'override' keyword (and the matching base.{method}() call if the base method isn't actually virtual)",
    },
    "CS0308": {
        "category": "generic method has no matching overload",
        "deterministic": True,
        "advice": "Drop the <T> type argument and use the non-generic overload; if none exists, fall back to GetComponent<T>()/AddComponent<T>()",
    },
    "CS1503": {
        "category": "argument type mismatch",
        "deterministic": False,
        "advice": "Grep the target method signature to confirm the real parameter type (common trap: out int vs out long), then fix the call site's variable type",
    },
    "CS0117": {
        "category": "type does not contain member",
        "deterministic": False,
        "advice": "Grep other call sites of the same type in the project to find the real static/extension method name, then replace",
    },
    "CS1061": {
        "category": "type does not contain property/method",
        "deterministic": False,
        "advice": "Grep the type definition to confirm the real property/method name (common trap: itemID vs configID)",
    },
    "CS0246": {
        "category": "type or namespace not found",
        "deterministic": True,
        "advice": "Add the missing using statement, or check for a typo in the type name",
    },
    "CS0029": {
        "category": "implicit conversion failed",
        "deterministic": False,
        "advice": "Grep both sides' type definitions to decide whether an explicit cast or a field type change is needed",
    },
}

# Matches: Path\File.cs(12,34): error CS0506: message
ERROR_LINE_RE = re.compile(
    r'^(?P<file>.+?\.(?:cs|cpp|h))\((?P<line>\d+),(?P<col>\d+)\):\s*error\s+(?P<code>[A-Z]+\d+):\s*(?P<message>.+)$'
)
# make output format: Path/File.cpp:12:34: error: message
MAKE_ERROR_RE = re.compile(
    r'^(?P<file>.+?\.(?:cpp|h)):(?P<line>\d+):(?P<col>\d+):\s*error:\s*(?P<message>.+)$'
)


def parse_errors(build_output, filter_str=None):
    errors = []
    for raw_line in build_output.splitlines():
        line = raw_line.strip()
        m = ERROR_LINE_RE.match(line)
        if m:
            d = m.groupdict()
            if filter_str and filter_str.lower() not in d["file"].lower():
                continue
            errors.append(d)
            continue

        m2 = MAKE_ERROR_RE.match(line)
        if m2:
            d = m2.groupdict()
            d["code"] = "CPP_ERROR"
            if filter_str and filter_str.lower() not in d["file"].lower():
                continue
            errors.append(d)
    return errors


def build_report(errors):
    if not errors:
        return "[OK] No compile errors detected\n"

    lines = []
    lines.append("[FAIL] Detected {0} compile error(s)\n".format(len(errors)))

    by_code = defaultdict(list)
    for e in errors:
        by_code[e["code"]].append(e)

    deterministic_count = 0
    grep_assisted_count = 0

    for code, items in by_code.items():
        rule = ERROR_RULES.get(code)
        lines.append("=" * 60)
        if rule:
            tag = "[AUTO-FIX]" if rule["deterministic"] else "[NEED-GREP]"
            lines.append("{0} {1}: {2} ({3} occurrence(s))".format(tag, code, rule["category"], len(items)))
            lines.append("  Fix strategy: {0}".format(rule["advice"]))
            if rule["deterministic"]:
                deterministic_count += len(items)
            else:
                grep_assisted_count += len(items)
        else:
            lines.append("[UNKNOWN] {0}: unregistered error code ({1} occurrence(s))".format(code, len(items)))
            lines.append("  Fix strategy: manual analysis; add to ERROR_RULES once resolved")

        for e in items:
            lines.append("  - {0}:{1} {2}".format(e["file"], e["line"], e["message"]))
        lines.append("")

    lines.append("=" * 60)
    lines.append("Summary: {0} deterministic auto-fixable, {1} need grep-assisted lookup, {2} unknown".format(
        deterministic_count, grep_assisted_count,
        len(errors) - deterministic_count - grep_assisted_count
    ))
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Parse compile errors and suggest fixes")
    parser.add_argument("build_output_file", help="Path to dotnet build / make output file")
    parser.add_argument("--filter", help="Only keep errors whose file path contains this string (e.g. the new module name)", default=None)
    args = parser.parse_args()

    try:
        with open(args.build_output_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except IOError as e:
        print("[ERROR] Failed to read file: {0}".format(e))
        sys.exit(1)

    errors = parse_errors(content, args.filter)
    report = build_report(errors)
    print(report)

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
