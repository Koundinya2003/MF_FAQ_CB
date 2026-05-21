import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from rag import get_rag_answer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("flask.log")
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app) # Allow all for local development, can restrict later if needed

@app.route("/ask", methods=["POST"])
def ask():
    logger.info(f"Received request: {request.headers}")
    data = request.get_json()
    logger.info(f"Request body: {data}")

    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "Question is required"}), 400
    
    # Automated filters for PII and Investment Advice
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
        answer, source_url = get_rag_answer(question)
        return jsonify({"answer": answer, "source": source_url})
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "FundBot backend is running"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
