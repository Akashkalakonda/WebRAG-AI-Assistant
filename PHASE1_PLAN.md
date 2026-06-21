# Phase 1 Implementation Plan — True RAG Backend

## 1. Updated Architecture

### Before (current)

```
User Query
  → search_and_scrape(query)
       → SerpAPI
       → BeautifulSoup scrape (up to 5 URLs)
       → concatenate all text → truncate to 10,000 chars → return string
  → generate_response(query, string)
       → hard-truncate string to 4,000 chars
       → inject as flat context into prompt
       → Mixtral via HuggingFace
       → return string
  → return {"response": string}
```

### After (Phase 1)

```
User Query
  → search_and_scrape(query)
       → SerpAPI
       → BeautifulSoup scrape (up to 5 URLs)
       → return list[{url, title, content}]           ← structured output
  → chunk_documents(docs)
       → split each document into 500-char overlapping chunks
       → return list[{id, url, title, text, chunk_index}]
  → build_collection(chunks)
       → embed each chunk with all-MiniLM-L6-v2
       → store in ephemeral ChromaDB collection
       → return collection handle
  → retrieve(query, collection, k=5)
       → embed query with same model
       → cosine similarity search
       → return top-5 list[{text, url, title}]
  → generate_response(query, retrieved_chunks, memory_context)
       → build numbered source prompt: [1] chunk... [2] chunk...
       → Mixtral via HuggingFace
       → return (response_text, deduplicated_sources)
  → return {"response": string, "sources": [{url, title}]}
```

---

## 2. Updated File Structure

```
RAG based Chatbot/
├── backend/
│   ├── app.py              ← MODIFY
│   ├── scraper.py          ← MODIFY
│   ├── llm.py              ← MODIFY
│   ├── chunker.py          ← CREATE (new)
│   ├── vector_store.py     ← CREATE (new)
│   ├── requirements.txt    ← MODIFY
│   └── .env
├── frontend/
│   └── app.py              ← MODIFY
├── CLAUDE.md
├── ROADMAP.md
└── PHASE1_PLAN.md
```

**5 files modified, 2 files created, 0 files deleted.**

---

## 3. New Dependencies

| Package | Version constraint | Purpose |
|---|---|---|
| `chromadb` | `>=0.4.0` | Vector store (ephemeral in-memory client) |
| `sentence-transformers` | `>=2.2.0` | `all-MiniLM-L6-v2` embedding model |

No other new packages are required. All other new functionality uses packages already in `requirements.txt` (`langchain`, `requests`, `beautifulsoup4`).

Note: `sentence-transformers` will pull in `torch` and `transformers` as transitive dependencies. The first run will download the `all-MiniLM-L6-v2` model (~90 MB) and cache it locally.

---

## 4. Files to Create

### `backend/chunker.py`

**Purpose:** Split raw document text into overlapping chunks. No external API calls. Stateless.

**Inputs:** `list[dict]` — each dict has keys `url` (str), `title` (str), `content` (str).

**Outputs:** `list[dict]` — each dict has keys:
- `id` (str): `"{url}#{chunk_index}"` — unique identifier for ChromaDB
- `url` (str): source URL, carried through from input
- `title` (str): page title, carried through from input
- `text` (str): the chunk text
- `chunk_index` (int): position of this chunk within its source document

**Design decisions:**
- Chunk size: **500 characters** (not tokens). Character-based is simpler and avoids a tokenizer dependency. At an average of ~4 chars/token this is ~125 tokens, well within `all-MiniLM-L6-v2`'s 256-token max.
- Overlap: **50 characters**. Prevents context loss at chunk boundaries.
- Minimum chunk size: **50 characters**. Chunks shorter than this (e.g., stray whitespace) are skipped.
- Uses `langchain.text_splitter.RecursiveCharacterTextSplitter` which splits on paragraphs, then sentences, then words, then characters — preserving natural language boundaries. This is already available via the existing `langchain` dependency.
- Import path: `from langchain.text_splitter import RecursiveCharacterTextSplitter` (compatible with the unpinned `langchain` version currently installed).

