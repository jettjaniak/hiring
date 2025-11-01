# Hiring Process Client

Python CLI client for the hiring process management tool. Handles encryption/decryption, local storage, and sync with the server.

## Setup

Create virtual environment and install dependencies:
```bash
python3.12 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## Usage

### Initialize Client

First time setup (option 1 - direct key):
```bash
./venv/bin/python cli.py init --key "your-password-here"
```

Or (option 2 - interactive prompt):
```bash
./venv/bin/python cli.py init
# You'll be prompted for encryption key
```

Note: Server URL defaults to http://localhost:8000/api

### Commands

**Check Status**
```bash
./venv/bin/python cli.py status
```

**Add a Candidate**
```bash
./venv/bin/python cli.py add-candidate
```

**List Candidates**
```bash
./venv/bin/python cli.py list-candidates
./venv/bin/python cli.py list-candidates --workflow tech_specialist_v1
```

**Show Candidate Details**
```bash
./venv/bin/python cli.py show-candidate candidate-001
```

**Update Candidate**
```bash
./venv/bin/python cli.py update-candidate candidate-001 --name "John Doe" --email "john@example.com"
```

**Complete a Task**
```bash
./venv/bin/python cli.py complete-task candidate-001 initial_screening_v1
```

**Sync with Server**
```bash
./venv/bin/python cli.py sync
```

**Run Migrations**
```bash
./venv/bin/python cli.py migrate
```

**Rotate Encryption Key**
```bash
./venv/bin/python cli.py rotate-key
```

## How It Works

### Encryption
- All sensitive candidate data is encrypted before sending to server
- Uses Fernet symmetric encryption with key derived from passphrase
- Server only stores encrypted blobs, never sees plaintext data

### Local Storage
- SQLite database stores decrypted data locally
- Located at `~/.hiring-client/local.db`
- Configuration at `~/.hiring-client/config.json`

### Sync
- Pulls changes from server since last sync
- Decrypts incoming data
- Encrypts outgoing changes
- Handles version conflicts with optimistic locking

### Schema Migrations
- Supports adding new fields to candidate schema
- Migrates both local and server data
- Version tracking ensures migrations run in order

### Key Rotation
- Allows changing encryption key
- Re-encrypts all data with new key
- Pushes updated encrypted data to server
- **Important**: Coordinate with team before rotating keys

## Architecture

```
cli.py          - Command-line interface
config.py       - Configuration management
database.py     - Local database setup
models.py       - Local data models (decrypted)
encryption.py   - Encryption/decryption
sync.py         - Server synchronization
migrations.py   - Schema migrations and key rotation
```

## Security Notes

1. **Encryption key** is stored in plaintext in `~/.hiring-client/config.json`
   - Keep this file secure
   - Don't commit it to version control

2. **Local database** contains decrypted data
   - Stored at `~/.hiring-client/local.db`
   - Secure your local filesystem

3. **Server** only has encrypted data
   - Safe even if server is compromised
   - But sync requires correct encryption key

## Future Extensions

This client is designed to be extended into a web app:
- Add HTTP server mode (e.g., Flask/FastAPI)
- Build web frontend
- Users run locally, access via browser
- Same encryption and sync logic
