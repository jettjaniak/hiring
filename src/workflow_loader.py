"""
Load and manage workflow definitions from YAML files
"""
import yaml
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING
from sqlmodel import Session, select
from .models import Task

if TYPE_CHECKING:
    from .database import Database


class WorkflowDefinition:
    """Represents a workflow definition"""

    def __init__(self, data: dict, db: 'Database'):
        self.id = data['id']
        self.name = data['name']
        self.description = data.get('description', '')

        # Create a session for task validation
        session = db.get_session().__enter__()

        try:
            self.tasks = [TaskDefinition(t, session) for t in data.get('tasks', [])]
        finally:
            session.close()

    def get_task_identifiers(self) -> List[str]:
        """Get list of all task identifiers in this workflow"""
        return [task.identifier for task in self.tasks]

    def get_task(self, identifier: str):
        """Get task by identifier"""
        for task in self.tasks:
            if task.identifier == identifier:
                return task
        return None


class TaskDefinition:
    """Represents a task definition loaded from database"""

    def __init__(self, data: dict, session: Optional[Session] = None):
        # Support both old format (with name/description) and new format (task_id only)
        if 'task_id' in data:
            # New format: load from database
            self.identifier = data['task_id']
            if session:
                task = session.exec(select(Task).where(Task.task_id == self.identifier)).first()
                if task:
                    self.name = task.name
                    self.description = task.description or ''
                else:
                    raise ValueError(f"Task '{self.identifier}' not found in database")
            else:
                # No session provided, use placeholder values
                self.name = self.identifier
                self.description = ''
        else:
            # Old format: use data from YAML
            self.identifier = data['identifier']
            self.name = data['name']
            self.description = data.get('description', '')

        self.dependencies = data.get('dependencies', [])


class WorkflowLoader:
    """Loads workflow definitions from YAML files"""

    def __init__(self, workflows_dir: str = None, db: 'Database' = None):
        if workflows_dir is None:
            # Default to workflows/ directory next to this file
            workflows_dir = Path(__file__).parent / 'workflows'
        self.workflows_dir = Path(workflows_dir)
        self.db = db
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self._load_workflows()

    def _load_workflows(self):
        """Load all workflow YAML files"""
        if not self.workflows_dir.exists():
            print(f"Warning: Workflows directory not found: {self.workflows_dir}")
            return

        for yaml_file in self.workflows_dir.glob('*.yaml'):
            try:
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f)
                    workflow = WorkflowDefinition(data, self.db)
                    self.workflows[workflow.id] = workflow
            except Exception as e:
                print(f"Error loading workflow {yaml_file}: {e}")

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition:
        """Get workflow by ID"""
        return self.workflows.get(workflow_id)

    def get_all_workflows(self) -> Dict[str, WorkflowDefinition]:
        """Get all workflows"""
        return self.workflows

    def get_workflow_ids(self) -> List[str]:
        """Get list of all workflow IDs"""
        return list(self.workflows.keys())

    def get_all_task_identifiers(self) -> List[str]:
        """Get list of all task identifiers across all workflows"""
        identifiers = set()
        for workflow in self.workflows.values():
            identifiers.update(workflow.get_task_identifiers())
        return sorted(list(identifiers))

    def get_tasks_for_workflow(self, workflow_id: str) -> List[TaskDefinition]:
        """Get all tasks for a specific workflow"""
        workflow = self.get_workflow(workflow_id)
        return workflow.tasks if workflow else []
