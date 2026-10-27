@echo off
REM RealityShield-AI: Project Startup Script for Windows CMD

setlocal enabledelayedexpansion

set REPO_ROOT=%~dp0
set BACKEND_DIR=%REPO_ROOT%backend
set FRONTEND_DIR=%REPO_ROOT%frontend
set VENV_DIR=%BACKEND_DIR%\.venv
set PYTHON=%VENV_DIR%\Scripts\python.exe

echo Checking prerequisites...
echo.

REM Check Python
if exist "%PYTHON%" (
    for /f "tokens=*" %%i in ('"%PYTHON%" --version') do echo Python: %%i
) else (
    echo Python virtual environment not found at %PYTHON%
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
    set PYTHON=%VENV_DIR%\Scripts\python.exe
)

REM Check Node.js
for /f "tokens=*" %%i in ('node --version 2^>nul') do (
    echo Node.js: %%i
) || (
    echo WARNING: Node.js not found. Please install Node.js 18+
)

REM Check Docker
for /f "tokens=*" %%i in ('docker --version 2^>nul') do (
    echo Docker: %%i
) || (
    echo WARNING: Docker not found
)

echo.
echo Prerequisites check complete.
echo.

REM Check for .env file
if not exist "%REPO_ROOT%.env" (
    echo .env file not found. Creating from .env.example...
    copy "%REPO_ROOT%.env.example" "%REPO_ROOT%.env"
    echo Please edit .env file and add your API keys.
    echo.
)

echo Installing Python dependencies...
"%PYTHON%" -m pip install --upgrade pip >nul 2>&1
"%PYTHON%" -m pip install -r "%BACKEND_DIR%\requirements.txt"
echo Python dependencies installed.
echo.

echo Installing Node.js dependencies...
cd /d "%FRONTEND_DIR%"
npm install
cd /d "%REPO_ROOT%"
echo Node.js dependencies installed.
echo.

echo Starting RealityShield-AI services...
echo.

REM Start backend
start "RealityShield Backend" cmd /k ^
    cd /d "%BACKEND_DIR%" ^& ^
    set APP_ENV=development ^& ^
    "%PYTHON%" -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

REM Start frontend
start "RealityShield Frontend" cmd /k ^
    cd /d "%FRONTEND_DIR%" ^& ^
    npm run dev -- --host 127.0.0.1 --port 5173

timeout /t 3 >nul

echo.
echo ===========================================
echo RealityShield-AI services started!
echo ===========================================
echo.
echo Frontend:     http://127.0.0.1:5173
echo Backend API:  http://127.0.0.1:8001
echo API Docs:     http://127.0.0.1:8001/docs
echo.
echo To stop services, close the command windows.
echo ===========================================
echo.

pause