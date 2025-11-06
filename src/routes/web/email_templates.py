"""
Email Template web UI routes
"""
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from pathlib import Path
from typing import List
import json
import uuid
from datetime import datetime, timezone

from ...models import EmailTemplate, TaskTemplate, EmailTemplateTask, Candidate
from ...dependencies import get_session
from ...utils.email_template import infer_template_variables

# Get project root directory
project_root = Path(__file__).parent.parent.parent.parent
templates = Jinja2Templates(directory=str(project_root / "templates"))

router = APIRouter(tags=["web-email-templates"])


@router.get("/templates", response_class=HTMLResponse)
def email_templates_page(request: Request, session: Session = Depends(get_session)):
    """List all email templates"""
    statement = select(EmailTemplate).order_by(EmailTemplate.name)
    email_templates = session.exec(statement).all()

    return templates.TemplateResponse("email_templates.html", {
        "request": request,
        "templates": email_templates
    })


@router.get("/template/add", response_class=HTMLResponse)
def add_email_template_page(request: Request, session: Session = Depends(get_session)):
    """Show form to add new email template"""
    # Get all tasks for linking
    all_tasks = session.exec(select(TaskTemplate).order_by(TaskTemplate.name)).all()

    return templates.TemplateResponse("email_template_form.html", {
        "request": request,
        "template": None,
        "mode": "add",
        "all_tasks": all_tasks,
        "linked_task_ids": []
    })


@router.post("/template/add")
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
                task_template_id=task_id
            )
            session.add(link)
        session.commit()

    return RedirectResponse(url="/templates", status_code=302)


@router.get("/template/{template_id}/edit", response_class=HTMLResponse)
def edit_email_template_page(template_id: str, request: Request, session: Session = Depends(get_session)):
    """Show form to edit email template"""
    email_template = session.get(EmailTemplate, template_id)
    if not email_template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Get all tasks for linking
    all_tasks = session.exec(select(TaskTemplate).order_by(TaskTemplate.name)).all()

    # Get currently linked tasks
    links = session.exec(
        select(EmailTemplateTask).where(EmailTemplateTask.email_template_id == template_id)
    ).all()
    linked_task_ids = [link.task_template_id for link in links]

    return templates.TemplateResponse("email_template_form.html", {
        "request": request,
        "template": email_template,
        "mode": "edit",
        "all_tasks": all_tasks,
        "linked_task_ids": linked_task_ids
    })


@router.post("/template/{template_id}/edit")
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
                task_template_id=task_id
            )
            session.add(link)
        session.commit()

    return RedirectResponse(url="/templates", status_code=302)


@router.post("/template/{template_id}/delete")
def delete_email_template(template_id: str, session: Session = Depends(get_session)):
    """Delete email template"""
    email_template = session.get(EmailTemplate, template_id)
    if not email_template:
        return RedirectResponse(url="/templates", status_code=302)

    session.delete(email_template)
    session.commit()

    return RedirectResponse(url="/templates", status_code=302)


@router.get("/email/send", response_class=HTMLResponse)
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


@router.get("/email/compose/{template_id}", response_class=HTMLResponse)
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
