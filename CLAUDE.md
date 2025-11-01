# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hiring process management and automation tool with end-to-end encryption. Backend serves as encrypted data storage and sync service between clients. Client-side encryption ensures candidate data is secure even with full database access.

## Architecture

**Backend (Python/FastAPI)**: Stores encrypted blobs and handles sync with optimistic locking
**Client (Python CLI)**: Terminal interface for managing candidates, handles encryption/decryption, syncs with server

### Data Model

- **Candidate**: Metadata container (id, workflow_id). One workflow per candidate.
- **CandidateField**: Stores encrypted candidate data with field-level versioning for granular conflict detection
- **CandidateTask**: Links candidate to workflow tasks. Tracks completion state with strict versioning.
- **ActionState**: Per-candidate state for Actions (mini-apps that help complete tasks)

### Key Concepts

**Workflows**: Define DAG of Tasks with dependencies (stored as JSON/YAML, bundled with app)
**Tasks**: Have identifier, name, dependencies. Same task can appear in multiple workflows.
**Actions**: Reusable mini-apps (HTML+JS) that can complete multiple tasks. Maintain per-candidate state.

### Conflict Resolution

- **CandidateTask**: Strict version locking - no concurrent edits allowed
- **CandidateField**: Field-level versions - different fields can be edited concurrently
- **ActionState**: Strict version locking

## Development Commands

### Server Setup
```bash
cd server
python3.12 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### Run Server
```bash
cd server
./venv/bin/python run.py
```
Server starts on `http://localhost:8000`. API docs at `http://localhost:8000/docs`

### Test Server API
```bash
cd server
./venv/bin/python test_api.py
```

### Client Setup
```bash
cd client
python3.12 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### Initialize Client (First Time)
```bash
cd client
./venv/bin/python cli.py init
# Enter encryption key when prompted
# Use same key across all team members
```

### Client Commands
```bash
cd client
./venv/bin/python cli.py status              # Show client status
./venv/bin/python cli.py add-candidate       # Add new candidate
./venv/bin/python cli.py list-candidates     # List all candidates
./venv/bin/python cli.py show-candidate <id> # Show candidate details
./venv/bin/python cli.py update-candidate <id> --name "..." --email "..."
./venv/bin/python cli.py complete-task <cid> <task_id>
./venv/bin/python cli.py sync                # Sync with server
./venv/bin/python cli.py migrate             # Run schema migrations
./venv/bin/python cli.py rotate-key          # Rotate encryption key
```

### Test Client
```bash
cd client
./venv/bin/python test_demo.py  # Run full demo (requires server running)
```

## API Architecture

All sensitive data stored as encrypted blobs (bytes). Server never sees plaintext candidate data.

**Sync model**: Client polls `/api/sync?since={timestamp}` to get all changes, merges locally.

**Version conflicts**: Return 409 with details. Client must fetch latest, re-encrypt, retry.

## Project Structure

```
server/
  ├── main.py          # FastAPI app and endpoints
  ├── models.py        # SQLAlchemy database models
  ├── schemas.py       # Pydantic request/response schemas
  ├── crud.py          # Database operations with version checking
  ├── database.py      # Database connection and initialization
  ├── run.py           # Server startup script
  └── test_api.py      # API test examples

client/
  ├── cli.py           # Command-line interface
  ├── config.py        # Configuration management
  ├── database.py      # Local database setup
  ├── models.py        # Local data models (decrypted)
  ├── encryption.py    # Encryption/decryption utilities
  ├── sync.py          # Server synchronization engine
  ├── migrations.py    # Schema migrations and key rotation
  └── test_demo.py     # Demo test script
```

## Client Features

- **E2EE**: All candidate data encrypted client-side with Fernet (symmetric encryption)
- **Local Storage**: SQLite database at `~/.hiring-client/local.db` stores decrypted data
- **Sync**: Pulls changes from server, decrypts; pushes local changes, encrypts
- **Conflict Detection**: Optimistic locking with version numbers
- **Schema Migrations**: Add new fields to candidate schema, migrate local and server data
- **Key Rotation**: Change encryption key, re-encrypt all data on server
- **Extensible**: Designed to be wrapped in HTTP server + web frontend later
