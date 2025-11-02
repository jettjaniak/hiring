"""
Comprehensive tests for the hiring process management application.
Tests all API endpoints and web views with a temporary database.
"""
import pytest
import tempfile
import shutil
import os
import yaml
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture(scope="function")
def test_app():
    """Create a test app with a temporary database."""
    # Create a temporary directory for test data with proper permissions
    test_dir = tempfile.mkdtemp()
    os.chmod(test_dir, 0o755)

    # Set up environment to use test database
    import sys
    original_argv = sys.argv.copy()
    sys.argv = ['test', '--data-dir', test_dir, '--port', '5001']

    # Clear any cached imports
    if 'src.app' in sys.modules:
        del sys.modules['src.app']
    if 'src.database' in sys.modules:
        del sys.modules['src.database']

    # Import app after setting up sys.argv
    from src.app import app

    client = TestClient(app)
    yield client

    # Restore original argv
    sys.argv = original_argv

    # Cleanup
    try:
        shutil.rmtree(test_dir)
    except:
        pass


class TestAPICandidates:
    """Test candidate API endpoints"""

    def test_create_candidate(self, test_app):
        """Test creating a new candidate"""
        response = test_app.post("/api/candidates", params={
            "name": "John Doe",
            "email": "john@example.com",
            "workflow_id": "senior_engineer_v2"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "John Doe"
        assert data["email"] == "john@example.com"
        assert data["workflow_id"] == "senior_engineer_v2"

    def test_list_candidates(self, test_app):
        """Test listing all candidates"""
        # Create a candidate first
        create_response = test_app.post("/api/candidates", params={
            "workflow_id": "senior_engineer_v2",
            "name": "Jane Doe",
            "email": "jane@example.com"
        })
        assert create_response.status_code == 201

        # List candidates
        response = test_app.get("/api/candidates")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(c["name"] == "Jane Doe" for c in data)

    def test_get_candidate(self, test_app):
        """Test getting a specific candidate"""
        # Create a candidate
        create_response = test_app.post("/api/candidates", params={
            "workflow_id": "senior_engineer_v2",
            "name": "Bob Smith",
            "email": "bob@example.com"
        })
        assert create_response.status_code == 201
        candidate_email = create_response.json()["email"]

        # Get the candidate
        response = test_app.get(f"/api/candidates/{candidate_email}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Bob Smith"
        assert data["email"] == "bob@example.com"

    def test_update_candidate(self, test_app):
        """Test updating a candidate"""
        # Create a candidate
        create_response = test_app.post("/api/candidates", params={
            "workflow_id": "senior_engineer_v2",
            "name": "Alice Johnson",
            "email": "alice@example.com"
        })
        assert create_response.status_code == 201
        candidate_email = create_response.json()["email"]

        # Update the candidate
        response = test_app.put(f"/api/candidates/{candidate_email}", params={
            "name": "Alice Johnson-Updated",
            "email": "alice.updated@example.com",
            "phone": "555-1234"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Alice Johnson-Updated"
        assert data["email"] == "alice.updated@example.com"
        assert data["phone"] == "555-1234"

    def test_delete_candidate(self, test_app):
        """Test deleting a candidate (hard delete)"""
        # Create a candidate
        create_response = test_app.post("/api/candidates", params={
            "workflow_id": "senior_engineer_v2",
            "name": "Delete Me",
            "email": "delete@example.com"
        })
        assert create_response.status_code == 201
        candidate_email = create_response.json()["email"]

        # Delete the candidate
        response = test_app.delete(f"/api/candidates/{candidate_email}")
        assert response.status_code == 204

        # Verify it's deleted
        response = test_app.get(f"/api/candidates/{candidate_email}")
        assert response.status_code == 404


class TestAPITasks:
    """Test task API endpoints"""

    def test_create_task(self, test_app):
        """Test creating a task for a candidate"""
        # Create a candidate first
        create_response = test_app.post("/api/candidates", params={
            "name": "Task Tester",
            "email": "task@example.com",
            "workflow_id": "senior_engineer_v2"
        })
        assert create_response.status_code == 201
        candidate_email = create_response.json()["email"]

        # Create a task
        response = test_app.put(
            f"/api/candidates/{candidate_email}/tasks/resume_screen",
            params={"status": "in_progress"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_identifier"] == "resume_screen"
        assert data["status"] == "in_progress"

    def test_list_tasks(self, test_app):
        """Test listing tasks for a candidate"""
        # Create a candidate
        create_response = test_app.post("/api/candidates", params={
            "workflow_id": "senior_engineer_v2",
            "name": "Multi Task",
            "email": "multi@example.com"
        })
        assert create_response.status_code == 201
        candidate_email = create_response.json()["email"]

        # Create tasks
        test_app.put(
            f"/api/candidates/{candidate_email}/tasks/task1",
            params={"status": "completed"}
        )
        test_app.put(
            f"/api/candidates/{candidate_email}/tasks/task2",
            params={"status": "not_started"}
        )

        # List tasks
        response = test_app.get(f"/api/candidates/{candidate_email}/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert any(t["task_identifier"] == "task1" for t in data)
        assert any(t["task_identifier"] == "task2" for t in data)

    def test_update_task_status(self, test_app):
        """Test updating a task status"""
        # Create candidate
        create_response = test_app.post("/api/candidates", params={
            "workflow_id": "senior_engineer_v2",
            "name": "Status Updater",
            "email": "status@example.com"
        })
        assert create_response.status_code == 201
        candidate_email = create_response.json()["email"]

        # Create task
        test_app.put(
            f"/api/candidates/{candidate_email}/tasks/test_task",
            params={"status": "not_started"}
        )

        # Update status
        response = test_app.put(
            f"/api/candidates/{candidate_email}/tasks/test_task",
            params={"status": "completed"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_delete_task(self, test_app):
        """Test deleting a task"""
        # Create candidate
        create_response = test_app.post("/api/candidates", params={
            "workflow_id": "senior_engineer_v2",
            "name": "Task Deleter",
            "email": "taskdel@example.com"
        })
        assert create_response.status_code == 201
        candidate_email = create_response.json()["email"]

        # Create task
        test_app.put(
            f"/api/candidates/{candidate_email}/tasks/delete_me",
            params={"status": "not_started"}
        )

        # Delete task
        response = test_app.delete(f"/api/candidates/{candidate_email}/tasks/delete_me")
        assert response.status_code == 204

        # Verify deleted
        response = test_app.get(f"/api/candidates/{candidate_email}/tasks/delete_me")
        assert response.status_code == 404


class TestWebViews:
    """Test web views return proper HTML"""

    def test_index_page(self, test_app):
        """Test index page returns HTML"""
        response = test_app.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"<!DOCTYPE html>" in response.content or b"<html" in response.content

    def test_table_view_page(self, test_app):
        """Test table view page returns HTML"""
        response = test_app.get("/table")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_add_candidate_page(self, test_app):
        """Test add candidate page returns HTML"""
        response = test_app.get("/candidate/add")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_view_candidate_page(self, test_app):
        """Test viewing a candidate page"""
        # Create a candidate first
        create_response = test_app.post("/api/candidates", params={
            "name": "View Me",
            "email": "view@example.com",
            "workflow_id": "senior_engineer_v2"
        })
        assert create_response.status_code == 201
        candidate_email = create_response.json()["email"]

        # View candidate
        response = test_app.get(f"/candidate/{candidate_email}")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"View Me" in response.content

    def test_workflow_view_page(self, test_app):
        """Test workflow view page"""
        # Create a candidate
        create_response = test_app.post("/api/candidates", params={
            "name": "Workflow Viewer",
            "email": "workflow@example.com",
            "workflow_id": "senior_engineer_v2"
        })
        assert create_response.status_code == 201
        candidate_email = create_response.json()["email"]

        # View workflow
        response = test_app.get(f"/candidate/{candidate_email}/workflow")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestFormSubmissions:
    """Test form submissions"""

    def test_create_candidate_form(self, test_app):
        """Test creating a candidate via form submission"""
        response = test_app.post("/candidate/add", data={
            "name": "Form Created",
            "email": "form@example.com",
            "workflow_id": "senior_engineer_v2"
        }, follow_redirects=False)

        # Should redirect after creation
        assert response.status_code in [302, 303]

    def test_update_candidate_form(self, test_app):
        """Test updating a candidate via form"""
        # Create candidate first
        create_response = test_app.post("/api/candidates", params={
            "workflow_id": "senior_engineer_v2",
            "name": "Form Update",
            "email": "formupdate@example.com"
        })
        assert create_response.status_code == 201
        candidate_email = create_response.json()["email"]

        # Update via form
        response = test_app.post(f"/candidate/{candidate_email}/edit", data={
            "workflow_id": "senior_engineer_v2",
            "name": "Form Updated",
            "email": "formupdated@example.com"
        }, follow_redirects=False)

        assert response.status_code in [302, 303]

        # Verify update (use new email since it changed)
        get_response = test_app.get(f"/api/candidates/formupdated@example.com")
        assert get_response.json()["name"] == "Form Updated"

    def test_delete_candidate_form(self, test_app):
        """Test deleting a candidate via form"""
        # Create candidate
        create_response = test_app.post("/api/candidates", params={
            "workflow_id": "senior_engineer_v2",
            "name": "Form Delete",
            "email": "formdelete@example.com"
        })
        assert create_response.status_code == 201
        candidate_email = create_response.json()["email"]

        # Delete via form
        response = test_app.post(f"/candidate/{candidate_email}/delete", follow_redirects=False)
        assert response.status_code in [302, 303]

        # Verify deleted
        get_response = test_app.get(f"/api/candidates/{candidate_email}")
        assert get_response.status_code == 404


class TestWorkflowValidation:
    """Test workflow validation with Task model"""

    def test_workflow_loads_with_valid_tasks(self, test_app):
        """Test that workflows load successfully when all tasks exist in database"""
        # The test_app fixture creates a fresh database with tasks from migration
        # Workflows should load without errors
        response = test_app.get("/api/candidates")
        assert response.status_code == 200

    def test_workflow_validation_fails_with_undefined_task(self, test_app):
        """Test that workflow loading skips workflows with undefined tasks"""
        import sys
        import tempfile

        # Create a temporary directory for this test
        test_dir = tempfile.mkdtemp()
        workflows_dir = Path(test_dir) / "workflows"
        workflows_dir.mkdir(parents=True)

        # Create a workflow YAML with an undefined task
        invalid_workflow = {
            'id': 'invalid_workflow',
            'name': 'Invalid Workflow',
            'description': 'Workflow with undefined tasks',
            'tasks': [
                {
                    'task_id': 'undefined_task_that_does_not_exist',
                    'dependencies': []
                }
            ]
        }

        workflow_file = workflows_dir / "invalid.yaml"
        with open(workflow_file, 'w') as f:
            yaml.dump(invalid_workflow, f)

        # Try to load workflows - invalid workflow should be skipped
        try:
            # Clear any cached imports
            if 'src.workflow_loader' in sys.modules:
                del sys.modules['src.workflow_loader']

            from src.workflow_loader import WorkflowLoader
            from src.database import Database

            # Get database from test app
            db_path = Path(test_dir) / "hiring.db"
            db = Database(str(db_path))
            db.init_db()

            # Load workflows - invalid one should be skipped with error message printed
            loader = WorkflowLoader(workflows_dir=str(workflows_dir), db=db)

            # Verify the invalid workflow was NOT loaded
            assert 'invalid_workflow' not in loader.workflows
            assert loader.get_workflow('invalid_workflow') is None
        finally:
            # Cleanup
            try:
                shutil.rmtree(test_dir)
            except:
                pass

    def test_workflow_with_all_valid_task_ids(self, test_app):
        """Test that workflow validates successfully with all valid task_ids"""
        import sys
        import tempfile

        # Create a temporary directory for this test
        test_dir = tempfile.mkdtemp()
        workflows_dir = Path(test_dir) / "workflows"
        workflows_dir.mkdir(parents=True)

        try:
            # Create database and add test tasks
            db_path = Path(test_dir) / "hiring.db"
            from src.database import Database
            from src.models import Task
            from sqlmodel import Session

            db = Database(str(db_path))
            db.init_db()

            # Add valid tasks to database
            with db.get_session() as session:
                task1 = Task(task_id="valid_task_1", name="Valid Task 1", description="Test task 1")
                task2 = Task(task_id="valid_task_2", name="Valid Task 2", description="Test task 2")
                session.add(task1)
                session.add(task2)
                session.commit()

            # Create a workflow YAML with valid tasks
            valid_workflow = {
                'id': 'valid_workflow',
                'name': 'Valid Workflow',
                'description': 'Workflow with valid tasks',
                'tasks': [
                    {
                        'task_id': 'valid_task_1',
                        'dependencies': []
                    },
                    {
                        'task_id': 'valid_task_2',
                        'dependencies': ['valid_task_1']
                    }
                ]
            }

            workflow_file = workflows_dir / "valid.yaml"
            with open(workflow_file, 'w') as f:
                yaml.dump(valid_workflow, f)

            # Clear any cached imports
            if 'src.workflow_loader' in sys.modules:
                del sys.modules['src.workflow_loader']

            from src.workflow_loader import WorkflowLoader

            # This should succeed
            loader = WorkflowLoader(workflows_dir=str(workflows_dir), db=db)

            # Verify workflow loaded
            assert 'valid_workflow' in loader.workflows
            workflow = loader.get_workflow('valid_workflow')
            assert workflow is not None
            assert len(workflow.tasks) == 2
            assert workflow.tasks[0].identifier == 'valid_task_1'
            assert workflow.tasks[1].identifier == 'valid_task_2'
            assert workflow.tasks[1].dependencies == ['valid_task_1']

        finally:
            # Cleanup
            try:
                shutil.rmtree(test_dir)
            except:
                pass


class TestAPIDocumentation:
    """Test API documentation is available"""

    def test_swagger_docs(self, test_app):
        """Test Swagger UI is accessible"""
        response = test_app.get("/api/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_openapi_schema(self, test_app):
        """Test OpenAPI schema is accessible"""
        response = test_app.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
