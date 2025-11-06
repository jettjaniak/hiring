#!/usr/bin/env python3
"""
Simple web interface for hiring process client
"""
import sys
from pathlib import Path

# Get project root directory (parent of src/)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Request, Form, HTTPException, Depends
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
import json
import uuid
import argparse
from datetime import datetime, timezone
from jinja2 import Environment, meta, nodes
from src.database import Database
from src.workflow_loader import WorkflowLoader
from src.models import Candidate, EmailTemplate, TaskTemplate, EmailTemplateTask, Checklist, CandidateChecklistState, Task, TaskCandidateLink
from src.constants import TaskStatus
from src.crud_helpers import get_or_404, update_model_fields, commit_and_refresh
from src.routes.api.candidates import router as candidates_router
from src.routes.api.task_templates import router as task_templates_router
from src.routes.api.kanban import router as kanban_router
from src.routes.web import home as home_routes
from src.routes.web import candidates as candidate_routes
from src.routes.web import email_templates as email_template_routes
from src.routes.web import task_templates as task_template_routes
from src.routes.web import checklists as checklist_routes
from src.routes.web import kanban as kanban_web_routes
from src.routes.web import special_actions as special_action_routes
from src import dependencies
from src.utils.email_template import infer_template_variables
from typing import Optional, List
from collections import defaultdict, deque
import uvicorn
import os
import re
from urllib.parse import quote, unquote

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

# Initialize dependency injection system
dependencies.init_database(db)

# Load workflow definitions (from project root)
# Pass database to validate task references
workflow_loader = WorkflowLoader(workflows_dir=str(project_root / "workflows"), db=db)

# Set workflow_loader for web routes that need it
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


# Dependency for database sessions (imported by routes from dependencies module)
from src.dependencies import get_session


# Include API routers
app.include_router(candidates_router)
app.include_router(task_templates_router)
app.include_router(kanban_router)

# Include web UI routers
app.include_router(home_routes.router)
app.include_router(candidate_routes.router)
app.include_router(email_template_routes.router)
app.include_router(task_template_routes.router)
app.include_router(checklist_routes.router)
app.include_router(kanban_web_routes.router)
app.include_router(special_action_routes.router)


# REST API Endpoints - Auto-generated from SQLModel


# ============================================================================
# Spawnable Tasks API Endpoints (Stage 2)
# ============================================================================

# Pydantic request models for spawnable tasks
class SpawnTaskRequest(BaseModel):
    template_id: str
    candidate_emails: List[str]
    title: Optional[str] = None
    description: Optional[str] = None


