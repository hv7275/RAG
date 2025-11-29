import requests
import json

FLASK_URL = "http://localhost:5000"

def test_flask_login():
    print(f"Testing Flask Login at {FLASK_URL}...")
    
    # Use a guaranteed non-existent user
    username = "nonexistent_user_12345"
    password = "password123" # We don't know the real password, but we want to see if it crashes
    
    # 2. Login (via Flask)
    print(f"\n2. Logging in via Flask as '{username}'...")
    try:
        resp = requests.post(f"{FLASK_URL}/login", json={
            "username": username,
            "password": password
        })
        print(f"Status: {resp.status_code}")
        try:
            print(f"Response JSON: {resp.json()}")
        except:
            print(f"Response Text (first 500 chars): {resp.text[:500]}")
    except Exception as e:
        print(f"Login request failed: {e}")

if __name__ == "__main__":
    test_flask_login()
