#!/usr/bin/env python3
"""
Migration: Remove soft delete columns from candidates table
"""
import sqlite3
import os
from pathlib import Path

def get_db_path():
    """Get the database path (same logic as in app.py)"""
    data_dir = Path.home() / ".hiring-client"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "hiring.db"

def migrate():
    db_path = get_db_path()

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    print(f"Migrating database at {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns exist
        cursor.execute("PRAGMA table_info(candidates)")
        columns = {row[1] for row in cursor.fetchall()}

        has_deleted = 'deleted' in columns
        has_deleted_at = 'deleted_at' in columns

        if not has_deleted and not has_deleted_at:
            print("✓ Soft delete columns already removed")
            return

        print(f"Found columns to remove: deleted={has_deleted}, deleted_at={has_deleted_at}")

        # SQLite doesn't support DROP COLUMN before version 3.35.0
        # So we need to recreate the table

        # 1. Create new table without soft delete columns
        cursor.execute("""
            CREATE TABLE candidates_new (
                id TEXT PRIMARY KEY,
                workflow_id TEXT,
                name TEXT,
                email TEXT,
                phone TEXT,
                resume_url TEXT,
                notes TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)

        # 2. Copy data from old table to new table
        cursor.execute("""
            INSERT INTO candidates_new
                (id, workflow_id, name, email, phone, resume_url, notes, created_at, updated_at)
            SELECT
                id, workflow_id, name, email, phone, resume_url, notes, created_at, updated_at
            FROM candidates
        """)

        # 3. Drop old table
        cursor.execute("DROP TABLE candidates")

        # 4. Rename new table to original name
        cursor.execute("ALTER TABLE candidates_new RENAME TO candidates")

        conn.commit()
        print("✓ Successfully removed soft delete columns from candidates table")

    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
