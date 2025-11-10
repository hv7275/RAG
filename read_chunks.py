import os
import json
import requests
import pandas as pd
import numpy as np
import faiss


def create_embeddings(text_list):
    URL = "http://localhost:11434/api/embed"
    PAYLOAD = {
        "model": "bge-m3",
        "input": text_list,
        "options": {"num_gpu": 0}  # force CPU (change to 1 if GPU available)
    }

    response = requests.post(URL, json=PAYLOAD)

    if response.status_code == 200:
        return response.json().get("embeddings")
    else:
        print("Embedding request failed:", response.text)
        return None


# Load transcript chunks and batch-embed
json_dir = "json_output"
json_files = [f for f in os.listdir(json_dir) if f.endswith(".json")]

all_chunks = []
chunk_id = 0

for filename in json_files:
    filepath = os.path.join(json_dir, filename)

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    video_title = os.path.splitext(filename)[0]

    # Batch embed all text chunks
    text_list = [chunk["text"] for chunk in data["chunks"]]
    embeddings = create_embeddings(text_list)

    if embeddings is None:
        print(f"Skipping {filename} due to embedding failure.")
        continue

    # Store embedding + metadata
    for chunk, emb in zip(data["chunks"], embeddings):
        all_chunks.append({
            "chunk_id": chunk_id,
            "title": video_title.split("_")[0],
            "chunk": chunk["text"],
            "embedding": emb
        })
        chunk_id += 1

# Create DataFrame
df = pd.DataFrame(all_chunks)
print("Chunks processed:", df.shape)


# Save metadata to Parquet
df.to_parquet("embeddings.parquet", index=False)
print("Saved metadata to embeddings.parquet")

# Build and save FAISS vector index
emb_matrix = np.array(df["embedding"].tolist()).astype("float32")

index = faiss.IndexFlatL2(emb_matrix.shape[1])
index.add(emb_matrix)
faiss.write_index(index, "vector_index.faiss")

print("FAISS index saved to vector_index.faiss")

# Search Function
def search(query, top_k=5):
    # Embed query
    query_vec = create_embeddings([query])[0]
    query_vec = np.array(query_vec).astype("float32").reshape(1, -1)

    # Load index + metadata
    index = faiss.read_index("vector_index.faiss")
    df = pd.read_parquet("embeddings.parquet")

    distances, indices = index.search(query_vec, top_k)

    return df.iloc[indices[0]]

# Example Usage
if __name__ == "__main__":
    print("\nExample search:")
    result = search("Explain reinforcement learning", top_k=3)
    print(result)
