# Hiring Process Manager

A simple, local-first web application for managing candidates through hiring workflows. Built with FastAPI + SQLModel, featuring truly auto-generated REST APIs with Swagger documentation.

## Setup

Create virtual environment and install dependencies:
```bash
python3.12 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## Usage

### Run the Application

Start the web server:
```bash
./venv/bin/python app.py
```

The server will start on http://localhost:5001 by default with:
- **Web Interface**: http://localhost:5001/
- **API Documentation**: http://localhost:5001/api/docs (Swagger UI)

You can customize the port and data directory:
```bash
./venv/bin/python app.py --port 8080 --data-dir /path/to/data
```

### Web Interface Features

- **View all candidates**: Navigate to `/` to see a list of all candidates
- **Table view**: Navigate to `/table` to see all candidates and their task statuses in a grid
- **Add candidate**: Click "Add Candidate" to create a new candidate record
- **View candidate details**: Click on a candidate to see their information and task progress
- **Edit candidate**: Edit candidate information from the detail view
- **Workflow view**: Visualize candidate progress through their hiring workflow as a DAG
- **Update task status**: Click on tasks to change their status (not started, in progress, completed, n/a)
- **Delete candidates**: Permanently remove candidates from the database

## REST API

The application provides a truly auto-generated REST API powered by FastAPI + SQLModel. **Adding a field to a model automatically exposes it in the API with zero code changes.**

### Accessing API Documentation

Visit http://localhost:5001/api/docs for interactive API documentation where you can:
- Browse all available endpoints
- View request/response schemas
- Test API calls directly from the browser

### API Endpoints

**Candidates**
- `GET /api/candidates` - List all candidates
- `POST /api/candidates` - Create new candidate
- `GET /api/candidates/{id}` - Get candidate details
- `PUT /api/candidates/{id}` - Update candidate
- `DELETE /api/candidates/{id}` - Delete candidate permanently

**Tasks**
- `GET /api/candidates/{id}/tasks` - List all tasks for a candidate
- `GET /api/candidates/{id}/tasks/{task_id}` - Get specific task
- `PUT /api/candidates/{id}/tasks/{task_id}` - Update or create task (upsert)
- `DELETE /api/candidates/{id}/tasks/{task_id}` - Delete task

**Action States**
- `GET /api/action-states` - List all action states
- `GET /api/action-states/{candidate_id}/{action_id}` - Get action state
- `PUT /api/action-states/{candidate_id}/{action_id}` - Update or create action state
- `DELETE /api/action-states/{candidate_id}/{action_id}` - Delete action state

### Example API Usage

Create a candidate:
```bash
curl -X POST http://localhost:5001/api/candidates \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "senior_engineer_v2",
    "name": "John Doe",
    "email": "john@example.com"
  }'
```

Update task status:
```bash
curl -X PUT http://localhost:5001/api/candidates/{id}/tasks/resume_screen \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}'
```

## Data Storage

- **Database**: SQLite database stored at `~/.hiring-client/hiring.db` (or custom location via `--data-dir`)
- **No encryption, no sync**: Just simple local storage
- **All data**: Stored in plaintext in the local database

## Workflows

Workflows are defined in YAML files in the `workflows/` directory. Each workflow defines:
- A list of tasks that can be assigned to candidates
- Dependencies between tasks (which tasks must be completed before others)

The web interface uses these workflow definitions to:
- Show available workflows when adding candidates
- Display task progress in the workflow view
- Render task dependencies as a directed acyclic graph (DAG)

Example workflows included:
- `senior_engineer_v2.yaml` - Hiring process for senior engineers
- `tech_specialist_v1.yaml` - Hiring process for technical specialists

## Architecture

```
app.py             - FastAPI web application with auto-generated REST API
database.py        - Database setup and session management
models.py          - SQLModel data models (Candidate, CandidateTask, ActionState)
workflow_loader.py - Loads workflow definitions from YAML files
templates/         - HTML templates for the web interface
workflows/         - YAML workflow definition files
requirements.txt   - Python dependencies
```

## Data Models

### Candidate
- Basic information: name, email, phone, resume URL, notes
- Assigned to a workflow
- Automatic timestamps (created_at, updated_at)

### CandidateTask
- Links a candidate to a specific task in their workflow
- Stores task status: not_started, in_progress, completed, or na
- Automatic timestamps

### ActionState
- Stores arbitrary JSON state for workflow actions
- Used to persist action-specific data between steps

## Technology Stack

- **FastAPI** (0.115.5) - Modern async web framework with automatic OpenAPI/Swagger generation
- **SQLModel** (0.0.22) - Combines SQLAlchemy + Pydantic for type-safe, auto-validating models
- **Uvicorn** (0.32.1) - ASGI server for running FastAPI
- **PyYAML** (6.0.1) - Workflow definition parsing
- **SQLite** - Local database (built-in with Python)

### Why FastAPI + SQLModel?

This stack enables truly auto-generated APIs:
- **Define models once** with type hints (e.g., `name: Optional[str] = None`)
- **API automatically generated** - add a field and it appears in all API endpoints
- **Automatic validation** - Pydantic validates all incoming data
- **Free Swagger docs** - OpenAPI schema generated from models
- **Zero manual serialization** - models convert to/from JSON automatically
