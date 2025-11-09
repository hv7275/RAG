import os
import whisper

model = whisper.load_model("small")

audio_folder = r"C:\Users\Harshvardhan rai\OneDrive\Desktop\RAG\audios"
output_folder = r"C:\Users\Harshvardhan rai\OneDrive\Desktop\RAG\transcripts"
os.makedirs(output_folder, exist_ok=True)

for filename in os.listdir(audio_folder):
    if filename.lower().endswith((".mp3", ".wav", ".m4a")):
        audio_path = os.path.join(audio_folder, filename)
        print(f"\nTranscribing: {filename}")

        result = model.transcribe(audio_path, task="translate", verbose=True)

        # Save full transcription with timestamps
        output_path = os.path.join(output_folder, filename + ".tsv")
        with open(output_path, "w", encoding="utf-8") as f:
            for segment in result["segments"]:
                start = round(segment["start"], 2)
                end = round(segment["end"], 2)
                text = segment["text"].strip()
                f.write(f"{start}\t{end}\t{text}\n")

        print(f"Saved timestamp transcript → {output_path}")

print("\nAll timestamp transcripts saved.")
