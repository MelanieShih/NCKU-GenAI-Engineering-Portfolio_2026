import argparse
import fnmatch
import os
import hashlib
import json
import time
from datetime import datetime, timezone
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import chardet
import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv
from huggingface_hub import InferenceClient


RAW_DIR_DEFAULT = Path("data/raw")
PROCESSED_DIR_DEFAULT = Path("data/processed")
TABLE_DEFAULT = "rag_chunks"
MODEL_DEFAULT = "sentence-transformers/all-MiniLM-L6-v2"
CACHE_PATH_DEFAULT = Path("data/.embedding_cache.jsonl")


@dataclass
class RawDoc:
    path: Path
    rel_path: Path
    ext: str


@dataclass
class ChunkRecord:
    source_file: str
    source_type: str
    chunk_index: int
    file_hash: str
    content: str
    original_title: Optional[str]
    section_path: Optional[str]
    updated_at: datetime


def detect_and_decode(path: Path) -> str:
    data = path.read_bytes()
    if not data:
        return ""
    # Prefer UTF-8 first (most source files are UTF-8). Fall back to chardet if needed.
    for enc in ["utf-8", "utf-8-sig"]:
        try:
            return data.decode(enc, errors="strict")
        except Exception:
            pass

    detected = chardet.detect(data)
    encoding = detected.get("encoding")
    confidence = detected.get("confidence") or 0.0
    if encoding and confidence >= 0.5:
        try:
            return data.decode(encoding, errors="replace")
        except Exception:
            pass

    return data.decode("utf-8", errors="ignore")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_raw_files(raw_dir: Path, subdir: Optional[str], pattern: Optional[str]) -> List[RawDoc]:
    root = raw_dir / subdir if subdir else raw_dir
    if not root.exists():
        return []

    docs: List[RawDoc] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext not in {".md", ".txt"}:
            continue
        if pattern and not fnmatch.fnmatch(path.name, pattern):
            continue
        rel = path.relative_to(raw_dir)
        docs.append(RawDoc(path=path, rel_path=rel, ext=ext))
    return docs


def parse_raw_wrapper_metadata(text: str) -> Tuple[Dict[str, str], str]:
    metadata: Dict[str, str] = {}
    body_lines: List[str] = []
    in_body = False
    for line in text.splitlines():
        if line.startswith("Title:"):
            metadata["original_title"] = line.replace("Title:", "", 1).strip()
            continue
        if line.startswith("URL Source:"):
            metadata["source_url"] = line.replace("URL Source:", "", 1).strip()
            continue
        if line.startswith("Markdown Content:"):
            in_body = True
            continue
        if in_body or ("original_title" not in metadata and "source_url" not in metadata):
            body_lines.append(line)
    return metadata, "\n".join(body_lines)


def clean_markdown_links(text: str) -> str:
    # [text](url) -> text
    return re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)


def remove_markdown_images(text: str) -> str:
    return re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)

def remove_inline_noise(text: str) -> str:
    # Remove inline editorial notes
    text = text.replace("（圖／擷取自ouraring官網）", "")
    return text

