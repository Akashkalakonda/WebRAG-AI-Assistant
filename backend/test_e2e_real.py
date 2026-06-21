"""
Full end-to-end pipeline test — real embeddings, real ChromaDB, real Groq LLM.
Only the scraper is replaced with synthetic docs to avoid live SerpAPI calls.
"""
import logging
import unittest.mock as mock
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("e2e_test")

SYNTHETIC_DOCS = [
    {
        "url": "https://example.com/rag-overview",
        "title": "RAG Overview",
        "content": (
            "Retrieval-Augmented Generation (RAG) is an AI technique that combines "
            "information retrieval with language model generation. RAG retrieves relevant "
            "documents from an external knowledge base using semantic search and then uses "
            "those documents as context for the language model to generate accurate, grounded "
            "answers with source citations. This approach reduces hallucination and keeps "
            "responses factually grounded."
        ),
    },
    {
        "url": "https://example.com/chromadb",
        "title": "ChromaDB Vector Store",
        "content": (
            "ChromaDB is an open-source vector database designed for AI applications. "
            "It stores embeddings alongside metadata and supports fast cosine similarity "
            "search. ChromaDB supports both ephemeral in-memory clients and persistent "
            "clients backed by SQLite. It integrates natively with sentence-transformers "
            "and LangChain. Upsert operations allow deduplication by ID."
        ),
    },
    {
        "url": "https://example.com/sentence-transformers",
        "title": "Sentence Transformers",
        "content": (
            "Sentence Transformers are bi-encoder models that encode text into dense "
            "vector representations. The all-MiniLM-L6-v2 model produces 384-dimensional "
            "embeddings and is optimized for semantic similarity tasks. It runs entirely "
            "on CPU and encodes sentences in milliseconds. The model was fine-tuned on "
            "over 1 billion training pairs using contrastive learning objectives."
        ),
    },
]

import rag
import llm
import scraper
import app as flask_app

print("=" * 60)
print("STAGE 1: Chunk")
print("=" * 60)
chunks = rag.chunk_documents(SYNTHETIC_DOCS)
logger.info(f"Produced {len(chunks)} chunks")
assert len(chunks) >= 3
for c in chunks:
    print(f"  {c['id']}  ({len(c['text'])} chars)")
print("PASS\n")

print("=" * 60)
print("STAGE 2: Embed + Store (ChromaDB)")
print("=" * 60)
rag.reset_collection()
rag.embed_and_store(chunks)
count = rag._collection.count()
logger.info(f"ChromaDB collection count: {count}")
assert count == len(chunks), f"Expected {len(chunks)}, got {count}"
print(f"PASS  ({count} vectors stored)\n")

print("=" * 60)
print("STAGE 3: Retrieve")
print("=" * 60)
retrieved = rag.retrieve("How does RAG work with vector databases?", k=5)
logger.info(f"Retrieved {len(retrieved)} chunks")
assert len(retrieved) >= 2
for r in retrieved:
    print(f"  [{r['url'].split('/')[-1]}] {r['text'][:80]!r}")
print("PASS\n")

print("=" * 60)
print("STAGE 4: Real Groq LLM call")
print("=" * 60)
response, sources = llm.generate_response(
    query="How does RAG use ChromaDB for semantic retrieval?",
    chunks=retrieved,
    memory_context="",
)
print(f"\nResponse:\n{response}\n")
print(f"Sources ({len(sources)}):")
for i, s in enumerate(sources, 1):
    print(f"  [{i}] {s['title']} — {s['url']}")
assert not response.startswith("Error"), f"LLM returned error: {response}"
assert len(response.split()) >= 10
assert len(sources) >= 1
print("PASS\n")

print("=" * 60)
print("STAGE 5: Flask /query endpoint (real LLM, synthetic scraper)")
print("=" * 60)
flask_app.app.config["TESTING"] = True
client = flask_app.app.test_client()
rag.reset_collection()
rag.embed_and_store(chunks)

with mock.patch.object(scraper, "search_and_scrape", return_value=SYNTHETIC_DOCS):
    resp = client.post(
        "/query",
        json={"query": "What is RAG and how does it store embeddings?"},
        content_type="application/json",
    )

data = resp.get_json()
print(f"HTTP status: {resp.status_code}")
assert resp.status_code == 200, f"Expected 200, got {resp.status_code}. Body: {data}"
assert "response" in data and "sources" in data
assert not data["response"].startswith("Error")
assert len(data["sources"]) >= 1

print(f"Response ({len(data['response'])} chars):")
print(f"  {data['response'][:300]}")
print(f"\nSources ({len(data['sources'])}):")
for s in data["sources"]:
    print(f"  - {s['title']} | {s['url']}")
print("PASS\n")

print("=" * 60)
print("ALL STAGES PASSED — Phase 1 pipeline fully operational")
print("=" * 60)
print(
    "  LLM:         Groq llama-3.3-70b-versatile  (real HTTP, 200 OK)\n"
    "  Embeddings:  sentence-transformers/all-MiniLM-L6-v2  (CPU)\n"
    "  Vector DB:   ChromaDB PersistentClient\n"
    "  Scraper:     google-search-results GoogleSearch  (mocked for this test)\n"
    "  API:         Flask /query -> {response, sources}\n"
)
