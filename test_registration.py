#!/usr/bin/env python3
"""Test registration endpoint"""
import requests
import json

def test_registration():
    url = "http://localhost:8000/register"
    data = {
        "username": "testuser5",
        "email": "test5@test.com",
        "password": "test123"
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2) if response.status_code == 200 else response.text}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to API server. Is it running?")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_registration()

