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
from src.models import Candidate, CandidateTask, EmailTemplate, Task, EmailTemplateTask, Checklist, CandidateChecklistState
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
args = parser.parse_args()

# Initialize database
data_dir = args.data_dir or os.path.expanduser('~/.hiring-client')
os.makedirs(data_dir, exist_ok=True)
db_file = os.path.join(data_dir, 'hiring.db')

db = Database(db_file)
db.init_db()

# Load workflow definitions (from project root)
# Pass database to validate task references
workflow_loader = WorkflowLoader(workflows_dir=str(project_root / "workflows"), db=db)

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


# Dependency for database sessions
def get_session():
    with db.get_session() as session:
        yield session


def ensure_workflow_tasks(candidate_id: str, workflow_id: str, session: Session):
    """Ensure all workflow tasks exist for candidate"""
    workflow = workflow_loader.get_workflow(workflow_id)
    if not workflow:
        return

    for task_def in workflow.tasks:
        # Check if task exists
        existing = session.exec(
            select(CandidateTask).where(
                CandidateTask.candidate_id == candidate_id,
                CandidateTask.task_identifier == task_def.identifier
            )
        ).first()

        if not existing:
            # Create task with default status
            new_task = CandidateTask(
                candidate_id=candidate_id,
                task_identifier=task_def.identifier,
                status="not_started"
            )
            session.add(new_task)
    session.commit()


# REST API Endpoints - Auto-generated from SQLModel
@app.post("/api/candidates", response_model=Candidate, status_code=201)
def create_candidate(
    workflow_id: str,
    email: str,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    resume_url: Optional[str] = None,
    notes: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Create a new candidate"""
    candidate = Candidate(
        email=email,
        workflow_id=workflow_id,
        name=name,
        phone=phone,
        resume_url=resume_url,
        notes=notes
    )
    session.add(candidate)
    session.commit()
    session.refresh(candidate)

    # Auto-create workflow tasks
    ensure_workflow_tasks(email, workflow_id, session)

    return candidate


@app.get("/api/candidates", response_model=List[Candidate])
def list_candidates(session: Session = Depends(get_session)):
    """List all candidates"""
    candidates = session.exec(select(Candidate)).all()
    return candidates


@app.get("/api/candidates/{candidate_id}", response_model=Candidate)
def get_candidate(candidate_id: str, session: Session = Depends(get_session)):
    """Get a candidate by ID"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")
    return candidate


@app.put("/api/candidates/{candidate_id}", response_model=Candidate)
def update_candidate(
    candidate_id: str,
    workflow_id: Optional[str] = None,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    resume_url: Optional[str] = None,
    notes: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Update a candidate"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")

    if workflow_id is not None:
        candidate.workflow_id = workflow_id
    if name is not None:
        candidate.name = name
    if email is not None:
        candidate.email = email
    if phone is not None:
        candidate.phone = phone
    if resume_url is not None:
        candidate.resume_url = resume_url
    if notes is not None:
        candidate.notes = notes

    candidate.updated_at = datetime.now(timezone.utc)
    session.add(candidate)
    session.commit()
    session.refresh(candidate)
    return candidate


@app.delete("/api/candidates/{candidate_id}", status_code=204)
def delete_candidate(candidate_id: str, session: Session = Depends(get_session)):
    """Delete a candidate"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")

    session.delete(candidate)
    session.commit()
    return None


# Task API Endpoints
@app.get("/api/tasks", response_model=List[Task])
def list_tasks(session: Session = Depends(get_session)):
    """List all tasks"""
    tasks = session.exec(select(Task)).all()
    return tasks


@app.get("/api/tasks/{task_id}", response_model=Task)
def get_task(task_id: str, session: Session = Depends(get_session)):
    """Get a specific task"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.post("/api/tasks", response_model=Task, status_code=201)
def create_task(
    task_id: str,
    name: str,
    description: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Create a new task"""
    # Check if task already exists
    existing_task = session.get(Task, task_id)
    if existing_task:
        raise HTTPException(status_code=400, detail=f"Task {task_id} already exists")

    task = Task(
        task_id=task_id,
        name=name,
        description=description
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@app.put("/api/tasks/{task_id}", response_model=Task)
def update_task(
    task_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Update a task"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if name is not None:
        task.name = name
    if description is not None:
        task.description = description

    task.updated_at = datetime.now(timezone.utc)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: str, session: Session = Depends(get_session)):
    """Delete a task"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    session.delete(task)
    session.commit()
    return None


@app.get("/api/candidates/{candidate_id}/tasks", response_model=List[CandidateTask])
def list_candidate_tasks(candidate_id: str, session: Session = Depends(get_session)):
    """List all tasks for a candidate"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")

    tasks = session.exec(select(CandidateTask).where(CandidateTask.candidate_id == candidate_id)).all()
    return tasks


@app.get("/api/candidates/{candidate_id}/tasks/{task_identifier}", response_model=CandidateTask)
def get_candidate_task(candidate_id: str, task_identifier: str, session: Session = Depends(get_session)):
    """Get a specific task for a candidate"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")

    task = session.exec(
        select(CandidateTask).where(
            CandidateTask.candidate_id == candidate_id,
            CandidateTask.task_identifier == task_identifier
        )
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_identifier} not found for candidate {candidate_id}")

    return task


