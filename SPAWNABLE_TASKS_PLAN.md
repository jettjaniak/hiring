# Spawnable Tasks Implementation Plan

## Overview
Transform tasks from fixed workflow steps into spawnable work items that can be created from templates or ad-hoc.

## Design Decisions (from discussion)
1. ✅ Keep DAG visualization - dependencies help spawn correct tasks
2. ✅ One spawn per template per candidate (no duplicates)
3. ✅ Keep it simple - minimal fields, basic functionality
4. ✅ Tasks visible in Kanban, can be reopened
5. ✅ Can add/remove candidate associations
6. ✅ Migrate existing CandidateTask → SpawnedTask
7. ✅ Email templates/checklists/special actions only on templates

---

## Stage 1: Data Model & Migration
**Goal:** Add new tables, migrate existing data without breaking anything

### 1.1 Create New Models
```python
# Rename: Task → TaskTemplate
# Keep existing Task model structure

# New model: SpawnedTask
class SpawnedTask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    status: str = "todo"  # todo, in_progress, done
    template_id: Optional[str] = None  # FK to TaskTemplate
    workflow_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# New model: TaskCandidateLink (many-to-many)
class TaskCandidateLink(SQLModel, table=True):
    task_id: int = Field(foreign_key="spawnedtask.id", primary_key=True)
    candidate_email: str = Field(foreign_key="candidate.email", primary_key=True)
```

### 1.2 Database Migration
- Add `spawned_tasks` table
- Add `task_candidate_links` table
- Migrate data from `candidate_tasks`:
  - For each CandidateTask: create SpawnedTask + TaskCandidateLink
  - Map status: not_started→todo, in_progress→in_progress, completed→done, na→done
- Keep `candidate_tasks` table temporarily for rollback safety

### 1.3 Testing
- ✅ Unit tests: Model creation, relationships
- ✅ Migration test: Verify all CandidateTask data migrated correctly
- ✅ Manual: Check database schema with `sqlite3 .schema`

**Commit:** "Stage 1: Add SpawnedTask and TaskCandidateLink models with migration"

---

## Stage 2: Backend - Task Spawning API
**Goal:** Create endpoints to spawn and manage tasks

### 2.1 Spawn Task Endpoint
```python
POST /api/tasks/spawn
{
  "template_id": "phone_screen_v1",
  "candidate_emails": ["candidate@example.com"],
  "title": "Phone Screen", # optional, defaults to template name
  "description": "..." # optional
}

# Business logic:
# - Check: Has this template already been spawned for this candidate?
# - If yes: return existing task
# - If no: create new SpawnedTask + TaskCandidateLinks
```

### 2.2 CRUD Endpoints for SpawnedTasks
```python
GET    /api/tasks          # List all spawned tasks (with filters)
GET    /api/tasks/{id}     # Get single task
POST   /api/tasks          # Create ad-hoc task (no template)
PUT    /api/tasks/{id}     # Update task (title, description, status)
DELETE /api/tasks/{id}     # Delete task
```

### 2.3 Candidate Association Endpoints
```python
POST   /api/tasks/{id}/candidates     # Add candidates to task
DELETE /api/tasks/{id}/candidates/{email}  # Remove candidate from task
GET    /api/tasks/{id}/candidates     # List candidates for task
```

### 2.4 Testing
- ✅ Unit tests: Spawn logic, duplicate prevention
- ✅ Unit tests: CRUD operations
- ✅ Unit tests: Candidate association add/remove
- ✅ Manual: curl test all endpoints
  ```bash
  # Test spawn
  curl -X POST http://localhost:8000/api/tasks/spawn \
    -H "Content-Type: application/json" \
    -d '{"template_id":"phone_screen_v1","candidate_emails":["test@example.com"]}'

  # Test duplicate prevention
  # (run same curl twice, should return same task)

  # Test status update
  curl -X PUT http://localhost:8000/api/tasks/1 \
    -H "Content-Type: application/json" \
    -d '{"status":"in_progress"}'
  ```

**Commit:** "Stage 2: Add task spawning and management API endpoints"

---

## Stage 3: Kanban View UI
**Goal:** Create Kanban board to view and manage spawned tasks

### 3.1 Backend Endpoint
```python
GET /tasks/kanban  # Returns HTML kanban view
GET /api/tasks/kanban  # Returns JSON: {todo: [...], in_progress: [...], done: [...]}
```

### 3.2 Frontend Template
- Create `templates/kanban_view.html`
- Three columns: To Do | In Progress | Done
- Each card shows:
  - Title
  - Associated candidates (avatars/names)
  - Template badge (if from template)
  - Actions: Move status, View details, Delete
- Drag & drop to change status (JavaScript)

### 3.3 Navigation
- Add "Kanban" link to main navigation (templates/base.html)

### 3.4 Testing
- ✅ Manual: Open http://localhost:8000/tasks/kanban
- ✅ Manual: Verify tasks appear in correct columns
- ✅ Manual: Move task between columns
- ✅ Manual: Click task to view details

