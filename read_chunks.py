import requests
import os
import json

def create_embeddings(text):
    URL = "http://localhost:11434/api/embeddings"
    PAYLOAD = {
        "model": "bge-m3",
        "prompt": text
    }
    
    response = requests.post(URL, json=PAYLOAD)

    if response.status_code == 200:
        data = response.json()
        embeddings = data.get("embedding")
        return embeddings
    else:
        print("Request failed with status:", response.status_code)
        print("Response:", response.text)
        return None


# Read JSON files correctly
json_files = os.listdir('json_output')
all_chunks = []   # will store: {title, chunk, embedding (optional)}
chunk_id = 0

for filename in json_files:
    
    if filename.endswith(".json"):
        filepath = os.path.join("json_output", filename)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract a clean video title from filename
        video_title = os.path.splitext(filename)[0]

        # Add chunk + source video title to list
        for chunk in data["chunks"]:
            all_chunks.append({
                "chunk_id" : chunk_id,
                "title": video_title.split("_")[0],
                "chunk": chunk,
            })
            
            
            chunk_id += 1 # Increase the chunk_id

print("Total chunks collected:", len(all_chunks))
print("Example entry:")
print(all_chunks[:5])
