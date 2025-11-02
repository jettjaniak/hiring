"""
Comprehensive tests for the hiring process management application.
Tests all API endpoints and web views with a temporary database.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture(scope="function")
def test_app():
    """Create a test app with a temporary database."""
    # Create a temporary directory for test data
    test_dir = tempfile.mkdtemp()

    # Set up environment to use test database
    import sys
    sys.argv = ['test', '--data-dir', test_dir, '--port', '5001']

    # Import app after setting up sys.argv
    from src.app import app

    yield TestClient(app)

    # Cleanup
    shutil.rmtree(test_dir)


class TestAPICandidates:
    """Test candidate API endpoints"""

    def test_create_candidate(self, test_app):
        """Test creating a new candidate"""
        response = test_app.post("/api/candidates", json={
            "id": "test-candidate-1",
            "name": "John Doe",
            "email": "john@example.com",
            "workflow_id": "senior_engineer_v2"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "John Doe"
        assert data["email"] == "john@example.com"
        assert data["workflow_id"] == "senior_engineer_v2"

    def test_list_candidates(self, test_app):
        """Test listing all candidates"""
        # Create a candidate first
        test_app.post("/api/candidates", json={
            "id": "test-candidate-2",
            "name": "Jane Doe",
            "email": "jane@example.com"
        })

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
        test_app.post("/api/candidates", json={
            "id": "test-candidate-3",
            "name": "Bob Smith",
            "email": "bob@example.com"
        })

        # Get the candidate
        response = test_app.get("/api/candidates/test-candidate-3")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Bob Smith"
        assert data["email"] == "bob@example.com"

    def test_update_candidate(self, test_app):
        """Test updating a candidate"""
        # Create a candidate
        test_app.post("/api/candidates", json={
            "id": "test-candidate-4",
            "name": "Alice Johnson",
            "email": "alice@example.com"
        })

        # Update the candidate
        response = test_app.put("/api/candidates/test-candidate-4", json={
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
        test_app.post("/api/candidates", json={
            "id": "test-candidate-5",
            "name": "Delete Me",
            "email": "delete@example.com"
        })

        # Delete the candidate
        response = test_app.delete("/api/candidates/test-candidate-5")
        assert response.status_code == 204

        # Verify it's deleted
        response = test_app.get("/api/candidates/test-candidate-5")
        assert response.status_code == 404


class TestAPITasks:
    """Test task API endpoints"""

    def test_create_task(self, test_app):
        """Test creating a task for a candidate"""
        # Create a candidate first
        test_app.post("/api/candidates", json={
            "id": "test-candidate-6",
            "name": "Task Tester",
            "email": "task@example.com",
            "workflow_id": "senior_engineer_v2"
        })

        # Create a task
        response = test_app.put(
            "/api/candidates/test-candidate-6/tasks/resume_screen",
            params={"status": "in_progress"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_identifier"] == "resume_screen"
        assert data["status"] == "in_progress"

    def test_list_tasks(self, test_app):
        """Test listing tasks for a candidate"""
        # Create a candidate and task
        test_app.post("/api/candidates", json={
            "id": "test-candidate-7",
            "name": "Multi Task",
            "email": "multi@example.com"
        })
        test_app.put(
            "/api/candidates/test-candidate-7/tasks/task1",
            params={"status": "completed"}
        )
        test_app.put(
            "/api/candidates/test-candidate-7/tasks/task2",
            params={"status": "not_started"}
        )

        # List tasks
        response = test_app.get("/api/candidates/test-candidate-7/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert any(t["task_identifier"] == "task1" for t in data)
        assert any(t["task_identifier"] == "task2" for t in data)

    def test_update_task_status(self, test_app):
        """Test updating a task status"""
        # Create candidate and task
        test_app.post("/api/candidates", json={
            "id": "test-candidate-8",
            "name": "Status Updater",
            "email": "status@example.com"
        })
        test_app.put(
            "/api/candidates/test-candidate-8/tasks/test_task",
            params={"status": "not_started"}
        )

        # Update status
        response = test_app.put(
            "/api/candidates/test-candidate-8/tasks/test_task",
            params={"status": "completed"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_delete_task(self, test_app):
        """Test deleting a task"""
        # Create candidate and task
        test_app.post("/api/candidates", json={
            "id": "test-candidate-9",
            "name": "Task Deleter",
            "email": "taskdel@example.com"
        })
        test_app.put(
            "/api/candidates/test-candidate-9/tasks/delete_me",
            params={"status": "not_started"}
        )

        # Delete task
        response = test_app.delete("/api/candidates/test-candidate-9/tasks/delete_me")
        assert response.status_code == 204

        # Verify deleted
        response = test_app.get("/api/candidates/test-candidate-9/tasks/delete_me")
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
        test_app.post("/api/candidates", json={
            "id": "test-candidate-10",
            "name": "View Me",
            "email": "view@example.com",
            "workflow_id": "senior_engineer_v2"
        })

        # View candidate
        response = test_app.get("/candidate/test-candidate-10")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"View Me" in response.content

    def test_workflow_view_page(self, test_app):
        """Test workflow view page"""
        # Create a candidate
        test_app.post("/api/candidates", json={
            "id": "test-candidate-11",
            "name": "Workflow Viewer",
            "email": "workflow@example.com",
            "workflow_id": "senior_engineer_v2"
        })

        # View workflow
        response = test_app.get("/candidate/test-candidate-11/workflow")
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
        test_app.post("/api/candidates", json={
            "id": "test-candidate-12",
            "name": "Form Update",
            "email": "formupdate@example.com"
        })

        # Update via form
        response = test_app.post("/candidate/test-candidate-12/edit", data={
            "name": "Form Updated",
            "email": "formupdated@example.com"
        }, follow_redirects=False)

        assert response.status_code in [302, 303]

        # Verify update
        get_response = test_app.get("/api/candidates/test-candidate-12")
        assert get_response.json()["name"] == "Form Updated"

    def test_delete_candidate_form(self, test_app):
        """Test deleting a candidate via form"""
        # Create candidate
        test_app.post("/api/candidates", json={
            "id": "test-candidate-13",
            "name": "Form Delete",
            "email": "formdelete@example.com"
        })

        # Delete via form
        response = test_app.post("/candidate/test-candidate-13/delete", follow_redirects=False)
        assert response.status_code in [302, 303]

        # Verify deleted
        get_response = test_app.get("/api/candidates/test-candidate-13")
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
