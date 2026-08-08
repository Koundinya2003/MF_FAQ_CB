"""The LLM layer must degrade to the retrieved text on every failure path.

A wrong answer is worse than an unpolished one, so none of these cases may raise
or return invented text.
"""

from __future__ import annotations

import json
import urllib.error

import pytest

from fundbot import llm

CONTEXT = "Mirae Asset Large Cap Fund charges an exit load of 1% within 365 days."
QUESTION = "what is the exit load"


@pytest.fixture
def with_key(monkeypatch):
    monkeypatch.delenv("FUNDBOT_DISABLE_LLM", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")


def fake_response(payload):
    def _post(url, body, headers, timeout):
        return payload

    return _post


class TestDisabled:
    def test_no_key_returns_context(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        result = llm.polish(QUESTION, CONTEXT)
        assert result.text == CONTEXT
        assert result.used_llm is False
        assert result.error == "llm_disabled"

    def test_explicit_disable_flag_wins_over_key(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
        monkeypatch.setenv("FUNDBOT_DISABLE_LLM", "1")
        assert llm.polish(QUESTION, CONTEXT).used_llm is False


class TestSuccess:
    def test_uses_model_text(self, monkeypatch, with_key):
        monkeypatch.setattr(
            llm,
            "_post",
            fake_response({"choices": [{"message": {"content": "  Exit load is 1% within a year.  "}}]}),
        )
        result = llm.polish(QUESTION, CONTEXT)
        assert result.text == "Exit load is 1% within a year."
        assert result.used_llm is True

    def test_sends_the_configured_model(self, monkeypatch, with_key):
        monkeypatch.setenv("OPENROUTER_MODEL", "deepseek/deepseek-r1:free")
        captured = {}

        def _post(url, body, headers, timeout):
            captured.update({"url": url, "body": body, "headers": headers})
            return {"choices": [{"message": {"content": "ok"}}]}

        monkeypatch.setattr(llm, "_post", _post)
        llm.polish(QUESTION, CONTEXT)

        assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
        assert captured["body"]["model"] == "deepseek/deepseek-r1:free"
        assert captured["headers"]["Authorization"] == "Bearer sk-or-v1-test"
        assert CONTEXT in json.dumps(captured["body"])


class TestFailurePaths:
    @pytest.mark.parametrize(
        "exception,expected_error",
        [
            (urllib.error.URLError("boom"), "unreachable"),
            (TimeoutError(), "unreachable"),
            (OSError("socket closed"), "unreachable"),
        ],
    )
    def test_network_errors_fall_back(self, monkeypatch, with_key, exception, expected_error):
        def _raise(*args, **kwargs):
            raise exception

        monkeypatch.setattr(llm, "_post", _raise)
        result = llm.polish(QUESTION, CONTEXT)
        assert result.text == CONTEXT
        assert result.used_llm is False
        assert result.error == expected_error

    def test_http_error_falls_back(self, monkeypatch, with_key):
        def _raise(*args, **kwargs):
            raise urllib.error.HTTPError("url", 429, "Too Many Requests", {}, None)

        monkeypatch.setattr(llm, "_post", _raise)
        result = llm.polish(QUESTION, CONTEXT)
        assert result.text == CONTEXT
        assert result.error == "http_429"

    @pytest.mark.parametrize(
        "payload,expected_error",
        [
            ({"error": {"message": "rate limited"}}, "provider_error"),
            ({"choices": []}, "bad_shape"),
            ({"unexpected": True}, "bad_shape"),
            ({"choices": [{"message": {"content": ""}}]}, "empty"),
            ({"choices": [{"message": {"content": None}}]}, "empty"),
        ],
    )
    def test_bad_payloads_fall_back(self, monkeypatch, with_key, payload, expected_error):
        monkeypatch.setattr(llm, "_post", fake_response(payload))
        result = llm.polish(QUESTION, CONTEXT)
        assert result.text == CONTEXT
        assert result.used_llm is False
        assert result.error == expected_error

    def test_model_saying_it_cannot_answer_falls_back(self, monkeypatch, with_key):
        """Retrieval was confident; the retrieved passage beats a model shrug."""
        monkeypatch.setattr(
            llm,
            "_post",
            fake_response({"choices": [{"message": {"content": llm.NO_ANSWER_SENTINEL}}]}),
        )
        result = llm.polish(QUESTION, CONTEXT)
        assert result.text == CONTEXT
        assert result.error == "model_no_answer"
