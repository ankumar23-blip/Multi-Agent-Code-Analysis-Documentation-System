# Start both backend and frontend services together
# Usage: .\run_all.ps1

Write-Host "Starting Multi-Agent Code Analysis (Backend + Frontend)..." -ForegroundColor Green
Write-Host ""

# Check if venv is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Virtual environment not activated. Activating .venv..." -ForegroundColor Yellow
    & ".\backend\.venv\Scripts\Activate.ps1"
}

Write-Host "Ensuring backend dependencies are installed..." -ForegroundColor Cyan
python -m pip install -q -r backend/requirements.txt

Write-Host "Ensuring dashboard dependencies are installed..." -ForegroundColor Cyan
python -m pip install -q -r dashboard/requirements.txt

Write-Host ""
Write-Host "Starting Backend (FastAPI on port 8000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; python -m uvicorn asgi:app --reload"

Write-Host "Waiting 3 seconds for backend to start..." -ForegroundColor Gray
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "Starting Frontend (Streamlit on port 8501)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; streamlit run dashboard/app.py"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Backend: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Frontend: http://localhost:8501" -ForegroundColor Green
Write-Host "API Docs: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Both services are starting in separate windows." -ForegroundColor Yellow
Write-Host "Close the windows to stop them." -ForegroundColor Yellow
