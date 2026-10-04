#!/usr/bin/env python3
"""bug-hunter skill — file-based result writer."""

from __future__ import annotations

import json
import os
import sys


ALLOWED_VERDICTS = {"buggy", "clean"}
ALLOWED_TYPES = {
    "off_by_one", "null_deref", "type_error", "logic_error",
    "edge_case", "api_misuse", "inefficient", "unhandled_input",
}
ALLOWED_SEVERITIES = {"critical", "high", "medium", "low"}


def _clamp_confidence(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, f))


def resolve_result_path() -> str:
    return os.environ.get("AIASE_RESULT_PATH") or os.path.join(os.getcwd(), "aiase_result.json")


def _sanitize_bug(b: dict) -> dict | None:
    if not isinstance(b, dict):
        return None
    try:
        ls = int(b.get("line_start"))
        le = int(b.get("line_end", ls))
    except (TypeError, ValueError):
        return None
    if ls < 1 or le < ls:
        return None
    sev = str(b.get("severity", "")).strip().lower()
    typ = str(b.get("type", "")).strip().lower()
    if sev not in ALLOWED_SEVERITIES or typ not in ALLOWED_TYPES:
        return None
    return {
        "line_start": ls,
        "line_end": le,
        "severity": sev,
        "type": typ,
        "description": str(b.get("description", "")),
        "suggested_fix": str(b.get("suggested_fix", "")),
    }


def build_contract(obj: dict) -> dict:
    verdict = str(obj.get("verdict", "")).strip().lower()
    if verdict not in ALLOWED_VERDICTS:
        verdict = "clean"

    raw_bugs = obj.get("bugs") or []
    if not isinstance(raw_bugs, list):
        raw_bugs = []
    bugs = [b for b in (_sanitize_bug(x) for x in raw_bugs) if b is not None]

    # 規格:verdict=clean 時 bugs[] 必須是 []。
    if verdict == "clean":
        bugs = []
    # 若有 bugs 卻 verdict=clean 已被擋;反之有 bug 但 verdict=buggy ok。
    if verdict == "buggy" and not bugs:
        # buggy 但沒列任何 bug 是 contract 違規,但我們不自動翻為 clean — 留給評分器扣分。
        pass

    return {
        "task_id": str(obj.get("task_id", "")),
        "verdict": verdict,
        "bugs": bugs,
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
    except (json.JSONDecodeError, ValueError):
        return {
            "task_id": "",
            "verdict": "clean",
            "bugs": [],
            "confidence": 0.0,
        }, "invalid"


def main(argv: list[str]) -> int:
    payload, state = _load_payload(argv)
    if state == "missing":
        return write_contract({"task_id": "", "verdict": "clean", "bugs": [], "confidence": 0.0})
    if state == "invalid":
        return write_contract(payload or {})
    return write_contract(payload)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
