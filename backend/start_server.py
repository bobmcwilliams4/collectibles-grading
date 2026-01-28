#!/usr/bin/env python
"""Simple server starter - bypasses complex imports"""
import os
import sys

# Set encoding for Windows console
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Clear problematic paths
sys.path = [p for p in sys.path if 'PROMETHEUS_PRIME' not in p and 'GS343' not in p]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Disable vault import by setting env
os.environ['SKIP_VAULT'] = '1'
os.environ['JWT_SECRET_KEY'] = 'collectibles-grading-temp-key-2024'

if __name__ == '__main__':
    import uvicorn
    print("Starting Collectibles Grading Backend...")
    print("Server: http://localhost:8000")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
