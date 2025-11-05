# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hiring process management tool

## Architecture

**Single FastAPI Application**: Web interface with auto-generated REST APIs powered by FastAPI + SQLModel. **Adding a field to a model automatically exposes it in the API.**

### Data Model

- **Candidate**: Basic candidate information (name, email, phone, resume URL, notes). Linked to a workflow.
- **TaskTemplate**: Reusable task blueprints with dependencies. Can have email templates, checklists, and special actions attached.
- **Task**: Actual work items. Can be created from TaskTemplate (template-based) or standalone (ad-hoc). Has status: todo, in_progress, done.
- **TaskCandidateLink**: Many-to-many relationship between Tasks and Candidates.
- **EmailTemplate**: Email templates with variable substitution support.
- **Checklist**: Checklists associated with TaskTemplates.

### Key Concepts

**Workflows**: Define DAG of TaskTemplates with dependencies (stored as YAML in `workflows/` directory)
**TaskTemplates**: Have identifier, name, dependencies. Serve as blueprints for creating Tasks.
**Tasks**: Actual work items with status tracking. Can be:
  - Template-based: Created from TaskTemplate, linked to workflow, appear in Kanban + Workflow + Table views
  - Ad-hoc: Created standalone (no template_id, no workflow_id), only appear in Kanban view

## Development Commands

### Setup

```bash
python3.12 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### Run Application

```bash
./venv/bin/python -m src.app
# Or with restart script:
./restart_server.sh
```

Server starts on `http://localhost:8000` by default.
- **Web Interface**: `http://localhost:8000/`
- **API Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **Kanban Board**: `http://localhost:8000/kanban`

## Project Structure

```
hiring/
  ├── src/
  │   ├── app.py               # FastAPI application with auto-generated REST API and HTML views
  │   ├── models.py            # SQLModel data models (combines SQLAlchemy + Pydantic)
  │   ├── database.py          # Database setup and session management
  │   └── workflow_loader.py   # Loads workflow definitions from YAML
  ├── templates/               # HTML templates for web interface
  │   ├── base.html
  │   ├── index.html
  │   ├── table_view.html
  │   ├── workflow_view.html
  │   ├── kanban_view.html     # Kanban board with drag-and-drop
  │   └── ...
  ├── tests/                   # Pytest test suite
  ├── workflows/               # YAML workflow definition files
  ├── requirements.txt         # Python dependencies
  ├── restart_server.sh        # Server restart script
  ├── README.md                # User documentation
  ├── CLAUDE.md                # Developer documentation (this file)
  └── SPAWNABLE_TASKS_PLAN.md  # Detailed plan for task management feature
```

## Features

- **Local Storage**: SQLite database at `~/.hiring-client/hiring.db`
- **Web Interface**: Full-featured UI for managing candidates and tracking workflow progress
- **REST API**: Auto-generated CRUD API with Swagger documentation
- **Workflow Visualization**: DAG view showing task dependencies and progress
- **Table View**: Grid view of all candidates and their task statuses
- **Kanban Board**: Drag-and-drop task management with status columns
- **Email Templates**: Variable substitution and candidate-specific emails
- **Checklists**: Task-associated checklists for structured completion

## Technology Stack

- **FastAPI** (0.115.5) - Modern async web framework with automatic OpenAPI/Swagger generation
- **SQLModel** (0.0.22) - Combines SQLAlchemy + Pydantic for type-safe, auto-validating models
- **Uvicorn** (0.32.1) - ASGI server for running FastAPI
- **PyYAML** (6.0.1) - Workflow definition parsing
- **SQLite** - Local database (built-in with Python)

**Why FastAPI + SQLModel?**

This stack enables truly auto-generated APIs:
- Define models once with type hints (e.g., `name: Optional[str] = None`)
- Add a field → automatically appears in ALL API endpoints
- Automatic validation via Pydantic
- Free Swagger docs from OpenAPI schema
- Zero manual serialization code

## Best Practices

When extending this application:

1. **Models**: Add fields to models in `src/models.py` using type hints. They automatically appear in the API! Example:
   ```python
   class Candidate(SQLModel, table=True):
       new_field: Optional[str] = None  # Automatically in API!
   ```
2. **Workflows**: Create new workflows as YAML files in `workflows/` directory
3. **HTML Templates**: Extend `base.html` for consistent styling
5. **Database Changes**: Update model definitions and write migrations

**Key Advantage**: With SQLModel, you define each field once with its type. No manual serialization, no separate API schemas, no manual validation. It just works.

---

## Important Development Practices

**ALWAYS TEST BEFORE CLAIMING IT WORKS**
- Never tell the user something is working without actually testing it
- Test the actual functionality via curl
- Verify that changes are reflected in the running application
- Check that the database is being queried correctly
- Don't assume code that looks correct will work correctly

### Python Scripts, Not Shell Scripts

**CRITICAL**: When creating utility scripts:
- Create Python scripts (`.py` files) and run them with `./venv/bin/python script.py` - these don't require approval
- Do not create .sh scripts or don't run scripts using ./script.py

## Standard Development Workflow

When implementing any new feature or change, follow this process:

### 1. Implement
- Write the code changes needed
- Update models, endpoints, templates, etc.
- Create Python scripts (NOT shell scripts) for any utility/migration tasks

### 2. Extend Tests
- Add or update tests in `tests/` to cover the new functionality
- Ensure edge cases are covered

### 3. Run Tests
```bash
./venv/bin/pytest tests/ -v
```
- All tests must pass before proceeding
- Fix any failing tests

### 4. Manual Testing on localhost:8000
**CRITICAL: Do not skip this step**

a) **Restart server:**
```bash
./restart_server.sh
```

b) **Send manual test requests:**
```bash
# Test the specific endpoint you changed
curl -X GET http://localhost:8000/your-endpoint
curl -X POST http://localhost:8000/your-endpoint -H "Content-Type: application/json" -d '{"test":"data"}'
```

c) **Verify via curl:**
- Open http://localhost:8000
- Navigate to the feature you implemented
- Test all user flows and interactions
- Verify database changes took effect

d) **Check server logs:**
- Look for any errors or warnings in the server output
- Verify expected log messages appear

### 5. Commit at Each Stage
- Commit after completing each logical phase
- This allows easy rollback if something goes wrong
- Use descriptive commit messages

### 6. Verify & Report
Only after completing steps 1-5:
- Confirm to the user that the feature is working
- Provide specific evidence (test results, curl output, etc.)
- Note any issues or limitations discovered during testing

**Common failure modes to check:**
- Server crashes on startup
- 404/500 errors when accessing endpoints
- Database schema mismatches
- Template rendering errors
- Missing imports or dependencies