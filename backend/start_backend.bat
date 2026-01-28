@echo off
cd /d E:\ECHO_OMEGA_PRIME\COLLECTIBLES_GRADING\backend
set GS343_DISABLE=1
set PHOENIX_DISABLE=1
set VAULT_DISABLE=1
set EPOCGS_DEV_MODE=true
rd /s /q __pycache__ 2>nul
H:\Tools\PyManager\pythons\py311\python.exe -B -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
