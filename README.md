<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/readme/01_hero_dark.svg">
  <img src="docs/readme/01_hero_light.svg" width="100%" alt="FundBot. A facts only FAQ assistant for four Mirae Asset mutual fund schemes, built on 47 curated documents with sources as of June 2025. Ask a factual question about a fund and get a short answer with the official source linked, or an honest refusal. The model never supplies a fact: it only rewrites a passage retrieval already chose, and if it fails the passage is returned as is. Example chat: asked for the exit load of the large cap fund, FundBot answers that Mirae Asset Large Cap Fund charges 1% if units are redeemed within 365 days from allotment and nothing after 365 days, citing miraeassetmf.co.in, June 2025. Schemes: Large Cap (NIFTY 100 TRI), Flexi Cap (Nifty 500 TRI), ELSS Tax Saver (NIFTY 500 TRI), Midcap (NIFTY Midcap 150 TRI). Live at mf-faq-cbmark1.vercel.app.">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/readme/02_pipeline_dark.svg">
  <img src="docs/readme/02_pipeline_light.svg" width="100%" alt="One question, three gates. FundBot answers factual questions on 4 Mirae Asset schemes and general fund concepts; refuses investment advice, personal identifiers and other fund houses; declines anything retrieval is unsure of, saying so instead of guessing; and cites the source URL and date read on every answer. Flow: the question arrives at POST /api/ask. Stage 1, guardrails in fundbot/guards.py check personal data, scope and advice; a blocked question gets a polite refusal pointing to a SEBI registered adviser or AMFI and never reaches the knowledge base or model. Stage 2, retrieval in fundbot/retrieval.py uses hybrid BM25F and TF IDF scoring over 47 curated documents with fund affinity; below a confidence of 0.06 it replies that it does not know. Stage 3, generation in fundbot/llm.py has DeepSeek via OpenRouter rephrase the passage without adding numbers; if the key is missing or the call times out, the retrieved passage is returned verbatim. The reply carries a source link and date. Less chatty, never less correct: the app works with no LLM at all.">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/readme/03_retrieval_dark.svg">
  <img src="docs/readme/03_retrieval_light.svg" width="100%" alt="Retrieval that knows when it does not know. BM25F lite field weights: title 3, questions 3, keywords 2, fund names 2, text 1, folded into term frequencies, with bigrams indexed next to single words. Fund affinity boosts the scheme the question names and suppresses the other three. Embeddings were skipped because sentence transformers pulls in about 2 GB of torch, too big for a free serverless tier, with cold starts of tens of seconds. Confidence is TF IDF cosine multiplied by IDF coverage. On a number line from 0 to 0.30, the answer floor sits at 0.06, the hardest off topic question peaks at 0.052, and cosine alone scored 'what is the capital of Mongolia' against the capital gains document at 0.29. Coverage charges unseen words like Mongolia at maximum IDF, pushing them under the floor. 0.06 was chosen from a sweep: it answers 97.6% of real questions with zero false answers.">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/readme/04_quality_dark.svg">
  <img src="docs/readme/04_quality_light.svg" width="100%" alt="Quality is a build gate, not a claim. Measured against floors that fail the build: top 1 accuracy 92.7% (38 of 41, floor 85%), top 3 accuracy 100% (41 of 41, floor 95%), answered 97.6% (40 of 41, floor 90%), off topic rejected 100% (12 of 12, floor 100%), competitor questions scoped 100% (5 of 5, floor 100%). The test set: 41 hand labelled paraphrases none copied from the corpus, 12 off topic questions, 5 questions about other fund houses. 111 pytest tests run in CI on Python 3.11 and 3.12. python scripts/evaluate.py exits non zero if any floor breaks.">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/readme/05_coverage_dark.svg">
  <img src="docs/readme/05_coverage_light.svg" width="100%" alt="Four schemes, read from the factsheet. A SEBI riskometer with six levels from Low to Very High points at Very High: every scheme covered is an equity fund labelled Very High. Large Cap Fund: benchmark NIFTY 100 TRI, SIP from Rs. 99, exit load 1% within 365 days. Flexi Cap Fund: benchmark Nifty 500 TRI, SIP from Rs. 99, exit load 1% within 365 days. ELSS Tax Saver Fund: benchmark NIFTY 500 TRI (tier 1) and Nifty 200 TRI (tier 2), from Rs. 99, lock in of 3 years per instalment. Midcap Fund: benchmark NIFTY Midcap 150 TRI, SIP from Rs. 99, exit load per scheme documents. Plus 14 explainers: SIP, NAV, ELSS, expense ratio, exit load, riskometer, SWP, STP, KYC, direct versus regular, equity tax, statements. Documents per fund: Large Cap 8, Flexi Cap 8, ELSS 9, Midcap 8, general 14. Figures are point in time, as of June 2025.">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/readme/06_stack_dark.svg">
  <img src="docs/readme/06_stack_light.svg" width="100%" alt="Built free, with its limits written down. Free tooling end to end: Vercel for the static frontend in public/ and Python serverless functions in api/; OpenRouter with a free DeepSeek model for optional rephrasing; the Python standard library for the tokenizer, synonyms, BM25F and TF IDF with no vector database; Flask behind /api/ask, /api/health and a debug /api/search; CI running pytest plus the retrieval quality gate on every push; Docker for Fly.io, Render, Hugging Face Spaces or a VPS. Known limits: point in time sources as of June 2025 with no live data, and expense ratios change monthly so some answers link the TER page instead; four schemes only, other Mirae funds get I don't know and other fund houses are refused; a lexical ceiling, so a paraphrase with no shared vocabulary will miss; no memory, so a follow up like 'and for the midcap?' will not resolve. Not advice: informational only, not a recommendation, not a substitute for a SEBI registered investment adviser. Mutual fund investments are subject to market risks; read all scheme related documents carefully.">
