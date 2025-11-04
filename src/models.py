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

    email: str = Field(primary_key=True)  # Email is now the primary key

    # Candidate data fields
    workflow_id: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    resume_url: Optional[str] = None
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))

    # System timestamps
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class CandidateTask(SQLModel, table=True):
    """Task status record"""
    __tablename__ = "candidate_tasks"

    candidate_id: str = Field(foreign_key="candidates.email", primary_key=True, ondelete="CASCADE")
    task_identifier: str = Field(primary_key=True)

    # Task status: "not_started", "in_progress", "completed", "na"
    status: Optional[str] = None

    # System timestamps
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class Checklist(SQLModel, table=True):
    """Checklist definition"""
    __tablename__ = "checklists"

    id: str = Field(primary_key=True)
    name: str
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    task_id: str = Field(foreign_key="tasks.task_id", unique=True, ondelete="CASCADE")
    items: str = Field(sa_column=Column(Text))  # JSON string: ["item1", "item2", ...]

    # System timestamps
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class CandidateChecklistState(SQLModel, table=True):
    """Checklist completion state for a candidate"""
    __tablename__ = "candidate_checklist_states"

    candidate_id: str = Field(foreign_key="candidates.email", primary_key=True, ondelete="CASCADE")
    task_identifier: str = Field(primary_key=True)
    checklist_id: str = Field(foreign_key="checklists.id", primary_key=True, ondelete="CASCADE")
    items_state: str = Field(sa_column=Column(Text))  # JSON string: [true, false, true, ...]

    # System timestamps
    last_modified: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class EmailTemplate(SQLModel, table=True):
    """Email template for candidate communications"""
    __tablename__ = "email_templates"

    id: str = Field(primary_key=True)
    name: str
    description: Optional[str] = None
    subject: Optional[str] = None
    to: Optional[str] = None
    cc: Optional[str] = None
    bcc: Optional[str] = None
    content: str = Field(sa_column=Column(Text))
    variables: Optional[str] = None  # JSON string: [{"name": "var1", "type": "text"}, {"name": "var2", "type": "boolean"}]

    # System timestamps
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class Task(SQLModel, table=True):
    """Task definition"""
    __tablename__ = "tasks"

    task_id: str = Field(primary_key=True)
    name: str
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    special_action: Optional[str] = None  # Name of the special action view (e.g., "fill_offer_letter")

    # System timestamps
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class EmailTemplateTask(SQLModel, table=True):
    """Many-to-many relationship between email templates and tasks"""
    __tablename__ = "email_template_tasks"

    email_template_id: str = Field(foreign_key="email_templates.id", primary_key=True, ondelete="CASCADE")
    task_id: str = Field(foreign_key="tasks.task_id", primary_key=True, ondelete="CASCADE")

    # System timestamps
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class SpawnedTask(SQLModel, table=True):
    """Spawned task instance - actual work item that can be created from templates or ad-hoc"""
    __tablename__ = "spawned_tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    status: str = "todo"  # todo, in_progress, done
    template_id: Optional[str] = Field(default=None, foreign_key="tasks.task_id", ondelete="SET NULL")
    workflow_id: Optional[str] = None

    # System timestamps
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaskCandidateLink(SQLModel, table=True):
    """Many-to-many relationship between spawned tasks and candidates"""
    __tablename__ = "task_candidate_links"

    task_id: int = Field(foreign_key="spawned_tasks.id", primary_key=True, ondelete="CASCADE")
    candidate_email: str = Field(foreign_key="candidates.email", primary_key=True, ondelete="CASCADE")

    # System timestamps
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
