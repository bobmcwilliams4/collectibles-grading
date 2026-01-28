@echo off
title ECHO PRIME OMEGA - Comic Grading System
echo.
echo ====================================================
echo      ECHO PRIME OMEGA COMIC GRADING SYSTEM v1.0.0
echo          AI-Powered Comic Book Grading
echo ====================================================
echo.

:: Set the project directory
set PROJECT_DIR=%~dp0

:: Start the FastAPI backend server
echo [1/2] Starting Backend Server...
start "Comic Grading Backend" /D "%PROJECT_DIR%backend" cmd /c "python -m uvicorn main:app --host 0.0.0.0 --port 8000"

:: Wait for backend to start
echo      Waiting for backend to initialize...
timeout /t 3 /nobreak > nul

:: Start the Electron frontend
echo [2/2] Starting Electron Frontend...
start "Comic Grading Frontend" /D "%PROJECT_DIR%electron-app" cmd /c "npm start"

echo.
echo ====================================================
echo  System Started Successfully!
echo.
echo  Backend API:    http://localhost:8000
echo  API Docs:       http://localhost:8000/docs
echo  WebSocket:      ws://localhost:8000/ws
echo.
echo  The Electron app window should open automatically.
echo ====================================================
echo.
echo Press any key to close this window (servers will keep running)...
pause > nul
