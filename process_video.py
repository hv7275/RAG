import whisper

model = whisper.load_model("small")  # options: tiny, base, small, medium
result = model.transcribe("audio_file.mp3", task="translate")
print(result["text"])
