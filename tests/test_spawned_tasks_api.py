"""
Tests for SpawnedTask API endpoints (Stage 2)
Simplified version without complex dependency overrides
"""
import pytest
import tempfile
import shutil
import os
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy.pool import StaticPool

from src.models import Candidate, Task, SpawnedTask, TaskCandidateLink
from src.database import Database


@pytest.fixture(scope="function")
def test_engine():
    """Create an in-memory test database engine"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create a test database session"""
    with Session(test_engine) as session:
        # Set up test data
        template1 = Task(
            task_id="phone_screen",
            name="Phone Screen",
            description="Initial phone screening"
        )
        template2 = Task(
            task_id="technical_interview",
            name="Technical Interview",
            description="Technical assessment"
        )
        session.add(template1)
        session.add(template2)

        candidate1 = Candidate(
            email="candidate1@example.com",
            name="Candidate One",
            workflow_id="senior_engineer"
        )
        candidate2 = Candidate(
            email="candidate2@example.com",
            name="Candidate Two",
            workflow_id="junior_engineer"
        )
        session.add(candidate1)
        session.add(candidate2)

        session.commit()
        yield session


@pytest.fixture(scope="function")
def client(test_engine):
    """Create a test client with in-memory database"""
    # Import app here to avoid circular imports
    from src.app import app, get_session

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    # Create test data
    with Session(test_engine) as session:
        template1 = Task(
            task_id="phone_screen",
            name="Phone Screen",
            description="Initial phone screening"
        )
        template2 = Task(
            task_id="technical_interview",
            name="Technical Interview",
            description="Technical assessment"
        )
        session.add(template1)
        session.add(template2)

        candidate1 = Candidate(
            email="candidate1@example.com",
            name="Candidate One",
            workflow_id="senior_engineer"
        )
        candidate2 = Candidate(
            email="candidate2@example.com",
            name="Candidate Two",
            workflow_id="junior_engineer"
        )
        session.add(candidate1)
        session.add(candidate2)

        session.commit()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


