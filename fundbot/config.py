"""Environment-driven configuration.

Read lazily rather than at import time so that tests (and a `vercel dev` session
that picks up a new `.env`) see changes without reimporting the package.
"""

from __future__ import annotations

import os

# OpenRouter exposes several DeepSeek checkpoints on its free tier. The default
# below is the free general-purpose chat model; override OPENROUTER_MODEL to pin a
# different one (e.g. "deepseek/deepseek-r1:free") without touching code.
DEFAULT_MODEL = "deepseek/deepseek-chat-v3.1:free"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

# Same-origin on Vercel means production needs no CORS at all; these cover local
# dev servers and any static host you point at a deployed API.
DEFAULT_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
)


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def openrouter_api_key() -> str:
    return _env("OPENROUTER_API_KEY")


def openrouter_model() -> str:
    return _env("OPENROUTER_MODEL") or DEFAULT_MODEL


def openrouter_base_url() -> str:
    return (_env("OPENROUTER_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def llm_enabled() -> bool:
    if _env("FUNDBOT_DISABLE_LLM").lower() in {"1", "true", "yes"}:
        return False
    return bool(openrouter_api_key())


def llm_timeout() -> float:
    """Kept well under the platform function timeout so a slow model degrades
    to the extractive answer instead of failing the whole request."""
    try:
        return max(1.0, float(_env("LLM_TIMEOUT_SECONDS", "12")))
    except ValueError:
        return 12.0


def public_url() -> str:
    """Sent to OpenRouter as HTTP-Referer for attribution. Optional."""
    explicit = _env("APP_PUBLIC_URL")
    if explicit:
        return explicit
    vercel_url = _env("VERCEL_URL")
    return f"https://{vercel_url}" if vercel_url else ""


def allowed_origins() -> list[str]:
    raw = _env("ALLOWED_ORIGINS")
    if not raw:
        return list(DEFAULT_ORIGINS)
    if raw == "*":
        return ["*"]
    return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]


def top_k() -> int:
    try:
        return max(1, int(_env("RETRIEVAL_TOP_K", "3")))
    except ValueError:
        return 3
