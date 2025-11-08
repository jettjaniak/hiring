#!/usr/bin/env python3
"""
Migration: Add task condition fields

Adds completion_condition and display_condition fields to task_templates table,
and test fields to candidates table for demonstration.

Run this script from the project root:
    python migrate_add_conditions.py --data-dir ~/.hiring-client
"""
import sqlite3
import argparse
from datetime import date, timedelta


def migrate(db_path: str):
    """Run the migration"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add columns to task_templates
        print("Adding columns to task_templates table...")
        cursor.execute("""
            ALTER TABLE task_templates
            ADD COLUMN completion_condition TEXT
        """)
        cursor.execute("""
            ALTER TABLE task_templates
            ADD COLUMN display_condition TEXT
        """)

        # Add test fields to candidates table
        print("Adding test fields to candidates table...")
        try:
            cursor.execute("""
                ALTER TABLE candidates
                ADD COLUMN work_permit_verified INTEGER DEFAULT 0
            """)
        except sqlite3.OperationalError:
            print("  work_permit_verified column already exists, skipping")

        try:
            cursor.execute("""
                ALTER TABLE candidates
                ADD COLUMN background_check_date TEXT
            """)
        except sqlite3.OperationalError:
            print("  background_check_date column already exists, skipping")

        try:
            cursor.execute("""
                ALTER TABLE candidates
                ADD COLUMN requires_visa INTEGER DEFAULT 0
            """)
        except sqlite3.OperationalError:
            print("  requires_visa column already exists, skipping")

        try:
            cursor.execute("""
                ALTER TABLE candidates
                ADD COLUMN visa_expiry TEXT
            """)
        except sqlite3.OperationalError:
            print("  visa_expiry column already exists, skipping")

        conn.commit()

        # Add test data
        print("\nAdding test data...")

        # Update some candidates with test data
        test_date = (date.today() - timedelta(days=60)).isoformat()
        future_date = (date.today() + timedelta(days=365)).isoformat()

        # Get one candidate to update with test data
        cursor.execute("SELECT email FROM candidates LIMIT 1")
        result = cursor.fetchone()
        if result:
            cursor.execute("""
                UPDATE candidates
                SET work_permit_verified = 1,
                    background_check_date = ?,
                    requires_visa = 0
                WHERE email = ?
            """, (test_date, result[0]))

        # Get another candidate for visa test data
        cursor.execute("""
            SELECT email FROM candidates
            WHERE email != ? OR ? IS NULL
            LIMIT 1
        """, (result[0] if result else None, result[0] if result else None))
        result2 = cursor.fetchone()
        if result2:
            cursor.execute("""
                UPDATE candidates
                SET work_permit_verified = 0,
                    requires_visa = 1,
                    visa_expiry = ?
                WHERE email = ?
            """, (future_date, result2[0]))

        # Update a task template with example conditions
        cursor.execute("""
            SELECT task_id FROM task_templates
            WHERE task_id LIKE '%interview%'
            LIMIT 1
        """)
        task1 = cursor.fetchone()
        if task1:
            cursor.execute("""
                UPDATE task_templates
                SET completion_condition = 'work_permit_verified',
                    display_condition = ''
                WHERE task_id = ?
            """, (task1[0],))

        cursor.execute("""
            SELECT task_id FROM task_templates
            WHERE task_id LIKE '%background%' OR task_id LIKE '%check%'
            LIMIT 1
        """)
        task2 = cursor.fetchone()
        if task2:
            cursor.execute("""
                UPDATE task_templates
                SET completion_condition = 'background_check_date and background_check_date >= days_ago(90)',
                    display_condition = 'work_permit_verified'
                WHERE task_id = ?
            """, (task2[0],))

        conn.commit()

        print("\nMigration completed successfully!")
        print("\nTest conditions added:")
        print("  - Some candidates have work_permit_verified=True, background_check dates")
        print("  - Some candidates have requires_visa=True with visa_expiry dates")
        print("  - Some tasks have completion/display conditions")

    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print(f"Column already exists: {e}")
            print("Migration may have been run before. Continuing...")
        else:
            raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate database to add condition fields")
    parser.add_argument("--data-dir", default="~/.hiring-client", help="Data directory")
    args = parser.parse_args()

    import os
    data_dir = os.path.expanduser(args.data_dir)
    db_path = os.path.join(data_dir, "hiring.db")

    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        print(f"Make sure the server has been run at least once to create the database.")
        exit(1)

    print(f"Migrating database at: {db_path}\n")
    migrate(db_path)
