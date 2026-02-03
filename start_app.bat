@echo off
title DRC-ATEN Production Server
cd /d "%~dp0"

REM Activate virtual environment
call venv\Scripts\activate.bat

echo.
echo ========================================
echo    DRC-ATEN Production Server
echo ========================================
echo.
echo Starting application with PyWebView...
echo Close the window to stop the server
echo.

REM Run PyWebView launcher (blocks until window closes)
python start_webview.py

REM When window closes, script ends automatically
echo.
echo Application stopped.
timeout /t 2 /nobreak >nul
exit
