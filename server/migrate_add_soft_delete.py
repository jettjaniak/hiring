"""
Migration: Add soft delete columns
"""
import sqlite3
import os

def migrate():
    db_path = 'hiring.db'

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(candidates)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'deleted' not in columns:
        print("Adding soft delete columns to candidates...")
        cursor.execute("ALTER TABLE candidates ADD COLUMN deleted BOOLEAN NOT NULL DEFAULT 0")
        cursor.execute("ALTER TABLE candidates ADD COLUMN deleted_at TIMESTAMP")
        print("✓ Updated candidates table")
    else:
        print("✓ Candidates table already has soft delete columns")

    cursor.execute("PRAGMA table_info(candidate_tasks)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'deleted' not in columns:
        print("Adding soft delete columns to candidate_tasks...")
        cursor.execute("ALTER TABLE candidate_tasks ADD COLUMN deleted BOOLEAN NOT NULL DEFAULT 0")
        cursor.execute("ALTER TABLE candidate_tasks ADD COLUMN deleted_at TIMESTAMP")
        print("✓ Updated candidate_tasks table")
    else:
        print("✓ Candidate_tasks table already has soft delete columns")

    cursor.execute("PRAGMA table_info(action_states)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'deleted' not in columns:
        print("Adding soft delete columns to action_states...")
        cursor.execute("ALTER TABLE action_states ADD COLUMN deleted BOOLEAN NOT NULL DEFAULT 0")
        cursor.execute("ALTER TABLE action_states ADD COLUMN deleted_at TIMESTAMP")
        print("✓ Updated action_states table")
    else:
        print("✓ Action_states table already has soft delete columns")

    conn.commit()
    conn.close()
    print("\n✅ Migration complete!")

if __name__ == '__main__':
    migrate()
