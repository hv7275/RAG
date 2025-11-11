# Quick Start - Authentication & Database

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize Database** (optional - auto-creates on first run):
   ```bash
   python setup_database.py
   ```

3. **Set Environment Variables** (optional - has defaults):
   Create a `.env` file:
   ```env
   SECRET_KEY=your-secret-key-here
   FLASK_SECRET_KEY=your-flask-secret-key-here
   ```

## Running the System

1. **Start FastAPI Backend**:
   ```bash
   python run_api.py
   ```
   Runs on: http://localhost:8000

2. **Start Flask Frontend**:
   ```bash
   python run_app.py
   ```
   Runs on: http://localhost:5000

## Using Authentication

### Register a New User
1. Open http://localhost:5000
2. Click "Register" button
3. Enter username, email, and password
4. Click "Register"
5. You'll be automatically logged in

### Login
1. Click "Login" button
2. Enter username and password
3. Click "Login"

### View Chat History
1. After logging in, click "Chat History" button
2. View all your previous queries and answers

### Logout
1. Click "Logout" button
2. Session is cleared

## Features

✅ **User Registration & Login**
✅ **JWT Token Authentication**
✅ **Password Hashing (bcrypt)**
✅ **Chat History Storage**
✅ **Optional Authentication** (queries work without login)
✅ **Automatic History Saving** (when logged in)
✅ **Secure Session Management**

## Database

- **Database File**: `rag_system.db` (SQLite)
- **Auto-created**: On first API start
- **Tables**: `users`, `chat_history`

## API Endpoints

### Public Endpoints
- `POST /register` - Register new user
- `POST /login` - Login and get token
- `POST /query` - Query RAG system (works without auth)
- `GET /status` - System status

### Protected Endpoints (require authentication)
- `GET /me` - Get current user info
- `GET /chat-history` - Get chat history
- `DELETE /chat-history/{chat_id}` - Delete chat history item

## Notes

- **Queries work without login**: You can use the system without registering
- **History is saved when logged in**: Chat history is only saved if you're authenticated
- **Tokens expire**: JWT tokens expire after 7 days
- **Password security**: Passwords are hashed with bcrypt

## Troubleshooting

### Database Issues
- Delete `rag_system.db` and restart API
- Database auto-creates on first start

### Authentication Issues
- Check that dependencies are installed
- Verify SECRET_KEY is set (or use default)
- Check server logs for errors

### Chat History Not Saving
- Verify you're logged in (check header)
- Check database connection
- Verify token is being sent

## Next Steps

See `AUTH_SETUP.md` for detailed documentation and advanced configuration.