def normalize_formatting(text: str) -> str:
    # Convert headings to plain markers
    text = re.sub(r"^\s*#\s+(.+)$", r"【\1】", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*##\s+(.+)$", r"【\1】", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*###\s+(.+)$", r"〈\1〉", text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
    # Convert bullet list markers
    text = re.sub(r"^\s*[\*\-]\s+", "• ", text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r"^\s*([*\-]\s*){3,}$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*_{3,}\s*$", "", text, flags=re.MULTILINE)
    return text


def convert_markdown_tables_to_bullets(text: str) -> str:
    lines = text.splitlines()
    output: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "|" not in line:
            output.append(line)
            i += 1
            continue

        # Try to parse a markdown table block
        table_lines = []
        j = i
        while j < len(lines) and "|" in lines[j]:
            table_lines.append(lines[j])
            j += 1

        # Need at least header + separator + one row
        if len(table_lines) >= 3 and re.match(r"^\s*\|?\s*:?-{2,}\s*\|", table_lines[1]):
            # Parse header
            header_cells = [c.strip() for c in table_lines[0].strip().strip("|").split("|")]
            # Determine row cells
            rows = []
            for row_line in table_lines[2:]:
                cells = [c.strip() for c in row_line.strip().strip("|").split("|")]
                if len(cells) < len(header_cells):
                    cells += [""] * (len(header_cells) - len(cells))
                rows.append(cells[:len(header_cells)])

            if len(header_cells) >= 2:
                label_col = header_cells[0]
                entity_cols = header_cells[1:]
                # Build per-entity sections (方案 1)
                entity_to_pairs: List[List[str]] = [[] for _ in entity_cols]
                for row in rows:
                    label = row[0]
                    for idx, ent in enumerate(entity_cols):
                        value = row[idx + 1] if idx + 1 < len(row) else ""
                        if label or value:
                            entity_to_pairs[idx].append(f"{label}：{value}".strip())
                for idx, ent in enumerate(entity_cols):
                    output.append(f"{ent}：")
                    for pair in entity_to_pairs[idx]:
                        output.append(f"• {pair}")
                    output.append("")
            else:
                # Fallback: just append the table as-is
                output.extend(table_lines)

            i = j
            continue

        # Not a valid table block
        output.append(line)
        i += 1

    return "\n".join(output)

def normalize_blank_lines(text: str) -> str:
    # Normalize blank lines, keep spacing around headings and bullet blocks
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned: List[str] = []
    blank = 0
    for idx, line in enumerate(lines):
        if line.strip() == "":
            blank += 1
            if blank <= 1:
                cleaned.append("")
            continue

        blank = 0
        # Ensure a blank line before headings and bullet blocks when previous line is text
        if cleaned and cleaned[-1] != "":
            if re.match(r"^(【.+】|〈.+〉)$", line) or line.startswith("• "):
                cleaned.append("")
        cleaned.append(line)

        # Ensure a blank line after headings if next line is text/bullet
        if re.match(r"^(【.+】|〈.+〉)$", line):
            cleaned.append("")

    # Collapse any accidental multiple blanks
    final_lines: List[str] = []
    blank = 0
    for line in cleaned:
        if line.strip() == "":
            blank += 1
            if blank <= 1:
                final_lines.append("")
        else:
            blank = 0
            final_lines.append(line)
    return "\n".join(final_lines).strip()


def split_paragraphs_with_sections(text: str) -> List[Tuple[str, Optional[str]]]:
    lines = text.splitlines()
    paragraphs: List[Tuple[str, Optional[str]]] = []
    current_lines: List[str] = []
    section: Optional[str] = None
    subsection: Optional[str] = None

    def current_section_path() -> Optional[str]:
        if section and subsection:
            return f"{section} > {subsection}"
        if section:
            return section
        return None

    def flush_paragraph() -> None:
        nonlocal current_lines
        if current_lines:
            para = "\n".join(current_lines).strip()
            if para:
                paragraphs.append((para, current_section_path()))
            current_lines = []

    for line in lines:
        if line.strip() == "":
            flush_paragraph()
            continue
        # Detect headings in either raw or normalized form
        m_section = re.match(r"^\s*(##\s+(.+)|【(.+)】)$", line)
        m_sub = re.match(r"^\s*(###\s+(.+)|〈(.+)〉)$", line)
        if m_section:
            flush_paragraph()
            section = (m_section.group(2) or m_section.group(3) or "").strip().strip("*")
            subsection = None
            continue
        if m_sub:
            flush_paragraph()
            subsection = (m_sub.group(2) or m_sub.group(3) or "").strip().strip("*")
            continue
        current_lines.append(line)

    flush_paragraph()
    return paragraphs


def split_fixed_length(text: str, chunk_size: int, overlap: int) -> List[str]:
    if chunk_size <= 0:
        return []
    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 4)
    step = max(1, chunk_size - overlap)
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += step
    return chunks


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    paragraphs = [p for p, _ in split_paragraphs_with_sections(text)]
    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        if len(para) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(split_fixed_length(para, chunk_size, overlap))
            continue

        if not current:
            current = para
            continue

        if len(current) + 2 + len(para) <= chunk_size:
            current = f"{current}\n\n{para}"
        else:
            chunks.append(current)
            current = para

    if current:
        chunks.append(current)

    return chunks


def remove_html_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def is_link_only_line(line: str) -> bool:
    return re.match(r"^\s*([\-*+]\s+)?\[[^\]]+\]\([^)]*\)\s*$", line) is not None


def is_url_only_line(line: str) -> bool:
    return re.match(r"^\s*([\-*+]\s+)?https?://\S+\s*$", line) is not None


