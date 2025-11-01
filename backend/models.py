"""
Database models using SQLModel (combines SQLAlchemy + Pydantic)
SQLModel automatically generates:
- Database tables
- Pydantic schemas for validation
- OpenAPI/Swagger documentation
"""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, JSON, Column
from sqlalchemy import DateTime
from sqlalchemy.sql import func


class Candidate(SQLModel, table=True):
    """Candidate in the hiring process"""
    __tablename__ = "candidates"

    id: Optional[str] = Field(default=None, primary_key=True)

    # Candidate information
    workflow_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    resume_url: Optional[str] = None
    notes: Optional[str] = None

    # System fields
    created_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )

    # Soft delete
    deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class CandidateTask(SQLModel, table=True):
    """Task status for a candidate"""
    __tablename__ = "candidate_tasks"

    candidate_id: str = Field(foreign_key="candidates.id", primary_key=True, ondelete="CASCADE")
    task_identifier: str = Field(primary_key=True)

    # Task status: not_started, in_progress, completed, na
    status: Optional[str] = None

    # System fields
    created_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )


class ActionState(SQLModel, table=True):
    """Action state storage for workflow actions"""
    __tablename__ = "action_states"

    candidate_id: str = Field(foreign_key="candidates.id", primary_key=True, ondelete="CASCADE")
    action_id: str = Field(primary_key=True)

    # State as JSON
    state: Optional[dict] = Field(default_factory=dict, sa_column=Column(JSON))

    # System fields
    created_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )
