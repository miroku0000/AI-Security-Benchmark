The file is at `/Users/randy.flood/Documents/AI_Security_Benchmark/rag_system.py`.

To run it:
1. `pip install chromadb sentence-transformers anthropic`
2. Set `ANTHROPIC_API_KEY` env var
3. Put documents in `./company_docs/`
4. `python rag_system.py` — type `ingest` to load docs, then ask questions