</picture>

# FundBot

**Live:** https://mf-faq-cbmark1.vercel.app/

A facts only FAQ assistant for Mirae Asset mutual fund schemes. Ask about expense ratios, exit loads, SIP and lump sum minimums, benchmarks, riskometer levels or ELSS lock in, and get a short answer with the official source linked.

Runs entirely on free tooling: **Vercel** hosting (static frontend plus Python serverless functions), **OpenRouter** with a free DeepSeek model, and a retrieval stack built on the Python standard library.

## What it does

* **Answers** factual questions about 4 Mirae Asset schemes (Large Cap, Flexi Cap, ELSS Tax Saver, Midcap) plus general mutual fund concepts.
* **Refuses** investment advice, personal identifiers, and schemes from other fund houses.
* **Declines** anything retrieval is not confident about. It says so rather than guessing.
* **Cites** the source URL and the date that source was last read on every answer.

## How it works

```
 Browser (public/)
      │  POST /api/ask  {"question": "..."}
      ▼
 1. Guardrails    fundbot/guards.py
    PII, then scope, then advice. A blocked question never
    reaches the knowledge base or the model.
 2. Retrieval     fundbot/retrieval.py
    Hybrid BM25F + TF IDF over 47 curated documents.
    Fund affinity picks the right scheme; IDF coverage
    decides whether we know the answer at all.
 3. Generation    fundbot/llm.py
    DeepSeek via OpenRouter rephrases the retrieved passage.
    Optional: every failure falls back to the passage verbatim.
      │  {"answer", "source", "kind", "confidence", ...}
      ▼
 Browser renders the answer + source link
```

**The model never supplies a fact.** It only rewrites text that retrieval already selected, under a prompt that forbids adding numbers. If the key is missing, the quota is exhausted or the request times out, FundBot returns the retrieved passage as is. Answers get less conversational; they never get less correct.

### Retrieval in more detail

Two scorers run over the same weighted field term counts:

* **BM25F lite** drives ranking. Field weights (`title` ×3, `questions` ×3, `keywords` ×2, `fund_names` ×2, `text` ×1) are folded into term frequencies before scoring. Adjacent word **bigrams** are indexed alongside single words.
* **TF IDF cosine × IDF coverage** produces the confidence score. Cosine alone is fooled by short off topic questions that share one rare word: *"what is the capital of Mongolia"* matched the capital gains document at 0.29. Coverage asks what share of the question's IDF mass the document actually accounts for, and charges unseen words (*Mongolia*, *sourdough*) at maximum IDF, which pushes them below the floor.

A fund affinity pass boosts documents belonging to the scheme named in the question and suppresses the other three, so *"exit load of the midcap fund"* cannot be answered with the large cap figure.

**Why not embeddings and FAISS?** `sentence-transformers` pulls in about 2 GB of torch. That does not fit a free serverless tier, and cold starts would be measured in tens of seconds. For a corpus of 47 short, keyword dense financial documents, lexical retrieval with synonym expansion measures better per byte (see the numbers below).

## Measured quality

