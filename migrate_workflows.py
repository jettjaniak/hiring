#!/usr/bin/env python3
"""
Migration script to:
1. Read all workflow YAMLs
2. Create TaskTemplate records in DB for all tasks
3. Update YAMLs to remove names/descriptions (keep only task_id and dependencies)
"""
import yaml
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from database import Database
from models import TaskTemplate
from sqlmodel import select

def migrate_workflows():
    """Migrate workflow definitions to use DB-backed TaskTemplates"""

    workflows_dir = Path('workflows')
    if not workflows_dir.exists():
        print(f"Error: {workflows_dir} not found")
        return

    # Initialize database with the correct path
    from pathlib import Path as PathLib
    db_path = PathLib.home() / '.hiring-client' / 'hiring.db'
    db = Database(str(db_path))
    session = db.get_session().__enter__()
    
    tasks_created = 0
    tasks_updated = 0
    tasks_skipped = 0
    
    # Process each workflow
    for yaml_file in workflows_dir.glob('*.yaml'):
        print(f"\nProcessing {yaml_file.name}...")
        
        with open(yaml_file, 'r') as f:
            data = yaml.safe_load(f)
        
        if 'tasks' not in data:
            print(f"  No tasks found in {yaml_file.name}")
            continue
        
        # Extract task definitions and create/update TaskTemplates
        for task in data['tasks']:
            if 'task_id' in task:
                # Already migrated format
                task_id = task['task_id']
                print(f"  Task {task_id}: already using task_id format")
                tasks_skipped += 1
                continue
            
            # Old format with identifier, name, description
            task_id = task.get('identifier')
            name = task.get('name', task_id)
            description = task.get('description', '')
            
            if not task_id:
                print(f"  WARNING: Task missing identifier: {task}")
                continue
            
            # Check if TaskTemplate exists
            existing = session.exec(
                select(TaskTemplate).where(TaskTemplate.task_id == task_id)
            ).first()
            
            if existing:
                # Update if name/description changed
                if existing.name != name or existing.description != description:
                    existing.name = name
                    existing.description = description
                    session.add(existing)
                    print(f"  Task {task_id}: updated")
                    tasks_updated += 1
                else:
                    print(f"  Task {task_id}: already exists, no changes")
                    tasks_skipped += 1
            else:
                # Create new TaskTemplate
                task_template = TaskTemplate(
                    task_id=task_id,
                    name=name,
                    description=description
                )
                session.add(task_template)
                print(f"  Task {task_id}: created")
                tasks_created += 1
        
        session.commit()
        
        # Update YAML file to use task_id format
        updated_tasks = []
        for task in data['tasks']:
            if 'task_id' in task:
                # Already in new format
                updated_tasks.append(task)
            else:
                # Convert to new format
                updated_task = {
                    'task_id': task['identifier'],
                    'dependencies': task.get('dependencies', [])
                }
                updated_tasks.append(updated_task)
        
        data['tasks'] = updated_tasks
        
        # Write updated YAML
        with open(yaml_file, 'w') as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
        print(f"  Updated {yaml_file.name} to use task_id format")
    
    session.close()
    
    print(f"\n=== Migration Summary ===")
    print(f"TaskTemplates created: {tasks_created}")
    print(f"TaskTemplates updated: {tasks_updated}")
    print(f"TaskTemplates skipped: {tasks_skipped}")
    print(f"Total: {tasks_created + tasks_updated + tasks_skipped}")

if __name__ == '__main__':
    migrate_workflows()
