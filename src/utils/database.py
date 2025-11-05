"""
Database utility functions to reduce code duplication
"""
from typing import List, Type, TypeVar, Optional
from fastapi import HTTPException
from sqlmodel import Session, select
from ..models import Task, TaskCandidateLink, EmailTemplate, EmailTemplateTask

T = TypeVar('T')


def get_or_404(session: Session, model: Type[T], id: any, entity_name: str = "Entity") -> T:
    """
    Get entity by ID or raise 404 HTTPException.

    Eliminates the pattern:
        entity = session.get(Model, id)
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

    Args:
        session: Database session
        model: SQLModel class
        id: Primary key value
        entity_name: Name to use in error message

    Returns:
        The entity instance

    Raises:
        HTTPException: 404 if entity not found
    """
    entity = session.get(model, id)
    if not entity:
        raise HTTPException(status_code=404, detail=f"{entity_name} not found")
    return entity


def save_and_refresh(session: Session, entity: T) -> T:
    """
    Save entity to database and refresh to get updated values.

    Eliminates the pattern:
        session.add(entity)
        session.commit()
        session.refresh(entity)

    Args:
        session: Database session
        entity: Entity to save

    Returns:
        The refreshed entity
    """
    session.add(entity)
    session.commit()
    session.refresh(entity)
    return entity


def get_candidate_tasks(session: Session, candidate_email: str) -> List[Task]:
    """
    Get all tasks for a candidate via TaskCandidateLink.

    Args:
        session: Database session
        candidate_email: Candidate's email address

    Returns:
        List of Task instances
    """
    links = session.exec(
        select(TaskCandidateLink).where(TaskCandidateLink.candidate_email == candidate_email)
    ).all()

    tasks = []
    for link in links:
        task = session.get(Task, link.task_id)
        if task:
            tasks.append(task)

    return tasks


def get_task_email_templates(session: Session, task_id: int) -> List[EmailTemplate]:
    """
    Get all email templates linked to a task.

    Args:
        session: Database session
        task_id: Task ID (spawned task, not template)

    Returns:
        List of EmailTemplate instances
    """
    links = session.exec(
        select(EmailTemplateTask).where(EmailTemplateTask.task_id == task_id)
    ).all()

    templates = []
    for link in links:
        template = session.get(EmailTemplate, link.template_id)
        if template:
            templates.append(template)

    return templates


def get_template_tasks(session: Session, template_id: int) -> List[Task]:
    """
    Get all tasks linked to an email template.

    Args:
        session: Database session
        template_id: EmailTemplate ID

    Returns:
        List of Task instances
    """
    links = session.exec(
        select(EmailTemplateTask).where(EmailTemplateTask.template_id == template_id)
    ).all()

    tasks = []
    for link in links:
        task = session.get(Task, link.task_id)
        if task:
            tasks.append(task)

    return tasks


def link_task_to_templates(session: Session, task_id: int, template_ids: List[int]) -> None:
    """
    Link a task to multiple email templates.

    Creates EmailTemplateTask records for each template.
    Skips if link already exists.

    Args:
        session: Database session
        task_id: Task ID
        template_ids: List of EmailTemplate IDs
    """
    for template_id in template_ids:
        # Check if link already exists
        existing = session.exec(
            select(EmailTemplateTask).where(
                EmailTemplateTask.task_id == task_id,
                EmailTemplateTask.template_id == template_id
            )
        ).first()

        if not existing:
            link = EmailTemplateTask(task_id=task_id, template_id=template_id)
            session.add(link)

    session.commit()


def unlink_task_from_all_templates(session: Session, task_id: int) -> int:
    """
    Remove all email template links for a task.

    Args:
        session: Database session
        task_id: Task ID

    Returns:
        Number of links deleted
    """
    links = session.exec(
        select(EmailTemplateTask).where(EmailTemplateTask.task_id == task_id)
    ).all()

    count = len(links)
    for link in links:
        session.delete(link)

    session.commit()
    return count
