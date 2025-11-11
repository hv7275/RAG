# RAG — Video/Audio → Retrieval-Augmented Generation

Small, local pipeline to convert video/audio into searchable, timestamped text chunks and run retrieval + generation locally.

Key scripts

- `speech_to_text.py` — transcribe audio files (Whisper) into `transcripts/` (TSV with start/end/text).
- `chunks_with_timestamp.py` — group transcript segments into human-readable chunk `.txt` files in `chunks/`.
- `chunk_to_json.py` — convert transcripts / chunks into structured JSON files in `json_output/` (used for embedding).
- `read_chunks.py` — library of functions: load JSON, clean & chunk text, call embedding service, build FAISS index, hybrid search, and answer generation helpers.
- `incomings.py` — CLI entrypoint that orchestrates the pipeline (build or load artifacts, run retrieval, optional generation).

Configuration (.env)

- Project reads runtime configuration from a `.env` file at the repo root (optional). Example keys:
  - `EMBED_URL` — embedding endpoint (e.g. `http://127.0.0.1:11434/api/embed`).
  - `EMBED_MODEL` — default embed model name/tag (e.g. `nomic-embed-text:latest` or `mxbai-embed-large:latest`).
  - `OLLAMA_URL` — generation endpoint (e.g. `http://127.0.0.1:11434/api/chat` or `/api/generate`).
  - `GEN_MODEL` — generator model name/tag (e.g. `llama3.2:3b`).
  - `JSON_DIR`, `OUT_PARQUET`, `OUT_NPY`, `OUT_FAISS`, and chunking/timeout settings — see `.env` in repo for defaults.

Quick start

1. Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

2. Optionally edit `.env` to match your local servers and preferred models.

3. Put audio files into `audios/` and run the transcript step:

```powershell
python speech_to_text.py
```

4. Produce structured JSON (used for embedding):

```powershell
python chunk_to_json.py
```

5. Build embeddings and index (or run directly via the CLI):

```powershell
python incomings.py --query "What is this video about?" --answer
```

Notes

- `incomings.py` is the recommended entrypoint. It will rebuild artifacts when needed or load existing ones (`embeddings.parquet`, `embeddings.npy`, `vector_index.faiss`).
- `read_chunks.py` contains reusable functions and now acts as a library (importable).
- The code tries common generation endpoints (`/api/chat`, `/api/generate`, etc.) and multiple payload shapes to be tolerant of different local servers. If generation fails with a 500, check your `OLLAMA_URL` and `GEN_MODEL` values.

Troubleshooting

- 404 when calling generation: verify `OLLAMA_URL` is correct and includes the path your local server expects (`/api/chat` vs `/api/generate`).
- 500 from generation: often means the model name is not available or the server failed to run the model — confirm your local model is installed and the `GEN_MODEL` matches.
- Embedding errors: ensure `EMBED_URL` points to a working embedding server and that `EMBED_MODEL` is available.

Where to go next

- Add `--check-servers` to proactively probe endpoints and show which candidate endpoint/payload works (I can add this for you).
- Add unit tests that mock the embedding/generation endpoints.

License
MIT

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

# Video → RAG (Retrieval-Augmented Generation)

This repository provides a small pipeline that converts audio/video into searchable, timestamped text chunks and adds a hybrid retrieval layer combining semantic embeddings (BGE-M3) and lexical TF‑IDF with FAISS indexing.

What you get: speech → transcripts (.tsv) → chunks (.txt / JSON) → embeddings + FAISS → hybrid search.

## Repository layout

- `audios/` — input audio files (folder tracked; contents ignored by `.gitignore`)
- `transcripts/` — Whisper transcripts (`.tsv`) with timestamps (folder tracked; contents ignored)
- `chunks/` — human-readable chunk `.txt` files (folder tracked; contents ignored)
- `json_output/` — structured JSON per video with `full_text` and `chunks` (folder tracked; contents ignored)
- `Videos/` — optional source videos (folder tracked; contents ignored)
- `speech_to_text.py` — run Whisper to transcribe files in `audios/` → `transcripts/*.tsv`
- `chunks_with_timestamp.py` — groups transcript segments into timestamped `.txt` chunks in `chunks/`
- `chunk_to_json.py` — converts `transcripts/*.tsv` → `json_output/*.json` (used by `read_chunks.py`)
- `read_chunks.py` — loads `json_output`, creates embeddings via a local service, builds FAISS, and provides `search_hybrid`
- `process_video.py` — minimal example showing whisper usage for a single file
- `requirements.txt` — Python dependencies

