#!/usr/bin/env python3
"""open-code-repair skill — file-based result writer."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from evaluate_repair import evaluate_payload  # noqa: E402


def _clamp_confidence(value) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, score))


def resolve_result_path() -> str:
    return os.environ.get("AIASE_RESULT_PATH") or os.path.join(os.getcwd(), "aiase_result.json")


def _write(obj: dict) -> int:
    path = resolve_result_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(obj, handle, ensure_ascii=False)
    os.replace(tmp, path)
    print("```json")
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    print("```")
    print(f"written ok -> {path}")
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


def emit_contract(payload: dict) -> int:
    repaired_code = str(payload.get("repaired_code", payload.get("code", "")))
    out = {
        "task_id": str(payload.get("task_id", "")),
        "repaired_code": repaired_code,
        "repair_summary": str(payload.get("repair_summary", "")),
        "confidence": _clamp_confidence(payload.get("confidence", 0.5)),
        "repair_evaluation": evaluate_payload(payload),
    }
    return _write(out)


def main(argv: list[str]) -> int:
    payload, state, info = _load_payload(argv)
    if state == "missing":
        return emit_contract({
            "task_id": "",
            "repaired_code": "",
            "repair_summary": "run.py invoked without argv/stdin payload",
            "confidence": 0.0,
            "task_description": "",
            "buggy_code": "",
            "constraints": {},
        })
    if state == "invalid":
        return emit_contract({
            "task_id": "",
            "repaired_code": "",
            "repair_summary": info,
            "confidence": 0.0,
            "task_description": "",
            "buggy_code": "",
            "constraints": {},
        })
    return emit_contract(payload or {})


if __name__ == "__main__":
    sys.exit(main(sys.argv))