**Commit:** "Stage 3: Add Kanban board view for spawned tasks"

---

## Stage 4: Workflow View Integration
**Goal:** Update workflow view to show spawn buttons

### 4.1 Update Workflow View
- For each task template in workflow:
  - Show existing spawned task status (if exists)
  - OR show "Spawn Task" button
  - No dependency checking - allow spawning any task

### 4.2 Spawn from Workflow
```javascript
// Add onclick handler
function spawnTask(templateId, candidateEmail, workflowId) {
  fetch('/api/tasks/spawn', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      template_id: templateId,
      candidate_emails: [candidateEmail],
      workflow_id: workflowId
    })
  }).then(() => location.reload());
}
```

### 4.3 Update Task Status Display
- Instead of CandidateTask.status, show SpawnedTask.status
- Map: todo→not_started, in_progress→in_progress, done→completed

### 4.4 Testing
- ✅ Manual: Go to candidate workflow view
- ✅ Manual: Click "Spawn Task" button
- ✅ Manual: Verify task appears in Kanban
- ✅ Manual: Verify duplicate spawn prevention works
- ✅ Manual: Complete task, verify DAG updates

**Commit:** "Stage 4: Integrate task spawning into workflow view"

---

## Stage 5: Task Detail View
**Goal:** Create detailed view for individual tasks

### 5.1 Task Detail Page
```
GET /tasks/{id}
```
Shows:
- Title (editable)
- Description (editable)
- Status dropdown (todo/in_progress/done)
- Associated candidates:
  - List with remove buttons
  - Add candidate dropdown
- Template info (if spawned from template)
- Actions available (from template: emails, checklists, special actions)
- Created/updated timestamps

### 5.2 Testing
- ✅ Manual: Click task from Kanban → opens detail view
- ✅ Manual: Edit title and description
- ✅ Manual: Change status
- ✅ Manual: Add/remove candidates
- ✅ Manual: Trigger email template from task

**Commit:** "Stage 5: Add task detail view with editing capabilities"

---

## Stage 6: Ad-hoc Task Creation
**Goal:** Allow creating tasks not from templates

### 6.1 Create Task Form
```
GET /tasks/new
POST /tasks/create
```
Form fields:
- Title (required)
- Description (optional)
- Candidate associations (multi-select)
- Initial status (default: todo)

### 6.2 Add to Navigation
- "Create Task" button in Kanban view
- "Create Task" button in candidate detail view (pre-selects candidate)

### 6.3 Testing
- ✅ Manual: Click "Create Task" from Kanban
- ✅ Manual: Fill form and submit
- ✅ Manual: Verify task appears in Kanban
- ✅ Manual: Create task from candidate view, verify pre-selection

**Commit:** "Stage 6: Add ad-hoc task creation"

---

## Stage 7: Cleanup & Deprecation
**Goal:** Remove old CandidateTask table

### 7.1 Remove CandidateTask References
- Update all code using CandidateTask to use SpawnedTask
- Remove CandidateTask model from models.py
- Drop `candidate_tasks` table

### 7.2 Update Tests
- Remove CandidateTask tests
- Ensure all tests use SpawnedTask

### 7.3 Testing
- ✅ Run full test suite: `./venv/bin/pytest tests/ -v`
- ✅ Manual: Full user journey test
  1. Create candidate
  2. Assign workflow
  3. Spawn tasks from workflow
  4. Move tasks in Kanban
  5. Create ad-hoc task
  6. Complete all tasks
  7. Verify everything works

**Commit:** "Stage 7: Remove deprecated CandidateTask model"

---

## Testing Checklist (After Each Stage)

### Automated Tests
```bash
# Run tests
./venv/bin/pytest tests/ -v

# Check coverage
./venv/bin/pytest --cov=src tests/
```

### Manual Testing
```bash
# Check server status
curl http://localhost:8000/ -I

# Restart if needed
./restart_server.sh

# Test specific endpoints (varies by stage)
curl http://localhost:8000/api/tasks
curl http://localhost:8000/tasks/kanban
```

### Browser Testing
- Navigate to http://localhost:8000
- Test all user flows
- Check browser console for errors
- Verify database changes with:
  ```bash
  sqlite3 ~/.hiring-client/hiring.db "SELECT * FROM spawned_tasks;"
  ```

---

## Rollback Plan
If anything breaks:
1. Git checkout previous commit
2. CandidateTask table still exists (until Stage 7)
3. Can roll back database with backup

## Success Criteria
- ✅ All existing tests pass
- ✅ New tests added for spawnable tasks
- ✅ Kanban view shows all tasks
- ✅ Can spawn tasks from workflow
- ✅ Can create ad-hoc tasks
- ✅ Can manage candidate associations
- ✅ Workflow DAG still works
- ✅ No duplicate spawns per candidate per template
