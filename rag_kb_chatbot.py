#!/usr/bin/env python3
import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import requests
from sklearn.feature_extraction.text import HashingVectorizer


SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS chunks (
  id TEXT PRIMARY KEY,
  doc_path TEXT NOT NULL,
  doc_mtime_ns INTEGER NOT NULL,
  doc_size INTEGER NOT NULL,
  doc_sha256 TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  chunk_start INTEGER NOT NULL,
  chunk_end INTEGER NOT NULL,
  chunk_text TEXT NOT NULL,
  embedding BLOB NOT NULL,
  embedding_dim INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc_path ON chunks(doc_path);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_sha ON chunks(doc_sha256);
"""


DEFAULT_DB_PATH = "./rag_kb.sqlite3"
DEFAULT_DOCS_DIR = "./docs"
DEFAULT_DIM = 2048


TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".rst",
    ".log",
    ".csv",
    ".tsv",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".htm",
    ".py",
    ".js",
    ".ts",
    ".java",
    ".go",
    ".rs",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".php",
    ".rb",
    ".sql",
    ".sh",
    ".ini",
    ".toml",
    ".cfg",
}


def _utc_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _read_bytes(path: Path, max_bytes: int) -> bytes:
    with path.open("rb") as f:
        data = f.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"File too large (>{max_bytes} bytes): {path}")
    return data


def _safe_decode(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")


def _load_text_from_file(path: Path, max_bytes: int) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "PDF support requires pypdf. Install with: pip install pypdf"
            ) from e
        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)

    if ext in TEXT_EXTENSIONS or ext == "":
        data = _read_bytes(path, max_bytes=max_bytes)
        return _safe_decode(data)

    raise ValueError(f"Unsupported file type: {path}")


_WS_RE = re.compile(r"[ \t]+\n")
_MULTI_NL_RE = re.compile(r"\n{3,}")


def normalize_text(t: str) -> str:
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = _WS_RE.sub("\n", t)
    t = _MULTI_NL_RE.sub("\n\n", t)
    return t.strip()


@dataclass(frozen=True)
class Chunk:
    doc_path: str
    doc_mtime_ns: int
    doc_size: int
    doc_sha256: str
    chunk_index: int
    chunk_start: int
    chunk_end: int
    chunk_text: str

    @property
    def id(self) -> str:
        h = hashlib.sha256()
        h.update(self.doc_sha256.encode("utf-8"))
        h.update(b"|")
        h.update(str(self.chunk_index).encode("utf-8"))
        return h.hexdigest()


def chunk_text(
    text: str,
    *,
    chunk_chars: int,
    overlap_chars: int,
) -> List[Tuple[int, int, str]]:
    if chunk_chars <= 0:
        raise ValueError("chunk_chars must be > 0")
    if overlap_chars < 0:
        raise ValueError("overlap_chars must be >= 0")
    if overlap_chars >= chunk_chars:
        raise ValueError("overlap_chars must be < chunk_chars")

    text = normalize_text(text)
    if not text:
        return []

    n = len(text)
    out: List[Tuple[int, int, str]] = []
    start = 0
    idx = 0
    while start < n:
        end = min(n, start + chunk_chars)
        chunk = text[start:end]
        chunk = chunk.strip()
        if chunk:
            out.append((start, end, chunk))
            idx += 1
        if end >= n:
            break
        start = max(0, end - overlap_chars)
    return out


class SqliteVectorDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def __enter__(self) -> "SqliteVectorDB":
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._conn.executescript(SCHEMA_SQL)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._conn is not None:
            self._conn.commit()
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("DB not open")
        return self._conn

    def upsert_chunks(self, chunks: Sequence[Chunk], embeddings: np.ndarray) -> int:
        if len(chunks) != embeddings.shape[0]:
            raise ValueError("chunks and embeddings row count mismatch")
        if embeddings.ndim != 2:
            raise ValueError("embeddings must be 2D")
        dim = int(embeddings.shape[1])
        now = _utc_iso()
        rows = []
        for ch, emb in zip(chunks, embeddings):
            emb = np.asarray(emb, dtype=np.float32)
            if emb.shape != (dim,):
                raise ValueError("embedding shape mismatch")
            rows.append(
                (
                    ch.id,
                    ch.doc_path,
                    ch.doc_mtime_ns,
                    ch.doc_size,
                    ch.doc_sha256,
                    ch.chunk_index,
                    ch.chunk_start,
                    ch.chunk_end,
                    ch.chunk_text,
                    emb.tobytes(),
                    dim,
                    now,
                )
            )
        cur = self.conn.cursor()
        cur.executemany(
            """
            INSERT INTO chunks (
              id, doc_path, doc_mtime_ns, doc_size, doc_sha256,
              chunk_index, chunk_start, chunk_end, chunk_text,
              embedding, embedding_dim, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              doc_path=excluded.doc_path,
              doc_mtime_ns=excluded.doc_mtime_ns,
              doc_size=excluded.doc_size,
              doc_sha256=excluded.doc_sha256,
              chunk_index=excluded.chunk_index,
              chunk_start=excluded.chunk_start,
              chunk_end=excluded.chunk_end,
              chunk_text=excluded.chunk_text,
              embedding=excluded.embedding,
              embedding_dim=excluded.embedding_dim
            """,
            rows,
        )
        self.conn.commit()
        return cur.rowcount

    def delete_doc_path_prefix(self, prefix: str) -> int:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM chunks WHERE doc_path LIKE ?", (prefix.rstrip("/") + "/%",))
        self.conn.commit()
        return cur.rowcount

    def count_chunks(self) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM chunks")
        return int(cur.fetchone()[0])

    def iter_all_embeddings(self) -> Iterable[Tuple[str, str, str, int, int, int, int, str, bytes, int]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT
              id, doc_path, doc_sha256, chunk_index, chunk_start, chunk_end,
              doc_mtime_ns, chunk_text, embedding, embedding_dim
            FROM chunks
            """
        )
        for row in cur:
            yield (
                row[0],
                row[1],
                row[2],
                int(row[3]),
                int(row[4]),
                int(row[5]),
                int(row[6]),
                row[7],
                row[8],
                int(row[9]),
            )

    def get_chunks_by_ids(self, ids: Sequence[str]) -> Dict[str, Dict]:
        if not ids:
            return {}
        placeholders = ",".join(["?"] * len(ids))
        cur = self.conn.cursor()
        cur.execute(
            f"""
            SELECT
              id, doc_path, doc_sha256, chunk_index, chunk_start, chunk_end,
              doc_mtime_ns, doc_size, chunk_text, created_at
            FROM chunks
            WHERE id IN ({placeholders})
            """,
            tuple(ids),
        )
        out: Dict[str, Dict] = {}
        for row in cur.fetchall():
            out[row[0]] = {
                "id": row[0],
                "doc_path": row[1],
                "doc_sha256": row[2],
                "chunk_index": int(row[3]),
                "chunk_start": int(row[4]),
                "chunk_end": int(row[5]),
                "doc_mtime_ns": int(row[6]),
                "doc_size": int(row[7]),
                "chunk_text": row[8],
                "created_at": row[9],
            }
        return out


class HashedEmbeddingModel:
    def __init__(self, dim: int):
        if dim <= 0:
            raise ValueError("dim must be > 0")
        self.dim = dim
        self._vectorizer = HashingVectorizer(
            n_features=dim,
            alternate_sign=False,
            norm=None,
            lowercase=True,
            ngram_range=(1, 2),
        )

    def embed_texts(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        X = self._vectorizer.transform(texts)  # scipy sparse
        X = X.astype(np.float32)
        dense = X.toarray()
        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        dense = dense / norms
        return dense.astype(np.float32, copy=False)


def iter_doc_files(root: Path, *, follow_symlinks: bool) -> Iterable[Path]:
    root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(str(root))
    if root.is_file():
        yield root
        return

    for p in root.rglob("*"):
        try:
            if not follow_symlinks and p.is_symlink():
                continue
            if p.is_file():
                yield p
        except OSError:
            continue


def build_chunks_for_path(
    path: Path,
    *,
    docs_root: Path,
    max_bytes: int,
    chunk_chars: int,
    overlap_chars: int,
) -> List[Chunk]:
    stat = path.stat()
    raw = _load_text_from_file(path, max_bytes=max_bytes)
    text = normalize_text(raw)
    if not text:
        return []
    doc_sha = _sha256_bytes(text.encode("utf-8"))
    rel = str(path.resolve().relative_to(docs_root.resolve()))
    pieces = chunk_text(text, chunk_chars=chunk_chars, overlap_chars=overlap_chars)
    chunks: List[Chunk] = []
    for i, (start, end, chunk) in enumerate(pieces):
        chunks.append(
            Chunk(
                doc_path=rel,
                doc_mtime_ns=int(stat.st_mtime_ns),
                doc_size=int(stat.st_size),
                doc_sha256=doc_sha,
                chunk_index=i,
                chunk_start=start,
                chunk_end=end,
                chunk_text=chunk,
            )
        )
    return chunks


def cosine_top_k(
    query_vec: np.ndarray,
    items: Sequence[Tuple[str, np.ndarray]],
    *,
    k: int,
) -> List[Tuple[str, float]]:
    if k <= 0:
        return []
    q = np.asarray(query_vec, dtype=np.float32)
    if q.ndim != 1:
        raise ValueError("query_vec must be 1D")
    scores: List[Tuple[str, float]] = []
    for item_id, v in items:
        s = float(np.dot(q, v))
        scores.append((item_id, s))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:k]


def retrieve(
    db: SqliteVectorDB,
    embedder: HashedEmbeddingModel,
    query: str,
    *,
    top_k: int,
    min_score: float,
    max_chunks_scanned: Optional[int] = None,
) -> List[Dict]:
    qv = embedder.embed_texts([query])[0]
    items: List[Tuple[str, np.ndarray]] = []
    scanned = 0
    for (cid, _doc_path, _doc_sha, _chunk_idx, _cs, _ce, _mtime, _text, emb_blob, emb_dim) in db.iter_all_embeddings():
        if emb_dim != embedder.dim:
            continue
        v = np.frombuffer(emb_blob, dtype=np.float32)
        if v.shape != (embedder.dim,):
            continue
        items.append((cid, v))
        scanned += 1
        if max_chunks_scanned is not None and scanned >= max_chunks_scanned:
            break
    ranked = cosine_top_k(qv, items, k=top_k)
    ids = [cid for cid, score in ranked if score >= min_score]
    meta_by_id = db.get_chunks_by_ids(ids)
    out = []
    for cid, score in ranked:
        if score < min_score:
            continue
        m = meta_by_id.get(cid)
        if not m:
            continue
        m = dict(m)
        m["score"] = float(score)
        out.append(m)
    return out


def build_prompt(
    user_query: str,
    retrieved: Sequence[Dict],
    *,
    system_prompt: str,
) -> List[Dict[str, str]]:
    ctx_parts = []
    for i, ch in enumerate(retrieved, start=1):
        header = (
            f"[{i}] doc_path={ch.get('doc_path')} "
            f"chunk_index={ch.get('chunk_index')} "
            f"chars={ch.get('chunk_start')}-{ch.get('chunk_end')} "
            f"sha256={ch.get('doc_sha256')} "
            f"score={ch.get('score'):.4f}"
        )
        ctx_parts.append(header + "\n" + (ch.get("chunk_text") or ""))
    context_block = "\n\n---\n\n".join(ctx_parts) if ctx_parts else "(no retrieved context)"

    developer = (
        "You are an internal knowledge base assistant. "
        "Answer the user using only the retrieved context below. "
        "If the context does not contain the answer, say you don't know and suggest what to search for next. "
        "Cite sources by referring to the bracketed chunk numbers like [1], [2].\n\n"
        "RETRIEVED CONTEXT (verbatim):\n"
        f"{context_block}"
    )
    return [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "developer", "content": developer},
        {"role": "user", "content": user_query.strip()},
    ]