---

### `backend/vector_store.py`

**Purpose:** Embed chunks and perform semantic retrieval using ChromaDB.

**Functions:**

`build_collection(chunks: list[dict]) -> chromadb.Collection`
- Creates a new ephemeral ChromaDB collection with a UUID-based name (safe for concurrent requests).
- Uses ChromaDB's built-in `SentenceTransformerEmbeddingFunction("sentence-transformers/all-MiniLM-L6-v2")` — ChromaDB calls the model internally, no manual embedding step needed.
- Adds all chunks to the collection in one batch call:
  - `ids`: the `chunk["id"]` values
  - `documents`: the `chunk["text"]` values (ChromaDB embeds these automatically)
  - `metadatas`: `[{"url": chunk["url"], "title": chunk["title"]}]` per chunk
- Returns the collection object.
- If `chunks` is empty, returns `None`.

`retrieve(query: str, collection, k: int = 5) -> list[dict]`
- If `collection` is `None`, returns `[]`.
- Calls `collection.query(query_texts=[query], n_results=min(k, collection.count()))`.
- ChromaDB embeds the query with the same model automatically.
- Flattens the nested result structure ChromaDB returns.
- Returns `list[dict]` where each dict has: `text` (str), `url` (str), `title` (str), `distance` (float).
- Deduplicates by URL within results (keeps the chunk with the lowest distance per URL).

**Ephemeral design rationale:**  
Using `chromadb.EphemeralClient()` (in-memory) means each request creates, populates, queries, and discards its own collection. This avoids stale data from prior queries, requires no disk setup, and eliminates deduplication complexity. Persistence will be added in Phase 2.

---

## 5. Files to Modify

### `backend/requirements.txt`

**Current (12 packages):**
```
flask
requests
beautifulsoup4
python-dotenv
serpapi
huggingface_hub
langchain
langchain-community
langchain-huggingface
tiktoken
google-search-results
streamlit
```

**Change:** Add 2 lines at the end:
```
chromadb
sentence-transformers
```

No other changes. Versions remain unpinned to match the existing project convention (pinning is a Phase 4 task).

---

### `backend/scraper.py`

**What changes:** The return type of `search_and_scrape()`. Everything else (SerpAPI call, BeautifulSoup parse, retry logic, Wikipedia fallback) is preserved exactly.

**Current return type:** `str` — a single concatenated, truncated string.

**New return type:** `list[dict]` — one dict per successfully scraped URL.

Each dict:
```python
{"url": str, "title": str, "content": str}
```

**Specific line-by-line changes:**

1. **Line 27** — Error return changes from `return "Error: SERPAPI_KEY not found in .env file."` to `raise ValueError("SERPAPI_KEY not found in .env file.")`. This lets `app.py`'s existing `try/except` catch it cleanly.

2. **Line 42** — `all_content = []` stays as-is (list of dicts now instead of list of strings).

3. **Line 44** — Extract `title` from SerpAPI result: add `title = result.get('title', url)` alongside `url = result.get('link')`.

4. **Lines 59–60** — Change `all_content.append(content)` to `all_content.append({"url": url, "title": title, "content": content})` (and the same pattern for the retry path on line 79–80).

5. **Lines 91–119 (Wikipedia fallback)** — Same change: append a dict `{"url": url, "title": "Wikipedia", "content": content}` instead of a bare string.

6. **Lines 121–123** — Remove the final `concatenated_content = ' '.join(all_content)` block entirely. Replace with:
   ```python
   logger.debug(f"Collected {len(all_content)} documents")
   return all_content
   ```
   The 10,000-char truncation is removed because chunking now handles content sizing.

7. **Line 126** — The outer exception handler returns `[]` instead of `f"Error in search_and_scrape: {str(e)}"`. The error is logged (already there). Returning an empty list lets `app.py` detect "no content" without string-parsing an error message.

**What is NOT changed:** User-agent list, SerpAPI client setup, BeautifulSoup parsing logic, retry logic, Wikipedia fallback trigger condition, all logging calls.

---

### `backend/llm.py`

