"""
Real LLM test — calls Groq mixtral-8x7b-32768 with actual HTTP request.
No mocks.
"""
import llm

chunks = [
    {
        "url": "https://example.com/rag",
        "title": "RAG Overview",
        "text": (
            "Retrieval-Augmented Generation (RAG) combines a retrieval system with "
            "a language model. The retriever fetches relevant documents from a vector "
            "store using semantic search. The generator then uses those documents as "
            "context to produce a grounded, accurate answer."
        ),
    },
    {
        "url": "https://example.com/chromadb",
        "title": "ChromaDB",
        "text": (
            "ChromaDB is an open-source vector database that stores embeddings and "
            "supports cosine similarity search. It can run as an in-memory ephemeral "
            "client or a persistent client backed by SQLite."
        ),
    },
]

print("Calling Groq mixtral-8x7b-32768 (real HTTP)...")
response, sources = llm.generate_response(
    query="How does RAG use ChromaDB for retrieval?",
    chunks=chunks,
    memory_context="",
)

print(f"\nResponse:\n{response}")
print(f"\nSources ({len(sources)}):")
for i, s in enumerate(sources, 1):
    print(f"  [{i}] {s['title']} — {s['url']}")

assert isinstance(response, str) and len(response.split()) >= 5, "Response too short"
assert isinstance(sources, list) and len(sources) > 0, "No sources returned"
assert not response.startswith("Error"), f"Got error response: {response}"
print("\nPASS: Real Groq LLM call succeeded")
