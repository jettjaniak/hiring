"""
FastAPI dependency functions

This module provides shared dependency functions that can be imported
by both the main app and router modules.
"""
from typing import Optional
from fastapi import Request, Depends
from sqlmodel import Session, select
from src.database import Database
from src.models import User

# Module-level database instance - initialized by app.py
_db: Database = None


def init_database(database: Database):
    """
    Initialize the module-level database instance.

    This must be called from app.py before any routes are accessed.

    Args:
        database: The Database instance to use for all sessions
    """
    global _db
    _db = database


def get_session():
    """
    FastAPI dependency that provides a database session.

    Yields:
        Session: SQLModel database session

    Example:
        @router.get("/items")
        def list_items(session: Session = Depends(get_session)):
            return session.exec(select(Item)).all()
    """
    with _db.get_session() as session:
        yield session


def get_current_user(
    request: Request,
    session: Session = Depends(get_session)
) -> Optional[User]:
    """
    FastAPI dependency that retrieves the current authenticated user from the session.

    Args:
        request: The FastAPI request object (contains session data)
        session: Database session

    Returns:
        User object if authenticated, None otherwise

    Example:
        @router.get("/profile")
        def get_profile(current_user: Optional[User] = Depends(get_current_user)):
            if not current_user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            return current_user
    """
    # Check if user_id exists in session
    user_id = request.session.get("user_id")
    if not user_id:
        return None

    # Fetch user from database
    user = session.get(User, user_id)
    return user
