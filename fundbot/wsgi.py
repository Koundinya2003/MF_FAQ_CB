"""Shared WSGI entrypoint for the Vercel functions in `api/`.

Importing this module builds the retrieval index as part of the cold start, so
the first request of a new instance does not pay for it.
"""

from __future__ import annotations

import logging

from .app import app
from .knowledge import get_retriever

logger = logging.getLogger(__name__)

try:
    get_retriever()
except Exception:  # pragma: no cover - /health surfaces the failure to callers
    logger.exception("Failed to warm the retrieval index during cold start")

__all__ = ["app"]
