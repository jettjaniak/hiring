"""
Home and dashboard web UI routes
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from pathlib import Path
from ...models import Candidate, Task, TaskCandidateLink
from ...dependencies import get_session
from ...constants import TaskStatus
from ...utils.workflow import compute_dag_layout

# Get project root directory (grandparent of grandparent of this file)
project_root = Path(__file__).parent.parent.parent.parent
templates = Jinja2Templates(directory=str(project_root / "templates"))

router = APIRouter(tags=["web-home"])

# Get workflow_loader from main app module - will be set by app.py
workflow_loader = None


@router.get("/", response_class=HTMLResponse)
def index(request: Request, session: Session = Depends(get_session)):
    """List all candidates"""
    candidates = session.exec(select(Candidate)).all()
    return templates.TemplateResponse("index.html", {"request": request, "candidates": candidates})


@router.get("/table", response_class=HTMLResponse)
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

        # Get actual Task instances for this candidate
        task_links = session.exec(
            select(TaskCandidateLink).where(TaskCandidateLink.candidate_email == candidate.email)
        ).all()
        task_ids = [link.task_id for link in task_links]

        candidate_tasks = []
        if task_ids:
            candidate_tasks = session.exec(
                select(Task).where(Task.id.in_(task_ids))
            ).all()

        # Build status map by template_id (ONLY for tasks that exist)
        task_status = {}
        for task in candidate_tasks:
            if task.template_id and task.template_id in workflow_task_ids:
                task_status[task.template_id] = task

        # Build task_states for this candidate
        task_states = {}
        for task_identifier, _ in sorted_tasks:
            if task_identifier not in workflow_task_ids:
                # Task not in this candidate's workflow
                task_states[task_identifier] = None
            else:
                # Task is in this candidate's workflow
                ct = task_status.get(task_identifier)
                if ct:  # Task exists
                    task_states[task_identifier] = {
                        'state': ct.status or TaskStatus.TODO,
                        'exists': True,
                        'task_id': ct.id
                    }
                else:  # Task doesn't exist yet but is in workflow
                    task_states[task_identifier] = {
                        'state': TaskStatus.TODO,
                        'exists': False,
                        'task_id': None
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
