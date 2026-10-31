#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hybrid task-dependency checker for OpenSpec tasks.md.

Two dependency sources, explicit wins over inferred (per-task):

  (A) Explicit annotation in the task description:
      "... -> 依赖任务 1.2" or "... 依赖任务 1.1, 2.3"
      If present, ONLY these ids are used as dependencies for that task.

  (B) Heuristic inference (used only when a task has no explicit annotation):
      1. Any non-[Contract] task implicitly depends on ALL [Contract] tasks
         (Contract is the shared foundation, always first).
      2. Any [Integration] task implicitly depends on ALL non-Integration
         tasks (Server/Client/Config/Contract all done before integration).
      3. Within the same numeric subgroup (e.g. "4.3.1", "4.3.2", "4.3.3"
         all share subgroup "4.3"), task k implicitly depends on task k-1
         in that subgroup (skeleton before logic before polish).

This mirrors the pattern already encoded by hand in growth-fund/tasks.md's
Mermaid graph, but derives it automatically from task IDs + tags so it
works on any tasks.md without a hand-drawn graph.

Usage:
    python check_task_deps.py tasks.md --report
    python check_task_deps.py tasks.md --check 4.3.2

Note: stdout is ASCII-only by design (Windows GBK console mangles Unicode
written via print()).
"""

import re
import sys
import argparse

# Task descriptions in tasks.md are Chinese. Windows consoles default to
# the GBK code page, which mangles UTF-8 text written via print(). Force
# stdout/stderr to UTF-8 so descriptions render correctly regardless of
# the console's active code page.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

TASK_LINE_RE = re.compile(
    r'^- \[(?P<status>[ x])\]\s*(?P<id>\d+(?:\.\d+)*)\s*\[(?P<tag>\w+)\]\s*(?P<desc>.+)$'
)
EXPLICIT_DEP_RE = re.compile(r'依赖任务\s*([\d.\s,，]+)')
DEP_ID_RE = re.compile(r'\d+(?:\.\d+)+')


def parse_tasks(tasks_md_path):
    tasks = {}
    order = []
    with open(tasks_md_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            m = TASK_LINE_RE.match(line.strip())
            if not m:
                continue
            d = m.groupdict()
            task_id = d["id"]
            explicit = None
            dep_match = EXPLICIT_DEP_RE.search(d["desc"])
            if dep_match:
                explicit = DEP_ID_RE.findall(dep_match.group(1))
            tasks[task_id] = {
                "id": task_id,
                "tag": d["tag"],
                "status": d["status"],
                "desc": d["desc"].strip(),
                "explicit_deps": explicit,
            }
            order.append(task_id)
    return tasks, order


def subgroup_of(task_id):
    """'4.3.2' -> '4.3'; '4.3' -> None (top-level, no subgroup sibling logic); '1.1' -> None"""
    parts = task_id.split(".")
    if len(parts) >= 3:
        return ".".join(parts[:-1])
    return None


def compute_deps(tasks, order):
    """Return {task_id: [dep_ids]} using explicit-wins-over-inferred rule."""
    contract_ids = [t["id"] for t in tasks.values() if t["tag"] == "Contract"]
    non_integration_ids = [t["id"] for t in tasks.values() if t["tag"] != "Integration"]

    # group tasks by subgroup, preserving file order, to compute "previous sibling"
    subgroup_members = {}
    for task_id in order:
        sg = subgroup_of(task_id)
        if sg is None:
            continue
        subgroup_members.setdefault(sg, []).append(task_id)

    deps = {}
    for task_id in order:
        t = tasks[task_id]
        if t["explicit_deps"]:
            deps[task_id] = list(dict.fromkeys(t["explicit_deps"]))  # dedupe, keep order
            continue

        inferred = []
        if t["tag"] == "Integration":
            inferred.extend(non_integration_ids)
        else:
            if t["tag"] != "Contract":
                inferred.extend(contract_ids)
            sg = subgroup_of(task_id)
            if sg is not None:
                siblings = subgroup_members.get(sg, [])
                idx = siblings.index(task_id)
                if idx > 0:
                    inferred.append(siblings[idx - 1])

        deps[task_id] = list(dict.fromkeys(inferred))

    return deps


def unmet_deps(task_id, tasks, deps):
    return [dep for dep in deps.get(task_id, []) if dep in tasks and tasks[dep]["status"] != "x"]


def print_report(tasks, order, deps):
    ready = []
    blocked = []
    for task_id in order:
        t = tasks[task_id]
        if t["status"] == "x":
            continue
        unmet = unmet_deps(task_id, tasks, deps)
        if unmet:
            blocked.append((task_id, t, unmet))
        else:
            ready.append((task_id, t))

    print("=" * 60)
    print("READY ({0} task(s), no unmet dependencies)".format(len(ready)))
    print("=" * 60)
    for task_id, t in ready:
        print("  [ ] {0} [{1}] {2}".format(task_id, t["tag"], t["desc"]))

    print()
    print("=" * 60)
    print("BLOCKED ({0} task(s), waiting on dependencies)".format(len(blocked)))
    print("=" * 60)
    for task_id, t, unmet in blocked:
        source = "explicit" if tasks[task_id]["explicit_deps"] else "inferred"
        print("  [ ] {0} [{1}] {2}".format(task_id, t["tag"], t["desc"]))
        print("      unmet deps ({0}): {1}".format(source, ", ".join(unmet)))


def check_single(task_id, tasks, deps):
    if task_id not in tasks:
        print("[ERROR] Task {0} not found in tasks.md".format(task_id))
        return 2

    unmet = unmet_deps(task_id, tasks, deps)
    if not unmet:
        print("[OK] Task {0} has no unmet dependencies, ready to execute".format(task_id))
        return 0

    source = "explicit" if tasks[task_id]["explicit_deps"] else "inferred"
    print("[BLOCKED] Task {0} has unmet dependencies ({1}):".format(task_id, source))
    for dep in unmet:
        dep_task = tasks.get(dep)
        desc = dep_task["desc"] if dep_task else "(not found in tasks.md)"
        print("  - {0}: {1}".format(dep, desc))
    return 1


def main():
    parser = argparse.ArgumentParser(description="Hybrid explicit+inferred task dependency checker")
    parser.add_argument("tasks_md", help="Path to tasks.md")
    parser.add_argument("--report", action="store_true", help="Print full ready/blocked report")
    parser.add_argument("--check", metavar="TASK_ID", help="Check whether a single task is ready to execute")
    args = parser.parse_args()

    tasks, order = parse_tasks(args.tasks_md)
    deps = compute_deps(tasks, order)

    if args.check:
        sys.exit(check_single(args.check, tasks, deps))

    print_report(tasks, order, deps)
    sys.exit(0)


if __name__ == "__main__":
    main()
