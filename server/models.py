from sqlalchemy import Column, String, Integer, Boolean, DateTime, LargeBinary, ForeignKey, ForeignKeyConstraint, Index
from sqlalchemy.sql import func
from database import Base


class Metadata(Base):
    """Shared metadata for all synced entities"""
    __tablename__ = "metadata"

    id = Column(String, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class Candidate(Base):
    """Candidate record"""
    __tablename__ = "candidates"

    id = Column(String, primary_key=True)
    metadata_id = Column(String, ForeignKey("metadata.id", ondelete="CASCADE"), nullable=False)


class CandidateField(Base):
    """Candidate fields (encrypted)"""
    __tablename__ = "candidate_fields"

    candidate_id = Column(String, ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True)
    field_name = Column(String, primary_key=True)
    encrypted_value = Column(LargeBinary, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('ix_candidate_field_updated', 'updated_at'),
    )


class CandidateTask(Base):
    """Candidate task record"""
    __tablename__ = "candidate_tasks"

    candidate_id = Column(String, ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True)
    task_identifier = Column(String, primary_key=True)
    metadata_id = Column(String, ForeignKey("metadata.id", ondelete="CASCADE"), nullable=False)


class CandidateTaskField(Base):
    """Candidate task fields (encrypted)"""
    __tablename__ = "candidate_task_fields"

    candidate_id = Column(String, primary_key=True)
    task_identifier = Column(String, primary_key=True)
    field_name = Column(String, primary_key=True)
    encrypted_value = Column(LargeBinary, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ['candidate_id', 'task_identifier'],
            ['candidate_tasks.candidate_id', 'candidate_tasks.task_identifier'],
            ondelete="CASCADE"
        ),
        Index('ix_candidate_task_field_updated', 'updated_at'),
    )


class ActionState(Base):
    """Action state record"""
    __tablename__ = "action_states"

    candidate_id = Column(String, ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True)
    action_id = Column(String, primary_key=True)
    metadata_id = Column(String, ForeignKey("metadata.id", ondelete="CASCADE"), nullable=False)


class ActionStateField(Base):
    """Action state fields (encrypted)"""
    __tablename__ = "action_state_fields"

    candidate_id = Column(String, primary_key=True)
    action_id = Column(String, primary_key=True)
    field_name = Column(String, primary_key=True)
    encrypted_value = Column(LargeBinary, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ['candidate_id', 'action_id'],
            ['action_states.candidate_id', 'action_states.action_id'],
            ondelete="CASCADE"
        ),
        Index('ix_action_state_field_updated', 'updated_at'),
    )


class KeyVerification(Base):
    __tablename__ = "key_verification"

    id = Column(Integer, primary_key=True, default=1)
    encrypted_canary = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
