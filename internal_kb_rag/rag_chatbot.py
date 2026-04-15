#!/usr/bin/env python3
import argparse
import os
import sys
import uuid
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI

DEFAULT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
EMBED_MODEL = os.environ.get("RAG_EMBED_MODEL", "all-MiniLM-L6-v2")
CHROMA_PATH = os.environ.get("RAG_CHROMA_PATH", "./chroma_db")
COLLECTION_NAME = os.environ.get("RAG_COLLECTION", "company_kb")
CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", "120"))
TOP_K = int(os.environ.get("RAG_TOP_K", "8"))
TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunks.append(text[start:end])
        if end >= n:
            break
        next_start = end - overlap
        if next_start <= start:
            next_start = start + 1
        start = next_start
    return chunks


def iter_document_files(root: Path) -> list[Path]:
    files = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in TEXT_EXTENSIONS:
            files.append(p)
    return files


def read_file_safe(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def get_collection(persist_dir: str, collection_name: str):
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    client = chromadb.PersistentClient(path=persist_dir)
    return client.get_or_create_collection(name=collection_name, embedding_function=ef)


def cmd_ingest(args: argparse.Namespace) -> None:
    root = Path(args.documents_dir).resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        sys.exit(1)
    collection = get_collection(args.chroma_path, args.collection)
    files = iter_document_files(root)
    if not files:
        print(f"No documents found under {root} ({', '.join(sorted(TEXT_EXTENSIONS))})", file=sys.stderr)
        sys.exit(1)
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []
    for fp in files:
        rel = str(fp.relative_to(root))
        body = read_file_safe(fp)
        parts = chunk_text(body, args.chunk_size, args.chunk_overlap)
        for i, part in enumerate(parts):
            ids.append(f"{rel}::{i}::{uuid.uuid4().hex[:12]}")
            documents.append(part)
            metadatas.append({"source": rel, "chunk_index": i})
    batch = 100
    for i in range(0, len(documents), batch):
        collection.add(
            ids=ids[i : i + batch],
            documents=documents[i : i + batch],
            metadatas=metadatas[i : i + batch],
        )
    print(f"Ingested {len(documents)} chunks from {len(files)} files into {args.chroma_path}")


def build_context_from_results(documents: list[str], metadatas: list[dict]) -> str:
    blocks = []
    for idx, doc in enumerate(documents):
        meta = metadatas[idx] if idx < len(metadatas) else {}
        src = meta.get("source", "unknown")
        ci = meta.get("chunk_index", "")
        blocks.append(f"--- Document {idx + 1} (source: {src}, chunk: {ci}) ---\n{doc}")
    return "\n\n".join(blocks)


def cmd_query(args: argparse.Namespace) -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)
    collection = get_collection(args.chroma_path, args.collection)
    total = collection.count()
    if total == 0:
        print("The vector database is empty. Run ingest first.", file=sys.stderr)
        sys.exit(1)
    n_results = min(args.top_k, total)
    res = collection.query(query_texts=[args.question], n_results=n_results, include=["documents", "metadatas"])
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    context = build_context_from_results(docs, metas)
    client = OpenAI()
    system = (
        "You are an internal company knowledge assistant. Answer using only the context below. "
        "If the context is insufficient, say so and suggest what information might be missing."
    )
    user = f"Context from company documents:\n\n{context}\n\nUser question: {args.question}"
    completion = client.chat.completions.create(
        model=args.model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=args.temperature,
    )
    answer = completion.choices[0].message.content or ""
    print(answer)


def cmd_clear(args: argparse.Namespace) -> None:
    client = chromadb.PersistentClient(path=args.chroma_path)
    try:
        client.delete_collection(args.collection)
    except Exception:
        pass
    print(f"Deleted collection {args.collection!r} (if it existed).")


def main() -> None:
    p = argparse.ArgumentParser(description="Internal KB RAG: ingest documents and query with retrieval + LLM.")
    p.add_argument("--chroma-path", default=CHROMA_PATH, help="Chroma persistence directory")
    p.add_argument("--collection", default=COLLECTION_NAME, help="Collection name")
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("ingest", help="Load documents from a folder into the vector store")
    pi.add_argument("documents_dir", help="Root folder containing .txt and .md files")
    pi.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    pi.add_argument("--chunk-overlap", type=int, default=CHUNK_OVERLAP)
    pi.set_defaults(func=cmd_ingest)

    pq = sub.add_parser("query", help="Retrieve context and answer with the LLM")
    pq.add_argument("question", help="User question")
    pq.add_argument("--top-k", type=int, default=TOP_K, help="Number of chunks to retrieve (all included in prompt)")
    pq.add_argument("--model", default=DEFAULT_MODEL)
    pq.add_argument("--temperature", type=float, default=0.2)
    pq.set_defaults(func=cmd_query)

    pc = sub.add_parser("clear", help="Remove the collection from the local Chroma store")
    pc.set_defaults(func=cmd_clear)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
