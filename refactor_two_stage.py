#!/usr/bin/env python3
"""
Two-stage model refactoring to avoid name conflicts:
Stage 1: Task → TEMP_TaskTemplate
Stage 2: SpawnedTask → Task
Stage 3: TEMP_TaskTemplate → TaskTemplate
"""

def refactor_models():
    with open('src/app.py', 'r') as f:
        content = f.read()

    print("Starting two-stage model refactoring...")

    # Stage 1: Rename Task → TEMP_TaskTemplate (to avoid conflicts)
    # We need to be careful not to replace:
    # - UpdateTaskRequest, CreateTaskRequest, etc. (these have "Task" but aren't the model)
    # - SpawnedTask (handled separately)
    # - CandidateTask (left alone for now)
    # - task, tasks (lowercase variables)

    print("\nStage 1: Task → TEMP_TaskTemplate")

    # Replace Task in imports (but not SpawnedTask, CandidateTask, or *TaskRequest)
    content = content.replace('from src.models import Candidate, EmailTemplate, Task,',
                            'from src.models import Candidate, EmailTemplate, TEMP_TaskTemplate,')

    # Replace standalone Task references with word boundaries
    # Using simple but effective replacements:
    replacements_stage1 = [
        ('select(Task)', 'select(TEMP_TaskTemplate)'),
        ('List[Task]', 'List[TEMP_TaskTemplate]'),
        ('response_model=Task', 'response_model=TEMP_TaskTemplate'),
        ('.get(Task,', '.get(TEMP_TaskTemplate,'),
        ('= Task(', '= TEMP_TaskTemplate('),
        (': Task ', ': TEMP_TaskTemplate '),
        (': Task)', ': TEMP_TaskTemplate)'),
        (' Task ', ' TEMP_TaskTemplate '),
        (' Task,', ' TEMP_TaskTemplate,'),
        (' Task\n', ' TEMP_TaskTemplate\n'),
    ]

    for old, new in replacements_stage1:
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            print(f"  Replaced '{old}' → '{new}' ({count} times)")

    # Stage 2: Rename SpawnedTask → Task
    print("\nStage 2: SpawnedTask → Task")
    spawned_count = content.count('SpawnedTask')
    content = content.replace('SpawnedTask', 'Task')
    print(f"  Replaced 'SpawnedTask' → 'Task' ({spawned_count} times)")

    # Stage 3: Rename TEMP_TaskTemplate → TaskTemplate
    print("\nStage 3: TEMP_TaskTemplate → TaskTemplate")
    temp_count = content.count('TEMP_TaskTemplate')
    content = content.replace('TEMP_TaskTemplate', 'TaskTemplate')
    print(f"  Replaced 'TEMP_TaskTemplate' → 'TaskTemplate' ({temp_count} times)")

    # Write the result
    with open('src/app.py', 'w') as f:
        f.write(content)

    print("\n✓ Model refactoring complete!")
    print("✓ Updated src/app.py")

    # Verify no TEMP_ references remain
    if 'TEMP_' in content:
        print("\n⚠ WARNING: TEMP_ references still exist!")
    else:
        print("✓ No temporary references remain")

if __name__ == "__main__":
    refactor_models()
