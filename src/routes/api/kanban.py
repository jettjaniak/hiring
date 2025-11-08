"""
Kanban API routes
"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import Optional
from ...models import Task, TaskCandidateLink, Candidate, User, TaskStatus
from ...dependencies import get_session

router = APIRouter(prefix="/api/tasks/kanban", tags=["kanban"])


@router.get("")
def get_kanban_data(
    candidate_email: Optional[str] = None,
    assigned_to: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """
    Get tasks grouped by status for kanban view

    Args:
        candidate_email: Optional email to filter tasks by candidate.
                        Use "unassigned" to show tasks with no candidates.
                        Omit to show all tasks.
        assigned_to: Optional username to filter tasks by assigned user.
                    Use "unassigned" to show tasks with no assigned user.
    """
    # Get all tasks
    tasks = session.exec(select(Task)).all()

    # Group tasks by status
    kanban_data = {
        TaskStatus.TODO: [],
        TaskStatus.IN_PROGRESS: [],
        TaskStatus.DONE: []
    }

    for task in tasks:
        # Get associated candidates for this task
        links = session.exec(
            select(TaskCandidateLink).where(TaskCandidateLink.task_id == task.id)
        ).all()
        candidate_emails = [link.candidate_email for link in links]

        # Apply filtering based on candidate_email parameter
        if candidate_email is not None:
            if candidate_email == "unassigned":
                # Show only tasks with no candidates
                if len(candidate_emails) > 0:
                    continue
            else:
                # Show only tasks for specific candidate
                if candidate_email not in candidate_emails:
                    continue

        # Apply filtering based on assigned_to parameter
        if assigned_to is not None:
            if assigned_to == "unassigned":
                # Show only tasks with no assigned user
                if task.assigned_to is not None:
                    continue
            else:
                # Show only tasks assigned to specific user
                if task.assigned_to != assigned_to:
                    continue

        # Get candidate names
        candidates = []
        for email in candidate_emails:
            candidate = session.get(Candidate, email)
            if candidate:
                candidates.append({
                    "email": candidate.email,
                    "name": candidate.name or candidate.email
                })

        # Get assigned user info
        assigned_user = None
        if task.assigned_to:
            user = session.get(User, task.assigned_to)
            if user:
                assigned_user = {
                    "username": user.username,
                    "full_name": user.full_name or user.username
                }

        task_data = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "template_id": task.template_id,
            "workflow_id": task.workflow_id,
            "candidates": candidates,
            "assigned_user": assigned_user,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None
        }

        kanban_data[task.status].append(task_data)

    return kanban_data
