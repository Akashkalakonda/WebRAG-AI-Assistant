# 🪐 WebRAG — Web-Grounded AI Research Assistant

WebRAG is an AI-powered research assistant that combines real-time web search, semantic retrieval, and large language models to generate accurate, source-grounded answers.

Instead of relying solely on an LLM's training data, WebRAG searches the web, retrieves relevant information, builds a temporary knowledge base, and generates responses backed by cited sources.

---
<img width="1920" height="1200" alt="image" src="https://github.com/user-attachments/assets/d50ac909-46d8-464a-9e09-1fc73ebdf6a8" />


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
---

## ⚙️ Tech Stack

| Category              | Technologies                                  |
| --------------------- | --------------------------------------------- |
| **Frontend**          | Streamlit, Custom CSS, Real-Time Streaming UI |
| **Backend**           | Flask, Python                                 |
| **Retrieval Layer**   | LangChain, ChromaDB, Sentence Transformers    |
| **Search & Scraping** | SerpAPI, BeautifulSoup                        |
| **LLM**               | Groq API, LLaMA 3.3 70B                       |

---

## 🔄 RAG Pipeline

### 1️⃣ Search

The system searches the web using **SerpAPI** to identify relevant sources for the user's query.

### 2️⃣ Scrape

Relevant webpages are scraped and cleaned using **BeautifulSoup**.

### 3️⃣ Chunk

Extracted content is split into smaller semantic chunks suitable for retrieval.

### 4️⃣ Embed

Chunks are converted into vector embeddings using the **all-MiniLM-L6-v2** Sentence Transformer model.

### 5️⃣ Store

Embeddings are stored in **ChromaDB** for efficient similarity search.

### 6️⃣ Retrieve

The most relevant chunks are retrieved based on semantic similarity to the user's query.

### 7️⃣ Generate

Retrieved context is passed to **Groq's LLaMA 3.3 70B** model to generate a grounded response.

---

## 📸 Interface

### Main Features

* 💬 Chat-based interaction
* ⚡ Streaming responses
* 📑 Source citations
* 📊 Retrieval statistics
* 🕒 Conversation history
* 🌙 Responsive dark-themed UI

---

## 📂 Project Structure

```text
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
```

---

## 🔑 Environment Variables

Create a `.env` file in the project root:

```env
SERPAPI_API_KEY=your_key
GROQ_API_KEY=your_key
```

---

## 🛠️ Installation

### Clone the Repository

```bash
git clone https://github.com/Akashkalakonda/WebRAG-AI-Assistant.git
cd WebRAG-AI-Assistant
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Project

### Backend

```bash
cd backend
python app.py
```

Runs on:

```text
http://localhost:5001
```

### Frontend

```bash
streamlit run frontend/app.py
```

Runs on:

```text
http://localhost:8501
```

---

## 🎯 Key Learning Outcomes

This project demonstrates practical experience in:

* Retrieval-Augmented Generation (RAG)
* Vector Databases
* Semantic Search
* Information Retrieval
* Large Language Model Integration
* Prompt Engineering
* Web Scraping & Data Extraction
* Streamlit Application Development
* End-to-End AI System Design

---

## 🔮 Future Improvements

* 🧠 Multi-turn conversational memory
* 🔍 Hybrid retrieval (BM25 + Vector Search)
* 📈 Re-ranking models
* 👤 Persistent user sessions
* 📄 PDF and document ingestion
* ☁️ Streamlit Community Cloud deployment
* 🌐 Multi-source research mode

