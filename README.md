# RAG System - Video/Audio Retrieval-Augmented Generation

A comprehensive RAG (Retrieval-Augmented Generation) system that processes video/audio content into searchable chunks with semantic search capabilities. The system includes a modern web UI with user authentication, chat history, and real-time query processing.

## 🚀 Features

### Core RAG Capabilities
- **Speech-to-Text Conversion**: Uses OpenAI's Whisper model for accurate transcription
- **Timestamp Preservation**: Maintains timing information for each segment
- **Intelligent Chunking**: Splits transcripts into manageable segments with context
- **Hybrid Search**: Combines semantic embeddings (FAISS) and lexical search (TF-IDF)
- **Answer Generation**: Uses Ollama LLM for generating answers from retrieved chunks
- **Vector Indexing**: Fast similarity search using FAISS

### Web Interface
- **Modern UI**: Beautiful, responsive web interface built with Flask
- **Real-time Status**: Live status checking for system health
- **Interactive Queries**: Easy-to-use query interface with configurable parameters
- **Copy to Clipboard**: Copy answers and chunks with one click
- **Error Handling**: Comprehensive error messages and user feedback

### Authentication & Database
- **User Authentication**: JWT-based authentication system
- **User Registration & Login**: Secure user management
- **Chat History**: Automatically saves and retrieves user query history
- **Password Security**: Bcrypt password hashing
- **Session Management**: Secure session handling

## 📋 Table of Contents

- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Authentication](#authentication)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## 🏗️ Architecture

The system consists of three main components:

### 1. FastAPI Backend (`api.py`)
- RESTful API for RAG operations
- User authentication and authorization
- Database operations (users, chat history)
- Embedding and indexing management
- Query processing and answer generation

### 2. Flask Frontend (`app.py`)
- Web UI server
- Authentication routes
- API proxy for frontend
- Session management

### 3. Core RAG Library (`read_chunks.py`)
- Embedding generation
- FAISS index management
- Hybrid search implementation
- Answer generation via Ollama

## 📁 Project Structure

```
RAG/
├── api.py                  # FastAPI backend server
├── app.py                  # Flask frontend server
├── auth.py                 # Authentication utilities
├── database.py             # Database models and configuration
├── read_chunks.py          # Core RAG library
├── run_api.py              # FastAPI server runner
├── run_app.py              # Flask server runner
├── setup_database.py       # Database initialization script
├── requirements.txt        # Python dependencies
├── .env                    # Environment configuration (create this)
│
├── audios/                 # Input audio files
├── chunks/                 # Text chunks with timestamps
├── json_output/            # JSON formatted transcripts
├── transcripts/            # Raw transcripts (TSV format)
├── Videos/                 # Source video files
│
├── templates/              # HTML templates
│   └── index.html          # Main UI page
├── static/                 # Static files
│   ├── css/
│   │   └── style.css       # UI styles
│   └── js/
│       └── app.js          # Frontend JavaScript
│
├── rag_system.db           # SQLite database (auto-created)
├── embeddings.parquet      # Embeddings metadata
├── embeddings.npy          # Embedding vectors
└── vector_index.faiss      # FAISS index
```

## 🔧 Installation

### Prerequisites

- Python 3.8 or higher
- Ollama installed and running (for embeddings and generation)
- Git (optional)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd RAG
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set Up Ollama

1. Install Ollama from [https://ollama.ai](https://ollama.ai)
2. Start Ollama service
3. Pull required models:
   ```bash
   ollama pull nomic-embed-text
   ollama pull llama3.2:3b
   ```

### Step 5: Configure Environment

Create a `.env` file in the project root:

```env
# Ollama Configuration
EMBED_URL=http://127.0.0.1:11434/api/embed
EMBED_MODEL=nomic-embed-text:latest
OLLAMA_URL=http://127.0.0.1:11434
GEN_MODEL=llama3.2:3b

# Database
DATABASE_URL=sqlite:///./rag_system.db

# Security (change these in production!)
SECRET_KEY=your-secret-key-change-this-in-production
FLASK_SECRET_KEY=your-flask-secret-key-change-this-in-production

# API Configuration
API_URL=http://localhost:8000
```

### Step 6: Initialize Database

```bash
python setup_database.py
```

Or the database will be automatically created when you start the API server.

## 🚀 Quick Start

### 1. Prepare Your Audio/Video Files

Place your audio files in the `audios/` directory:
- Supported formats: `.mp3`, `.wav`, `.m4a`, `.mp4`

### 2. Generate Transcripts

```bash
python speech_to_text.py
```

This creates TSV files in `transcripts/` with timestamps.

### 3. Convert to JSON Format

```bash
python chunk_to_json.py
```

This creates JSON files in `json_output/` for embedding.

### 4. Build Embeddings and Index

The system will automatically build embeddings when you start the API, or you can trigger it manually via the UI's "Rebuild Index" button.

### 5. Start the Servers

**Terminal 1 - FastAPI Backend:**
```bash
python run_api.py
```
API will be available at `http://localhost:8000`

**Terminal 2 - Flask Frontend:**
```bash
python run_app.py
```
UI will be available at `http://localhost:5000`

### 6. Access the Web UI

Open your browser and navigate to:
```
http://localhost:5000
```

## 📖 Usage

### Web Interface

1. **Register/Login**: Click "Register" to create an account or "Login" to access existing account
2. **Check Status**: Verify system status in the status bar
3. **Enter Query**: Type your question in the query box
4. **Configure Settings**:
   - **Top K results**: Number of relevant chunks (default: 4)
   - **Generate answer**: Enable/disable answer generation
5. **Search**: Click "Search" to query the RAG system
6. **View Results**:
   - **Answer**: Generated answer based on retrieved chunks
   - **Relevant Chunks**: List of chunks with scores and timestamps
7. **Copy Content**: Click copy buttons to copy answers or chunks
8. **View History**: Click "Chat History" to view previous queries

### Command Line Interface

You can also use the CLI for quick queries:

```bash
python incomings.py --query "What is this video about?" --answer
```

## 🔌 API Endpoints

### Public Endpoints

#### `GET /`
- **Description**: API information
- **Response**: API version and features

#### `GET /status`
- **Description**: Check system status
- **Response**: 
  ```json
  {
    "status": "ready",
    "chunks_count": 87,
    "ollama_status": "connected"
  }
  ```

#### `POST /query`
- **Description**: Query the RAG system
- **Body**:
  ```json
  {
    "query": "Your question",
    "k": 4,
    "generate_answer": true,
    "max_ctx": 4000
  }
  ```
- **Response**:
  ```json
  {
    "query": "Your question",
    "chunks": [...],
    "answer": "Generated answer",
    "message": "Success"
  }
  ```

#### `POST /register`
- **Description**: Register a new user
- **Body**:
  ```json
  {
    "username": "user123",
    "email": "user@example.com",
    "password": "password123"
  }
  ```

#### `POST /login`
- **Description**: Login and get access token
- **Body**:
  ```json
  {
    "username": "user123",
    "password": "password123"
  }
  ```
- **Response**:
  ```json
  {
    "access_token": "jwt_token",
    "token_type": "bearer",
    "user": {...}
  }
  ```

### Protected Endpoints (Require Authentication)

#### `GET /me`
- **Description**: Get current user information
- **Headers**: `Authorization: Bearer <token>`

#### `GET /chat-history`
- **Description**: Get user's chat history
- **Headers**: `Authorization: Bearer <token>`
- **Query Params**: `skip` (optional), `limit` (optional, default: 50)

#### `DELETE /chat-history/{chat_id}`
- **Description**: Delete a chat history item
- **Headers**: `Authorization: Bearer <token>`

#### `POST /rebuild`
- **Description**: Rebuild embeddings and index
- **Headers**: `Authorization: Bearer <token>` (optional)

## 🔐 Authentication

### Registration

1. Click "Register" button in the header
2. Enter username, email, and password (minimum 6 characters)
3. Click "Register"
4. You'll be automatically logged in after registration

### Login

1. Click "Login" button in the header
2. Enter username and password
3. Click "Login"
4. Your session will be maintained until logout

### Chat History

- Chat history is automatically saved when you're logged in
- Click "Chat History" to view all your previous queries
- History includes queries, answers, and timestamps

### Security Features

- **Password Hashing**: Bcrypt with salt
- **JWT Tokens**: Secure token-based authentication
- **Session Management**: Secure session handling
- **SQL Injection Protection**: SQLAlchemy ORM
- **CORS Protection**: Configured for allowed origins

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Ollama Configuration
EMBED_URL=http://127.0.0.1:11434/api/embed
EMBED_MODEL=nomic-embed-text:latest
OLLAMA_URL=http://127.0.0.1:11434
GEN_MODEL=llama3.2:3b

# Database
DATABASE_URL=sqlite:///./rag_system.db

# Security (CHANGE IN PRODUCTION!)
SECRET_KEY=your-secret-key-change-this-in-production
FLASK_SECRET_KEY=your-flask-secret-key-change-this-in-production

# API Configuration
API_URL=http://localhost:8000

# Chunking Configuration
SEGMENTS_PER_CHUNK=5
JSON_DIR=json_output
```

### Model Configuration

- **Embedding Model**: Default is `nomic-embed-text:latest`. You can use other models like `bge-m3` or `mxbai-embed-large`.
- **Generation Model**: Default is `llama3.2:3b`. You can use other models like `llama3.2:1b` or `mistral:7b`.

### Chunking Configuration

- **SEGMENTS_PER_CHUNK**: Number of transcript segments per chunk (default: 5)
- Adjust this in `chunks_with_timestamp.py` and `chunk_to_json.py`

## 🐛 Troubleshooting

### Common Issues

#### 1. "Unable to connect to API"
- **Solution**: Ensure FastAPI backend is running on port 8000
- Check: `http://localhost:8000/status`

#### 2. "Embeddings not found"
- **Solution**: Run the pipeline to generate embeddings first
- Or use "Rebuild Index" button in the UI
- Check: `embeddings.parquet` and `vector_index.faiss` exist

#### 3. "Query failed" or "Generation error"
- **Solution**: Check that Ollama is running
- Verify models are installed: `ollama list`
- Check: `OLLAMA_URL` and `GEN_MODEL` in `.env`

#### 4. "Registration failed"
- **Solution**: Check database is initialized
- Verify username/email is not already taken
- Check password is at least 6 characters
- Check API server is running

#### 5. "Login failed"
- **Solution**: Verify username and password are correct
- Check API server is running
- Check database connection

#### 6. "Database error"
- **Solution**: Delete `rag_system.db` and restart API server
- Database will be recreated automatically
- Or run: `python setup_database.py`

#### 7. "CORS errors"
- **Solution**: Check CORS configuration in `api.py`
- Ensure Flask app URL is in allowed origins

#### 8. "Module not found"
- **Solution**: Install dependencies: `pip install -r requirements.txt`
- Verify virtual environment is activated

### Debug Mode

Enable debug mode for detailed error messages:

```python
# In api.py
app = FastAPI(debug=True)

# In app.py
app.run(debug=True)
```

## 🛠️ Development

### Project Structure

- **Backend API**: `api.py` - FastAPI application
- **Frontend Server**: `app.py` - Flask application
- **Authentication**: `auth.py` - JWT and password utilities
- **Database**: `database.py` - SQLAlchemy models
- **RAG Core**: `read_chunks.py` - Embedding and search logic

### Adding New Features

1. **New API Endpoint**: Add to `api.py`
2. **New UI Feature**: Modify `templates/index.html` and `static/js/app.js`
3. **New Database Model**: Add to `database.py`
4. **New Authentication**: Extend `auth.py`

### Testing

Test the setup:
```bash
python verify_setup.py
```

Test registration:
```bash
python test_registration.py
```

### Database Migrations

For production, consider using Alembic:
```bash
pip install alembic
alembic init alembic
```

## 📝 Scripts Reference

### Core Scripts

- **`speech_to_text.py`**: Transcribe audio files using Whisper
- **`chunks_with_timestamp.py`**: Create timestamped text chunks
- **`chunk_to_json.py`**: Convert transcripts to JSON format
- **`read_chunks.py`**: Core RAG library (embeddings, search, generation)
- **`incomings.py`**: CLI entrypoint for queries

### Server Scripts

- **`run_api.py`**: Start FastAPI backend server
- **`run_app.py`**: Start Flask frontend server
- **`setup_database.py`**: Initialize database

### Utility Scripts

- **`verify_setup.py`**: Verify installation and setup
- **`test_registration.py`**: Test registration endpoint
- **`test_servers.py`**: Test server connectivity

## 🔒 Security Notes

### Production Deployment

1. **Change Secret Keys**: Always change `SECRET_KEY` and `FLASK_SECRET_KEY` in production
2. **Use HTTPS**: Use HTTPS in production to protect tokens in transit
3. **Database Security**: Use PostgreSQL with proper authentication in production
4. **Environment Variables**: Store secrets in environment variables, not in code
5. **Rate Limiting**: Add rate limiting to prevent abuse
6. **Input Validation**: All inputs are validated, but review for your use case

### Password Security

- Passwords are hashed using bcrypt with salt
- Minimum password length: 6 characters (configurable)
- Passwords are never stored in plain text

### Token Security

- JWT tokens expire after 7 days (configurable)
- Tokens are stored in localStorage (consider httpOnly cookies for production)
- Tokens are sent in Authorization header

## 📚 Additional Documentation

- **`AUTH_SETUP.md`**: Detailed authentication setup guide
- **`QUICK_START_AUTH.md`**: Quick start guide for authentication
- **`UI_README.md`**: UI-specific documentation
- **`REGISTRATION_FIX_SUMMARY.md`**: Registration troubleshooting guide

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License

## 🙏 Acknowledgments

- OpenAI Whisper for speech-to-text
- Ollama for embeddings and generation
- FAISS for vector search
- FastAPI and Flask for web frameworks

## 📞 Support

For issues and questions:
1. Check the Troubleshooting section
2. Review the documentation files
3. Check existing issues
4. Create a new issue with detailed information

## 🎯 Next Steps

- [ ] Add password reset functionality
- [ ] Add email verification
- [ ] Add user profile management
- [ ] Add chat history search and filtering
- [ ] Add export chat history feature
- [ ] Add user roles and permissions
- [ ] Add API rate limiting
- [ ] Add unit tests
- [ ] Add integration tests
- [ ] Migrate to PostgreSQL for production

---

**Happy Querying! 🚀**
