@echo off
title Installing Collectibles Grading Launcher
color 0B

echo.
echo  ============================================================
echo   COLLECTIBLES GRADING SYSTEM - LAUNCHER INSTALLER
echo  ============================================================
echo.
echo  This will install the high-end graphical launcher.
echo.

cd /d "%~dp0"

echo  [1/3] Checking Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Node.js not found!
    echo  Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)
node --version
echo.

echo  [2/3] Installing dependencies...
call npm install
if %errorlevel% neq 0 (
    echo  [ERROR] npm install failed!
    pause
    exit /b 1
)
echo.

echo  [3/3] Installation complete!
echo.
echo  ============================================================
echo   To run the launcher, double-click:
echo   RUN_LAUNCHER.bat
echo  ============================================================
echo.

pause
