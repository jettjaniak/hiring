#!/bin/bash
# Restart the hiring app server on port 8000

# Kill any existing process on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Wait a moment for the port to be released
sleep 2

# Start the server in the background
./venv/bin/python -m src.app --port 8000 &

echo "Server restarted on port 8000"
