# Mirae Asset Mutual Fund RAG Assistant

This workspace contains a standalone Python Flask application that answers factual questions about Mirae Asset mutual funds using a retrieval-augmented generation (RAG) workflow.

## Files

- `scraper.py`: Scrapes official Mirae Asset fund pages and saves the raw page text to `data/scraped_data.json`.
- `embedder.py`: Converts scraped text into embeddings using `sentence-transformers`, stores them in a FAISS index, and persists metadata.
- `rag.py`: Retrieves the most relevant chunks from the FAISS index and queries OpenAI `gpt-3.5-turbo` with a prompt constructed from those documents.
- `server.py`: Flask API that accepts questions and displays answers with source URLs.
- `requirements.txt`: Python dependencies for the assistant.

## Setup

1. pip install -r requirements.txt
2. export OPENAI_API_KEY="your_key_here"
3. python scraper.py          # scrapes pages, saves scraped_data.json
4. python embedder.py         # builds FAISS index  
5. python server.py           # starts Flask API at http://localhost:5000
6. Open index.html in browser # your frontend talks to the Flask server
Do NOT run streamlit. The frontend is index.html and the backend is server.py on port 5000.

## Usage

- Enter a question or select one of the example questions.
- The app returns a concise answer and the source URL from the retrieved documents.

## Notes

- The assistant is designed for factual Mirae Asset mutual fund information only.
- It does not provide investment advice.
- Answers are generated from retrieved source content; if the information is unavailable, it replies with `I don't know.`
