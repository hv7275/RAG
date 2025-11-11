# Error Fix Summary - Ollama 500 Error

## Problem
The RAG system was showing a 500 Server Error when trying to generate answers via Ollama's `/api/generate` endpoint.

## Root Causes Identified
1. **Timeout Issues**: Ollama requests were timing out (default 120s, increased to 180s)
2. **Memory/VRAM Issues**: Model might be too large for available GPU memory
3. **Prompt Length**: Very long prompts could cause processing issues
4. **Error Handling**: Error messages weren't providing enough detail for debugging

## Fixes Applied

### 1. Improved Error Handling
- Added detailed error messages with Ollama response body
- Better exception handling for timeouts, connection errors, and HTTP errors
- More informative error messages in the UI

### 2. Automatic CPU Fallback
- On 500 errors, automatically retry with `gpu_layers=0` (CPU mode)
- Reduces context window to 1024 tokens for CPU mode
- Helps when GPU memory is insufficient

### 3. Prompt Truncation
- Added automatic prompt truncation if it exceeds context limits
- Calculates available space more accurately
- Ensures at least some context is always included

### 4. Increased Timeouts
- Increased timeout from 120s to 180s for model loading
- Better handling of timeout exceptions
- Clearer timeout error messages

### 5. Better Status Checking
- Added Ollama connectivity check in status endpoint
- Shows Ollama connection status in the UI
- Helps diagnose connection issues early

### 6. Improved Error Messages
- More descriptive error messages in the API response
- Suggests solutions (try smaller model, reduce prompt, etc.)
- Better debugging information in server logs

## Testing

### Test 1: Simple Query
1. Open the UI at http://localhost:5000
2. Enter a simple query like "What is CSS?"
3. Click Search
4. Should now work with automatic CPU fallback if needed

### Test 2: Check Ollama Status
1. Visit http://localhost:8000/status
2. Check if Ollama shows as "Connected"
3. If not, ensure Ollama is running

### Test 3: Verify Model Availability
```bash
python -c "import requests; r = requests.get('http://127.0.0.1:11434/api/tags'); print([m['name'] for m in r.json().get('models', [])])"
```

## Configuration

### Environment Variables
You can set these in your `.env` file or environment:

- `GEN_MODEL`: Generation model name (default: `llama3.2:3b`)
  - Recommended: `llama3.2:1b` for better performance
- `GEN_GPU_LAYERS`: GPU layers (set to `0` to force CPU)
- `GEN_NUM_CTX`: Context window size (default: 2048)
- `GEN_NUM_PREDICT`: Max tokens to generate (default: 256)

### Recommended Settings
For systems with limited GPU memory:
```env
GEN_MODEL=llama3.2:1b
GEN_GPU_LAYERS=0
GEN_NUM_CTX=1024
```

## Troubleshooting

### If you still get 500 errors:

1. **Check Ollama is running:**
   ```bash
   curl http://127.0.0.1:11434/api/tags
   ```

2. **Try a smaller model:**
   ```bash
   ollama pull llama3.2:1b
   ```
   Then set `GEN_MODEL=llama3.2:1b` in your `.env` file

3. **Force CPU mode:**
   Set `GEN_GPU_LAYERS=0` in your `.env` file

4. **Reduce context window:**
   Set `GEN_NUM_CTX=1024` in your `.env` file

5. **Check server logs:**
   Look at the FastAPI backend console for detailed error messages

### Common Issues

**Issue: "Request timed out"**
- Solution: The model is taking too long. Try a smaller model or reduce prompt length.

**Issue: "Failed to connect to Ollama"**
- Solution: Make sure Ollama is running. Start it with `ollama serve` if needed.

**Issue: "HTTP 500 error"**
- Solution: The automatic CPU fallback should handle this. Check server logs for details.

**Issue: "Model not found"**
- Solution: Pull the model: `ollama pull llama3.2:1b`

## Next Steps

1. **Restart the servers** to apply the fixes:
   ```bash
   # Stop existing servers (Ctrl+C)
   # Then restart:
   python run_api.py  # Terminal 1
   python run_app.py  # Terminal 2
   ```

2. **Test with a simple query** to verify the fix works

3. **Check the server logs** for any remaining issues

4. **Adjust configuration** if needed based on your system capabilities

## Files Modified

- `read_chunks.py`: Improved error handling, CPU fallback, prompt truncation
- `api.py`: Added Ollama status check, better error messages
- Error handling now provides more detailed information

## Summary

The fixes ensure that:
- ✅ Errors are handled gracefully with informative messages
- ✅ Automatic CPU fallback resolves most 500 errors
- ✅ Prompt length is managed to prevent issues
- ✅ Timeouts are sufficient for model loading
- ✅ Users get helpful error messages and suggestions

The system should now work reliably even when GPU memory is limited or models are slow to load.

