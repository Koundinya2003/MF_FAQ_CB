"""Flask application factory.

Every endpoint is registered twice: bare (`/ask`) and namespaced (`/api/ask`).
On Vercel the browser calls `/api/ask` because that prefix is what routes to the
Python function; running locally the same app also answers `/ask`. Registering
both means one codebase serves both without a rewrite that has to rewrite paths.

CORS is hand-rolled rather than pulled in from flask-cors: it is roughly fifteen
lines, and in the default Vercel deployment the frontend is same-origin so it is
only ever needed for local dev and split-host setups.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Callable

from flask import Flask, Response, jsonify, request, send_from_directory

from . import config
from .knowledge import corpus_stats, get_retriever
from .service import answer_question

logger = logging.getLogger(__name__)

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"

# 16 KB is far more than any legitimate question and keeps oversized bodies from
# being buffered at all.
MAX_CONTENT_LENGTH = 16 * 1024


def _register(app: Flask, rule: str, **options: Any) -> Callable:
    """Register a view at both `<rule>` and `/api<rule>`."""

    def decorator(view: Callable) -> Callable:
        app.add_url_rule(rule, view.__name__, view, **options)
        app.add_url_rule(f"/api{rule}", f"{view.__name__}_api", view, **options)
        return view

    return decorator


def _resolve_cors_origin(origin: str) -> str | None:
    if not origin:
        return None
    allowed = config.allowed_origins()
    if "*" in allowed:
        return "*"
    return origin if origin.rstrip("/") in allowed else None


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    app.config["JSON_SORT_KEYS"] = False

    @app.after_request
    def add_cors_headers(response: Response) -> Response:
        allowed = _resolve_cors_origin(request.headers.get("Origin", ""))
        if allowed:
            response.headers["Access-Control-Allow-Origin"] = allowed
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Max-Age"] = "86400"
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return response

    @_register(app, "/ask", methods=["POST", "OPTIONS"])
    def ask() -> Response | tuple[Response, int]:
        if request.method == "OPTIONS":
            return Response(status=204)

        payload = request.get_json(silent=True) or {}
        question = payload.get("question")
        if not isinstance(question, str) or not question.strip():
            return jsonify({"error": "A non-empty 'question' string is required."}), 400

        try:
            return jsonify(answer_question(question).to_dict())
        except Exception:
            # Anything reaching here is a bug, not bad input. Log it with the stack
            # but never return internals to the browser.
            logger.exception("Unhandled error answering question")
            return jsonify({"error": "Internal error while answering."}), 500

    @_register(app, "/health", methods=["GET"])
    def health() -> Response:
        payload: dict[str, Any] = {
            "status": "ok",
            "service": "fundbot",
            "llm": {
                "enabled": config.llm_enabled(),
                "provider": "openrouter",
                "model": config.openrouter_model(),
            },
        }
        try:
            retriever = get_retriever()
            payload["corpus"] = corpus_stats()
            payload["corpus"]["indexed_terms"] = len(retriever.bm25_idf)
        except Exception as exc:
            payload["status"] = "degraded"
            payload["corpus_error"] = str(exc)
        return jsonify(payload)

    @_register(app, "/search", methods=["POST"])
    def search() -> Response | tuple[Response, int]:
        """Retrieval-only view for tuning. Enable with FUNDBOT_DEBUG=1."""
        if os.environ.get("FUNDBOT_DEBUG", "").lower() not in {"1", "true", "yes"}:
            return jsonify({"error": "Not found"}), 404

        payload = request.get_json(silent=True) or {}
        question = str(payload.get("question", ""))
        retriever = get_retriever()
        hits = retriever.search(question, top_k=int(payload.get("top_k", 5)))
        return jsonify(
            {
                "question": question,
                "detected_fund": retriever.detect_fund(question),
                "definition_intent": retriever.is_definition_question(question),
                "hits": [
                    {
                        "id": hit.document.id,
                        "score": round(hit.score, 4),
                        "confidence": round(hit.confidence, 4),
                        "title": hit.document.title,
                    }
                    for hit in hits
                ],
            }
        )

    # Static frontend. On Vercel these paths never reach the function (the CDN
    # serves public/ directly); this exists so `python -m fundbot.app` runs the
    # whole app from one process locally.
    @app.route("/", methods=["GET"])
    def index() -> Response:
        return send_from_directory(PUBLIC_DIR, "index.html")

    @app.route("/<path:filename>", methods=["GET"])
    def static_files(filename: str) -> Response | tuple[Response, int]:
        target = PUBLIC_DIR / filename
        if not target.is_file():
            return jsonify({"error": "Not found"}), 404
        return send_from_directory(PUBLIC_DIR, filename)

    return app


app = create_app()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    port = int(os.environ.get("PORT", "8000"))
    logger.info("FundBot on http://localhost:%s (LLM enabled: %s)", port, config.llm_enabled())
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
