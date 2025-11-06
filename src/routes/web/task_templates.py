"""
Task Template web UI routes
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from pathlib import Path
from typing import List
from datetime import datetime, timezone

from ...models import TaskTemplate, EmailTemplate, EmailTemplateTask
from ...dependencies import get_session

# Get project root directory
project_root = Path(__file__).parent.parent.parent.parent
templates = Jinja2Templates(directory=str(project_root / "templates"))

router = APIRouter(tags=["web-task-templates"])


@router.get("/tasks", response_class=HTMLResponse)
def tasks_page(request: Request, session: Session = Depends(get_session)):
    """List all tasks"""
    statement = select(TaskTemplate).order_by(TaskTemplate.name)
    tasks = session.exec(statement).all()

    # Get linked templates for each task
    task_templates = {}
    for task in tasks:
        links = session.exec(
            select(EmailTemplateTask).where(EmailTemplateTask.task_template_id == task.task_id)
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


@router.get("/tasks/add", response_class=HTMLResponse)
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


@router.post("/tasks/add")
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
    existing_task = session.get(TaskTemplate, task_id)
    if existing_task:
        raise HTTPException(status_code=400, detail=f"Task {task_id} already exists")

    task = TaskTemplate(
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
                task_template_id=task_id,
                email_template_id=template_id
            )
            session.add(link)
        session.commit()

    return RedirectResponse(url="/tasks", status_code=302)


@router.get("/tasks/{task_id}/edit", response_class=HTMLResponse)
def edit_task_page(task_id: str, request: Request, session: Session = Depends(get_session)):
    """Show form to edit task"""
    task = session.get(TaskTemplate, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get all email templates for linking
    email_templates = session.exec(select(EmailTemplate).order_by(EmailTemplate.name)).all()

    # Get currently linked templates
    links = session.exec(
        select(EmailTemplateTask).where(EmailTemplateTask.task_template_id == task_id)
    ).all()
    linked_template_ids = [link.email_template_id for link in links]

    return templates.TemplateResponse("task_edit.html", {
        "request": request,
        "task": task,
        "mode": "edit",
        "email_templates": email_templates,
        "linked_template_ids": linked_template_ids
    })


@router.post("/tasks/{task_id}/edit")
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
    task = session.get(TaskTemplate, task_id)
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
        select(EmailTemplateTask).where(EmailTemplateTask.task_template_id == task_id)
    ).all()
    for link in existing_links:
        session.delete(link)
    session.commit()

    # Then add new links
    if template_ids:
        for template_id in template_ids:
            link = EmailTemplateTask(
                task_template_id=task_id,
                email_template_id=template_id
            )
            session.add(link)
        session.commit()

    return RedirectResponse(url="/tasks", status_code=302)


@router.post("/tasks/{task_id}/delete")
def delete_task_form(task_id: str, session: Session = Depends(get_session)):
    """Delete task"""
    task = session.get(TaskTemplate, task_id)
    if not task:
        return RedirectResponse(url="/tasks", status_code=302)

    session.delete(task)
    session.commit()

    return RedirectResponse(url="/tasks", status_code=302)
