@echo off
echo ============================================================
echo DRC Online - Installation Script
echo Premeir System Engineering Co.ltd
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo Please install Python 3.8 or higher from https://www.python.org/
    pause
    exit /b 1
)

echo [1/4] Python found
python --version

echo.
echo [2/4] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)

echo [3/4] Installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [4/4] Creating startup script...
echo @echo off > start_drc_online.bat
echo cd /d "%%~dp0" >> start_drc_online.bat
echo call venv\Scripts\activate.bat >> start_drc_online.bat
echo python app.py >> start_drc_online.bat
echo pause >> start_drc_online.bat

echo.
echo ============================================================
echo Installation completed successfully!
echo ============================================================
echo.
echo To start DRC Online, run: start_drc_online.bat
echo.
pause
