import os
import json
import faiss
import numpy as np
import openai
from sentence_transformers import SentenceTransformer

# Load environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
INDEX_PATH = os.path.join(DATA_DIR, "faiss_index.bin")
METADATA_PATH = os.path.join(DATA_DIR, "metadata.json")

# Initialize model and load index/metadata
print("Initializing RAG logic...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
index = faiss.read_index(INDEX_PATH)
with open(METADATA_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)

def retrieve_context(question, top_k=3):
    query_embedding = embedding_model.encode([question])
    query_embedding = np.array(query_embedding).astype('float32')

    distances, indices = index.search(query_embedding, top_k)

    results = []
    for idx in indices[0]:
        if idx != -1:
            results.append(metadata[idx])

    context_text = "\n\n".join([res["content"] for res in results])
    source_url = results[0]["url"] if results else "https://www.miraeassetmf.co.in"

    return context_text, source_url

def get_rag_answer(question):
    context, source_url = retrieve_context(question)

    prompt = f"""You are FundBot, a facts-only mutual fund assistant for Mirae Asset schemes.

Rules:
- Answer using ONLY the source text below
- Maximum 3 sentences
- No investment advice or opinions
- No numbers not present in the source text
- If answer not found say exactly: I could not find that detail. Please check the official source linked below.

Source text:
{context}

Question: {question}

Answer:"""

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    answer = response.choices[0].message.content

    return answer, source_url
