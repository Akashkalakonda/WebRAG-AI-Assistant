print("APP.PY STARTED", flush=True)
from flask import Flask, request, jsonify, Response, stream_with_context
print("FLASK IMPORTED", flush=True)
from scraper import search_and_scrape
print("SCRAPER IMPORTED", flush=True)
from llm import generate_response, generate_stream
print("LLM IMPORTED", flush=True)
from langchain.memory import ConversationBufferMemory
import rag
print("RAG IMPORTED", flush=True)
import logging
import os
import json
from dotenv import load_dotenv

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

load_dotenv()
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')

memory = ConversationBufferMemory()

@app.route('/query', methods=['POST'])
def query():
    try:
        data = request.get_json()
        user_query = data.get('query')
        if not user_query or not isinstance(user_query, str):
            return jsonify({"error": "query must be a non-empty string"}), 400
        user_query = user_query.strip()[:1000]
        logger.info(f"Received query: {user_query}")

        # Step 1: Search and scrape
        docs = search_and_scrape(user_query)
        logger.debug(f"Scraped {len(docs)} documents")

        # Step 2: Chunk and embed into ChromaDB
        chunks = rag.chunk_documents(docs)
        rag.embed_and_store(chunks)

        # Step 3: Retrieve semantically relevant chunks
        retrieved = rag.retrieve(user_query, k=5)
        logger.debug(f"Retrieved {len(retrieved)} chunks")

        # Step 4: Generate response with memory context
        memory_context = memory.load_memory_variables({}).get("history", "")
        response, sources = generate_response(user_query, retrieved, memory_context)

        # Step 5: Update memory
        memory.save_context({"input": user_query}, {"output": response})

        return jsonify({
            "response": response,
            "sources": sources,
            "stats": {
                "sources_searched": len(docs),
                "pages_scraped": len(docs),
                "chunks_created": len(chunks),
                "chunks_retrieved": len(retrieved),
                "model": "llama-3.3-70b-versatile",
            },
        })
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/query/stream', methods=['POST'])
def query_stream():
    data = request.get_json()
    user_query = (data.get('query') or '').strip()[:1000]
    if not user_query:
        return jsonify({"error": "query must be a non-empty string"}), 400

    def _generate():
        try:
            yield json.dumps({"type": "status", "stage": "searching"}) + "\n"
            docs = search_and_scrape(user_query)

            yield json.dumps({"type": "status", "stage": "processing"}) + "\n"
            chunks = rag.chunk_documents(docs)

            yield json.dumps({"type": "status", "stage": "embedding"}) + "\n"
            rag.embed_and_store(chunks)

            yield json.dumps({"type": "status", "stage": "retrieving"}) + "\n"
            retrieved = rag.retrieve(user_query, k=5)

            memory_context = memory.load_memory_variables({}).get("history", "")

            seen_urls, sources = set(), []
            for chunk in retrieved:
                if chunk["url"] not in seen_urls:
                    seen_urls.add(chunk["url"])
                    sources.append({"url": chunk["url"], "title": chunk["title"]})

            stats = {
                "sources_searched": len(docs),
                "pages_scraped":    len(docs),
                "chunks_created":   len(chunks),
                "chunks_retrieved": len(retrieved),
                "model":            "llama-3.3-70b-versatile",
            }
            yield json.dumps({"type": "meta", "sources": sources, "stats": stats}) + "\n"

            yield json.dumps({"type": "status", "stage": "generating"}) + "\n"

            full_response = ""
            for token in generate_stream(user_query, retrieved, memory_context):
                full_response += token
                yield json.dumps({"type": "token", "data": token}) + "\n"

            memory.save_context({"input": user_query}, {"output": full_response})
            yield json.dumps({"type": "done"}) + "\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield json.dumps({"type": "error", "message": str(e)}) + "\n"

    return Response(
        stream_with_context(_generate()),
        content_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


if __name__ == '__main__':
    if os.getenv("RESET_CHROMA", "false").lower() == "true":
        rag.reset_collection()

    port = int(os.getenv("PORT", 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
    print("STARTING FLASK SERVER", flush=True)
