"""
Comprehensive tests for the hiring process management application.
Tests all API endpoints and web views with a temporary database.
"""
import pytest
import tempfile
import shutil
import os
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
        assert "id" in data  # ID should be auto-generated

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
        candidate_id = create_response.json()["id"]

        # Get the candidate
        response = test_app.get(f"/api/candidates/{candidate_id}")
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
        candidate_id = create_response.json()["id"]

        # Update the candidate
        response = test_app.put(f"/api/candidates/{candidate_id}", params={
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
        candidate_id = create_response.json()["id"]

        # Delete the candidate
        response = test_app.delete(f"/api/candidates/{candidate_id}")
        assert response.status_code == 204

        # Verify it's deleted
        response = test_app.get(f"/api/candidates/{candidate_id}")
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
        candidate_id = create_response.json()["id"]

        # Create a task
        response = test_app.put(
            f"/api/candidates/{candidate_id}/tasks/resume_screen",
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
        candidate_id = create_response.json()["id"]

        # Create tasks
        test_app.put(
            f"/api/candidates/{candidate_id}/tasks/task1",
            params={"status": "completed"}
        )
        test_app.put(
            f"/api/candidates/{candidate_id}/tasks/task2",
            params={"status": "not_started"}
        )

        # List tasks
        response = test_app.get(f"/api/candidates/{candidate_id}/tasks")
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
        candidate_id = create_response.json()["id"]

        # Create task
        test_app.put(
            f"/api/candidates/{candidate_id}/tasks/test_task",
            params={"status": "not_started"}
        )

        # Update status
        response = test_app.put(
            f"/api/candidates/{candidate_id}/tasks/test_task",
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
        candidate_id = create_response.json()["id"]

        # Create task
        test_app.put(
            f"/api/candidates/{candidate_id}/tasks/delete_me",
            params={"status": "not_started"}
        )

        # Delete task
        response = test_app.delete(f"/api/candidates/{candidate_id}/tasks/delete_me")
        assert response.status_code == 204

        # Verify deleted
        response = test_app.get(f"/api/candidates/{candidate_id}/tasks/delete_me")
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
        candidate_id = create_response.json()["id"]

        # View candidate
        response = test_app.get(f"/candidate/{candidate_id}")
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
        candidate_id = create_response.json()["id"]

        # View workflow
        response = test_app.get(f"/candidate/{candidate_id}/workflow")
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
        candidate_id = create_response.json()["id"]

        # Update via form
        response = test_app.post(f"/candidate/{candidate_id}/edit", data={
            "workflow_id": "senior_engineer_v2",
            "name": "Form Updated",
            "email": "formupdated@example.com"
        }, follow_redirects=False)

        assert response.status_code in [302, 303]

        # Verify update
        get_response = test_app.get(f"/api/candidates/{candidate_id}")
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
        candidate_id = create_response.json()["id"]

        # Delete via form
        response = test_app.post(f"/candidate/{candidate_id}/delete", follow_redirects=False)
        assert response.status_code in [302, 303]

        # Verify deleted
        get_response = test_app.get(f"/api/candidates/{candidate_id}")
        assert get_response.status_code == 404


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
