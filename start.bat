@echo off
echo ==========================================
echo   PRISM - AI Response Evaluator
echo   Starting Backend + Frontend
echo ==========================================

REM Set pip cache to D: to avoid C: space issues
set PIP_CACHE_DIR=D:\pip_cache
set TEMP=D:\pip_tmp
set TMP=D:\pip_tmp

echo.
echo [1/3] Setting up database...
cd /d "d:\Meghana Projects\Infosys\backend"
.\venv\Scripts\python.exe setup_db.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Database setup failed. Check PostgreSQL is running.
    pause
    exit /b 1
)

echo.
echo [2/3] Starting FastAPI backend (http://localhost:8000)...
start "PRISM Backend" cmd /k "cd /d "d:\Meghana Projects\Infosys\backend" && .\venv\Scripts\uvicorn.exe main:app --reload --host 0.0.0.0 --port 8000"

echo Waiting for backend to start...
timeout /t 3 /nobreak >nul

echo.
echo [3/3] Starting React frontend (http://localhost:5173)...
start "PRISM Frontend" cmd /k "cd /d "d:\Meghana Projects\Infosys\frontend" && npm run dev"

echo.
echo ==========================================
echo   PRISM is starting!
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo   API Docs: http://localhost:8000/docs
echo ==========================================
echo.
echo NOTE: First run will take 5-10 minutes to ingest
echo       TruthfulQA + SQuAD into ChromaDB.
echo       Subsequent starts are instant.
echo.
pause