@app.put("/api/candidates/{candidate_id}/tasks/{task_identifier}", response_model=CandidateTask)
def update_candidate_task(
    candidate_id: str,
    task_identifier: str,
    status: str,
    session: Session = Depends(get_session)
):
    """Update or create a task for a candidate"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")

    if status not in ['not_started', 'in_progress', 'completed', 'na']:
        raise HTTPException(status_code=400, detail="Invalid status. Must be one of: not_started, in_progress, completed, na")

    task = session.exec(
        select(CandidateTask).where(
            CandidateTask.candidate_id == candidate_id,
            CandidateTask.task_identifier == task_identifier
        )
    ).first()

    if not task:
        task = CandidateTask(
            candidate_id=candidate_id,
            task_identifier=task_identifier,
            status=status
        )
        session.add(task)
    else:
        task.status = status
        task.updated_at = datetime.now(timezone.utc)
        session.add(task)

    session.commit()
    session.refresh(task)
    return task


@app.delete("/api/candidates/{candidate_id}/tasks/{task_identifier}", status_code=204)
def delete_candidate_task(candidate_id: str, task_identifier: str, session: Session = Depends(get_session)):
    """Delete a task for a candidate"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")

    task = session.exec(
        select(CandidateTask).where(
            CandidateTask.candidate_id == candidate_id,
            CandidateTask.task_identifier == task_identifier
        )
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_identifier} not found for candidate {candidate_id}")

    session.delete(task)
    session.commit()
    return None


# Task-Template Relationship API Endpoints
@app.get("/api/tasks/{task_id}/templates", response_model=List[EmailTemplate])
def get_task_templates(task_id: str, session: Session = Depends(get_session)):
    """Get all email templates for a task"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Get all template IDs linked to this task
    links = session.exec(
        select(EmailTemplateTask).where(EmailTemplateTask.task_id == task_id)
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


@app.put("/api/tasks/{task_id}/templates/{template_id}", status_code=201)
def link_template_to_task(task_id: str, template_id: str, session: Session = Depends(get_session)):
    """Link a template to a task"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    template = session.get(EmailTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    # Check if link already exists
    existing_link = session.exec(
        select(EmailTemplateTask).where(
            EmailTemplateTask.task_id == task_id,
            EmailTemplateTask.email_template_id == template_id
        )
    ).first()

    if existing_link:
        return {"message": "Link already exists"}

    # Create new link
    link = EmailTemplateTask(
        task_id=task_id,
        email_template_id=template_id
    )
    session.add(link)
    session.commit()

    return {"message": "Link created successfully"}


