# RAG Chatbot — Migration Roadmap

## 1. Current Architecture

```
User (Streamlit frontend)
  └─ HTTP POST http://localhost:5001/query
       └─ Flask backend (backend/app.py)
            ├─ search_and_scrape(query)         ← scraper.py
            │    ├─ SerpAPI → Google Search
            │    └─ BeautifulSoup → raw HTML scrape (up to 5 URLs)
            ├─ generate_response(query, context) ← llm.py
            │    ├─ HuggingFace InferenceClient (Mixtral-8x7B)
            │    └─ context hard-truncated to first 4,000 chars
            └─ ConversationBufferMemory (in-process, volatile)
```

**File inventory**

| File | Role |
|---|---|
| `backend/app.py` | Flask server, single `/query` endpoint |
| `backend/scraper.py` | SerpAPI search + BeautifulSoup scrape |
| `backend/llm.py` | HuggingFace Mixtral inference + prompt building |
| `frontend/app.py` | Streamlit chat UI |
| `backend/requirements.txt` | Python dependencies (unpinned) |
| `backend/.env` | API keys (plaintext, not gitignored) |

---

## 2. Strengths

- **Decoupled frontend/backend** — Streamlit and Flask are separate processes; swapping either is straightforward.
- **Retry logic in LLM calls** — `llm.py` retries up to 3 times with exponential delay, preventing transient API failures from surfacing to the user.
- **Wikipedia fallback** — `scraper.py` falls back to Wikipedia when primary scrape yields insufficient content, improving recall for sparse topics.
- **User-agent rotation** — reduces the probability of being blocked by basic bot-detection on target sites.
- **Memory scaffolding exists** — LangChain `ConversationBufferMemory` is already imported, providing a starting point for multi-turn conversations.
- **Logging throughout** — DEBUG-level logs are present in all three backend modules, which aids local debugging.

---

## 3. Weaknesses

### Not true RAG
The system does not embed, index, or semantically retrieve anything. It concatenates raw scraped text and hard-truncates it to 4,000 characters before passing it to the LLM. This is "retrieve-by-keyword, inject-everything" — the opposite of retrieval-augmented generation.

### Broken memory
`ConversationBufferMemory` is instantiated as a **module-level global** in both `backend/app.py` (line 19) and `backend/llm.py` (line 15). These are two separate objects; the memory saved in `app.py` is never read, and the one in `llm.py` is never shared with `app.py`. Memory is also entirely in-process and is lost on every restart.

### Naive context injection
Scraped content is joined into one string and truncated at a hard byte boundary (10,000 chars from scraper, then 4,000 chars in the prompt). There is no relevance ranking, no chunking, and no semantic filtering. The most relevant content may be after the cutoff point.

### Hardcoded year
`scraper.py` (line 29) and `llm.py` (line 27) check for the literal string `"2025"` to detect current-affairs queries. This logic broke on 2026-01-01.

### Duplicate and wasted retries in scraper
The `alt_headers` dict in `scraper.py` (lines 67–73) is identical to `headers` (lines 47–52). The retry sends the exact same request to the same URL — it will fail for the same reasons.

### InferenceClient re-instantiated per request
A new `InferenceClient` object is created on every call to `generate_response`. This adds unnecessary overhead and no connection pooling.

### Response length cap
`max_new_tokens=200` (llm.py line 50) produces very short answers, which is inadequate for complex queries. It also forces the prompt to artificially constrain the answer to "1-2 sentences".

### No streaming
The entire LLM response is generated before anything is returned to the user. For a model like Mixtral accessed via HuggingFace Inference API, this creates a significant latency wall.

### No source citations
The frontend never receives or displays which URLs the answer was derived from.

### Unpinned dependencies
`requirements.txt` lists no versions. LangChain's API changed significantly between v0.1, v0.2, and v0.3, making this fragile on any fresh install.

---

## 4. Security Issues

### CRITICAL — Live API keys committed in plaintext
`backend/.env` contains live `SERPAPI_KEY` and `HUGGINGFACE_API_KEY` values. If this directory is ever pushed to a git remote, these keys will be permanently exposed in git history even if later deleted. **Rotate both keys immediately and add `.env` to `.gitignore`.**

### Flask debug mode in production
`app.run(debug=True)` (backend/app.py line 44) enables the Werkzeug interactive debugger. If an unhandled exception occurs in a reachable environment, this exposes a browser-based Python REPL — equivalent to **remote code execution**.

### No authentication on `/query`
The endpoint is open to any caller. There is no API key, session token, or any other access control. Anyone who can reach port 5001 can query the LLM and incur API costs.

### No rate limiting
A single client can send thousands of requests per second, exhausting SerpAPI and HuggingFace quotas and causing a denial-of-service by cost.

### No input validation
`user_query = data.get('query')` (backend/app.py line 24) is passed directly to the scraper and LLM with no length check, type check, or sanitization. A null value will cause an unhandled exception; an extremely long string could inflate API costs.

