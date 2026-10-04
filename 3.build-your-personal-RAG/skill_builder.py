import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from dotenv import load_dotenv
import psycopg2

try:
    from openai import OpenAI  # type: ignore
except Exception:
    OpenAI = None

import rag_query as rq


TABLE_DEFAULT = "rag_chunks"
EMBEDDING_MODEL_DEFAULT = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


DEFAULT_QUESTIONS = [
    ("這個知識庫涵蓋了哪些關於 Oura Ring 的核心主題與內容分類（如規格、支援、評價）？", None),
    ("若要向新使用者介紹 Oura Ring 的核心定位與優勢，最重要的重點是什麼？", None),
    ("Oura Ring 4 在工業設計、材質工藝及配件（如充電器、測量套組）上有哪些特色？", "產品規格_功能/"),
    ("Oura Ring 4 的核心感測能力為何？它如何透過 Smart Sensing 技術提升測量準確度？", "產品規格_功能/"),
    ("主要監測指標（如準備度、睡眠、活動、壓力）涵蓋哪些生理數據？它們如何協助使用者了解自身狀態？", "產品規格_功能/"),
    ("在特殊健康領域（如女性健康、心臟健康、代謝追蹤）提供了哪些洞察功能？", "產品規格_功能/"),
    ("在 App 操作、設備同步、配戴習慣與充電維護上，有哪些關鍵的建議與注意事項？", "使用支援/"),
    ("根據使用者評價，Oura Ring 的主要優點、潛在缺點，以及它與智慧手錶在功能定位上的差異為何？", "評價體驗/"),
    ("知識庫中提及了哪些核心名詞、功能模組或專屬分數（如 Oura Membership, Resilience）？", None),
    ("根據現有資訊，Oura Ring 在軟硬體設計、使用環境、特定運動或數據解讀上有哪些明確的限制或提醒？", None),
]


@dataclass
class QAItem:
    question: str
    answer: str
    sources: List[str]


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing {name} in environment.")
    return value


def connect_db() -> psycopg2.extensions.connection:
    conn_str = require_env("PGVECTOR_CONNECTION_STRING")
    return psycopg2.connect(conn_str)


def get_source_list(conn: psycopg2.extensions.connection, table: str) -> List[str]:
    with conn.cursor() as cur:
        cur.execute(f"SELECT DISTINCT source_file FROM {table} ORDER BY source_file;")
        return [row[0] for row in cur.fetchall()]


def call_llm(model: str, messages: List[dict]) -> str:
    if OpenAI is None:
        raise RuntimeError("openai is not installed. Please add openai to requirements.")
    api_key = require_env("LITELLM_API_KEY")
    api_base = require_env("LITELLM_BASE_URL")
    client = OpenAI(api_key=api_key, base_url=api_base)
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content


