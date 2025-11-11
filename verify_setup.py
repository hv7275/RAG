#!/usr/bin/env python3
"""
Verify that all dependencies are installed and the system is ready to run
"""
import sys

def check_imports():
    """Check if all required modules can be imported"""
    print("Checking imports...")
    errors = []
    
    try:
        from jose import JWTError, jwt
        print("  [OK] python-jose")
    except ImportError as e:
        print(f"  [ERROR] python-jose: {e}")
        errors.append("python-jose")
    
    try:
        from passlib.context import CryptContext
        print("  [OK] passlib")
    except ImportError as e:
        print(f"  [ERROR] passlib: {e}")
        errors.append("passlib")
    
    try:
        from sqlalchemy import create_engine
        print("  [OK] sqlalchemy")
    except ImportError as e:
        print(f"  [ERROR] sqlalchemy: {e}")
        errors.append("sqlalchemy")
    
    try:
        from pydantic import EmailStr
        print("  [OK] pydantic")
    except ImportError as e:
        print(f"  [ERROR] pydantic: {e}")
        errors.append("pydantic")
    
    try:
        import auth
        print("  [OK] auth module")
    except Exception as e:
        print(f"  [ERROR] auth module: {e}")
        errors.append("auth")
    
    try:
        import database
        print("  [OK] database module")
    except Exception as e:
        print(f"  [ERROR] database module: {e}")
        errors.append("database")
    
    try:
        import api
        print("  [OK] api module")
        print(f"  [INFO] API has {len(api.app.routes)} endpoints")
    except Exception as e:
        print(f"  [ERROR] api module: {e}")
        errors.append("api")
    
    try:
        import app
        print("  [OK] Flask app module")
    except Exception as e:
        print(f"  [ERROR] Flask app module: {e}")
        errors.append("app")
    
    return errors

def check_database():
    """Check if database can be initialized"""
    print("\nChecking database...")
    try:
        from database import init_db
        init_db()
        print("  [OK] Database initialized")
        
        import os
        if os.path.exists("rag_system.db"):
            print("  [OK] Database file exists")
            size = os.path.getsize("rag_system.db")
            print(f"  [INFO] Database size: {size} bytes")
        else:
            print("  [WARN] Database file not found (will be created on first run)")
        
        return True
    except Exception as e:
        print(f"  [ERROR] Database initialization failed: {e}")
        return False

def main():
    print("=" * 50)
    print("RAG System Setup Verification")
    print("=" * 50)
    
    # Check imports
    errors = check_imports()
    
    # Check database
    db_ok = check_database()
    
    # Summary
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    
    if errors:
        print(f"[ERROR] {len(errors)} module(s) failed to import:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease install missing dependencies:")
        print("  pip install -r requirements.txt")
        return 1
    else:
        print("[SUCCESS] All modules imported successfully!")
    
    if db_ok:
        print("[SUCCESS] Database is ready!")
    else:
        print("[WARN] Database initialization had issues")
    
    print("\n[INFO] System is ready to run!")
    print("\nTo start the servers:")
    print("  1. python run_api.py    (Terminal 1)")
    print("  2. python run_app.py    (Terminal 2)")
    print("  3. Open http://localhost:5000 in your browser")
    
    return 0 if not errors and db_ok else 1

if __name__ == "__main__":
    sys.exit(main())

