# 🤖 Mirae Asset Mutual Fund FAQ Chatbot

A RAG-powered (Retrieval-Augmented Generation) chatbot that answers factual questions about Mirae Asset mutual funds — built with Python, FAISS, OpenAI, and a Streamlit frontend.

---

## 📌 Overview

This project scrapes official Mirae Asset fund pages, converts the content into vector embeddings, and uses semantic search + GPT-3.5-turbo to answer user questions grounded in real, retrieved source data.

No hallucinations. No investment advice. Just facts — from the source.

---

## 🏗️ Architecture

```
scraper.py
    │  Scrapes official Mirae Asset fund pages
    ▼
facts.json / scraped_data.json
    │  Raw page text stored as JSON
    ▼
embedder.py
    │  Generates sentence-transformer embeddings
    │  Builds & persists FAISS vector index
    ▼
rag.py
    │  Semantic search over FAISS index
    │  Constructs prompt from retrieved chunks
    │  Queries OpenAI GPT-3.5-turbo
    ▼
app.py  (Streamlit UI)
    │  Question input + example prompts
    │  Displays answer + source URL
    ▼
index.html / script.js / styles.css
    └  Static web frontend (alternative UI)
```

---

## 📁 Project Structure

```
MF_FAQ_CB/
├── app.py               # Streamlit app (main entry point)
├── scraper.py           # Web scraper for Mirae Asset fund pages
├── embedder.py          # Embedding + FAISS index builder
├── rag.py               # RAG retrieval + OpenAI query logic
├── facts.json           # Scraped fund data
├── requirements.txt     # Python dependencies
├── index.html           # Static web UI
├── script.js            # Frontend JS logic
└── styles.css           # Frontend styles
```

---

## ⚙️ Setup

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your OpenAI API key

```bash
export OPENAI_API_KEY="your_openai_api_key"
```

### 4. Run the app

```bash
streamlit run app.py
```

---

## 🚀 Usage

1. **Refresh Data** — Click the button to scrape Mirae Asset fund pages and rebuild the FAISS index with fresh embeddings.
2. **Ask a Question** — Type your question or pick one of the example prompts.
3. **Get an Answer** — The app retrieves the most relevant chunks and returns a concise, source-cited response.

---

## 🧠 How It Works

| Step | Module | Description |
|------|--------|-------------|
| Scrape | `scraper.py` | Fetches and stores raw text from official Mirae Asset fund pages |
| Embed | `embedder.py` | Encodes text chunks using `sentence-transformers` and indexes them with FAISS |
| Retrieve | `rag.py` | Performs semantic similarity search, builds a context-rich prompt |
| Generate | `rag.py` + OpenAI | Sends prompt to `gpt-3.5-turbo` and returns a grounded answer |
| Display | `app.py` | Streamlit UI surfaces the answer with the source URL |

---

## 🛡️ Constraints & Design Decisions

- **Factual only** — The assistant only answers questions about Mirae Asset mutual funds.
- **No investment advice** — Responses are informational, not financial recommendations.
- **Grounded answers** — If the information isn't in the retrieved context, the model responds with `I don't know.`
- **No PII** — No user data is stored or sent beyond the OpenAI API call.

---

## 🔧 Tech Stack

| Layer | Technology |
|-------|------------|
| LLM | OpenAI GPT-3.5-turbo |
| Embeddings | `sentence-transformers` |
| Vector Store | FAISS |
| Frontend | Streamlit + HTML/CSS/JS |
| Scraping | Python (requests / BeautifulSoup) |
| Language | Python 3.11+ |

---

## 📦 Requirements

- Python 3.11+
- OpenAI API key
- Internet access (for scraping Mirae Asset fund pages)

---

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| `OPENAI_API_KEY is not set` | Add your key via `export OPENAI_API_KEY="..."` |
| Empty or stale answers | Click **Refresh Data** to re-scrape and rebuild the index |
| Import errors | Ensure your virtual environment is active and `pip install -r requirements.txt` has been run |

---

## 📄 License

Internal / project use. Not intended for redistribution.
