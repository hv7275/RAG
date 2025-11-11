# Authentication and Database Setup Guide

## Overview

The RAG system now includes user authentication and chat history storage. Users can register, login, and their queries are automatically saved to the database.

## Features

- ✅ User registration and login
- ✅ JWT token-based authentication
- ✅ Password hashing with bcrypt
- ✅ Chat history storage per user
- ✅ Optional authentication (queries work without login, but history is saved when logged in)
- ✅ Secure session management

## Database

The system uses SQLite database by default (`rag_system.db`). The database includes:

### Users Table
- `id`: Primary key
- `username`: Unique username
- `email`: Unique email address
- `hashed_password`: Bcrypt hashed password
- `created_at`: Account creation timestamp
- `updated_at`: Last update timestamp

### Chat History Table
- `id`: Primary key
- `user_id`: Foreign key to users table
- `query`: User's query text
- `answer`: Generated answer (if available)
- `chunks_count`: Number of relevant chunks found
- `created_at`: Query timestamp

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

New dependencies include:
- `sqlalchemy`: Database ORM
- `python-jose[cryptography]`: JWT token handling
- `passlib[bcrypt]`: Password hashing
- `python-multipart`: Form data parsing

### 2. Initialize Database

The database is automatically initialized when the API starts. The database file (`rag_system.db`) will be created in the project root directory.

### 3. Environment Variables

Add to your `.env` file:

```env
# Secret key for JWT tokens (change this in production!)
SECRET_KEY=your-secret-key-change-this-in-production

# Flask secret key for sessions
FLASK_SECRET_KEY=your-flask-secret-key-change-this-in-production

# Database URL (optional, defaults to SQLite)
DATABASE_URL=sqlite:///./rag_system.db
```

### 4. Start the Servers

```bash
# Terminal 1 - FastAPI Backend
python run_api.py

# Terminal 2 - Flask Frontend
python run_app.py
```

## Usage

### Registration

1. Click "Register" button in the header
2. Enter username, email, and password
3. Click "Register"
4. You'll be automatically logged in after registration

### Login

1. Click "Login" button in the header
2. Enter username and password
3. Click "Login"

### Chat History

1. After logging in, click "Chat History" button
2. View all your previous queries and answers
3. History is automatically saved when you're logged in

### Logout

1. Click "Logout" button in the header
2. Session is cleared and you're logged out

## API Endpoints

### Authentication Endpoints

- `POST /register`: Register a new user
  - Body: `{"username": "string", "email": "string", "password": "string"}`
  - Returns: User information

- `POST /login`: Login and get access token
  - Body: `{"username": "string", "password": "string"}`
  - Returns: Access token and user information

- `GET /me`: Get current user information (requires authentication)
  - Headers: `Authorization: Bearer <token>`
  - Returns: User information

### Chat History Endpoints

- `GET /chat-history`: Get chat history for current user (requires authentication)
  - Headers: `Authorization: Bearer <token>`
  - Query params: `skip` (optional), `limit` (optional, default: 50)
  - Returns: List of chat history items

- `DELETE /chat-history/{chat_id}`: Delete a specific chat history item (requires authentication)
  - Headers: `Authorization: Bearer <token>`
  - Returns: Success message

### Query Endpoint (Updated)

- `POST /query`: Query the RAG system (authentication optional)
  - Headers: `Authorization: Bearer <token>` (optional)
  - Body: `{"query": "string", "k": 4, "generate_answer": true, "max_ctx": 4000}`
  - If user is authenticated, query is saved to chat history
  - If user is not authenticated, query works normally but is not saved

## Security Notes

1. **Change Secret Keys**: Always change the `SECRET_KEY` and `FLASK_SECRET_KEY` in production
2. **Password Security**: Passwords are hashed using bcrypt before storage
3. **JWT Tokens**: Tokens expire after 7 days (configurable in `auth.py`)
4. **SQL Injection**: SQLAlchemy ORM prevents SQL injection attacks
5. **HTTPS**: Use HTTPS in production to protect tokens in transit

## Database Migrations

For production, consider using Alembic for database migrations:

```bash
pip install alembic
alembic init alembic
```

## Production Considerations

1. **Use PostgreSQL**: For production, switch to PostgreSQL:
   ```env
   DATABASE_URL=postgresql://user:password@localhost/rag_system
   ```

2. **Environment Variables**: Store secrets in environment variables, not in code

3. **Database Backups**: Implement regular database backups

4. **Rate Limiting**: Add rate limiting to prevent abuse

5. **Email Verification**: Add email verification for user registration

6. **Password Reset**: Implement password reset functionality

## Troubleshooting

### Database Issues

If you encounter database errors:
1. Delete `rag_system.db` file
2. Restart the API server (database will be recreated)

### Authentication Issues

If login fails:
1. Check that the database is initialized
2. Verify username and password are correct
3. Check server logs for error messages

### Chat History Not Saving

1. Verify you're logged in (check header for username)
2. Check that the token is being sent in requests
3. Check server logs for database errors

## Next Steps

- Add password reset functionality
- Add email verification
- Add user profile management
- Add chat history search and filtering
- Add export chat history feature
- Add user roles and permissions

