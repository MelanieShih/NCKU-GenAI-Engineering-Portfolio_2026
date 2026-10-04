#!/usr/bin/env python3
"""code-author skill — file-based result writer."""

from __future__ import annotations

import json
import os
import sys

from selftest import (
    compute_sloc,
    find_import_violations,
    has_entry_function,
    run_sample,
    select_samples,
)


def _clamp_confidence(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, f))


def resolve_result_path() -> str:
    return os.environ.get("AIASE_RESULT_PATH") or os.path.join(os.getcwd(), "aiase_result.json")


def _maybe_compute_self_test(obj: dict) -> tuple[dict, int]:
    existing = obj.get("self_test_results")
    existing_loc = obj.get("loc")
    if isinstance(existing, dict) and existing:
        existing.setdefault("passed", 0)
        existing.setdefault("failed", 0)
        loc = int(existing_loc) if str(existing_loc).lstrip("-").isdigit() else 0
        return existing, loc

    code = str(obj.get("code", ""))
    task_description = str(obj.get("task_description", ""))
    constraints = obj.get("constraints", {}) or {}
    entry = str(constraints.get("entry_function", ""))
    timeout_sec = float(obj.get("timeout_sec", 1.0))

    sloc = compute_sloc(code)
    loc_violation = sloc > int(constraints.get("max_loc", 500))
    import_violations = find_import_violations(code, constraints.get("imports_forbidden", []))
    samples, sample_source = select_samples(obj, task_description, entry)

    passed = 0
    failed = 0
    errors: list[str] = []

    if not entry:
        errors.append("constraints.entry_function not provided")
    elif not has_entry_function(code, entry):
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

    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "sloc": sloc,
        "loc_violation": loc_violation,
        "import_violations": import_violations,
        "sample_source": sample_source,
    }, sloc


def build_contract(obj: dict) -> dict:
    self_test, measured_loc = _maybe_compute_self_test(obj)
    if not isinstance(self_test, dict):
        self_test = {"passed": 0, "failed": 0, "_warning": "non-object coerced"}
    self_test.setdefault("passed", 0)
    self_test.setdefault("failed", 0)

    return {
        "task_id": str(obj.get("task_id", "")),
        "code": str(obj.get("code", "")),
        "loc": int(obj.get("loc", measured_loc)) if str(obj.get("loc", measured_loc)).lstrip("-").isdigit() else measured_loc,
        "self_test_results": self_test,
        "rationale": str(obj.get("rationale", "")),
        "confidence": _clamp_confidence(obj.get("confidence", 0.5)),
    }


def write_contract(obj: dict) -> int:
    out = build_contract(obj)
    path = resolve_result_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False)
    os.replace(tmp, path)
    print(f"written ok -> {path}")
    return 0


def _load_payload(argv: list[str]) -> tuple[dict | None, str]:
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
        return None, "missing"
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("payload not an object")
        return payload, source
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "task_id": "", "code": "", "loc": 0,
            "self_test_results": {"passed": 0, "failed": 0},
            "rationale": f"invalid {source} JSON: {exc}",
            "confidence": 0.0,
        }, "invalid"


def main(argv: list[str]) -> int:
    payload, state = _load_payload(argv)
    if state == "missing":
        return write_contract({
            "task_id": "", "code": "", "loc": 0,
            "self_test_results": {"passed": 0, "failed": 0},
            "rationale": "run.py invoked without argv/stdin payload",
            "confidence": 0.0,
        })
    if state == "invalid":
        return write_contract(payload or {})
    return write_contract(payload)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
