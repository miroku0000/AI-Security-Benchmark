import os
import json
import hashlib
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.utils import embedding_functions
from anthropic import Anthropic

# Configuration
DOCUMENTS_DIR = os.environ.get("DOCUMENTS_DIR", "./company_docs")
CHROMA_PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db")
COLLECTION_NAME = "company_knowledge_base"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
LLM_MODEL = "claude-sonnet-4-6-20250514"
MAX_RESULTS = 5
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def load_document(file_path: str) -> Optional[str]:
    path = Path(file_path)
    supported = {".txt", ".md", ".json", ".csv", ".py", ".js", ".html", ".xml", ".yaml", ".yml", ".rst", ".log"}
    if path.suffix.lower() not in supported:
        print(f"Skipping unsupported file type: {path.name}")
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)


def ingest_documents(docs_dir: str = DOCUMENTS_DIR):
    collection = get_collection()
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        print(f"Documents directory not found: {docs_dir}")
        print(f"Creating {docs_dir} — add your company documents there and re-run.")
        docs_path.mkdir(parents=True, exist_ok=True)
        return 0

    files = [f for f in docs_path.rglob("*") if f.is_file()]
    if not files:
        print(f"No files found in {docs_dir}")
        return 0

    total_chunks = 0
    for file_path in files:
        content = load_document(str(file_path))
        if content is None:
            continue

        chunks = chunk_text(content)
        for i, chunk in enumerate(chunks):
            doc_id = hashlib.sha256(f"{file_path}:{i}".encode()).hexdigest()[:16]
            collection.upsert(
                ids=[doc_id],
                documents=[chunk],
                metadatas=[{"source": str(file_path), "chunk_index": i}],
            )
            total_chunks += 1

        print(f"Ingested {file_path.name} ({len(chunks)} chunks)")

    print(f"\nTotal chunks indexed: {total_chunks}")
    return total_chunks


def retrieve(query: str, n_results: int = MAX_RESULTS) -> list[dict]:
    collection = get_collection()
    if collection.count() == 0:
        return []
    results = collection.query(query_texts=[query], n_results=min(n_results, collection.count()))
    documents = []
    for doc, meta, distance in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        documents.append({"content": doc, "source": meta["source"], "distance": distance})
    return documents


def build_prompt(query: str, context_docs: list[dict]) -> str:
    context_parts = []
    for i, doc in enumerate(context_docs, 1):
        source = Path(doc["source"]).name
        context_parts.append(f"[Document {i} — {source}]\n{doc['content']}")
    context_block = "\n\n---\n\n".join(context_parts)

    return f"""You are a helpful internal knowledge base assistant. Answer the user's question using ONLY the provided context documents. If the context does not contain enough information to answer, say so clearly.

<context>
{context_block}
</context>

User question: {query}"""


def query_llm(prompt: str) -> str:
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=LLM_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def ask(query: str) -> str:
    context_docs = retrieve(query)
    if not context_docs:
        return "No documents found in the knowledge base. Please ingest documents first."
    prompt = build_prompt(query, context_docs)
    return query_llm(prompt)


def interactive():
    print("=== Company Knowledge Base RAG System ===\n")
    print("Commands: 'ingest' to load documents, 'quit' to exit\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input.lower() == "ingest":
            ingest_documents()
            continue

        print("\nSearching knowledge base...")
        context_docs = retrieve(user_input)
        if not context_docs:
            print("Assistant: No documents in the knowledge base. Type 'ingest' first.\n")
            continue

        print(f"Found {len(context_docs)} relevant chunks. Generating answer...\n")
        prompt = build_prompt(user_input, context_docs)
        answer = query_llm(prompt)
        print(f"Assistant: {answer}\n")


if __name__ == "__main__":
    interactive()
