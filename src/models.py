"""
Database models for local storage
"""
from sqlmodel import SQLModel, Field, JSON, Column
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Text


class Candidate(SQLModel, table=True):
    """Candidate record"""
    __tablename__ = "candidates"

    id: str = Field(primary_key=True)

    # Candidate data fields
    workflow_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    resume_url: Optional[str] = None
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))

    # System timestamps
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class CandidateTask(SQLModel, table=True):
    """Task status record"""
    __tablename__ = "candidate_tasks"

    candidate_id: str = Field(foreign_key="candidates.id", primary_key=True, ondelete="CASCADE")
    task_identifier: str = Field(primary_key=True)

    # Task status: "not_started", "in_progress", "completed", "na"
    status: Optional[str] = None

    # System timestamps
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class ActionState(SQLModel, table=True):
    """Action state storage"""
    __tablename__ = "action_states"

    candidate_id: str = Field(foreign_key="candidates.id", primary_key=True, ondelete="CASCADE")
    action_id: str = Field(primary_key=True)

    # Action state as JSON
    state: Optional[dict] = Field(default_factory=dict, sa_type=JSON)

    # System timestamps
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
