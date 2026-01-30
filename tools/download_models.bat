@echo off
chcp 65001 > nul
echo ==========================================
echo   Voice Organizer Model Downloader
echo ==========================================
echo.

cd /d "%~dp0"
:: Navigate to project root (parent of 'tools')
cd ..

:: Check if python is installed
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in your PATH.
    echo Please install Python and try again.
    pause
    exit /b
)

:: Activate venv if it exists (common convention)
if exist venv\Scripts\activate.bat (
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [INFO] No virtual environment found, using system Python.
)

echo [INFO] Starting download process...
python tools\download_models.py

echo.
pause