@app.delete("/api/tasks/{task_id}/templates/{template_id}", status_code=204)
def unlink_template_from_task(task_id: str, template_id: str, session: Session = Depends(get_session)):
    """Unlink a template from a task"""
    link = session.exec(
        select(EmailTemplateTask).where(
            EmailTemplateTask.task_id == task_id,
            EmailTemplateTask.email_template_id == template_id
        )
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    session.delete(link)
    session.commit()
    return None


@app.get("/api/templates/{template_id}/tasks", response_model=List[Task])
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
            select(Task).where(Task.task_id.in_(task_ids))
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

    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Check if link already exists
    existing_link = session.exec(
        select(EmailTemplateTask).where(
            EmailTemplateTask.task_id == task_id,
            EmailTemplateTask.email_template_id == template_id
        )
    ).first()

    if existing_link:
        return {"message": "Link already exists"}

    # Create new link
    link = EmailTemplateTask(
        task_id=task_id,
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
            EmailTemplateTask.task_id == task_id,
            EmailTemplateTask.email_template_id == template_id
        )
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    session.delete(link)
    session.commit()
    return None


# Helper function for DAG layout computation
def compute_dag_layout(workflow):
    """Compute DAG layout with layers based on dependencies"""
    task_deps = {}
    task_by_id = {}
    for task in workflow.tasks:
        task_by_id[task.identifier] = task
        task_deps[task.identifier] = list(task.dependencies)

    in_degree = defaultdict(int)
    for task_id, deps in task_deps.items():
        for dep in deps:
            in_degree[task_id] += 1

    queue = deque()
    layers = {}
    for task_id in task_deps.keys():
        if in_degree[task_id] == 0:
            queue.append(task_id)
            layers[task_id] = 0

    while queue:
        current = queue.popleft()
        current_layer = layers[current]

        for task_id, deps in task_deps.items():
            if current in deps:
                in_degree[task_id] -= 1
                if in_degree[task_id] == 0:
                    max_dep_layer = max(layers[dep] for dep in task_deps[task_id])
                    layers[task_id] = max_dep_layer + 1
                    queue.append(task_id)

    layer_groups = defaultdict(list)
    for task_id, layer in layers.items():
        layer_groups[layer].append(task_id)

    layout = {}
    for layer, task_ids in layer_groups.items():
        for idx, task_id in enumerate(task_ids):
            layout[task_id] = {
                'layer': layer,
                'index': idx,
                'total_in_layer': len(task_ids)
            }

    return layout, max(layers.values()) if layers else 0


# HTML View Routes
@app.get("/", response_class=HTMLResponse)
def index(request: Request, session: Session = Depends(get_session)):
    """List all candidates"""
    candidates = session.exec(select(Candidate)).all()
    return templates.TemplateResponse("index.html", {"request": request, "candidates": candidates})


@app.get("/table", response_class=HTMLResponse)
def table_view(request: Request, session: Session = Depends(get_session)):
    """Table view of all candidates and tasks"""
    candidates = session.exec(select(Candidate)).all()

    task_info = {}
    for candidate in candidates:
        workflow = workflow_loader.get_workflow(candidate.workflow_id)
        if not workflow:
            continue

        layout, _ = compute_dag_layout(workflow)

        for task_def in workflow.tasks:
            if task_def.identifier not in task_info:
                task_info[task_def.identifier] = {
                    'name': task_def.name,
                    'workflows': set(),
                    'min_layer': float('inf')
                }

            task_info[task_def.identifier]['workflows'].add(candidate.workflow_id)
            layer = layout.get(task_def.identifier, {}).get('layer', 0)
            task_info[task_def.identifier]['min_layer'] = min(
                task_info[task_def.identifier]['min_layer'],
                layer
            )

    sorted_tasks = sorted(
        task_info.items(),
        key=lambda x: (x[1]['min_layer'], -len(x[1]['workflows']), x[0])
    )

    candidate_data = []
    for candidate in candidates:
        workflow = workflow_loader.get_workflow(candidate.workflow_id)
        if not workflow:
            continue

        workflow_task_ids = {t.identifier for t in workflow.tasks}
        candidate_tasks = session.exec(
            select(CandidateTask).where(CandidateTask.candidate_id == candidate.email)
        ).all()
        task_status = {ct.task_identifier: ct for ct in candidate_tasks}

        task_states = {}
        for task_identifier, _ in sorted_tasks:
            if task_identifier not in workflow_task_ids:
                task_states[task_identifier] = None
            else:
                ct = task_status.get(task_identifier)
                if ct:
                    task_states[task_identifier] = {
                        'state': ct.status or 'not_started',
                        'exists': True
                    }
                else:
                    task_states[task_identifier] = {
                        'state': 'not_started',
                        'exists': False
                    }

        candidate_data.append({
            'candidate': candidate,
            'task_states': task_states
        })

    return templates.TemplateResponse("table_view.html", {
        "request": request,
        "candidate_data": candidate_data,
        "sorted_tasks": sorted_tasks
    })


@app.get("/candidate/add", response_class=HTMLResponse)
def add_candidate_form(request: Request):
    """Show add candidate form"""
    workflows = workflow_loader.get_all_workflows()
    return templates.TemplateResponse("add.html", {"request": request, "workflows": workflows})


@app.post("/candidate/add")
def add_candidate(
    workflow_id: str = Form(...),
    email: str = Form(...),
    name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    resume_url: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    """Add a new candidate"""
    candidate = Candidate(
        email=email,
        workflow_id=workflow_id,
        name=name,
        phone=phone,
        resume_url=resume_url,
        notes=notes
    )

    session.add(candidate)
    session.commit()

    # Auto-create workflow tasks
    ensure_workflow_tasks(email, workflow_id, session)

    return RedirectResponse(url=f"/candidate/{quote(email)}", status_code=302)


@app.get("/candidate/{candidate_id}/workflow", response_class=HTMLResponse)
def workflow_view(request: Request, candidate_id: str, session: Session = Depends(get_session)):
    """View candidate workflow progress"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        return RedirectResponse(url="/", status_code=302)

    workflow = workflow_loader.get_workflow(candidate.workflow_id)
    if not workflow:
        return RedirectResponse(url="/", status_code=302)

    # Ensure all workflow tasks exist for this candidate
    ensure_workflow_tasks(candidate_id, candidate.workflow_id, session)

    candidate_tasks = session.exec(
        select(CandidateTask).where(CandidateTask.candidate_id == candidate_id)
    ).all()
    task_status = {ct.task_identifier: ct for ct in candidate_tasks}

    # Get all task IDs in this workflow
    task_identifiers = [task.identifier for task in workflow.tasks]

    # Get all email templates linked to these tasks
    template_task_links = session.exec(
        select(EmailTemplateTask).where(EmailTemplateTask.task_id.in_(task_identifiers))
    ).all()

    # Build a map of task_id -> list of template IDs
    task_template_map = {}
    for link in template_task_links:
        if link.task_id not in task_template_map:
            task_template_map[link.task_id] = []
        task_template_map[link.task_id].append(link.email_template_id)

    # Get all email templates that are linked
    all_template_ids = []
    for template_ids in task_template_map.values():
        all_template_ids.extend(template_ids)

    templates_dict = {}
    if all_template_ids:
        email_templates = session.exec(
            select(EmailTemplate).where(EmailTemplate.id.in_(all_template_ids))
        ).all()
        templates_dict = {t.id: t for t in email_templates}

    # Get all checklists linked to these tasks
    checklists = session.exec(
        select(Checklist).where(Checklist.task_id.in_(task_identifiers))
    ).all()
    task_checklist_map = {c.task_id: c for c in checklists}

    # Get all Task database records to access special_action field
    db_tasks = session.exec(
        select(Task).where(Task.task_id.in_(task_identifiers))
    ).all()
    task_db_map = {t.task_id: t for t in db_tasks}

    layout, max_layer = compute_dag_layout(workflow)

    tasks_with_status = []
    for task_def in workflow.tasks:
        ct = task_status.get(task_def.identifier)
        state = ct.status or 'not_started' if ct else 'not_started'

        # Get linked templates for this task
        template_ids = task_template_map.get(task_def.identifier, [])
        linked_templates = [templates_dict[tid] for tid in template_ids if tid in templates_dict]

        # Get linked checklist for this task
        linked_checklist = task_checklist_map.get(task_def.identifier)

        # Get database task record for special_action
        db_task = task_db_map.get(task_def.identifier)
        special_action = db_task.special_action if db_task else None

        task_info = {
            'definition': task_def,
            'candidate_task': ct,
            'state': state,
            'layout': layout.get(task_def.identifier, {'layer': 0, 'index': 0, 'total_in_layer': 1}),
            'email_templates': linked_templates,
            'checklist': linked_checklist,
            'special_action': special_action
        }
        tasks_with_status.append(task_info)

    return templates.TemplateResponse("workflow_view.html", {
        "request": request,
        "candidate": candidate,
        "workflow": workflow,
        "tasks": tasks_with_status,
        "max_layer": max_layer
    })


@app.get("/candidate/{candidate_id}", response_class=HTMLResponse)
def view_candidate(request: Request, candidate_id: str, session: Session = Depends(get_session)):
    """View candidate details"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        return RedirectResponse(url="/", status_code=302)

    tasks = session.exec(
        select(CandidateTask).where(CandidateTask.candidate_id == candidate_id)
    ).all()
    workflow_tasks = workflow_loader.get_tasks_for_workflow(candidate.workflow_id)

    return templates.TemplateResponse("view.html", {
        "request": request,
        "candidate": candidate,
        "tasks": tasks,
        "workflow_tasks": workflow_tasks
    })


@app.get("/candidate/{candidate_id}/edit", response_class=HTMLResponse)
def edit_candidate_form(request: Request, candidate_id: str, session: Session = Depends(get_session)):
    """Show edit candidate form"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        return RedirectResponse(url="/", status_code=302)

    workflows = workflow_loader.get_all_workflows()
    return templates.TemplateResponse("edit.html", {
        "request": request,
        "candidate": candidate,
        "workflows": workflows
    })


@app.post("/candidate/{candidate_id}/edit")
def edit_candidate(
    candidate_id: str,
    workflow_id: str = Form(...),
    name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    resume_url: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    """Edit candidate"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        return RedirectResponse(url="/", status_code=302)

    old_workflow_id = candidate.workflow_id

    candidate.workflow_id = workflow_id
    candidate.name = name
    candidate.email = email
    candidate.phone = phone
    candidate.resume_url = resume_url
    candidate.notes = notes
    candidate.updated_at = datetime.now(timezone.utc)

    session.add(candidate)
    session.commit()

    # Auto-create workflow tasks if workflow changed
    if workflow_id != old_workflow_id:
        ensure_workflow_tasks(candidate.email, workflow_id, session)

    return RedirectResponse(url=f"/candidate/{quote(candidate.email)}", status_code=302)


@app.post("/candidate/{candidate_id}/delete")
def delete_candidate_form(candidate_id: str, session: Session = Depends(get_session)):
    """Delete candidate"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        return RedirectResponse(url="/", status_code=302)

    session.delete(candidate)
    session.commit()

    return RedirectResponse(url="/", status_code=302)


# ============================================================================
# Email Template Helper Functions
# ============================================================================

def infer_template_variables(content: str, subject: str = "", to: str = "", cc: str = "", bcc: str = "") -> List[dict]:
    """
    Infer variables from template content using Jinja2 AST parsing.
    Finds variables in {{ }} and determines their type based on usage.

    Returns list of {"name": str, "type": "text"|"boolean"}
    """
    env = Environment()
    all_text = f"{subject} {to} {cc} {bcc} {content}"

    try:
        ast = env.parse(all_text)
    except Exception:
        # If template parsing fails, return empty list
        return []

    # Find all undeclared variables
    all_vars = meta.find_undeclared_variables(ast)

    # Find variables used in If conditions (these are booleans)
    boolean_vars = set()

    def visit_node(node):
        if isinstance(node, nodes.If):
            # Extract variable names from If test expression
            if isinstance(node.test, nodes.Name):
                boolean_vars.add(node.test.name)
            elif isinstance(node.test, nodes.Not) and isinstance(node.test.node, nodes.Name):
                boolean_vars.add(node.test.node.name)

        # Recursively visit child nodes
        for child in node.iter_child_nodes():
            visit_node(child)

    visit_node(ast)

    # Filter out variables with dots (like candidate.name) - these are provided by candidate object
    simple_vars = {var for var in all_vars if '.' not in var and var != 'candidate'}

    # Build result
    result = []
    for var in sorted(simple_vars):
        var_type = "boolean" if var in boolean_vars else "text"
        result.append({"name": var, "type": var_type})

    return result


# ============================================================================
# Email Template Routes
# ============================================================================

@app.get("/templates")
def email_templates_page(request: Request, session: Session = Depends(get_session)):
    """List all email templates"""
    statement = select(EmailTemplate).order_by(EmailTemplate.name)
    email_templates = session.exec(statement).all()

    return templates.TemplateResponse("email_templates.html", {
        "request": request,
        "templates": email_templates
    })


@app.get("/template/add")
def add_email_template_page(request: Request, session: Session = Depends(get_session)):
    """Show form to add new email template"""
    # Get all tasks for linking
    all_tasks = session.exec(select(Task).order_by(Task.name)).all()

    return templates.TemplateResponse("email_template_form.html", {
        "request": request,
        "template": None,
        "mode": "add",
        "all_tasks": all_tasks,
        "linked_task_ids": []
    })


@app.post("/template/add")
def add_email_template(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    subject: str = Form(""),
    to: str = Form(""),
    cc: str = Form(""),
    bcc: str = Form(""),
    content: str = Form(...),
    variables: str = Form(""),
    task_ids: List[str] = Form([]),
    session: Session = Depends(get_session)
):
    """Create new email template"""
    # Infer variables from template content
    inferred_vars = infer_template_variables(content, subject, to, cc, bcc)
    variables_json = json.dumps(inferred_vars) if inferred_vars else None

    template = EmailTemplate(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        subject=subject,
        to=to,
        cc=cc,
        bcc=bcc,
        content=content,
        variables=variables_json
    )

    session.add(template)
    session.commit()

    # Link to selected tasks
    if task_ids:
        for task_id in task_ids:
            link = EmailTemplateTask(
                email_template_id=template.id,
                task_id=task_id
            )
            session.add(link)
        session.commit()

    return RedirectResponse(url="/templates", status_code=302)


@app.get("/template/{template_id}/edit")
def edit_email_template_page(template_id: str, request: Request, session: Session = Depends(get_session)):
    """Show form to edit email template"""
    email_template = session.get(EmailTemplate, template_id)
    if not email_template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Get all tasks for linking
    all_tasks = session.exec(select(Task).order_by(Task.name)).all()

    # Get currently linked tasks
    links = session.exec(
        select(EmailTemplateTask).where(EmailTemplateTask.email_template_id == template_id)
    ).all()
    linked_task_ids = [link.task_id for link in links]

    return templates.TemplateResponse("email_template_form.html", {
        "request": request,
        "template": email_template,
        "mode": "edit",
        "all_tasks": all_tasks,
        "linked_task_ids": linked_task_ids
    })


@app.post("/template/{template_id}/edit")
def edit_email_template(
    template_id: str,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    subject: str = Form(""),
    to: str = Form(""),
    cc: str = Form(""),
    bcc: str = Form(""),
    content: str = Form(...),
    variables: str = Form(""),
    task_ids: List[str] = Form([]),
    session: Session = Depends(get_session)
):
    """Update email template"""
    email_template = session.get(EmailTemplate, template_id)
    if not email_template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Infer variables from template content
    inferred_vars = infer_template_variables(content, subject, to, cc, bcc)
    variables_json = json.dumps(inferred_vars) if inferred_vars else None

    email_template.name = name
    email_template.description = description
    email_template.subject = subject
    email_template.to = to
    email_template.cc = cc
    email_template.bcc = bcc
    email_template.content = content
    email_template.variables = variables_json
    email_template.updated_at = datetime.now(timezone.utc)

    session.add(email_template)
    session.commit()

    # Update task links
    # First, remove all existing links
    existing_links = session.exec(
        select(EmailTemplateTask).where(EmailTemplateTask.email_template_id == template_id)
    ).all()
    for link in existing_links:
        session.delete(link)
    session.commit()

    # Then add new links
    if task_ids:
        for task_id in task_ids:
            link = EmailTemplateTask(
                email_template_id=template_id,
                task_id=task_id
            )
            session.add(link)
        session.commit()

    return RedirectResponse(url="/templates", status_code=302)


@app.post("/template/{template_id}/delete")
def delete_email_template(template_id: str, session: Session = Depends(get_session)):
    """Delete email template"""
    email_template = session.get(EmailTemplate, template_id)
    if not email_template:
        return RedirectResponse(url="/templates", status_code=302)

    session.delete(email_template)
    session.commit()

    return RedirectResponse(url="/templates", status_code=302)


@app.get("/email/send")
def email_send_page(request: Request, session: Session = Depends(get_session)):
    """Page to select candidate and template for composing email"""
    # Load all candidates and templates
    candidates_statement = select(Candidate).order_by(Candidate.name)
    candidates = session.exec(candidates_statement).all()

    templates_statement = select(EmailTemplate).order_by(EmailTemplate.name)
    email_templates = session.exec(templates_statement).all()

    return templates.TemplateResponse("email_send.html", {
        "request": request,
        "candidates": candidates,
        "email_templates": email_templates
    })


@app.get("/email/compose/{template_id}")
def compose_email(template_id: str, request: Request, session: Session = Depends(get_session)):
    """Compose email using template with dynamic variable substitution"""
    # Load template
    email_template = session.get(EmailTemplate, template_id)
    if not email_template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Parse variables from JSON if available
    variables = []
    if email_template.variables:
        try:
            variables = json.loads(email_template.variables)
        except json.JSONDecodeError:
            variables = []

    # Get all candidates for dropdown
    candidates_statement = select(Candidate).order_by(Candidate.name)
    candidates = session.exec(candidates_statement).all()

    return templates.TemplateResponse("email_compose.html", {
        "request": request,
        "template": email_template,
        "candidates": candidates,
        "variables": variables
    })


# ============================================================================
# Task Routes
# ============================================================================

@app.get("/tasks")
def tasks_page(request: Request, session: Session = Depends(get_session)):
    """List all tasks"""
    statement = select(Task).order_by(Task.name)
    tasks = session.exec(statement).all()

    # Get linked templates for each task
    task_templates = {}
    for task in tasks:
        links = session.exec(
            select(EmailTemplateTask).where(EmailTemplateTask.task_id == task.task_id)
        ).all()
        template_ids = [link.email_template_id for link in links]
        if template_ids:
            templates_list = session.exec(
                select(EmailTemplate).where(EmailTemplate.id.in_(template_ids))
            ).all()
            task_templates[task.task_id] = templates_list
        else:
            task_templates[task.task_id] = []

    return templates.TemplateResponse("tasks.html", {
        "request": request,
        "tasks": tasks,
        "task_templates": task_templates
    })


@app.get("/tasks/add")
def add_task_page(request: Request, session: Session = Depends(get_session)):
    """Show form to add new task"""
    # Get all email templates for linking
    email_templates = session.exec(select(EmailTemplate).order_by(EmailTemplate.name)).all()

    return templates.TemplateResponse("task_edit.html", {
        "request": request,
        "task": None,
        "mode": "add",
        "email_templates": email_templates,
        "linked_template_ids": []
    })


@app.post("/tasks/add")
def add_task(
    request: Request,
    task_id: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    special_action: str = Form(""),
    template_ids: List[str] = Form([]),
    session: Session = Depends(get_session)
):
    """Create new task"""
    # Check if task already exists
    existing_task = session.get(Task, task_id)
    if existing_task:
        raise HTTPException(status_code=400, detail=f"Task {task_id} already exists")

    task = Task(
        task_id=task_id,
        name=name,
        description=description,
        special_action=special_action if special_action else None
    )

    session.add(task)
    session.commit()

    # Link to selected templates
    if template_ids:
        for template_id in template_ids:
            link = EmailTemplateTask(
                task_id=task_id,
                email_template_id=template_id
            )
            session.add(link)
        session.commit()

    return RedirectResponse(url="/tasks", status_code=302)


@app.get("/tasks/{task_id}/edit")
def edit_task_page(task_id: str, request: Request, session: Session = Depends(get_session)):
    """Show form to edit task"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get all email templates for linking
    email_templates = session.exec(select(EmailTemplate).order_by(EmailTemplate.name)).all()

    # Get currently linked templates
    links = session.exec(
        select(EmailTemplateTask).where(EmailTemplateTask.task_id == task_id)
    ).all()
    linked_template_ids = [link.email_template_id for link in links]

    return templates.TemplateResponse("task_edit.html", {
        "request": request,
        "task": task,
        "mode": "edit",
        "email_templates": email_templates,
        "linked_template_ids": linked_template_ids
    })


@app.post("/tasks/{task_id}/edit")
def edit_task(
    task_id: str,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    special_action: str = Form(""),
    template_ids: List[str] = Form([]),
    session: Session = Depends(get_session)
):
    """Update task"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.name = name
    task.description = description
    task.special_action = special_action if special_action else None
    task.updated_at = datetime.now(timezone.utc)

    session.add(task)
    session.commit()

    # Update template links
    # First, remove all existing links
    existing_links = session.exec(
        select(EmailTemplateTask).where(EmailTemplateTask.task_id == task_id)
    ).all()
    for link in existing_links:
        session.delete(link)
    session.commit()

    # Then add new links
    if template_ids:
        for template_id in template_ids:
            link = EmailTemplateTask(
                task_id=task_id,
                email_template_id=template_id
            )
            session.add(link)
        session.commit()

    return RedirectResponse(url="/tasks", status_code=302)


@app.post("/tasks/{task_id}/delete")
def delete_task_form(task_id: str, session: Session = Depends(get_session)):
    """Delete task"""
    task = session.get(Task, task_id)
    if not task:
        return RedirectResponse(url="/tasks", status_code=302)

    session.delete(task)
    session.commit()

    return RedirectResponse(url="/tasks", status_code=302)


# Checklist Web UI Endpoints
@app.get("/checklists")
def checklists_page(request: Request, session: Session = Depends(get_session)):
    """List all checklists"""
    statement = select(Checklist).order_by(Checklist.name)
    checklists = session.exec(statement).all()

    # Get task info for each checklist
    checklist_tasks = {}
    for checklist in checklists:
        task = session.get(Task, checklist.task_id)
        checklist_tasks[checklist.id] = task

    return templates.TemplateResponse("checklists.html", {
        "request": request,
        "checklists": checklists,
        "checklist_tasks": checklist_tasks
    })


@app.get("/checklists/add")
def add_checklist_page(request: Request, session: Session = Depends(get_session)):
    """Show form to add new checklist"""
    # Get all tasks
    tasks = session.exec(select(Task).order_by(Task.name)).all()

    # Get tasks that already have checklists
    existing_checklists = session.exec(select(Checklist)).all()
    used_task_ids = {c.task_id for c in existing_checklists}

    # Filter to only show tasks without checklists
    available_tasks = [t for t in tasks if t.task_id not in used_task_ids]

    return templates.TemplateResponse("checklist_edit.html", {
        "request": request,
        "checklist": None,
        "mode": "add",
        "available_tasks": available_tasks
    })


@app.post("/checklists/add")
def add_checklist(
    request: Request,
    checklist_id: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    task_id: str = Form(...),
    items: str = Form(...),
    session: Session = Depends(get_session)
):
    """Create new checklist"""
    # Check if checklist already exists
    existing_checklist = session.get(Checklist, checklist_id)
    if existing_checklist:
        raise HTTPException(status_code=400, detail=f"Checklist {checklist_id} already exists")

    # Check if task exists
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Check if task already has a checklist
    existing_for_task = session.exec(
        select(Checklist).where(Checklist.task_id == task_id)
    ).first()
    if existing_for_task:
        raise HTTPException(status_code=400, detail=f"Task {task_id} already has a checklist")

    # Parse items (newline separated) and convert to JSON string
    import json
    items_list = [item.strip() for item in items.split('\n') if item.strip()]
    items_json = json.dumps(items_list)

    checklist = Checklist(
        id=checklist_id,
        name=name,
        description=description,
        task_id=task_id,
        items=items_json
    )

    session.add(checklist)
    session.commit()

    return RedirectResponse(url="/checklists", status_code=302)


@app.get("/checklists/{checklist_id}/edit")
def edit_checklist_page(checklist_id: str, request: Request, session: Session = Depends(get_session)):
    """Show form to edit checklist"""
    checklist = session.get(Checklist, checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    # Get the task
    task = session.get(Task, checklist.task_id)

    # Parse items JSON to display as text
    import json
    items_list = json.loads(checklist.items)
    items_text = '\n'.join(items_list)

    return templates.TemplateResponse("checklist_edit.html", {
        "request": request,
        "checklist": checklist,
        "mode": "edit",
        "available_tasks": [task] if task else [],
        "items_text": items_text
    })


@app.post("/checklists/{checklist_id}/edit")
def edit_checklist(
    checklist_id: str,
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    items: str = Form(...),
    session: Session = Depends(get_session)
):
    """Update checklist"""
    checklist = session.get(Checklist, checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    # Parse items (newline separated) and convert to JSON string
    import json
    items_list = [item.strip() for item in items.split('\n') if item.strip()]
    items_json = json.dumps(items_list)

    checklist.name = name
    checklist.description = description
    checklist.items = items_json
    checklist.updated_at = datetime.now(timezone.utc)

    session.add(checklist)
    session.commit()

    return RedirectResponse(url="/checklists", status_code=302)


@app.post("/checklists/{checklist_id}/delete")
def delete_checklist_form(checklist_id: str, session: Session = Depends(get_session)):
    """Delete checklist"""
    checklist = session.get(Checklist, checklist_id)
    if not checklist:
        return RedirectResponse(url="/checklists", status_code=302)

    session.delete(checklist)
    session.commit()

    return RedirectResponse(url="/checklists", status_code=302)


# Checklist View and Save Endpoints
@app.get("/checklist/{checklist_id}/view")
def view_checklist(
    checklist_id: str,
    candidate: str,
    task: str,
    request: Request,
    session: Session = Depends(get_session)
):
    """View checklist for a candidate"""
    import json

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


@app.post("/checklist/{checklist_id}/save")
def save_checklist(
    checklist_id: str,
    candidate: str = Form(...),
    task: str = Form(...),
    session: Session = Depends(get_session)
):
    """Save checklist state for a candidate"""
    import json
    from fastapi import Form as FormParam
    from starlette.requests import Request as StarletteRequest

    # Get form data
    async def get_form_data(request: StarletteRequest):
        form = await request.form()
        return form

    checklist = session.get(Checklist, checklist_id)
    if not checklist:
        raise HTTPException(status_code=404, detail="Checklist not found")

    items = json.loads(checklist.items)

    # Build items_state from form data
    # The form will have checkboxes named "item_0", "item_1", etc.
    items_state = []
    from starlette.requests import Request as StarletteRequest

    # We need to get the request to access form data
    # This is a workaround - we'll accept items_state as a JSON string
    return RedirectResponse(url=f"/checklist/{checklist_id}/view?candidate={candidate}&task={task}", status_code=302)


# Better approach: use JSON endpoint
class ChecklistSaveRequest(BaseModel):
    candidate_id: str
    task_identifier: str
    items_state: List[bool]


@app.post("/api/checklist/{checklist_id}/save")
def save_checklist_api(
    checklist_id: str,
    request: ChecklistSaveRequest,
    session: Session = Depends(get_session)
):
    """Save checklist state for a candidate (API)"""
    import json

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


# ============================================================================
# Special Actions - Document Generation
# ============================================================================

@app.get("/action/fill_offer_letter")
def fill_offer_letter_form(
    request: Request,
    candidate: str,
    task: str,
    session: Session = Depends(get_session)
):
    """Form to fill offer letter for a candidate"""
    from src.document_generator import extract_placeholders_from_docx

    # Get candidate
    cand = session.get(Candidate, candidate)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Extract required fields from template
    try:
        placeholders = extract_placeholders_from_docx("offer_letter_template.docx")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Template file not found")

    # Pre-fill some fields from candidate data
    prefilled = {
        "CANDIDATE_NAME": cand.name or "",
        "CANDIDATE_EMAIL": cand.email or "",
    }

    return templates.TemplateResponse("action_offer_letter.html", {
        "request": request,
        "candidate": cand,
        "task_id": task,
        "placeholders": placeholders,
        "prefilled": prefilled
    })


@app.post("/action/fill_offer_letter")
async def generate_offer_letter(
    request: Request,
    candidate: str = Form(...),
    task: str = Form(...),
    session: Session = Depends(get_session)
):
    """Generate and download filled offer letter"""
    from src.document_generator import fill_docx_template
    from fastapi.responses import StreamingResponse

    # Get candidate
    cand = session.get(Candidate, candidate)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Get all form fields
    form_data = await request.form()

    # Build replacements dictionary
    replacements = {}
    for key, value in form_data.items():
        if key not in ["candidate", "task"] and value:
            replacements[f"{{{{{key}}}}}"] = value

    # Generate document
    try:
        doc_bytes = fill_docx_template("offer_letter_template.docx", replacements)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {str(e)}")

    # Return as downloadable file
    filename = f"offer_letter_{cand.name.replace(' ', '_') if cand.name else cand.email}.docx"
    return StreamingResponse(
        doc_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/action/fill_background_check")
def fill_background_check_form(
    request: Request,
    candidate: str,
    task: str,
    session: Session = Depends(get_session)
):
    """Form to fill background check for a candidate"""
    from src.document_generator import extract_placeholders_from_xlsx

    # Get candidate
    cand = session.get(Candidate, candidate)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Extract required fields from template
    try:
        placeholders = extract_placeholders_from_xlsx("background_check_template.xlsx")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Template file not found")

    # Pre-fill some fields from candidate data
    prefilled = {
        "CANDIDATE_NAME": cand.name or "",
        "CANDIDATE_EMAIL": cand.email or "",
        "CANDIDATE_PHONE": cand.phone or "",
    }

    return templates.TemplateResponse("action_background_check.html", {
        "request": request,
        "candidate": cand,
        "task_id": task,
        "placeholders": placeholders,
        "prefilled": prefilled
    })


@app.post("/action/fill_background_check")
async def generate_background_check(
    request: Request,
    candidate: str = Form(...),
    task: str = Form(...),
    session: Session = Depends(get_session)
):
    """Generate and download filled background check"""
    from src.document_generator import fill_xlsx_template
    from fastapi.responses import StreamingResponse

    # Get candidate
    cand = session.get(Candidate, candidate)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Get all form fields
    form_data = await request.form()

    # Build replacements dictionary
    replacements = {}
    for key, value in form_data.items():
        if key not in ["candidate", "task"] and value:
            replacements[f"{{{{{key}}}}}"] = value

    # Generate document
    try:
        doc_bytes = fill_xlsx_template("background_check_template.xlsx", replacements)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {str(e)}")

    # Return as downloadable file
    filename = f"background_check_{cand.name.replace(' ', '_') if cand.name else cand.email}.xlsx"
    return StreamingResponse(
        doc_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


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
