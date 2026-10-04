"""JSON-backed memory store used by capture/retrieve."""
from __future__ import annotations

import hashlib
import json
import os


class JsonStore:
    def __init__(self, path: str):
        self.path = path
        self.items: list[dict] = []
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.path):
            self.items = []
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.items = data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            self.items = []

    def _persist(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)

    def add(self, obs: dict) -> bool:
        summary = str(obs.get("summary", ""))
        summary_hash = hashlib.sha256(summary.encode("utf-8")).hexdigest()
        if any(
            hashlib.sha256(str(item.get("summary", "")).encode("utf-8")).hexdigest() == summary_hash
            for item in self.items
        ):
            return False
        new_obs = dict(obs)
        if not new_obs.get("id"):
            new_obs["id"] = summary_hash
        self.items.append(new_obs)
        self._persist()
        return True

    def delete_by_id(self, memory_id: str) -> bool:
        before = len(self.items)
        self.items = [item for item in self.items if str(item.get("id")) != str(memory_id)]
        changed = len(self.items) != before
        if changed:
            self._persist()
        return changed

    def update_last_used(self, memory_ids: list[str], used_at_ms: int) -> int:
        if not memory_ids:
            return 0
        id_set = {str(memory_id) for memory_id in memory_ids}
        changed = 0
        for item in self.items:
            if str(item.get("id")) in id_set:
                if item.get("last_used_at") != used_at_ms:
                    item["last_used_at"] = used_at_ms
                    changed += 1
        if changed:
            self._persist()
        return changed

    def all(self) -> list[dict]:
        return list(self.items)

    def clear(self) -> None:
        self.items = []
        self._persist()



