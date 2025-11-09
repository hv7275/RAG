import os
import json
import re

# Folders
transcripts_folder = r"C:\Users\Harshvardhan rai\OneDrive\Desktop\RAG\transcripts"
json_output_folder = r"C:\Users\Harshvardhan rai\OneDrive\Desktop\RAG\json_output"

os.makedirs(json_output_folder, exist_ok=True)

SEGMENTS_PER_CHUNK = 5  # you selected 5

def clean(text):
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

for filename in os.listdir(transcripts_folder):
    if filename.endswith(".tsv"):
        path = os.path.join(transcripts_folder, filename)
        base_name = filename.replace(".tsv", "")

        with open(path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]

        # ===== CREATE FULL TEXT =====
        full_text = " ".join([line.split("\t")[2].strip() for line in lines])
        full_text = clean(full_text)

        # ===== CREATE TIMESTAMP CHUNKS =====
        chunks = []
        for i in range(0, len(lines), SEGMENTS_PER_CHUNK):
            group = lines[i:i + SEGMENTS_PER_CHUNK]
            start = float(group[0].split("\t")[0])
            end = float(group[-1].split("\t")[1])
            text = clean(" ".join([seg.split("\t")[2].strip() for seg in group]))

            chunks.append({
                "start": start,
                "end": end,
                "text": text
            })

        # ===== COMBINE INTO ONE JSON =====
        data = {
            "full_text": full_text,
            "chunks": chunks
        }

        # Save JSON
        output_path = os.path.join(json_output_folder, base_name + ".json")
        with open(output_path, "w", encoding="utf-8") as jf:
            json.dump(data, jf, ensure_ascii=False, indent=4)

        print(f"✅ Created {output_path}")

print("\n✅ All videos converted successfully. JSON files are in `json_output` folder.")