### Internal error details leaked
`return jsonify({"error": str(e)}), 500` (backend/app.py line 41) returns raw Python exception messages — including stack traces in some cases — to the client. This leaks internal implementation details.

### No CORS policy
Flask has no CORS configuration. In a browser context this is not a restriction issue but it also means no intentional restriction is in place for cross-origin callers.

### Web scraping without consent
Rotating user agents to bypass bot detection may violate the Terms of Service of scraped sites and, in some jurisdictions, computer fraud statutes.

---

## 5. Scalability Issues

| Issue | Impact |
|---|---|
| In-process volatile memory | Horizontal scaling is impossible; each replica has its own disconnected conversation state |
| Synchronous serial scraping | Each request blocks while scraping 5 URLs sequentially; P99 latency is ~5× per-URL scrape time |
| No vector store | Semantic retrieval cannot be added without one; keyword-only search does not scale to large corpora |
| No caching | Identical queries re-run the full SerpAPI + scrape + LLM pipeline every time |
| No worker queue | Long-running scrape + inference tasks block the Flask request thread |
| Streamlit for multi-user | Streamlit's session model is not designed for concurrent multi-user production workloads |
| Flask dev server | Single-threaded by default; not suitable beyond one concurrent user |
| No persistent storage | Conversation history, scraped content, and embeddings are all ephemeral |

---

## 6. Migration Roadmap

The migration is structured into four phases. Each phase is independently deployable and delivers incremental value. **Do not begin any phase until the previous phase is complete and tested.**

---

### Phase 0 — Security hardening (prerequisite, 1–2 days)

This must be completed before any other work.

**0.1 Rotate exposed API keys**
- Revoke current `SERPAPI_KEY` and `HUGGINGFACE_API_KEY` on their respective platforms.
- Generate new keys and store them only in environment variables or a secrets manager — never in files.

**0.2 Gitignore and secrets hygiene**
- Add `.env`, `*.env`, `__pycache__/`, and `*.pyc` to `.gitignore`.
- If a git remote exists, audit history for any previously committed secrets.

**0.3 Disable Flask debug mode**
- Replace `app.run(debug=True)` with `debug=os.getenv("FLASK_DEBUG", "false").lower() == "true"`.

**0.4 Pin all dependencies**
- Run `pip freeze > requirements.txt` in a clean virtual environment to lock all transitive dependencies.

---

### Phase 1 — True RAG backend (1–2 weeks)

Replace the "scrape-and-truncate" pipeline with a proper retrieve-embed-generate loop.

**1.1 Document ingestion pipeline**
- On each search, chunk scraped content into overlapping segments (e.g., 512 tokens, 50-token overlap) using a token-aware chunker (LangChain's `RecursiveCharacterTextSplitter` or LlamaIndex's `SentenceSplitter`).
- Tag each chunk with its source URL, scrape timestamp, and position index.

**1.2 Vector store**
- Stand up a vector database. For a local/free start use **ChromaDB** (embedded); for production use **Pinecone** or **Weaviate**.
- Embed chunks using **`sentence-transformers/all-MiniLM-L6-v2`** (free, runs locally, 384 dimensions) or the HuggingFace Inference API embedding endpoint to avoid a separate model server.

**1.3 Semantic retrieval**
- On each user query, embed the query with the same model and retrieve the top-k (k=5–10) most similar chunks by cosine similarity.
- Replace the hard-truncated string concatenation with these ranked, relevant chunks.

**1.4 Source citations**
- The `/query` response JSON must include a `sources` array: `[{ "url": "...", "title": "...", "chunk": "..." }]`.
- The LLM prompt must instruct the model to reference sources by index: "According to [1]...".

**1.5 Unified memory**
- Remove the duplicate `ConversationBufferMemory` instances.
- Store conversation history in a database (PostgreSQL or Redis) keyed by `session_id`.
- Pass `session_id` from the frontend on every request.

**1.6 Switch to a production WSGI server**
- Replace Flask's built-in dev server with **Gunicorn** (`gunicorn -w 4 app:app`).
- Add **Flask-Limiter** for rate limiting (e.g., 20 requests/minute per IP).
- Add input validation: enforce query length limits and reject null/empty queries.

**1.7 Fix scraper retry logic**
- On HTTP 403/406, actually change the request strategy (e.g., switch to a headless browser or a different proxy), not just re-send the same headers.
- Add concurrent scraping with `asyncio` + `aiohttp` to parallelize the 5-URL fetch.

---

### Phase 2 — Streaming and LLM upgrade (1 week)

**2.1 Streaming LLM responses**
- Switch from `client.text_generation()` (blocking) to the streaming variant.
- Expose a `/stream` SSE (Server-Sent Events) endpoint in Flask that yields tokens as they arrive.
- Consider migrating from HuggingFace Inference API to the **Claude API** (Anthropic) or **OpenAI API** for more reliable streaming, better quality, and higher token limits. Both support streaming natively.

