#!/usr/bin/env python3
"""
Migrate task statuses from "not_started" to "todo"
"""

from sqlmodel import Session, create_engine, select
from src.models import Task

def migrate_statuses():
    # Connect to database
    engine = create_engine("sqlite:///hiring.db")

    with Session(engine) as session:
        # Find all tasks with "not_started" status
        tasks = session.exec(
            select(Task).where(Task.status == "not_started")
        ).all()

        print(f"Found {len(tasks)} tasks with 'not_started' status")

        # Update each task
        for task in tasks:
            print(f"  Updating task {task.id}: '{task.status}' → 'todo'")
            task.status = "todo"

        # Commit changes
        session.commit()
        print(f"\n✓ Successfully migrated {len(tasks)} tasks")

if __name__ == "__main__":
    migrate_statuses()