**What changes:** Function signature, prompt construction, return type. The HuggingFace client call and retry loop are preserved.

**Current signature:** `generate_response(query: str, context: str) -> str`

**New signature:** `generate_response(query: str, chunks: list[dict], memory_context: str = "") -> tuple[str, list[dict]]`

- `chunks`: list of dicts with keys `text`, `url`, `title` (output of `retrieve()`)
- `memory_context`: conversation history string, passed in from `app.py` (fixes the disconnected memory bug)
- Returns `(response_text: str, sources: list[dict])` where each source dict is `{"url": str, "title": str}`

**Specific line-by-line changes:**

1. **Line 6** — Remove `from langchain.memory import ConversationBufferMemory` import.

2. **Line 15** — Remove `memory = ConversationBufferMemory()` module-level instance (this was the broken duplicate; memory now lives only in `app.py`).

3. **Line 17** — Update function signature to `def generate_response(query, chunks, memory_context="", retries=3, delay=2):`.

4. **Lines 26–29** — Replace the `memory_context = memory.load_memory_variables({})...` call and the `is_current_affairs` empty-context check with:
   ```python
   if not chunks:
       return "No relevant content found for this query. Try rephrasing.", []
   ```
   The empty-context check is now based on `chunks` being empty, which is unambiguous.

5. **Lines 31–42 (prompt construction)** — Replace entirely with a numbered-source prompt:
   ```
   Build context string:
     [1] {chunks[0]["text"]}
     Source: {chunks[0]["url"]}
     
     [2] {chunks[1]["text"]}
     Source: {chunks[1]["url"]}
     ... up to 5 chunks
   
   Prompt:
     "You are an assistant. Answer the question using ONLY the numbered sources below.
      Cite sources by number, e.g. [1], [2].
      If the sources are insufficient, say so clearly.
      
      Conversation History: {memory_context}
      
      Sources:
      {context_string}
      
      Question: {query}
      
      Answer:"
   ```

6. **Line 49** — Change `max_new_tokens=200` to `max_new_tokens=500`.

7. **Line 54** — Update the `re.sub` cleanup pattern to strip everything up to and including `Answer:` instead of `Answer in 1-2 sentences:`.

8. **Lines 59** — Remove `memory.save_context(...)` call (memory is managed by `app.py`).

9. **Line 61** — Change `return cleaned_response` to `return cleaned_response, sources` where `sources` is the deduplicated list of `{url, title}` dicts derived from `chunks` (deduplicated by URL, preserving first-occurrence order).

10. **Lines 69–71** — Update the outer exception return from `return f"Error generating response: {str(e)}."` to `return f"Error generating response: {str(e)}.", []` to match the new tuple return type.

**What is NOT changed:** `InferenceClient` initialization, `HUGGINGFACE_API_KEY` loading, the retry loop (lines 44–67), `temperature`, `top_p`, `do_sample` settings, all logging calls.

---

### `backend/app.py`

**What changes:** Import additions, pipeline wiring, response shape. Flask setup and logging are preserved.

**Specific line-by-line changes:**

1. **Lines 4–5** — Remove `from langchain.chains import ConversationChain` (unused). Keep `from langchain.memory import ConversationBufferMemory`.

2. **After line 2** — Add imports:
   ```python
   from chunker import chunk_documents
   from vector_store import build_collection, retrieve
   ```

3. **Lines 29–38 (the query handler body)** — Replace with:
   ```python
   # Validate input
   if not user_query or not isinstance(user_query, str):
       return jsonify({"error": "query must be a non-empty string"}), 400
   user_query = user_query.strip()[:1000]   # length cap

   # Step 1: Search and scrape
   docs = search_and_scrape(user_query)
   logger.debug(f"Scraped {len(docs)} documents")

   # Step 2: Chunk
   chunks = chunk_documents(docs)
   logger.debug(f"Produced {len(chunks)} chunks")

   # Step 3: Embed and store
   collection = build_collection(chunks)

   # Step 4: Retrieve semantically relevant chunks
   retrieved = retrieve(user_query, collection, k=5)
   logger.debug(f"Retrieved {len(retrieved)} chunks")

   # Step 5: Load memory context
   memory_context = memory.load_memory_variables({}).get("history", "")

   # Step 6: Generate response
   response, sources = generate_response(user_query, retrieved, memory_context)

   # Step 7: Update memory
   memory.save_context({"input": user_query}, {"output": response})

   return jsonify({"response": response, "sources": sources})
   ```

