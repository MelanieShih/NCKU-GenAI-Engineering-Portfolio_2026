"""BM25-lite：給每筆文件對查詢打相關度分數，回傳排序後的前 K 筆。整個作業的核心。
tokenize() 已給你；bm25_search() 的計分要你填。"""
from __future__ import annotations
import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    """小寫化後，取出英數字詞與單個 CJK 字元。不做 stemming。（已提供）"""
    return _TOKEN_RE.findall(text.lower())


def bm25_search(
    query: str,
    docs: list[dict],
    k: int = 8,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[dict]:
    """
    TODO（主戰場）：實作標準 BM25 排序。
    docs = [{"id": str, "text": str}, ...]；回傳 [{"id", "score"}, ...]（高到低，前 k 筆）。

      score(q,d) = Σ_qi IDF(qi) * (tf*(k1+1)) / (tf + k1*(1 - b + b*|d|/avgdl))
      IDF(qi)    = ln( (N - n + 0.5)/(n + 0.5) + 1 )
      tf = qi 在 d 出現次數 | |d| = d 詞數 | avgdl = 平均詞數 | N = 文件數 | n = 含 qi 的文件數

    步驟：
      1) 用 tokenize() 斷詞，記每篇長度，算 avgdl
      2) 算每個詞的 document frequency（df）
      3) 對每篇文件，加總查詢每個詞的 BM25 貢獻
      4) 依分數高到低排序（同分保持原始順序），回傳前 k 筆

    建議先用 tests/ 裡的 pnpm 三筆範例手動驗證（D1/D3 應勝 D2），再接 Pi / 跑 benchmark。
    """
    if k <= 0 or not docs:
        return []

    query_tokens = tokenize(query or "")

    tokenized_docs: list[list[str]] = []
    doc_lengths: list[int] = []
    document_frequencies: Counter[str] = Counter()

    for doc in docs:
        text = str(doc.get("text") or doc.get("summary") or "")
        tokens = tokenize(text)
        tokenized_docs.append(tokens)
        doc_lengths.append(len(tokens))
        for token in set(tokens):
            document_frequencies[token] += 1

    total_docs = len(docs)
    avgdl = sum(doc_lengths) / total_docs if total_docs > 0 else 0.0

    scored: list[dict] = []

    for index, (doc, tokens, doc_length) in enumerate(zip(docs, tokenized_docs, doc_lengths)):
        term_frequencies = Counter(tokens)
        score = 0.0

        for term in query_tokens:
            tf = term_frequencies.get(term, 0)
            if tf == 0:
                continue

            df = document_frequencies.get(term, 0)
            idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1.0)
            length_norm = 1.0 - b + b * (doc_length / avgdl) if avgdl > 0 else 1.0
            denominator = tf + k1 * length_norm
            score += idf * (tf * (k1 + 1.0)) / denominator

        scored.append({
            "id": doc.get("id"),
            "score": float(score),
            "_order": index,
        })

    scored.sort(key=lambda item: (-item["score"], item["_order"]))

    return [
        {"id": item["id"], "score": item["score"]}
        for item in scored[:k]
    ]
