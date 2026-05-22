# FundBot — Mirae Asset Mutual Fund FAQ

Static frontend (`index.html` + `script.js`) + Flask API (`server.py`) backed by curated fund facts (`Topic Detection Data.json`).

## Project layout

```
Mutual_Funds/
├── index.html              # Frontend UI
├── script.js               # Chat UI + API client
├── config.js               # API base URL (local vs Netlify proxy)
├── styles.css
├── server.py               # Flask API (/ask, /health)
├── topic_detection.py      # Topic + fund detection
├── Topic Detection Data.json
├── requirements.txt
├── Dockerfile              # Railway backend image
├── railway.json            # Railway deploy hints
├── netlify.toml            # Netlify publish + /api proxy
├── .env.example
├── DEPLOYMENT.md           # Full deploy + checklist
└── app.py                  # Legacy Streamlit demo (not used by FundBot UI)
```

## Local development

### 1. Backend

```bash
cd /path/to/Mutual_Funds
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Optional — enables LLM-polished answers
export OPENAI_API_KEY="sk-..."

python server.py
# API: http://localhost:8000/health  and  POST http://localhost:8000/ask
```

### 2. Frontend

Serve the repo root with any static server, then open the site:

```bash
# Option A — Python
python3 -m http.server 5500

# Option B — VS Code Live Server (port 5500)
```

Open `http://localhost:5500` — `config.js` points API calls to `http://localhost:8000`.

**Do not use `app.py` (Streamlit)** for this UI; the chat frontend uses `server.py` only.

## Production URLs

- Frontend: https://mf-faq.netlify.app
- Backend: https://mffaqcb-production.up.railway.app
- Frontend API path in prod: `/api/ask` (proxied to Railway)

See **[DEPLOYMENT.md](./DEPLOYMENT.md)** for deploy commands and verification checklist.

## API

### `GET /health`

```json
{"status": "ok", "message": "FundBot backend is running", "openai_configured": true}
```

### `POST /ask`

Body: `{"question": "What is the expense ratio of Mirae Asset Large Cap Fund?"}`

Response: `{"answer": "...", "source": "https://..."}`

## Notes

- Facts-only assistant; no investment advice.
- Answers come from `Topic Detection Data.json`; optional OpenAI pass when `OPENAI_API_KEY` is set.
