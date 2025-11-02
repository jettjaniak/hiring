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
from src.models import Candidate, CandidateTask, ActionState, EmailTemplate
from typing import Optional, List
from collections import defaultdict, deque
import uvicorn
import os
import re

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
workflow_loader = WorkflowLoader(workflows_dir=str(project_root / "workflows"))

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


# REST API Endpoints - Auto-generated from SQLModel
@app.post("/api/candidates", response_model=Candidate, status_code=201)
def create_candidate(
    workflow_id: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    resume_url: Optional[str] = None,
    notes: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Create a new candidate"""
    candidate = Candidate(
        id=f"candidate-{uuid.uuid4().hex[:12]}",
        workflow_id=workflow_id,
        name=name,
        email=email,
        phone=phone,
        resume_url=resume_url,
        notes=notes
    )
    session.add(candidate)
    session.commit()
    session.refresh(candidate)
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


@app.get("/api/action-states", response_model=List[ActionState])
def list_action_states(session: Session = Depends(get_session)):
    """List all action states"""
    action_states = session.exec(select(ActionState)).all()
    return action_states


@app.get("/api/action-states/{candidate_id}/{action_id}", response_model=ActionState)
def get_action_state(candidate_id: str, action_id: str, session: Session = Depends(get_session)):
    """Get an action state"""
    action_state = session.exec(
        select(ActionState).where(
            ActionState.candidate_id == candidate_id,
            ActionState.action_id == action_id
        )
    ).first()

    if not action_state:
        raise HTTPException(status_code=404, detail="Action state not found")

    return action_state


@app.put("/api/action-states/{candidate_id}/{action_id}", response_model=ActionState)
def update_action_state(
    candidate_id: str,
    action_id: str,
    state: dict,
    session: Session = Depends(get_session)
):
    """Update or create an action state"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")

    action_state = session.exec(
        select(ActionState).where(
            ActionState.candidate_id == candidate_id,
            ActionState.action_id == action_id
        )
    ).first()

    if not action_state:
        action_state = ActionState(
            candidate_id=candidate_id,
            action_id=action_id,
            state=state
        )
        session.add(action_state)
    else:
        action_state.state = state
        action_state.updated_at = datetime.now(timezone.utc)
        session.add(action_state)

    session.commit()
    session.refresh(action_state)
    return action_state


@app.delete("/api/action-states/{candidate_id}/{action_id}", status_code=204)
def delete_action_state(candidate_id: str, action_id: str, session: Session = Depends(get_session)):
    """Delete an action state"""
    action_state = session.exec(
        select(ActionState).where(
            ActionState.candidate_id == candidate_id,
            ActionState.action_id == action_id
        )
    ).first()

    if not action_state:
        raise HTTPException(status_code=404, detail="Action state not found")

    session.delete(action_state)
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
            select(CandidateTask).where(CandidateTask.candidate_id == candidate.id)
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
    name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    resume_url: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    """Add a new candidate"""
    candidate_id = f"candidate-{uuid.uuid4().hex[:12]}"
    candidate = Candidate(
        id=candidate_id,
        workflow_id=workflow_id,
        name=name,
        email=email,
        phone=phone,
        resume_url=resume_url,
        notes=notes
    )

    session.add(candidate)
    session.commit()

    return RedirectResponse(url=f"/candidate/{candidate_id}", status_code=302)


@app.get("/candidate/{candidate_id}/workflow", response_class=HTMLResponse)
def workflow_view(request: Request, candidate_id: str, session: Session = Depends(get_session)):
    """View candidate workflow progress"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        return RedirectResponse(url="/", status_code=302)

    workflow = workflow_loader.get_workflow(candidate.workflow_id)
    if not workflow:
        return RedirectResponse(url="/", status_code=302)

    candidate_tasks = session.exec(
        select(CandidateTask).where(CandidateTask.candidate_id == candidate_id)
    ).all()
    task_status = {ct.task_identifier: ct for ct in candidate_tasks}

    layout, max_layer = compute_dag_layout(workflow)

    tasks_with_status = []
    for task_def in workflow.tasks:
        ct = task_status.get(task_def.identifier)
        state = ct.status or 'not_started' if ct else 'not_started'

        task_info = {
            'definition': task_def,
            'candidate_task': ct,
            'state': state,
            'layout': layout.get(task_def.identifier, {'layer': 0, 'index': 0, 'total_in_layer': 1})
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

    candidate.workflow_id = workflow_id
    candidate.name = name
    candidate.email = email
    candidate.phone = phone
    candidate.resume_url = resume_url
    candidate.notes = notes
    candidate.updated_at = datetime.now(timezone.utc)

    session.add(candidate)
    session.commit()

    return RedirectResponse(url=f"/candidate/{candidate_id}", status_code=302)


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
def add_email_template_page(request: Request):
    """Show form to add new email template"""
    return templates.TemplateResponse("email_template_form.html", {
        "request": request,
        "template": None,
        "mode": "add"
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

    return RedirectResponse(url="/templates", status_code=302)


@app.get("/template/{template_id}/edit")
def edit_email_template_page(template_id: str, request: Request, session: Session = Depends(get_session)):
    """Show form to edit email template"""
    email_template = session.get(EmailTemplate, template_id)
    if not email_template:
        raise HTTPException(status_code=404, detail="Template not found")

    return templates.TemplateResponse("email_template_form.html", {
        "request": request,
        "template": email_template,
        "mode": "edit"
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
