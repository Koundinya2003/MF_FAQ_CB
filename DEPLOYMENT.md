# FundBot — Deployment Guide

## Architecture

| Layer | Host | URL |
|-------|------|-----|
| Frontend (static) | Netlify | `https://mf-faq.netlify.app` |
| Backend (Flask API) | Railway | `https://mffaqcb-production.up.railway.app` |

Production frontend calls **`/api/ask`** on the same Netlify origin. Netlify proxies that to Railway (`netlify.toml`), so the browser never needs cross-origin CORS for normal users.

Local development calls **`http://localhost:8000/ask`** directly (`config.js`).

---

## Environment variables

### Railway (backend) — required in dashboard

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Recommended | Enables LLM polish on answers. **If unset, answers still work** using retrieved facts only. |
| `ALLOWED_ORIGINS` | Optional | Comma-separated list for direct browser → Railway calls (GitHub Pages, previews). |
| `PORT` | Auto | Set by Railway; do not override unless debugging. |

### Netlify (frontend)

No build env vars required when using the `/api` proxy. Optional override:

| Variable / meta | Description |
|-----------------|-------------|
| `<meta name="api-base-url">` | Force a specific API base (e.g. direct Railway URL for debugging). |

---

## Deploy backend (Railway)

1. Connect this repo to Railway (or `railway up` from CLI).
2. Ensure the service uses the root `Dockerfile`.
3. In **Variables**, set `OPENAI_API_KEY` (recommended).
4. Deploy and verify:

```bash
curl https://mffaqcb-production.up.railway.app/health
# Expect: {"status":"ok","openai_configured":true,...}

curl -X POST https://mffaqcb-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the expense ratio of Mirae Asset Large Cap Fund?"}'
```

---

## Deploy frontend (Netlify)

1. Connect repo; **publish directory** = `.` (repo root).
2. `netlify.toml` is picked up automatically (includes `/api/*` proxy).
3. After deploy, verify proxy:

```bash
curl -X POST https://mf-faq.netlify.app/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the minimum SIP for Mirae Asset ELSS Tax Saver Fund?"}'
```

4. Open `https://mf-faq.netlify.app` and send a chat message.

---

## Deployment verification checklist

- [ ] `GET /health` on Railway returns `status: ok`
- [ ] `openai_configured` is `true` if you set `OPENAI_API_KEY`
- [ ] `POST /ask` on Railway returns `answer` + `source` (not 500)
- [ ] `POST /api/ask` on Netlify returns the same (proxy works)
- [ ] FundBot UI loads on Netlify without console CORS errors
- [ ] Chat message returns an answer with a source link
- [ ] Advice-style question returns refusal (no crash)
- [ ] PII-style input returns privacy message

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 500 on `/ask` with OpenAI auth error | Missing `OPENAI_API_KEY` on Railway (old deploy) | Redeploy with latest `server.py` (has fallback) **or** set the key |
| CORS error in browser | Frontend calling Railway directly from Netlify | Use `/api` proxy; redeploy Netlify with updated `netlify.toml` |
| "Cannot reach API" locally | Backend not running | `python server.py` on port 8000 |
| Wrong port in docs | Old README said 5000 | Backend default is **8000** |
| Netlify `503 usage_exceeded` | Netlify account bandwidth/build limits | Upgrade Netlify plan or use direct Railway URL in meta `api-base-url` temporarily |
| Answers say "data not entered" | Placeholder `[FILL IN]` in JSON | Fill `Topic Detection Data.json` for that fund/topic |