## Quick start

1. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

2. Add audio files to `audios/` (.mp3, .wav, .m4a).

3. Transcribe audio to timestamped TSV files:

```powershell
python speech_to_text.py
```

4. (Optional) Create human-readable chunk text files:

```powershell
python chunks_with_timestamp.py
```

5. Convert transcripts to structured JSON for embedding:

```powershell
python chunk_to_json.py
```

6. Build embeddings, create FAISS index, and run an example hybrid query:

```powershell
python read_chunks.py
```

After running `read_chunks.py` you'll find (by default):

- `embeddings.parquet` — dataframe metadata and embeddings
- `embeddings.npy` — dense embedding matrix
- `vector_index.faiss` — FAISS index file

## How `read_chunks.py` works (summary)

- Loads `json_output/*.json` and extracts `chunks` (text + start/end timestamps).
- Calls a local embedding service at `http://localhost:11434/api/embed` to get embeddings (BGE‑M3 by default).
- Builds a FAISS inner-product index over L2-normalized vectors to support cosine similarity.
- Builds a TF‑IDF matrix for lexical similarity.
- Runs a hybrid search that blends embedding and TF‑IDF scores (weight controlled by `ALPHA`).

You can import functions from `read_chunks.py` (e.g. `load_chunks_from_json`, `build_tfidf`, `search_hybrid`) if you want to embed or query programmatically.

## Configuration

Edit `read_chunks.py` constants to tune behavior:

- `EMBED_URL` — local embedding service URL (default: `http://localhost:11434/api/embed`)
- `EMBED_MODEL` — embedding model name (default: `bge-m3`)
- `EMBED_OPTIONS` — options sent to the embedding service (`{"num_gpu": 0}` by default)
- `ALPHA` — embedding vs lexical weighting (0.0..1.0)
- `JSON_DIR`, `PARQUET_PATH`, `EMB_NPY_PATH`, `FAISS_PATH` — output file paths

Chunking behavior is controlled in `chunks_with_timestamp.py` and `chunk_to_json.py` via `SEGMENTS_PER_CHUNK` (default 5).

## .gitignore and folder tracking

This repository is set up to keep empty folders under version control while ignoring the data they will contain. Each data folder (`audios`, `transcripts`, `chunks`, `json_output`, `Videos`) has a `.gitkeep` and the `.gitignore` uses `folder/*` + `!folder/.gitkeep` so the folder is tracked but its contents are not.

Large artifacts are explicitly ignored:

- `embeddings.npy`
- `embeddings.parquet`
- `vector_index.faiss`
- wildcard patterns: `*.faiss`, `*.npy`, `*.parquet`

If you previously committed those artifacts, remove them from tracking with:

```powershell
git rm --cached embeddings.parquet embeddings.npy vector_index.faiss
git commit -m "Remove large artifact files from tracking"
```

## Troubleshooting

- Embedding connection/SSL errors: ensure `EMBED_URL` uses the correct scheme (`http://` vs `https://`). Local dev services usually run on plain HTTP.
- No JSON files found: run `chunk_to_json.py` and confirm `json_output/` contains `.json` files.
- FAISS import issues: install `faiss-cpu` for CPU or `faiss-gpu` (requires matching CUDA) for GPU.

## Next suggestions (I can implement)

- Add a `run_pipeline.py` to orchestrate the full pipeline (transcribe → chunk → json → embed → index).
- Add a CLI for `read_chunks.py` so you can query from the command line.
- Add unit tests (small) for `chunk_to_json.py` and `read_chunks.py` functions (mock embedding calls).

If you'd like any of the above, tell me which and I'll add it.
