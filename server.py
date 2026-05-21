import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
from topic_detection import get_answer

openai.api_key = os.environ.get("OPENAI_API_KEY")

def call_llm(question, context_text):
    prompt = f"""You are FundBot, a facts-only mutual fund assistant for Mirae Asset schemes.

Rules:
- Answer using ONLY the source text below
- Maximum 3 sentences
- No investment advice or opinions
- No numbers not present in the source text
- If answer not found say exactly: I could not find that detail. Please check the official source linked below.

Source text:
{context_text}

Question: {question}

Answer:"""

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

app = Flask(__name__)
CORS(app, resources={
    r"/ask": {
        "origins": [
            "https://mf-faq.netlify.app",
            "https://koundinya2003.github.io",
            "http://127.0.0.1:5500",
            "http://localhost:5500"
        ]
    },
    r"/health": {"origins": "*"}
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

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "FundBot backend is running"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
