#!/usr/bin/env python3
"""
Migration script to add the 'variables' column to email_templates table.
Run this once to update existing databases.
"""

import sqlite3
import sys
import os
from pathlib import Path

def migrate_database(db_path):
    """Add variables column to email_templates table if it doesn't exist"""

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(email_templates)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'variables' in columns:
            print(f"✓ Column 'variables' already exists in {db_path}")
            return True

        # Add the column
        cursor.execute("ALTER TABLE email_templates ADD COLUMN variables TEXT")
        conn.commit()
        print(f"✓ Added 'variables' column to email_templates table in {db_path}")
        return True

    except sqlite3.Error as e:
        print(f"✗ Error migrating {db_path}: {e}")
        return False

    finally:
        conn.close()

def main():
    """Run migration on all common database locations"""

    # Default database location
    default_db = Path.home() / ".hiring-client" / "hiring.db"

    # Alternative database location
    alt_db = Path.home() / ".hiring-client-2" / "hiring.db"

    # Local database
    local_db = Path("hiring.db")

    databases = []

    # Check which databases exist
    if default_db.exists():
        databases.append(default_db)
    if alt_db.exists():
        databases.append(alt_db)
    if local_db.exists():
        databases.append(local_db)

    if not databases:
        print("No databases found to migrate.")
        print(f"Checked locations:")
        print(f"  - {default_db}")
        print(f"  - {alt_db}")
        print(f"  - {local_db}")
        return 1

    print(f"Found {len(databases)} database(s) to migrate:")
    for db in databases:
        print(f"  - {db}")
    print()

    # Migrate each database
    success = True
    for db in databases:
        if not migrate_database(db):
            success = False

    if success:
        print("\n✓ All migrations completed successfully!")
        return 0
    else:
        print("\n✗ Some migrations failed. Check the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
