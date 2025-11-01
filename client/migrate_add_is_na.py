#!/usr/bin/env python3
"""
Migration: Add is_na column to candidate_tasks table
"""
import sqlite3
from pathlib import Path
from config import Config

def migrate():
    """Add is_na column to candidate_tasks"""
    config = Config()
    db_path = config.db_file

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(candidate_tasks)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'is_na' in columns:
            print("Column 'is_na' already exists, skipping migration")
            return

        # Add the is_na column with default value False
        print("Adding 'is_na' column to candidate_tasks...")
        cursor.execute("""
            ALTER TABLE candidate_tasks
            ADD COLUMN is_na BOOLEAN NOT NULL DEFAULT 0
        """)

        conn.commit()
        print("Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