4. **Line 44** — No change to `app.run()` (debug mode fix is Phase 0, already documented).

**What is NOT changed:** Flask app initialization, logging setup, `load_dotenv()`, `HUGGINGFACE_API_KEY` loading, memory initialization on line 19, the outer `try/except` error handler.

---

### `frontend/app.py`

**What changes:** Extract and display `sources` from the API response. The chat input, message history loop, and `requests.post` call are preserved.

**Specific line-by-line changes:**

1. **Line 27** — Change:
   ```python
   answer = response_data.get("response", "Error: No response from server.")
   ```
   to:
   ```python
   answer = response_data.get("response", "Error: No response from server.")
   sources = response_data.get("sources", [])
   ```

2. **Lines 31–33** — Change the assistant message block from:
   ```python
   with st.chat_message("assistant"):
       st.markdown(answer)
   st.session_state.messages.append({"role": "assistant", "content": answer})
   ```
   to:
   ```python
   with st.chat_message("assistant"):
       st.markdown(answer)
       if sources:
           with st.expander(f"Sources ({len(sources)})"):
               for i, src in enumerate(sources, 1):
                   st.markdown(f"**[{i}]** [{src.get('title', src['url'])}]({src['url']})")
   st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
   ```

3. **Lines 10–13 (history replay loop)** — Update to also render sources for historical messages:
   ```python
   for message in st.session_state.messages:
       with st.chat_message(message["role"]):
           st.markdown(message["content"])
           if message["role"] == "assistant" and message.get("sources"):
               with st.expander(f"Sources ({len(message['sources'])})"):
                   for i, src in enumerate(message["sources"], 1):
                       st.markdown(f"**[{i}]** [{src.get('title', src['url'])}]({src['url']})")
   ```

**What is NOT changed:** `st.title`, `st.write`, `st.chat_input`, `requests.post` call, error handling.

---

## 6. Implementation Order

The order is chosen so each step is independently testable before the next begins. A failure in any step does not break the currently-working system because `app.py` is modified last (it is the integration point).

### Step 1 — Install new dependencies
```
pip install chromadb sentence-transformers
```
Update `requirements.txt` (add 2 lines).  
Verify: `python -c "import chromadb; import sentence_transformers; print('OK')"`.  
Risk: None. No existing code is touched.

---

### Step 2 — Create `backend/chunker.py`
Create the new file. No other files depend on it yet.  
Verify: Run `python chunker.py` with a hardcoded test doc list and print the output.  
Risk: None. No existing code is touched.

---

### Step 3 — Create `backend/vector_store.py`
Create the new file.  
Verify: Run `python vector_store.py` with a hardcoded chunk list and a test query; confirm top-k results are returned.  
Risk: None. No existing code is touched.

---

### Step 4 — Modify `backend/scraper.py`
Change return type from `str` to `list[dict]`.  
Verify: Run `python scraper.py` from a test script that calls `search_and_scrape("test query")` and prints the result — confirm it is a list of dicts with `url`, `title`, `content` keys.  
Risk: **Medium.** This breaks the existing `app.py` call on line 29 (`len(scraped_content)` will fail on a list). Do this step only after steps 1–3 are confirmed, and proceed immediately to step 6 (app.py) without running the server in between.

---

### Step 5 — Modify `backend/llm.py`
Change signature to `generate_response(query, chunks, memory_context="")` and return type to `(str, list)`.  
Verify: Run `python llm.py` from a test script with hardcoded chunks and confirm it returns a tuple `(str, list)`.  
Risk: **Medium.** This breaks the existing `app.py` call on line 33. Same as step 4 — proceed immediately to step 6.

