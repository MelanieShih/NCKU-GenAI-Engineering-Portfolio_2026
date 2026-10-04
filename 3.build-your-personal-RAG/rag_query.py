import argparse
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from dotenv import load_dotenv
import psycopg2
from pgvector.psycopg2 import register_vector
from huggingface_hub import InferenceClient

try:
    import cohere  # type: ignore
except Exception:
    cohere = None

try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None


TABLE_DEFAULT = "rag_chunks"
EMBEDDING_MODEL_DEFAULT = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K_DEFAULT = 5
FETCH_K_DEFAULT = 20
HISTORY_TURNS_DEFAULT = 3


@dataclass
class Hit:
    source_file: str
    source_type: str
    chunk_index: int
    section_path: Optional[str]
    content: str
    distance: float


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing {name} in environment.")
    return value


def connect_db() -> psycopg2.extensions.connection:
    conn_str = require_env("PGVECTOR_CONNECTION_STRING")
    conn = psycopg2.connect(conn_str)
    register_vector(conn)
    return conn


def ensure_table_name_safe(name: str) -> str:
    if not re.match(r"^[A-Za-z0-9_]+$", name):
        raise ValueError(f"Unsafe table name: {name}")
    return name


def embed_query_hf(
    text: str,
    model: str,
    rate_limit_seconds: float,
    max_retries: int,
) -> List[float]:
    token = require_env("HF_API_KEY")
    client = InferenceClient(token=token)

    attempt = 0
    while True:
        try:
            emb = client.feature_extraction([text], model=model)
            break
        except Exception as e:
            attempt += 1
            if attempt > max_retries:
                raise e
            time.sleep(rate_limit_seconds * attempt)

    if hasattr(emb, "tolist"):
        emb = emb.tolist()
    if isinstance(emb, list) and emb and isinstance(emb[0], list):
        return emb[0]
    if isinstance(emb, list) and emb and isinstance(emb[0], (int, float)):
        return emb
    raise RuntimeError("Unexpected embedding output format from HF API.")


_LOCAL_QUERY_MODEL_CACHE: Dict[str, "SentenceTransformer"] = {}


def embed_query_local(text: str, model: str) -> List[float]:
    from sentence_transformers import SentenceTransformer
    if model not in _LOCAL_QUERY_MODEL_CACHE:
        _LOCAL_QUERY_MODEL_CACHE[model] = SentenceTransformer(model)
    local_model = _LOCAL_QUERY_MODEL_CACHE[model]
    emb = local_model.encode([text])
    if hasattr(emb, "tolist"):
        emb = emb.tolist()
    if isinstance(emb, list) and emb and isinstance(emb[0], list):
        return emb[0]
    if isinstance(emb, list) and emb and isinstance(emb[0], (int, float)):
        return emb
    raise RuntimeError("Unexpected embedding output format from sentence-transformers.")


def build_filters(
    source_prefix: Optional[str],
    source_type: Optional[str],
    section_contains: Optional[str],
) -> Tuple[str, List[Any]]:
    clauses: List[str] = []
    params: List[Any] = []

    if source_prefix:
        normalized = source_prefix.replace("\\", "/")
        clauses.append("source_file LIKE %s")
        params.append(f"{normalized}%")
    if source_type:
        clauses.append("source_type = %s")
        params.append(source_type)
    if section_contains:
        clauses.append("section_path ILIKE %s")
        params.append(f"%{section_contains}%")

    if clauses:
        return "WHERE " + " AND ".join(clauses), params
    return "", params


def fetch_candidates(
    conn: psycopg2.extensions.connection,
    table: str,
    query_vec: List[float],
    fetch_k: int,
    source_prefix: Optional[str],
    source_type: Optional[str],
    section_contains: Optional[str],
) -> List[Hit]:
    where_sql, filter_params = build_filters(source_prefix, source_type, section_contains)
    sql = f"""
        SELECT source_file, source_type, chunk_index, section_path, content,
               embedding <-> %s::vector AS distance
        FROM {table}
        {where_sql}
        ORDER BY embedding <-> %s::vector
        LIMIT %s;
    """
    params: List[Any] = [query_vec] + filter_params + [query_vec, fetch_k]

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    hits: List[Hit] = []
    for row in rows:
        hits.append(
            Hit(
                source_file=row[0],
                source_type=row[1],
                chunk_index=row[2],
                section_path=row[3],
                content=row[4],
                distance=float(row[5]),
            )
        )
    return hits


