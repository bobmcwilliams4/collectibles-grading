@echo off
REM ═══════════════════════════════════════════════════════════════════════════
REM   COLLECTIBLES GRADING SYSTEM - PRODUCTION LAUNCHER
REM   AI-Powered Collectibles Analysis Platform
REM ═══════════════════════════════════════════════════════════════════════════

title Collectibles Grading System Launcher
color 0B

echo.
echo  ╔═══════════════════════════════════════════════════════════════╗
echo  ║                                                               ║
echo  ║   ██████╗ ██████╗ ██╗     ██╗     ███████╗ ██████╗████████╗   ║
echo  ║  ██╔════╝██╔═══██╗██║     ██║     ██╔════╝██╔════╝╚══██╔══╝   ║
echo  ║  ██║     ██║   ██║██║     ██║     █████╗  ██║        ██║      ║
echo  ║  ██║     ██║   ██║██║     ██║     ██╔══╝  ██║        ██║      ║
echo  ║  ╚██████╗╚██████╔╝███████╗███████╗███████╗╚██████╗   ██║      ║
echo  ║   ╚═════╝ ╚═════╝ ╚══════╝╚══════╝╚══════╝ ╚═════╝   ╚═╝      ║
echo  ║                                                               ║
echo  ║              GRADING SYSTEM v2.0                              ║
echo  ║         AI-Powered Collectibles Analysis                      ║
echo  ║                                                               ║
echo  ╚═══════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo [%time%] Initializing launcher...
echo.

REM Check for Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python 3.11+
    pause
    exit /b 1
)

echo [%time%] Select launch mode:
echo.
echo   [1] Launch Full System (Backend + GUI)
echo   [2] Launch Backend Only
echo   [3] Launch GUI Only
echo   [4] Open Web Launcher (Browser-based)
echo   [5] Exit
echo.

set /p choice="Enter choice (1-5): "

if "%choice%"=="1" goto launch_all
if "%choice%"=="2" goto launch_backend
if "%choice%"=="3" goto launch_gui
if "%choice%"=="4" goto launch_web
if "%choice%"=="5" goto end

echo Invalid choice. Launching full system...
goto launch_all

:launch_all
echo.
echo [%time%] Launching full system...
python launcher\launch_system.py
goto end

:launch_backend
echo.
echo [%time%] Starting Backend Server...
cd backend
start "Collectibles Backend" cmd /k "python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
echo [%time%] Backend starting at http://localhost:8000
echo [%time%] API Docs at http://localhost:8000/docs
cd ..
timeout /t 3 >nul
goto end

:launch_gui
echo.
echo [%time%] Starting Electron GUI...
cd electron-app
start "Collectibles GUI" cmd /k "npm start"
cd ..
goto end

:launch_web
echo.
echo [%time%] Opening Web Launcher...
start "" "launcher\launcher.html"
goto end

:end
echo.
echo [%time%] Launcher complete.
echo.
