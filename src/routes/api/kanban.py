"""
Kanban API routes
"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from ...models import Task, TaskCandidateLink, Candidate, TaskStatus
from ...dependencies import get_session

router = APIRouter(prefix="/api/tasks/kanban", tags=["kanban"])


@router.get("")
def get_kanban_data(session: Session = Depends(get_session)):
    """Get tasks grouped by status for kanban view"""
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

        # Get candidate names
        candidates = []
        for email in candidate_emails:
            candidate = session.get(Candidate, email)
            if candidate:
                candidates.append({
                    "email": candidate.email,
                    "name": candidate.name or candidate.email
                })

        task_data = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "template_id": task.template_id,
            "workflow_id": task.workflow_id,
            "candidates": candidates,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None
        }

        kanban_data[task.status].append(task_data)

    return kanban_data