**2.2 Increase response quality**
- Remove the "1-2 sentences" constraint and the 200-token cap.
- Set `max_new_tokens` to 1024–2048 depending on the chosen model.
- Move system instructions out of the user prompt and into a proper system message (required for instruction-tuned models).

**2.3 Caching layer**
- Add **Redis** to cache: (a) SerpAPI results keyed by query hash, (b) embedding vectors for repeated queries, (c) scraped content by URL + date.
- Set TTL of 1 hour for news content, 24 hours for stable content.

---

### Phase 3 — Frontend migration to Next.js (1–2 weeks)

**3.1 Scaffold Next.js app**
- Initialize a Next.js 14+ app (App Router) in a `frontend/` directory.
- Use **TypeScript** throughout.
- Use **Tailwind CSS** for styling.

**3.2 Chat UI**
- Implement a chat interface with: message history, user/assistant bubbles, a streaming response display (consume the SSE `/stream` endpoint token-by-token), and a loading state.
- Display source citations as expandable cards below each assistant message, showing URL, title, and the relevant excerpt.

**3.3 Session management**
- Generate a `session_id` (UUID) on first load, stored in `localStorage`.
- Send `session_id` with every API request to maintain per-user conversation history.

**3.4 API route layer**
- Use Next.js API routes to proxy requests to the Flask backend, adding authentication headers server-side so keys are never exposed to the browser.

**3.5 Environment configuration**
- Store the Flask backend URL in `NEXT_PUBLIC_API_URL` (for client-side fetches) and `API_URL` (for server-side proxy routes).

---

### Phase 4 — Production deployment on Vercel (3–5 days)

**4.1 Backend containerization**
- Write a `Dockerfile` for the Flask backend.
- Deploy to **Railway**, **Fly.io**, or **Google Cloud Run** (Vercel does not support long-running Python servers).
- Use managed **PostgreSQL** (Railway, Supabase, or Neon) for conversation history.
- Use managed **Redis** (Upstash) for caching.
- Use **Pinecone** (serverless tier) for the vector store.

**4.2 Frontend deployment**
- Connect the Next.js frontend repo to Vercel.
- Set all environment variables in the Vercel dashboard (never in committed files).
- Configure the backend URL in Vercel's environment variables.

**4.3 Authentication**
- Add **Clerk** or **NextAuth.js** to the Next.js frontend for user auth.
- Protect the Flask `/query` and `/stream` endpoints with a bearer token validated against Clerk's JWKS endpoint.

**4.4 Observability**
- Add structured JSON logging to Flask (replace `logging.basicConfig` with `python-json-logger`).
- Add **Sentry** error tracking to both Flask and Next.js.
- Add a `/health` endpoint to Flask that returns database and vector store connectivity status.

**4.5 CI/CD**
- Add a GitHub Actions workflow that: runs tests on PR, lints code, builds the Docker image and deploys to the backend host on merge to `main`, and triggers a Vercel deploy for the frontend.

---

## 7. Target Architecture (post-migration)

```
Browser (Next.js on Vercel)
  └─ API Route (Next.js server-side proxy)
       └─ Flask API (Gunicorn on Railway/Fly.io)
            ├─ Rate Limiter (Flask-Limiter)
            ├─ Auth (Clerk JWT verification)
            ├─ /query  ──► RAG Pipeline
            │               ├─ SerpAPI search
            │               ├─ Async scrape (aiohttp)
            │               ├─ Chunk + embed (sentence-transformers)
            │               ├─ Upsert to Pinecone
            │               ├─ Semantic retrieval (top-k chunks)
            │               └─ LLM (Claude/GPT-4 with streaming)
            ├─ /stream ──► SSE token stream to browser
            └─ Session memory ──► PostgreSQL (per session_id)
                                   Redis (query + embedding cache)
```

---

## 8. Phase Summary

| Phase | Scope | Effort | Unlocks |
|---|---|---|---|
| 0 | Security hardening | 1–2 days | Safe to continue development |
| 1 | True RAG backend | 1–2 weeks | Semantic retrieval, citations, persistent memory |
| 2 | Streaming + LLM upgrade | 1 week | Real-time responses, better quality, caching |
| 3 | Next.js frontend | 1–2 weeks | Production-grade UI, source display, streaming UX |
| 4 | Vercel deployment | 3–5 days | Publicly accessible, authenticated, observable |

**Total estimated effort: 4–7 weeks** for a single developer working full-time.

---

## 9. Immediate Action Items (before writing any code)

1. **Rotate the SERPAPI_KEY and HUGGINGFACE_API_KEY** — the values currently in `backend/.env` are live and should be considered compromised if this directory has ever been synced, shared, or pushed anywhere.
2. **Add `.env` to `.gitignore`** before initializing a git repository.
3. **Decide on the production LLM** — HuggingFace Inference API for Mixtral is rate-limited and slow for production; Claude API or OpenAI API offer streaming, higher limits, and significantly better instruction following.
4. **Decide on the vector store** — ChromaDB (local, free, no infra) for development; Pinecone serverless for production.
5. **Approve this roadmap** before any code changes are made (per project instructions).
