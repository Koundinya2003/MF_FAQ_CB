"""Knowledge base loading and the process-wide retriever singleton."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from .retrieval import Retriever

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent
DEFAULT_KB_PATH = PROJECT_ROOT / "data" / "knowledge_base.json"


def kb_path() -> Path:
    override = os.environ.get("FUNDBOT_KB_PATH", "").strip()
    return Path(override) if override else DEFAULT_KB_PATH


@lru_cache(maxsize=1)
def load_knowledge_base() -> dict[str, Any]:
    path = kb_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"Knowledge base not found at {path}. "
            "On Vercel this usually means data/** is missing from includeFiles in vercel.json."
        )
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    documents = data.get("documents")
    if not documents:
        raise ValueError(f"Knowledge base at {path} has no documents")

    seen: set[str] = set()
    for doc in documents:
        for required in ("id", "text", "source_url"):
            if not doc.get(required):
                raise ValueError(f"Document {doc.get('id', '<unknown>')} is missing '{required}'")
        if doc["id"] in seen:
            raise ValueError(f"Duplicate document id: {doc['id']}")
        seen.add(doc["id"])

    return data


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    """Built once per process; warm serverless invocations reuse the same index."""
    data = load_knowledge_base()
    return Retriever(documents=data["documents"], funds=data.get("funds", {}))


def corpus_stats() -> dict[str, Any]:
    data = load_knowledge_base()
    return {
        "documents": len(data["documents"]),
        "funds": len(data.get("funds", {})),
        "version": data.get("version", "unknown"),
        "corpus_last_updated": data.get("corpus_last_updated", "unknown"),
    }