def openai_chat_completion(
    messages: Sequence[Dict[str, str]],
    *,
    model: str,
    temperature: float,
    timeout_s: int,
) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        prompt_preview = json.dumps(list(messages), ensure_ascii=False, indent=2)
        return (
            "OPENAI_API_KEY is not set.\n\n"
            "Constructed prompt messages (JSON):\n"
            f"{prompt_preview}\n"
        )
    url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": list(messages),
        "temperature": float(temperature),
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
    if resp.status_code >= 400:
        return f"OpenAI API error ({resp.status_code}): {resp.text}"
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        return json.dumps(data, ensure_ascii=False, indent=2)


def cmd_index(args: argparse.Namespace) -> int:
    docs_root = Path(args.docs).resolve()
    db_path = args.db
    embedder = HashedEmbeddingModel(dim=args.dim)

    include_ext = {e.lower().strip() for e in (args.include_ext or []) if e.strip()}
    exclude_globs = [g for g in (args.exclude_glob or []) if g.strip()]

    def is_allowed(p: Path) -> bool:
        if include_ext:
            if p.suffix.lower() not in include_ext:
                return False
        if not include_ext:
            if p.suffix.lower() not in TEXT_EXTENSIONS and p.suffix.lower() != ".pdf":
                return False
        rel = str(p.resolve().relative_to(docs_root)).replace("\\", "/")
        for g in exclude_globs:
            if Path(rel).match(g):
                return False
        return True

    all_chunks: List[Chunk] = []
    t0 = time.time()
    files = [p for p in iter_doc_files(docs_root, follow_symlinks=args.follow_symlinks) if is_allowed(p)]
    files.sort(key=lambda p: str(p))
    for p in files:
        try:
            all_chunks.extend(
                build_chunks_for_path(
                    p,
                    docs_root=docs_root,
                    max_bytes=args.max_bytes,
                    chunk_chars=args.chunk_chars,
                    overlap_chars=args.overlap_chars,
                )
            )
        except Exception as e:
            print(f"[WARN] Skipping {p}: {e}", file=sys.stderr)
            continue

    texts = [c.chunk_text for c in all_chunks]
    embeddings = embedder.embed_texts(texts)

    with SqliteVectorDB(db_path) as db:
        wrote = db.upsert_chunks(all_chunks, embeddings)
        total = db.count_chunks()

    dt = time.time() - t0
    print(json.dumps({"indexed_files": len(files), "indexed_chunks": len(all_chunks), "rows_written": wrote, "db_total_chunks": total, "seconds": dt}, indent=2))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    embedder = HashedEmbeddingModel(dim=args.dim)
    with SqliteVectorDB(args.db) as db:
        retrieved = retrieve(
            db,
            embedder,
            args.q,
            top_k=args.top_k,
            min_score=args.min_score,
            max_chunks_scanned=args.max_chunks_scanned,
        )
    print(json.dumps({"query": args.q, "top_k": args.top_k, "min_score": args.min_score, "retrieved": retrieved}, ensure_ascii=False, indent=2))
    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    embedder = HashedEmbeddingModel(dim=args.dim)
    system_prompt = os.environ.get("RAG_SYSTEM_PROMPT", "You are a helpful assistant.").strip()
    model = os.environ.get("RAG_MODEL", "gpt-4o-mini").strip()
    temperature = float(os.environ.get("RAG_TEMPERATURE", str(args.temperature)))
    timeout_s = int(os.environ.get("RAG_TIMEOUT_S", str(args.timeout_s)))

    with SqliteVectorDB(args.db) as db:
        print(f"RAG KB chatbot ready. DB={args.db}  chunks={db.count_chunks()}  model={model}")
        print("Type your question and press Enter. Type ':quit' to exit, ':stats' for DB stats.")
        while True:
            try:
                q = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if not q:
                continue
            if q in {":q", ":quit", "quit", "exit"}:
                return 0
            if q == ":stats":
                print(json.dumps({"db": args.db, "chunks": db.count_chunks(), "dim": args.dim}, indent=2))
                continue

            retrieved = retrieve(
                db,
                embedder,
                q,
                top_k=args.top_k,
                min_score=args.min_score,
                max_chunks_scanned=args.max_chunks_scanned,
            )
            messages = build_prompt(q, retrieved, system_prompt=system_prompt)
            answer = openai_chat_completion(
                messages,
                model=model,
                temperature=temperature,
                timeout_s=timeout_s,
            )
            print("\n" + answer.strip() + "\n")

            if args.show_sources:
                for i, ch in enumerate(retrieved, start=1):
                    print(
                        f"[{i}] score={ch.get('score'):.4f} doc_path={ch.get('doc_path')} chunk_index={ch.get('chunk_index')} chars={ch.get('chunk_start')}-{ch.get('chunk_end')}"
                    )
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rag_kb_chatbot",
        description="Local SQLite RAG knowledge base chatbot (index + retrieve + chat).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_index = sub.add_parser("index", help="Index documents into the vector database.")
    p_index.add_argument("--docs", default=DEFAULT_DOCS_DIR, help="Docs folder to ingest (default: ./docs).")
    p_index.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite DB path (default: ./rag_kb.sqlite3).")
    p_index.add_argument("--dim", type=int, default=DEFAULT_DIM, help="Embedding dimension (default: 2048).")
    p_index.add_argument("--chunk-chars", type=int, default=1800, help="Chunk size in characters.")
    p_index.add_argument("--overlap-chars", type=int, default=200, help="Chunk overlap in characters.")
    p_index.add_argument("--max-bytes", type=int, default=10_000_000, help="Max bytes per file to read (text).")
    p_index.add_argument("--follow-symlinks", action="store_true", help="Follow symlinks while scanning docs.")
    p_index.add_argument("--include-ext", action="append", help="Only ingest these extensions (repeatable), e.g. --include-ext .md")
    p_index.add_argument("--exclude-glob", action="append", help="Exclude files matching glob relative to docs root, e.g. '**/node_modules/**'")
    p_index.set_defaults(func=cmd_index)

    p_query = sub.add_parser("query", help="Run a single retrieval query and print retrieved chunks as JSON.")
    p_query.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite DB path.")
    p_query.add_argument("--dim", type=int, default=DEFAULT_DIM, help="Embedding dimension (must match indexed dim).")
    p_query.add_argument("-q", required=True, help="User query.")
    p_query.add_argument("--top-k", type=int, default=8, help="Number of chunks to retrieve.")
    p_query.add_argument("--min-score", type=float, default=0.10, help="Minimum cosine score to keep a chunk.")
    p_query.add_argument("--max-chunks-scanned", type=int, default=None, help="Optional cap on scanned chunks (debug/perf).")
    p_query.set_defaults(func=cmd_query)

    p_chat = sub.add_parser("chat", help="Interactive chat loop with retrieval and LLM answering.")
    p_chat.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite DB path.")
    p_chat.add_argument("--dim", type=int, default=DEFAULT_DIM, help="Embedding dimension (must match indexed dim).")
    p_chat.add_argument("--top-k", type=int, default=8, help="Number of chunks to retrieve.")
    p_chat.add_argument("--min-score", type=float, default=0.10, help="Minimum cosine score to keep a chunk.")
    p_chat.add_argument("--max-chunks-scanned", type=int, default=None, help="Optional cap on scanned chunks (debug/perf).")
    p_chat.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature.")
    p_chat.add_argument("--timeout-s", type=int, default=60, help="HTTP timeout in seconds.")
    p_chat.add_argument("--show-sources", action="store_true", help="Print retrieved sources after each answer.")
    p_chat.set_defaults(func=cmd_chat)

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

