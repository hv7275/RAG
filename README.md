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
- faiss-cpu (or faiss-gpu for GPU support)

## Usage

1. **Convert Speech to Text**:

   ```bash
   python speech_to_text.py
   ```

   Place your audio files in the `audios/` directory. Supports .mp3, .wav, .m4a formats.

2. **Create Timestamped Chunks**:

   ```bash
   python chunks_with_timestamp.py
   ```

   Segments the transcripts into smaller chunks while preserving timestamp information.

3. **Generate JSON Format**:

   ```bash
   python chunk_to_json.py
   ```

   Converts the chunked transcripts into a structured JSON format.

4. **Create Embeddings and Search**:
   ```bash
   python read_chunks.py
   ```
   Generates embeddings for all chunks and enables semantic search functionality.

## Search Example

```python
from read_chunks import search

# Search for relevant content
results = search("Explain reinforcement learning", top_k=3)
print(results)
```

## Project Configuration

- **Chunk Size**: Default is 5 segments per chunk (configurable in `chunks_with_timestamp.py`)
- **Whisper Model**: Uses "small" model by default (options: tiny, base, small, medium)
- **Embedding Model**: Uses BGE-M3 for generating embeddings
- **Vector Store**: Uses FAISS for similarity search

## Output Files

- `transcripts/*.tsv`: Tab-separated files with timestamps and text
- `chunks/*.txt`: Individual text chunks with timestamp ranges
- `json_output/*.json`: Structured JSON with full text and chunks
- `embeddings.parquet`: Metadata and embeddings in Parquet format
- `vector_index.faiss`: FAISS index for vector similarity search

## Notes

- The project uses local embedding service (requires running on port 11434)
- GPU support can be enabled by modifying the `options` in `read_chunks.py`
- All file paths are configured to be relative to the project root
- Intermediate files are gitignored by default

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request
