from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
from typing import List, Optional, Tuple
import models
import schemas
import uuid


class VersionConflictError(Exception):
    def __init__(self, message: str, conflicting_keys: List[str] = None):
        self.message = message
        self.conflicting_keys = conflicting_keys or []
        super().__init__(self.message)


# Candidate operations
def create_candidate(db: Session, candidate: schemas.CandidateCreate) -> models.Candidate:
    # Create metadata entry
    metadata_id = f"metadata-{uuid.uuid4().hex[:12]}"
    db_metadata = models.Metadata(id=metadata_id)
    db.add(db_metadata)

    # Create candidate with metadata reference
    db_candidate = models.Candidate(
        id=candidate.id,
        metadata_id=metadata_id
    )
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    db.refresh(db_metadata)
    return db_candidate


def get_candidate(db: Session, candidate_id: str) -> Optional[models.Candidate]:
    return db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()


def list_candidates(db: Session) -> List[models.Candidate]:
    return db.query(models.Candidate).all()


# CandidateField operations
def get_candidate_fields(db: Session, candidate_id: str) -> List[models.CandidateField]:
    return db.query(models.CandidateField).filter(
        models.CandidateField.candidate_id == candidate_id
    ).all()


def update_candidate_fields(
    db: Session,
    candidate_id: str,
    fields: List[schemas.FieldUpdate]
) -> List[Tuple[str, int]]:
    """
    Update multiple fields with version checking.
    Returns list of (key, new_version) tuples.
    Raises VersionConflictError if any version mismatches.
    """
    # First, check all versions
    conflicting_keys = []
    for field in fields:
        existing = db.query(models.CandidateField).filter(
            models.CandidateField.candidate_id == candidate_id,
            models.CandidateField.field_name == field.key
        ).first()

        if existing and existing.version != field.version:
            conflicting_keys.append(field.key)

    if conflicting_keys:
        raise VersionConflictError(
            f"Version conflict on fields: {', '.join(conflicting_keys)}",
            conflicting_keys
        )

    # All versions match, perform updates
    results = []
    for field in fields:
        existing = db.query(models.CandidateField).filter(
            models.CandidateField.candidate_id == candidate_id,
            models.CandidateField.field_name == field.key
        ).first()

        if existing:
            existing.encrypted_value = field.encrypted_value
            existing.version += 1
            results.append((field.key, existing.version))
        else:
            # New field
            new_field = models.CandidateField(
                candidate_id=candidate_id,
                field_name=field.key,
                encrypted_value=field.encrypted_value,
                version=1
            )
            db.add(new_field)
            results.append((field.key, 1))

    db.commit()
    return results


# CandidateTask operations
def get_candidate_tasks(db: Session, candidate_id: str) -> List[models.CandidateTask]:
    return db.query(models.CandidateTask).filter(
        models.CandidateTask.candidate_id == candidate_id
    ).all()


