import requests
import json
import time

def test_query(query):
    url = "http://localhost:8000/query"
    payload = {
        "query": query,
        "k": 6,
        "generate_answer": True
    }
    print(f"Sending query: {query}")
    start_time = time.time()
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        duration = time.time() - start_time
        
        print(f"Time taken: {duration:.2f}s")
        print(f"Answer: {data['answer']}")
        print(f"Chunks used: {len(data['chunks'])}")
        print("-" * 50)
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Response text: {e.response.text}")

if __name__ == "__main__":
    # Wait a bit for server to be ready if we were running this in a real CI/CD
    # But here we assume the user will run the server separately or it's already running.
    # For this test, we will just try to hit it.
    
    print("Test 1: Simple factual query")
    test_query("What is the main topic?")
    
    print("\nTest 2: Summarization")
    test_query("Summarize the key points.")
