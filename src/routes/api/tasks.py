"""
Spawnable Tasks API routes - Task instances spawned from templates or created ad-hoc
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional, List

from ...models import Task, TaskTemplate, TaskCandidateLink, Candidate, User
from ...dependencies import get_session, get_current_user
from ...constants import TaskStatus
from ...crud_helpers import get_or_404, update_model_fields, commit_and_refresh, set_created_by

router = APIRouter(prefix="/api", tags=["tasks"])


# Pydantic request models
class SpawnTaskRequest(BaseModel):
    template_id: str
    candidate_emails: List[str]
    title: Optional[str] = None
    description: Optional[str] = None


class CreateTaskRequest(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = TaskStatus.TODO
    workflow_id: Optional[str] = None
    candidate_emails: List[str] = []


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class AddCandidatesRequest(BaseModel):
    candidate_emails: List[str]


@router.post("/task-templates/spawn", response_model=Task, status_code=201)
def spawn_task(
    request: SpawnTaskRequest,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Spawn a task from a template for specific candidates

    If the same template has already been spawned for a candidate, returns the existing task.
    """
    # Validate template exists
    template = session.get(TaskTemplate, request.template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {request.template_id} not found")

    # Template-based tasks must have exactly one candidate
    if len(request.candidate_emails) != 1:
        raise HTTPException(
            status_code=400,
            detail=f"Template-based tasks must be created for exactly one candidate. "
                   f"You provided {len(request.candidate_emails)} candidates. "
                   f"To create tasks for multiple candidates, call this endpoint once per candidate."
        )

    # Validate all candidates exist
    for email in request.candidate_emails:
        candidate = session.get(Candidate, email)
        if not candidate:
            raise HTTPException(status_code=404, detail=f"Candidate {email} not found")

    # Check if this template has already been spawned for any of these candidates
    # Get the first candidate to check workflow_id
    first_candidate = session.get(Candidate, request.candidate_emails[0])
    workflow_id = first_candidate.workflow_id if first_candidate else None

    # Look for existing spawned task with same template_id and any of the candidate_emails
    existing_links = session.exec(
        select(TaskCandidateLink).where(
            TaskCandidateLink.candidate_email.in_(request.candidate_emails)
        )
    ).all()

    if existing_links:
        # Check if any of these links point to a task with the same template_id
        for link in existing_links:
            spawned_task = session.get(Task, link.task_id)
            if spawned_task and spawned_task.template_id == request.template_id:
                # Found existing task with same template for at least one candidate
                # Return it (duplicate prevention)
                return spawned_task

    # Create new spawned task
    title = request.title or template.name
    description = request.description or template.description

    spawned_task = Task(
        title=title,
        description=description,
        status=TaskStatus.TODO,
        template_id=request.template_id,
        workflow_id=workflow_id,
        assigned_to=template.default_dri  # Use template's default DRI
    )
    set_created_by(spawned_task, current_user)
    session.add(spawned_task)
    session.commit()
    session.refresh(spawned_task)

    # Create task-candidate links
    for email in request.candidate_emails:
        link = TaskCandidateLink(
            task_id=spawned_task.id,
            candidate_email=email
        )
        set_created_by(link, current_user)
        session.add(link)
    session.commit()
    session.refresh(spawned_task)  # Refresh after second commit to ensure object is attached

    return spawned_task


@router.get("/tasks", response_model=List[Task])
def list_spawned_tasks(
    status: Optional[str] = None,
    workflow_id: Optional[str] = None,
    template_id: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """List all spawned tasks with optional filters"""
    query = select(Task)

    if status:
        query = query.where(Task.status == status)
    if workflow_id:
        query = query.where(Task.workflow_id == workflow_id)
    if template_id:
        query = query.where(Task.template_id == template_id)

    tasks = session.exec(query).all()
    return tasks


@router.get("/tasks/{task_id}", response_model=Task)
def get_spawned_task(task_id: int, session: Session = Depends(get_session)):
    """Get a specific spawned task by ID"""
    return get_or_404(session, Task, task_id, "Spawned task")


@router.post("/tasks", response_model=Task, status_code=201)
def create_spawned_task(
    request: CreateTaskRequest,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Create a new ad-hoc spawned task (not from template)"""
    # Validate status
    if request.status not in TaskStatus.all():
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(TaskStatus.all())}")

    # Validate all candidates exist
    for email in request.candidate_emails:
        candidate = session.get(Candidate, email)
        if not candidate:
            raise HTTPException(status_code=404, detail=f"Candidate {email} not found")

    # Create spawned task
    spawned_task = Task(
        title=request.title,
        description=request.description,
        status=request.status,
        workflow_id=request.workflow_id
    )
    set_created_by(spawned_task, current_user)
    session.add(spawned_task)
    session.commit()
    session.refresh(spawned_task)

    # Create task-candidate links
    for email in request.candidate_emails:
        link = TaskCandidateLink(
            task_id=spawned_task.id,
            candidate_email=email
        )
        set_created_by(link, current_user)
        session.add(link)
    session.commit()
    session.refresh(spawned_task)  # Refresh after second commit to ensure object is attached

    return spawned_task


@router.put("/tasks/{task_id}", response_model=Task)
def update_spawned_task(
    task_id: int,
    request: UpdateTaskRequest,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Update a spawned task"""
    task = get_or_404(session, Task, task_id, "Spawned task")

    # Validate status before updating
    if request.status is not None and request.status not in TaskStatus.all():
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(TaskStatus.all())}")

    update_model_fields(task, {
        'title': request.title,
        'description': request.description,
        'status': request.status
    }, current_user=current_user)
    return commit_and_refresh(session, task, current_user)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_spawned_task(task_id: int, session: Session = Depends(get_session)):
    """Delete a spawned task"""
    task = get_or_404(session, Task, task_id, "Spawned task")
    session.delete(task)
    session.commit()
    return None


@router.get("/tasks/{task_id}/candidates", response_model=List[str])
def get_task_candidates(task_id: int, session: Session = Depends(get_session)):
    """Get all candidates associated with a spawned task"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Spawned task {task_id} not found")

    links = session.exec(
        select(TaskCandidateLink).where(TaskCandidateLink.task_id == task_id)
    ).all()

    return [link.candidate_email for link in links]


@router.post("/tasks/{task_id}/candidates", status_code=201)
def add_candidates_to_task(
    task_id: int,
    request: AddCandidatesRequest,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Add candidates to a spawned task"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Spawned task {task_id} not found")

    # Tasks from templates cannot be shared between candidates
    if task.template_id is not None:
        existing_links = session.exec(
            select(TaskCandidateLink).where(TaskCandidateLink.task_id == task_id)
        ).all()
        if existing_links:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot add candidates to template-based task. Task is already assigned to {existing_links[0].candidate_email}. Template-based tasks must be separate for each candidate."
            )

    # Validate all candidates exist
    for email in request.candidate_emails:
        candidate = session.get(Candidate, email)
        if not candidate:
            raise HTTPException(status_code=404, detail=f"Candidate {email} not found")

    # Add new links (skip if already exists)
    added = []
    for email in request.candidate_emails:
        existing = session.exec(
            select(TaskCandidateLink).where(
                TaskCandidateLink.task_id == task_id,
                TaskCandidateLink.candidate_email == email
            )
        ).first()

        if not existing:
            link = TaskCandidateLink(
                task_id=task_id,
                candidate_email=email
            )
            set_created_by(link, current_user)
            session.add(link)
            added.append(email)

    session.commit()

    return {"message": f"Added {len(added)} candidate(s)", "added": added}


@router.delete("/tasks/{task_id}/candidates/{candidate_email}", status_code=204)
def remove_candidate_from_task(
    task_id: int,
    candidate_email: str,
    session: Session = Depends(get_session)
):
    """Remove a candidate from a spawned task"""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Spawned task {task_id} not found")

    link = session.exec(
        select(TaskCandidateLink).where(
            TaskCandidateLink.task_id == task_id,
            TaskCandidateLink.candidate_email == candidate_email
        )
    ).first()

    if not link:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_email} not associated with task {task_id}")

    session.delete(link)
    session.commit()
    return None
