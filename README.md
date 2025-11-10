# Video to RAG System

This project implements a Retrieval-Augmented Generation (RAG) system that processes video/audio content into searchable chunks with semantic search capabilities. It converts speech to text, segments the transcripts, and creates embeddings for efficient retrieval.

## Project Structure

```
RAG/
├── audios/              # Store input audio files
├── chunks/              # Timestamped text chunks
├── json_output/         # JSON formatted transcripts
├── transcripts/         # Raw transcripts with timestamps
├── Videos/             # Source video files
├── speech_to_text.py   # Convert audio to text using Whisper
├── chunks_with_timestamp.py # Segment transcripts into chunks
├── chunk_to_json.py    # Convert chunks to JSON format
├── read_chunks.py      # Create embeddings and semantic search
└── process_video.py    # Single file video processing
```

## Features

- **Speech-to-Text Conversion**: Uses OpenAI's Whisper model for accurate transcription
- **Timestamp Preservation**: Maintains timing information for each segment
- **Chunking System**: Splits transcripts into manageable segments (default: 5 segments per chunk)
- **Vector Search**: Implements FAISS for efficient similarity search
- **Embeddings**: Uses BGE-M3 model for generating embeddings
- **Structured Output**: Saves data in multiple formats (TSV, JSON, FAISS index)

## Prerequisites

```bash
pip install -r requirements.txt
```

Required packages:

- whisper
- requests
- pandas
- numpy

# Video → RAG (Retrieval-Augmented Generation)

This repository is a lightweight pipeline that converts audio/video into searchable text chunks and provides a hybrid semantic+lexical retrieval layer (embeddings + TF‑IDF + FAISS).

This README has exact commands for the scripts included in this project and notes about configuration, `.gitignore` behavior, and the local embedding service used by `read_chunks.py`.

## What this repo contains

Relevant scripts and folders:

- `audios/` — drop your audio files here (folder tracked, contents ignored by `.gitignore`)
- `transcripts/` — per-audio `.tsv` transcripts with timestamps (folder tracked, contents ignored)
- `chunks/` — human-readable chunk `.txt` files (folder tracked, contents ignored)
- `json_output/` — structured JSON per video (folder tracked, contents ignored)
- `Videos/` — (optional) original video files (folder tracked, contents ignored)
- `speech_to_text.py` — runs Whisper over `audios/` and writes `transcripts/*.tsv`
- `chunks_with_timestamp.py` — groups transcript segments into timestamped chunk files in `chunks/`
- `chunk_to_json.py` — converts transcripts (`.tsv`) into `json_output/*.json` with `full_text` + `chunks`
- `read_chunks.py` — loads `json_output`, requests embeddings from a local embedding service, builds FAISS, and provides a hybrid search function
- `process_video.py` — tiny example to transcribe a single file

## Quick start — full pipeline

1. Install dependencies (see `requirements.txt`):

```powershell
python -m pip install -r requirements.txt
```

2. Put audio files in `audios/` (supported formats: `.mp3`, `.wav`, `.m4a`).

3. Generate transcripts (Whisper):

```powershell
python speech_to_text.py
```

This will write TSV files into `transcripts/` with lines formatted as: `start\tend\ttext`.

4. (Option A) Create plain text chunks (one `.txt` per chunk):

```powershell
python chunks_with_timestamp.py
```

5. (Option B) Convert transcripts into structured JSON (used by `read_chunks.py`):

```powershell
python chunk_to_json.py
```

6. Build embeddings and FAISS index, then run an example hybrid search:

```powershell
python read_chunks.py
```

`read_chunks.py` will:

- call a local embedding service at `http://localhost:11434/api/embed` (see configuration below)
- save a Parquet metadata file (default `embeddings.parquet`)
- save a dense `.npy` embedding matrix (default `embeddings.npy`)
- save a FAISS index (default `vector_index.faiss`)

If you prefer to import and call functions programmatically, `read_chunks.py` exposes `create_embeddings`, `load_chunks_from_json`, `build_faiss_ip_index`, `build_tfidf`, and `search_hybrid`.