def load_sources_metadata(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_sources_block(sources: List[str], metadata: dict) -> str:
    lines = []
    for idx, src in enumerate(sources, start=1):
        meta = metadata.get(src, {})
        src_type = meta.get("type", "未提供")
        src_date = meta.get("date", "未提供")
        lines.append(f"- {idx}. {src} | 類型：{src_type} | 日期：{src_date}")
    return "\n".join(lines)


def build_qa_block(items: List[QAItem]) -> str:
    blocks: List[str] = []
    for i, item in enumerate(items, start=1):
        sources = "；".join(item.sources) if item.sources else "（無）"
        blocks.append(f"Q{i}: {item.question}\nA{i}: {item.answer}\nSources: {sources}")
    return "\n\n".join(blocks)


def synthesize_skill_md(
    topic: str,
    source_list: List[str],
    qa_items: List[QAItem],
    model: str,
    metadata: dict,
) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    sources_block = build_sources_block(source_list, metadata)
    qa_block = build_qa_block(qa_items)

    system_prompt = (
    "你是一位嚴謹且具備洞察力的知識庫彙整專家。"
    "你的任務是根據提供的 Q&A 結果，自動產生一份結構完整且具專業感的 skill.md。"
    
    "【核心原則】"
    "1. 資訊提煉：僅使用 Q&A 中出現的資訊。若某些功能的具體演算法或技術數值未詳述，請專注於描述該功能的『目的』、『監測面向』與『對使用者的價值』，避免在文中反覆強調資料不足。"
    "2. 整合與歸納：優先整合多個 Q&A 的資訊，去除重複，並將零碎的描述整合成較高層次的邏輯歸納。"
    "3. 重新定義缺口：『Knowledge Gaps & Limitations』章節應聚焦於『產品本身的限制』（例如：不具備螢幕、訂閱制成本、不適用於特定運動）以及『使用上的邊界提示』，而非針對文檔內容多寡進行稽核。"
    "4. 專業語調：輸出內容必須結構清楚、語氣客觀且具備導讀性質。避免使用『資料未說明』或『內容零散』等描述，應改以總結性的陳述。"
    "5. 格式要求：輸出標題必須嚴格遵守指定格式（Overview, Core Concepts, Key Trends, Key Entities, Methodology & Best Practices, Knowledge Gaps & Limitations, Example Q&A, Source References）。"
    "使用繁體中文，確保讀起來像是一份能讓新使用者快速掌握 Oura Ring 核心價值的專業文件。"
    "在輸出 Example Q&A 時，請確保範例編號是連續的（從 1 開始遞增），不要跳號或保留原始索引編號。"
)

    user_prompt = (
        "請根據以下 Q&A 內容整理一份 skill.md。\n\n"
        f"主題：{topic}\n"
        f"資料來源數量：{len(source_list)}\n"
        f"最後更新時間：{today}\n"
        "適用 Agent 類型：健康穿戴裝置顧問\n\n"
        "Q&A 內容：\n"
        f"{qa_block}\n\n"
        "來源清單（供 Source References 使用）：\n"
        f"{sources_block}\n\n"
        "skill.md 格式（必須完整輸出所有段落標題）：\n"
        "# Skill: [主題名稱]\n\n"
        "## Metadata\n"
        "- **知識領域**：\n"
        "- **資料來源數量**：\n"
        "- **最後更新時間**：\n"
        "- **適用 Agent 類型**：\n\n"
        "## Overview\n"
        "[200字以內摘要]\n\n"
        "## Core Concepts\n"
        "[條列 5–15 個概念]\n\n"
        "## Key Trends\n"
        "[條列 3–10 個趨勢]\n\n"
        "## Key Entities\n"
        "[條列重要實體]\n\n"
        "## Methodology & Best Practices\n"
        "[方法論與最佳實踐]\n\n"
        "## Knowledge Gaps & Limitations\n"
        "[知識邊界]\n\n"
        "## Example Q&A\n"
        "[列出 3–5 組]\n\n"
        "## Source References\n"
        "[列出來源清單]\n"
    )

    return call_llm(model, [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}])


def main() -> None:
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="Skill builder for RAG knowledge base.")
    parser.add_argument("--output", type=str, default="skill.md", help="Output skill.md path.")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", help="LLM model name.")
    parser.add_argument("--topic", type=str, default="Oura Ring 智慧健康戒指", help="Skill topic name.")
    parser.add_argument("--table", type=str, default=TABLE_DEFAULT, help="pgvector table name.")
    parser.add_argument("--top-k", type=int, default=5, help="Top-k chunks per question.")
    parser.add_argument("--fetch-k", type=int, default=20, help="Initial candidates to fetch.")
    parser.add_argument("--rerank", action="store_true", help="Enable reranking.")
    parser.add_argument("--rerank-model", type=str, default="rerank-multilingual-v3.0", help="Cohere rerank model.")
    parser.add_argument("--source-prefix", type=str, default=None, help="Filter by source_file prefix.")
    parser.add_argument("--source-type", type=str, default=None, help="Filter by source_type (md/txt).")
    parser.add_argument("--section-contains", type=str, default=None, help="Filter by section path keyword.")
    parser.add_argument("--embedding-model", type=str, default=os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL_DEFAULT))
    parser.add_argument(
        "--embedding-provider",
        type=str,
        default=os.getenv("EMBEDDING_PROVIDER", "huggingface"),
    )
    parser.add_argument(
        "--sources-metadata",
        type=str,
        default="sources_metadata.json",
        help="JSON file mapping source_file to type/date.",
    )
    args = parser.parse_args()

    conn = connect_db()
    try:
        source_list = get_source_list(conn, args.table)
    finally:
        conn.close()

    qa_items: List[QAItem] = []
    for q, prefix in DEFAULT_QUESTIONS:
        query_args = argparse.Namespace(
            model=args.model,
            table=args.table,
            embedding_model=args.embedding_model,
            embedding_provider=args.embedding_provider,
            top_k=args.top_k,
            fetch_k=args.fetch_k,
            rerank=args.rerank,
            rerank_model=args.rerank_model,
            source_prefix=prefix or args.source_prefix,
            source_type=args.source_type,
            section_contains=args.section_contains,
            show_context=False,
            history_turns=0,
            rate_limit=0.5,
            max_retries=3,
        )
        answer, hits = rq.handle_query(q, query_args, history=None)
        sources = [f"{h.source_file} | chunk {h.chunk_index}" for h in hits]
        qa_items.append(QAItem(question=q, answer=answer, sources=sources))

    metadata = load_sources_metadata(args.sources_metadata)
    skill_md = synthesize_skill_md(args.topic, source_list, qa_items, args.model, metadata)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(skill_md.strip() + "\n")

    print(f"skill.md written to {args.output}")


if __name__ == "__main__":
    main()
