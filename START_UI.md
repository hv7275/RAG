# Quick Start Guide - RAG UI

## Prerequisites

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Ensure embeddings are built:**
   - Either run the pipeline to generate `embeddings.parquet`, `embeddings.npy`, and `vector_index.faiss`
   - Or ensure JSON files exist in `json_output/` directory (the system will build embeddings on first query)

3. **Start Ollama:**
   - Make sure Ollama is running and accessible
   - Ensure your embedding and generation models are available

## Starting the Application

### Step 1: Start FastAPI Backend

Open a terminal and run:
```bash
python run_api.py
```

Or directly:
```bash
python api.py
```

The API will be available at `http://localhost:8000`

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 2: Start Flask Frontend

Open another terminal and run:
```bash
python run_app.py
```

Or directly:
```bash
python app.py
```

The UI will be available at `http://localhost:5000`

You should see:
```
 * Running on http://0.0.0.0:5000
```

### Step 3: Open the UI

Open your browser and navigate to:
```
http://localhost:5000
```

## Using the UI

1. **Check Status**: The status bar at the top shows if the system is ready
2. **Enter Query**: Type your question in the text area
3. **Configure Settings**:
   - **Top K results**: Number of chunks to retrieve (default: 4)
   - **Generate answer**: Toggle to enable/disable answer generation
4. **Search**: Click the "Search" button
5. **View Results**:
   - **Answer**: Generated answer (if enabled)
   - **Relevant Chunks**: List of chunks with scores, timestamps, and source information

## Troubleshooting

### Backend won't start
- Check if port 8000 is already in use
- Verify all dependencies are installed
- Check that `read_chunks.py` is in the same directory

### Frontend won't start
- Check if port 5000 is already in use
- Verify Flask is installed
- Check that `templates/` and `static/` directories exist

### "Unable to connect to API"
- Make sure the FastAPI backend is running on port 8000
- Check the `API_URL` environment variable in Flask (default: `http://localhost:8000`)

### "Embeddings not found"
- Run the pipeline to generate embeddings first:
  ```bash
  python incomings.py --query "test" --k 1
  ```
- Or ensure JSON files exist in `json_output/` directory

### Query fails
- Verify Ollama is running
- Check that embedding and generation models are available
- Check the FastAPI backend logs for error messages

## API Documentation

Once the FastAPI backend is running, you can access:
- API docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

## Environment Variables

You can configure the system using environment variables or a `.env` file:

- `EMBED_URL`: Embedding service URL (default: `http://127.0.0.1:11434/api/embed`)
- `EMBED_MODEL`: Embedding model name (default: `nomic-embed-text:latest`)
- `OLLAMA_URL`: Ollama base URL (default: `http://127.0.0.1:11434`)
- `GEN_MODEL`: Generation model name (default: `llama3.2:3b`)
- `JSON_DIR`: Directory containing JSON files (default: `json_output`)
- `API_URL`: FastAPI backend URL for Flask (default: `http://localhost:8000`)

## Features

- ✅ Modern, responsive UI
- ✅ Real-time status checking
- ✅ Configurable query parameters
- ✅ Display of relevant chunks with scores and timestamps
- ✅ Answer generation using Ollama
- ✅ Error handling and user feedback
- ✅ Rebuild index functionality
- ✅ REST API for programmatic access

## Next Steps

- Customize the UI by editing `templates/index.html` and `static/css/style.css`
- Add more features to the API in `api.py`
- Integrate with other services using the REST API
- Deploy to production (consider using gunicorn for Flask and proper ASGI server for FastAPI)

