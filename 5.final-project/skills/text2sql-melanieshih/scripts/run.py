#!/usr/bin/env python3
"""text2sql skill — file-based result writer."""

from __future__ import annotations

import json
import os
import sys


CONTRACT_FIELDS = ("task_id", "sql", "rationale", "confidence")


def resolve_result_path() -> str:
    return os.environ.get("AIASE_RESULT_PATH") or os.path.join(os.getcwd(), "aiase_result.json")


def build_contract(obj: dict) -> dict:
    return {
        "task_id": str(obj.get("task_id", "")),
        "sql": str(obj.get("sql", "")).strip(),
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


def _clamp_confidence(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    if f < 0.0:
        return 0.0
    if f > 1.0:
        return 1.0
    return f


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
            "task_id": "",
            "sql": "",
            "rationale": f"invalid {source} JSON: {exc}",
            "confidence": 0.0,
        }, "invalid"


def main(argv: list[str]) -> int:
    payload, state = _load_payload(argv)
    if state == "missing":
        return write_contract({
            "task_id": "",
            "sql": "",
            "rationale": "run.py invoked without argv/stdin payload",
            "confidence": 0.0,
        })
    if state == "invalid":
        return write_contract(payload or {})
    return write_contract(payload)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
