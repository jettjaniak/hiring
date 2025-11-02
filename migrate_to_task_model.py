#!/usr/bin/env python3
"""
Migration script to extract tasks from workflow YAMLs and populate Task table
Also updates workflow YAMLs to use new format (task_id + dependencies only)
"""
import sys
import os
import sqlite3
import shutil
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List


def migrate_workflows(db_path: str, workflows_dir: str, update_yamls: bool = False):
    """Migrate workflows to use Task model"""

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        print("Creating new database...")

    # Check if workflows directory exists
    workflows_path = Path(workflows_dir)
    if not workflows_path.exists():
        print(f"Workflows directory not found: {workflows_dir}")
        sys.exit(1)

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Create tasks table if it doesn't exist
        print("\nCreating tasks table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)

        # Load all workflow YAML files
        print(f"\nLoading workflows from: {workflows_dir}")
        workflow_files = list(workflows_path.glob('*.yaml'))
        print(f"Found {len(workflow_files)} workflow files")

        # Extract all unique tasks
        tasks_map: Dict[str, Dict[str, str]] = {}  # task_id -> {name, description}

        for yaml_file in workflow_files:
            print(f"\n  Processing: {yaml_file.name}")
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)

            workflow_id = data.get('id', 'unknown')
            tasks = data.get('tasks', [])
            print(f"    Workflow: {workflow_id}")
            print(f"    Tasks: {len(tasks)}")

            for task in tasks:
                # Support both old format (identifier) and new format (task_id)
                task_id = task.get('task_id') or task.get('identifier')

                if not task_id:
                    print(f"    WARNING: Task without identifier/task_id in {yaml_file.name}")
                    continue

                # Only store if we have name (old format)
                # New format tasks are already in the database
                if 'name' in task:
                    name = task['name']
                    description = task.get('description', '')

                    # If task already exists, keep the first occurrence
                    if task_id not in tasks_map:
                        tasks_map[task_id] = {
                            'name': name,
                            'description': description
                        }
                        print(f"      - {task_id}: {name}")
                    else:
                        # Task exists, check if details match
                        existing = tasks_map[task_id]
                        if existing['name'] != name:
                            print(f"      ! WARNING: Task {task_id} has different names:")
                            print(f"          First: {existing['name']}")
                            print(f"          Here:  {name}")
                        if existing['description'] != description and description:
                            print(f"      ! WARNING: Task {task_id} has different descriptions")

        print(f"\n\nExtracted {len(tasks_map)} unique tasks")

        # Insert tasks into database
        print("\nInserting tasks into database...")
        now = datetime.now().isoformat()
        inserted_count = 0
        skipped_count = 0

        for task_id, task_data in tasks_map.items():
            # Check if task already exists
            cursor.execute("SELECT task_id FROM tasks WHERE task_id = ?", (task_id,))
            existing = cursor.fetchone()

            if existing:
                print(f"  Skipping {task_id} (already exists)")
                skipped_count += 1
            else:
                cursor.execute("""
                    INSERT INTO tasks (task_id, name, description, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    task_id,
                    task_data['name'],
                    task_data['description'],
                    now,
                    now
                ))
                print(f"  Inserted: {task_id}")
                inserted_count += 1

        # Commit changes
        conn.commit()
        print(f"\n✓ Inserted {inserted_count} tasks (skipped {skipped_count} existing)")

        # Optionally update YAML files to new format
        if update_yamls:
            print("\n" + "=" * 60)
            print("Updating workflow YAML files to new format...")
            print("=" * 60)

            for yaml_file in workflow_files:
                # Create backup
                backup_path = yaml_file.with_suffix('.yaml.backup')
                shutil.copy2(yaml_file, backup_path)
                print(f"\n  Backup: {backup_path.name}")

                # Load YAML
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f)

                # Convert tasks to new format
                new_tasks = []
                for task in data.get('tasks', []):
                    task_id = task.get('task_id') or task.get('identifier')
                    dependencies = task.get('dependencies', [])

                    new_task = {
                        'task_id': task_id,
                        'dependencies': dependencies
                    }
                    new_tasks.append(new_task)

                # Update data
                data['tasks'] = new_tasks

                # Write back to file
                with open(yaml_file, 'w') as f:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False)

                print(f"  Updated: {yaml_file.name}")
                print(f"    Converted {len(new_tasks)} tasks to new format")

            print("\n✓ All workflow YAML files updated")
            print("  Backups saved with .backup extension")

        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        print(f"\nSummary:")
        print(f"  - Tasks extracted: {len(tasks_map)}")
        print(f"  - Tasks inserted: {inserted_count}")
        print(f"  - Tasks skipped: {skipped_count}")
        print(f"  - Workflows processed: {len(workflow_files)}")
        if update_yamls:
            print(f"  - YAMLs updated: {len(workflow_files)}")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrate workflows to use Task model"
    )
    parser.add_argument(
        "--db",
        default=os.path.expanduser("~/.hiring-client/hiring.db"),
        help="Path to database file (default: ~/.hiring-client/hiring.db)"
    )
    parser.add_argument(
        "--workflows",
        default="workflows",
        help="Path to workflows directory (default: workflows)"
    )
    parser.add_argument(
        "--update-yamls",
        action="store_true",
        help="Update workflow YAML files to new format (creates backups)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Workflow Task Migration")
    print("=" * 60)
    print(f"Database: {args.db}")
    print(f"Workflows: {args.workflows}")
    print(f"Update YAMLs: {args.update_yamls}")
    print()

    migrate_workflows(args.db, args.workflows, args.update_yamls)