class CreateTaskRequest(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = TaskStatus.TODO
    workflow_id: Optional[str] = None
    candidate_emails: List[str] = []


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class AddCandidatesRequest(BaseModel):
    candidate_emails: List[str]


@app.post("/api/task-templates/spawn", response_model=Task, status_code=201)
def spawn_task(
    request: SpawnTaskRequest,
    session: Session = Depends(get_session)
):
    """Spawn a task from a template for specific candidates

    If the same template has already been spawned for a candidate, returns the existing task.
    """
    # Validate template exists
    template = session.get(TaskTemplate, request.template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {request.template_id} not found")

    # Validate all candidates exist
    for email in request.candidate_emails:
        candidate = session.get(Candidate, email)
        if not candidate:
            raise HTTPException(status_code=404, detail=f"Candidate {email} not found")

    # Check if this template has already been spawned for any of these candidates
    # Get the first candidate to check workflow_id
    first_candidate = session.get(Candidate, request.candidate_emails[0])
    workflow_id = first_candidate.workflow_id if first_candidate else None

    # Look for existing spawned task with same template_id and any of the candidate_emails
    existing_links = session.exec(
        select(TaskCandidateLink).where(
            TaskCandidateLink.candidate_email.in_(request.candidate_emails)
        )
    ).all()

    if existing_links:
        # Check if any of these links point to a task with the same template_id
        for link in existing_links:
            spawned_task = session.get(Task, link.task_id)
            if spawned_task and spawned_task.template_id == request.template_id:
                # Found existing task with same template for at least one candidate
                # Return it (duplicate prevention)
                return spawned_task

    # Create new spawned task
    title = request.title or template.name
    description = request.description or template.description

    spawned_task = Task(
        title=title,
        description=description,
        status=TaskStatus.TODO,
        template_id=request.template_id,
        workflow_id=workflow_id
    )
    session.add(spawned_task)
    session.commit()
    session.refresh(spawned_task)

    # Create task-candidate links
    for email in request.candidate_emails:
        link = TaskCandidateLink(
            task_id=spawned_task.id,
            candidate_email=email
        )
        session.add(link)
    session.commit()
    session.refresh(spawned_task)  # Refresh after second commit to ensure object is attached

    return spawned_task


@app.get("/api/tasks", response_model=List[Task])
def list_spawned_tasks(
    status: Optional[str] = None,
    workflow_id: Optional[str] = None,
    template_id: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """List all spawned tasks with optional filters"""
    query = select(Task)

    if status:
        query = query.where(Task.status == status)
    if workflow_id:
        query = query.where(Task.workflow_id == workflow_id)
    if template_id:
        query = query.where(Task.template_id == template_id)

    tasks = session.exec(query).all()
    return tasks


@app.get("/api/tasks/{task_id}", response_model=Task)
def get_spawned_task(task_id: int, session: Session = Depends(get_session)):
    """Get a specific spawned task by ID"""
    return get_or_404(session, Task, task_id, "Spawned task")


@app.post("/api/tasks", response_model=Task, status_code=201)
def create_spawned_task(
    request: CreateTaskRequest,
    session: Session = Depends(get_session)
):
    """Create a new ad-hoc spawned task (not from template)"""
    # Validate status
    if request.status not in TaskStatus.all():
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(TaskStatus.all())}")

    # Validate all candidates exist
    for email in request.candidate_emails:
        candidate = session.get(Candidate, email)
        if not candidate:
            raise HTTPException(status_code=404, detail=f"Candidate {email} not found")

    # Create spawned task
    spawned_task = Task(
        title=request.title,
        description=request.description,
        status=request.status,
        workflow_id=request.workflow_id
    )
    session.add(spawned_task)
    session.commit()
    session.refresh(spawned_task)

    # Create task-candidate links
    for email in request.candidate_emails:
        link = TaskCandidateLink(
            task_id=spawned_task.id,
            candidate_email=email
        )
        session.add(link)
    session.commit()
    session.refresh(spawned_task)  # Refresh after second commit to ensure object is attached

    return spawned_task


@app.put("/api/tasks/{task_id}", response_model=Task)
def update_spawned_task(
    task_id: int,
    request: UpdateTaskRequest,
    session: Session = Depends(get_session)
):
    """Update a spawned task"""
    task = get_or_404(session, Task, task_id, "Spawned task")

    # Validate status before updating
    if request.status is not None and request.status not in TaskStatus.all():
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(TaskStatus.all())}")

    update_model_fields(task, {
        'title': request.title,
        'description': request.description,
        'status': request.status
    })
    return commit_and_refresh(session, task)


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_spawned_task(task_id: int, session: Session = Depends(get_session)):
    """Delete a spawned task"""
    task = get_or_404(session, Task, task_id, "Spawned task")
    session.delete(task)
    session.commit()
    return None


@app.get("/api/tasks/{task_id}/candidates", response_model=List[str])
def get_task_candidates(task_id: int, session: Session = Depends(get_session)):
    """Get all candidates associated with a spawned task"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Spawned task {task_id} not found")

    links = session.exec(
        select(TaskCandidateLink).where(TaskCandidateLink.task_id == task_id)
    ).all()

    return [link.candidate_email for link in links]


@app.post("/api/tasks/{task_id}/candidates", status_code=201)
def add_candidates_to_task(
    task_id: int,
    request: AddCandidatesRequest,
    session: Session = Depends(get_session)
):
    """Add candidates to a spawned task"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Spawned task {task_id} not found")

    # Tasks from templates cannot be shared between candidates
    if task.template_id is not None:
        existing_links = session.exec(
            select(TaskCandidateLink).where(TaskCandidateLink.task_id == task_id)
        ).all()
        if existing_links:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot add candidates to template-based task. Task is already assigned to {existing_links[0].candidate_email}. Template-based tasks must be separate for each candidate."
            )

    # Validate all candidates exist
    for email in request.candidate_emails:
        candidate = session.get(Candidate, email)
        if not candidate:
            raise HTTPException(status_code=404, detail=f"Candidate {email} not found")

    # Add new links (skip if already exists)
    added = []
    for email in request.candidate_emails:
        existing = session.exec(
            select(TaskCandidateLink).where(
                TaskCandidateLink.task_id == task_id,
                TaskCandidateLink.candidate_email == email
            )
        ).first()

        if not existing:
            link = TaskCandidateLink(
                task_id=task_id,
                candidate_email=email
            )
            session.add(link)
            added.append(email)

    session.commit()

    return {"message": f"Added {len(added)} candidate(s)", "added": added}


