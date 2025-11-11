# PowerShell script to start both servers
Write-Host "Starting RAG System Servers..." -ForegroundColor Green
Write-Host ""

# Start FastAPI Backend
Write-Host "Starting FastAPI Backend on http://localhost:8000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python run_api.py"

Start-Sleep -Seconds 3

# Start Flask Frontend
Write-Host "Starting Flask Frontend on http://localhost:5000..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python run_app.py"

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Servers are starting!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "FastAPI Backend: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Flask Frontend:  http://localhost:5000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Open your browser and navigate to:" -ForegroundColor Yellow
Write-Host "http://localhost:5000" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

