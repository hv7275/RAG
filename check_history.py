from database import init_db, get_db, User, ChatHistory
from sqlalchemy.orm import Session

init_db()
db = next(get_db())

users = db.query(User).all()
print(f"Found {len(users)} users.")
for u in users:
    print(f"User: {u.username} (ID: {u.id})")
    chats = db.query(ChatHistory).filter(ChatHistory.user_id == u.id).all()
    print(f"  - Chat History Count: {len(chats)}")
    for c in chats[:3]:
        print(f"    - [{c.id}] {c.query[:50]}...")
