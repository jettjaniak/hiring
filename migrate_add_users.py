#!/usr/bin/env python3
"""
Migration script to add user authentication and assignment tracking fields.

This script adds:
1. users table with User model
2. assigned_to field to tasks table
3. default_dri field to task_templates table
4. created_by and updated_by fields to all relevant tables

Run this script after updating the models.py file with the new fields.

Usage:
    python migrate_add_users.py [--data-dir PATH]

Example:
    python migrate_add_users.py
    python migrate_add_users.py --data-dir ~/.hiring-client
"""
import os
import sys
import argparse
import sqlite3
from pathlib import Path

# Get project root directory
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def migrate_database(db_path: str):
    """
    Apply migration to add user authentication and assignment tracking.

    Args:
        db_path: Path to the SQLite database file
    """
    print(f"Migrating database: {db_path}")

    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if users table already exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        if cursor.fetchone():
            print("Migration already applied: users table exists")
            conn.close()
            return True

        print("\nApplying migration...")

        # 1. Create users table
        print("  - Creating users table...")
        cursor.execute("""
            CREATE TABLE users (
                username TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL,
                full_name TEXT,
                created_at TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX idx_users_email ON users(email)")

        # 2. Add assigned_to to tasks table
        print("  - Adding assigned_to to tasks table...")
        cursor.execute("""
            ALTER TABLE tasks
            ADD COLUMN assigned_to TEXT
            REFERENCES users(username)
        """)

        # 3. Add default_dri to task_templates table
        print("  - Adding default_dri to task_templates table...")
        cursor.execute("""
            ALTER TABLE task_templates
            ADD COLUMN default_dri TEXT
            REFERENCES users(username)
        """)

        # 4. Add created_by and updated_by to candidates table
        print("  - Adding audit fields to candidates table...")
        cursor.execute("""
            ALTER TABLE candidates
            ADD COLUMN created_by TEXT
            REFERENCES users(username)
        """)
        cursor.execute("""
            ALTER TABLE candidates
            ADD COLUMN updated_by TEXT
            REFERENCES users(username)
        """)

        # 5. Add audit fields to checklists table
        print("  - Adding audit fields to checklists table...")
        cursor.execute("""
            ALTER TABLE checklists
            ADD COLUMN created_by TEXT
            REFERENCES users(username)
        """)
        cursor.execute("""
            ALTER TABLE checklists
            ADD COLUMN updated_by TEXT
            REFERENCES users(username)
        """)

        # 6. Add audit fields to candidate_checklist_states table
        print("  - Adding audit fields to candidate_checklist_states table...")
        cursor.execute("""
            ALTER TABLE candidate_checklist_states
            ADD COLUMN created_by TEXT
            REFERENCES users(username)
        """)
        cursor.execute("""
            ALTER TABLE candidate_checklist_states
            ADD COLUMN updated_by TEXT
            REFERENCES users(username)
        """)

        # 7. Add audit fields to email_templates table
        print("  - Adding audit fields to email_templates table...")
        cursor.execute("""
            ALTER TABLE email_templates
            ADD COLUMN created_by TEXT
            REFERENCES users(username)
        """)
        cursor.execute("""
            ALTER TABLE email_templates
            ADD COLUMN updated_by TEXT
            REFERENCES users(username)
        """)

        # 8. Add audit fields to task_templates table
        print("  - Adding audit fields to task_templates table...")
        cursor.execute("""
            ALTER TABLE task_templates
            ADD COLUMN created_by TEXT
            REFERENCES users(username)
        """)
        cursor.execute("""
            ALTER TABLE task_templates
            ADD COLUMN updated_by TEXT
            REFERENCES users(username)
        """)

        # 9. Add audit fields to email_template_tasks table
        print("  - Adding audit fields to email_template_tasks table...")
        cursor.execute("""
            ALTER TABLE email_template_tasks
            ADD COLUMN created_by TEXT
            REFERENCES users(username)
        """)

        # 10. Add audit fields to tasks table
        print("  - Adding audit fields to tasks table...")
        cursor.execute("""
            ALTER TABLE tasks
            ADD COLUMN created_by TEXT
            REFERENCES users(username)
        """)
        cursor.execute("""
            ALTER TABLE tasks
            ADD COLUMN updated_by TEXT
            REFERENCES users(username)
        """)

        # 11. Add audit fields to task_candidate_links table
        print("  - Adding audit fields to task_candidate_links table...")
        cursor.execute("""
            ALTER TABLE task_candidate_links
            ADD COLUMN created_by TEXT
            REFERENCES users(username)
        """)

        # Commit all changes
        conn.commit()
        print("\nMigration completed successfully!")
        print("\nNext steps:")
        print("  1. You can now register users via /api/auth/register")
        print("  2. Assign tasks to users using the assigned_to field")
        print("  3. Set default_dri on task templates")
        print("  4. All create/update operations will track created_by/updated_by")

        return True

    except sqlite3.Error as e:
        print(f"\nError during migration: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def main():
    """Main entry point for migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate database to add user authentication and assignment tracking"
    )
    parser.add_argument(
        '--data-dir',
        default=None,
        help='Data directory for client files (default: ~/.hiring-client)'
    )
    args = parser.parse_args()

    # Determine database path
    data_dir = args.data_dir or os.path.expanduser('~/.hiring-client')
    db_path = os.path.join(data_dir, 'hiring.db')

    print("=" * 70)
    print("User Authentication & Assignment Migration")
    print("=" * 70)

    # Run migration
    success = migrate_database(db_path)

    if success:
        print("\n" + "=" * 70)
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("Migration failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
