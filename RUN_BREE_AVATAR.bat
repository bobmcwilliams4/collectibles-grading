@echo off
title Bree AI Avatar System
cd /d "%~dp0bree-avatar-app"

if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
)

echo.
echo  ======================================
echo   BREE AI AVATAR SYSTEM
echo   ElevenLabs TTS V3 + Lip Sync
echo  ======================================
echo.
echo  Styles: Holographic, Realistic, Stylized, Anime
echo  Voice ID: pzKXffibtCDxnrVO8d1U
echo.

echo Starting Bree Avatar System...
call npm start
