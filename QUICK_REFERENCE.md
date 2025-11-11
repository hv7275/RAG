# RAG System Quick Reference Guide

Quick reference for common tasks and commands.

## 🚀 Quick Start

### 1. Installation
```bash
pip install -r requirements.txt
python setup_database.py
```

### 2. Start Servers
```bash
# Terminal 1
python run_api.py

# Terminal 2
python run_app.py
```

### 3. Access UI
```
http://localhost:5000
```

## 📝 Common Commands

### Data Processing
```bash
# Transcribe audio
python speech_to_text.py

# Create chunks
python chunks_with_timestamp.py

# Convert to JSON
python chunk_to_json.py

# Query via CLI
python incomings.py --query "Your question" --answer
```

### Server Management
```bash
# Start FastAPI
python run_api.py

# Start Flask
python run_app.py

# Start both (Windows)
start_servers.bat

# Start both (PowerShell)
start_servers.ps1
```

### Database
```bash
# Initialize database
python setup_database.py

# Verify setup
python verify_setup.py
```

## 🔑 API Endpoints

### Public Endpoints
- `GET /status` - System status
- `POST /query` - Query RAG system
- `POST /register` - Register user
- `POST /login` - Login user

### Protected Endpoints (Require Auth)
- `GET /me` - Get user info
- `GET /chat-history` - Get chat history
- `DELETE /chat-history/{id}` - Delete chat
- `POST /rebuild` - Rebuild index

## 🔐 Authentication

### Register
```bash
POST /register
{
  "username": "user123",
  "email": "user@example.com",
  "password": "password123"
}
```

### Login
```bash
POST /login
{
  "username": "user123",
  "password": "password123"
}
```

### Use Token
```bash
GET /me
Headers: Authorization: Bearer <token>
```

## ⚙️ Configuration

### Environment Variables
```env
EMBED_URL=http://127.0.0.1:11434/api/embed
EMBED_MODEL=nomic-embed-text:latest
OLLAMA_URL=http://127.0.0.1:11434
GEN_MODEL=llama3.2:3b
DATABASE_URL=sqlite:///./rag_system.db
SECRET_KEY=your-secret-key
FLASK_SECRET_KEY=your-flask-secret-key
API_URL=http://localhost:8000
```

### Ollama Models
```bash
# Pull embedding model
ollama pull nomic-embed-text

# Pull generation model
ollama pull llama3.2:3b

# List models
ollama list
```

## 🐛 Troubleshooting

### API Not Running
```bash
# Check status
curl http://localhost:8000/status

# Start API
python run_api.py
```

### Database Issues
```bash
# Recreate database
rm rag_system.db
python setup_database.py
```

### Ollama Issues
```bash
# Check Ollama
ollama list
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve
```

### Embeddings Not Found
```bash
# Rebuild embeddings
# Use "Rebuild Index" button in UI
# Or via API: POST /rebuild
```

## 📁 File Structure

```
RAG/
├── api.py              # FastAPI backend
├── app.py              # Flask frontend
├── auth.py             # Authentication
├── database.py         # Database models
├── read_chunks.py      # RAG core
├── run_api.py          # API server
├── run_app.py          # Flask server
├── setup_database.py   # DB setup
├── requirements.txt    # Dependencies
├── .env               # Configuration
├── rag_system.db      # Database
├── templates/         # HTML templates
├── static/            # CSS/JS
├── audios/            # Audio files
├── transcripts/       # Transcripts
├── chunks/            # Text chunks
└── json_output/       # JSON files
```

## 🔧 Development

### Test Setup
```bash
python verify_setup.py
```

### Test Registration
```bash
python test_registration.py
```

### Debug Mode
```python
# Flask
app.run(debug=True)

# FastAPI
app = FastAPI(debug=True)
```

## 📊 Status Codes

### API Responses
- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `500` - Internal Server Error
- `503` - Service Unavailable

## 🎯 Common Tasks

### Add New User
1. Open UI: `http://localhost:5000`
2. Click "Register"
3. Enter username, email, password
4. Click "Register"

### Query System
1. Open UI: `http://localhost:5000`
2. Enter query in text box
3. Adjust settings (K, generate answer)
4. Click "Search"
5. View results

### View History
1. Login to UI
2. Click "Chat History"
3. View previous queries

### Rebuild Index
1. Click "Rebuild Index" button
2. Wait for completion
3. Check status

## 🔒 Security

### Change Secrets
```env
SECRET_KEY=your-new-secret-key
FLASK_SECRET_KEY=your-new-flask-secret-key
```

### Password Requirements
- Minimum 6 characters
- Bcrypt hashed
- Never stored in plain text

### Token Security
- JWT tokens
- 7-day expiration
- Stored in localStorage
- Sent in Authorization header

## 📚 Documentation

- **Main README**: `README.md`
- **UI README**: `UI_README.md`
- **Auth Setup**: `AUTH_SETUP.md`
- **Quick Start**: `QUICK_START_AUTH.md`

## 🆘 Help

### Check Logs
- FastAPI: Terminal output
- Flask: Terminal output
- Browser: Console (F12)

### Verify Installation
```bash
python verify_setup.py
```

### Test Connection
```bash
curl http://localhost:8000/status
curl http://localhost:5000/status
```

---

**Quick Reference v2.0.0**