`scripts/evaluate.py` scores retrieval against 41 hand labelled paraphrases (none copied from the knowledge base's own phrasings), 12 off topic questions, and 5 competitor AMC questions.

```
Top-1 accuracy     :  92.7%  (38/41)   floor 85%
Top-3 accuracy     : 100.0%  (41/41)   floor 95%
Answered (>= floor):  97.6%  (40/41)   floor 90%
Off-topic rejected : 100.0%  (12/12)   floor 100%
Competitor scoped  : 100.0%  (5/5)     floor 100%
```

The script exits with a non zero code when any floor is breached, and CI runs it on every push. Run it again after touching the tokenizer, the scoring weights or the corpus:

```bash
python scripts/evaluate.py --verbose   # list every miss
python scripts/evaluate.py --sweep     # trade off curve for MIN_CONFIDENCE
```

`MIN_CONFIDENCE = 0.06` was chosen from that sweep: the hardest off topic question peaks at 0.052, so 0.06 answers 97.6% of real questions with zero false answers.

## Quick start

Requires Python 3.11 or newer (`python --version` to check).

**macOS, Linux, WSL or Git Bash:**

```bash
git clone https://github.com/Koundinya2003/MF_FAQ_CB.git
cd MF_FAQ_CB
./run-local.sh                    # http://localhost:8000
```

`run-local.sh` creates the virtualenv and installs dependencies on first run, so that one command is the whole setup.

**Windows (PowerShell)**, the same thing done by hand:

```powershell
git clone https://github.com/Koundinya2003/MF_FAQ_CB.git
cd MF_FAQ_CB
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python -m fundbot.app        # http://localhost:8000
```

Either way the API and the frontend are served from one process. The LLM is optional: without a key the app returns retrieved text unrephrased.

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

## Deploying

Full instructions are in **[DEPLOYMENT.md](DEPLOYMENT.md)**. Short version:

```bash
npm i -g vercel
vercel            # preview
vercel --prod     # production
```

Then set `OPENROUTER_API_KEY` in the Vercel dashboard under Settings, Environment Variables.

A `Dockerfile` is included for hosts other than Vercel (Fly.io, Render, Hugging Face Spaces, a VPS).

## Project layout

```
MF_FAQ_CB/
├── api/                      Vercel functions, one file per route
│   ├── ask.py                POST /api/ask
│   ├── health.py             GET  /api/health
│   └── search.py             POST /api/search   (debug, off unless FUNDBOT_DEBUG=1)
├── fundbot/
│   ├── app.py                Flask factory, routes, CORS
│   ├── service.py            guards, then retrieval, then LLM pipeline
│   ├── retrieval.py          hybrid BM25 + TF IDF index
│   ├── text.py               tokenizer, synonyms, bigrams
│   ├── guards.py             PII, scope and advice rules
│   ├── llm.py                OpenRouter client (stdlib urllib)
│   ├── knowledge.py          corpus loading and validation
│   ├── config.py             environment configuration
│   └── wsgi.py               shared entrypoint, warms the index
├── data/knowledge_base.json  47 curated documents, the single source of truth
├── public/                   static frontend (no build step)
├── scripts/evaluate.py       retrieval quality harness
├── tests/                    111 tests
├── docs/readme/              README panels and the page they are built from
├── vercel.json               function config + security headers
└── Dockerfile                for non Vercel hosts
```

## Editing the knowledge base

Everything FundBot can say lives in `data/knowledge_base.json`. To add or correct a fact, edit that file; no code changes are needed:

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

`questions` and `keywords` are indexed at higher weight than `text`, so adding phrasings is the fastest way to improve recall for a topic users keep missing. Run `pytest && python scripts/evaluate.py` afterwards.

## Configuration

<table>
  <tr><th>Variable</th><th>Default</th><th>Purpose</th></tr>
  <tr><td><code>OPENROUTER_API_KEY</code></td><td>(none)</td><td>Free key from openrouter.ai. Unset means extractive answers</td></tr>
  <tr><td><code>OPENROUTER_MODEL</code></td><td><code>deepseek/deepseek-chat-v3.1:free</code></td><td>Any OpenRouter model id</td></tr>
  <tr><td><code>LLM_TIMEOUT_SECONDS</code></td><td><code>12</code></td><td>Fall back to retrieved text after this</td></tr>
  <tr><td><code>FUNDBOT_DISABLE_LLM</code></td><td><code>0</code></td><td><code>1</code> skips the model entirely</td></tr>
  <tr><td><code>ALLOWED_ORIGINS</code></td><td>localhost set</td><td>Cross origin callers. Unneeded on Vercel</td></tr>
  <tr><td><code>RETRIEVAL_TOP_K</code></td><td><code>3</code></td><td>Passages passed to the model as context</td></tr>
  <tr><td><code>FUNDBOT_DEBUG</code></td><td><code>0</code></td><td><code>1</code> enables <code>POST /api/search</code></td></tr>
  <tr><td><code>PORT</code></td><td><code>8000</code></td><td>Local and Docker listen port</td></tr>
</table>

## Limitations

* **Figures are point in time.** The corpus reflects sources as of June 2025 and does not fetch live data. Expense ratios in particular change monthly; several documents deliberately point at the AMC's TER page rather than quoting a number that would go stale.
* **Four schemes only.** Questions about other Mirae funds fall through to the "I don't know" reply; questions about other fund houses are refused explicitly.
* **Lexical retrieval has a ceiling.** A paraphrase sharing no vocabulary with the corpus will miss. The fix is to add phrasings to `questions`, which is why that field is weighted heavily.
* **No conversation memory.** Each question is answered independently; follow ups like "and for the midcap?" will not resolve.

## Rebuilding the panels

The images at the top are SVG panels generated from one HTML page. Edit `docs/readme/one_sheet.html`, then run:

```bash
node docs/readme/build_readme_svgs.js docs/readme/one_sheet.html docs/readme 960
```

This needs Node with Playwright installed, and curl (fonts are fetched from Google Fonts and embedded).

## Disclaimer

FundBot is informational only. It is not investment advice, not a recommendation, and not a substitute for a SEBI registered investment adviser. Figures are sourced from public AMC, AMFI and SEBI pages and may be out of date; verify with the AMC before acting on anything here. Mutual fund investments are subject to market risks; read all scheme related documents carefully.
