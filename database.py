"""
Local database for storing data
"""
from sqlmodel import create_engine, SQLModel, Session


class Database:
    def __init__(self, db_path: str):
        self.engine = create_engine(f"sqlite:///{db_path}")

    def init_db(self):
        """Initialize database tables"""
        SQLModel.metadata.create_all(self.engine)

    def get_session(self):
        """Get a new database session"""
        return Session(self.engine)
