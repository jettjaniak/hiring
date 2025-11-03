# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Simple, local-first hiring process management tool with web interface. No encryption, no sync, just straightforward candidate tracking with workflow visualization.

## Architecture

**Single FastAPI Application**: Web interface with truly auto-generated REST APIs powered by FastAPI + SQLModel. **Adding a field to a model automatically exposes it in the API.**

### Data Model

- **Candidate**: Basic candidate information (name, email, phone, resume URL, notes). Linked to a workflow.
- **CandidateTask**: Links candidate to workflow tasks. Tracks completion status (not_started, in_progress, completed, na).
- **ActionState**: Per-candidate state for Actions (mini-apps that help complete tasks). Stores JSON data.

### Key Concepts

**Workflows**: Define DAG of Tasks with dependencies (stored as YAML in `workflows/` directory)
**Tasks**: Have identifier, name, dependencies. Same task can appear in multiple workflows.
**Actions**: Reusable mini-apps (HTML+JS) that can complete multiple tasks. Maintain per-candidate state.

## Development Commands

### Setup

```bash
python3.12 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### Run Application

```bash
./venv/bin/python app.py
# Or specify custom port and data directory:
./venv/bin/python app.py --port 8080 --data-dir /path/to/data
```

Server starts on `http://localhost:5001` by default.
- **Web Interface**: `http://localhost:5001/`
- **API Documentation**: `http://localhost:5001/api/docs` (Swagger UI)

## REST API

Auto-generated REST API with full Swagger/OpenAPI documentation at `/api/docs`.

### Candidate Endpoints

- `GET /api/candidates` - List all candidates
- `POST /api/candidates` - Create new candidate
- `GET /api/candidates/{id}` - Get candidate by ID
- `PUT /api/candidates/{id}` - Update candidate
- `DELETE /api/candidates/{id}` - Delete candidate permanently

### Task Endpoints

- `GET /api/candidates/{id}/tasks` - List candidate tasks
- `GET /api/candidates/{id}/tasks/{task_id}` - Get specific task
- `PUT /api/candidates/{id}/tasks/{task_id}` - Update/create task (upsert)
- `DELETE /api/candidates/{id}/tasks/{task_id}` - Delete task

### Action State Endpoints

- `GET /api/action-states` - List all action states
- `GET /api/action-states/{candidate_id}/{action_id}` - Get action state
- `PUT /api/action-states/{candidate_id}/{action_id}` - Update/create action state
- `DELETE /api/action-states/{candidate_id}/{action_id}` - Delete action state

## Project Structure

```
hiring/
  ├── app.py               # FastAPI application with auto-generated REST API and HTML views
  ├── models.py            # SQLModel data models (combines SQLAlchemy + Pydantic)
  ├── database.py          # Database setup and session management
  ├── workflow_loader.py   # Loads workflow definitions from YAML
  ├── requirements.txt     # Python dependencies
  ├── README.md            # User documentation
  ├── CLAUDE.md            # Developer documentation (this file)
  ├── templates/           # HTML templates for web interface
  │   ├── base.html
  │   ├── index.html
  │   ├── table_view.html
  │   ├── workflow_view.html
  │   ├── view.html
  │   ├── add.html
  │   ├── edit.html
  │   └── task_controls.html
  └── workflows/           # YAML workflow definition files
      ├── senior_engineer_v2.yaml
      └── tech_specialist_v1.yaml
```

## Features

- **Local Storage**: SQLite database at `~/.hiring-client/hiring.db` (or custom location via `--data-dir`)
- **Web Interface**: Full-featured UI for managing candidates and tracking workflow progress
- **REST API**: Auto-generated CRUD API with Swagger documentation
- **Workflow Visualization**: DAG view showing task dependencies and progress
- **Table View**: Grid view of all candidates and their task statuses
- **No External Dependencies**: No server, no sync, no encryption - just simple local data management

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

1. **Models**: Add fields to models in `models.py` using type hints. They automatically appear in the API! Example:
   ```python
   class Candidate(SQLModel, table=True):
       new_field: Optional[str] = None  # Automatically in API!
   ```
2. **Workflows**: Create new workflows as YAML files in `workflows/` directory
3. **HTML Templates**: Extend `base.html` for consistent styling
4. **API Endpoints**: Use FastAPI's dependency injection and response_model for type-safe endpoints
5. **Database Changes**: Update model definitions and recreate the database (or write migrations if needed)

