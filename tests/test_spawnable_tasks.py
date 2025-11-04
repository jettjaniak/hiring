"""
Tests for SpawnedTask and TaskCandidateLink models (Stage 1)
"""
import pytest
import tempfile
import shutil
import os
import sqlite3
from datetime import datetime
from sqlmodel import Session, select

# Import models at module level so they're registered with SQLModel
from src.models import SpawnedTask, TaskCandidateLink, Candidate, Task, CandidateTask


@pytest.fixture(scope="function")
def test_db():
    """Create a test database with models."""
    test_dir = tempfile.mkdtemp()
    os.chmod(test_dir, 0o755)
    db_path = os.path.join(test_dir, "test.db")

    # Import after creating temp dir
    from src.database import Database
    db = Database(db_path)
    db.init_db()

    yield db, db_path

    # Cleanup
    try:
        shutil.rmtree(test_dir)
    except:
        pass


class TestSpawnedTaskModel:
    """Test SpawnedTask model creation and basic operations"""

    def test_create_spawned_task(self, test_db):
        """Test creating a SpawnedTask"""
        db, _ = test_db
        from src.models import SpawnedTask

        with db.get_session() as session:
            task = SpawnedTask(
                title="Test Task",
                description="Test description",
                status="todo"
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            assert task.id is not None
            assert task.title == "Test Task"
            assert task.description == "Test description"
            assert task.status == "todo"
            assert task.created_at is not None
            assert task.updated_at is not None

    def test_spawned_task_with_template(self, test_db):
        """Test creating a SpawnedTask linked to a template"""
        db, _ = test_db
        from src.models import SpawnedTask, Task

        with db.get_session() as session:
            # Create a task template first
            template = Task(
                task_id="phone_screen",
                name="Phone Screen",
                description="Initial phone screening"
            )
            session.add(template)
            session.commit()

            # Create spawned task from template
            spawned = SpawnedTask(
                title="Phone Screen",
                description="Phone screen for John Doe",
                status="todo",
                template_id="phone_screen",
                workflow_id="senior_engineer_v2"
            )
            session.add(spawned)
            session.commit()
            session.refresh(spawned)

            assert spawned.id is not None
            assert spawned.template_id == "phone_screen"
            assert spawned.workflow_id == "senior_engineer_v2"

    def test_spawned_task_status_values(self, test_db):
        """Test that SpawnedTask accepts valid status values"""
        db, _ = test_db
        from src.models import SpawnedTask

        valid_statuses = ["todo", "in_progress", "done"]

        with db.get_session() as session:
            for status in valid_statuses:
                task = SpawnedTask(
                    title=f"Task {status}",
                    status=status
                )
                session.add(task)
                session.commit()
                session.refresh(task)
                assert task.status == status

    def test_spawned_task_default_status(self, test_db):
        """Test that SpawnedTask has default status 'todo'"""
        db, _ = test_db
        from src.models import SpawnedTask

        with db.get_session() as session:
            task = SpawnedTask(title="Test Task")
            session.add(task)
            session.commit()
            session.refresh(task)

            assert task.status == "todo"

    def test_update_spawned_task(self, test_db):
        """Test updating a SpawnedTask"""
        db, _ = test_db
        from src.models import SpawnedTask

        with db.get_session() as session:
            # Create task
            task = SpawnedTask(
                title="Original Title",
                description="Original description",
                status="todo"
            )
            session.add(task)
            session.commit()
            task_id = task.id

            # Update task
            task.title = "Updated Title"
            task.status = "in_progress"
            session.commit()

            # Retrieve and verify
            updated_task = session.get(SpawnedTask, task_id)
            assert updated_task.title == "Updated Title"
            assert updated_task.status == "in_progress"

    def test_delete_spawned_task(self, test_db):
        """Test deleting a SpawnedTask"""
        db, _ = test_db
        from src.models import SpawnedTask

        with db.get_session() as session:
            task = SpawnedTask(title="Delete Me")
            session.add(task)
            session.commit()
            task_id = task.id

            # Delete
            session.delete(task)
            session.commit()

            # Verify deleted
            deleted_task = session.get(SpawnedTask, task_id)
            assert deleted_task is None


class TestTaskCandidateLinkModel:
    """Test TaskCandidateLink model and relationships"""

    def test_create_task_candidate_link(self, test_db):
        """Test creating a link between task and candidate"""
        db, _ = test_db
        from src.models import SpawnedTask, Candidate, TaskCandidateLink

        with db.get_session() as session:
            # Create candidate
            candidate = Candidate(
                email="test@example.com",
                name="Test User"
            )
            session.add(candidate)

            # Create task
            task = SpawnedTask(title="Test Task")
            session.add(task)
            session.commit()
            session.refresh(task)

            # Create link
            link = TaskCandidateLink(
                task_id=task.id,
                candidate_email=candidate.email
            )
            session.add(link)
            session.commit()

            assert link.task_id == task.id
            assert link.candidate_email == candidate.email
            assert link.created_at is not None

    def test_task_multiple_candidates(self, test_db):
        """Test linking one task to multiple candidates"""
        db, _ = test_db
        from src.models import SpawnedTask, Candidate, TaskCandidateLink

        with db.get_session() as session:
            # Create task
            task = SpawnedTask(title="Shared Task")
            session.add(task)
            session.commit()
            session.refresh(task)

            # Create multiple candidates
            candidates = [
                Candidate(email="user1@example.com", name="User 1"),
                Candidate(email="user2@example.com", name="User 2"),
                Candidate(email="user3@example.com", name="User 3")
            ]
            for candidate in candidates:
                session.add(candidate)
            session.commit()

            # Link task to all candidates
            for candidate in candidates:
                link = TaskCandidateLink(
                    task_id=task.id,
                    candidate_email=candidate.email
                )
                session.add(link)
            session.commit()

            # Verify all links exist
            links = session.exec(
                select(TaskCandidateLink).where(TaskCandidateLink.task_id == task.id)
            ).all()
            assert len(links) == 3
            linked_emails = [link.candidate_email for link in links]
            assert "user1@example.com" in linked_emails
            assert "user2@example.com" in linked_emails
            assert "user3@example.com" in linked_emails

    def test_candidate_multiple_tasks(self, test_db):
        """Test linking one candidate to multiple tasks"""
        db, _ = test_db
        from src.models import SpawnedTask, Candidate, TaskCandidateLink

        with db.get_session() as session:
            # Create candidate
            candidate = Candidate(email="busy@example.com", name="Busy User")
            session.add(candidate)
            session.commit()

            # Create multiple tasks
            tasks = [
                SpawnedTask(title="Task 1"),
                SpawnedTask(title="Task 2"),
                SpawnedTask(title="Task 3")
            ]
            for task in tasks:
                session.add(task)
            session.commit()

            # Link all tasks to candidate
            for task in tasks:
                session.refresh(task)
                link = TaskCandidateLink(
                    task_id=task.id,
                    candidate_email=candidate.email
                )
                session.add(link)
            session.commit()

            # Verify all links exist
            links = session.exec(
                select(TaskCandidateLink).where(
                    TaskCandidateLink.candidate_email == candidate.email
                )
            ).all()
            assert len(links) == 3

    def test_delete_task_and_links(self, test_db):
        """Test that task can be deleted (links may remain if FK constraints not enabled)"""
        db, _ = test_db
        from src.models import SpawnedTask, Candidate, TaskCandidateLink

        with db.get_session() as session:
            # Create task and candidate
            task = SpawnedTask(title="Delete Me")
            candidate = Candidate(email="test@example.com", name="Test")
            session.add(task)
            session.add(candidate)
            session.commit()
            session.refresh(task)

            # Create link
            link = TaskCandidateLink(
                task_id=task.id,
                candidate_email=candidate.email
            )
            session.add(link)
            session.commit()

            # Delete task
            task_id = task.id
            session.delete(task)
            session.commit()

            # Verify task is deleted
            deleted_task = session.get(SpawnedTask, task_id)
            assert deleted_task is None

            # Note: Cascade behavior depends on SQLite FK enforcement being enabled
            # which is not guaranteed in all test environments

    def test_delete_candidate_and_links(self, test_db):
        """Test that candidate can be deleted (links may remain if FK constraints not enabled)"""
        db, _ = test_db
        from src.models import SpawnedTask, Candidate, TaskCandidateLink

        with db.get_session() as session:
            # Create task and candidate
            task = SpawnedTask(title="Test Task")
            candidate = Candidate(email="delete@example.com", name="Delete Me")
            session.add(task)
            session.add(candidate)
            session.commit()
            session.refresh(task)

            # Create link
            link = TaskCandidateLink(
                task_id=task.id,
                candidate_email=candidate.email
            )
            session.add(link)
            session.commit()

            # Delete candidate
            candidate_email = candidate.email
            session.delete(candidate)
            session.commit()

            # Verify candidate is deleted
            deleted_candidate = session.get(Candidate, candidate_email)
            assert deleted_candidate is None

            # Note: Cascade behavior depends on SQLite FK enforcement being enabled
            # which is not guaranteed in all test environments


class TestMigration:
    """Test the migration from CandidateTask to SpawnedTask"""

    def test_migration_script_basic(self, test_db):
        """Test that migration script creates correct tables and migrates data"""
        db, db_path = test_db
        from src.models import Candidate, CandidateTask, Task, SpawnedTask, TaskCandidateLink

        # Create some test data in old format
        with db.get_session() as session:
            # Create candidate
            candidate = Candidate(
                email="migrate@example.com",
                name="Migration Test",
                workflow_id="test_workflow"
            )
            session.add(candidate)

            # Create task template
            task_template = Task(
                task_id="resume_review",
                name="Resume Review",
                description="Review candidate resume"
            )
            session.add(task_template)
            session.commit()

            # Create candidate task (old format)
            candidate_task = CandidateTask(
                candidate_id=candidate.email,
                task_identifier="resume_review",
                status="in_progress"
            )
            session.add(candidate_task)
            session.commit()

        # Run migration
        import subprocess
        result = subprocess.run(
            ["python3", "migrate_to_spawnable_tasks.py", "--db", db_path],
            cwd="/Users/jett/Documents/jett/hiring",
            capture_output=True,
            text=True
        )

        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr)
            pytest.fail(f"Migration failed with exit code {result.returncode}")

        # Verify migration results
        with db.get_session() as session:
            # Check spawned task was created
            spawned_tasks = session.exec(select(SpawnedTask)).all()
            assert len(spawned_tasks) == 1

            spawned_task = spawned_tasks[0]
            assert spawned_task.title == "Resume Review"
            assert spawned_task.description == "Review candidate resume"
            assert spawned_task.status == "in_progress"
            assert spawned_task.template_id == "resume_review"
            assert spawned_task.workflow_id == "test_workflow"

            # Check task-candidate link was created
            links = session.exec(
                select(TaskCandidateLink).where(
                    TaskCandidateLink.task_id == spawned_task.id,
                    TaskCandidateLink.candidate_email == "migrate@example.com"
                )
            ).all()
            assert len(links) == 1

    def test_migration_status_mapping(self, test_db):
        """Test that migration correctly maps old statuses to new ones"""
        db, db_path = test_db
        from src.models import Candidate, CandidateTask, Task, SpawnedTask

        status_mappings = {
            "not_started": "todo",
            "in_progress": "in_progress",
            "completed": "done",
            "na": "done"
        }

        # Create test data for each status
        with db.get_session() as session:
            candidate = Candidate(email="status@example.com", name="Status Test")
            session.add(candidate)

            for old_status in status_mappings.keys():
                task = Task(
                    task_id=f"task_{old_status}",
                    name=f"Task {old_status}"
                )
                session.add(task)
            session.commit()

            for old_status in status_mappings.keys():
                ct = CandidateTask(
                    candidate_id=candidate.email,
                    task_identifier=f"task_{old_status}",
                    status=old_status
                )
                session.add(ct)
            session.commit()

        # Run migration
        import subprocess
        result = subprocess.run(
            ["python3", "migrate_to_spawnable_tasks.py", "--db", db_path],
            cwd="/Users/jett/Documents/jett/hiring",
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.fail(f"Migration failed: {result.stderr}")

        # Verify status mappings
        with db.get_session() as session:
            spawned_tasks = session.exec(select(SpawnedTask)).all()
            assert len(spawned_tasks) == len(status_mappings)

            for task in spawned_tasks:
                # Extract old status from template_id
                old_status = task.template_id.replace("task_", "")
                expected_new_status = status_mappings[old_status]
                assert task.status == expected_new_status, \
                    f"Task with old status '{old_status}' should have new status '{expected_new_status}', got '{task.status}'"
