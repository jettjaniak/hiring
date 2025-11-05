"""
Validation utility functions
"""
from typing import List
from fastapi import HTTPException
from sqlmodel import Session, select
from ..models import Candidate, TaskStatus


def validate_status(status: str) -> None:
    """
    Validate that a status is one of the allowed TaskStatus values.

    Args:
        status: Status string to validate

    Raises:
        HTTPException: 400 if status is invalid
    """
    valid_statuses = [
        TaskStatus.TODO,
        TaskStatus.IN_PROGRESS,
        TaskStatus.BLOCKED,
        TaskStatus.DONE,
        TaskStatus.CANCELLED
    ]

    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )


def validate_candidates_exist(session: Session, emails: List[str]) -> None:
    """
    Validate that all candidates with given emails exist in the database.

    Args:
        session: Database session
        emails: List of candidate email addresses

    Raises:
        HTTPException: 404 if any candidate doesn't exist
    """
    for email in emails:
        candidate = session.get(Candidate, email)
        if not candidate:
            raise HTTPException(
                status_code=404,
                detail=f"Candidate {email} not found"
            )