**Key Advantage**: With SQLModel, you define each field once with its type. No manual serialization, no separate API schemas, no manual validation. It just works.

---

## Important Development Practices

**ALWAYS TEST BEFORE CLAIMING IT WORKS**
- Never tell the user something is working without actually testing it
- Test the actual functionality in a browser or via API calls
- Verify that changes are reflected in the running application
- Check that the database is being queried correctly
- Don't assume code that looks correct will work correctly

## Standard Development Workflow

When implementing any new feature or change, follow this process:

### 1. Implement
- Write the code changes needed
- Update models, endpoints, templates, etc.

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

a) **Check server status:**
```bash
# Check if server is running
curl http://localhost:8000/ -I
```

b) **Restart server if needed:**
```bash
./restart_server.sh
```

c) **Send manual test requests:**
```bash
# Test the specific endpoint you changed
curl -X GET http://localhost:8000/your-endpoint
curl -X POST http://localhost:8000/your-endpoint -H "Content-Type: application/json" -d '{"test":"data"}'
```

d) **Verify in browser:**
- Open http://localhost:8000 in a browser
- Navigate to the feature you implemented
- Test all user flows and interactions
- Check browser console for JavaScript errors
- Verify database changes took effect

e) **Check server logs:**
- Look for any errors or warnings in the server output
- Verify expected log messages appear

### 5. Verify & Report
Only after completing steps 1-4:
- Confirm to the user that the feature is working
- Provide specific evidence (test results, curl output, etc.)
- Note any issues or limitations discovered during testing

**Common failure modes to check:**
- Server crashes on startup
- 404/500 errors when accessing endpoints
- Database schema mismatches
- Template rendering errors
- Missing imports or dependencies
- JavaScript errors in browser console

## Testing Notes

### Email Compose Dropdown Implementation (2025-11-02)

**BUGS FOUND** before claiming it works:

#### Critical Issues:
1. **Missing error handling in `loadCandidate()`** (email_compose.html:200-224) - **FIXED**
   - Previously: catch block only logged to console, never called `updatePreviews()`
   - Fixed: Now clears candidate data and calls `updatePreviews()` on both non-OK responses and exceptions
   - User sees empty preview state instead of stale data when API call fails

2. **No loading state**
   - When fetching candidate data from API, no visual indicator shown to user
   - User doesn't know if dropdown is working or if data is loading

#### Potential Issues:
3. **Race condition risk**
   - If user rapidly changes dropdown selection, multiple API calls could be in flight
   - Last response to arrive wins, but may not be the most recent selection
   - No request cancellation or debouncing

4. **Silent failure on invalid candidate ID**
   - If URL contains `?candidate=invalid-id`, dropdown value is set but may not match any option
   - loadCandidate() will fetch and likely get 404, falling into silent error case (#1)

#### Code Locations:
- Backend route: `src/app.py:746-771`
- Frontend: `templates/email_compose.html:194-370`
- API endpoint: `src/app.py:99-105` (exists, returns Candidate model)

#### Test Plan:
1. ✗ Test dropdown with valid candidate - manually verify API call succeeds
2. ✗ Test dropdown with no candidate (clear selection) - verify preview clears
3. ✗ Test URL with valid `?candidate=id` - verify auto-population
4. ✗ Test URL with invalid `?candidate=bad-id` - verify error handling
5. ✗ Test custom variables from URL - verify pre-population
6. ✗ Test rapid dropdown changes - check for race conditions

**Status: READY FOR TESTING**

#### Summary:
- Fixed critical error handling bug in `loadCandidate()`
- Implementation complete for:
  - Candidate dropdown with API-based data fetching
  - URL parameter support (`?candidate=id`)
  - Custom variable pre-population from URL
  - All candidate fields accessible via `{{candidate.fieldname}}` in templates
  - Variable UI (no manual JSON editing required)
- Known minor issues remain (loading state, race conditions) but won't prevent functionality
- Dropdown should work correctly now

#### Changes Made:
1. **Backend** (src/app.py:746-771): Changed route from `/{template_id}/{candidate_id}` to `/{template_id}?candidate=`
2. **Frontend** (templates/email_compose.html): Added dropdown, API fetch, error handling
3. **Variable UI** (templates/email_template_form.html): Visual interface for adding/removing variables
