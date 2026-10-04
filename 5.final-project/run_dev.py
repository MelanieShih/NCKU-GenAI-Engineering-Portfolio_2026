#!/usr/bin/env python3
"""Local dev runner for AIASE 2026 with file-based result contract.

This version keeps the new teacher-required flow:
- invoke Hermes with `skills,terminal --yolo -Q`
- let each skill write JSON to `AIASE_RESULT_PATH`
- grade by reading the result file

It also preserves backward-compatible helper exports used by the public tests:
- `extract_last_json_block`
- `bag_equal`
- `is_read_only_sql`
- `run_sql`
- `load_basic_tasks`
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aiase_contract as contract


REPO_ROOT = Path(__file__).resolve().parent
DEV_SET_DIR = REPO_ROOT / "dev_set"
HERMES_BASE = ["hermes", "chat", "--toolsets", "skills,terminal", "--yolo", "-Q"]

_FENCED_JSON_RE = re.compile(
    r"```json[ \t]*\r?\n(?P<body>.*?)\r?\n```",
    re.DOTALL | re.IGNORECASE,
)

READ_ONLY_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|ATTACH|DETACH|REPLACE|TRUNCATE|VACUUM|PRAGMA)\b",
    re.IGNORECASE,
)


def extract_last_json_block(stdout) -> Optional[dict]:
    if not isinstance(stdout, str):
        return None
    matches = _FENCED_JSON_RE.findall(stdout)
    if not matches:
        return None
    try:
        obj = json.loads(matches[-1].strip())
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _cell(value):
    if isinstance(value, bytes):
        return ("__bytes__", value)
    return value


def _row_to_hashable(row):
    if isinstance(row, tuple):
        return tuple(_cell(cell) for cell in row)
    if isinstance(row, list):
        return tuple(_cell(cell) for cell in row)
    return (_cell(row),)


def bag_equal(rows_a, rows_b) -> bool:
    left = [_row_to_hashable(row) for row in rows_a]
    right = [_row_to_hashable(row) for row in rows_b]
    if len(left) != len(right):
        return False
    return Counter(left) == Counter(right)


def is_read_only_sql(sql: str):
    if not isinstance(sql, str) or not sql.strip():
        return False, "Empty SQL."
    stripped = sql.strip()
    if ";" in stripped.rstrip(";"):
        return False, "Multiple SQL statements not allowed."
    if READ_ONLY_FORBIDDEN_KEYWORDS.search(sql):
        return False, "DDL/DML keyword detected."
    return True, ""


def run_sql(db_path, sql: str, timeout_sec: float = 5.0):
    con = sqlite3.connect(str(db_path), timeout=timeout_sec)
    try:
        con.execute("PRAGMA query_only = ON;")
        cur = con.execute(sql)
        return list(cur.fetchall())
    finally:
        con.close()


def load_basic_tasks() -> list[dict]:
    tasks = []
    basic_dir = DEV_SET_DIR / "basic"
    if not basic_dir.exists():
        return tasks
    for path in sorted(basic_dir.glob("task_nl2sql_*.json")):
        with open(path, encoding="utf-8") as handle:
            task = json.load(handle)
        db_path = task.get("db_path", "")
        if db_path:
            absolute_db = (REPO_ROOT / db_path).resolve()
            try:
                task["db_path"] = str(absolute_db.relative_to(REPO_ROOT))
            except ValueError:
                task["db_path"] = str(absolute_db)
        tasks.append(task)
    return tasks


def load_tasks(dev_dir: str, track: str | None) -> list[dict]:
    tasks = []
    patterns: list[str] = []

    if track in (None, "", "basic"):
        patterns.append(os.path.join(dev_dir, "basic", "task_nl2sql_*.json"))
    if track == "pairwise":
        patterns.extend(
            [
                os.path.join(dev_dir, "pairwise", "reference_tasks", "task_*.json"),
                os.path.join(dev_dir, "pairwise", "task_pairwise_EXAMPLE.json"),
            ]
        )
    if track == "open":
        patterns.append(os.path.join(dev_dir, "open_track", "repair_tasks", "*.json"))

    seen: set[str] = set()
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            if path in seen:
                continue
            seen.add(path)
            with open(path, encoding="utf-8") as handle:
                task = json.load(handle)
            db_path = task.get("db_path", "")
            if db_path and not os.path.isabs(db_path):
                task["db_path"] = str((REPO_ROOT / db_path).resolve())
            if "track" not in task:
                task["track"] = track or ("basic" if "task_nl2sql_" in os.path.basename(path) else track)
            tasks.append(task)
    return tasks


def build_skill_input(task: dict) -> str:
    drop = {"gold_sql", "db_path", "seed_sql", "track"}
    payload = {key: value for key, value in task.items() if key not in drop}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def invoke_skill(skill: str, task: dict, result_path: str, model: str | None) -> tuple[int, str]:
    env = dict(os.environ)
    env["AIASE_RESULT_PATH"] = result_path
    cmd = list(HERMES_BASE)
    if model:
        cmd += ["-m", model]
    cmd += ["-q", f"/{skill} {build_skill_input(task)}"]
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def evaluate_task(task: dict, result_path: str, track: str) -> tuple[bool, str]:
    obj = contract.read_result(result_path)
    if obj is None:
        return False, "no result file (task not produced)"

    if track == "basic":
        ok, reason = contract.validate_basic_schema(obj, task["task_id"])
        if not ok:
            return False, f"schema invalid: {reason}"
        try:
            got = run_sql(task["db_path"], obj["sql"])
        except Exception as exc:
            return False, f"student SQL failed to execute: {exc}"
        try:
            gold = run_sql(task["db_path"], task["gold_sql"])
        except Exception as exc:
            return False, f"gold SQL failed (dev-set bug): {exc}"
        if bag_equal(got, gold):
            return True, "result set matches gold (bag-equal)"
        return False, "result set differs from gold"

    if obj.get("task_id") != task["task_id"]:
        return False, "task_id mismatch"
    return True, "result file present & valid JSON object (grader judges correctness)"


def run(
    skill,
    dev_dir,
    only_task,
    track,
    limit,
    model,
    dry_run,
    dry_result_file,
    invoke=invoke_skill,
):
    tasks = load_tasks(dev_dir, track)
    if only_task:
        tasks = [task for task in tasks if task["task_id"] == only_task]
    if limit:
        tasks = tasks[:limit]

    results = []
    tmpdir = tempfile.mkdtemp(prefix="aiase_dev_")

    for task in tasks:
        result_path = dry_result_file if dry_run else os.path.join(tmpdir, f"{task['task_id']}.json")
        invoke_output = ""
        invoke_code = 0

        if not dry_run:
            if os.path.exists(result_path):
                os.remove(result_path)
            invoke_code, invoke_output = invoke(skill, task, result_path, model)

        passed, detail = evaluate_task(task, result_path, task.get("track", track or "basic"))
        if not passed and invoke_code != 0:
            output = (invoke_output or "").strip()
            if output:
                detail = f"{detail}; hermes failed: {output[:400]}"

        results.append({"task_id": task["task_id"], "passed": passed, "detail": detail})
        print(f"  [{'PASS' if passed else 'FAIL'}] {task['task_id']}: {detail}")

    total = len(results)
    passed_count = sum(1 for result in results if result["passed"])
    print(f"\nDev set: {passed_count}/{total} passed" + (f"  ({passed_count / total * 100:.0f}%)" if total else ""))
    return {"total": total, "passed": passed_count, "results": results}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", help="skill name, e.g. text2sql-<github_id>")
    parser.add_argument("--track", default="basic", help="basic | pairwise | open")
    parser.add_argument("--limit", type=int, default=0, help="only run the first N tasks")
    parser.add_argument("--task", dest="only_task", default=None)
    parser.add_argument("--model", default=None, help="override model (else config default)")
    parser.add_argument("--dev-dir", default=os.path.join(os.path.dirname(__file__), "dev_set"))
    parser.add_argument("--dry-run", action="store_true", help="do not invoke hermes; grade an existing result file")
    parser.add_argument("--result-file", dest="dry_result_file", default=None)
    args = parser.parse_args()

    if not args.dry_run and not args.skill:
        parser.error("--skill is required unless --dry-run")
    if args.dry_run and not args.dry_result_file:
        parser.error("--dry-run requires --result-file")

    summary = run(
        args.skill,
        args.dev_dir,
        args.only_task,
        args.track,
        args.limit,
        args.model,
        args.dry_run,
        args.dry_result_file,
    )
    return 0 if summary["total"] and summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
