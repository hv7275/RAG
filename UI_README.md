# RAG System Web UI Documentation

Complete guide to using and developing the RAG System web interface.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Setup](#setup)
- [Running the Application](#running-the-application)
- [User Guide](#user-guide)
- [API Endpoints](#api-endpoints)
- [Authentication](#authentication)
- [Configuration](#configuration)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

The RAG System Web UI provides a modern, user-friendly interface for interacting with the RAG (Retrieval-Augmented Generation) system. It allows users to:

- Query video/audio content using natural language
- View relevant chunks with timestamps and scores
- Generate answers using LLM
- Manage user accounts and authentication
- View and manage chat history
- Copy answers and chunks to clipboard

## 🏗️ Architecture

The web UI is built with a **Flask + FastAPI** architecture:

### Frontend (Flask)
- **Server**: `app.py` - Flask application
- **Templates**: `templates/index.html` - HTML template
- **Static Files**: 
  - `static/css/style.css` - Styles
  - `static/js/app.js` - JavaScript logic

### Backend (FastAPI)
- **Server**: `api.py` - FastAPI REST API
- **Endpoints**: Query, authentication, chat history, status
- **Database**: SQLite (SQLAlchemy ORM)
- **Authentication**: JWT tokens

### Communication Flow

```
User Browser
    ↓
Flask Frontend (port 5000)
    ↓
FastAPI Backend (port 8000)
    ↓
RAG System (read_chunks.py)
    ↓
Ollama (embeddings + generation)
```

## ✨ Features

### Core Features

1. **Query Interface**
   - Natural language query input
   - Configurable top K results
   - Optional answer generation
   - Real-time status updates

2. **Results Display**
   - Generated answers with copy button
   - Relevant chunks with scores
   - Timestamp information
   - Source video titles
   - Copy individual chunks

3. **User Authentication**
   - User registration
   - User login
   - Secure session management
   - JWT token authentication

4. **Chat History**
   - Automatic history saving (when logged in)
   - View previous queries
   - View previous answers
   - Timestamp information

5. **System Management**
   - Status monitoring
   - Index rebuilding
   - Error handling
   - Connection status

### UI Components

- **Header**: Title, authentication buttons, user info
- **Status Bar**: System status, chunk count, Ollama status
- **Query Section**: Input form, settings, search button
- **Results Section**: Answers, chunks, error messages
- **Modals**: Login, register, chat history
- **Footer**: Rebuild index button, version info

## 🚀 Setup

### Prerequisites

1. **Python 3.8+** installed
2. **Ollama** installed and running
3. **Dependencies** installed (see main README)

### Installation Steps

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   Create `.env` file:
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

3. **Initialize Database**:
   ```bash
   python setup_database.py
   ```

4. **Prepare Data**:
   - Place audio files in `audios/`
   - Run `python speech_to_text.py`
   - Run `python chunk_to_json.py`
   - Build embeddings (via UI or API)

## 🏃 Running the Application

### Option 1: Run Both Servers (Recommended)

**Terminal 1 - FastAPI Backend:**
```bash
python run_api.py
```
Backend runs on: `http://localhost:8000`

**Terminal 2 - Flask Frontend:**
```bash
python run_app.py
```
Frontend runs on: `http://localhost:5000`

### Option 2: Use Start Scripts

**Windows:**
```bash
start_servers.bat
```

**PowerShell:**
```bash
start_servers.ps1
```

### Option 3: Run Directly

**FastAPI:**
```bash
python api.py
# or
uvicorn api:app --host 0.0.0.0 --port 8000
```

**Flask:**
```bash
python app.py
# or
flask run
```

### Access the UI

Open your browser and navigate to:
```
http://localhost:5000
```

## 📖 User Guide

### Getting Started

1. **Check System Status**
   - Status bar shows system status
   - Green "Ready" indicates system is ready
   - Chunk count shows available chunks

2. **Register/Login**
   - Click "Register" to create an account
   - Click "Login" to access existing account
   - Session persists until logout

3. **Make a Query**
   - Enter your question in the query box
   - Adjust settings (top K, generate answer)
   - Click "Search" button
   - Wait for results

4. **View Results**
   - Generated answer (if enabled)
   - Relevant chunks with scores
   - Timestamps and source information

5. **Copy Content**
   - Click copy button on answer
   - Click copy button on individual chunks
   - Content is copied to clipboard

6. **View History**
   - Click "Chat History" button
   - View all previous queries
   - See answers and timestamps

### Query Settings

- **Top K Results**: Number of relevant chunks to retrieve (default: 4)
  - Higher values: More chunks, slower search
  - Lower values: Fewer chunks, faster search

- **Generate Answer**: Enable/disable answer generation
  - Enabled: LLM generates answer from chunks
  - Disabled: Only shows relevant chunks

### Keyboard Shortcuts

- **Enter** (in query box): Submit query
- **Escape**: Close modals
- **Ctrl+C**: Copy selected text

## 🔌 API Endpoints

### Flask Frontend Endpoints

#### `GET /`
- **Description**: Main UI page
- **Response**: HTML page

#### `GET /status`
- **Description**: Proxy to FastAPI status endpoint
- **Response**: System status JSON

#### `POST /query`
- **Description**: Proxy to FastAPI query endpoint
- **Body**: Query request JSON
- **Response**: Query response JSON

#### `POST /register`
- **Description**: Proxy to FastAPI registration endpoint
- **Body**: Registration data JSON
- **Response**: User data JSON

#### `POST /login`
- **Description**: Proxy to FastAPI login endpoint
- **Body**: Login credentials JSON
- **Response**: Token and user data JSON

#### `POST /logout`
- **Description**: Logout user
- **Response**: Success message

#### `GET /me`
- **Description**: Proxy to FastAPI user info endpoint
- **Headers**: Authorization token (optional)
- **Response**: User data JSON

#### `GET /chat-history`
- **Description**: Proxy to FastAPI chat history endpoint
- **Headers**: Authorization token
- **Response**: Chat history JSON

#### `POST /rebuild`
- **Description**: Proxy to FastAPI rebuild endpoint
- **Response**: Rebuild status JSON

### FastAPI Backend Endpoints

See main README for detailed API documentation.

## 🔐 Authentication

### Registration

1. Click "Register" button
2. Fill in:
   - Username (unique)
   - Email (unique, valid format)
   - Password (minimum 6 characters)
3. Click "Register"
4. Automatic login after registration

### Login

1. Click "Login" button
2. Enter:
   - Username
   - Password
3. Click "Login"
4. Session maintained until logout

### Logout

1. Click "Logout" button
2. Session cleared
3. Token removed from storage

### Session Management

- Tokens stored in `localStorage`
- Tokens sent in `Authorization` header
- Tokens expire after 7 days
- Automatic token validation

### Chat History

- **Automatic Saving**: Queries saved when logged in
- **View History**: Click "Chat History" button
- **History Includes**: Query, answer, timestamp, chunk count
- **Private**: Each user sees only their history

## ⚙️ Configuration

### Environment Variables

```env
# Ollama Configuration
EMBED_URL=http://127.0.0.1:11434/api/embed
EMBED_MODEL=nomic-embed-text:latest
OLLAMA_URL=http://127.0.0.1:11434
GEN_MODEL=llama3.2:3b

# Database
DATABASE_URL=sqlite:///./rag_system.db

# Security
SECRET_KEY=your-secret-key-change-this-in-production
FLASK_SECRET_KEY=your-flask-secret-key-change-this-in-production

# API Configuration
API_URL=http://localhost:8000
```

### Frontend Configuration

Edit `static/js/app.js`:
```javascript
const API_BASE = '';  // Empty for same origin, or set to API URL
```

### Backend Configuration

Edit `app.py`:
```python
API_URL = os.environ.get("API_URL", "http://localhost:8000")
```

### CORS Configuration

Edit `api.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://127.0.0.1:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🛠️ Development

### Project Structure

```
RAG/
├── app.py                  # Flask frontend server
├── api.py                  # FastAPI backend server
├── templates/
│   └── index.html          # Main UI template
├── static/
│   ├── css/
│   │   └── style.css       # Styles
│   └── js/
│       └── app.js          # JavaScript logic
```

### Modifying the UI

#### HTML Template

Edit `templates/index.html`:
- Header section
- Query form
- Results display
- Modals (login, register, history)

#### Styles

Edit `static/css/style.css`:
- Color scheme
- Layout
- Responsive design
- Animations

#### JavaScript

Edit `static/js/app.js`:
- API calls
- Event handlers
- UI updates
- Authentication logic

### Adding New Features

1. **New UI Component**:
   - Add HTML to `templates/index.html`
   - Add styles to `static/css/style.css`
   - Add JavaScript to `static/js/app.js`

2. **New API Endpoint**:
   - Add endpoint to `api.py`
   - Add proxy route to `app.py` (if needed)
   - Update JavaScript to call endpoint

3. **New Authentication Feature**:
   - Update `auth.py`
   - Update `api.py`
   - Update `app.py`
   - Update JavaScript

### Testing

1. **Test Setup**:
   ```bash
   python verify_setup.py
   ```

2. **Test Registration**:
   ```bash
   python test_registration.py
   ```

3. **Test Servers**:
   ```bash
   python test_servers.py
   ```

### Debugging

1. **Enable Debug Mode**:
   ```python
   # In app.py
   app.run(debug=True)
   
   # In api.py
   app = FastAPI(debug=True)
   ```

2. **Check Browser Console**:
   - Open browser developer tools
   - Check console for errors
   - Check network tab for API calls

3. **Check Server Logs**:
   - FastAPI logs in terminal
   - Flask logs in terminal
   - Check for error messages

## 🐛 Troubleshooting

### Common Issues

#### 1. "Unable to connect to API"
- **Cause**: FastAPI backend not running
- **Solution**: Start backend server on port 8000
- **Check**: `http://localhost:8000/status`

#### 2. "Registration failed"
- **Cause**: API server not running or database error
- **Solution**: Check API server, check database
- **Check**: Browser console for error details

#### 3. "Login failed"
- **Cause**: Wrong credentials or API error
- **Solution**: Verify username/password, check API server
- **Check**: Browser console for error details

#### 4. "Query failed"
- **Cause**: Ollama not running or model not available
- **Solution**: Start Ollama, check models
- **Check**: `ollama list`

#### 5. "Chat history not loading"
- **Cause**: Not logged in or API error
- **Solution**: Login first, check API server
- **Check**: Browser console for error details

#### 6. "CORS errors"
- **Cause**: CORS not configured correctly
- **Solution**: Check CORS configuration in `api.py`
- **Check**: Allowed origins include Flask URL

#### 7. "Status shows 'Not Ready'"
- **Cause**: Embeddings not built or files missing
- **Solution**: Build embeddings, check files exist
- **Check**: `embeddings.parquet`, `vector_index.faiss`

#### 8. "Copy button not working"
- **Cause**: Browser permissions or JavaScript error
- **Solution**: Check browser console, grant clipboard permissions
- **Check**: Browser settings for clipboard access

### Debug Steps

1. **Check Server Status**:
   ```bash
   curl http://localhost:8000/status
   curl http://localhost:5000/status
   ```

2. **Check Database**:
   ```bash
   python -c "from database import SessionLocal, User; db = SessionLocal(); print(db.query(User).count()); db.close()"
   ```

3. **Check Ollama**:
   ```bash
   ollama list
   curl http://localhost:11434/api/tags
   ```

4. **Check Logs**:
   - FastAPI logs in terminal
   - Flask logs in terminal
   - Browser console logs

## 📝 Best Practices

### Security

1. **Change Secret Keys**: Always change default secret keys
2. **Use HTTPS**: Use HTTPS in production
3. **Validate Input**: All inputs are validated
4. **Sanitize Output**: All outputs are sanitized
5. **Token Security**: Tokens expire after 7 days

### Performance

1. **Cache Embeddings**: Embeddings are cached in memory
2. **Lazy Loading**: Load data only when needed
3. **Optimize Queries**: Use appropriate K values
4. **Connection Pooling**: Database connections are pooled

### User Experience

1. **Error Messages**: Clear, helpful error messages
2. **Loading States**: Show loading indicators
3. **Feedback**: Provide user feedback
4. **Responsive Design**: Mobile-friendly design

## 🎨 Customization

### Changing Colors

Edit `static/css/style.css`:
```css
:root {
  --primary-color: #667eea;
  --secondary-color: #764ba2;
  --success-color: #10b981;
  --error-color: #ef4444;
}
```

### Changing Layout

Edit `templates/index.html` and `static/css/style.css`:
- Modify HTML structure
- Update CSS grid/flexbox
- Adjust responsive breakpoints

### Adding Features

1. **New Modal**: Add HTML, CSS, JavaScript
2. **New Button**: Add HTML, event handler
3. **New Endpoint**: Add API endpoint, update JavaScript

## 📚 Additional Resources

- **Main README**: See `README.md` for complete documentation
- **Authentication Guide**: See `AUTH_SETUP.md`
- **Quick Start**: See `QUICK_START_AUTH.md`
- **API Documentation**: See FastAPI docs at `http://localhost:8000/docs`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License

---

**Happy Querying! 🚀**
