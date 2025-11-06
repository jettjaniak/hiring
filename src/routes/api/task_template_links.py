"""
Task-Template Relationship API routes - Managing links between tasks and email templates
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from ...models import TaskTemplate, EmailTemplate, EmailTemplateTask
from ...dependencies import get_session

router = APIRouter(prefix="/api", tags=["task-template-links"])


@router.get("/task-templates/{task_id}/templates", response_model=List[EmailTemplate])
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


@router.put("/task-templates/{task_id}/templates/{template_id}", status_code=201)
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


@router.delete("/task-templates/{task_id}/templates/{template_id}", status_code=204)
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


@router.get("/templates/{template_id}/tasks", response_model=List[TaskTemplate])
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


@router.put("/templates/{template_id}/tasks/{task_id}", status_code=201)
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


@router.delete("/templates/{template_id}/tasks/{task_id}", status_code=204)
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
