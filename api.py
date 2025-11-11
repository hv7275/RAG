# FastAPI Backend for RAG System
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import os
import numpy as np
import pandas as pd
import faiss
import requests
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from read_chunks import (
    JSON_DIR, OUT_PARQUET, OUT_FAISS, OUT_NPY,
    DEFAULT_EMBED_URL, DEFAULT_EMBED_MODEL,
    DEFAULT_OLLAMA_URL, DEFAULT_GEN_MODEL,
    process_json_dir, save_artifacts,
    embed_query, build_faiss_ip_index, search_index,
    generate_answer
)
from database import init_db, get_db, User, ChatHistory
from auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, get_current_user_optional
)

load_dotenv()

# Initialize database
init_db()

app = FastAPI(title="RAG API", version="2.0.0")

# CORS middleware to allow Flask frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://127.0.0.1:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for loaded embeddings
_embeddings_cache = {
    "df": None,
    "index": None,
    "loaded": False
}

def get_embeddings():
    """Load or build embeddings, with caching"""
    if _embeddings_cache["loaded"] and _embeddings_cache["df"] is not None:
        return _embeddings_cache["df"], _embeddings_cache["index"]
    
    json_dir = os.environ.get("JSON_DIR", JSON_DIR)
    embed_url = os.environ.get("EMBED_URL", DEFAULT_EMBED_URL)
    embed_model = os.environ.get("EMBED_MODEL", DEFAULT_EMBED_MODEL)
    
    if os.path.exists(OUT_PARQUET) and os.path.exists(OUT_NPY) and os.path.exists(OUT_FAISS):
        df = pd.read_parquet(OUT_PARQUET)
        idx = faiss.read_index(OUT_FAISS)
        _embeddings_cache["df"] = df
        _embeddings_cache["index"] = idx
        _embeddings_cache["loaded"] = True
        return df, idx
    
    # Build if not exists
    df = process_json_dir(json_dir, embed_url, embed_model)
    if df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No chunks found in {json_dir}. Please run the pipeline first."
        )
    emb, idx = save_artifacts(df)
    _embeddings_cache["df"] = df
    _embeddings_cache["index"] = idx
    _embeddings_cache["loaded"] = True
    return df, idx

# Request/Response models
class QueryRequest(BaseModel):
    query: str
    k: int = 4
    generate_answer: bool = True
    max_ctx: int = 4000

class ChunkResult(BaseModel):
    chunk_id: int
    title: str
    chunk: str
    start: Optional[str]
    end: Optional[str]
    score: float

class QueryResponse(BaseModel):
    query: str
    chunks: List[ChunkResult]
    answer: Optional[str] = None
    message: Optional[str] = None

class StatusResponse(BaseModel):
    embeddings_loaded: bool
    index_exists: bool
    parquet_exists: bool
    total_chunks: int
    message: str

# Authentication models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

class ChatHistoryItem(BaseModel):
    id: int
    query: str
    answer: Optional[str]
    chunks_count: int
    created_at: datetime

class ChatHistoryResponse(BaseModel):
    chats: List[ChatHistoryItem]
    total: int

@app.get("/")
async def root():
    return {"message": "RAG API is running", "version": "2.0.0", "features": ["authentication", "chat_history"]}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/status", response_model=StatusResponse)
async def status():
    """Check the status of embeddings and index"""
    parquet_exists = os.path.exists(OUT_PARQUET)
    index_exists = os.path.exists(OUT_FAISS)
    embeddings_loaded = _embeddings_cache["loaded"]
    total_chunks = 0
    
    if parquet_exists:
        try:
            df = pd.read_parquet(OUT_PARQUET)
            total_chunks = len(df)
        except Exception:
            pass
    
    # Check Ollama connectivity
    ollama_status = "Unknown"
    try:
        ollama_url = os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)
        base = ollama_url.rstrip("/").rstrip("/api/chat").rstrip("/api/generate")
        test_response = requests.get(f"{base}/api/tags", timeout=3)
        if test_response.status_code == 200:
            ollama_status = "Connected"
        else:
            ollama_status = f"Error: {test_response.status_code}"
    except Exception as e:
        ollama_status = f"Not connected: {str(e)[:50]}"
    
    message = "Ready" if (parquet_exists and index_exists) else "Embeddings not found. Please run the pipeline first."
    if ollama_status != "Connected":
        message += f" Ollama: {ollama_status}"
    
    return StatusResponse(
        embeddings_loaded=embeddings_loaded,
        index_exists=index_exists,
        parquet_exists=parquet_exists,
        total_chunks=total_chunks,
        message=message
    )

