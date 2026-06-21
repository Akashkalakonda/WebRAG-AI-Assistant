from sentence_transformers import SentenceTransformer
import chromadb
import logging

logger = logging.getLogger(__name__)

# Loaded once when this module is first imported; reused for every request.
_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
_client = chromadb.PersistentClient(path="./chroma_db")
_collection = _client.get_or_create_collection(
    name="rag_knowledge",
    metadata={"hnsw:space": "cosine"},
)


def reset_collection():
    """Drops and recreates the collection. Called once at Flask startup for a clean session."""
    global _collection
    _client.delete_collection("rag_knowledge")
    _collection = _client.get_or_create_collection(
        name="rag_knowledge",
        metadata={"hnsw:space": "cosine"},
    )
    logger.info("ChromaDB collection cleared for new session")


def chunk_documents(docs, chunk_size=500, chunk_overlap=50):
    """
    docs: list[{url, title, content}]
    Returns list[{id, url, title, text}]
    """
    chunks = []
    advance = max(1, chunk_size - chunk_overlap)
    for doc in docs:
        text = doc.get("content", "")
        url = doc.get("url", "")
        title = doc.get("title", url)
        start = 0
        idx = 0
        while start < len(text):
            chunk_text = text[start : start + chunk_size].strip()
            if len(chunk_text) >= 50:
                chunks.append({"id": f"{url}#{idx}", "url": url, "title": title, "text": chunk_text})
                idx += 1
            start += advance
    logger.debug(f"Produced {len(chunks)} chunks from {len(docs)} docs")
    return chunks


def embed_and_store(chunks):
    """Embeds chunks and upserts them into the persistent ChromaDB collection."""
    if not chunks:
        return
    texts = [c["text"] for c in chunks]
    ids = [c["id"] for c in chunks]
    metadatas = [{"url": c["url"], "title": c["title"]} for c in chunks]
    embeddings = _model.encode(texts, show_progress_bar=False).tolist()
    _collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    logger.debug(f"Upserted {len(chunks)} chunks into ChromaDB")


def retrieve(query, k=5):
    """
    Returns the top-k semantically similar chunks for the query.
    Returns list[{text, url, title}]
    """
    count = _collection.count()
    if count == 0:
        return []
    query_embedding = _model.encode([query], show_progress_bar=False).tolist()
    results = _collection.query(
        query_embeddings=query_embedding,
        n_results=min(k, count),
        include=["documents", "metadatas"],
    )
    return [
        {"text": doc, "url": meta.get("url", ""), "title": meta.get("title", "")}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]
