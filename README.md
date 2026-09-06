# FundBot

Live @ https://mf-faq-cbmark1.vercel.app/

A facts-only FAQ assistant for Mirae Asset mutual fund schemes. Ask about expense
ratios, exit loads, SIP and lump sum minimums, benchmarks, riskometer levels or
ELSS lock-in, and get a short answer with the official source linked.

Runs entirely on free tooling: **Vercel** hosting (static frontend + Python
serverless functions), **OpenRouter** with a free DeepSeek model, and a retrieval
stack built on the Python standard library.

---

## What it does

| | |
|---|---|
| **Answers** | Factual questions about 4 Mirae Asset schemes + general mutual fund concepts |
| **Refuses** | Investment advice, personal identifiers, and schemes from other fund houses |
| **Declines** | Anything retrieval is not confident about — it says so rather than guessing |
| **Cites** | Every answer carries the source URL and the date that source was last read |

---

## How it works

```
 Browser (public/)
      │  POST /api/ask  {"question": "..."}
      ▼
 ┌──────────────────────────────────────────────────────────┐
 │ 1. Guardrails            fundbot/guards.py               │
 │    PII → scope → advice. A blocked question never         │
 │    reaches the knowledge base or the model.               │
 ├──────────────────────────────────────────────────────────┤
 │ 2. Retrieval             fundbot/retrieval.py            │
 │    Hybrid BM25F + TF-IDF over 47 curated documents.       │
 │    Fund affinity picks the right scheme; IDF coverage     │
 │    decides whether we know the answer at all.             │
 ├──────────────────────────────────────────────────────────┤
 │ 3. Generation            fundbot/llm.py                  │
 │    DeepSeek via OpenRouter rephrases the retrieved        │
 │    passage. Optional — every failure falls back to the    │
 │    passage verbatim.                                      │
 └──────────────────────────────────────────────────────────┘
      │  {"answer", "source", "kind", "confidence", …}
      ▼
 Browser renders the answer + source link
```

**The model never supplies a fact.** It only rewrites text that retrieval already
selected, under a prompt that forbids adding numbers. If the key is missing, the
quota is exhausted or the request times out, FundBot returns the retrieved
passage as-is. Answers get less conversational; they never get less correct.

### Retrieval, in more detail

Two scorers run over the same weighted-field term counts:

- **BM25F-lite** drives ranking. Field weights (`title` ×3, `questions` ×3,
  `keywords` ×2, `fund_names` ×2, `text` ×1) are folded into term frequencies
  before scoring. Adjacent-word **bigrams** are indexed alongside unigrams.
- **TF-IDF cosine × IDF coverage** produces the confidence score. Cosine alone is
  fooled by short off-topic questions that share one rare word — *"what is the
  capital of Mongolia"* matched the capital-gains document at 0.29. Coverage asks
  what share of the question's IDF mass the document actually accounts for, and
  charges unseen words (*Mongolia*, *sourdough*) at maximum IDF, which pushes
  them below the floor.

A fund-affinity pass boosts documents belonging to the scheme named in the
question and suppresses the other three, so *"exit load of the midcap fund"*
cannot be answered with the large cap figure.

**Why not embeddings and FAISS?** `sentence-transformers` pulls in ~2 GB of
torch. That does not fit a free serverless tier, and cold starts would be
measured in tens of seconds. For a corpus of 47 short, keyword-dense financial
documents, lexical retrieval with synonym expansion measures better per byte —
see the numbers below.

---

## Measured quality

