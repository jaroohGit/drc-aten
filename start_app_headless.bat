@echo off
title DRC-ATEN Production Server (Headless)
cd /d "%~dp0"

REM Activate virtual environment
call venv\Scripts\activate.bat

echo.
echo ========================================
echo    DRC-ATEN Production Server
echo    HEADLESS MODE
echo ========================================
echo.
echo Server behavior:
echo   - Stops backend when no clients (5 min idle)
echo   - Server keeps running
echo   - Reconnect anytime to resume
echo.
echo Access from local machine:
echo   http://PSE-PCADXX01:5000
echo.
echo Press Ctrl+C to stop server manually
echo ========================================
echo.

REM Set environment variable for headless mode
set HEADLESS_MODE=true
set IDLE_TIMEOUT=300

REM Run Flask server (no PyWebView)
python app.py

echo.
echo Application stopped.
pause