---

### Step 6 — Modify `backend/app.py`
Wire all four modules together. This is the integration step.  
Verify: Start the Flask server and send a test POST request:
```
curl -X POST http://localhost:5001/query \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"latest AI news\"}"
```
Confirm the response JSON contains both `response` (str) and `sources` (list).  
Risk: **High integration surface** but contained — all dependencies were verified individually in prior steps.

---

### Step 7 — Modify `frontend/app.py`
Update the Streamlit UI to display sources.  
Verify: Run `streamlit run frontend/app.py`, submit a query, confirm the answer appears and a "Sources (N)" expander is visible below it with clickable links.  
Risk: **Low.** The frontend change is additive — it reads a new key from the existing JSON response. If the backend does not return `sources`, `response_data.get("sources", [])` defaults to `[]` and no expander is shown.

---

## 7. Data Flow Diagram (post-Phase 1)

```
frontend/app.py
  POST {"query": "..."}
    │
    ▼
backend/app.py  (/query endpoint)
    │
    ├─► scraper.search_and_scrape(query)
    │       └─► [{"url":..., "title":..., "content":...}, ...]
    │
    ├─► chunker.chunk_documents(docs)
    │       └─► [{"id":..., "url":..., "title":..., "text":..., "chunk_index":...}, ...]
    │
    ├─► vector_store.build_collection(chunks)
    │       ├─ chromadb.EphemeralClient() → new collection
    │       ├─ SentenceTransformerEmbeddingFunction("all-MiniLM-L6-v2")
    │       └─► collection (in-memory)
    │
    ├─► vector_store.retrieve(query, collection, k=5)
    │       └─► [{"text":..., "url":..., "title":..., "distance":...}, ...]  (top-5)
    │
    ├─► llm.generate_response(query, retrieved_chunks, memory_context)
    │       ├─ Build numbered-source prompt
    │       ├─ HuggingFace InferenceClient → Mixtral-8x7B
    │       └─► (response_text, [{"url":..., "title":...}, ...])
    │
    └─► return {"response": "...", "sources": [{"url":..., "title":...}, ...]}

frontend/app.py
  Display response text
  Display "Sources (N)" expander with URL links
```

---

## 8. What Is NOT Changed in Phase 1

- SerpAPI integration (search logic, query refinement, news vs. organic toggle)
- BeautifulSoup scraping logic (paragraph extraction, retry on 403/406)
- Wikipedia fallback logic
- User-agent rotation
- HuggingFace `InferenceClient` and Mixtral model choice
- Flask framework and `/query` endpoint path
- Streamlit UI structure (title, chat input, message history)
- `.env` file and environment variable loading
- Logging configuration

---

## 9. Known Limitations Accepted for Phase 1

These are documented as intentional deferments, not oversights.

| Limitation | Deferred to |
|---|---|
| ChromaDB is ephemeral (in-memory per request) — no persistence between requests | Phase 2 |
| Embedding model loaded fresh per request (no singleton caching) — slow cold start | Phase 2 |
| LangChain `ConversationBufferMemory` is still in-process and lost on restart | Phase 2 |
| No async scraping — 5 URLs fetched sequentially | Phase 2 |
| Flask debug mode still enabled | Phase 0 (already documented in ROADMAP.md) |
| No rate limiting or authentication | Phase 4 |
| Chunking is character-based, not token-based | Phase 2 |

---

## 10. Approval Checklist

Before implementation begins, confirm:

- [ ] ChromaDB ephemeral (in-memory) approach is acceptable for Phase 1
- [ ] `sentence-transformers/all-MiniLM-L6-v2` is the intended embedding model
- [ ] Chunk size of 500 characters / 50-character overlap is acceptable
- [ ] Top-5 retrieval (k=5) is acceptable
- [ ] `max_new_tokens` increase from 200 → 500 is acceptable
- [ ] Source citation format (numbered `[1]`, `[2]` in prompt) is acceptable
- [ ] Frontend source display via `st.expander` is acceptable
- [ ] Implementation order (steps 1–7) is acceptable
