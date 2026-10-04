#!/usr/bin/env python3
"""
Deterministic evaluator for the Open Track code-repair skill.

It compares a buggy implementation with a repaired implementation on the same
sample set and reports whether the repaired version demonstrably improves.
"""

from __future__ import annotations

import ast
import json
import signal
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path


def _emit(obj: dict) -> int:
    sys.stdout.write("```json\n")
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.stdout.write("\n```\n")
    return 0


def _load_payload(argv: list[str]) -> tuple[dict | None, str, str]:
    raw = ""
    source = ""
    if len(argv) >= 2 and str(argv[1]).strip():
        raw = argv[1]
        source = "argv"
    else:
        stdin_text = sys.stdin.read()
        if stdin_text.strip():
            raw = stdin_text
            source = "stdin"
    if not raw:
        return None, "missing", ""
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        return payload, "ok", source
    except (json.JSONDecodeError, ValueError) as exc:
        return None, "invalid", f"invalid {source} JSON: {exc}"


def compute_sloc(code: str) -> int:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as handle:
        handle.write(code)
        path = Path(handle.name)
    try:
        try:
            proc = subprocess.run(
                ["radon", "raw", str(path), "--json"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                if isinstance(data, dict):
                    for value in data.values():
                        if isinstance(value, dict) and "sloc" in value:
                            return int(value["sloc"])
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass

        count = 0
        for line in code.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                count += 1
        return count
    finally:
        try:
            path.unlink()
        except OSError:
            pass


def find_import_violations(code: str, forbidden: list[str]) -> list[str]:
    if not forbidden:
        return []
    forbidden_set = {item.strip() for item in forbidden if str(item).strip()}
    found: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ["<syntax error: imports not checked>"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in forbidden_set:
                    found.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                if root in forbidden_set:
                    found.append(node.module)
    return sorted(set(found))


def has_entry_function(code: str, entry: str) -> bool:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == entry:
            return True
    return False


class _Timeout(Exception):
    pass


@contextmanager
def _time_limit(seconds: float):
    if not hasattr(signal, "SIGALRM"):
        yield
        return

    def _handler(signum, frame):
        raise _Timeout("candidate timed out")

    previous = signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _samples_for_known_task(task_description: str, entry: str) -> list[dict]:
    text = f"{entry}\n{task_description}".lower()

    if "merge_intervals" in text or "interval" in text:
        return [
            {"input": [[]], "expected": []},
            {"input": [[[1, 3]]], "expected": [[1, 3]]},
            {"input": [[[1, 3], [2, 4]]], "expected": [[1, 4]]},
            {"input": [[[1, 2], [2, 3], [3, 5]]], "expected": [[1, 5]]},
            {"input": [[[5, 7], [1, 3], [2, 4]]], "expected": [[1, 4], [5, 7]]},
        ]

    if "binary_search" in text or ("sorted" in text and "target" in text):
        return [
            {"input": [[], 5], "expected": -1},
            {"input": [[5], 5], "expected": 0},
            {"input": [[1, 2, 3, 4, 5], 3], "expected": 2},
            {"input": [[1, 2, 3, 4, 5], 6], "expected": -1},
            {"input": [[1, 2, 3, 4, 5], 1], "expected": 0},
        ]

    if "parse_csv_line" in text or ("csv" in text and "quoted" in text):
        return [
            {"input": [""], "expected": [""]},
            {"input": ["a,b,c"], "expected": ["a", "b", "c"]},
            {"input": ["a,,b"], "expected": ["a", "", "b"]},
            {"input": ['a,"b,c",d'], "expected": ["a", "b,c", "d"]},
            {"input": ['"hello ""world"""'], "expected": ['hello "world"']},
        ]

    if "unique_paths" in text or ("grid" in text and "right or down" in text):
        return [
            {"input": [1, 1], "expected": 1},
            {"input": [1, 5], "expected": 1},
            {"input": [2, 2], "expected": 2},
            {"input": [3, 3], "expected": 6},
            {"input": [0, 5], "expected": 0},
        ]

    if "kth_smallest" in text or ("k-th smallest" in text):
        return [
            {"input": [[3, 1, 2], 1], "expected": 1},
            {"input": [[3, 1, 2], 2], "expected": 2},
            {"input": [[], 1], "expected": None},
            {"input": [[5], 2], "expected": None},
            {"input": [[1, 1, 1], 2], "expected": 1},
        ]

    return []


def select_samples(payload: dict, task_description: str, entry: str) -> tuple[list[dict], str]:
    explicit = payload.get("sample_inputs") or payload.get("sample_tests") or []
    if isinstance(explicit, list) and explicit:
        return explicit, "provided"

    known = _samples_for_known_task(task_description, entry)
    if known:
        return known, "derived"

    return [], "none"


def evaluate_candidate(code: str, entry: str, samples: list[dict], timeout_sec: float) -> dict:
    total = len(samples)
    if not entry:
        return {
            "passed": 0,
            "failed": total,
            "errors": ["constraints.entry_function not provided"],
        }
    if not has_entry_function(code, entry):
        return {
            "passed": 0,
            "failed": total,
            "errors": [f"entry function {entry!r} not found in candidate code"],
        }

    namespace: dict = {}
    try:
        exec(compile(code, "<candidate>", "exec"), namespace)
    except Exception as exc:
        return {
            "passed": 0,
            "failed": total,
            "errors": [f"compile/exec error: {exc!r}"],
        }

    func = namespace.get(entry)
    if not callable(func):
        return {
            "passed": 0,
            "failed": total,
            "errors": [f"entry function {entry!r} not callable after exec"],
        }

    passed = 0
    failed = 0
    errors: list[str] = []
    for sample in samples:
        args = deepcopy(sample.get("input", []))
        expected = deepcopy(sample.get("expected"))
        try:
            with _time_limit(timeout_sec):
                got = func(*args) if isinstance(args, list) else func(args)
        except _Timeout as exc:
            failed += 1
            errors.append(str(exc))
            continue
        except Exception as exc:
            failed += 1
            errors.append(f"runtime error on input {args!r}: {exc!r}")
            continue

        if got != expected:
            failed += 1
            errors.append(f"mismatch on {args!r}: got {got!r}, expected {expected!r}")
        else:
            passed += 1

    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
    }


def evaluate_payload(payload: dict) -> dict:
    task_description = str(payload.get("task_description", ""))
    constraints = payload.get("constraints", {}) or {}
    entry = str(constraints.get("entry_function", ""))
    timeout_sec = float(payload.get("timeout_sec", 1.0))
    buggy_code = str(payload.get("buggy_code", ""))
    repaired_code = str(payload.get("repaired_code", payload.get("code", "")))

    samples, sample_source = select_samples(payload, task_description, entry)
    sample_count = len(samples)

    loc = compute_sloc(repaired_code)
    max_loc = int(constraints.get("max_loc", 500))
    loc_violation = loc > max_loc
    import_violations = find_import_violations(repaired_code, constraints.get("imports_forbidden", []))
    entry_found = bool(entry) and has_entry_function(repaired_code, entry)

    buggy_eval = evaluate_candidate(buggy_code, entry, samples, timeout_sec)
    repaired_eval = evaluate_candidate(repaired_code, entry, samples, timeout_sec)

    buggy_passed = int(buggy_eval["passed"])
    repaired_passed = int(repaired_eval["passed"])
    total_tests = sample_count

    return {
        "buggy_passed": buggy_passed,
        "buggy_failed": int(buggy_eval["failed"]),
        "repaired_passed": repaired_passed,
        "repaired_failed": int(repaired_eval["failed"]),
        "total_tests": total_tests,
        "improved": repaired_passed > buggy_passed,
        "fully_fixed": total_tests > 0 and repaired_passed == total_tests,
        "repair_delta": repaired_passed - buggy_passed,
        "loc": loc,
        "loc_violation": loc_violation,
        "import_violations": import_violations,
        "sample_source": sample_source,
        "sample_count": sample_count,
        "entry_function_found": entry_found,
        "buggy_errors": buggy_eval["errors"],
        "repaired_errors": repaired_eval["errors"],
    }


def main(argv: list[str]) -> int:
    payload, state, info = _load_payload(argv)
    empty = {
        "buggy_passed": 0,
        "buggy_failed": 0,
        "repaired_passed": 0,
        "repaired_failed": 0,
        "total_tests": 0,
        "improved": False,
        "fully_fixed": False,
        "repair_delta": 0,
        "loc": 0,
        "loc_violation": False,
        "import_violations": [],
        "sample_source": "none",
        "sample_count": 0,
        "entry_function_found": False,
        "buggy_errors": [],
        "repaired_errors": [],
    }
    if state == "missing":
        empty["repaired_errors"] = ["usage: evaluate_repair.py '<json>' or pipe JSON to stdin"]
        return _emit(empty)
    if state == "invalid":
        empty["repaired_errors"] = [info]
        return _emit(empty)
    return _emit(evaluate_payload(payload or {}))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
