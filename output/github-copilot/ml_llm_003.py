#!/usr/bin/env python3

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Tuple
from abc import ABC, abstractmethod
import pickle

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss


class DocumentLoader:
    """Load documents from various sources."""
    
    @staticmethod
    def load_from_text_files(directory: str) -> List[Dict[str, str]]:
        """Load documents from text files in a directory."""
        documents = []
        path = Path(directory)
        
        if not path.exists():
            raise ValueError(f"Directory {directory} does not exist")
        
        for file_path in path.glob("**/*.txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                documents.append({
                    "id": str(file_path.relative_to(path)),
                    "content": content,
                    "source": str(file_path)
                })
        
        return documents
    
    @staticmethod
    def load_from_json(file_path: str) -> List[Dict[str, str]]:
        """Load documents from JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [{"id": k, "content": str(v), "source": file_path} for k, v in data.items()]
        else:
            raise ValueError("JSON must be a list of dicts or a dict of key-value pairs")
    
    @staticmethod
    def load_sample_documents() -> List[Dict[str, str]]:
        """Load sample documents for testing."""
        return [
            {
                "id": "doc1",
                "content": "Our company was founded in 2010 with a mission to revolutionize cloud infrastructure. We have grown from 5 employees to over 500 team members worldwide.",
                "source": "company_history.txt"
            },
            {
                "id": "doc2",
                "content": "We offer three main products: CloudCore for infrastructure management, DataFlow for data processing, and SecureVault for security solutions.",
                "source": "products.txt"
            },
            {
                "id": "doc3",
                "content": "Our customer support team operates 24/7 across multiple time zones. You can reach us via email at support@company.com or through our support portal.",
                "source": "support.txt"
            },
            {
                "id": "doc4",
                "content": "We follow Agile development practices with 2-week sprints. All code goes through peer review before merging to main branch.",
                "source": "development_practices.txt"
            },
            {
                "id": "doc5",
                "content": "Employee benefits include health insurance, 401k matching, remote work flexibility, unlimited PTO, and professional development budgets.",
                "source": "hr_policies.txt"
            },
            {
                "id": "doc6",
                "content": "Data security is our top priority. We use AES-256 encryption for data at rest and TLS 1.3 for data in transit. All systems are audited annually.",
                "source": "security.txt"
            },
            {
                "id": "doc7",
                "content": "Our pricing model is based on usage. Customers pay per compute hour and per GB of data stored. Enterprise plans include dedicated support.",
                "source": "pricing.txt"
            },
            {
                "id": "doc8",
                "content": "We are committed to sustainability. Our data centers use 80% renewable energy and we offset our carbon emissions annually.",
                "source": "sustainability.txt"
            }
        ]


class TextChunker:
    """Split documents into chunks for better retrieval."""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_documents(self, documents: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Split documents into overlapping chunks."""
        chunked = []
        
        for doc in documents:
            content = doc["content"]
            source = doc["source"]
            doc_id = doc["id"]
            
            chunks = self._split_into_chunks(content)
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc_id}_chunk_{i}"
                chunked.append({
                    "id": chunk_id,
                    "content": chunk,
                    "source": source,
                    "original_doc_id": doc_id
                })
        
        return chunked
    
    def _split_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size - self.overlap):
            chunk = " ".join(words[i:i + self.chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks if chunks else [text]


class EmbeddingGenerator:
    """Generate embeddings for documents."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        return self.model.encode([text], show_progress_bar=False)[0]


class VectorStore:
    """Store and retrieve vectors using FAISS."""
    
    def __init__(self, embedding_dim: int = 384):
        self.index = faiss.IndexFlatL2(embedding_dim)
        self.documents = []
        self.embedding_dim = embedding_dim
    
    def add_documents(self, documents: List[Dict[str, str]], embeddings: np.ndarray):
        """Add documents with their embeddings to the index."""
        if len(documents) != len(embeddings):
            raise ValueError("Number of documents and embeddings must match")
        
        self.documents.extend(documents)
        embeddings = embeddings.astype(np.float32)
        self.index.add(embeddings)
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Tuple[Dict[str, str], float]]:
        """Search for similar documents."""
        query_embedding = query_embedding.astype(np.float32).reshape(1, -1)
        distances, indices = self.index.search(query_embedding, k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(self.documents):
                distance = distances[0][i]
                similarity = 1 / (1 + distance)
                results.append((self.documents[int(idx)], float(similarity)))
        
        return results
    
    def save(self, path: str):
        """Save index and documents to disk."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        index_path = path + ".index"
        docs_path = path + ".pkl"
        
        faiss.write_index(self.index, index_path)
        with open(docs_path, "wb") as f:
            pickle.dump(self.documents, f)
    
    def load(self, path: str):
        """Load index and documents from disk."""
        index_path = path + ".index"
        docs_path = path + ".pkl"
        
        if not os.path.exists(index_path) or not os.path.exists(docs_path):
            raise FileNotFoundError(f"Vector store files not found at {path}")
        
        self.index = faiss.read_index(index_path)
        with open(docs_path, "rb") as f:
            self.documents = pickle.load(f)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        pass


class LocalLLMProvider(LLMProvider):
    """Local LLM provider using transformers."""
    
    def __init__(self):
        try:
            from transformers import pipeline
            self.pipeline = pipeline("text-generation", model="gpt2")
        except ImportError:
            raise ImportError("transformers library required for LocalLLMProvider")
    
    def generate(self, prompt: str, max_tokens: int = 200) -> str:
        """Generate text using local LLM."""
        result = self.pipeline(prompt, max_length=max_tokens, num_return_sequences=1)
        return result[0]["generated_text"]


class OpenAILLMProvider(LLMProvider):
    """OpenAI LLM provider."""
    
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo"):
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
            self.model = model
        except ImportError:
            raise ImportError("openai library required for OpenAILLMProvider")
    
    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """Generate text using OpenAI API."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content


class PromptBuilder:
    """Build prompts with retrieved context."""
    
    @staticmethod
    def build_rag_prompt(query: str, retrieved_docs: List[Dict[str, str]]) -> str:
        """Build a RAG prompt with retrieved documents."""
        context = "\n".join([f"Source: {doc['source']}\n{doc['content']}" for doc in retrieved_docs])
        
        prompt = f"""You are a helpful assistant with access to company knowledge.

COMPANY KNOWLEDGE:
{context}

USER QUERY:
{query}

Based on the company knowledge provided above, answer the user's query. If the information is not available in the knowledge base, say so clearly."""
        
        return prompt


class RAGSystem:
    """Complete RAG system."""
    
    def __init__(self, llm_provider: LLMProvider = None, vector_store_path: str = "rag_index"):
        self.embedding_generator = EmbeddingGenerator()
        self.vector_store = VectorStore(embedding_dim=384)
        self.llm_provider = llm_provider or LocalLLMProvider()
        self.vector_store_path = vector_store_path
        self.chunker = TextChunker(chunk_size=500, overlap=50)
    
    def index_documents(self, documents: List[Dict[str, str]]):
        """Index documents for retrieval."""
        chunked_docs = self.chunker.chunk_documents(documents)
        
        texts = [doc["content"] for doc in chunked_docs]
        embeddings = self.embedding_generator.generate_embeddings(texts)
        
        self.vector_store.add_documents(chunked_docs, embeddings)
        print(f"Indexed {len(chunked_docs)} document chunks")
    
    def query(self, query: str, num_results: int = 5, max_tokens: int = 1000) -> Dict:
        """Query the RAG system."""
        query_embedding = self.embedding_generator.generate_embedding(query)
        retrieved_docs = self.vector_store.search(query_embedding, k=num_results)
        
        doc_list = [doc for doc, _ in retrieved_docs]
        
        prompt = PromptBuilder.build_rag_prompt(query, doc_list)
        
        response = self.llm_provider.generate(prompt, max_tokens=max_tokens)
        
        return {
            "query": query,
            "response": response,
            "retrieved_documents": [
                {
                    "id": doc["id"],
                    "source": doc["source"],
                    "content": doc["content"],
                    "similarity": similarity
                }
                for doc, similarity in retrieved_docs
            ]
        }
    
    def save_index(self):
        """Save the vector index to disk."""
        self.vector_store.save(self.vector_store_path)
        print(f"Vector index saved to {self.vector_store_path}")
    
    def load_index(self):
        """Load the vector index from disk."""
        self.vector_store.load(self.vector_store_path)
        print(f"Vector index loaded from {self.vector_store_path}")


def main():
    """Main function to demonstrate RAG system."""
    print("Initializing RAG System...")
    
    rag_system = RAGSystem()
    
    print("\nLoading sample documents...")
    documents = DocumentLoader.load_sample_documents()
    
    print(f"Indexing {len(documents)} documents...")
    rag_system.index_documents(documents)
    
    print("\nRAG System ready. Enter queries (type 'quit' to exit):\n")
    
    sample_queries = [
        "What products do we offer?",
        "How can I contact support?",
        "What are our security practices?",
        "What are the employee benefits?"
    ]
    
    for query in sample_queries:
        print(f"Query: {query}")
        result = rag_system.query(query, num_results=3)
        
        print(f"Response: {result['response'][:500]}...")
        print(f"\nRetrieved Documents:")
        for doc in result['retrieved_documents']:
            print(f"  - {doc['source']} (similarity: {doc['similarity']:.3f})")
        print()
    
    interactive_mode = True
    if interactive_mode:
        print("\n--- Interactive Mode ---")
        while True:
            try:
                user_query = input("Enter query (or 'quit'): ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            
            if user_query.lower() == 'quit':
                break
            
            if not user_query:
                continue
            
            result = rag_system.query(user_query, num_results=3)
            print(f"\nResponse: {result['response']}\n")
            print("Retrieved Documents:")
            for doc in result['retrieved_documents']:
                print(f"  - {doc['source']} (similarity: {doc['similarity']:.3f})")
                print(f"    Content: {doc['content'][:200]}...\n")


if __name__ == "__main__":
    main()