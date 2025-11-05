"""
Task Template API routes
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from ...models import TaskTemplate
from ...dependencies import get_session

router = APIRouter(prefix="/api/task-templates", tags=["task-templates"])


@router.get("", response_model=List[TaskTemplate])
def list_tasks(session: Session = Depends(get_session)):
    """List all tasks"""
    tasks = session.exec(select(TaskTemplate)).all()
    return tasks


@router.get("/{task_id}", response_model=TaskTemplate)
def get_task(task_id: str, session: Session = Depends(get_session)):
    """Get a specific task"""
    task = session.get(TaskTemplate, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@router.post("", response_model=TaskTemplate, status_code=201)
def create_task(
    task_id: str,
    name: str,
    description: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Create a new task"""
    # Check if task already exists
    existing_task = session.get(TaskTemplate, task_id)
    if existing_task:
        raise HTTPException(status_code=400, detail=f"Task {task_id} already exists")

    task = TaskTemplate(
        task_id=task_id,
        name=name,
        description=description
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.put("/{task_id}", response_model=TaskTemplate)
def update_task(
    task_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Update a task"""
    task = session.get(TaskTemplate, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if name is not None:
        task.name = name
    if description is not None:
        task.description = description

    task.updated_at = datetime.now(timezone.utc)
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: str, session: Session = Depends(get_session)):
    """Delete a task"""
    task = session.get(TaskTemplate, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    session.delete(task)
    session.commit()
    return None
