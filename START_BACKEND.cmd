@echo off
title COLLECTIBLES GRADING - Backend Server
color 0A

echo ============================================
echo   COLLECTIBLES GRADING - Backend Server
echo   Port: 8000
echo ============================================
echo.

cd /d "E:\ECHO_OMEGA_PRIME\COLLECTIBLES_GRADING\backend"

echo Setting environment variables...
set GS343_DISABLE=1
set PHOENIX_DISABLE=1
set VAULT_DISABLE=1
set SKIP_VAULT=1
set EPOCGS_DEV_MODE=true
set PYTHONSTARTUP=
set PYTHONUSERBASE=

echo Clearing cache...
rd /s /q __pycache__ 2>nul

echo.
echo Starting uvicorn server...
echo.

"H:\Tools\PyManager\pythons\py311\python.exe" -B run_server.py

echo.
echo Server stopped. Press any key to exit...
pause > nul
