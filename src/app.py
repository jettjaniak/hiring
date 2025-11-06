#!/usr/bin/env python3
"""
Simple web interface for hiring process client
"""
import sys
import os
import argparse
import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# Get project root directory (parent of src/)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import Database
from src.workflow_loader import WorkflowLoader
from src import dependencies
from src.admin import setup_admin
from src.routes.api.candidates import router as candidates_router
from src.routes.api.task_templates import router as task_templates_router
from src.routes.api.kanban import router as kanban_router
from src.routes.api.tasks import router as tasks_router
from src.routes.api.task_template_links import router as task_template_links_router
from src.routes.api.checklists import router as checklists_api_router
from src.routes.web import home as home_routes
from src.routes.web import candidates as candidate_routes
from src.routes.web import email_templates as email_template_routes
from src.routes.web import task_templates as task_template_routes
from src.routes.web import checklists as checklist_routes
from src.routes.web import kanban as kanban_web_routes
from src.routes.web import special_actions as special_action_routes

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Hiring Process Web Client')
parser.add_argument('--data-dir', default=None, help='Data directory for client files (default: ~/.hiring-client)')
parser.add_argument('--port', type=int, default=5001, help='Port to run on (default: 5001)')
args, _ = parser.parse_known_args()  # Use parse_known_args to avoid conflicts with pytest

# Initialize database
data_dir = args.data_dir or os.path.expanduser('~/.hiring-client')
os.makedirs(data_dir, exist_ok=True)
db_file = os.path.join(data_dir, 'hiring.db')

db = Database(db_file)
db.init_db()
dependencies.init_database(db)

# Load workflows and set for web routes
workflow_loader = WorkflowLoader(workflows_dir=str(project_root / "workflows"), db=db)
home_routes.workflow_loader = workflow_loader
candidate_routes.workflow_loader = workflow_loader

# Initialize FastAPI
app = FastAPI(
    title="Hiring Process API",
    description="Auto-generated REST API for hiring process management",
    version="1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

templates = Jinja2Templates(directory=str(project_root / "templates"))
app.mount("/static", StaticFiles(directory=str(project_root / "static")), name="static")

# Set up SQLAdmin
setup_admin(app, db.engine)

# Include API routers
app.include_router(candidates_router)
app.include_router(task_templates_router)
app.include_router(kanban_router)
app.include_router(tasks_router)
app.include_router(task_template_links_router)
app.include_router(checklists_api_router)

# Include web UI routers
app.include_router(home_routes.router)
app.include_router(candidate_routes.router)
app.include_router(email_template_routes.router)
app.include_router(task_template_routes.router)
app.include_router(checklist_routes.router)
app.include_router(kanban_web_routes.router)
app.include_router(special_action_routes.router)

if __name__ == '__main__':
    print("=" * 60)
    print("Hiring Process Management - Web Interface")
    print("=" * 60)
    print(f"Database: {db_file}")
    print("=" * 60)
    print(f"\nStarting web server on http://localhost:{args.port}")
    print(f"API Documentation: http://localhost:{args.port}/api/docs")
    print("Press Ctrl+C to stop\n")

    uvicorn.run(app, host="0.0.0.0", port=args.port)