@app.delete("/api/tasks/{task_id}/candidates/{candidate_email}", status_code=204)
def remove_candidate_from_task(
    task_id: int,
    candidate_email: str,
    session: Session = Depends(get_session)
):
    """Remove a candidate from a spawned task"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Spawned task {task_id} not found")

    link = session.exec(
        select(TaskCandidateLink).where(
            TaskCandidateLink.task_id == task_id,
            TaskCandidateLink.candidate_email == candidate_email
        )
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_email} not associated with task {task_id}")

    session.delete(link)
    session.commit()
    return None


# Task-Template Relationship API Endpoints
@app.get("/api/task-templates/{task_id}/templates", response_model=List[EmailTemplate])
def get_task_templates(task_id: str, session: Session = Depends(get_session)):
    """Get all email templates for a task"""
    task = session.get(TaskTemplate, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Get all template IDs linked to this task
    links = session.exec(
        select(EmailTemplateTask).where(EmailTemplateTask.task_template_id == task_id)
    ).all()

    template_ids = [link.email_template_id for link in links]

    # Get the actual templates
    if template_ids:
        templates = session.exec(
            select(EmailTemplate).where(EmailTemplate.id.in_(template_ids))
        ).all()
    else:
        templates = []

    return templates


@app.put("/api/task-templates/{task_id}/templates/{template_id}", status_code=201)
def link_template_to_task(task_id: str, template_id: str, session: Session = Depends(get_session)):
    """Link a template to a task"""
    task = session.get(TaskTemplate, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    template = session.get(EmailTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    # Check if link already exists
    existing_link = session.exec(
        select(EmailTemplateTask).where(
            EmailTemplateTask.task_template_id == task_id,
            EmailTemplateTask.email_template_id == template_id
        )
    ).first()

    if existing_link:
        return {"message": "Link already exists"}

    # Create new link
    link = EmailTemplateTask(
        task_template_id=task_id,
        email_template_id=template_id
    )
    session.add(link)
    session.commit()

    return {"message": "Link created successfully"}


@app.delete("/api/task-templates/{task_id}/templates/{template_id}", status_code=204)
def unlink_template_from_task(task_id: str, template_id: str, session: Session = Depends(get_session)):
    """Unlink a template from a task"""
    link = session.exec(
        select(EmailTemplateTask).where(
            EmailTemplateTask.task_template_id == task_id,
            EmailTemplateTask.email_template_id == template_id
        )
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    session.delete(link)
    session.commit()
    return None


@app.get("/api/templates/{template_id}/tasks", response_model=List[TaskTemplate])
def get_template_tasks(template_id: str, session: Session = Depends(get_session)):
    """Get all tasks for a template"""
    template = session.get(EmailTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    # Get all task IDs linked to this template
    links = session.exec(
        select(EmailTemplateTask).where(EmailTemplateTask.email_template_id == template_id)
    ).all()

    task_ids = [link.task_id for link in links]

    # Get the actual tasks
    if task_ids:
        tasks = session.exec(
            select(TaskTemplate).where(TaskTemplate.task_id.in_(task_ids))
        ).all()
    else:
        tasks = []

    return tasks


@app.put("/api/templates/{template_id}/tasks/{task_id}", status_code=201)
def link_task_to_template(template_id: str, task_id: str, session: Session = Depends(get_session)):
    """Link a task to a template"""
    template = session.get(EmailTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    task = session.get(TaskTemplate, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Check if link already exists
    existing_link = session.exec(
        select(EmailTemplateTask).where(
            EmailTemplateTask.task_template_id == task_id,
            EmailTemplateTask.email_template_id == template_id
        )
    ).first()

    if existing_link:
        return {"message": "Link already exists"}

    # Create new link
    link = EmailTemplateTask(
        task_template_id=task_id,
        email_template_id=template_id
    )
    session.add(link)
    session.commit()

    return {"message": "Link created successfully"}


@app.delete("/api/templates/{template_id}/tasks/{task_id}", status_code=204)
def unlink_task_from_template(template_id: str, task_id: str, session: Session = Depends(get_session)):
    """Unlink a task from a template"""
    link = session.exec(
        select(EmailTemplateTask).where(
            EmailTemplateTask.task_template_id == task_id,
            EmailTemplateTask.email_template_id == template_id
        )
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    session.delete(link)
    session.commit()
    return None




# HTML View Routes (extracted to src/routes/web/)


# Legacy checklist API endpoints (deprecated - kept for backward compatibility)
@app.get("/checklist/{checklist_id}/view")
def view_checklist_legacy(
    checklist_id: str,
    candidate: str,
    task: str,
    request: Request,
    session: Session = Depends(get_session)
):
    """View checklist for a candidate (legacy endpoint)"""
    checklist = session.get(Checklist, checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    candidate_obj = session.get(Candidate, candidate)
    if not candidate_obj:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Parse checklist items
    items = json.loads(checklist.items)

    # Get existing state
    state = session.exec(
        select(CandidateChecklistState).where(
            CandidateChecklistState.candidate_id == candidate,
            CandidateChecklistState.task_identifier == task,
            CandidateChecklistState.checklist_id == checklist_id
        )
    ).first()

    if state:
        items_state = json.loads(state.items_state)
    else:
        items_state = [False] * len(items)

    return templates.TemplateResponse("checklist_view.html", {
        "request": request,
        "checklist": checklist,
        "candidate": candidate_obj,
        "task_identifier": task,
        "items": items,
        "items_state": items_state
    })


# Define model for checklist save request
class ChecklistSaveRequest(BaseModel):
    candidate_id: str
    task_identifier: str
    items_state: List[bool]


@app.post("/api/checklist/{checklist_id}/save")
def save_checklist_api_legacy(
    checklist_id: str,
    request: ChecklistSaveRequest,
    session: Session = Depends(get_session)
):
    """Save checklist state for a candidate (legacy API endpoint)"""
    checklist = session.get(Checklist, checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    # Get or create state
    state = session.exec(
        select(CandidateChecklistState).where(
            CandidateChecklistState.candidate_id == request.candidate_id,
            CandidateChecklistState.task_identifier == request.task_identifier,
            CandidateChecklistState.checklist_id == checklist_id
        )
    ).first()

    if state:
        state.items_state = json.dumps(request.items_state)
        state.last_modified = datetime.now(timezone.utc)
    else:
        state = CandidateChecklistState(
            candidate_id=request.candidate_id,
            task_identifier=request.task_identifier,
            checklist_id=checklist_id,
            items_state=json.dumps(request.items_state)
        )
        session.add(state)

    session.commit()
    return {"success": True}


# Special action routes extracted to src/routes/web/special_actions.py


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
