#!/bin/bash
# ECHO PRIME OMEGA - Comic Grading System Launcher

echo ""
echo "===================================================="
echo "     ECHO PRIME OMEGA COMIC GRADING SYSTEM v1.0.0"
echo "         AI-Powered Comic Book Grading"
echo "===================================================="
echo ""

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Start the FastAPI backend server
echo "[1/2] Starting Backend Server..."
cd "$SCRIPT_DIR/backend"
python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
echo "     Waiting for backend to initialize..."
sleep 3

# Check if backend is running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "     Backend started successfully!"
else
    echo "     Warning: Backend may not have started properly"
fi

# Start the Electron frontend
echo "[2/2] Starting Electron Frontend..."
cd "$SCRIPT_DIR/electron-app"
npm start &
FRONTEND_PID=$!

echo ""
echo "===================================================="
echo " System Started Successfully!"
echo ""
echo " Backend API:    http://localhost:8000"
echo " API Docs:       http://localhost:8000/docs"
echo " WebSocket:      ws://localhost:8000/ws"
echo ""
echo " Backend PID:    $BACKEND_PID"
echo " Frontend PID:   $FRONTEND_PID"
echo ""
echo " Press Ctrl+C to stop both services"
echo "===================================================="
echo ""

# Wait for Ctrl+C
trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
