#!/usr/bin/env python3
"""
Simple HTTP server for Email Template Tool
Run this from the email-tool directory
"""

import http.server
import socketserver
import os
import sys

PORT = 8000

# Ensure we're in the right directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

Handler = http.server.SimpleHTTPRequestHandler

print(f"""
╔════════════════════════════════════════════════════════╗
║        Email Template Tool - Local Server              ║
╚════════════════════════════════════════════════════════╝

✓ Server starting on port {PORT}...
✓ Open your browser to:

    http://localhost:{PORT}/

Press Ctrl+C to stop the server.
""")

try:
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()
except KeyboardInterrupt:
    print("\n\n✓ Server stopped.")
    sys.exit(0)
except OSError as e:
    if "Address already in use" in str(e):
        print(f"\n✗ Error: Port {PORT} is already in use.")
        print(f"  Try: python3 start-server.py")
        print(f"  Or run: python -m http.server {PORT+1}")
    else:
        print(f"\n✗ Error: {e}")
    sys.exit(1)
