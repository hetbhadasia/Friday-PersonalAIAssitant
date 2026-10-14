@echo off
REM ==============================================================================
REM F.R.I.D.A.Y. V2 — All-In-One Unified Launch Script for Windows
REM ==============================================================================

echo ============================================================
echo     F.R.I.D.A.Y. V2 -- Starting Full System Stack
echo ============================================================

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Detect Python
set PYTHON_BIN=python
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    set PYTHON_BIN="%SCRIPT_DIR%.venv\Scripts\python.exe"
)

echo Starting FastMCP Server on :8000...
start "FRIDAY - MCP Server" cmd /k "%PYTHON_BIN% server.py"

echo Starting Token Server on :8080...
start "FRIDAY - Token Server" cmd /k "%PYTHON_BIN% token_server.py"

timeout /t 2 /nobreak >nul

echo Starting LiveKit Voice Agent...
start "FRIDAY - Voice Agent" cmd /k "%PYTHON_BIN% agent_friday.py dev"

echo Starting Frontend Web UI...
start "FRIDAY - Frontend" cmd /k "cd frontend && npm run dev"

echo ============================================================
echo All services launched in separate windows!
echo Open http://localhost:5173 in your browser.
echo ============================================================
