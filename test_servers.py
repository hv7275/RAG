#!/usr/bin/env python3
"""
Test script to verify servers can start
"""
import sys
import time

print("Testing RAG System Setup...")
print("=" * 50)

# Test 1: Check imports
print("\n1. Testing imports...")
try:
    import api
    print("   [OK] API module imports successfully")
except Exception as e:
    print(f"   [ERROR] API import failed: {e}")
    sys.exit(1)

try:
    import app
    print("   [OK] App module imports successfully")
except Exception as e:
    print(f"   [ERROR] App import failed: {e}")
    sys.exit(1)

# Test 2: Check dependencies
print("\n2. Testing dependencies...")
try:
    import fastapi
    print("   [OK] FastAPI installed")
except ImportError:
    print("   [ERROR] FastAPI not installed. Run: pip install fastapi uvicorn")
    sys.exit(1)

try:
    import flask
    print("   [OK] Flask installed")
except ImportError:
    print("   [ERROR] Flask not installed. Run: pip install flask")
    sys.exit(1)

try:
    import uvicorn
    print("   [OK] Uvicorn installed")
except ImportError:
    print("   [ERROR] Uvicorn not installed. Run: pip install uvicorn")
    sys.exit(1)

# Test 3: Check embeddings
print("\n3. Checking embeddings...")
import os
if os.path.exists("embeddings.parquet") and os.path.exists("vector_index.faiss"):
    print("   [OK] Embeddings and index files found")
else:
    print("   [WARN] Embeddings not found. System will build them on first query.")
    print("          Make sure JSON files exist in json_output/ directory")

# Test 4: Check read_chunks module
print("\n4. Testing read_chunks module...")
try:
    from read_chunks import (
        DEFAULT_EMBED_URL, DEFAULT_EMBED_MODEL,
        DEFAULT_OLLAMA_URL, DEFAULT_GEN_MODEL
    )
    print("   [OK] read_chunks module accessible")
    print(f"        Embed URL: {DEFAULT_EMBED_URL}")
    print(f"        Embed Model: {DEFAULT_EMBED_MODEL}")
    print(f"        Ollama URL: {DEFAULT_OLLAMA_URL}")
    print(f"        Gen Model: {DEFAULT_GEN_MODEL}")
except Exception as e:
    print(f"   [ERROR] read_chunks import failed: {e}")
    sys.exit(1)

print("\n" + "=" * 50)
print("[SUCCESS] All tests passed!")
print("\nTo start the servers:")
print("  1. Open a terminal and run: python run_api.py")
print("  2. Open another terminal and run: python run_app.py")
print("  3. Open browser to: http://localhost:5000")
print("\nOr use the startup script:")
print("  Windows: start_servers.bat")
print("  PowerShell: .\\start_servers.ps1")

