"""
Local database for storing data
"""
from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy import event


class Database:
    def __init__(self, db_path: str):
        self.engine = create_engine(f"sqlite:///{db_path}")

        # Enable foreign key constraints for SQLite
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    def init_db(self):
        """Initialize database tables"""
        SQLModel.metadata.create_all(self.engine)

    def get_session(self):
        """Get a new database session"""
        return Session(self.engine)