def is_attachment_line(line: str) -> bool:
    lowered = line.lower()
    if any(k in lowered for k in ["article_attachments", "attachment", "download"]):
        return True
    if "附件" in line:
        return True
    if re.match(r"^\s*([\-*+]\s+)?\[[^\]]+\]\([^)]*\.(pdf|zip|png|jpg|jpeg|gif)\)\s*$", line, re.IGNORECASE):
        return True
    return False


def remove_attachment_lines(lines: List[str]) -> List[str]:
    return [line for line in lines if not is_attachment_line(line)]


def remove_front_matter_noise(lines: List[str]) -> List[str]:
    if not lines:
        return lines

    # Per your rule: treat everything before the first valid "##" as navigation noise,
    # but skip headings that are known navigation sections (e.g., 國家/地區, 目錄).
    nav_headings = {"國家/地區", "目錄", "語言", "商品已加入購物車"}
    for i, line in enumerate(lines):
        m = re.match(r"^\s*##\s+(.+)", line)
        if not m:
            continue
        heading = m.group(1).strip().strip("*")
        if heading in nav_headings:
            continue
        return lines[i:]
    return lines


def keep_main_body(lines: List[str]) -> List[str]:
    # Placeholder for future refinement; for now keep all after front noise removal
    return lines


def truncate_tail_noise(lines: List[str]) -> List[str]:
    keywords = [
        "更多資訊",
        "相關文章",
        "推薦閱讀",
        "more information",
        "related articles",
        "you may also like",
        "related posts",
        "延伸閱讀",
        "參考資料",
        "目錄",
    ]
    for i, line in enumerate(lines):
        stripped = re.sub(r"^[#\-* ]+", "", line).strip().strip("*")
        lower = stripped.lower()
        # Hard stop if these words appear anywhere in the line
        if "分享文章" in stripped or "分享此文" in stripped or "newsflash" in lower:
            return lines[:i]
        if "資料來源" in stripped:
            return lines[:i]
        # Only truncate on section headings for these keywords (##/###)
        if re.match(r"^\s*#{2,3}\s+.+", line) and any(k in stripped for k in keywords):
            return lines[:i]
    return lines


def remove_link_only_blocks(lines: List[str]) -> List[str]:
    cleaned: List[str] = []
    block: List[str] = []
    heading_re = re.compile(r"^\s*#{2,6}\s+.+")

    def flush_block() -> None:
        nonlocal block
        if not block:
            return
        if any(heading_re.match(ln) for ln in block):
            cleaned.extend(block)
            block = []
            return
        link_lines = [ln for ln in block if is_link_only_line(ln) or is_url_only_line(ln)]
        if len(link_lines) >= max(1, len(block) - 1):
            block = []
            return
        cleaned.extend(block)
        block = []

    for line in lines:
        if line.strip() == "":
            flush_block()
            cleaned.append(line)
        else:
            block.append(line)

    flush_block()
    return cleaned


