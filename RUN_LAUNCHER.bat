@echo off
title Collectibles Grading - Launcher
cd /d "%~dp0launcher-app"

REM Check if node_modules exists
if not exist "node_modules" (
    echo Installing dependencies first...
    call npm install
    echo.
)

REM Start the Electron launcher
echo Starting Collectibles Grading Launcher...
call npm start
