# Hiring Process Manager

A simple, modern web application for managing candidates through hiring workflows.

## Architecture

This application follows a clean **backend/frontend separation**:

- **Backend**: FastAPI + SQLModel REST API with auto-generated documentation
- **Frontend**: Flask web interface that consumes the backend API
- **Database**: SQLite (shared between backend and frontend for simplicity)

## Features

- Manage candidates through customizable hiring workflows
- Track task completion for each candidate
- Visualize workflow progress as a DAG
- RESTful API with automatic OpenAPI documentation
- Soft delete support
- Simple, maintainable codebase

## Quick Start

### 1. Backend Setup

```bash
cd backend
python3.12 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Start the backend API:
```bash
./venv/bin/uvicorn api:app --reload --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Swagger docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 2. Frontend Setup

```bash
cd frontend
python3.12 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Start the frontend:
```bash
./venv/bin/python app.py
```

The web interface will be available at http://localhost:5001

## Project Structure

```
hiring/
├── backend/
│   ├── api.py              # FastAPI application (auto-generates CRUD endpoints)
│   ├── models.py           # SQLModel models (defines DB schema + API schemas)
│   ├── workflow_loader.py  # Loads workflow definitions from YAML
│   ├── workflows/          # Workflow definition files (YAML)
│   └── requirements.txt
│
├── frontend/
│   ├── app.py              # Flask web application
│   ├── templates/          # HTML templates
│   └── requirements.txt
│
├── README.md               # This file
└── CONTRIBUTING.md         # Development guidelines
```

## API Endpoints

The backend automatically generates RESTful endpoints:

### Candidates
- `GET /api/candidates` - List all candidates
- `GET /api/candidates/{id}` - Get candidate details
- `POST /api/candidates` - Create new candidate
- `PATCH /api/candidates/{id}` - Update candidate
- `DELETE /api/candidates/{id}` - Soft delete candidate

### Tasks
- `GET /api/candidates/{id}/tasks` - List candidate's tasks
- `PUT /api/tasks/{candidate_id}/{task_id}` - Create/update task status

### Action States
- `GET /api/action-states/{candidate_id}/{action_id}` - Get action state
- `PUT /api/action-states/{candidate_id}/{action_id}` - Update action state

Full API documentation available at http://localhost:8000/docs

## Workflows

Workflows are defined in YAML files in `backend/workflows/`. Each workflow specifies:
- Tasks that candidates go through
- Dependencies between tasks (which must complete before others)

Example workflow:
```yaml
name: "Tech Specialist Hiring"
identifier: "tech_specialist_v1"
tasks:
  - name: "Initial Screening"
    identifier: "initial_screening"
    dependencies: []
  - name: "Technical Interview"
    identifier: "tech_interview"
    dependencies: ["initial_screening"]
```

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code organization principles
- How to add new features
- Testing guidelines
- Best practices

## Data Storage

- Database: `~/.hiring-app/hiring.db` (SQLite)
- Shared between backend and frontend for simplicity
- Can be easily changed to PostgreSQL/MySQL in production

## Why This Architecture?

1. **Separation of Concerns**: Backend handles data, frontend handles presentation
2. **Auto-generated API**: SQLModel + FastAPI automatically create REST endpoints and docs
3. **Type Safety**: Pydantic models provide validation and type checking
4. **Scalability**: Easy to add a React/Vue frontend or mobile app later
5. **Simplicity**: Minimal boilerplate, maximum functionality

## License

MIT
