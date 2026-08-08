# Deploying FundBot

Everything below is free. Vercel's Hobby plan covers the whole app, and
OpenRouter's free tier covers the model.

---

## Architecture on Vercel

One project, one domain, no CORS:

| Path | Served by | Source |
|---|---|---|
| `/`, `/styles.css`, `/script.js` | Vercel CDN (static) | `public/` |
| `/api/ask` | Python serverless function | `api/ask.py` |
| `/api/health` | Python serverless function | `api/health.py` |
| `/api/search` | Python serverless function (404 unless `FUNDBOT_DEBUG=1`) | `api/search.py` |

Vercel maps each file in `api/` to its own route, so no rewrite rules are
involved and there is no ambiguity about which path a function receives. All
three files import the same Flask app from `fundbot/wsgi.py`.

Because the page and the API share an origin, the browser never issues a
cross-origin request in production.

---

## Deploy

### Option A — Vercel CLI

```bash
npm i -g vercel
cd MF_FAQ_CB
vercel            # first run links the project and deploys a preview
vercel --prod     # promote to production
```

### Option B — Git integration

1. Push the repo to GitHub.
2. At [vercel.com/new](https://vercel.com/new), import it.
3. Framework preset: **Other**. Leave build command and output directory empty —
   `public/` is detected automatically and `api/*.py` is built by the Python
   runtime.
4. Deploy. Every later push to the default branch redeploys.

### Set the API key

Vercel dashboard → your project → **Settings → Environment Variables**:

| Name | Value | Environments |
|---|---|---|
| `OPENROUTER_API_KEY` | your key from [openrouter.ai/keys](https://openrouter.ai/keys) | Production, Preview, Development |

Redeploy after adding it — environment variables are baked in at build time.

> Skipping this is a supported configuration, not a broken one. Without a key
> FundBot returns the retrieved passage verbatim. Retrieval, guardrails, citations
> and confidence all behave identically; only the phrasing is less polished.

Optional variables are listed in `.env.example` and in the README's
configuration table.

---

## Verify a deployment

```bash
BASE=https://your-project.vercel.app

# 1. Corpus loaded and key wired up
curl -s $BASE/api/health
# → {"status":"ok","corpus":{"documents":47,…},"llm":{"enabled":true,…}}

# 2. A normal answer, with a citation
curl -s -X POST $BASE/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is the exit load for Mirae Asset Midcap Fund?"}'
# → {"answer":"…","source":"https://www.miraeassetmf.co.in/…","kind":"answer",…}

# 3. Advice is refused
curl -s -X POST $BASE/api/ask -H 'Content-Type: application/json' \
  -d '{"question":"should I invest in the ELSS fund"}'      # kind: refusal_advice

# 4. Another fund house is out of scope
curl -s -X POST $BASE/api/ask -H 'Content-Type: application/json' \
  -d '{"question":"expense ratio of HDFC Top 100"}'         # kind: refusal_scope

# 5. Personal data is refused
curl -s -X POST $BASE/api/ask -H 'Content-Type: application/json' \
  -d '{"question":"my PAN is ABCDE1234F"}'                  # kind: refusal_pii

# 6. Off-topic is declined rather than guessed
curl -s -X POST $BASE/api/ask -H 'Content-Type: application/json' \
  -d '{"question":"how do I bake bread"}'                   # kind: no_answer
```

Checklist:

- [ ] `/api/health` returns `status: ok` and a non-zero `corpus.documents`
- [ ] `llm.enabled` is `true` if you set the key
- [ ] A covered question returns `kind: "answer"` with a source URL
- [ ] Each of the three refusal kinds fires on its example above
- [ ] The page loads and a chat message round-trips with no console errors
- [ ] The status dot in the chat header is green

---

## Local development

```bash
./run-local.sh              # API + frontend on :8000
```

If you prefer a separate static server (Live Server, `python -m http.server`),
`public/config.js` detects the port mismatch and points the frontend at
`http://localhost:8000/api` automatically. Set `ALLOWED_ORIGINS` to that static
origin so CORS permits it:

```bash
ALLOWED_ORIGINS=http://localhost:5500 ./run-local.sh
```

To emulate the Vercel routing exactly:

```bash
vercel dev
```

---

## Deploying somewhere other than Vercel

The `Dockerfile` builds a self-contained image serving both the API and the
frontend via gunicorn.

```bash
docker build -t fundbot .
docker run -p 8000:8000 -e OPENROUTER_API_KEY=sk-or-v1-… fundbot
```

Known-good free-tier targets for that image:

| Host | Notes |
|---|---|
| **Hugging Face Spaces** | Free indefinitely, Docker SDK, no sleep. Set `PORT=7860` |
| **Render** | Free web service; sleeps after 15 min idle, ~50 s cold start |
| **Fly.io** | Free allowance suits it; requires a card on file |

The image does not include `api/`, `tests/` or `vercel.json` — see
`.dockerignore`.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `/api/health` reports `status: degraded` with `corpus_error` | `data/` missing from the function bundle | Confirm `includeFiles` in `vercel.json` still reads `{fundbot/**,data/**}` |
| Answers are correct but stiff and never rephrased | No API key, or the model call is failing | Check `llm.enabled` in `/api/health`; inspect Vercel function logs for `OpenRouter …` warnings |
| `http_401` in the logs | Bad or unset `OPENROUTER_API_KEY` | Re-add the variable, then redeploy so it is picked up |
| `http_429` in the logs | Free-tier rate limit reached | Answers still return, unrephrased. Wait, or set `OPENROUTER_MODEL` to another free model |
| Function times out | LLM slower than the function limit | Lower `LLM_TIMEOUT_SECONDS` below `maxDuration` (30 s in `vercel.json`) |
| A fund's numbers look stale | The corpus is point-in-time, not live | Edit `data/knowledge_base.json` and bump its `last_updated` |
| CORS error in the browser | Frontend on a different origin from the API | Add that origin to `ALLOWED_ORIGINS`, or serve both from one Vercel project |
