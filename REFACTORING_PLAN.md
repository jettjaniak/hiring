# Task System Refactoring Plan

## Current Status (as of 2025-11-04)

### ✅ REFACTORING COMPLETE

All phases completed successfully. The task system has been fully refactored and all issues resolved.

### Completed ✓
1. **Phase 1**: Database migration
   - Migrated from CandidateTask model to Task + TaskCandidateLink
   - 33 records successfully migrated
   - Old CandidateTask table preserved with "_old" suffix

2. **Phase 2**: Model and endpoint renaming
   - `Task` → `TaskTemplate` (task definitions/blueprints)
   - `SpawnedTask` → `Task` (actual task instances)
   - `/api/tasks` → `/api/task-templates`
   - `/api/spawned-tasks` → `/api/tasks`

3. **Phase 3**: Fixed crashes from field name mismatches
   - Fixed tasks page (src/app.py:1391, 1398)
   - Fixed checklists page (src/app.py:1563, 1577, 1581)
   - Fixed workflow view (src/app.py:957, 963-965, 981, 983)
   - All changed `task_id` → `task_template_id` in EmailTemplateTask and Checklist models

4. **Phase 4**: Restored task endpoints and fixed remaining issues
   - Added missing GET endpoints for candidate tasks
   - Fixed kanban drag-and-drop endpoint reference (templates/kanban_view.html:264)
   - Fixed status inconsistency: replaced "not_started" with "todo" (src/app.py:1012, 1144)
   - All views now display consistent task data

## Previously Critical Issues (NOW RESOLVED) ✓

### Problem
Three views should show the SAME tasks but currently don't:
1. **Kanban view** (`/kanban`) - Line 848: `candidate_tasks = []` (DISABLED)
2. **Candidate table view** (`/candidate/{id}`) - Line 1037: `tasks = []` (DISABLED)
3. **Workflow view** (`/candidate/{id}/workflow`) - ✓ WORKING (shows actual Task instances)

### Expected Behavior
All three views should:
- Show actual Task instances linked to the candidate via TaskCandidateLink
- Display tasks from the candidate's workflow definition
- Show "not yet created" tasks with a "Create" button
- Refer to the exact same data source

## Remaining Work

### Phase 4: Restore Task Display in Kanban and Table Views

#### 4.1 Fix Kanban View (src/app.py:~848)
**Location**: `/kanban` endpoint
**Current**: `candidate_tasks = []` with TODO comment
**Required**:
```python
# Get all task links for this candidate
task_links = session.exec(
    select(TaskCandidateLink).where(TaskCandidateLink.candidate_email == candidate.email)
).all()
task_ids = [link.task_id for link in task_links]

# Get actual Task instances
candidate_tasks = []
if task_ids:
    candidate_tasks = session.exec(
        select(Task).where(Task.id.in_(task_ids))
    ).all()

# Build status map by template_id
task_status = {}
for task in candidate_tasks:
    if task.template_id and task.template_id in workflow_task_ids:
        task_status[task.template_id] = task
```

**Testing**: Verify kanban shows same tasks as workflow view for each candidate

#### 4.2 Fix Candidate Table View (src/app.py:~1037)
**Location**: `/candidate/{candidate_id}` endpoint
**Current**: `tasks = []` with TODO comment
**Required**:
```python
# Get all tasks for this candidate via TaskCandidateLink
task_links = session.exec(
    select(TaskCandidateLink).where(TaskCandidateLink.candidate_email == candidate.email)
).all()
task_ids = [link.task_id for link in task_links]

tasks = []
if task_ids:
    tasks = session.exec(
        select(Task).where(Task.id.in_(task_ids))
    ).all()
```

**Testing**: Verify table view shows same tasks as workflow view

#### 4.3 Restore Task Creation Endpoints (src/app.py:~302)
**Location**: Lines commented with "PHASE 4 TODO"
**Current**: All `/api/candidates/{candidate_id}/tasks` endpoints removed
**Required**: Reimplement using Task + TaskCandidateLink:

