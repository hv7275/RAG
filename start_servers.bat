@echo off
echo Starting RAG System Servers...
echo.

echo Starting FastAPI Backend on http://localhost:8000...
start "FastAPI Backend" cmd /k "python run_api.py"

timeout /t 3 /nobreak >nul

echo Starting Flask Frontend on http://localhost:5000...
start "Flask Frontend" cmd /k "python run_app.py"

timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo Servers are starting!
echo ========================================
echo FastAPI Backend: http://localhost:8000
echo Flask Frontend:  http://localhost:5000
echo.
echo Open your browser and navigate to:
echo http://localhost:5000
echo.
echo Press any key to exit this window...
echo (The server windows will remain open)
pause >nul

