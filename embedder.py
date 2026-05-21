import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

def chunk_text(text, chunk_size=500, overlap=100):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def main():
    data_dir = "data"
    scraped_file = os.path.join(data_dir, "scraped_data.json")

    if not os.path.exists(scraped_file):
        print(f"Error: {scraped_file} not found.")
        return

    with open(scraped_file, "r", encoding="utf-8") as f:
        scraped_data = json.load(f)

    print("Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    all_chunks = []
    all_metadata = []

    for entry in scraped_data:
        url = entry["url"]
        content = entry["content"]
        chunks = chunk_text(content)
        for chunk in chunks:
            all_chunks.append(chunk)
            all_metadata.append({"url": url, "content": chunk})

    print(f"Generating embeddings for {len(all_chunks)} chunks...")
    embeddings = model.encode(all_chunks)
    embeddings = np.array(embeddings).astype('float32')

    # Build FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    # Save index and metadata
    index_file = os.path.join(data_dir, "faiss_index.bin")
    faiss.write_index(index, index_file)

    metadata_file = os.path.join(data_dir, "metadata.json")
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f)

    print(f"FAISS index saved to {index_file}")
    print(f"Metadata saved to {metadata_file}")

if __name__ == "__main__":
    main()
