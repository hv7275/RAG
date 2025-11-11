#!/usr/bin/env python3
"""
Start the FastAPI backend server
"""
import sys
import uvicorn

if __name__ == "__main__":
    try:
        uvicorn.run(
            "api:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nShutting down server...")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        print("\nTrying alternative method...")
        # Alternative: use python -m uvicorn
        import subprocess
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "api:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])

