import requests
import json
import time
import random
import string

API_URL = "http://localhost:8000"

def get_random_string(length=8):
    return ''.join(random.choice(string.ascii_letters) for _ in range(length))

def test_auth_flow():
    username = f"user_{get_random_string()}"
    password = "password123"
    email = f"{username}@example.com"
    
    print(f"Testing with user: {username}")
    
    # 1. Register
    print("\n1. Registering...")
    resp = requests.post(f"{API_URL}/register", json={
        "username": username,
        "email": email,
        "password": password
    })
    if resp.status_code != 200:
        print(f"Registration failed: {resp.text}")
        return
    print("   [OK] Registered")
    
    # 2. Login
    print("\n2. Logging in...")
    resp = requests.post(f"{API_URL}/login", json={
        "username": username,
        "password": password
    })
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return
    token_data = resp.json()
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("   [OK] Logged in")
    
    # 3. Get Me
    print("\n3. Getting user info...")
    resp = requests.get(f"{API_URL}/me", headers=headers)
    if resp.status_code != 200:
        print(f"Get Me failed: {resp.text}")
        return
    print(f"   [OK] User info: {resp.json()['username']}")
    
    # 4. Perform Query (to create history)
    print("\n4. Performing query...")
    resp = requests.post(f"{API_URL}/query", json={
        "query": "test query",
        "k": 1,
        "generate_answer": False
    }, headers=headers)
    if resp.status_code != 200:
        print(f"Query failed: {resp.text}")
        return
    print("   [OK] Query successful")
    
    # 5. Get Chat History
    print("\n5. Getting chat history...")
    resp = requests.get(f"{API_URL}/chat-history", headers=headers)
    if resp.status_code != 200:
        print(f"Get history failed: {resp.text}")
        return
    history = resp.json()
    print(f"   [OK] History count: {history['total']}")
    if history['total'] > 0:
        print(f"   Last query: {history['chats'][0]['query']}")
    else:
        print("   [WARN] No history found (maybe async saving issue?)")

if __name__ == "__main__":
    try:
        test_auth_flow()
    except Exception as e:
        print(f"Test failed with exception: {e}")
