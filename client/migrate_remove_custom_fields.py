"""
Migration: Remove custom_fields column
"""
import sqlite3
import os

def migrate():
    db_path = os.path.expanduser('~/.hiring-client/local.db')

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if column exists
    cursor.execute("PRAGMA table_info(candidates)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'custom_fields' in columns:
        print("Removing custom_fields column from candidates...")

        # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
        # First, get the current data
        cursor.execute("""
            CREATE TABLE candidates_new (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                name TEXT,
                email TEXT,
                phone TEXT,
                resume_url TEXT,
                notes TEXT,
                field_versions TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_synced TIMESTAMP,
                deleted BOOLEAN NOT NULL DEFAULT 0,
                deleted_at TIMESTAMP
            )
        """)

        # Copy data
        cursor.execute("""
            INSERT INTO candidates_new
            SELECT id, workflow_id, name, email, phone, resume_url, notes,
                   field_versions, created_at, updated_at, last_synced, deleted, deleted_at
            FROM candidates
        """)

        # Drop old table and rename new one
        cursor.execute("DROP TABLE candidates")
        cursor.execute("ALTER TABLE candidates_new RENAME TO candidates")

        print("✓ Removed custom_fields column")
    else:
        print("✓ Candidates table doesn't have custom_fields column")

    conn.commit()
    conn.close()
    print("\n✅ Migration complete!")

if __name__ == '__main__':
    migrate()
