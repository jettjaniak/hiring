"""
FastAPI dependency functions

This module provides shared dependency functions that can be imported
by both the main app and router modules.
"""
from src.database import Database

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
