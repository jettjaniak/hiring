#!/usr/bin/env python3
"""
Migration script to convert CandidateTask to SpawnedTask model
Creates new spawned_tasks and task_candidate_links tables and migrates data
"""
import sys
import os
import sqlite3
from datetime import datetime
from pathlib import Path


def migrate_to_spawnable_tasks(db_path: str):
    """Migrate from CandidateTask to SpawnedTask + TaskCandidateLink"""

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        sys.exit(1)

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        print("\n" + "=" * 60)
        print("Stage 1: Creating New Tables")
        print("=" * 60)

        # Create spawned_tasks table
        print("\nCreating spawned_tasks table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spawned_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'todo',
                template_id TEXT,
                workflow_id TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES tasks (task_id) ON DELETE SET NULL
            )
        """)
        print("✓ spawned_tasks table created")

        # Create task_candidate_links table
        print("\nCreating task_candidate_links table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_candidate_links (
                task_id INTEGER NOT NULL,
                candidate_email TEXT NOT NULL,
                created_at TIMESTAMP,
                PRIMARY KEY (task_id, candidate_email),
                FOREIGN KEY (task_id) REFERENCES spawned_tasks (id) ON DELETE CASCADE,
                FOREIGN KEY (candidate_email) REFERENCES candidates (email) ON DELETE CASCADE
            )
        """)
        print("✓ task_candidate_links table created")

        print("\n" + "=" * 60)
        print("Stage 2: Migrating Data from candidate_tasks")
        print("=" * 60)

        # Get all candidate tasks
        cursor.execute("""
            SELECT candidate_id, task_identifier, status, created_at, updated_at
            FROM candidate_tasks
            ORDER BY candidate_id, task_identifier
        """)
        candidate_tasks = cursor.fetchall()

        print(f"\nFound {len(candidate_tasks)} candidate task records to migrate")

        # Status mapping
        status_map = {
            'not_started': 'todo',
            'in_progress': 'in_progress',
            'completed': 'done',
            'na': 'done'
        }

        migrated_count = 0
        error_count = 0
        now = datetime.now().isoformat()

        # Group by task_identifier to create unique spawned tasks
        # Each task_identifier should become one spawned task per candidate
        for row in candidate_tasks:
            candidate_id = row['candidate_id']
            task_identifier = row['task_identifier']
            old_status = row['status'] or 'not_started'
            new_status = status_map.get(old_status, 'todo')
            created_at = row['created_at'] or now
            updated_at = row['updated_at'] or now

            try:
                # Get task details from tasks table
                cursor.execute("""
                    SELECT task_id, name, description
                    FROM tasks
                    WHERE task_id = ?
                """, (task_identifier,))
                task_row = cursor.fetchone()

                if task_row:
                    title = task_row['name']
                    description = task_row['description']
                    template_id = task_row['task_id']
                else:
                    # Task not in tasks table, use identifier as title
                    title = task_identifier
                    description = None
                    template_id = None
                    print(f"  WARNING: Task {task_identifier} not found in tasks table")

                # Get candidate's workflow_id
                cursor.execute("""
                    SELECT workflow_id
                    FROM candidates
                    WHERE email = ?
                """, (candidate_id,))
                candidate_row = cursor.fetchone()
                workflow_id = candidate_row['workflow_id'] if candidate_row else None

                # Create spawned task
                cursor.execute("""
                    INSERT INTO spawned_tasks (title, description, status, template_id, workflow_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (title, description, new_status, template_id, workflow_id, created_at, updated_at))

                spawned_task_id = cursor.lastrowid

                # Create task-candidate link
                cursor.execute("""
                    INSERT INTO task_candidate_links (task_id, candidate_email, created_at)
                    VALUES (?, ?, ?)
                """, (spawned_task_id, candidate_id, created_at))

                migrated_count += 1
                print(f"  ✓ Migrated: {candidate_id} / {task_identifier} → SpawnedTask #{spawned_task_id} (status: {old_status} → {new_status})")

            except Exception as e:
                error_count += 1
                print(f"  ✗ Error migrating {candidate_id}/{task_identifier}: {e}")

        # Commit all changes
        conn.commit()

        print("\n" + "=" * 60)
        print("Migration Summary")
        print("=" * 60)
        print(f"  Total candidate tasks: {len(candidate_tasks)}")
        print(f"  Successfully migrated: {migrated_count}")
        print(f"  Errors: {error_count}")
        print()
        print("✓ Migration completed successfully!")
        print()
        print("NOTE: The candidate_tasks table has NOT been removed.")
        print("      It will be removed in Stage 7 of the implementation.")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate from CandidateTask to SpawnedTask model"
    )
    parser.add_argument(
        "--db",
        default=os.path.expanduser("~/.hiring-client/hiring.db"),
        help="Path to database file (default: ~/.hiring-client/hiring.db)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Spawnable Tasks Migration")
    print("=" * 60)
    print(f"Database: {args.db}")
    print()

    migrate_to_spawnable_tasks(args.db)
