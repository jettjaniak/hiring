# Hiring Process Manager

A simple web-based tool for managing candidates through hiring workflows. Built with Flask and SQLite.

## Setup

Create virtual environment and install dependencies:
```bash
python3.12 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## Usage

### Run the Web Interface

Start the web server:
```bash
./venv/bin/python web.py
```

The server will start on http://localhost:5001 by default.

You can customize the port and data directory:
```bash
./venv/bin/python web.py --port 8080 --data-dir /path/to/data
```

### Web Interface Features

- **View all candidates**: Navigate to `/` to see a list of all candidates
- **Table view**: Navigate to `/table` to see all candidates and their task statuses in a grid
- **Add candidate**: Click "Add Candidate" to create a new candidate record
- **View candidate details**: Click on a candidate to see their information and task progress
- **Edit candidate**: Edit candidate information from the detail view
- **Workflow view**: Visualize candidate progress through their hiring workflow as a DAG
- **Update task status**: Click on tasks to change their status (not started, in progress, completed, n/a)
- **Soft delete**: Delete candidates (they're marked as deleted but not removed from database)

## Data Storage

- Database: SQLite database stored at `~/.hiring-client/hiring.db` (or custom location via `--data-dir`)
- No encryption, no sync, just local storage
- All data is stored in plaintext in the local database

## Workflows

Workflows are defined in YAML files in the `workflows/` directory. Each workflow defines:
- A list of tasks that can be assigned to candidates
- Dependencies between tasks (which tasks must be completed before others)

The web interface uses these workflow definitions to:
- Show available workflows when adding candidates
- Display task progress in the workflow view
- Render task dependencies as a directed acyclic graph (DAG)

## Architecture

```
web.py           - Flask web application
database.py      - Database setup and session management
models.py        - SQLAlchemy data models (Candidate, CandidateTask, ActionState)
workflow_loader.py - Loads workflow definitions from YAML files
templates/       - HTML templates for the web interface
workflows/       - YAML workflow definition files
```

## Models

### Candidate
- Basic information: name, email, phone, resume URL, notes
- Assigned to a workflow
- Soft delete support (deleted flag + deleted_at timestamp)
- Automatic timestamps (created_at, updated_at)

### CandidateTask
- Links a candidate to a specific task in their workflow
- Stores task status: not_started, in_progress, completed, or na
- Automatic timestamps

### ActionState
- Stores arbitrary JSON state for workflow actions
- Used to persist action-specific data between steps

## API Endpoints

### Update Task Status
```
POST /api/candidate/<candidate_id>/task/<task_identifier>/update
Content-Type: application/json

{
  "status": "completed"  // or "not_started", "in_progress", "na"
}
```

Returns: `{"success": true, "status": "completed"}`
