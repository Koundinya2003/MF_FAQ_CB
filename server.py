"""
FundBot Flask API — serves /ask and /health for the static frontend.

Environment variables:
  OPENAI_API_KEY   — optional; when unset, answers use retrieved facts only (no LLM polish)
  ALLOWED_ORIGINS  — comma-separated CORS origins (defaults include Netlify + local dev)
  PORT             — listen port (default 8000; Railway sets this automatically)
"""

import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

from topic_detection import get_answer

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_ORIGINS = [
    "https://mf-faq.netlify.app",
    "https://koundinya2003.github.io",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:8888",
    "http://localhost:8888",
]

def _parse_origins() -> list[str]:
    raw = os.environ.get("ALLOWED_ORIGINS", "").strip()
    if not raw:
        return DEFAULT_ORIGINS
    return [o.strip() for o in raw.split(",") if o.strip()]


_openai_client: OpenAI | None = None


def _get_openai_client() -> OpenAI | None:
    """Lazy-init OpenAI client only when an API key is present."""
    global _openai_client
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    if _openai_client is None:
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def call_llm(question: str, context_text: str) -> str:
    """
    Optionally rephrase retrieved facts via GPT-4o-mini.
    Falls back to context_text when OPENAI_API_KEY is not configured.
    """
    client = _get_openai_client()
    if client is None:
        return context_text

    prompt = f"""You are FundBot, a facts-only mutual fund assistant for Mirae Asset schemes.

Rules:
- Answer using ONLY the source text below
- Maximum 3 sentences
- No investment advice or opinions
- No numbers not present in the source text
- If answer not found say exactly: I could not find that detail. Please check the official source linked below.

Source text:
{context_text}

Question: {question}

Answer:"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or context_text


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)

# CORS on all API routes — origins driven by env for easy production updates
CORS(
    app,
    resources={r"/*": {"origins": _parse_origins()}},
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.route("/ask", methods=["POST", "OPTIONS"])
def ask():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Question is required"}), 400

    pii_triggers = ["@", "pan", "aadhaar"]
    digit_count = sum(1 for c in question if c.isdigit())
    if any(t in question.lower() for t in pii_triggers) or digit_count > 7:
        return jsonify({
            "answer": "Please do not share personal identifiers here.",
            "source": "",
        })

    advice_triggers = [
        "should i", "buy", "sell", "recommend", "best fund",
        "which is better", "worth investing",
    ]
    if any(t in question.lower() for t in advice_triggers):
        return jsonify({
            "answer": (
                "I only provide factual scheme information — no investment advice. "
                "Please consult a SEBI-registered advisor."
            ),
            "source": "https://www.amfiindia.com",
        })

    try:
        answer, source_url = get_answer(question)
        llm_answer = call_llm(question, answer)
        return jsonify({"answer": llm_answer, "source": source_url})
    except Exception as exc:
        app.logger.exception("Error handling /ask")
        return jsonify({"error": str(exc)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "message": "FundBot backend is running",
        "openai_configured": _get_openai_client() is not None,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
