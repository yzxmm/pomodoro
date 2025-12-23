@echo off
cd /d "%~dp0"

echo [1/3] Updating manifest.json...
python tools/build_cloud_manifest.py

echo.
echo [2/3] Preparing to upload to GitHub (pomodoro-assets)...
cd cloud

:: Initialize git if not already done (safe to run multiple times)
if not exist .git (
    echo Initializing Git repository...
    git init
    git branch -M main
    git remote add origin https://github.com/yzxmm/pomodoro-assets.git
)

:: Ensure user identity is set
git config user.name "yzxmm"
git config user.email "1240028169@qq.com"

:: Pull from remote first to avoid conflicts (if remote has changes)
echo.
echo [2.5/3] Pulling from GitHub...
git pull origin main --rebase

:: Add all changes
git add .

:: Commit with timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set timestamp=%datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2% %datetime:~8,2%:%datetime:~10,2%
git commit -m "Auto-update assets: %timestamp%"

echo.
echo [3/3] Pushing to GitHub...
git push -u origin main

echo.
if %errorlevel% equ 0 (
    echo ========================================
    echo SUCCESS! Assets uploaded successfully.
    echo ========================================
) else (
    echo ========================================
    echo FAILED! Please check your internet or git credentials.
    echo ========================================
)
pause