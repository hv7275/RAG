import os

# Input / Output folders (update only if your path is different)
transcripts_folder = r"C:\Users\Harshvardhan rai\OneDrive\Desktop\RAG\transcripts"
chunks_folder = r"C:\Users\Harshvardhan rai\OneDrive\Desktop\RAG\chunks"

os.makedirs(chunks_folder, exist_ok=True)

SEGMENTS_PER_CHUNK = 5   # as you requested

for filename in os.listdir(transcripts_folder):
    if filename.endswith(".tsv"):
        input_path = os.path.join(transcripts_folder, filename)
        base_name = filename.replace(".tsv", "")

        with open(input_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]

        # Process segments into chunk groups
        for i in range(0, len(lines), SEGMENTS_PER_CHUNK):
            segment_group = lines[i:i + SEGMENTS_PER_CHUNK]

            # Extract start & end timestamps
            start_time = segment_group[0].split("\t")[0]
            end_time = segment_group[-1].split("\t")[1]

            # Combine text from all segments
            text_content = " ".join([seg.split("\t")[2].strip() for seg in segment_group])

            # Create chunk text with timestamp header
            chunk_text = f"[{start_time} → {end_time}]\n{text_content}"

            # Save chunk
            chunk_filename = f"{base_name}_chunk_{i//SEGMENTS_PER_CHUNK + 1}.txt"
            output_path = os.path.join(chunks_folder, chunk_filename)

            with open(output_path, "w", encoding="utf-8") as c:
                c.write(chunk_text)

        print(f"✅ Chunked {filename}")

print("\n✅ All timestamp chunk files are saved in the 'chunks' folder.")
