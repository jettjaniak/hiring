#!/usr/bin/env python3
"""
Migration script to change Candidate primary key from id to email
Handles duplicate emails by appending numbers to make them unique
"""
import sys
import os
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

def migrate_database(db_path: str):
    """Migrate database to use email as primary key"""

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        print("Nothing to migrate.")
        return

    # Create backup
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Read all existing candidates
        print("\nReading existing candidates...")
        cursor.execute("SELECT * FROM candidates")
        candidates = cursor.fetchall()
        print(f"Found {len(candidates)} candidates")

        # Read all existing candidate tasks
        cursor.execute("SELECT * FROM candidate_tasks")
        tasks = cursor.fetchall()
        print(f"Found {len(tasks)} candidate tasks")

        # Read all existing action states
        cursor.execute("SELECT * FROM action_states")
        action_states = cursor.fetchall()
        print(f"Found {len(action_states)} action states")

        # Handle duplicate emails
        print("\nChecking for duplicate emails...")
        email_counts = {}
        email_to_id = {}  # Map email -> list of old IDs

        for candidate in candidates:
            email = candidate['email']
            old_id = candidate['id']

            if email:
                if email not in email_counts:
                    email_counts[email] = 0
                    email_to_id[email] = []
                email_counts[email] += 1
                email_to_id[email].append(old_id)

        # Find duplicates
        duplicates = {email: count for email, count in email_counts.items() if count > 1}

        if duplicates:
            print(f"Found {len(duplicates)} duplicate emails:")
            for email, count in duplicates.items():
                print(f"  - {email}: {count} occurrences")
        else:
            print("No duplicate emails found")

        # Create mapping from old ID to new email (with numbers appended for duplicates)
        id_to_new_email = {}
        email_usage = {}  # Track which number we're on for each email

        for candidate in candidates:
            old_id = candidate['id']
            email = candidate['email']

            if not email:
                # Generate email for candidates without one
                email = f"candidate-{old_id}@unknown.com"
                print(f"  Candidate {old_id} has no email, using: {email}")

            # If this email has duplicates, append a number
            if email in duplicates:
                if email not in email_usage:
                    email_usage[email] = 0
                else:
                    email_usage[email] += 1

                if email_usage[email] > 0:
                    # Append number to make unique
                    base_email = email.split('@')
                    if len(base_email) == 2:
                        new_email = f"{base_email[0]}-{email_usage[email]}@{base_email[1]}"
                    else:
                        new_email = f"{email}-{email_usage[email]}"
                    print(f"  Renaming duplicate: {email} -> {new_email}")
                    email = new_email

            id_to_new_email[old_id] = email

        # Drop existing tables and recreate with new schema
        print("\nRecreating database schema...")
        cursor.execute("DROP TABLE IF EXISTS candidate_tasks")
        cursor.execute("DROP TABLE IF EXISTS action_states")
        cursor.execute("DROP TABLE IF EXISTS candidates")

        # Create new candidates table with email as PK
        cursor.execute("""
            CREATE TABLE candidates (
                email TEXT PRIMARY KEY NOT NULL,
                workflow_id TEXT,
                name TEXT,
                phone TEXT,
                resume_url TEXT,
                notes TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)

        # Create new candidate_tasks table
        cursor.execute("""
            CREATE TABLE candidate_tasks (
                candidate_id TEXT NOT NULL,
                task_identifier TEXT NOT NULL,
                status TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                PRIMARY KEY (candidate_id, task_identifier),
                FOREIGN KEY (candidate_id) REFERENCES candidates(email) ON DELETE CASCADE
            )
        """)

        # Create new action_states table
        cursor.execute("""
            CREATE TABLE action_states (
                candidate_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                state TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                PRIMARY KEY (candidate_id, action_id),
                FOREIGN KEY (candidate_id) REFERENCES candidates(email) ON DELETE CASCADE
            )
        """)

        # Migrate candidates
        print(f"\nMigrating {len(candidates)} candidates...")
        for candidate in candidates:
            old_id = candidate['id']
            new_email = id_to_new_email[old_id]

            cursor.execute("""
                INSERT INTO candidates (email, workflow_id, name, phone, resume_url, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_email,
                candidate['workflow_id'],
                candidate['name'],
                candidate['phone'],
                candidate['resume_url'],
                candidate['notes'],
                candidate['created_at'],
                candidate['updated_at']
            ))

        # Migrate candidate tasks
        print(f"Migrating {len(tasks)} candidate tasks...")
        for task in tasks:
            old_candidate_id = task['candidate_id']
            new_email = id_to_new_email.get(old_candidate_id)

            if new_email:
                cursor.execute("""
                    INSERT INTO candidate_tasks (candidate_id, task_identifier, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    new_email,
                    task['task_identifier'],
                    task['status'],
                    task['created_at'],
                    task['updated_at']
                ))

        # Migrate action states
        print(f"Migrating {len(action_states)} action states...")
        for action_state in action_states:
            old_candidate_id = action_state['candidate_id']
            new_email = id_to_new_email.get(old_candidate_id)

            if new_email:
                cursor.execute("""
                    INSERT INTO action_states (candidate_id, action_id, state, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    new_email,
                    action_state['action_id'],
                    action_state['state'],
                    action_state['created_at'],
                    action_state['updated_at']
                ))

        # Commit changes
        conn.commit()
        print("\n✓ Migration completed successfully!")
        print(f"Backup saved to: {backup_path}")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        print(f"Restoring from backup: {backup_path}")
        conn.close()
        shutil.copy2(backup_path, db_path)
        print("Database restored")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    # Default database location
    default_db = os.path.expanduser("~/.hiring-client/hiring.db")

    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = default_db

    print("=" * 60)
    print("Candidate Email Primary Key Migration")
    print("=" * 60)
    print(f"Database: {db_path}")
    print()

    migrate_database(db_path)
