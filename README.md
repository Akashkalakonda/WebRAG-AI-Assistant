# 🪐 WebRAG — Web-Grounded AI Research Assistant

WebRAG is an AI-powered research assistant that combines real-time web search, semantic retrieval, and large language models to generate accurate, source-grounded answers.

Instead of relying solely on an LLM's training data, WebRAG searches the web, retrieves relevant information, builds a temporary knowledge base, and generates responses backed by cited sources.

---

## 🚀 Features

- 🔍 Real-time web search using SerpAPI
- 🌐 Automatic webpage scraping and content extraction
- 🧠 Semantic chunking and vector embeddings
- 📚 Retrieval-Augmented Generation (RAG) pipeline
- 🤖 Answer generation using Groq LLaMA 3.3 70B
- 📑 Source attribution and citation support
- 💬 Conversational chat interface
- 🌙 Modern dark-themed Streamlit UI

---

## 🏗️ System Architecture

```text
User Query
     │
     ▼
SerpAPI Search
     │
     ▼
Web Scraping
(BeautifulSoup)
     │
     ▼
Text Chunking
     │
     ▼
Embedding Generation
(sentence-transformers)
     │
     ▼
ChromaDB Vector Store
     │
     ▼
Relevant Context Retrieval
     │
     ▼
Groq LLaMA 3.3 70B
     │
     ▼
Grounded Response + Sources
```

⚙️ Tech Stack
Frontend
Streamlit
Custom CSS
Real-time streaming interface
Backend
Flask
Python
Retrieval Layer
LangChain
ChromaDB
Sentence Transformers
Search & Scraping
SerpAPI
BeautifulSoup
LLM
Groq API
LLaMA 3.3 70B
🔄 RAG Pipeline
1. Search

The system searches the web using SerpAPI to identify relevant sources for the user's query.

2. Scrape

Relevant webpages are scraped and cleaned using BeautifulSoup.

3. Chunk

Extracted content is split into smaller semantic chunks suitable for retrieval.

4. Embed

Chunks are converted into vector embeddings using the all-MiniLM-L6-v2 Sentence Transformer model.

5. Store

Embeddings are stored in ChromaDB for similarity search.

6. Retrieve

The most relevant chunks are retrieved based on semantic similarity to the user query.

7. Generate

Retrieved context is passed to Groq's LLaMA 3.3 70B model to generate a grounded answer.

📸 Interface
Main Features
Chat-based interaction
Streaming responses
Source citations
Retrieval statistics
Conversation history
Responsive dark-themed UI
📂 Project Structure
WebRAG-AI-Assistant/
│
├── frontend/
│   └── app.py
│
├── backend/
│   ├── app.py
│   ├── rag.py
│   ├── scraper.py
│   └── llm.py
│
├── .streamlit/
│   └── config.toml
│
├── requirements.txt
└── README.md
🔑 Environment Variables

Create a .env file:

SERPAPI_API_KEY=your_key
GROQ_API_KEY=your_key
🛠️ Installation

Clone the repository:

git clone https://github.com/Akashkalakonda/WebRAG-AI-Assistant.git
cd WebRAG-AI-Assistant

Install dependencies:

pip install -r requirements.txt
▶️ Running the Project
Backend
cd backend
python app.py

Runs on:

http://localhost:5001
Frontend
streamlit run frontend/app.py

Runs on:

http://localhost:8501
🎯 Key Learning Outcomes

This project demonstrates:

Retrieval-Augmented Generation (RAG)
Vector Databases
Semantic Search
Information Retrieval
LLM Integration
Prompt Engineering
Web Scraping
Streamlit Application Development
AI System Design

🔮 Future Improvements
Multi-turn conversational memory
Hybrid retrieval (BM25 + Vector Search)
Re-ranking models
Persistent user sessions
PDF and document ingestion
Streamlit Community Cloud deployment
Multi-source research mode
