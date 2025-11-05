"""
Pydantic request/response models for API endpoints
"""
from typing import List, Optional
from pydantic import BaseModel
from .models import TaskStatus


class SpawnTaskRequest(BaseModel):
    """Request model for spawning tasks from a template"""
    template_id: str
    candidate_emails: List[str]
    title: Optional[str] = None
    description: Optional[str] = None


class CreateTaskRequest(BaseModel):
    """Request model for creating ad-hoc tasks"""
    title: str
    description: Optional[str] = None
    status: Optional[str] = TaskStatus.TODO
    workflow_id: Optional[str] = None
    candidate_emails: List[str] = []


class UpdateTaskRequest(BaseModel):
    """Request model for updating task properties"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class AddCandidatesRequest(BaseModel):
    """Request model for adding candidates to a task"""
    candidate_emails: List[str]


class ChecklistSaveRequest(BaseModel):
    """Request model for saving checklist state"""
    candidate_id: str
    task_identifier: str
    items_state: List[bool]
