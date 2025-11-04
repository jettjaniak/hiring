"""Application-wide constants"""


class TaskStatus:
    """Task status constants

    Centralizes all task status values to avoid magic strings throughout the codebase.
    """
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"

    @classmethod
    def all(cls):
        """Return list of all valid status values"""
        return [cls.TODO, cls.IN_PROGRESS, cls.DONE]

    @classmethod
    def is_valid(cls, status):
        """Check if a status value is valid"""
        return status in cls.all()
