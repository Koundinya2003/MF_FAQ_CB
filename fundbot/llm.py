"""OpenRouter client.

Uses `urllib` from the standard library rather than `requests` or the OpenAI SDK
so the deployed function carries no HTTP dependency at all — it keeps the Vercel
bundle small and the cold start short.

The LLM only ever *rephrases* text that retrieval already selected. It is never
the source of a fact, and every failure path falls back to the retrieved text
verbatim, so a missing key, a rate limit or a timeout degrades the wording of an
answer but never its correctness or availability.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

from . import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are FundBot, a facts-only assistant for Mirae Asset mutual fund schemes."
)

_PROMPT_TEMPLATE = """Rewrite the source material below into a direct answer to the user's question.

Rules:
- Use ONLY the source material. Add nothing from your own knowledge.
- Never state a number, percentage, date or fund name that is not in the source material.
- Keep it to three sentences at most, in plain English.
- No investment advice, recommendations, opinions or predictions.
- If the source material does not answer the question, reply with exactly: {no_answer}

Source material:
\"\"\"
{context}
\"\"\"

User question: {question}

Answer:"""

NO_ANSWER_SENTINEL = "I could not find that detail in my sources."


@dataclass(frozen=True)
class LLMResult:
    text: str
    used_llm: bool
    error: str = ""


def _post(url: str, payload: dict, headers: dict[str, str], timeout: float) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def polish(question: str, context: str) -> LLMResult:
    """Rephrase `context` as an answer to `question`.

    Returns `context` unchanged whenever the LLM is unavailable or misbehaves.
    """
    if not config.llm_enabled():
        return LLMResult(text=context, used_llm=False, error="llm_disabled")

    headers = {
        "Authorization": f"Bearer {config.openrouter_api_key()}",
        "Content-Type": "application/json",
        "X-Title": "FundBot",
    }
    referer = config.public_url()
    if referer:
        headers["HTTP-Referer"] = referer

    payload = {
        "model": config.openrouter_model(),
        "temperature": 0.1,
        "max_tokens": 220,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _PROMPT_TEMPLATE.format(
                    context=context, question=question, no_answer=NO_ANSWER_SENTINEL
                ),
            },
        ],
    }

    url = f"{config.openrouter_base_url()}/chat/completions"
    try:
        data = _post(url, payload, headers, config.llm_timeout())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200] if exc.fp else ""
        logger.warning("OpenRouter HTTP %s: %s", exc.code, detail)
        return LLMResult(text=context, used_llm=False, error=f"http_{exc.code}")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("OpenRouter unreachable: %s", exc)
        return LLMResult(text=context, used_llm=False, error="unreachable")
    except json.JSONDecodeError:
        logger.warning("OpenRouter returned non-JSON")
        return LLMResult(text=context, used_llm=False, error="bad_json")

    # OpenRouter reports upstream provider failures in-band with HTTP 200.
    if isinstance(data.get("error"), dict):
        message = str(data["error"].get("message", ""))[:200]
        logger.warning("OpenRouter error payload: %s", message)
        return LLMResult(text=context, used_llm=False, error="provider_error")

    try:
        text = (data["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError):
        logger.warning("Unexpected OpenRouter response shape")
        return LLMResult(text=context, used_llm=False, error="bad_shape")

    if not text:
        return LLMResult(text=context, used_llm=False, error="empty")

    # A model that claims it cannot answer is less useful than the retrieved
    # passage the retriever was confident enough to return, so prefer the source.
    if NO_ANSWER_SENTINEL.lower().rstrip(".") in text.lower():
        return LLMResult(text=context, used_llm=False, error="model_no_answer")

    return LLMResult(text=text, used_llm=True)