`scripts/evaluate.py` scores retrieval against 41 hand-labelled paraphrases (none
copied from the knowledge base's own phrasings), 12 off-topic questions, and 5
competitor-AMC questions.

```
Top-1 accuracy     :  92.7%  (38/41)   floor 85%
Top-3 accuracy     : 100.0%  (41/41)   floor 95%
Answered (>= floor):  97.6%  (40/41)   floor 90%
Off-topic rejected : 100.0%  (12/12)   floor 100%
Competitor scoped  : 100.0%  (5/5)     floor 100%
```

The script exits non-zero when any floor is breached, and CI runs it on every
push. Re-run it after touching the tokenizer, the scoring weights or the corpus:

```bash
python scripts/evaluate.py --verbose   # list every miss
python scripts/evaluate.py --sweep     # trade-off curve for MIN_CONFIDENCE
```

`MIN_CONFIDENCE = 0.06` was chosen from that sweep: the hardest off-topic
question peaks at 0.052, so 0.06 answers 97.6% of real questions with zero false
answers.

---

## Quick start

**macOS / Linux / WSL / Git Bash:**

```bash
git clone https://github.com/Koundinya2003/MF_FAQ_CB.git
cd MF_FAQ_CB
./run-local.sh                    # http://localhost:8000
```

`run-local.sh` creates the virtualenv and installs dependencies on first run, so
that one command is the whole setup.

**Windows (PowerShell)** — same thing, done by hand:

```powershell
git clone https://github.com/Koundinya2003/MF_FAQ_CB.git
cd MF_FAQ_CB
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m fundbot.app        # http://localhost:8000
```

Either way the API and the frontend are served from one process. The LLM is
optional — the app works without a key, returning retrieved text unrephrased.

Requires Python 3.11 or newer (`python --version` to check).

To enable rephrasing, get a free key at [openrouter.ai/keys](https://openrouter.ai/keys):

```bash
cp .env.example .env
# set OPENROUTER_API_KEY in .env
./run-local.sh
```

### Tests

```bash
.venv/bin/pytest                      # 111 tests
.venv/bin/python scripts/evaluate.py  # retrieval quality gate
```

On Windows use `.venv\Scripts\pytest` and `.venv\Scripts\python`.

---

## Deploying

Full instructions in **[DEPLOYMENT.md](DEPLOYMENT.md)**. Short version:

```bash
npm i -g vercel
vercel            # preview
vercel --prod     # production
```

Then set `OPENROUTER_API_KEY` in the Vercel dashboard under
Settings → Environment Variables.

A `Dockerfile` is included for hosts other than Vercel (Fly.io, Render, Hugging
Face Spaces, a VPS).

---

## Project layout

```
MF_FAQ_CB/
├── api/                      Vercel functions — one file per route
│   ├── ask.py                POST /api/ask
│   ├── health.py             GET  /api/health
│   └── search.py             POST /api/search   (debug, off unless FUNDBOT_DEBUG=1)
├── fundbot/
│   ├── app.py                Flask factory, routes, CORS
│   ├── service.py            guards → retrieval → LLM pipeline
│   ├── retrieval.py          hybrid BM25 + TF-IDF index
│   ├── text.py               tokenizer, synonyms, bigrams
│   ├── guards.py             PII / scope / advice rules
│   ├── llm.py                OpenRouter client (stdlib urllib)
│   ├── knowledge.py          corpus loading + validation
│   ├── config.py             environment configuration
│   └── wsgi.py               shared entrypoint, warms the index
├── data/knowledge_base.json  47 curated documents — the single source of truth
├── public/                   static frontend (no build step)
├── scripts/evaluate.py       retrieval quality harness
├── tests/                    111 tests
├── vercel.json               function config + security headers
└── Dockerfile                for non-Vercel hosts
```

---

## Editing the knowledge base

Everything FundBot can say lives in `data/knowledge_base.json`. To add or correct
a fact, edit that file — no code changes:

```json
{
  "id": "large_cap.exit_load",
  "fund": "large_cap",
  "topic": "exit_load",
  "title": "Exit load of Mirae Asset Large Cap Fund",
  "text": "The answer, as it should be read back to the user.",
  "questions": ["phrasings a user might type"],
  "keywords": ["terms", "to", "match"],
  "source_url": "https://…",
  "source_label": "miraeassetmf.co.in",
  "last_updated": "June 2025"
}
```

`questions` and `keywords` are indexed at higher weight than `text`, so adding
phrasings is the fastest way to improve recall for a topic users keep missing.
Run `pytest && python scripts/evaluate.py` afterwards.

---

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | — | Free key from openrouter.ai. Unset ⇒ extractive answers |
| `OPENROUTER_MODEL` | `deepseek/deepseek-chat-v3.1:free` | Any OpenRouter model id |
| `LLM_TIMEOUT_SECONDS` | `12` | Fall back to retrieved text after this |
| `FUNDBOT_DISABLE_LLM` | `0` | `1` skips the model entirely |
| `ALLOWED_ORIGINS` | localhost set | Cross-origin callers. Unneeded on Vercel |
| `RETRIEVAL_TOP_K` | `3` | Passages passed to the model as context |
| `FUNDBOT_DEBUG` | `0` | `1` enables `POST /api/search` |
| `PORT` | `8000` | Local / Docker listen port |

---

## Limitations

- **Figures are point-in-time.** The corpus reflects sources as of June 2025 and
  does not fetch live data. Expense ratios in particular change monthly; several
  documents deliberately point at the AMC's TER page rather than quoting a number
  that would go stale.
- **Four schemes only.** Questions about other Mirae funds fall through to the
  "I don't know" reply; questions about other fund houses are refused explicitly.
- **Lexical retrieval has a ceiling.** A paraphrase sharing no vocabulary with the
  corpus will miss. The fix is to add phrasings to `questions`, which is why that
  field is weighted heavily.
- **No conversation memory.** Each question is answered independently; follow-ups
  like "and for the midcap?" will not resolve.

---

## Disclaimer

FundBot is informational only. It is not investment advice, not a recommendation,
and not a substitute for a SEBI-registered investment adviser. Figures are
sourced from public AMC, AMFI and SEBI pages and may be out of date — verify with
the AMC before acting on anything here. Mutual fund investments are subject to
market risks; read all scheme-related documents carefully.
