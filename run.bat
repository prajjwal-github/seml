@echo off
REM =========================================================================
REM SecureWipe - Local Development Runner
REM Launches PostgreSQL (port 5434), FastAPI (port 8001), and Vite (port 5173)
REM =========================================================================

echo [SecureWipe] Starting all platform services in simulation mode...

REM Check if PostgreSQL is running on port 5434
netstat -ano | findstr 5434 | findstr LISTENING >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [1/3] Starting PostgreSQL daemon on port 5434...
    start "SecureWipe - PostgreSQL (5434)" "C:\Program Files\PostgreSQL\18\bin\postgres.exe" -D "%~dp0pgdata" -p 5434
    timeout /t 3 /nobreak >nul
) else (
    echo [1/3] PostgreSQL is already listening on port 5434.
)

REM Start FastAPI Backend
netstat -ano | findstr 8001 | findstr LISTENING >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [2/3] Starting FastAPI backend on port 8001...
    start "SecureWipe - Backend (8001)" cmd /k "cd /d %~dp0 && .\.venv\Scripts\uvicorn.exe backend.app.main:app --host 127.0.0.1 --port 8001 --reload"
    timeout /t 2 /nobreak >nul
) else (
    echo [2/3] FastAPI backend is already listening on port 8001.
)

REM Start Vite Frontend
netstat -ano | findstr 5173 | findstr LISTENING >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [3/3] Starting Vite frontend on port 5173...
    start "SecureWipe - Frontend (5173)" cmd /k "cd /d %~dp0frontend && npm run dev"
) else (
    echo [3/3] Vite frontend is already listening on port 5173.
)

echo.
echo =========================================================================
echo SecureWipe Platform is live:
echo   - Web UI:           http://127.0.0.1:5173
echo   - Backend API Docs: http://127.0.0.1:8001/docs
echo   - Health Check:     http://127.0.0.1:8001/health
echo   - Public Verifier:  http://127.0.0.1:5173/verify
echo.
echo Persona Logins:
echo   Operator: operator@securewipe.local / Operator123!
echo   Approver: approver@securewipe.local / Approver123!
echo   Admin:    admin@securewipe.local    / Admin123!
echo   Auditor:  auditor@securewipe.local  / Auditor123!
echo =========================================================================
