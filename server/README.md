# Hiring Process API Server

Python backend API for the hiring process management tool. Provides encrypted data storage and sync capabilities.

## Setup

Create virtual environment and install dependencies:
```bash
python3.12 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## Running the Server

```bash
./venv/bin/python run.py
```

Server will start on `http://localhost:8000`

API documentation available at: `http://localhost:8000/docs`

## Testing

Run the test script (with server running):
```bash
./venv/bin/python test_api.py
```

## API Overview

### Candidates
- `POST /api/candidates` - Create candidate
- `GET /api/candidates` - List all candidates (id + workflow_id only)
- `GET /api/candidates/{id}` - Get candidate with all fields
- `PUT /api/candidates/{id}/fields` - Update specific fields (with version check)

### Candidate Tasks
- `GET /api/candidates/{id}/tasks` - Get all tasks for candidate
- `POST /api/candidate-tasks` - Create new task
- `PUT /api/candidate-tasks/{candidate_id}/{task_id}` - Update task (with version check)

### Action States
- `GET /api/candidates/{id}/action-states` - Get all action states for candidate
- `POST /api/action-states` - Create action state
- `PUT /api/action-states/{candidate_id}/{action_id}` - Update action state (with version check)

### Sync
- `GET /api/sync?since={timestamp}` - Get all changes since timestamp

## Key Design Features

1. **Field-level versioning** - Each candidate field has its own version for granular conflict detection
2. **Strict task versioning** - CandidateTasks have strict version checks to prevent concurrent edits
3. **Encrypted storage** - All sensitive data stored as encrypted blobs (encryption happens client-side)
4. **Sync support** - `/sync` endpoint returns all changes since a given timestamp

## Database

SQLite database file: `hiring.db` (created automatically on first run)
