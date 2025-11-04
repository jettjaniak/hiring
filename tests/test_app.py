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

            # Add valid task templates to database
            with db.get_session() as session:
                from src.models import TaskTemplate
                task1 = TaskTemplate(task_id="valid_task_1", name="Valid Task 1", description="Test task 1")
                task2 = TaskTemplate(task_id="valid_task_2", name="Valid Task 2", description="Test task 2")
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


class TestAPITaskDefinitions:
    """Test TaskTemplate API endpoints"""

    def test_create_task(self, test_app):
        """Test creating a new task template"""
        response = test_app.post("/api/task-templates", params={
            "task_id": "test_task_1",
            "name": "Test Task 1",
            "description": "This is a test task"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["task_id"] == "test_task_1"
        assert data["name"] == "Test Task 1"
        assert data["description"] == "This is a test task"

    def test_list_tasks(self, test_app):
        """Test listing all task templates"""
        # Create a task first
        test_app.post("/api/task-templates", params={
            "task_id": "list_task",
            "name": "List Task",
            "description": "Task for listing"
        })

        # List tasks
        response = test_app.get("/api/task-templates")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Check that our task is in the list
        task_ids = [t["task_id"] for t in data]
        assert "list_task" in task_ids

    def test_get_task(self, test_app):
        """Test getting a specific task template"""
        # Create a task
        test_app.post("/api/task-templates", params={
            "task_id": "get_task",
            "name": "Get Task",
            "description": "Task to get"
        })

        # Get the task
        response = test_app.get("/api/task-templates/get_task")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "get_task"
        assert data["name"] == "Get Task"

    def test_update_task(self, test_app):
        """Test updating a task template"""
        # Create a task
        test_app.post("/api/task-templates", params={
            "task_id": "update_task",
            "name": "Original Name",
            "description": "Original description"
        })

        # Update the task
        response = test_app.put("/api/task-templates/update_task", params={
            "name": "Updated Name",
            "description": "Updated description"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "update_task"
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"

    def test_delete_task(self, test_app):
        """Test deleting a task template"""
        # Create a task
        test_app.post("/api/task-templates", params={
            "task_id": "delete_task",
            "name": "Delete Task",
            "description": "Task to delete"
        })

        # Delete the task
        response = test_app.delete("/api/task-templates/delete_task")
        assert response.status_code == 204

        # Verify it's deleted
        response = test_app.get("/api/task-templates/delete_task")
        assert response.status_code == 404


class TestTaskTemplateWebForms:
    """Test task-template relationship via web forms"""

    def test_create_task_with_templates(self, test_app):
        """Test creating a task and linking it to email templates via web form"""
        # Create some email templates first
        test_app.post("/template/add", data={
            "name": "Welcome Email",
            "content": "Welcome to the team!"
        }, follow_redirects=False)

        test_app.post("/template/add", data={
            "name": "Rejection Email",
            "content": "Thank you for your interest"
        }, follow_redirects=False)

        # Get template IDs from the database
        from src.database import Database
        from src.models import EmailTemplate
        from sqlmodel import select
        import sys

        test_dir = sys.argv[2]
        db = Database(f"{test_dir}/hiring.db")

        with db.get_session() as session:
            templates = session.exec(select(EmailTemplate)).all()
            template_ids = [t.id for t in templates]

        # Create a task and link it to the first template
        response = test_app.post("/tasks/add", data={
            "task_id": "send_welcome",
            "name": "Send Welcome Email",
            "description": "Send welcome email to new candidate",
            "template_ids": [template_ids[0]]  # Link to first template
        }, follow_redirects=False)

        assert response.status_code in [302, 303]

        # Verify the link was created
        from src.models import EmailTemplateTask
        with db.get_session() as session:
            link = session.exec(
                select(EmailTemplateTask).where(
                    EmailTemplateTask.task_id == "send_welcome",
                    EmailTemplateTask.email_template_id == template_ids[0]
                )
            ).first()
            assert link is not None

    def test_edit_task_template_links(self, test_app):
        """Test editing task to change linked templates"""
        # Create a template
        test_app.post("/template/add", data={
            "name": "Interview Invite",
            "content": "You're invited to interview"
        }, follow_redirects=False)

        # Create a task
        test_app.post("/tasks/add", data={
            "task_id": "schedule_interview",
            "name": "Schedule Interview",
            "description": "Send interview invitation"
        }, follow_redirects=False)

        # Get template ID
        from src.database import Database
        from src.models import EmailTemplate
        from sqlmodel import select
        import sys

        test_dir = sys.argv[2]
        db = Database(f"{test_dir}/hiring.db")

        with db.get_session() as session:
            template = session.exec(select(EmailTemplate).where(EmailTemplate.name == "Interview Invite")).first()
            template_id = template.id

        # Edit task to link the template
        response = test_app.post("/tasks/schedule_interview/edit", data={
            "task_id": "schedule_interview",
            "name": "Schedule Interview",
            "description": "Send interview invitation",
            "template_ids": [template_id]
        }, follow_redirects=False)

        assert response.status_code in [302, 303]

        # Verify link exists
        from src.models import EmailTemplateTask
        with db.get_session() as session:
            link = session.exec(
                select(EmailTemplateTask).where(
                    EmailTemplateTask.task_id == "schedule_interview",
                    EmailTemplateTask.email_template_id == template_id
                )
            ).first()
            assert link is not None

    def test_create_template_with_tasks(self, test_app):
        """Test creating an email template and linking it to tasks via web form"""
        # Create some task templates first
        test_app.post("/api/task-templates", params={
            "task_id": "screen_resume",
            "name": "Screen Resume"
        })

        test_app.post("/api/task-templates", params={
            "task_id": "phone_screen",
            "name": "Phone Screen"
        })

        # Create a template and link it to the first task
        response = test_app.post("/template/add", data={
            "name": "Screening Email",
            "content": "We'd like to schedule a phone screen",
            "task_ids": ["screen_resume"]
        }, follow_redirects=False)

        assert response.status_code in [302, 303]

        # Verify the link was created
        from src.database import Database
        from src.models import EmailTemplate, EmailTemplateTask
        from sqlmodel import select
        import sys

        test_dir = sys.argv[2]
        db = Database(f"{test_dir}/hiring.db")

        with db.get_session() as session:
            template = session.exec(select(EmailTemplate).where(EmailTemplate.name == "Screening Email")).first()
            link = session.exec(
                select(EmailTemplateTask).where(
                    EmailTemplateTask.task_id == "screen_resume",
                    EmailTemplateTask.email_template_id == template.id
                )
            ).first()
            assert link is not None


class TestChecklistOperations:
    """Test checklist CRUD operations and state management"""

    def test_create_checklist(self, test_app):
        """Test creating a checklist via web form"""
        # Create a task first
        test_app.post("/api/task-templates", params={
            "task_id": "reference_check",
            "name": "Reference Check",
            "description": "Conduct reference checks"
        })

        # Create a checklist
        response = test_app.post("/checklists/add", data={
            "checklist_id": "reference_checklist",
            "name": "Reference Check List",
            "description": "Items to verify during reference check",
            "task_id": "reference_check",
            "items": "Verify employment dates\nCheck job title\nConfirm responsibilities"
        }, follow_redirects=False)

        assert response.status_code in [302, 303]

        # Verify checklist was created
        from src.database import Database
        from src.models import Checklist
        from sqlmodel import select
        import sys
        import json

        test_dir = sys.argv[2]
        db = Database(f"{test_dir}/hiring.db")

        with db.get_session() as session:
            checklist = session.get(Checklist, "reference_checklist")
            assert checklist is not None
            assert checklist.name == "Reference Check List"
            assert checklist.description == "Items to verify during reference check"
            assert checklist.task_template_id == "reference_check"

            # Verify items are stored as JSON
            items = json.loads(checklist.items)
            assert len(items) == 3
            assert "Verify employment dates" in items
            assert "Check job title" in items
            assert "Confirm responsibilities" in items

    def test_checklist_one_to_one_constraint(self, test_app):
        """Test that a task can only have one checklist"""
        # Create a task
        test_app.post("/api/task-templates", params={
            "task_id": "onboarding",
            "name": "Onboarding"
        })

        # Create first checklist
        test_app.post("/checklists/add", data={
            "checklist_id": "onboarding_checklist_1",
            "name": "Onboarding Checklist 1",
            "task_id": "onboarding",
            "items": "Item 1\nItem 2"
        }, follow_redirects=False)

        # Try to create second checklist for same task - should fail
        response = test_app.post("/checklists/add", data={
            "checklist_id": "onboarding_checklist_2",
            "name": "Onboarding Checklist 2",
            "task_id": "onboarding",
            "items": "Item 3\nItem 4"
        }, follow_redirects=False)

        # Should return error (400 status)
        assert response.status_code == 400

    def test_edit_checklist(self, test_app):
        """Test editing a checklist"""
        # Create task and checklist
        test_app.post("/api/task-templates", params={
            "task_id": "background_check",
            "name": "Background Check"
        })

        test_app.post("/checklists/add", data={
            "checklist_id": "bg_checklist",
            "name": "BG Check List",
            "description": "Original description",
            "task_id": "background_check",
            "items": "Item 1\nItem 2"
        }, follow_redirects=False)

        # Edit the checklist
        response = test_app.post("/checklists/bg_checklist/edit", data={
            "checklist_id": "bg_checklist",
            "name": "Updated BG Check List",
            "description": "Updated description",
            "items": "Updated Item 1\nUpdated Item 2\nNew Item 3"
        }, follow_redirects=False)

        assert response.status_code in [302, 303]

        # Verify changes
        from src.database import Database
        from src.models import Checklist
        import sys
        import json

        test_dir = sys.argv[2]
        db = Database(f"{test_dir}/hiring.db")

        with db.get_session() as session:
            checklist = session.get(Checklist, "bg_checklist")
            assert checklist.name == "Updated BG Check List"
            assert checklist.description == "Updated description"
            items = json.loads(checklist.items)
            assert len(items) == 3
            assert "New Item 3" in items

    def test_delete_checklist(self, test_app):
        """Test deleting a checklist"""
        # Create task and checklist
        test_app.post("/api/task-templates", params={
            "task_id": "drug_test",
            "name": "Drug Test"
        })

        test_app.post("/checklists/add", data={
            "checklist_id": "drug_test_checklist",
            "name": "Drug Test Checklist",
            "task_id": "drug_test",
            "items": "Schedule test\nReceive results"
        }, follow_redirects=False)

        # Delete the checklist
        response = test_app.post("/checklists/drug_test_checklist/delete", follow_redirects=False)
        assert response.status_code in [302, 303]

        # Verify it's deleted
        from src.database import Database
        from src.models import Checklist
        import sys

        test_dir = sys.argv[2]
        db = Database(f"{test_dir}/hiring.db")

        with db.get_session() as session:
            checklist = session.get(Checklist, "drug_test_checklist")
            assert checklist is None

    def test_checklist_state_save_and_retrieve(self, test_app):
        """Test saving and retrieving checklist state for a candidate"""
        import json

        # Create candidate
        response = test_app.post("/api/candidates", params={
            "name": "Test Candidate",
            "email": "test@example.com",
            "workflow_id": "standard_workflow"
        })

        # Create task and checklist
        test_app.post("/api/task-templates", params={
            "task_id": "training",
            "name": "Training"
        })

        test_app.post("/checklists/add", data={
            "checklist_id": "training_checklist",
            "name": "Training Checklist",
            "task_id": "training",
            "items": "Complete module 1\nComplete module 2\nPass quiz"
        }, follow_redirects=False)

        # Save checklist state
        items_state = [True, False, True]  # Module 1 done, module 2 not done, quiz done
        response = test_app.post(
            "/api/checklist/training_checklist/save",
            json={
                "candidate_id": "test@example.com",
                "task_identifier": "training",
                "items_state": items_state
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Retrieve checklist view to verify state was saved
        response = test_app.get(
            "/checklist/training_checklist/view?candidate=test@example.com&task=training"
        )
        assert response.status_code == 200

        # Verify state in database
        from src.database import Database
        from src.models import CandidateChecklistState
        from sqlmodel import select
        import sys

        test_dir = sys.argv[2]
        db = Database(f"{test_dir}/hiring.db")

        with db.get_session() as session:
            state = session.exec(
                select(CandidateChecklistState).where(
                    CandidateChecklistState.candidate_id == "test@example.com",
                    CandidateChecklistState.task_identifier == "training",
                    CandidateChecklistState.checklist_id == "training_checklist"
                )
            ).first()

            assert state is not None
            saved_items = json.loads(state.items_state)
            assert saved_items == items_state
            assert state.last_modified is not None

    def test_checklist_state_update(self, test_app):
        """Test updating existing checklist state"""
        import json

        # Create candidate
        test_app.post("/api/candidates", params={
            "name": "Update Test",
            "email": "update@example.com",
            "workflow_id": "standard_workflow"
        })

        # Create task and checklist
        test_app.post("/api/task-templates", params={
            "task_id": "orientation",
            "name": "Orientation"
        })

        test_app.post("/checklists/add", data={
            "checklist_id": "orientation_checklist",
            "name": "Orientation Checklist",
            "task_id": "orientation",
            "items": "Tour office\nMeet team\nSetup workstation"
        }, follow_redirects=False)

        # Save initial state
        initial_state = [True, False, False]
        test_app.post(
            "/api/checklist/orientation_checklist/save",
            json={
                "candidate_id": "update@example.com",
                "task_identifier": "orientation",
                "items_state": initial_state
            }
        )

        # Update state
        updated_state = [True, True, True]
        response = test_app.post(
            "/api/checklist/orientation_checklist/save",
            json={
                "candidate_id": "update@example.com",
                "task_identifier": "orientation",
                "items_state": updated_state
            }
        )

        assert response.status_code == 200

        # Verify updated state
        from src.database import Database
        from src.models import CandidateChecklistState
        from sqlmodel import select
        import sys

        test_dir = sys.argv[2]
        db = Database(f"{test_dir}/hiring.db")

        with db.get_session() as session:
            state = session.exec(
                select(CandidateChecklistState).where(
                    CandidateChecklistState.candidate_id == "update@example.com",
                    CandidateChecklistState.task_identifier == "orientation",
                    CandidateChecklistState.checklist_id == "orientation_checklist"
                )
            ).first()

            saved_items = json.loads(state.items_state)
            assert saved_items == updated_state

    def test_checklist_view_page_loads(self, test_app):
        """Test that checklist view page loads correctly"""
        # Create candidate
        test_app.post("/api/candidates", params={
            "name": "View Test",
            "email": "view@example.com",
            "workflow_id": "test_workflow"
        })

        # Create task
        test_app.post("/api/task-templates", params={
            "task_id": "review",
            "name": "Review"
        })

        # Create checklist for task
        test_app.post("/checklists/add", data={
            "checklist_id": "review_checklist",
            "name": "Review Checklist",
            "task_id": "review",
            "items": "Item 1\nItem 2\nItem 3"
        }, follow_redirects=False)

        # Get checklist view page
        response = test_app.get("/checklist/review_checklist/view?candidate=view@example.com&task=review")
        assert response.status_code == 200
        assert b"Review Checklist" in response.content
        assert b"Item 1" in response.content


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