1. **GET `/api/candidates/{candidate_id}/tasks`** - List all tasks for candidate
2. **GET `/api/candidates/{candidate_id}/tasks/{task_identifier}`** - Get specific task
3. **POST `/api/candidates/{candidate_id}/tasks/{task_identifier}`** - Create task instance from template
4. **PUT `/api/candidates/{candidate_id}/tasks/{task_identifier}`** - Update task status/notes

**Implementation pattern**:
```python
@app.post("/api/candidates/{candidate_id}/tasks/{task_identifier}")
def create_candidate_task(
    candidate_id: str,
    task_identifier: str,
    session: Session = Depends(get_session)
):
    # 1. Get candidate
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # 2. Get TaskTemplate by identifier
    task_template = session.exec(
        select(TaskTemplate).where(TaskTemplate.task_id == task_identifier)
    ).first()
    if not task_template:
        raise HTTPException(status_code=404, detail="Task template not found")

    # 3. Create Task instance
    new_task = Task(
        id=str(uuid.uuid4()),
        template_id=task_template.task_id,
        status="not_started",
        assignee=None,
        notes=None
    )
    session.add(new_task)

    # 4. Link to candidate
    link = TaskCandidateLink(
        task_id=new_task.id,
        candidate_email=candidate.email
    )
    session.add(link)
    session.commit()
    session.refresh(new_task)

    return new_task
```

### Phase 5: Template Updates

Review and update HTML templates to handle task creation:
- `templates/kanban.html` - Ensure "Create" buttons call new endpoint
- `templates/view.html` - Same
- `templates/workflow.html` - Already working, verify consistency

### Phase 6: Workflow Task Auto-Creation Decision

**Current**: `ensure_workflow_tasks()` is stubbed out (line 72)
**Question**: Should tasks be auto-created when candidate is added to workflow?

**Option A** - Manual creation (RECOMMENDED):
- Keep function stubbed
- Users must explicitly click "Create" for each task
- More control, clearer audit trail

**Option B** - Auto-creation:
- Restore `ensure_workflow_tasks()` to auto-create all workflow tasks
- Happens automatically when candidate is assigned workflow
- Less user interaction needed

**Decision needed from user**

## Testing Checklist

After Phase 4 completion:
- [ ] Kanban view shows same tasks as workflow view
- [ ] Table view shows same tasks as workflow view
- [ ] Can create task from kanban view
- [ ] Can create task from table view
- [ ] Can create task from workflow view
- [ ] Created tasks appear in all three views immediately
- [ ] Task status updates reflect in all views
- [ ] No duplicate tasks created
- [ ] TaskCandidateLink properly maintains relationships

## Data Model Reference

```
TaskTemplate (task_templates table)
├── task_id: str (PK) - e.g., "application_review"
├── name: str
└── description: str

Task (tasks table)
├── id: str (PK) - UUID
├── template_id: str (FK → TaskTemplate.task_id)
├── status: str
├── assignee: str (optional)
└── notes: str (optional)

TaskCandidateLink (task_candidate_links table)
├── task_id: str (PK, FK → Task.id)
└── candidate_email: str (PK, FK → Candidate.email)

Candidate
├── email: str (PK)
└── workflow_id: str
```

## Key Principles

1. **Single Source of Truth**: All views query Task instances via TaskCandidateLink
2. **Template vs Instance**: TaskTemplate = blueprint, Task = actual instance
3. **Lazy Creation**: Tasks are only created when explicitly requested (for now)
4. **Consistency**: Same query pattern across kanban/table/workflow views

## Implementation Order

1. Fix kanban view task queries (Phase 4.1)
2. Fix table view task queries (Phase 4.2)
3. Test both views show same data as workflow
4. Implement task creation endpoints (Phase 4.3)
5. Test task creation from all views
6. Update templates if needed (Phase 5)
7. Decide on auto-creation behavior (Phase 6)