def rerank_hits(
    query: str,
    hits: List[Hit],
    top_k: int,
    model: str,
) -> List[Hit]:
    if not hits:
        return hits
    if cohere is None:
        print("Warning: cohere not installed, skipping rerank.")
        return hits[:top_k]
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        print("Warning: COHERE_API_KEY missing, skipping rerank.")
        return hits[:top_k]

    client = cohere.Client(api_key)
    documents = [h.content for h in hits]
    result = client.rerank(
        model=model,
        query=query,
        documents=documents,
        top_n=min(top_k, len(documents)),
    )
    index_order = [r.index for r in result.results]
    return [hits[i] for i in index_order]


def format_sources(hits: Sequence[Hit]) -> str:
    lines = []
    for idx, h in enumerate(hits, start=1):
        section = f" | section: {h.section_path}" if h.section_path else ""
        lines.append(f"[{idx}] {h.source_file} | chunk {h.chunk_index}{section}")
    return "\n".join(lines)


def build_user_prompt(query: str, hits: Sequence[Hit]) -> str:
    context_blocks = []
    for idx, h in enumerate(hits, start=1):
        context_blocks.append(f"[{idx}] {h.content}")
    context_text = "\n\n".join(context_blocks)
    return (
        "請根據以下參考內容回答問題，並在答案中使用 [編號] 引用來源。\n"
        "若資料不足，請誠實回答不知道，不要臆測。\n\n"
        f"問題：{query}\n\n"
        "參考內容：\n"
        f"{context_text}"
    )


def call_llm(model: str, messages: List[Dict[str, str]]) -> str:
    api_key = os.getenv("LITELLM_API_KEY")
    api_base = os.getenv("LITELLM_BASE_URL")
    if not api_key or not api_base:
        raise RuntimeError("Missing LITELLM_API_KEY or LITELLM_BASE_URL in environment.")

    if OpenAI is None:
        raise RuntimeError("openai is not installed. Please add openai to requirements.")

    client = OpenAI(api_key=api_key, base_url=api_base)
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content


