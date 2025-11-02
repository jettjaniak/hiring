"""
Load and manage workflow definitions from YAML files
"""
import yaml
from pathlib import Path
from typing import Dict, List


class WorkflowDefinition:
    """Represents a workflow definition"""

    def __init__(self, data: dict):
        self.id = data['id']
        self.name = data['name']
        self.description = data.get('description', '')
        self.tasks = [TaskDefinition(t) for t in data.get('tasks', [])]

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
    """Represents a task definition"""

    def __init__(self, data: dict):
        self.identifier = data['identifier']
        self.name = data['name']
        self.description = data.get('description', '')
        self.dependencies = data.get('dependencies', [])


class WorkflowLoader:
    """Loads workflow definitions from YAML files"""

    def __init__(self, workflows_dir: str = None):
        if workflows_dir is None:
            # Default to workflows/ directory next to this file
            workflows_dir = Path(__file__).parent / 'workflows'
        self.workflows_dir = Path(workflows_dir)
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
                    workflow = WorkflowDefinition(data)
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
