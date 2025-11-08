"""
Candidate API routes
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ...models import Candidate, Task, TaskCandidateLink, TaskTemplate, TaskStatus
from ...crud_helpers import get_or_404, update_model_fields, commit_and_refresh
from ...dependencies import get_session

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


def ensure_workflow_tasks(candidate_id: str, workflow_id: str, session: Session):
    """Ensure all workflow tasks exist for candidate"""
    # PHASE 6 TODO: Remove auto-creation - users will create tasks manually
    pass


@router.post("", response_model=Candidate, status_code=201)
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


@router.get("", response_model=List[Candidate])
def list_candidates(session: Session = Depends(get_session)):
    """List all candidates"""
    candidates = session.exec(select(Candidate)).all()
    return candidates


@router.get("/{candidate_id}", response_model=Candidate)
def get_candidate(candidate_id: str, session: Session = Depends(get_session)):
    """Get a candidate by ID"""
    return get_or_404(session, Candidate, candidate_id, "Candidate")


@router.put("/{candidate_id}", response_model=Candidate)
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
    candidate = get_or_404(session, Candidate, candidate_id, "Candidate")
    update_model_fields(candidate, {
        'workflow_id': workflow_id,
        'name': name,
        'email': email,
        'phone': phone,
        'resume_url': resume_url,
        'notes': notes
    })
    return commit_and_refresh(session, candidate)


@router.delete("/{candidate_id}", status_code=204)
def delete_candidate(candidate_id: str, session: Session = Depends(get_session)):
    """Delete a candidate"""
    candidate = get_or_404(session, Candidate, candidate_id, "Candidate")
    session.delete(candidate)
    session.commit()
    return None


# ============================================================================
# Candidate Task Endpoints
# ============================================================================

@router.get("/{candidate_email}/tasks")
def list_candidate_tasks(
    candidate_email: str,
    session: Session = Depends(get_session)
):
    """List all Task instances for a specific candidate"""
    # Verify candidate exists
    candidate = session.exec(
        select(Candidate).where(Candidate.email == candidate_email)
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Get all tasks for this candidate via TaskCandidateLink
    task_links = session.exec(
        select(TaskCandidateLink).where(TaskCandidateLink.candidate_email == candidate_email)
    ).all()
    task_ids = [link.task_id for link in task_links]

    tasks = []
    if task_ids:
        tasks = session.exec(
            select(Task).where(Task.id.in_(task_ids))
        ).all()

    return tasks


@router.get("/{candidate_email}/tasks/{task_identifier}")
def get_candidate_task(
    candidate_email: str,
    task_identifier: str,
    session: Session = Depends(get_session)
):
    """Get a specific Task instance for a candidate by task template identifier"""
    # Get the task
    task = session.exec(
        select(Task).join(TaskCandidateLink).where(
            TaskCandidateLink.candidate_email == candidate_email,
            Task.template_id == task_identifier
        )
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.post("/{candidate_email}/tasks/{task_identifier}", status_code=201)
def create_candidate_task(
    candidate_email: str,
    task_identifier: str,
    session: Session = Depends(get_session)
):
    """Create a Task instance from a TaskTemplate for a specific candidate"""
    # Get candidate
    candidate = session.exec(
        select(Candidate).where(Candidate.email == candidate_email)
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Get TaskTemplate by identifier
    task_template = session.exec(
        select(TaskTemplate).where(TaskTemplate.task_id == task_identifier)
    ).first()
    if not task_template:
        raise HTTPException(status_code=404, detail="Task template not found")

    # Check if task already exists for this candidate
    existing_tasks = session.exec(
        select(Task).join(TaskCandidateLink).where(
            TaskCandidateLink.candidate_email == candidate_email,
            Task.template_id == task_identifier
        )
    ).all()
    if existing_tasks:
        raise HTTPException(status_code=400, detail="Task already exists for this candidate")

    # Create Task instance from template
    new_task = Task(
        title=task_template.name,
        description=task_template.description,
        template_id=task_template.task_id,
        status=TaskStatus.TODO,
        workflow_id=candidate.workflow_id
    )
    session.add(new_task)
    session.flush()  # Flush to get the auto-generated ID

    # Link to candidate
    link = TaskCandidateLink(
        task_id=new_task.id,
        candidate_email=candidate.email
    )
    session.add(link)
    session.commit()
    session.refresh(new_task)

    return new_task


@router.put("/{candidate_email}/tasks/{task_identifier}")
def update_candidate_task(
    candidate_email: str,
    task_identifier: str,
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    notes: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Update a Task instance for a specific candidate"""
    # Get the task
    task = session.exec(
        select(Task).join(TaskCandidateLink).where(
            TaskCandidateLink.candidate_email == candidate_email,
            Task.template_id == task_identifier
        )
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check completion condition if status is being changed to "done"
    if status is not None and status == TaskStatus.DONE:
        # Get the candidate for condition evaluation
        candidate = session.exec(
            select(Candidate).where(Candidate.email == candidate_email)
        ).first()

        # Get the task template to access completion_condition
        task_template = session.exec(
            select(TaskTemplate).where(TaskTemplate.task_id == task_identifier)
        ).first()

        if task_template and task_template.completion_condition and candidate:
            from src.utils.conditions import safe_eval_condition
            completion_satisfied = safe_eval_condition(candidate, task_template.completion_condition)

            if not completion_satisfied:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot mark task as done: completion condition not satisfied ({task_template.completion_condition})"
                )

    # Update fields if provided
    if status is not None:
        task.status = status
    if assignee is not None:
        task.assignee = assignee
    if notes is not None:
        task.notes = notes

    session.add(task)
    session.commit()
    session.refresh(task)

    return task


@router.delete("/{candidate_email}/tasks/{task_identifier}", status_code=204)
def delete_candidate_task(
    candidate_email: str,
    task_identifier: str,
    session: Session = Depends(get_session)
):
    """Delete a Task instance for a specific candidate"""
    # Get the task
    task = session.exec(
        select(Task).join(TaskCandidateLink).where(
            TaskCandidateLink.candidate_email == candidate_email,
            Task.template_id == task_identifier
        )
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Delete the task (CASCADE will handle TaskCandidateLink)
    session.delete(task)
    session.commit()

    return None
