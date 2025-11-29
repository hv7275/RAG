# Flask Frontend for RAG System
from flask import Flask, render_template, request, jsonify, session
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your-secret-key-change-this-in-production")

# FastAPI backend URL
API_URL = os.environ.get("API_URL", "http://localhost:8000")

def get_auth_headers():
    """Get authentication headers if user is logged in"""
    token = session.get('access_token')
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}

@app.route("/")
def index():
    """Main page"""
    return render_template("index.html")

@app.route("/status")
def status():
    """Check API status"""
    try:
        response = requests.get(f"{API_URL}/status", timeout=5)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Unable to connect to API: {str(e)}"}), 503

@app.route("/query", methods=["POST"])
def query():
    """Handle query requests"""
    try:
        data = request.get_json()
        query_text = data.get("query", "")
        k = data.get("k", 4)
        generate_answer = data.get("generate_answer", True)
        max_ctx = data.get("max_ctx", 4000)
        
        if not query_text:
            return jsonify({"error": "Query is required"}), 400
        
        # Forward request to FastAPI backend with auth headers
        response = requests.post(
            f"{API_URL}/query",
            json={
                "query": query_text,
                "k": k,
                "generate_answer": generate_answer,
                "max_ctx": max_ctx,
                "history": data.get("history", []) # Forward history
            },
            headers=get_auth_headers(),
            timeout=120  # Longer timeout for generation
        )
        
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({"error": response.text}), response.status_code
            
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timed out. The query may be taking too long."}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"API request failed: {str(e)}"}), 503
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route("/register", methods=["POST"])
def register():
    """Handle user registration"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"detail": "No data provided"}), 400
        
        response = requests.post(
            f"{API_URL}/register",
            json=data,
            timeout=10
        )
        
        # Try to get JSON response
        try:
            response_data = response.json()
        except:
            response_data = {"detail": response.text or "Registration failed"}
        
        # Return the response with proper status code
        return jsonify(response_data), response.status_code
        
    except requests.exceptions.ConnectionError:
        return jsonify({"detail": "Cannot connect to API server. Please ensure the API is running."}), 503
    except requests.exceptions.Timeout:
        return jsonify({"detail": "Request timed out. Please try again."}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"detail": f"Registration failed: {str(e)}"}), 503
    except Exception as e:
        return jsonify({"detail": f"Unexpected error: {str(e)}"}), 500

@app.route("/login", methods=["POST"])
def login():
    """Handle user login"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"detail": "No data provided"}), 400
        
        response = requests.post(
            f"{API_URL}/login",
            json=data,
            timeout=10
        )
        
        # Try to get JSON response
        try:
            response_data = response.json()
        except:
            response_data = {"detail": response.text or "Login failed"}
        
        if response.status_code == 200:
            # Store token in session
            session['access_token'] = response_data.get('access_token')
            session['user'] = response_data.get('user')
            return jsonify(response_data), 200
        else:
            return jsonify(response_data), response.status_code
            
    except requests.exceptions.ConnectionError:
        return jsonify({"detail": "Cannot connect to API server. Please ensure the API is running."}), 503
    except requests.exceptions.Timeout:
        return jsonify({"detail": "Request timed out. Please try again."}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"detail": f"Login failed: {str(e)}"}), 503
    except Exception as e:
        return jsonify({"detail": f"Unexpected error: {str(e)}"}), 500

@app.route("/logout", methods=["POST"])
def logout():
    """Handle user logout"""
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200

@app.route("/me", methods=["GET"])
def get_user():
    """Get current user information"""
    try:
        # Get token from Authorization header or session
        auth_header = request.headers.get('Authorization')
        headers = {}
        if auth_header:
            headers['Authorization'] = auth_header
        elif 'access_token' in session:
            headers['Authorization'] = f"Bearer {session['access_token']}"
        else:
            return jsonify({"detail": "Not authenticated"}), 401
        
        response = requests.get(
            f"{API_URL}/me",
            headers=headers,
            timeout=10
        )
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            try:
                error_data = response.json()
                return jsonify(error_data), response.status_code
            except:
                return jsonify({"detail": "Not authenticated"}), 401
    except requests.exceptions.RequestException as e:
        return jsonify({"detail": f"Request failed: {str(e)}"}), 503

@app.route("/chat-history", methods=["GET"])
def get_chat_history():
    """Get chat history for current user"""
    try:
        # Get token from Authorization header or session
        auth_header = request.headers.get('Authorization')
        headers = {}
        if auth_header:
            headers['Authorization'] = auth_header
        elif 'access_token' in session:
            headers['Authorization'] = f"Bearer {session['access_token']}"
        else:
            return jsonify({"detail": "Not authenticated"}), 401
        
        skip = request.args.get('skip', 0, type=int)
        limit = request.args.get('limit', 50, type=int)
        response = requests.get(
            f"{API_URL}/chat-history",
            headers=headers,
            params={'skip': skip, 'limit': limit},
            timeout=10
        )
        try:
            return jsonify(response.json()), response.status_code
        except:
            return jsonify({"detail": response.text or "Request failed"}), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"detail": f"Request failed: {str(e)}"}), 503

@app.route("/rebuild", methods=["POST"])
def rebuild():
    """Trigger rebuild of embeddings"""
    try:
        response = requests.post(f"{API_URL}/rebuild", timeout=300)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Rebuild failed: {str(e)}"}), 503

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

