#!/usr/bin/env python3
"""
Two-stage endpoint refactoring to avoid path conflicts:
Stage 1: /api/tasks → /api/TEMP_task-templates
Stage 2: /api/spawned-tasks → /api/tasks
Stage 3: /api/TEMP_task-templates → /api/task-templates
"""

def refactor_endpoints():
    with open('src/app.py', 'r') as f:
        content = f.read()

    print("Starting two-stage endpoint refactoring...")

    # Stage 1: /api/tasks → /api/TEMP_task-templates
    print("\nStage 1: /api/tasks → /api/TEMP_task-templates")

    # Replace all /api/tasks paths (but not /api/tasks/ to avoid partial matches)
    replacements_stage1 = [
        ('"/api/tasks"', '"/api/TEMP_task-templates"'),
        ('"/api/tasks/', '"/api/TEMP_task-templates/'),
    ]

    for old, new in replacements_stage1:
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            print(f"  Replaced {old} → {new} ({count} times)")

    # Stage 2: /api/spawned-tasks → /api/tasks
    print("\nStage 2: /api/spawned-tasks → /api/tasks")

    replacements_stage2 = [
        ('"/api/spawned-tasks"', '"/api/tasks"'),
        ('"/api/spawned-tasks/', '"/api/tasks/'),
    ]

    for old, new in replacements_stage2:
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            print(f"  Replaced {old} → {new} ({count} times)")

    # Stage 3: /api/TEMP_task-templates → /api/task-templates
    print("\nStage 3: /api/TEMP_task-templates → /api/task-templates")

    replacements_stage3 = [
        ('"/api/TEMP_task-templates"', '"/api/task-templates"'),
        ('"/api/TEMP_task-templates/', '"/api/task-templates/'),
    ]

    for old, new in replacements_stage3:
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            print(f"  Replaced {old} → {new} ({count} times)")

    # Write the result
    with open('src/app.py', 'w') as f:
        f.write(content)

    print("\n✓ Endpoint refactoring complete!")
    print("✓ Updated src/app.py")

    # Verify no TEMP_ references remain
    if 'TEMP_' in content:
        print("\n⚠ WARNING: TEMP_ references still exist!")
    else:
        print("✓ No temporary references remain")

if __name__ == "__main__":
    refactor_endpoints()
