#!/usr/bin/env python3
"""
Simple script to run the FastAPI server
"""
import uvicorn
import argparse
import os

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run the hiring server')
    parser.add_argument('--port', type=int, default=8000, help='Port to run on')
    parser.add_argument('--reset', action='store_true', help='Reset database before starting')
    args = parser.parse_args()

    # Reset database if requested
    if args.reset:
        db_path = "hiring.db"
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"✓ Removed {db_path}")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=args.port,
        reload=True,
        log_level="info"
    )
