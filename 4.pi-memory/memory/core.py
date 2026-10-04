"""Core memory pipeline: capture, retrieve, inject."""
from __future__ import annotations

import hashlib
import math
import os
import time
from pathlib import Path

from .bm25 import bm25_search
from .hybrid import hybrid_search
from .privacy import sanitize_observation
from .store import JsonStore

_store_path = os.environ.get("PI_MEMORY_PATH") or str(Path.home() / ".pi-memory.json")
_store: JsonStore | None = None


def _get_store() -> JsonStore:
    global _store
    if _store is None:
        _store = JsonStore(_store_path)
    return _store


def set_memory_path(path: str) -> None:
    global _store_path, _store
    _store_path = path
    _store = JsonStore(_store_path)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def make_observation(
    summary: str,
    session_id: str = "s",
    tool_name: str = "remember",
    tags: list[str] | None = None,
) -> dict:
    now_ms = int(time.time() * 1000)
    return {
        "id": sha256(summary),
        "sessionId": session_id,
        "timestamp": now_ms,
        "last_used_at": now_ms,
        "toolName": tool_name,
        "summary": summary,
        "tags": tags or [],
    }


def capture(obs: dict) -> None:
    use_privacy_filter = _bool_env("PI_MEMORY_ENABLE_PRIVACY_FILTER", True)
    payload = sanitize_observation(obs) if use_privacy_filter else dict(obs)
    _get_store().add(payload)


def _build_docs(observations: list[dict]) -> list[dict]:
    docs = []
    for item in observations:
        summary = str(item.get("summary", ""))
        tags = item.get("tags", [])
        tag_text = " ".join(str(tag) for tag in tags)
        docs.append({"id": str(item.get("id", "")), "text": f"{summary} {tag_text}".strip()})
    return docs


def _apply_time_decay(
    ranked_rows: list[dict],
    by_id: dict[str, dict],
    half_life_hours: float,
    floor: float,
) -> list[dict]:
    now_ms = int(time.time() * 1000)
    half_life_ms = max(1.0, half_life_hours * 3600 * 1000)
    rescored: list[dict] = []
    for index, row in enumerate(ranked_rows):
        item = by_id.get(str(row["id"]), {})
        reference_ts = int(item.get("last_used_at") or item.get("timestamp") or now_ms)
        age_ms = max(0, now_ms - reference_ts)
        decay = max(floor, math.exp(-math.log(2) * (age_ms / half_life_ms)))
        rescored.append(
            {
                "id": row["id"],
                "score": float(row["score"]) * float(decay),
                "_index": index,
            }
        )
    rescored.sort(key=lambda entry: (-entry["score"], entry["_index"]))
    return [{"id": row["id"], "score": row["score"]} for row in rescored]


def retrieve(
    query: str,
    k: int,
    *,
    mode: str | None = None,
    apply_decay: bool | None = None,
    alpha: float | None = None,
    candidates: int | None = None,
) -> list[dict]:
    all_obs = _get_store().all()
    if k <= 0 or not all_obs:
        return []

    retrieval_mode = (mode or os.environ.get("PI_MEMORY_RETRIEVAL_MODE", "bm25")).lower()
    docs = _build_docs(all_obs)
    by_id = {str(item.get("id")): item for item in all_obs}

    if retrieval_mode == "hybrid":
        hybrid_alpha = float(alpha if alpha is not None else os.environ.get("PI_MEMORY_HYBRID_ALPHA", 0.6))
        hybrid_candidates = int(
            candidates if candidates is not None else os.environ.get("PI_MEMORY_HYBRID_CANDIDATES", 30)
        )
        model_name = os.environ.get(
            "PI_MEMORY_EMBED_MODEL",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        )
        device = os.environ.get("PI_MEMORY_EMBED_DEVICE", "cpu")
        ranked = hybrid_search(
            query,
            docs,
            k=k,
            alpha=hybrid_alpha,
            candidates=hybrid_candidates,
            model_name=model_name,
            device=device,
        )
    else:
        ranked = bm25_search(query, docs, k)

    use_decay = _bool_env("PI_MEMORY_ENABLE_DECAY", False) if apply_decay is None else apply_decay
    if use_decay and ranked:
        half_life_hours = float(os.environ.get("PI_MEMORY_DECAY_HALF_LIFE_HOURS", 168))
        decay_floor = float(os.environ.get("PI_MEMORY_DECAY_FLOOR", 0.2))
        ranked = _apply_time_decay(ranked, by_id, half_life_hours=half_life_hours, floor=decay_floor)

    final_ranked = ranked[: min(k, len(ranked))]
    memory_ids = [str(row["id"]) for row in final_ranked]
    _get_store().update_last_used(memory_ids, int(time.time() * 1000))
    return [by_id[row["id"]] for row in final_ranked if row["id"] in by_id]


def forget(memory_id: str) -> bool:
    return _get_store().delete_by_id(memory_id)


def list_memories(limit: int = 20) -> list[dict]:
    items = _get_store().all()
    return items[: max(0, limit)]


def build_injection(
    query: str,
    token_budget: int = 2000,
    k: int = 8,
    *,
    mode: str | None = None,
    apply_decay: bool | None = None,
) -> str:
    hits = retrieve(query, k, mode=mode, apply_decay=apply_decay)
    header = "[記憶 - relevant notes from previous sessions]"
    lines, used = [], estimate_tokens(header)
    for item in hits:
        line = f"- {item.get('summary', '')}"
        cost = estimate_tokens(line)
        if used + cost > token_budget:
            break
        lines.append(line)
        used += cost
    return "\n".join([header, *lines]) if lines else ""
