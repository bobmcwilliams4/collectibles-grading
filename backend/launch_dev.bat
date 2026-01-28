@echo off
REM Launch Backend Development Server
REM Sets all required environment variables to disable GS343 interference

echo [COLLECTIBLES GRADING] Starting Backend Server...

REM Change to backend directory
cd /d %~dp0

REM Disable all GS343/Phoenix interference
set GS343_DISABLE=1
set PHOENIX_DISABLE=1
set VAULT_DISABLE=1
set SKIP_VAULT=1

REM Enable dev mode (bypasses auth)
set EPOCGS_DEV_MODE=true

REM Clear Python startup hooks
set PYTHONSTARTUP=
set PYTHONUSERBASE=

REM Clear pycache if exists
rd /s /q __pycache__ 2>nul

REM Launch via run_server.py which sets up env before imports
echo [COLLECTIBLES GRADING] Launching server via run_server.py...
H:\Tools\PyManager\pythons\py311\python.exe -B run_server.py

pause
