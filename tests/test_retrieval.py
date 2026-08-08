"""Retrieval behaviour: does the right passage come back for a paraphrased question?"""

from __future__ import annotations

import pytest

from fundbot.knowledge import get_retriever
from fundbot.retrieval import MIN_CONFIDENCE
from fundbot.text import expand, tokenize


@pytest.fixture(scope="module")
def retriever():
    return get_retriever()


class TestTokenizer:
    def test_lowercases_and_drops_stopwords(self):
        assert tokenize("What is the Exit Load?") == ["what", "exit", "load"]

    def test_strips_rupee_symbol(self):
        assert "rs" in tokenize("minimum is ₹99")

    def test_singularises_plurals(self):
        assert tokenize("charges fees funds") == ["charge", "fee", "fund"]

    def test_keeps_short_words_ending_in_s(self):
        # "is" is a stopword; the point is that stripping must not mangle it.
        assert tokenize("nav") == ["nav"]

    def test_expansion_keeps_original_tokens(self):
        expanded = expand(["ter"])
        assert expanded[0] == "ter"
        assert "expense" in expanded and "ratio" in expanded


class TestFundDetection:
    @pytest.mark.parametrize(
        "question,expected",
        [
            ("expense ratio of the large cap fund", "large_cap"),
            ("Mirae Asset Midcap Fund exit load", "midcap"),
            ("minimum sip for the ELSS tax saver", "elss"),
            ("flexicap benchmark", "flexi_cap"),
            ("what is an exit load", None),
        ],
    )
    def test_detects_named_fund(self, retriever, question, expected):
        assert retriever.detect_fund(question) == expected

    def test_two_funds_named_is_ambiguous(self, retriever):
        # Neither should win silently; ranking decides instead.
        assert retriever.detect_fund("large cap vs midcap benchmark") is None


class TestDefinitionIntent:
    @pytest.mark.parametrize(
        "question",
        ["what is a SIP", "explain exit load", "what does NAV mean", "define ELSS"],
    )
    def test_definition_questions(self, retriever, question):
        assert retriever.is_definition_question(question) is True

    @pytest.mark.parametrize(
        "question",
        ["exit load of the midcap fund", "minimum sip for large cap fund"],
    )
    def test_lookup_questions(self, retriever, question):
        assert retriever.is_definition_question(question) is False


class TestRanking:
    @pytest.mark.parametrize(
        "question,expected_id",
        [
            # Exact phrasing.
            ("What is the expense ratio of Mirae Asset Large Cap Fund?", "large_cap.expense_ratio"),
            # Paraphrases the keyword matcher in the old build could not handle.
            ("how much does the midcap fund charge every year", "midcap.expense_ratio"),
            ("what happens if I take my money out of the flexi cap fund early", "flexi_cap.exit_load"),
            ("smallest amount I can put into the tax saver monthly", "elss.sip_minimum"),
            ("which index is the midcap fund measured against", "midcap.benchmark"),
            ("how long is my money stuck in the elss fund", "elss.elss_lockin"),
            # Definition questions must reach the general explainers.
            ("what is a SIP", "general.what_is_sip"),
            ("what does NAV mean", "general.what_is_nav"),
            ("explain the difference between direct and regular plans", "general.direct_vs_regular"),
            ("how do I get my capital gains statement", "general.statement_download"),
        ],
    )
    def test_top_hit(self, retriever, question, expected_id):
        hits = retriever.search(question, top_k=3)
        assert hits, f"no hits for {question!r}"
        assert hits[0].document.id == expected_id, [h.document.id for h in hits]

    def test_fund_disambiguation(self, retriever):
        """The named fund must win even though all four docs share their wording."""
        for fund in ("large_cap", "flexi_cap", "midcap"):
            label = fund.replace("_", " ")
            hits = retriever.search(f"exit load for the {label} fund")
            assert hits[0].document.fund == fund, (label, hits[0].document.id)

    def test_results_are_sorted(self, retriever):
        hits = retriever.search("expense ratio large cap fund", top_k=5)
        scores = [hit.score for hit in hits]
        assert scores == sorted(scores, reverse=True)

    def test_empty_query_returns_nothing(self, retriever):
        assert retriever.search("") == []
        assert retriever.search("the and of") == []


class TestConfidence:
    @pytest.mark.parametrize(
        "question",
        [
            "how do I bake sourdough bread",
            "what is the capital of Mongolia",
            "who won the 2019 cricket world cup",
        ],
    )
    def test_off_topic_is_below_threshold(self, retriever, question):
        hits = retriever.search(question)
        top = hits[0].confidence if hits else 0.0
        assert top < MIN_CONFIDENCE, f"{question!r} scored {top}"

    @pytest.mark.parametrize(
        "question",
        [
            "What is the expense ratio of Mirae Asset Large Cap Fund?",
            "minimum sip for the midcap fund",
            "what is an exit load",
        ],
    )
    def test_on_topic_clears_threshold(self, retriever, question):
        hits = retriever.search(question)
        assert hits and hits[0].confidence >= MIN_CONFIDENCE