class TestSpawnTaskEndpoint:
    """Test POST /api/tasks/spawn endpoint"""

    def test_spawn_task_from_template(self, client):
        """Test spawning a task from a template"""
        response = client.post(
            "/api/tasks/spawn",
            json={
                "template_id": "phone_screen",
                "candidate_emails": ["candidate1@example.com"]
            }
        )

        assert response.status_code == 201
        data = response.json()
        print(f"DEBUG: Response JSON = {data}")
        print(f"DEBUG: Response status = {response.status_code}")
        print(f"DEBUG: Response text = {response.text}")
        assert data["title"] == "Phone Screen"
        assert data["description"] == "Initial phone screening"
        assert data["status"] == "todo"
        assert data["template_id"] == "phone_screen"
        assert data["workflow_id"] == "senior_engineer"
        assert "id" in data

    def test_spawn_task_with_custom_title(self, client):
        """Test spawning a task with custom title and description"""
        response = client.post(
            "/api/tasks/spawn",
            json={
                "template_id": "phone_screen",
                "candidate_emails": ["candidate1@example.com"],
                "title": "Custom Phone Screen",
                "description": "Custom description"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Custom Phone Screen"
        assert data["description"] == "Custom description"

    def test_spawn_task_duplicate_prevention(self, client):
        """Test that spawning the same template twice returns existing task"""
        # First spawn
        response1 = client.post(
            "/api/tasks/spawn",
            json={
                "template_id": "phone_screen",
                "candidate_emails": ["candidate1@example.com"]
            }
        )
        assert response1.status_code == 201
        task_id1 = response1.json()["id"]

        # Second spawn (should return same task)
        response2 = client.post(
            "/api/tasks/spawn",
            json={
                "template_id": "phone_screen",
                "candidate_emails": ["candidate1@example.com"]
            }
        )
        assert response2.status_code == 201
        task_id2 = response2.json()["id"]

        # Should be the same task
        assert task_id1 == task_id2

    def test_spawn_task_multiple_candidates(self, client):
        """Test spawning a task for multiple candidates"""
        response = client.post(
            "/api/tasks/spawn",
            json={
                "template_id": "phone_screen",
                "candidate_emails": ["candidate1@example.com", "candidate2@example.com"]
            }
        )

        assert response.status_code == 201
        task_id = response.json()["id"]

        # Verify both candidates are linked
        response = client.get(f"/api/spawned-tasks/{task_id}/candidates")
        assert response.status_code == 200
        candidates = response.json()
        assert len(candidates) == 2
        assert "candidate1@example.com" in candidates
        assert "candidate2@example.com" in candidates

    def test_spawn_task_template_not_found(self, client):
        """Test spawning with nonexistent template"""
        response = client.post(
            "/api/tasks/spawn",
            json={
                "template_id": "nonexistent",
                "candidate_emails": ["candidate1@example.com"]
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_spawn_task_candidate_not_found(self, client):
        """Test spawning with nonexistent candidate"""
        response = client.post(
            "/api/tasks/spawn",
            json={
                "template_id": "phone_screen",
                "candidate_emails": ["nonexistent@example.com"]
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestListSpawnedTasks:
    """Test GET /api/spawned-tasks endpoint"""

    def test_list_all_tasks(self, client):
        """Test listing all spawned tasks"""
        # Create some tasks
        client.post("/api/tasks/spawn", json={
            "template_id": "phone_screen",
            "candidate_emails": ["candidate1@example.com"]
        })
        client.post("/api/tasks/spawn", json={
            "template_id": "technical_interview",
            "candidate_emails": ["candidate2@example.com"]
        })

        response = client.get("/api/spawned-tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_tasks_filter_by_status(self, client):
        """Test filtering tasks by status"""
        # Create tasks with different statuses
        response1 = client.post("/api/tasks/spawn", json={
            "template_id": "phone_screen",
            "candidate_emails": ["candidate1@example.com"]
        })
        task_id = response1.json()["id"]

        # Update one to in_progress
        client.put(f"/api/spawned-tasks/{task_id}", json={"status": "in_progress"})

        # Create another in todo
        client.post("/api/tasks/spawn", json={
            "template_id": "technical_interview",
            "candidate_emails": ["candidate2@example.com"]
        })

        # Filter by in_progress
        response = client.get("/api/spawned-tasks?status=in_progress")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "in_progress"

    def test_list_tasks_filter_by_workflow(self, client):
        """Test filtering tasks by workflow_id"""
        client.post("/api/tasks/spawn", json={
            "template_id": "phone_screen",
            "candidate_emails": ["candidate1@example.com"]
        })
        client.post("/api/tasks/spawn", json={
            "template_id": "technical_interview",
            "candidate_emails": ["candidate2@example.com"]
        })

        response = client.get("/api/spawned-tasks?workflow_id=senior_engineer")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["workflow_id"] == "senior_engineer"

    def test_list_tasks_filter_by_template(self, client):
        """Test filtering tasks by template_id"""
        client.post("/api/tasks/spawn", json={
            "template_id": "phone_screen",
            "candidate_emails": ["candidate1@example.com"]
        })
        client.post("/api/tasks/spawn", json={
            "template_id": "technical_interview",
            "candidate_emails": ["candidate2@example.com"]
        })

        response = client.get("/api/spawned-tasks?template_id=phone_screen")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["template_id"] == "phone_screen"


class TestGetSpawnedTask:
    """Test GET /api/spawned-tasks/{id} endpoint"""

    def test_get_task_by_id(self, client):
        """Test getting a specific task"""
        # Create a task
        response = client.post("/api/tasks/spawn", json={
            "template_id": "phone_screen",
            "candidate_emails": ["candidate1@example.com"]
        })
        task_id = response.json()["id"]

        # Get the task
        response = client.get(f"/api/spawned-tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["title"] == "Phone Screen"

    def test_get_task_not_found(self, client):
        """Test getting nonexistent task"""
        response = client.get("/api/spawned-tasks/99999")
        assert response.status_code == 404


class TestCreateSpawnedTask:
    """Test POST /api/spawned-tasks endpoint (ad-hoc tasks)"""

    def test_create_adhoc_task(self, client):
        """Test creating an ad-hoc task"""
        response = client.post("/api/spawned-tasks", json={
            "title": "Ad-hoc Task",
            "description": "Custom task not from template",
            "status": "todo",
            "candidate_emails": ["candidate1@example.com"]
        })

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Ad-hoc Task"
        assert data["description"] == "Custom task not from template"
        assert data["status"] == "todo"
        assert data["template_id"] is None

    def test_create_adhoc_task_no_candidates(self, client):
        """Test creating an ad-hoc task with no candidates"""
        response = client.post("/api/spawned-tasks", json={
            "title": "Standalone Task",
            "description": "Task with no candidates",
            "candidate_emails": []
        })

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Standalone Task"

    def test_create_adhoc_task_invalid_status(self, client):
        """Test creating task with invalid status"""
        response = client.post("/api/spawned-tasks", json={
            "title": "Task",
            "status": "invalid_status",
            "candidate_emails": []
        })

        assert response.status_code == 400
        assert "invalid status" in response.json()["detail"].lower()

    def test_create_adhoc_task_candidate_not_found(self, client):
        """Test creating task with nonexistent candidate"""
        response = client.post("/api/spawned-tasks", json={
            "title": "Task",
            "candidate_emails": ["nonexistent@example.com"]
        })

        assert response.status_code == 404


class TestUpdateSpawnedTask:
    """Test PUT /api/spawned-tasks/{id} endpoint"""

    def test_update_task_title(self, client):
        """Test updating task title"""
        # Create task
        response = client.post("/api/tasks/spawn", json={
            "template_id": "phone_screen",
            "candidate_emails": ["candidate1@example.com"]
        })
        task_id = response.json()["id"]

        # Update title
        response = client.put(f"/api/spawned-tasks/{task_id}", json={
            "title": "Updated Title"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    def test_update_task_status(self, client):
        """Test updating task status"""
        # Create task
        response = client.post("/api/tasks/spawn", json={
            "template_id": "phone_screen",
            "candidate_emails": ["candidate1@example.com"]
        })
        task_id = response.json()["id"]

        # Update status to in_progress
        response = client.put(f"/api/spawned-tasks/{task_id}", json={
            "status": "in_progress"
        })
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

        # Update status to done
        response = client.put(f"/api/spawned-tasks/{task_id}", json={
            "status": "done"
        })
        assert response.status_code == 200
        assert response.json()["status"] == "done"

    def test_update_task_invalid_status(self, client):
        """Test updating task with invalid status"""
        # Create task
        response = client.post("/api/tasks/spawn", json={
            "template_id": "phone_screen",
            "candidate_emails": ["candidate1@example.com"]
        })
        task_id = response.json()["id"]

        # Try invalid status
        response = client.put(f"/api/spawned-tasks/{task_id}", json={
            "status": "invalid"
        })

        assert response.status_code == 400

    def test_update_task_not_found(self, client):
        """Test updating nonexistent task"""
        response = client.put("/api/spawned-tasks/99999", json={
            "title": "New Title"
        })

        assert response.status_code == 404


class TestDeleteSpawnedTask:
    """Test DELETE /api/spawned-tasks/{id} endpoint"""

    def test_delete_task(self, client):
        """Test deleting a task"""
        # Create task
        response = client.post("/api/tasks/spawn", json={
            "template_id": "phone_screen",
            "candidate_emails": ["candidate1@example.com"]
        })
        task_id = response.json()["id"]

        # Delete task
        response = client.delete(f"/api/spawned-tasks/{task_id}")
        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/api/spawned-tasks/{task_id}")
        assert response.status_code == 404

    def test_delete_task_not_found(self, client):
        """Test deleting nonexistent task"""
        response = client.delete("/api/spawned-tasks/99999")
        assert response.status_code == 404


class TestTaskCandidateAssociations:
    """Test candidate association endpoints"""

    def test_get_task_candidates(self, client):
        """Test getting candidates for a task"""
        # Create task
        response = client.post("/api/tasks/spawn", json={
            "template_id": "phone_screen",
            "candidate_emails": ["candidate1@example.com", "candidate2@example.com"]
        })
        task_id = response.json()["id"]

        # Get candidates
        response = client.get(f"/api/spawned-tasks/{task_id}/candidates")
        assert response.status_code == 200
        candidates = response.json()
        assert len(candidates) == 2
        assert "candidate1@example.com" in candidates
        assert "candidate2@example.com" in candidates

    def test_add_candidates_to_task(self, client):
        """Test adding candidates to a task"""
        # Create task with one candidate
        response = client.post("/api/tasks/spawn", json={
            "template_id": "phone_screen",
            "candidate_emails": ["candidate1@example.com"]
        })
        task_id = response.json()["id"]

        # Add another candidate
        response = client.post(f"/api/spawned-tasks/{task_id}/candidates", json={
            "candidate_emails": ["candidate2@example.com"]
        })
        assert response.status_code == 201
        assert response.json()["added"] == ["candidate2@example.com"]

        # Verify
        response = client.get(f"/api/spawned-tasks/{task_id}/candidates")
        candidates = response.json()
        assert len(candidates) == 2

    def test_add_candidates_skip_duplicates(self, client):
        """Test that adding existing candidates is skipped"""
        # Create task
        response = client.post("/api/tasks/spawn", json={
            "template_id": "phone_screen",
            "candidate_emails": ["candidate1@example.com"]
        })
        task_id = response.json()["id"]

        # Try to add same candidate again
        response = client.post(f"/api/spawned-tasks/{task_id}/candidates", json={
            "candidate_emails": ["candidate1@example.com"]
        })
        assert response.status_code == 201
        assert len(response.json()["added"]) == 0

    def test_add_candidates_task_not_found(self, client):
        """Test adding candidates to nonexistent task"""
        response = client.post("/api/spawned-tasks/99999/candidates", json={
            "candidate_emails": ["candidate1@example.com"]
        })
        assert response.status_code == 404

    def test_add_candidates_candidate_not_found(self, client):
        """Test adding nonexistent candidate"""
        # Create task
        response = client.post("/api/tasks/spawn", json={
            "template_id": "phone_screen",
            "candidate_emails": ["candidate1@example.com"]
        })
        task_id = response.json()["id"]

        # Try to add nonexistent candidate
        response = client.post(f"/api/spawned-tasks/{task_id}/candidates", json={
            "candidate_emails": ["nonexistent@example.com"]
        })
        assert response.status_code == 404

    def test_remove_candidate_from_task(self, client):
        """Test removing a candidate from a task"""
        # Create task with two candidates
        response = client.post("/api/tasks/spawn", json={
            "template_id": "phone_screen",
            "candidate_emails": ["candidate1@example.com", "candidate2@example.com"]
        })
        task_id = response.json()["id"]

        # Remove one candidate
        response = client.delete(
            f"/api/spawned-tasks/{task_id}/candidates/candidate1@example.com"
        )
        assert response.status_code == 204

        # Verify
        response = client.get(f"/api/spawned-tasks/{task_id}/candidates")
        candidates = response.json()
        assert len(candidates) == 1
        assert "candidate2@example.com" in candidates
        assert "candidate1@example.com" not in candidates

    def test_remove_candidate_task_not_found(self, client):
        """Test removing candidate from nonexistent task"""
        response = client.delete(
            "/api/spawned-tasks/99999/candidates/candidate1@example.com"
        )
        assert response.status_code == 404

    def test_remove_candidate_not_associated(self, client):
        """Test removing candidate not associated with task"""
        # Create task with one candidate
        response = client.post("/api/tasks/spawn", json={
            "template_id": "phone_screen",
            "candidate_emails": ["candidate1@example.com"]
        })
        task_id = response.json()["id"]

        # Try to remove different candidate
        response = client.delete(
            f"/api/spawned-tasks/{task_id}/candidates/candidate2@example.com"
        )
        assert response.status_code == 404
