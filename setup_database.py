#!/usr/bin/env python3
"""
Database setup script
Initializes the database and creates all tables
"""
from database import init_db, engine, Base
import os

def setup_database():
    """Initialize the database"""
    print("Setting up database...")
    
    # Create all tables
    init_db()
    
    print("[SUCCESS] Database initialized successfully!")
    print(f"[INFO] Database file: {os.path.abspath('rag_system.db')}")
    print("\nYou can now start the API server with: python run_api.py")

if __name__ == "__main__":
    setup_database()