@app.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Query the RAG system (authentication optional)"""
    try:
        # Load embeddings
        df, idx = get_embeddings()
        
        # Get configuration
        embed_url = os.environ.get("EMBED_URL", DEFAULT_EMBED_URL)
        embed_model = os.environ.get("EMBED_MODEL", DEFAULT_EMBED_MODEL)
        ollama_url = os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)
        gen_model = os.environ.get("GEN_MODEL", DEFAULT_GEN_MODEL)
        
        # Embed query and search
        q_emb = embed_query(request.query, embed_url, embed_model)
        # Ensure 2D array for FAISS (shape: [1, embedding_dim])
        if q_emb.ndim == 1:
            q_emb = q_emb.reshape(1, -1)
        D, I = search_index(idx, q_emb, request.k)
        
        # Convert FAISS indices to Python ints
        hits = [int(i) for i in I[0] if i >= 0]
        scores = [float(d) for d in D[0][:len(hits)]]
        
        # Get chunk results
        chunks = []
        for hit_idx, (hit, score) in enumerate(zip(hits, scores)):
            if hit < len(df):
                row = df.iloc[hit]
                chunks.append(ChunkResult(
                    chunk_id=int(row["chunk_id"]),
                    title=str(row.get("title", "Unknown")),
                    chunk=str(row["chunk"]),
                    start=str(row.get("start", "")) if pd.notna(row.get("start")) else None,
                    end=str(row.get("end", "")) if pd.notna(row.get("end")) else None,
                    score=score
                ))
        
        # Generate answer if requested
        answer = None
        if request.generate_answer:
            try:
                answer = generate_answer(
                    request.query,
                    df,
                    hits,
                    request.max_ctx,
                    gen_model=gen_model,
                    ollama_url=ollama_url
                )
            except Exception as e:
                answer = f"Error generating answer: {str(e)}"
        
        # Save to chat history if user is authenticated
        if current_user:
            try:
                chat_history = ChatHistory(
                    user_id=current_user.id,
                    query=request.query,
                    answer=answer,
                    chunks_count=len(chunks)
                )
                db.add(chat_history)
                db.commit()
            except Exception as e:
                db.rollback()
                # Don't fail the query if history saving fails
                print(f"Failed to save chat history: {e}")
        
        return QueryResponse(
            query=request.query,
            chunks=chunks,
            answer=answer,
            message="Success"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.post("/rebuild")
async def rebuild():
    """Rebuild embeddings and index"""
    try:
        json_dir = os.environ.get("JSON_DIR", JSON_DIR)
        embed_url = os.environ.get("EMBED_URL", DEFAULT_EMBED_URL)
        embed_model = os.environ.get("EMBED_MODEL", DEFAULT_EMBED_MODEL)
        
        # Clear cache
        _embeddings_cache["df"] = None
        _embeddings_cache["index"] = None
        _embeddings_cache["loaded"] = False
        
        # Rebuild
        df = process_json_dir(json_dir, embed_url, embed_model)
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No chunks found in {json_dir}"
            )
        emb, idx = save_artifacts(df)
        
        # Update cache
        _embeddings_cache["df"] = df
        _embeddings_cache["index"] = idx
        _embeddings_cache["loaded"] = True
        
        return {
            "message": "Embeddings rebuilt successfully",
            "total_chunks": len(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rebuild failed: {str(e)}")

# Authentication endpoints
@app.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )
        
        # Validate password length
        if len(user_data.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long"
            )
        
        # Create new user
        try:
            hashed_password = get_password_hash(user_data.password)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to hash password: {str(e)}"
            )
        
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password
        )
        
        try:
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user: {str(e)}"
            )
        
        return UserResponse(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            created_at=new_user.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@app.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login and get access token"""
    # Find user
    user = db.query(User).filter(User.username == user_data.username).first()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.username})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    )

@app.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at
    )

@app.get("/chat-history", response_model=ChatHistoryResponse)
async def get_chat_history(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chat history for the current user"""
    chats = db.query(ChatHistory).filter(
        ChatHistory.user_id == current_user.id
    ).order_by(ChatHistory.created_at.desc()).offset(skip).limit(limit).all()
    
    total = db.query(ChatHistory).filter(ChatHistory.user_id == current_user.id).count()
    
    return ChatHistoryResponse(
        chats=[
            ChatHistoryItem(
                id=chat.id,
                query=chat.query,
                answer=chat.answer,
                chunks_count=chat.chunks_count,
                created_at=chat.created_at
            )
            for chat in chats
        ],
        total=total
    )

@app.delete("/chat-history/{chat_id}")
async def delete_chat_history(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific chat history item"""
    chat = db.query(ChatHistory).filter(
        ChatHistory.id == chat_id,
        ChatHistory.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat history not found"
        )
    
    db.delete(chat)
    db.commit()
    
    return {"message": "Chat history deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
