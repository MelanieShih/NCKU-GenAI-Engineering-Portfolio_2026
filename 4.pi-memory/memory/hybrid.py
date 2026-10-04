"""Hybrid retrieval: BM25 candidate recall + embedding re-ranking."""
from __future__ import annotations

from dataclasses import dataclass

from .bm25 import bm25_search


@dataclass
class HybridConfig:
    alpha: float = 0.6
    candidates: int = 30
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    device: str = "cpu"


class _Embedder:
    def __init__(self, model_name: str, device: str = "cpu"):
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Hybrid retrieval requires sentence-transformers. "
                "Install with: pip install sentence-transformers"
            ) from exc
        self.model = SentenceTransformer(model_name, device=device)
        self._cache: dict[str, list[float]] = {}

    def encode(self, text: str) -> list[float]:
        if text in self._cache:
            return self._cache[text]
        embedding = self.model.encode(text, normalize_embeddings=True, show_progress_bar=False)
        vector = embedding.tolist()
        self._cache[text] = vector
        return vector


_EMBEDDER_CACHE: dict[tuple[str, str], _Embedder] = {}


def _get_embedder(model_name: str, device: str) -> _Embedder:
    key = (model_name, device)
    if key not in _EMBEDDER_CACHE:
        _EMBEDDER_CACHE[key] = _Embedder(model_name=model_name, device=device)
    return _EMBEDDER_CACHE[key]


def _dot(vec_a: list[float], vec_b: list[float]) -> float:
    return float(sum(a * b for a, b in zip(vec_a, vec_b)))


def _min_max_normalize(scores: list[float]) -> list[float]:
    if not scores:
        return []
    min_score = min(scores)
    max_score = max(scores)
    if max_score == min_score:
        return [0.0 for _ in scores]
    return [(score - min_score) / (max_score - min_score) for score in scores]


def hybrid_search(
    query: str,
    docs: list[dict],
    k: int = 8,
    *,
    alpha: float = 0.6,
    candidates: int = 30,
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    device: str = "cpu",
) -> list[dict]:
    if k <= 0 or not docs:
        return []

    candidate_size = min(max(candidates, k), len(docs))
    bm25_ranked = bm25_search(query, docs, candidate_size)
    bm25_by_id = {row["id"]: row["score"] for row in bm25_ranked}

    candidate_docs = []
    for index, doc in enumerate(docs):
        doc_id = str(doc.get("id", index))
        if doc_id in bm25_by_id:
            candidate_docs.append((index, doc))

    if not candidate_docs:
        candidate_docs = list(enumerate(docs))

    embedder = _get_embedder(model_name=model_name, device=device)
    query_vec = embedder.encode(query or "")

    raw_rows = []
    for index, doc in candidate_docs:
        doc_id = str(doc.get("id", index))
        doc_text = str(doc.get("text", ""))
        if not doc_text and doc.get("summary") is not None:
            doc_text = str(doc.get("summary"))
        doc_vec = embedder.encode(doc_text)
        embed_score = _dot(query_vec, doc_vec)
        bm25_score = float(bm25_by_id.get(doc_id, 0.0))
        raw_rows.append((doc_id, index, bm25_score, embed_score))

    bm25_norm = _min_max_normalize([row[2] for row in raw_rows])
    embed_norm = _min_max_normalize([row[3] for row in raw_rows])

    merged = []
    for i, row in enumerate(raw_rows):
        doc_id, index, _, _ = row
        final_score = alpha * bm25_norm[i] + (1.0 - alpha) * embed_norm[i]
        merged.append({"id": doc_id, "score": float(final_score), "_index": index})

    merged.sort(key=lambda item: (-item["score"], item["_index"]))
    topk = merged[: min(k, len(merged))]
    return [{"id": row["id"], "score": row["score"]} for row in topk]
