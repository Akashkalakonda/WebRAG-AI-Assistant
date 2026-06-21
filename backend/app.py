from flask import Flask, request, jsonify
from scraper import search_and_scrape
from llm import generate_response
from langchain.memory import ConversationBufferMemory
import rag
import logging
import os
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

        return jsonify({"response": response, "sources": sources})
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    rag.reset_collection()
    app.run(host='0.0.0.0', port=5001, debug=True)
