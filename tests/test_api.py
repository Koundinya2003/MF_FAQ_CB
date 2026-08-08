"""End-to-end HTTP behaviour, with the LLM disabled so answers are deterministic."""

from __future__ import annotations

import json

import pytest

from fundbot.app import create_app


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    """Force the extractive path: no network, no key, fully reproducible."""
    monkeypatch.setenv("FUNDBOT_DISABLE_LLM", "1")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def ask(client, question):
    response = client.post("/api/ask", json={"question": question})
    return response, response.get_json()


class TestAsk:
    def test_answers_a_covered_question(self, client):
        response, body = ask(client, "What is the exit load for Mirae Asset Large Cap Fund?")
        assert response.status_code == 200
        assert body["kind"] == "answer"
        assert "1%" in body["answer"]
        assert body["source"].startswith("https://www.miraeassetmf.co.in")
        assert body["used_llm"] is False

    def test_bare_path_also_works(self, client):
        """Local dev hits /ask; Vercel hits /api/ask. Both are registered."""
        response = client.post("/ask", json={"question": "what is a SIP"})
        assert response.status_code == 200
        assert response.get_json()["kind"] == "answer"

    def test_cites_the_matching_fund(self, client):
        _, body = ask(client, "benchmark index of the midcap fund")
        assert "midcap" in body["source"]
        assert "midcap.benchmark" in body["matched"]

    def test_unknown_topic_declines(self, client):
        _, body = ask(client, "what is the weather in Mumbai tomorrow")
        assert body["kind"] == "no_answer"
        assert "could not find" in body["answer"].lower()

    def test_advice_is_refused(self, client):
        _, body = ask(client, "should I invest in the ELSS fund")
        assert body["kind"] == "refusal_advice"
        assert "amfiindia" in body["source"]

    def test_other_fund_house_is_out_of_scope(self, client):
        """Must not answer with a Mirae figure — the most misleading failure here."""
        _, body = ask(client, "what is the expense ratio of HDFC Top 100 fund")
        assert body["kind"] == "refusal_scope"
        assert "99" not in body["answer"]
        assert "Mirae Asset" in body["answer"]

    def test_pii_is_refused_without_echo(self, client):
        _, body = ask(client, "my PAN is ABCDE1234F, what is the expense ratio")
        assert body["kind"] == "refusal_pii"
        assert "ABCDE1234F" not in json.dumps(body)

    @pytest.mark.parametrize("payload", [{}, {"question": ""}, {"question": "   "}, {"question": 42}])
    def test_bad_payloads_are_400(self, client, payload):
        assert client.post("/api/ask", json=payload).status_code == 400

    def test_overlong_question_is_truncated_not_rejected(self, client):
        response, body = ask(client, "expense ratio of large cap fund " + "x" * 5000)
        assert response.status_code == 200
        assert body["kind"] == "answer"

    def test_response_shape_is_stable(self, client):
        _, body = ask(client, "minimum sip for large cap fund")
        assert set(body) == {
            "answer",
            "source",
            "source_label",
            "last_updated",
            "kind",
            "confidence",
            "used_llm",
            "matched",
        }


class TestHealth:
    def test_reports_corpus_and_llm_state(self, client):
        body = client.get("/api/health").get_json()
        assert body["status"] == "ok"
        assert body["corpus"]["documents"] > 0
        assert body["llm"]["enabled"] is False
        assert body["llm"]["provider"] == "openrouter"

    def test_never_leaks_the_api_key(self, client, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-secret-value")
        body = client.get("/api/health").get_json()
        assert "sk-or-v1-secret-value" not in json.dumps(body)


class TestDebugRoute:
    def test_hidden_by_default(self, client):
        assert client.post("/api/search", json={"question": "sip"}).status_code == 404

    def test_available_when_enabled(self, client, monkeypatch):
        monkeypatch.setenv("FUNDBOT_DEBUG", "1")
        body = client.post("/api/search", json={"question": "exit load midcap"}).get_json()
        assert body["detected_fund"] == "midcap"
        assert body["hits"]


class TestCORS:
    def test_allows_configured_origin(self, client, monkeypatch):
        monkeypatch.setenv("ALLOWED_ORIGINS", "https://example.test")
        response = client.post(
            "/api/ask",
            json={"question": "what is a sip"},
            headers={"Origin": "https://example.test"},
        )
        assert response.headers["Access-Control-Allow-Origin"] == "https://example.test"

    def test_rejects_unknown_origin(self, client, monkeypatch):
        monkeypatch.setenv("ALLOWED_ORIGINS", "https://example.test")
        response = client.post(
            "/api/ask",
            json={"question": "what is a sip"},
            headers={"Origin": "https://evil.test"},
        )
        assert "Access-Control-Allow-Origin" not in response.headers
