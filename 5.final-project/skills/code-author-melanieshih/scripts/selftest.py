#!/usr/bin/env python3
"""
code-author self-test harness.

Usage:
    python selftest.py '{
        "code": "def merge_intervals(intervals): ...",
        "task_description": "Implement merge_intervals(intervals): ...",
        "constraints": {"entry_function": "merge_intervals", "max_loc": 500,
                        "imports_forbidden": ["os","sys"]},
        "sample_inputs": [
            {"input": [[[1,3],[2,4]]], "expected": [[1,4]]},
            {"input": [[]],            "expected": []}
        ]
    }'

or:

    cat payload.json | python selftest.py

Prints a single fenced JSON block:
    {"passed": int, "failed": int, "errors": [str],
     "sloc": int, "loc_violation": bool,
     "import_violations": [str], "sample_source": str,
     "sample_count": int, "entry_function_found": bool}

Deterministic. No network. Uses `radon raw` for SLOC when available.
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
    """Return SLOC via `radon raw --json`; fallback to non-empty non-comment lines."""
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
    """Parse imports via AST and return the forbidden ones that appear."""
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

    if "reverse_words" in text or ("space-separated words" in text):
        return [
            {"input": [""], "expected": ""},
            {"input": ["hello world"], "expected": "world hello"},
            {"input": ["  a   b  "], "expected": "b a"},
            {"input": ["x"], "expected": "x"},
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


def run_sample(code: str, entry: str, sample: dict, timeout_sec: float) -> tuple[bool, str]:
    namespace: dict = {}
    try:
        exec(compile(code, "<candidate>", "exec"), namespace)
    except Exception as exc:
        return False, f"compile/exec error: {exc!r}"

    func = namespace.get(entry)
    if not callable(func):
        return False, f"entry function {entry!r} not defined"

    args = deepcopy(sample.get("input", []))
    expected = deepcopy(sample.get("expected"))

    try:
        with _time_limit(timeout_sec):
            got = func(*args) if isinstance(args, list) else func(args)
    except _Timeout as exc:
        return False, str(exc)
    except Exception as exc:
        return False, f"runtime error on input {args!r}: {exc!r}"

    if got != expected:
        return False, f"mismatch on {args!r}: got {got!r}, expected {expected!r}"
    return True, ""


def main(argv: list[str]) -> int:
    empty = {
        "passed": 0,
        "failed": 0,
        "errors": [],
        "sloc": 0,
        "loc_violation": False,
        "import_violations": [],
        "sample_source": "none",
        "sample_count": 0,
        "entry_function_found": False,
    }

    payload, state, info = _load_payload(argv)
    if state == "missing":
        empty["errors"] = ["usage: selftest.py '<json>' or pipe JSON to stdin"]
        return _emit(empty)
    if state == "invalid":
        empty["errors"] = [info]
        return _emit(empty)

    code = str(payload.get("code", ""))
    task_description = str(payload.get("task_description", ""))
    constraints = payload.get("constraints", {}) or {}
    entry = str(constraints.get("entry_function", ""))
    timeout_sec = float(payload.get("timeout_sec", 1.0))

    sloc = compute_sloc(code)
    max_loc = int(constraints.get("max_loc", 500))
    loc_violation = sloc > max_loc
    import_violations = find_import_violations(code, constraints.get("imports_forbidden", []))

    samples, sample_source = select_samples(payload, task_description, entry)
    entry_found = bool(entry) and has_entry_function(code, entry)

    passed = 0
    failed = 0
    errors: list[str] = []

    if not entry:
        errors.append("constraints.entry_function not provided")
    elif not entry_found:
        errors.append(f"entry function {entry!r} not found in candidate code")

    if not samples:
        errors.append("no sample_inputs provided or derived")

    if not errors:
        for sample in samples:
            ok, err = run_sample(code, entry, sample, timeout_sec)
            if ok:
                passed += 1
            else:
                failed += 1
                errors.append(err)

    return _emit(
        {
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "sloc": sloc,
            "loc_violation": loc_violation,
            "import_violations": import_violations,
            "sample_source": sample_source,
            "sample_count": len(samples),
            "entry_function_found": entry_found,
        }
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv))
