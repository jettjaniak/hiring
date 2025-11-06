"""
Candidate web UI routes
"""
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from urllib.parse import quote

from ...models import (
    Candidate, Task, TaskCandidateLink, EmailTemplate, EmailTemplateTask,
    Checklist, TaskTemplate
)
from ...dependencies import get_session
from ...constants import TaskStatus
from ...utils.workflow import compute_dag_layout

# Get project root directory
project_root = Path(__file__).parent.parent.parent.parent
templates = Jinja2Templates(directory=str(project_root / "templates"))

router = APIRouter(tags=["web-candidates"])

# Workflow loader reference - will be set by app.py
workflow_loader = None


@router.get("/candidate/add", response_class=HTMLResponse)
def add_candidate_form(request: Request):
    """Show add candidate form"""
    workflows = workflow_loader.get_all_workflows()
    return templates.TemplateResponse("add.html", {"request": request, "workflows": workflows})


@router.post("/candidate/add")
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

    return RedirectResponse(url=f"/candidate/{quote(email)}", status_code=302)


@router.get("/candidate/{candidate_id}/workflow", response_class=HTMLResponse)
def workflow_view(request: Request, candidate_id: str, session: Session = Depends(get_session)):
    """View candidate workflow progress"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        return RedirectResponse(url="/", status_code=302)

    workflow = workflow_loader.get_workflow(candidate.workflow_id)
    if not workflow:
        return RedirectResponse(url="/", status_code=302)

    # Get all task IDs in this workflow
    task_identifiers = [task.identifier for task in workflow.tasks]

    # Query Tasks for this candidate that match workflow task identifiers
    # Get all tasks linked to this candidate
    task_links = session.exec(
        select(TaskCandidateLink).where(TaskCandidateLink.candidate_email == candidate.email)
    ).all()
    task_ids = [link.task_id for link in task_links]

    # Get all Tasks with these IDs
    candidate_tasks = []
    if task_ids:
        candidate_tasks = session.exec(
            select(Task).where(Task.id.in_(task_ids))
        ).all()

    # Build map of template_id -> Task for quick lookup
    # Filter only tasks that have template_ids matching workflow task identifiers
    task_status = {}
    for task in candidate_tasks:
        if task.template_id and task.template_id in task_identifiers:
            task_status[task.template_id] = task

    # Get all email templates linked to these tasks
    template_task_links = session.exec(
        select(EmailTemplateTask).where(EmailTemplateTask.task_template_id.in_(task_identifiers))
    ).all()

    # Build a map of task_id -> list of template IDs
    task_template_map = {}
    for link in template_task_links:
        if link.task_template_id not in task_template_map:
            task_template_map[link.task_template_id] = []
        task_template_map[link.task_template_id].append(link.email_template_id)

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
        select(Checklist).where(Checklist.task_template_id.in_(task_identifiers))
    ).all()
    task_checklist_map = {c.task_template_id: c for c in checklists}

    # Get all TaskTemplate database records to access special_action field
    db_tasks = session.exec(
        select(TaskTemplate).where(TaskTemplate.task_id.in_(task_identifiers))
    ).all()
    task_db_map = {t.task_id: t for t in db_tasks}

    layout, max_layer = compute_dag_layout(workflow)

    tasks_with_status = []
    for task_def in workflow.tasks:
        ct = task_status.get(task_def.identifier)
        state = ct.status or TaskStatus.TODO if ct else TaskStatus.TODO

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
            'exists': ct is not None,  # Track whether task instance exists
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


@router.get("/candidate/{candidate_id}", response_class=HTMLResponse)
def view_candidate(request: Request, candidate_id: str, session: Session = Depends(get_session)):
    """View candidate details"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        return RedirectResponse(url="/", status_code=302)

    # Get actual Task instances for this candidate
    task_links = session.exec(
        select(TaskCandidateLink).where(TaskCandidateLink.candidate_email == candidate.email)
    ).all()
    task_ids = [link.task_id for link in task_links]

    tasks = []
    if task_ids:
        tasks = session.exec(
            select(Task).where(Task.id.in_(task_ids))
        ).all()

    workflow_tasks = workflow_loader.get_tasks_for_workflow(candidate.workflow_id)

    return templates.TemplateResponse("view.html", {
        "request": request,
        "candidate": candidate,
        "tasks": tasks,
        "workflow_tasks": workflow_tasks
    })


@router.get("/candidate/{candidate_id}/edit", response_class=HTMLResponse)
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


@router.post("/candidate/{candidate_id}/edit")
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

    return RedirectResponse(url=f"/candidate/{quote(candidate.email)}", status_code=302)


@router.post("/candidate/{candidate_id}/delete")
def delete_candidate_form(candidate_id: str, session: Session = Depends(get_session)):
    """Delete candidate"""
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        return RedirectResponse(url="/", status_code=302)

    session.delete(candidate)
    session.commit()

    return RedirectResponse(url="/", status_code=302)
