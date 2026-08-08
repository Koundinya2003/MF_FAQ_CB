"""Guardrails: block what must be blocked, and — just as important — nothing else."""

from __future__ import annotations

import pytest

from fundbot import guards


class TestPII:
    @pytest.mark.parametrize(
        "question",
        [
            "my email is investor@example.com, send details",
            "my PAN is ABCDE1234F",
            "aadhaar 1234 5678 9012",
            "call me on 9876543210",
            "my folio number is 12345",
            "what is my account number 123456789012",
            "here is my OTP 445566",
        ],
    )
    def test_blocks_identifiers(self, question):
        result = guards.check_pii(question)
        assert result is not None, question
        assert result.kind == "pii"

    @pytest.mark.parametrize(
        "question",
        [
            "What is the expense ratio of Mirae Asset Large Cap Fund?",
            "exit load after 365 days",
            "is the benchmark nifty 100 or nifty 500",
            "what is the lock-in for ELSS, 3 years?",
            "minimum sip is 99 rupees?",
            "midcap 150 index",
        ],
    )
    def test_allows_ordinary_numbers(self, question):
        # The old build blocked anything with more than seven digits, which caught
        # legitimate questions about index names and amounts.
        assert guards.check_pii(question) is None, question


class TestAdvice:
    @pytest.mark.parametrize(
        "question",
        [
            "should I invest in the midcap fund",
            "which fund is better, large cap or flexi cap",
            "what is the best fund for me",
            "is it a good time to invest",
            "can you recommend a scheme",
            "is the elss fund worth investing in",
            "will the NAV go up next year",
            "how much return will I get",
            "predict the performance of the midcap fund",
        ],
    )
    def test_blocks_advice(self, question):
        result = guards.check_advice(question)
        assert result is not None, question
        assert result.kind == "advice"

    @pytest.mark.parametrize(
        "question",
        [
            # These contain transaction words but ask for facts. Blocking them
            # was the most damaging false positive in the previous build.
            "what is the exit load if I sell within a year",
            "what is the minimum amount to buy units of the large cap fund",
            "how do I redeem my ELSS units after the lock-in",
            "what is the best way to read a riskometer",
            "what is the expense ratio of the flexi cap fund",
            "how are equity mutual funds taxed",
        ],
    )
    def test_allows_factual_questions(self, question):
        assert guards.check_advice(question) is None, question


class TestScope:
    @pytest.mark.parametrize(
        "question",
        [
            "what is the expense ratio of HDFC Top 100 fund",
            "minimum sip for SBI bluechip fund",
            "exit load on Axis midcap fund",
            "what is the benchmark for Parag Parikh Flexi Cap",
            "riskometer of Nippon India small cap",
            "expense ratio of the ICICI Prudential technology fund",
        ],
    )
    def test_blocks_other_fund_houses(self, question):
        """These share almost all their vocabulary with the corpus, so retrieval
        answers them confidently with a Mirae figure. Only an explicit scope check
        catches them."""
        result = guards.check_scope(question)
        assert result is not None, question
        assert result.kind == "scope"

    @pytest.mark.parametrize(
        "question",
        [
            "what is the expense ratio of Mirae Asset Large Cap Fund",
            "minimum sip for the midcap fund",
            "what is a SIP",
            "how are equity mutual funds taxed",
        ],
    )
    def test_allows_in_scope_questions(self, question):
        assert guards.check_scope(question) is None, question

    def test_naming_mirae_alongside_another_amc_is_not_out_of_scope(self):
        assert guards.check_scope("how does Mirae compare to HDFC on TER") is None


class TestScreen:
    def test_scope_beats_advice(self):
        # "best fund" would trip the advice guard, but the more specific and more
        # useful answer is that the scheme is not covered at all.
        result = guards.screen("is the HDFC flexi cap the best fund")
        assert result is not None and result.kind == "scope"

    def test_pii_takes_precedence(self):
        # A question that trips both must never echo the identifier onward.
        result = guards.screen("should I invest? my PAN is ABCDE1234F")
        assert result is not None and result.kind == "pii"

    def test_clean_question_passes(self):
        assert guards.screen("what is the benchmark for the midcap fund") is None
