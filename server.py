import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from anthropic import Anthropic
from topic_detection import get_answer

client = Anthropic()

def call_llm(question, context_text):
    """Call Claude Haiku with FundBot system prompt."""
    system_prompt = """You are FundBot, a factual FAQ assistant for Mirae Asset mutual funds. 
Provide only facts from the given source text. Limit your answer to 3 sentences maximum. 
Do not provide investment advice or opinions. If information is not in the source, say so."""
    
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Source context: {context_text}\n\nQuestion: {question}"
            }
        ]
    )
    return message.content[0].text

app = Flask(__name__)
CORS(app, resources={
    "/ask": {
        "origins": [
            "https://mf-faq.netlify.app",
            "http://127.0.0.1:5500",
            "http://localhost:5500"
        ]
    },
    "/health": {"origins": "*"}
})

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "Question is required"}), 400
    
    pii_triggers = ["@", "pan", "aadhaar"]
    if any(t in question.lower() for t in pii_triggers) or any(c.isdigit() for c in question if question.count(c) > 7):
        return jsonify({
            "answer": "Please do not share personal identifiers here.",
            "source": ""
        })
    
    advice_triggers = ["should i", "buy", "sell", "recommend", "best fund", "which is better", "worth investing"]
    if any(t in question.lower() for t in advice_triggers):
        return jsonify({
            "answer": "I only provide factual scheme information — no investment advice. Please consult a SEBI-registered advisor.",
            "source": "https://www.amfiindia.com"
        })
    
    try:
        answer, source_url = get_answer(question)
        llm_answer = call_llm(question, answer)
        return jsonify({"answer": llm_answer, "source": source_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/refresh", methods=["POST"])
def refresh():
    try:
        from scraper import scrape_all
        from embedder import build_index
        scrape_all()
        build_index(force=True)
        return jsonify({"status": "Index refreshed successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "FundBot backend is running"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
