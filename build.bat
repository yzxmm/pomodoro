@echo off
echo [INFO] Starting build process...

:: Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller not found. Installing...
    pip install pyinstaller
)

:: Clean previous build
if exist "dist" (
    echo [INFO] Cleaning dist directory...
    rmdir /s /q "dist"
)
if exist "build" (
    echo [INFO] Cleaning build directory...
    rmdir /s /q "build"
)

:: Run PyInstaller
echo [INFO] Running PyInstaller...
pyinstaller main.spec

if %errorlevel% equ 0 (
    echo [SUCCESS] Build completed successfully!
    echo [INFO] Executable located at: dist\pomodoro_widget.exe
) else (
    echo [ERROR] Build failed. Please check the output above for errors.
)

pause
