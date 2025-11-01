"""
Local database models for decrypted data
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from database import Base


class Candidate(Base):
    """Local candidate record (decrypted)"""
    __tablename__ = "candidates"

    id = Column(String, primary_key=True)

    # User data fields (encrypted on server)
    workflow_id = Column(String, nullable=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    resume_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # Per-field version tracking (local metadata)
    workflow_id_version = Column(Integer, nullable=False, default=0)
    name_version = Column(Integer, nullable=False, default=0)
    email_version = Column(Integer, nullable=False, default=0)
    phone_version = Column(Integer, nullable=False, default=0)
    resume_url_version = Column(Integer, nullable=False, default=0)
    notes_version = Column(Integer, nullable=False, default=0)

    # Per-field dirty tracking (local metadata)
    workflow_id_dirty = Column(Boolean, nullable=False, default=False)
    name_dirty = Column(Boolean, nullable=False, default=False)
    email_dirty = Column(Boolean, nullable=False, default=False)
    phone_dirty = Column(Boolean, nullable=False, default=False)
    resume_url_dirty = Column(Boolean, nullable=False, default=False)
    notes_dirty = Column(Boolean, nullable=False, default=False)

    # System timestamps
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    last_synced = Column(DateTime(timezone=True), nullable=True)

    # Soft delete
    deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class CandidateTask(Base):
    """Local task record (decrypted)"""
    __tablename__ = "candidate_tasks"

    candidate_id = Column(String, ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True)
    task_identifier = Column(String, primary_key=True)

    # User data field (encrypted on server)
    # Values: "not_started", "in_progress", "completed", "na"
    status = Column(String, nullable=True)

    # Per-field version tracking (local metadata)
    status_version = Column(Integer, nullable=False, default=0)

    # Per-field dirty tracking (local metadata)
    status_dirty = Column(Boolean, nullable=False, default=False)

    # System timestamps
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    last_synced = Column(DateTime(timezone=True), nullable=True)


class ActionState(Base):
    """Local action state record (decrypted)"""
    __tablename__ = "action_states"

    candidate_id = Column(String, ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True)
    action_id = Column(String, primary_key=True)

    # User data field (encrypted on server)
    state = Column(JSON, nullable=True, default=dict)

    # Per-field version tracking (local metadata)
    state_version = Column(Integer, nullable=False, default=0)

    # Per-field dirty tracking (local metadata)
    state_dirty = Column(Boolean, nullable=False, default=False)

    # System timestamps
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    last_synced = Column(DateTime(timezone=True), nullable=True)


class SyncMetadata(Base):
    """Track sync state"""
    __tablename__ = "sync_metadata"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