def create_candidate_task(db: Session, task: schemas.CandidateTaskCreate) -> models.CandidateTask:
    # Create metadata entry
    metadata_id = f"metadata-{uuid.uuid4().hex[:12]}"
    db_metadata = models.Metadata(id=metadata_id)
    db.add(db_metadata)

    # Create task with metadata reference (no field data here)
    db_task = models.CandidateTask(
        candidate_id=task.candidate_id,
        task_identifier=task.task_identifier,
        metadata_id=metadata_id
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_candidate_task_fields(db: Session, candidate_id: str, task_identifier: str) -> List[models.CandidateTaskField]:
    return db.query(models.CandidateTaskField).filter(
        models.CandidateTaskField.candidate_id == candidate_id,
        models.CandidateTaskField.task_identifier == task_identifier
    ).all()


def update_candidate_task_fields(
    db: Session,
    candidate_id: str,
    task_identifier: str,
    fields: List[schemas.FieldUpdate]
) -> List[Tuple[str, int]]:
    """
    Update task fields with version checking.
    Returns list of (field_name, new_version) tuples.
    """
    # First, check all versions
    conflicting_keys = []
    for field in fields:
        existing = db.query(models.CandidateTaskField).filter(
            models.CandidateTaskField.candidate_id == candidate_id,
            models.CandidateTaskField.task_identifier == task_identifier,
            models.CandidateTaskField.field_name == field.key
        ).first()

        if existing and existing.version != field.version:
            conflicting_keys.append(field.key)

    if conflicting_keys:
        raise VersionConflictError(
            f"Version conflict on fields: {', '.join(conflicting_keys)}",
            conflicting_keys
        )

    # All versions match, perform updates
    results = []
    for field in fields:
        existing = db.query(models.CandidateTaskField).filter(
            models.CandidateTaskField.candidate_id == candidate_id,
            models.CandidateTaskField.task_identifier == task_identifier,
            models.CandidateTaskField.field_name == field.key
        ).first()

        if existing:
            existing.encrypted_value = field.encrypted_value
            existing.version += 1
            results.append((field.key, existing.version))
        else:
            # New field
            new_field = models.CandidateTaskField(
                candidate_id=candidate_id,
                task_identifier=task_identifier,
                field_name=field.key,
                encrypted_value=field.encrypted_value,
                version=1
            )
            db.add(new_field)
            results.append((field.key, 1))

    db.commit()
    return results




# ActionState operations
def get_action_states(db: Session, candidate_id: str) -> List[models.ActionState]:
    return db.query(models.ActionState).filter(
        models.ActionState.candidate_id == candidate_id
    ).all()


def create_action_state(db: Session, action_state: schemas.ActionStateCreate) -> models.ActionState:
    # Create metadata entry
    metadata_id = f"metadata-{uuid.uuid4().hex[:12]}"
    db_metadata = models.Metadata(id=metadata_id)
    db.add(db_metadata)

    # Create action state with metadata reference (no field data here)
    db_state = models.ActionState(
        candidate_id=action_state.candidate_id,
        action_id=action_state.action_id,
        metadata_id=metadata_id
    )
    db.add(db_state)
    db.commit()
    db.refresh(db_state)
    return db_state


def get_action_state_fields(db: Session, candidate_id: str, action_id: str) -> List[models.ActionStateField]:
    return db.query(models.ActionStateField).filter(
        models.ActionStateField.candidate_id == candidate_id,
        models.ActionStateField.action_id == action_id
    ).all()


def update_action_state_fields(
    db: Session,
    candidate_id: str,
    action_id: str,
    fields: List[schemas.FieldUpdate]
) -> List[Tuple[str, int]]:
    """
    Update action state fields with version checking.
    Returns list of (field_name, new_version) tuples.
    """
    # First, check all versions
    conflicting_keys = []
    for field in fields:
        existing = db.query(models.ActionStateField).filter(
            models.ActionStateField.candidate_id == candidate_id,
            models.ActionStateField.action_id == action_id,
            models.ActionStateField.field_name == field.key
        ).first()

        if existing and existing.version != field.version:
            conflicting_keys.append(field.key)

    if conflicting_keys:
        raise VersionConflictError(
            f"Version conflict on fields: {', '.join(conflicting_keys)}",
            conflicting_keys
        )

    # All versions match, perform updates
    results = []
    for field in fields:
        existing = db.query(models.ActionStateField).filter(
            models.ActionStateField.candidate_id == candidate_id,
            models.ActionStateField.action_id == action_id,
            models.ActionStateField.field_name == field.key
        ).first()

        if existing:
            existing.encrypted_value = field.encrypted_value
            existing.version += 1
            results.append((field.key, existing.version))
        else:
            # New field
            new_field = models.ActionStateField(
                candidate_id=candidate_id,
                action_id=action_id,
                field_name=field.key,
                encrypted_value=field.encrypted_value,
                version=1
            )
            db.add(new_field)
            results.append((field.key, 1))

    db.commit()
    return results


# Sync operations
def get_changes_since(db: Session, since: datetime) -> dict:
    """
    Get all changes since a given timestamp for sync.
    Uses metadata table to find updated entities, then returns their field data.
    """
    # Find all metadata entries updated since timestamp
    updated_metadata = db.query(models.Metadata).filter(
        or_(
            models.Metadata.created_at > since,
            models.Metadata.updated_at > since
        )
    ).all()

    metadata_ids = {m.id for m in updated_metadata}

    # Get candidates with updated metadata
    candidates = db.query(models.Candidate).filter(
        models.Candidate.metadata_id.in_(metadata_ids)
    ).all() if metadata_ids else []

    # Get all candidate fields updated since timestamp
    candidate_fields = db.query(models.CandidateField).filter(
        models.CandidateField.updated_at > since
    ).all()

    # Get tasks with updated metadata
    tasks = db.query(models.CandidateTask).filter(
        models.CandidateTask.metadata_id.in_(metadata_ids)
    ).all() if metadata_ids else []

    # Get all task fields updated since timestamp
    task_fields = db.query(models.CandidateTaskField).filter(
        models.CandidateTaskField.updated_at > since
    ).all()

    # Get action states with updated metadata
    action_states = db.query(models.ActionState).filter(
        models.ActionState.metadata_id.in_(metadata_ids)
    ).all() if metadata_ids else []

    # Get all action state fields updated since timestamp
    action_state_fields = db.query(models.ActionStateField).filter(
        models.ActionStateField.updated_at > since
    ).all()

    return {
        "candidates": candidates,
        "candidate_fields": candidate_fields,
        "tasks": tasks,
        "task_fields": task_fields,
        "action_states": action_states,
        "action_state_fields": action_state_fields
    }


# Key verification operations
def get_key_verification(db: Session) -> Optional[models.KeyVerification]:
    """Get the key verification record"""
    return db.query(models.KeyVerification).filter_by(id=1).first()


def create_key_verification(db: Session, encrypted_canary: bytes) -> models.KeyVerification:
    """Create key verification record"""
    db_verification = models.KeyVerification(
        id=1,
        encrypted_canary=encrypted_canary
    )
    db.add(db_verification)
    db.commit()
    db.refresh(db_verification)
    return db_verification
