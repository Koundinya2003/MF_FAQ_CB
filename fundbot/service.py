"""The answer pipeline: guardrails -> retrieval -> optional LLM rephrasing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import config, guards, llm
from .knowledge import get_retriever
from .retrieval import MIN_CONFIDENCE, Hit

MAX_QUESTION_CHARS = 500

NO_ANSWER_TEXT = (
    "I could not find that in my sources. I cover expense ratios, exit loads, SIP and "
    "lump sum minimums, benchmarks, riskometer levels and lock-in rules for four Mirae "
    "Asset schemes — the Large Cap, Flexi Cap, ELSS Tax Saver and Midcap funds. "
    "Please check the official site for anything outside that."
)
NO_ANSWER_SOURCE = "https://www.miraeassetmf.co.in"

# A supporting passage is only added to the prompt if it scores at least this
# fraction of the top hit. Without the gate a weak third result drags in a
# different fund's numbers and invites the model to blend them.
SUPPORTING_HIT_RATIO = 0.6


@dataclass
class Answer:
    answer: str
    source: str
    source_label: str = ""
    last_updated: str = ""
    kind: str = "answer"  # answer | no_answer | refusal_pii | refusal_advice | invalid
    confidence: float = 0.0
    used_llm: bool = False
    matched: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "source": self.source,
            "source_label": self.source_label,
            "last_updated": self.last_updated,
            "kind": self.kind,
            "confidence": round(self.confidence, 4),
            "used_llm": self.used_llm,
            "matched": self.matched,
        }


def _build_context(hits: list[Hit]) -> str:
    """Assemble the LLM prompt context from the top hit plus close-scoring support."""
    top_score = hits[0].score
    passages: list[str] = []
    for index, hit in enumerate(hits):
        if index > 0 and hit.score < SUPPORTING_HIT_RATIO * top_score:
            continue
        doc = hit.document
        passages.append(f"[{doc.title}]\n{doc.text}")
    return "\n\n".join(passages)


def answer_question(question: str) -> Answer:
    """Full pipeline for one user question. Never raises for ordinary bad input."""
    cleaned = (question or "").strip()
    if not cleaned:
        return Answer(
            answer="Please type a question about Mirae Asset mutual funds.",
            source="",
            kind="invalid",
        )

    if len(cleaned) > MAX_QUESTION_CHARS:
        cleaned = cleaned[:MAX_QUESTION_CHARS]

    blocked = guards.screen(cleaned)
    if blocked is not None:
        return Answer(
            answer=blocked.answer,
            source=blocked.source,
            kind=f"refusal_{blocked.kind}",
        )

    hits = get_retriever().search(cleaned, top_k=config.top_k())
    if not hits or hits[0].confidence < MIN_CONFIDENCE:
        return Answer(
            answer=NO_ANSWER_TEXT,
            source=NO_ANSWER_SOURCE,
            source_label="miraeassetmf.co.in",
            kind="no_answer",
            confidence=hits[0].confidence if hits else 0.0,
        )

    best = hits[0].document
    result = llm.polish(cleaned, _build_context(hits))

    # Without the LLM the reply must be a single clean passage — the prompt context
    # can carry several titled passages, which is prompt material, not user copy.
    answer_text = result.text if result.used_llm else best.text

    return Answer(
        answer=answer_text,
        source=best.source_url,
        source_label=best.source_label,
        last_updated=best.last_updated,
        kind="answer",
        confidence=hits[0].confidence,
        used_llm=result.used_llm,
        matched=[hit.document.id for hit in hits],
    )
