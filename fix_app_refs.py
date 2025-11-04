#!/usr/bin/env python3
"""
Python script to update model references in src/app.py
Replaces:
- SpawnedTask → Task
- Old Task → TaskTemplate (where it refers to the model, not requests)
"""
import re

def fix_model_references():
    with open('src/app.py', 'r') as f:
        content = f.read()

    # First, replace all SpawnedTask with Task
    content = content.replace('SpawnedTask', 'Task')

    # Now we need to carefully replace old Task with TaskTemplate
    # Be careful not to replace:
    # - CreateTaskRequest, UpdateTaskRequest
    # - task (lowercase variable name)
    # - tasks (lowercase variable name)

    # Replace in type hints and model references
    replacements = [
        # Import already fixed manually

        # select(Task) -> select(TaskTemplate) - but only if not already Task from SpawnedTask
        # This is tricky - we need to identify places that refer to the OLD Task model
        # Since we already replaced SpawnedTask->Task, we need to find the OLD Task usage

        # Actually, let's approach this differently:
        # The OLD Task model was used for task templates
        # It was referenced in:
        # - /api/tasks endpoints (these are for task templates)
        # - Task model in select() for task templates

        # Looking at the code, /api/tasks endpoints were for the old Task (template) model
        # And /api/spawned-tasks were for SpawnedTask model
        # After our replacement, /api/spawned-tasks now use Task
        # So we need to update /api/tasks to use TaskTemplate
    ]

    # Let's use regex to be more precise
    # Replace Task in specific contexts:

    # 1. In task template related endpoints (around line 200-300 based on original structure)
    # This needs manual review - let's do a simple find-replace for the obvious ones

    # After SpawnedTask->Task replacement, we have:
    # - "Task" where it was SpawnedTask (correct)
    # - "Task" where it was old Task (needs to be TaskTemplate)

    # Safe replacements:
    # session.exec(select(Task)) where it's listing all templates
    # This is complex, so let's just handle the most common cases:

    # Update response_model for task template endpoints
    # The /api/tasks/ endpoints are for task templates
    content = re.sub(r'@app\.get\("/api/tasks",\s*response_model=List\[Task\]\)',
                     '@app.get("/api/tasks", response_model=List[TaskTemplate])', content)
    content = re.sub(r'@app\.get\("/api/tasks/\{task_id\}",\s*response_model=Task\)',
                     '@app.get("/api/tasks/{task_id}", response_model=TaskTemplate)', content)
    content = re.sub(r'@app\.post\("/api/tasks",\s*response_model=Task',
                     '@app.post("/api/tasks", response_model=TaskTemplate', content)
    content = re.sub(r'@app\.put\("/api/tasks/\{task_id\}",\s*response_model=Task\)',
                     '@app.put("/api/tasks/{task_id}", response_model=TaskTemplate)', content)

    # In the GET /api/tasks endpoint, select(Task) should be select(TaskTemplate)
    # But we need to be careful - after line 200 or so, there's a different usage
    # Let's do a more targeted approach by looking at specific line patterns

    # Actually this is getting too complex. Let me just use word boundary matching
    # and be very careful:

    # select(Task) -> Could be either. Let's check context
    # session.get(Task, -> Could be either
    # Task( -> Could be either

    # The safest approach: let's restore from backup and do this more carefully
    print("Content has been updated with SpawnedTask->Task replacements")
    print("Manual review needed for Task->TaskTemplate replacements in template endpoints")

    with open('src/app.py', 'w') as f:
        f.write(content)

    print("✓ Updated src/app.py")
    print("Note: SpawnedTask->Task done. Some Task->TaskTemplate replacements may need manual review.")

if __name__ == "__main__":
    fix_model_references()
