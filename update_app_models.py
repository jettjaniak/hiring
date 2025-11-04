#!/usr/bin/env python3
"""
Script to update model references in app.py
"""

def update_app_models():
    with open('src/app.py', 'r') as f:
        content = f.read()

    # Step 1: Replace Task (old) with TaskTemplate
    # Be careful not to replace UpdateTaskRequest, etc.
    replacements = [
        # Import statements
        ('from src.models import Task, ', 'from src.models import TaskTemplate, '),
        ('from src.models import (', 'from src.models import (\n    TaskTemplate,'),

        # Type hints and variable usage - need to be careful with order
        # Replace whole words only
        (', Task,', ', TaskTemplate,'),
        ('Task,', 'TaskTemplate,'),
        ('(Task)', '(TaskTemplate)'),
        (': Task ', ': TaskTemplate '),
        ('= Task(', '= TaskTemplate('),
        ('.get(Task,', '.get(TaskTemplate,'),
        ('select(Task)', 'select(TaskTemplate)'),
        ('session.exec(select(Task)', 'session.exec(select(TaskTemplate)'),
    ]

    for old, new in replacements:
        content = content.replace(old, new)

    # Step 2: Replace SpawnedTask with Task
    content = content.replace('SpawnedTask', 'Task')

    # Step 3: Remove CandidateTask references
    # This is harder as we need to remove entire endpoints
    # For now, let's just do the replacements and we'll manually remove endpoints
    content = content.replace('CandidateTask', '# REMOVED: CandidateTask')

    with open('src/app.py', 'w') as f:
        f.write(content)

    print("✓ Updated src/app.py")

if __name__ == "__main__":
    update_app_models()
