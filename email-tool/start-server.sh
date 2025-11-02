#!/bin/bash
echo "Starting web server on port 8000..."
echo "Open your browser to: http://localhost:8000/"
echo "Press Ctrl+C to stop the server"
echo ""
python3 -m http.server 8000
