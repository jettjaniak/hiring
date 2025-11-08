"""
CRUD helper functions to reduce code duplication across API endpoints.

These helpers extract common patterns like:
- Get-or-404 logic
- Update field-by-field with None checks
- Standard commit/refresh patterns
- Automatic audit tracking (created_by/updated_by)
"""
from datetime import datetime, timezone
from typing import TypeVar, Type, Any, Dict, Optional, TYPE_CHECKING
from fastapi import HTTPException
from sqlmodel import Session
from sqlalchemy.inspection import inspect

if TYPE_CHECKING:
    from src.models import User

ModelType = TypeVar("ModelType")


def get_or_404(
    session: Session,
    model_class: Type[ModelType],
    model_id: Any,
    resource_name: Optional[str] = None
) -> ModelType:
    """
    Get a model instance by ID or raise 404 if not found.

    Args:
        session: Database session
        model_class: The SQLModel class to query
        model_id: The primary key value
        resource_name: Human-readable resource name for error message (defaults to model class name)

    Returns:
        The model instance

    Raises:
        HTTPException: 404 if model not found
    """
    instance = session.get(model_class, model_id)
    if not instance:
        name = resource_name or model_class.__name__
        raise HTTPException(
            status_code=404,
            detail=f"{name} {model_id} not found"
        )
    return instance


def update_model_fields(
    model: Any,
    updates: Dict[str, Any],
    exclude_fields: Optional[set] = None,
    update_timestamp: bool = True,
    current_user: Optional["User"] = None
) -> None:
    """
    Update model fields from a dictionary, skipping None values.

    This eliminates the verbose pattern of:
        if field is not None:
            model.field = field

    Args:
        model: The model instance to update
        updates: Dictionary of field_name: value pairs
        exclude_fields: Set of field names to skip even if present in updates
        update_timestamp: If True, automatically update 'updated_at' field
        current_user: Current authenticated user (for audit tracking)
    """
    exclude = exclude_fields or set()

    # Get valid column names for the model
    mapper = inspect(model.__class__)
    valid_columns = {col.key for col in mapper.columns}

    # Update each field if it's valid, not excluded, and not None
    for field_name, value in updates.items():
        if field_name in exclude:
            continue
        if field_name not in valid_columns:
            continue
        if value is None:
            continue

        setattr(model, field_name, value)

    # Update timestamp if the field exists and update_timestamp is True
    if update_timestamp and hasattr(model, 'updated_at'):
        model.updated_at = datetime.now(timezone.utc)

    # Update audit fields
    if current_user and hasattr(model, 'updated_by'):
        model.updated_by = current_user.username


def set_created_by(
    model: Any,
    current_user: Optional["User"] = None
) -> None:
    """
    Set the created_by field on a new model instance.

    Args:
        model: The model instance being created
        current_user: Current authenticated user (for audit tracking)
    """
    if current_user and hasattr(model, 'created_by'):
        model.created_by = current_user.username


def commit_and_refresh(
    session: Session,
    model: Any,
    current_user: Optional["User"] = None
) -> Any:
    """
    Standard commit and refresh pattern with audit tracking.

    Args:
        session: Database session
        model: Model instance to commit
        current_user: Current authenticated user (for audit tracking)

    Returns:
        The refreshed model instance
    """
    # Set created_by if this is a new instance
    if hasattr(model, 'created_by') and model.created_by is None and current_user:
        model.created_by = current_user.username

    session.add(model)
    session.commit()
    session.refresh(model)
    return model
