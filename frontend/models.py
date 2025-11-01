"""
Database models for local storage
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from database import Base


class Candidate(Base):
    """Candidate record"""
    __tablename__ = "candidates"

    id = Column(String, primary_key=True)

    # Candidate data fields
    workflow_id = Column(String, nullable=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    resume_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # System timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Soft delete
    deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class CandidateTask(Base):
    """Task status record"""
    __tablename__ = "candidate_tasks"

    candidate_id = Column(String, ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True)
    task_identifier = Column(String, primary_key=True)

    # Task status: "not_started", "in_progress", "completed", "na"
    status = Column(String, nullable=True)

    # System timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ActionState(Base):
    """Action state storage"""
    __tablename__ = "action_states"

    candidate_id = Column(String, ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True)
    action_id = Column(String, primary_key=True)

    # Action state as JSON
    state = Column(JSON, nullable=True, default=dict)

    # System timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
