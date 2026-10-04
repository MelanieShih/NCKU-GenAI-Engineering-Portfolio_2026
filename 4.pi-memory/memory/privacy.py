"""Privacy filter helpers for memory observations."""
from __future__ import annotations

import re

_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"), "[REDACTED_OPENAI_KEY]"),
    ("github_token", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (
        "password_assignment",
        re.compile(r"(?i)\b(password|passwd|pwd)\s*[:=]\s*[^\s,;]+"),
        r"\1=[REDACTED_PASSWORD]",
    ),
    (
        "api_key_assignment",
        re.compile(r"(?i)\b(api[_-]?key|token)\s*[:=]\s*[^\s,;]+"),
        r"\1=[REDACTED_SECRET]",
    ),
    (
        "bearer_token",
        re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}"),
        "Bearer [REDACTED_TOKEN]",
    ),
]


def redact_text(text: str) -> tuple[str, int, list[str]]:
    redacted = text
    redaction_count = 0
    matched_types: list[str] = []
    for pattern_name, pattern, replacement in _PATTERNS:
        redacted, matches = pattern.subn(replacement, redacted)
        if matches > 0:
            redaction_count += matches
            matched_types.append(pattern_name)
    return redacted, redaction_count, matched_types


def sanitize_observation(obs: dict) -> dict:
    sanitized = dict(obs)
    summary = str(sanitized.get("summary", ""))
    redacted_summary, count, matched_types = redact_text(summary)
    sanitized["summary"] = redacted_summary
    sanitized["sanitized"] = bool(count)
    sanitized["redaction_count"] = count
    sanitized["redaction_types"] = matched_types
    return sanitized