Example (python REPL):

```python
from read_chunks import load_chunks_from_json, build_faiss_ip_index, build_tfidf, search_hybrid
import pandas as pd
import faiss

# load existing parquet/index if you already built them, or rebuild via functions above
df = pd.read_parquet("embeddings.parquet")
index = faiss.read_index("vector_index.faiss")

# build TF-IDF vectorizer for lexical signal
from read_chunks import build_tfidf
tfidf_vectorizer, tfidf_matrix = build_tfidf(df['chunk'].tolist())

# run hybrid search
results = search_hybrid("explain reinforcement learning", df, index, None, tfidf_vectorizer, tfidf_matrix)
print(results['top_chunks'])
```

## Configuration notes

- Embedding endpoint: `read_chunks.py` uses `EMBED_URL = "http://localhost:11434/api/embed"` and `EMBED_MODEL = "bge-m3"` by default. If you run a different embedding service or path, update those constants in `read_chunks.py` or set up a small wrapper.
- GPU: set `EMBED_OPTIONS = {"num_gpu": 1}` in `read_chunks.py` if your local service supports GPU or change model choices.
- Chunk size: default is `SEGMENTS_PER_CHUNK = 5` (see `chunks_with_timestamp.py` and `chunk_to_json.py`). Adjust if you want longer/shorter chunks.
- Hybrid weighting: `ALPHA` in `read_chunks.py` controls how much weight to give embeddings vs lexical TF‑IDF (0.0..1.0).

## .gitignore / tracked folders

This repository is configured to keep the folder structure under source control while ignoring the data inside them. Each data folder contains a `.gitkeep` so the empty folder is tracked, but the contents are ignored. The current `.gitignore` rules:

- Track folders: `audios/`, `chunks/`, `json_output/`, `transcripts/`, `Videos/` (their `.gitkeep` files are tracked)
- Ignore folder contents: `audios/*`, `chunks/*`, `json_output/*`, `transcripts/*`, `Videos/*`
- Ignore large artifacts: `embeddings.npy`, `embeddings.parquet`, `vector_index.faiss`, plus wildcard patterns such as `*.faiss`, `*.npy`, `*.parquet`.

If you previously committed large files and want to remove them from the repo history (and stop tracking them), run:

```powershell
git rm --cached embeddings.parquet embeddings.npy vector_index.faiss
git commit -m "Remove large artifact files from tracking"
```

## Troubleshooting

- SSL / connection errors when calling the embedding service: if you see SSL errors, you are probably calling `https://` against a service that speaks plain HTTP (or has a mismatched cert). Ensure the `EMBED_URL` scheme (`http://` or `https://`) matches your service. For local dev it's typically `http://localhost:11434/...`.
- No `.json` files found: make sure `chunk_to_json.py` successfully created files under `json_output/` before running `read_chunks.py`.
- FAISS import errors: install `faiss-cpu` on CPU machines or `faiss-gpu` (ensure compatible CUDA) for GPU.

## Requirements

See `requirements.txt`. Main runtime dependencies used by the scripts are:

- `whisper` (OpenAI Whisper model)
- `requests`
- `pandas`, `numpy`
- `faiss-cpu` (or `faiss-gpu`)
- `scikit-learn` (for TF-IDF / cosine utilities)

## Development notes

- Filenames: `chunk_to_json.py` expects transcripts in `transcripts/*.tsv` (written by `speech_to_text.py`). Filenames influence the `title` field used in metadata.
- If you want to run the whole pipeline non-interactively, run the scripts in order: `speech_to_text.py` → `chunk_to_json.py` → `read_chunks.py`.

If you'd like, I can:

1. Add a tiny runner script `run_pipeline.py` that executes the steps in order and checks for errors.
2. Add a CLI wrapper around `read_chunks.py` so you can run searches from the command line.

---

If you want me to make the README more concise or add screenshots / sample outputs, tell me which parts to shorten or expand.
