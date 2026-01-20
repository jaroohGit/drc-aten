@echo off 
cd /d "%~dp0" 
call venv\Scripts\activate.bat 

echo ========================================
echo Starting DRC Online Web Application
echo ========================================
echo.
echo Server will start on: http://localhost:5000
echo Browser will open automatically...
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

REM Start Python app in background and wait a moment for server to start
start /B python app.py

REM Wait 3 seconds for server to initialize
timeout /t 3 /nobreak >nul

REM Open default browser to localhost:5000
start http://localhost:5000

REM Keep the window open to show server logs
echo.
echo Web application is running!
echo Keep this window open to keep the server running.
echo.
pause 
