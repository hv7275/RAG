from database import SessionLocal, User, DATABASE_URL
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

load_dotenv()

def inspect_user(username):
    print(f"DATABASE_URL: {os.environ.get('DATABASE_URL', 'Not set (using default)')}")
    print(f"Effective DATABASE_URL from module: {DATABASE_URL}")
    
    db: Session = SessionLocal()
    try:
        print(f"Querying for user: {username}")
        user = db.query(User).filter(User.username == username).first()
        if user:
            print(f"User found: ID={user.id}, Username={user.username}, Email={user.email}")
            print(f"Hashed Password: {user.hashed_password}")
            print(f"Created At: {user.created_at}")
        else:
            print("User not found.")
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_user("harsh")
