# WebRAG Chatbot

A web-search-grounded RAG (Retrieval-Augmented Generation) assistant. For any user query it searches the web, scrapes source pages, embeds the content into a vector store, retrieves the most semantically relevant chunks, and generates a cited answer using an LLM.

## Architecture (Phase 1)

```
User Query
  └─► SerpAPI (Google Search)
        └─► BeautifulSoup scrape (up to 5 URLs)
              └─► Chunk (500-char overlapping windows)
                    └─► Embed (all-MiniLM-L6-v2, 384-dim)
                          └─► ChromaDB (cosine similarity index)
                                └─► Top-5 semantic retrieval
                                      └─► Groq LLM (llama-3.3-70b-versatile)
                                            └─► Response + source citations
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | Flask |
| Frontend UI | Streamlit |
| Web Search | SerpAPI (Google Search) |
| Web Scraping | BeautifulSoup4 |
| Embeddings | sentence-transformers / all-MiniLM-L6-v2 |
| Vector Store | ChromaDB (persistent) |
| LLM | Groq — llama-3.3-70b-versatile |
| Conversation Memory | LangChain ConversationBufferMemory |

## Project Structure

```
RAG based Chatbot/
├── backend/
│   ├── app.py              # Flask server — /query endpoint, pipeline orchestration
│   ├── scraper.py          # SerpAPI search + BeautifulSoup scrape
│   ├── rag.py              # Chunking, embedding, ChromaDB storage, retrieval
│   ├── llm.py              # Groq LLM call, prompt construction, source deduplication
│   ├── requirements.txt    # Python dependencies
│   ├── .env.example        # Environment variable template
│   ├── test_e2e_real.py    # End-to-end pipeline test (real LLM)
│   └── test_llm_groq.py    # LLM unit test
├── frontend/
│   └── app.py              # Streamlit chat UI
├── ROADMAP.md              # Full migration roadmap (Phases 0–4)
├── PHASE1_PLAN.md          # Detailed Phase 1 implementation plan
└── CLAUDE.md               # Project instructions
```

## Setup

### Prerequisites

- Python 3.12
- Conda (recommended) or any Python virtual environment
- A [SerpAPI](https://serpapi.com) key (free tier: 100 searches/month)
- A [Groq](https://console.groq.com) API key (free tier)

### 1. Create and activate environment

```bash
conda create -n ragproject python=3.12
conda activate ragproject
```

### 2. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and fill in your keys:

```
SERPAPI_KEY=your_serpapi_key_here
GROQ_API_KEY=your_groq_api_key_here
```

### 4. Run the backend

```bash
cd backend
python app.py
```

The Flask server starts on `http://localhost:5001`.

### 5. Run the frontend

In a separate terminal:

```bash
conda activate ragproject
streamlit run frontend/app.py
```

Open `http://localhost:8501` in your browser.

## API

### POST /query

**Request**
```json
{ "query": "What is retrieval-augmented generation?" }
```

**Response**
```json
{
  "response": "RAG combines information retrieval with LLM generation [1]. ...",
  "sources": [
    { "url": "https://example.com/rag", "title": "RAG Overview" }
  ]
}
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SERPAPI_KEY` | Yes | SerpAPI key for Google Search |
| `GROQ_API_KEY` | Yes | Groq API key for LLM inference |
| `HUGGINGFACE_API_KEY` | No | Legacy — not currently used |

## Running Tests

```bash
cd backend
python test_e2e_real.py   # Full pipeline: chunk → embed → retrieve → LLM
python test_llm_groq.py   # LLM unit test only
```

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full four-phase migration plan:

| Phase | Goal | Status |
|---|---|---|
| 0 | Security hardening | Complete |
| 1 | True RAG backend | **Complete** |
| 2 | Streaming responses, async scraping, caching | Planned |
| 3 | Next.js frontend | Planned |
| 4 | Vercel deployment | Planned |
