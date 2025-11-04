#!/usr/bin/env python3
"""
Migration script to rename models and migrate CandidateTask data
"""
import sqlite3
import sys
from pathlib import Path

def migrate_database(db_path):
    print(f"Migrating database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Step 1: Rename tasks table to task_templates
        print("Step 1: Renaming tasks → task_templates...")
        cursor.execute("ALTER TABLE tasks RENAME TO task_templates")

        # Step 2: Rename spawned_tasks table to tasks
        print("Step 2: Renaming spawned_tasks → tasks...")
        cursor.execute("ALTER TABLE spawned_tasks RENAME TO tasks")

        # Step 3: Rename task_candidate_links columns (foreign key references old table names)
        print("Step 3: Updating task_candidate_links...")
        # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
        cursor.execute("""
            CREATE TABLE task_candidate_links_new (
                task_id INTEGER NOT NULL,
                candidate_email TEXT NOT NULL,
                created_at TIMESTAMP,
                PRIMARY KEY (task_id, candidate_email),
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (candidate_email) REFERENCES candidates(email) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            INSERT INTO task_candidate_links_new
            SELECT * FROM task_candidate_links
        """)
        cursor.execute("DROP TABLE task_candidate_links")
        cursor.execute("ALTER TABLE task_candidate_links_new RENAME TO task_candidate_links")

        # Step 4: Update checklists table - rename task_id to task_template_id
        print("Step 4: Updating checklists...")
        cursor.execute("""
            CREATE TABLE checklists_new (
                id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                task_template_id TEXT NOT NULL,
                items TEXT NOT NULL,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                PRIMARY KEY (id),
                UNIQUE (task_template_id),
                FOREIGN KEY (task_template_id) REFERENCES task_templates(task_id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            INSERT INTO checklists_new
            SELECT id, name, description, task_id, items, created_at, updated_at
            FROM checklists
        """)
        cursor.execute("DROP TABLE checklists")
        cursor.execute("ALTER TABLE checklists_new RENAME TO checklists")

        # Step 5: Update email_template_tasks table - rename task_id to task_template_id
        print("Step 5: Updating email_template_tasks...")
        cursor.execute("""
            CREATE TABLE email_template_tasks_new (
                email_template_id TEXT NOT NULL,
                task_template_id TEXT NOT NULL,
                created_at TIMESTAMP,
                PRIMARY KEY (email_template_id, task_template_id),
                FOREIGN KEY (email_template_id) REFERENCES email_templates(id) ON DELETE CASCADE,
                FOREIGN KEY (task_template_id) REFERENCES task_templates(task_id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            INSERT INTO email_template_tasks_new
            SELECT * FROM email_template_tasks
        """)
        cursor.execute("DROP TABLE email_template_tasks")
        cursor.execute("ALTER TABLE email_template_tasks_new RENAME TO email_template_tasks")

        # Step 6: Migrate CandidateTask data to Task + TaskCandidateLink
        print("Step 6: Migrating candidate_tasks to tasks + task_candidate_links...")

        # Check if candidate_tasks table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='candidate_tasks'
        """)
        if cursor.fetchone():
            # Get all CandidateTask records
            cursor.execute("""
                SELECT candidate_id, task_identifier, status, created_at, updated_at
                FROM candidate_tasks
            """)
            candidate_tasks = cursor.fetchall()

            print(f"   Found {len(candidate_tasks)} candidate task records to migrate")

            for candidate_id, task_identifier, status, created_at, updated_at in candidate_tasks:
                # Map old status to new status
                status_map = {
                    'not_started': 'todo',
                    'in_progress': 'in_progress',
                    'completed': 'done',
                    'na': 'done',
                    None: 'todo'
                }
                new_status = status_map.get(status, 'todo')

                # Get task template info if it exists
                cursor.execute("""
                    SELECT name, description FROM task_templates
                    WHERE task_id = ?
                """, (task_identifier,))
                template_info = cursor.fetchone()

                if template_info:
                    title = template_info[0]
                    description = template_info[1]
                    template_id = task_identifier

                    # Get workflow_id from candidate
                    cursor.execute("""
                        SELECT workflow_id FROM candidates WHERE email = ?
                    """, (candidate_id,))
                    workflow_result = cursor.fetchone()
                    workflow_id = workflow_result[0] if workflow_result else None

                    # Create Task instance
                    cursor.execute("""
                        INSERT INTO tasks (title, description, status, template_id, workflow_id, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (title, description, new_status, template_id, workflow_id, created_at, updated_at))

                    task_id = cursor.lastrowid

                    # Create TaskCandidateLink
                    cursor.execute("""
                        INSERT INTO task_candidate_links (task_id, candidate_email, created_at)
                        VALUES (?, ?, ?)
                    """, (task_id, candidate_id, created_at))

                    print(f"   Migrated task '{title}' for candidate {candidate_id}")

            # Drop candidate_tasks table
            print("Step 7: Dropping candidate_tasks table...")
            cursor.execute("DROP TABLE candidate_tasks")
        else:
            print("   No candidate_tasks table found, skipping migration")

        conn.commit()
        print("\n✓ Migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n✗ Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    # Default database path
    db_path = Path.home() / ".hiring-client" / "hiring.db"

    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        print("Creating new database with new schema...")
    else:
        # Backup database first
        backup_path = db_path.with_suffix('.db.backup')
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"Backup created: {backup_path}")

        migrate_database(str(db_path))
