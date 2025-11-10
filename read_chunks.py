import requests
import os
import json
import pandas as pd

def create_embeddings(text_list):
    URL = "http://localhost:11434/api/embed"
    PAYLOAD = {
        "model": "bge-m3",          # << use smaller model or keep bge-m3
        "input": text_list,
        "options": {"num_gpu": 0}      # << force CPU
    }
    
    response = requests.post(URL, json=PAYLOAD)

    if response.status_code == 200:
        return response.json().get("embeddings")
    print("Request failed:", response.text)
    return None


json_files = os.listdir('json_output')
all_chunks = []
chunk_id = 0

for filename in json_files:
    if filename.endswith(".json"):
        filepath = os.path.join("json_output", filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        video_title = os.path.splitext(filename)[0]

        for chunk in data["chunks"]:
            text_to_embed = chunk["text"]
            embeddings = create_embeddings([text_to_embed])
            if embeddings is None: continue
            embedding = embeddings[0]

            all_chunks.append({
                "chunk_id": chunk_id,
                "title": video_title.split("_")[0],
                "chunk": text_to_embed,
                "embedding": embedding
            })
            chunk_id += 1
        break

df = pd.DataFrame(all_chunks)
print(df.shape)
