"""Hybrid BM25 + TF-IDF retrieval over the FundBot knowledge base.

Two scorers run over the same weighted-field term counts:

* **BM25F-lite** drives the ranking. Field weights are folded into the term
  frequencies before scoring, which is why `title` and `questions` matter more
  than the answer prose itself.
* **TF-IDF cosine, scaled by IDF coverage** supplies the *confidence*. Cosine
  lives on a fixed 0..1 scale regardless of query length, so it is the only one
  of the two that can be compared against an absolute "do I actually know this?"
  threshold — BM25 scores are unbounded and query-dependent, so thresholding on
  them directly would be meaningless.

  Cosine alone is not enough, though. A short off-topic question that happens to
  share one rare word scores alarmingly well: "what is the capital of Mongolia"
  hit the capital-gains document at 0.29 because *capital* is rare and the query
  vector had almost nothing else in it. Coverage fixes that by asking what
  fraction of the question's IDF mass the document actually accounts for. Terms
  the index has never seen are charged at the maximum IDF, so *Mongolia* and
  *sourdough* are expensive to ignore and drag confidence below the floor.

A fund-affinity pass then rewards documents belonging to the scheme the user
named and suppresses the other three, which is what stops "exit load of the
midcap fund" from answering with the large cap figure.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable

from .text import bigrams, expand, tokenize

# BM25 free parameters. Standard Okapi defaults; b is on the low side because the
# documents are short and their length carries little signal.
BM25_K1 = 1.4
BM25_B = 0.6

# How many times each field's tokens are counted into the term frequencies.
FIELD_WEIGHTS = {
    "title": 3,
    "questions": 3,
    "keywords": 2,
    "fund_names": 2,
    "text": 1,
}

# Adjacent-token phrases are indexed alongside unigrams at this share of the
# field weight. Full weight would let a single matched phrase swamp the unigram
# evidence; zero loses the phrase signal entirely.
BIGRAM_WEIGHT = 2

# Ranking blend. BM25 leads; cosine mostly breaks ties between near-identical docs.
BM25_WEIGHT = 0.75
COSINE_WEIGHT = 0.25

# Fund affinity multipliers, applied after blending.
SAME_FUND_BOOST = 1.35
OTHER_FUND_PENALTY = 0.30
GENERAL_WHEN_FUND_NAMED = 0.75
GENERAL_WHEN_DEFINITION = 1.30
FUND_DOC_WHEN_DEFINITION = 0.80

# Confidence floor below which the retriever reports "I don't know" rather than
# guessing. Chosen from scripts/evaluate.py --sweep: the hardest off-topic
# question in that set peaks at 0.052, so 0.06 answers 92.7% of the labelled
# paraphrases with zero false answers. Re-run the sweep after any scoring change;
# the value is meaningless if the scoring underneath it moves.
MIN_CONFIDENCE = 0.06

# Matched against the raw question, not the token stream: `tokenize` drops "is",
# "are" and "does" as stopwords, so a token-level "what is" marker could never fire.
_DEFINITION_RE = re.compile(
    r"\b(?:what|which)\s+(?:is|are|does|do)\b"
    r"|\bwhat\b.*\bmeans?\b"
    r"|\b(?:explain|define|definition|meaning)\b",
    re.IGNORECASE,
)


@dataclass
class Document:
    """One retrievable fact, with the fields that get indexed and the citation."""

    id: str
    fund: str
    topic: str
    title: str
    text: str
    questions: list[str]
    keywords: list[str]
    source_url: str
    source_label: str
    last_updated: str

    # Populated by the index.
    term_freqs: Counter[str] = field(default_factory=Counter, repr=False)
    length: float = field(default=0.0, repr=False)
    tfidf: dict[str, float] = field(default_factory=dict, repr=False)
    tfidf_norm: float = field(default=0.0, repr=False)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Document":
        return cls(
            id=raw["id"],
            fund=raw.get("fund", "general"),
            topic=raw.get("topic", ""),
            title=raw.get("title", ""),
            text=raw["text"],
            questions=list(raw.get("questions", [])),
            keywords=list(raw.get("keywords", [])),
            source_url=raw.get("source_url", ""),
            source_label=raw.get("source_label", ""),
            last_updated=raw.get("last_updated", ""),
        )


@dataclass
class Hit:
    document: Document
    score: float
    confidence: float


class Retriever:
    """In-memory hybrid index. Built once per process and reused across requests."""

    def __init__(self, documents: Iterable[dict[str, Any]], funds: dict[str, Any]):
        self.funds = funds
        self.documents = [Document.from_dict(d) for d in documents]
        if not self.documents:
            raise ValueError("Knowledge base contains no documents")

        # fund key -> the alias token sequences that identify it in a question.
        self._fund_aliases: dict[str, list[list[str]]] = {}
        for key, meta in funds.items():
            phrases = [meta.get("name", ""), *meta.get("aliases", [])]
            self._fund_aliases[key] = [t for t in (tokenize(p) for p in phrases) if t]

        self._build()

    # -- index construction ------------------------------------------------

    def _document_fields(self, doc: Document) -> dict[str, list[str]]:
        fund_meta = self.funds.get(doc.fund, {})
        fund_text = " ".join(
            [fund_meta.get("name", ""), fund_meta.get("category", ""), *fund_meta.get("aliases", [])]
        )
        return {
            "title": tokenize(doc.title),
            "questions": tokenize(" ".join(doc.questions)),
            "keywords": tokenize(" ".join(doc.keywords)),
            "fund_names": tokenize(fund_text),
            "text": tokenize(doc.text),
        }

    def _build(self) -> None:
        doc_freq: Counter[str] = Counter()

        for doc in self.documents:
            counts: Counter[str] = Counter()
            for field_name, tokens in self._document_fields(doc).items():
                weight = FIELD_WEIGHTS[field_name]
                for token in tokens:
                    counts[token] += weight
                for phrase in bigrams(tokens):
                    counts[phrase] += weight * BIGRAM_WEIGHT
            doc.term_freqs = counts
            doc.length = float(sum(counts.values()))
            doc_freq.update(counts.keys())

        self.total_docs = len(self.documents)
        self.avg_length = sum(d.length for d in self.documents) / self.total_docs

        # BM25 probabilistic idf, floored so that a term present in every document
        # contributes a small positive amount instead of going negative.
        self.bm25_idf = {
            term: max(
                0.05,
                math.log((self.total_docs - freq + 0.5) / (freq + 0.5) + 1.0),
            )
            for term, freq in doc_freq.items()
        }
        # Smoothed idf for the cosine side.
        self.tfidf_idf = {
            term: math.log((self.total_docs + 1) / (freq + 1)) + 1.0
            for term, freq in doc_freq.items()
        }

        # Charged against query terms the index has never seen, so an unknown word
        # costs as much as the rarest known one.
        self.max_idf = max(self.tfidf_idf.values())

        for doc in self.documents:
            vector = {
                term: (1.0 + math.log(count)) * self.tfidf_idf[term]
                for term, count in doc.term_freqs.items()
            }
            doc.tfidf = vector
            doc.tfidf_norm = math.sqrt(sum(v * v for v in vector.values())) or 1.0

    # -- query analysis ----------------------------------------------------

    def detect_fund(self, question: str) -> str | None:
        """Return the single fund named in the question, or None.

        None is returned when no fund is named *and* when more than one is, since
        "large cap vs midcap" is a comparison — quietly boosting whichever alias
        happened to be longer would answer a different question than the one asked.
        """
        tokens = tokenize(question)
        matched = {
            key
            for key, alias_lists in self._fund_aliases.items()
            if any(_contains_subsequence(tokens, alias) for alias in alias_lists)
        }
        return matched.pop() if len(matched) == 1 else None

    @staticmethod
    def is_definition_question(question: str) -> bool:
        """True for "what is a SIP" style questions that want the general explainer."""
        return bool(_DEFINITION_RE.search(question))

    # -- scoring -----------------------------------------------------------

    def _bm25(self, doc: Document, query_counts: Counter[str]) -> float:
        score = 0.0
        norm = BM25_K1 * (1 - BM25_B + BM25_B * doc.length / self.avg_length)
        for term, q_count in query_counts.items():
            tf = doc.term_freqs.get(term)
            if not tf:
                continue
            idf = self.bm25_idf.get(term, 0.0)
            score += idf * q_count * (tf * (BM25_K1 + 1)) / (tf + norm)
        return score

    def _cosine(self, doc: Document, query_vector: dict[str, float], query_norm: float) -> float:
        if not query_vector:
            return 0.0
        # Iterate the shorter side; query vectors are always tiny.
        dot = sum(weight * doc.tfidf.get(term, 0.0) for term, weight in query_vector.items())
        if dot <= 0.0:
            return 0.0
        return dot / (query_norm * doc.tfidf_norm)

    def _idf_coverage(self, doc: Document, coverage_terms: set[str], total_idf: float) -> float:
        """Share of the question's IDF mass this document accounts for.

        Uses the *unexpanded* query terms — words and phrases the user actually
        typed. Synonyms exist to help ranking find the right document, not to let
        a document claim credit for wording nobody used.
        """
        if total_idf <= 0.0:
            return 0.0
        matched = sum(
            self.tfidf_idf.get(term, self.max_idf)
            for term in coverage_terms
            if term in doc.term_freqs
        )
        return matched / total_idf

    def search(self, question: str, top_k: int = 3) -> list[Hit]:
        """Rank documents for a question. Results are sorted best-first."""
        base_tokens = tokenize(question)
        if not base_tokens:
            return []

        base_phrases = bigrams(base_tokens)
        query_counts = Counter(expand(base_tokens) + base_phrases)

        query_vector = {
            term: (1.0 + math.log(count)) * self.tfidf_idf[term]
            for term, count in query_counts.items()
            if term in self.tfidf_idf
        }
        query_norm = math.sqrt(sum(v * v for v in query_vector.values())) or 1.0

        # Total IDF mass of what the user actually typed, unknown terms included.
        coverage_terms = set(base_tokens) | set(base_phrases)
        total_idf = sum(self.tfidf_idf.get(term, self.max_idf) for term in coverage_terms)

        named_fund = self.detect_fund(question)
        definition = self.is_definition_question(question)

        raw: list[tuple[float, float, Document]] = []
        max_bm25 = 0.0
        for doc in self.documents:
            bm25 = self._bm25(doc, query_counts)
            if bm25 <= 0.0:
                continue
            cosine = self._cosine(doc, query_vector, query_norm)
            max_bm25 = max(max_bm25, bm25)
            raw.append((bm25, cosine, doc))

        if not raw:
            return []

        hits: list[Hit] = []
        for bm25, cosine, doc in raw:
            blended = BM25_WEIGHT * (bm25 / max_bm25) + COSINE_WEIGHT * cosine
            blended *= self._affinity(doc, named_fund, definition)
            coverage = self._idf_coverage(doc, coverage_terms, total_idf)
            hits.append(Hit(document=doc, score=blended, confidence=cosine * coverage))

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]

    @staticmethod
    def _affinity(doc: Document, named_fund: str | None, definition: bool) -> float:
        """Post-ranking multiplier for fund affinity and definition intent.

        The two are mutually exclusive by design. "What is the expense ratio of
        the Large Cap Fund?" is syntactically a definition question, but naming a
        scheme makes it a lookup — so once a fund is identified, definition intent
        is ignored rather than pulling the answer toward the general explainers.
        """
        is_general = doc.fund == "general"

        if named_fund is not None:
            if doc.fund == named_fund:
                return SAME_FUND_BOOST
            return GENERAL_WHEN_FUND_NAMED if is_general else OTHER_FUND_PENALTY

        if definition:
            return GENERAL_WHEN_DEFINITION if is_general else FUND_DOC_WHEN_DEFINITION

        return 1.0


def _contains_subsequence(haystack: list[str], needle: list[str]) -> bool:
    """True if `needle` appears as a contiguous run inside `haystack`."""
    if not needle or len(needle) > len(haystack):
        return False
    first = needle[0]
    span = len(needle)
    for i, token in enumerate(haystack):
        if token == first and haystack[i : i + span] == needle:
            return True
    return False