def interactive_loop(args: argparse.Namespace) -> None:
    history: List[Dict[str, str]] = []
    print("Interactive mode. Type 'exit' or 'quit' to leave.")
    while True:
        user_input = input("\nYou: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break
        if user_input.startswith("/"):
            handle_command(user_input, args)
            continue

        answer, hits = handle_query(user_input, args, history)
        print("\nAssistant:\n" + answer)
        if hits:
            print("\nSources:\n" + format_sources(hits))


def handle_query(
    query: str,
    args: argparse.Namespace,
    history: Optional[List[Dict[str, str]]] = None,
) -> Tuple[str, List[Hit]]:
    if args.embedding_provider == "huggingface":
        query_vec = embed_query_hf(
            query,
            args.embedding_model,
            rate_limit_seconds=args.rate_limit,
            max_retries=args.max_retries,
        )
    else:
        query_vec = embed_query_local(query, args.embedding_model)
    table = ensure_table_name_safe(args.table)
    conn = connect_db()
    try:
        candidates = fetch_candidates(
            conn,
            table=table,
            query_vec=query_vec,
            fetch_k=args.fetch_k,
            source_prefix=args.source_prefix,
            source_type=args.source_type,
            section_contains=args.section_contains,
        )
    finally:
        conn.close()

    if args.rerank:
        hits = rerank_hits(query, candidates, args.top_k, args.rerank_model)
    else:
        hits = candidates[: args.top_k]

    if args.show_context:
        print("\nRetrieved Context:\n" + format_sources(hits))

    system_prompt = (
        "你是 Oura Ring 4 智慧戒指的健康穿戴裝置顧問。"
        "你的任務是根據提供的參考內容回答使用者問題，範圍僅限於 Oura Ring 4 的功能、使用支援、規格與使用者評價等內容。"
        "你只能使用參考內容中的資訊，禁止使用外部知識、禁止臆測、禁止自行補充。"
        "若參考內容未直接包含答案，請回答「資料不足」，並簡要說明缺少哪類資訊。"
        "作答時必須清楚、精簡，並以條列呈現明確的規格/功能/步驟。"
        "作答要求："
        "- 所有結論都必須附上來源引用 [編號]"
        "- 沒有來源支撐的內容不得出現"
        "- 問規格題時，只回答參考內容中明確出現的規格"
        "- 問功能題時，只列出文本明確提到的功能或可測量項目"
        "- 問使用支援題時，整理實際可操作的步驟或建議"
        "- 問評價題時，整理正面與負面回饋，不下主觀定論"
        "回答格式固定如下："
        "答案："
        "- 條列 2–5 點（只寫來源中明確內容）"
        "來源："
        "[1] ..."
    )
    user_prompt = build_user_prompt(query, hits)

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if history:
        keep = max(0, args.history_turns * 2)
        messages.extend(history[-keep:])
    messages.append({"role": "user", "content": user_prompt})

    answer = call_llm(args.model, messages)

    if history is not None:
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": answer})

    return answer, hits


def main() -> None:
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="RAG Query CLI with pgvector + LiteLLM")
    parser.add_argument("--query", type=str, default=None, help="Single query mode.")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", help="LLM model name.")
    parser.add_argument("--table", type=str, default=TABLE_DEFAULT, help="pgvector table name.")
    parser.add_argument("--embedding-model", type=str, default=EMBEDDING_MODEL_DEFAULT, help="HF embedding model.")
    parser.add_argument(
        "--embedding-provider",
        type=str,
        default=os.getenv("EMBEDDING_PROVIDER", "sentence-transformers"),
        help="Embedding provider: sentence-transformers or huggingface.",
    )
    parser.add_argument("--top-k", type=int, default=TOP_K_DEFAULT, help="Top-k chunks to use.")
    parser.add_argument("--fetch-k", type=int, default=FETCH_K_DEFAULT, help="Initial candidates to fetch.")
    parser.add_argument("--rerank", action="store_true", help="Enable Cohere reranking.")
    parser.add_argument("--rerank-model", type=str, default="rerank-multilingual-v3.0", help="Cohere rerank model.")
    parser.add_argument("--source-prefix", type=str, default=None, help="Filter by source_file prefix.")
    parser.add_argument("--source-type", type=str, default=None, help="Filter by source_type (md/txt).")
    parser.add_argument("--section-contains", type=str, default=None, help="Filter by section path keyword.")
    parser.add_argument("--show-context", action="store_true", help="Print retrieved sources.")
    parser.add_argument("--history-turns", type=int, default=HISTORY_TURNS_DEFAULT, help="Number of turns to keep.")
    parser.add_argument("--rate-limit", type=float, default=0.5, help="HF API rate limit seconds.")
    parser.add_argument("--max-retries", type=int, default=3, help="HF API max retries.")
    args = parser.parse_args()

    if args.query:
        answer, hits = handle_query(args.query, args, history=None)
        print("\nAnswer:\n" + answer)
        if hits:
            print("\nSources:\n" + format_sources(hits))
        return

    interactive_loop(args)


def handle_command(command: str, args: argparse.Namespace) -> None:
    parts = command.strip().split()
    name = parts[0].lower()

    if name in {"/help", "/?"}:
        print(
            "Commands:\n"
            "/rerank on|off\n"
            "/filter prefix <text>\n"
            "/filter type <md|txt>\n"
            "/filter section <keyword>\n"
            "/filter clear\n"
            "/topk <number>\n"
            "/fetchk <number>\n"
            "/showcontext on|off\n"
        )
        return

    if name == "/rerank" and len(parts) >= 2:
        args.rerank = parts[1].lower() == "on"
        print(f"rerank = {args.rerank}")
        return

    if name == "/showcontext" and len(parts) >= 2:
        args.show_context = parts[1].lower() == "on"
        print(f"show_context = {args.show_context}")
        return

    if name == "/topk" and len(parts) >= 2 and parts[1].isdigit():
        args.top_k = int(parts[1])
        print(f"top_k = {args.top_k}")
        return

    if name == "/fetchk" and len(parts) >= 2 and parts[1].isdigit():
        args.fetch_k = int(parts[1])
        print(f"fetch_k = {args.fetch_k}")
        return

    if name == "/filter" and len(parts) >= 2:
        sub = parts[1].lower()
        if sub == "clear":
            args.source_prefix = None
            args.source_type = None
            args.section_contains = None
            print("filters cleared")
            return
        if sub == "prefix" and len(parts) >= 3:
            args.source_prefix = " ".join(parts[2:])
            print(f"source_prefix = {args.source_prefix}")
            return
        if sub == "type" and len(parts) >= 3:
            args.source_type = parts[2]
            print(f"source_type = {args.source_type}")
            return
        if sub == "section" and len(parts) >= 3:
            args.section_contains = " ".join(parts[2:])
            print(f"section_contains = {args.section_contains}")
            return

    print("Unknown command. Type /help for options.")


if __name__ == "__main__":
    main()