def normalize_whitespace(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    cleaned: List[str] = []
    blank = 0
    for line in lines:
        if line == "":
            blank += 1
            if blank <= 1:
                cleaned.append("")
        else:
            blank = 0
            cleaned.append(line)
    return "\n".join(cleaned).strip()


def save_processed_text(processed_dir: Path, rel_path: Path, text: str) -> Path:
    out_path = processed_dir / rel_path.with_suffix(".txt")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Use UTF-8 with BOM to improve Windows text viewer compatibility
    out_path.write_text(text, encoding="utf-8-sig")
    return out_path


def clean_markdown(raw_text: str) -> Tuple[Dict[str, str], str]:
    metadata, body = parse_raw_wrapper_metadata(raw_text)

    body = remove_markdown_images(body)
    body = remove_html_tags(body)
    body = clean_markdown_links(body)
    body = remove_inline_noise(body)

    lines = body.splitlines()
    lines = remove_attachment_lines(lines)
    lines = remove_front_matter_noise(lines)
    lines = keep_main_body(lines)
    lines = truncate_tail_noise(lines)
    lines = remove_link_only_blocks(lines)

    text = normalize_whitespace("\n".join(lines))

    title = metadata.get("original_title")
    if title:
        text = f"# {title}\n\n{text}" if text else f"# {title}"

    return metadata, text


def clean_txt(raw_text: str) -> str:
    return normalize_whitespace(raw_text)


def rebuild_processed_dir(processed_dir: Path) -> None:
    if processed_dir.exists():
        shutil.rmtree(processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)


def post_process_processed_dir(processed_dir: Path, verbose: bool = False) -> None:
    if not processed_dir.exists():
        return
    for path in processed_dir.rglob("*.txt"):
        raw_text = path.read_text(encoding="utf-8-sig", errors="ignore")
        text = convert_markdown_tables_to_bullets(raw_text)
        text = normalize_formatting(text)
        text = normalize_blank_lines(text)
        path.write_text(text, encoding="utf-8-sig")
        if verbose:
            rel = path.relative_to(processed_dir)
            print(f"post-processed: {rel}")


def connect_db() -> psycopg2.extensions.connection:
    conn_str = os.getenv("PGVECTOR_CONNECTION_STRING")
    if not conn_str:
        raise RuntimeError("Missing PGVECTOR_CONNECTION_STRING in environment.")
    conn = psycopg2.connect(conn_str)
    register_vector(conn)
    return conn


def ensure_table(conn, table: str, dim: int) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id BIGSERIAL PRIMARY KEY,
                source_file TEXT NOT NULL,
                source_type TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                file_hash TEXT NOT NULL,
                content TEXT NOT NULL,
                original_title TEXT,
                section_path TEXT,
                updated_at TIMESTAMPTZ NOT NULL,
                embedding VECTOR({dim}) NOT NULL,
                UNIQUE (source_file, chunk_index, file_hash)
            );
            """
        )
        cur.execute(f"CREATE INDEX IF NOT EXISTS {table}_source_file_idx ON {table} (source_file);")
        cur.execute(f"CREATE INDEX IF NOT EXISTS {table}_file_hash_idx ON {table} (file_hash);")
    conn.commit()


def get_existing_hashes(conn, table: str, source_file: str) -> List[str]:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT DISTINCT file_hash FROM {table} WHERE source_file = %s;",
            (source_file,),
        )
        return [row[0] for row in cur.fetchall()]


def delete_by_source(conn, table: str, source_file: str) -> None:
    with conn.cursor() as cur:
        cur.execute(f"DELETE FROM {table} WHERE source_file = %s;", (source_file,))
    conn.commit()


def delete_missing_sources(conn, table: str, existing_sources: Iterable[str]) -> None:
    existing_sources_set = set(existing_sources)
    with conn.cursor() as cur:
        cur.execute(f"SELECT DISTINCT source_file FROM {table};")
        db_sources = {row[0] for row in cur.fetchall()}
    to_delete = sorted(db_sources - existing_sources_set)
    if not to_delete:
        return
    with conn.cursor() as cur:
        cur.execute(
            f"DELETE FROM {table} WHERE source_file = ANY(%s);",
            (to_delete,),
        )
    conn.commit()


def insert_chunks(
    conn,
    table: str,
    records: List[ChunkRecord],
    embeddings: List[List[float]],
) -> None:
    rows = []
    for rec, emb in zip(records, embeddings):
        rows.append(
            (
                rec.source_file,
                rec.source_type,
                rec.chunk_index,
                rec.file_hash,
                rec.content,
                rec.original_title,
                rec.section_path,
                rec.updated_at,
                emb,
            )
        )

    with conn.cursor() as cur:
        execute_values(
            cur,
            f"""
            INSERT INTO {table}
                (source_file, source_type, chunk_index, file_hash, content, original_title, section_path, updated_at, embedding)
            VALUES %s
            ON CONFLICT DO NOTHING;
            """,
            rows,
        )
    conn.commit()


def load_embedding_cache(path: Path) -> Dict[str, List[float]]:
    cache: Dict[str, List[float]] = {}
    if not path.exists():
        return cache
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            item = json.loads(line)
            cache[item["key"]] = item["embedding"]
        except Exception:
            continue
    return cache


def append_embedding_cache(path: Path, key: str, embedding: List[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"key": key, "embedding": embedding}, ensure_ascii=False) + "\n")


def make_cache_key(model: str, text: str) -> str:
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"{model}:{h}"


def embed_texts_hf(
    texts: List[str],
    model: str,
    batch_size: int,
    rate_limit_seconds: float,
    max_retries: int,
    cache_path: Path,
) -> List[List[float]]:
    token = os.getenv("HF_API_KEY")
    if not token:
        raise RuntimeError("Missing HF_API_KEY in environment.")
    client = InferenceClient(token=token)

    cache = load_embedding_cache(cache_path)
    outputs: List[Optional[List[float]]] = [None] * len(texts)

    # Fill from cache first
    to_embed: List[Tuple[int, str, str]] = []
    for idx, text in enumerate(texts):
        key = make_cache_key(model, text)
        if key in cache:
            outputs[idx] = cache[key]
        else:
            to_embed.append((idx, text, key))

    # Batch embedding for remaining texts
    for start in range(0, len(to_embed), batch_size):
        batch = to_embed[start : start + batch_size]
        batch_texts = [t for _, t, _ in batch]

        attempt = 0
        while True:
            try:
                # HF Inference API supports list input
                batch_embs = client.feature_extraction(batch_texts, model=model)
                break
            except Exception as e:
                attempt += 1
                if attempt > max_retries:
                    raise e
                time.sleep(rate_limit_seconds * attempt)

        # Normalize output shape
        if hasattr(batch_embs, "tolist"):
            batch_embs = batch_embs.tolist()
        if isinstance(batch_embs, list) and batch_embs:
            if isinstance(batch_embs[0], list) and batch_embs[0] and isinstance(batch_embs[0][0], (int, float)):
                normalized = batch_embs
            elif isinstance(batch_embs[0], (int, float)):
                # Single vector returned for single text
                normalized = [batch_embs]
            else:
                normalized = [emb[0] for emb in batch_embs]
        else:
            raise RuntimeError("Unexpected embedding output format from HF API.")

        for (idx, _text, key), emb in zip(batch, normalized):
            outputs[idx] = emb
            cache[key] = emb
            append_embedding_cache(cache_path, key, emb)

        if rate_limit_seconds > 0:
            time.sleep(rate_limit_seconds)

    # type ignore: all outputs filled
    return [emb for emb in outputs if emb is not None]


_LOCAL_MODEL_CACHE: Dict[str, "SentenceTransformer"] = {}


def embed_texts_local(texts: List[str], model: str) -> List[List[float]]:
    from sentence_transformers import SentenceTransformer
    if model not in _LOCAL_MODEL_CACHE:
        _LOCAL_MODEL_CACHE[model] = SentenceTransformer(model)
    local_model = _LOCAL_MODEL_CACHE[model]
    embeddings = local_model.encode(texts, show_progress_bar=False)
    if hasattr(embeddings, "tolist"):
        return embeddings.tolist()
    return [list(vec) for vec in embeddings]


def main() -> None:
    # Override any previously set environment variables with .env values
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="Phase 1: clean raw data to processed text.")
    parser.add_argument("--rebuild", action="store_true", help="Clear data/processed/ and rebuild.")
    parser.add_argument("--build-db", action="store_true", help="Chunk, embed, and write to pgvector.")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Chunk size (characters).")
    parser.add_argument("--overlap", type=int, default=200, help="Chunk overlap (characters).")
    parser.add_argument("--table", type=str, default=TABLE_DEFAULT, help="Vector table name.")
    parser.add_argument("--model", type=str, default=MODEL_DEFAULT, help="Embedding model name.")
    parser.add_argument("--batch-size", type=int, default=16, help="Embedding batch size for HF API.")
    parser.add_argument("--rate-limit", type=float, default=0.5, help="Seconds to sleep between HF API requests.")
    parser.add_argument("--max-retries", type=int, default=3, help="Max retries for HF API requests.")
    parser.add_argument("--cache-path", type=str, default=str(CACHE_PATH_DEFAULT), help="Embedding cache path.")
    parser.add_argument("--subdir", type=str, default=None, help="Only process data/raw/<subdir>.")
    parser.add_argument("--pattern", type=str, default=None, help="Only process files matching glob pattern.")
    parser.add_argument("--dry-run", action="store_true", help="List files to process without writing.")
    parser.add_argument("--verbose", action="store_true", help="Show processing details.")
    parser.add_argument("--post-process", action="store_true", help="Normalize symbols and blank lines in data/processed/.")
    parser.add_argument("--raw-dir", type=str, default=str(RAW_DIR_DEFAULT), help="Raw data directory.")
    parser.add_argument("--processed-dir", type=str, default=str(PROCESSED_DIR_DEFAULT), help="Processed data directory.")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    processed_dir = Path(args.processed_dir)

    if args.post_process:
        post_process_processed_dir(processed_dir, verbose=args.verbose)
        return

    if args.rebuild:
        rebuild_processed_dir(processed_dir)
    else:
        processed_dir.mkdir(parents=True, exist_ok=True)

    docs = load_raw_files(raw_dir, args.subdir, args.pattern)
    if args.verbose or args.dry_run:
        print(f"Found {len(docs)} files to process.")

    for doc in docs:
        if args.verbose or args.dry_run:
            print(f"- {doc.rel_path}")
        if args.dry_run:
            continue

        raw_text = detect_and_decode(doc.path)
        if doc.ext == ".md":
            _, cleaned = clean_markdown(raw_text)
        else:
            cleaned = clean_txt(raw_text)

        save_processed_text(processed_dir, doc.rel_path, cleaned)

    if not args.build_db:
        return

    # Ensure processed text is normalized before embedding
    post_process_processed_dir(processed_dir, verbose=args.verbose)

    embedding_provider = os.getenv("EMBEDDING_PROVIDER", "sentence-transformers").lower()

    if embedding_provider == "huggingface":
        test_emb = embed_texts_hf(
            ["ping"],
            args.model,
            batch_size=1,
            rate_limit_seconds=args.rate_limit,
            max_retries=args.max_retries,
            cache_path=Path(args.cache_path),
        )[0]
    else:
        test_emb = embed_texts_local(["ping"], args.model)[0]
    embed_dim = len(test_emb)

    conn = connect_db()
    ensure_table(conn, args.table, embed_dim)

    if args.rebuild:
        with conn.cursor() as cur:
            cur.execute(f"TRUNCATE TABLE {args.table};")
        conn.commit()

    raw_relative_files: List[str] = []

    for doc in docs:
        rel = doc.rel_path.as_posix()
        raw_relative_files.append(rel)

        raw_bytes = doc.path.read_bytes()
        file_hash = sha256_bytes(raw_bytes)
        existing_hashes = get_existing_hashes(conn, args.table, rel)

        processed_path = processed_dir / doc.rel_path.with_suffix(".txt")
        if not processed_path.exists():
            continue

        if existing_hashes and file_hash in existing_hashes:
            continue

        if existing_hashes and file_hash not in existing_hashes:
            delete_by_source(conn, args.table, rel)

        processed_text = processed_path.read_text(encoding="utf-8-sig", errors="ignore")
        paragraphs = split_paragraphs_with_sections(processed_text)

        # Build chunks while preserving section_path
        chunks: List[Tuple[str, Optional[str]]] = []
        for para_text, section_path in paragraphs:
            if len(para_text) > args.chunk_size:
                for part in split_fixed_length(para_text, args.chunk_size, args.overlap):
                    chunks.append((part, section_path))
            else:
                chunks.append((para_text, section_path))

        # Combine chunks to respect size limits
        final_chunks: List[Tuple[str, Optional[str]]] = []
        buffer_text = ""
        buffer_section: Optional[str] = None
        for text_part, section_path in chunks:
            if not buffer_text:
                buffer_text = text_part
                buffer_section = section_path
                continue
            if len(buffer_text) + 2 + len(text_part) <= args.chunk_size and buffer_section == section_path:
                buffer_text = f"{buffer_text}\n\n{text_part}"
            else:
                final_chunks.append((buffer_text, buffer_section))
                buffer_text = text_part
                buffer_section = section_path
        if buffer_text:
            final_chunks.append((buffer_text, buffer_section))

        records: List[ChunkRecord] = []
        for idx, (chunk_text, section_path) in enumerate(final_chunks):
            if not chunk_text.strip():
                continue
            records.append(
                ChunkRecord(
                    source_file=rel,
                    source_type=doc.ext.lstrip("."),
                    chunk_index=idx,
                    file_hash=file_hash,
                    content=chunk_text,
                    original_title=None,
                    section_path=section_path,
                    updated_at=datetime.now(timezone.utc),
                )
            )

        # Try to re-extract title from raw wrapper if possible
        raw_text = detect_and_decode(doc.path)
        metadata, _ = parse_raw_wrapper_metadata(raw_text)
        for rec in records:
            rec.original_title = metadata.get("original_title")

        if not records:
            continue

        if embedding_provider == "huggingface":
            embeddings_list = embed_texts_hf(
                [r.content for r in records],
                args.model,
                batch_size=args.batch_size,
                rate_limit_seconds=args.rate_limit,
                max_retries=args.max_retries,
                cache_path=Path(args.cache_path),
            )
        else:
            embeddings_list = embed_texts_local([r.content for r in records], args.model)
        insert_chunks(conn, args.table, records, embeddings_list)

    delete_missing_sources(conn, args.table, raw_relative_files)
    conn.close()


if __name__ == "__main__":
    main()
