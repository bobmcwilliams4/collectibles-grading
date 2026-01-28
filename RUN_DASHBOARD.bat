@echo off
title Collectibles Grading - Matrix Dashboard
cd /d "%~dp0dashboard-app"

if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
)

echo Starting Matrix Dashboard...
call npm start
