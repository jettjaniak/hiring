# App.py Modularization Plan

**Status**: Planning complete. Ready for implementation.  
**Current**: All tests passing (37/37), application fully functional  
**Goal**: Refactor src/app.py (2,206 lines, 68 endpoints) into modular structure

---

## Summary

### Proposed Structure
- **13 route modules** (6 API + 7 Web UI)
- **8 utility modules** (shared helpers)
- **100+ lines of duplicate code eliminated**
- **~12 hours implementation time**

### Current Problems
1. Monolithic 2,206-line file
2. Code duplication (10+ major patterns, 38+ instances)
3. Poor separation of concerns
4. Hard to test and maintain
5. Difficult team collaboration

### Expected Benefits
- Lines: 2,206 → ~1,900 (after deduplication)
- Avg file size: ~100-150 lines
- Zero duplication patterns
- Better maintainability and testability
- Easier onboarding and collaboration

---

## New Directory Structure

```
src/
├── app.py                          # Main app (~80 lines, down from 2,206!)
├── dependencies.py                 # FastAPI dependencies (~10 lines)
├── pydantic_models.py             # Request/response models (~35 lines)
│
├── routes/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── candidates.py          # ~80 lines (5 endpoints)
│   │   ├── task_templates.py      # ~135 lines (5 endpoints)
│   │   ├── candidate_tasks.py     # ~165 lines (5 endpoints)
│   │   ├── spawnable_tasks.py     # ~270 lines (9 endpoints)
│   │   ├── task_template_links.py # ~155 lines (6 endpoints)
│   │   └── kanban.py              # ~45 lines (1 endpoint)
│   │
│   └── web/
│       ├── __init__.py
│       ├── candidates.py          # ~345 lines (9 endpoints)
│       ├── task_templates.py      # ~165 lines (6 endpoints)
│       ├── email_templates.py     # ~215 lines (8 endpoints)
│       ├── checklists.py          # ~155 lines (6 endpoints)
│       ├── checklist_state.py     # ~125 lines (3 endpoints)
│       ├── kanban.py              # ~10 lines (1 endpoint)
│       └── special_actions.py     # ~155 lines (4 endpoints)
│
└── utils/
    ├── __init__.py
    ├── database.py                # ~120 lines (query helpers)
    ├── workflow.py                # ~150 lines (workflow helpers)
    ├── email_template.py          # ~50 lines (template helpers)
    ├── validation.py              # ~30 lines (validation)
    ├── forms.py                   # ~40 lines (form processing)
    └── responses.py               # ~20 lines (response helpers)
```

---

## Implementation Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1: Extract utilities | 4 hours | 8 modules + deduplication |
| Phase 2: Split API routes | 3 hours | 6 API modules |
| Phase 3: Split web routes | 4 hours | 7 web modules |
| Phase 4: Simplify main app | 1 hour | Final app.py (~80 lines) |
| **TOTAL** | **12 hours** | **22 modules** |

---

## Phase 1: Extract Utility Modules (4 hours)

### 1.1: `src/utils/database.py` (~120 lines)

**Eliminates 60+ instances of duplicated database code**

```python
def get_or_404(session, model, id, entity_name="Entity"):
    """Get entity or raise 404 (eliminates 38+ instances)"""
    
def save_and_refresh(session, entity):
    """Save and refresh entity (eliminates 15+ instances)"""
    
def get_candidate_tasks(session, candidate_email) -> List[Task]:
    """Get tasks for candidate via TaskCandidateLink (4 instances)"""
    
def get_task_email_templates(session, task_id) -> List[EmailTemplate]:
    """Get email templates for task (4 instances)"""
    
def get_template_tasks(session, template_id) -> List[TaskTemplate]:
    """Get tasks for email template (4 instances)"""
    
def link_task_to_templates(session, task_id, template_ids):
    """Link task to templates (2 instances)"""
    
def unlink_task_from_all_templates(session, task_id):
    """Unlink task from all templates (2 instances)"""
```

**Savings**: ~174 lines (114 from get_or_404 + 60 from save_and_refresh)

### 1.2: `src/utils/validation.py` (~30 lines)

```python
def validate_status(status: str):
    """Validate task status (5 instances)"""
    
def validate_candidates_exist(session, emails: List[str]):
    """Validate candidates exist (5 instances)"""
```

### 1.3: `src/utils/forms.py` (~40 lines)

```python
def parse_checklist_items(items_text: str) -> str:
    """Parse checklist items to JSON (2 instances)"""
    
def checklist_items_to_text(items_json: str) -> str:
    """Convert JSON to text (2 instances)"""
    
def build_document_replacements(form_data, exclude_keys) -> dict:
    """Build document replacements (2 instances)"""
```

### 1.4: `src/utils/workflow.py` (~150 lines)

```python
def compute_dag_layout(workflow) -> Tuple[dict, int]:
    """Compute DAG layout (move from app.py:884-972)"""
    
def build_candidate_task_status_map(...) -> Dict[str, Task]:
    """Build task status map (2 large blocks)"""
    
def get_workflow_task_states(...) -> Dict[str, dict]:
    """Get workflow task states (2 large blocks)"""
```

### 1.5: `src/utils/email_template.py` (~50 lines)

```python
def infer_template_variables(...) -> List[dict]:
    """Infer Jinja2 variables (move from app.py:1322-1367)"""
```

### 1.6: `src/utils/responses.py` (~20 lines)

```python
def redirect_to(url: str) -> RedirectResponse:
    """Standard redirect (eliminates 22+ instances)"""
    
def stream_document(doc_bytes, filename, media_type) -> StreamingResponse:
    """Stream document file (2 instances)"""
```

### 1.7: `src/pydantic_models.py` (~35 lines)

Move Pydantic models from app.py:459-482, 1995-1998

```python
class SpawnTaskRequest(BaseModel): ...
class CreateTaskRequest(BaseModel): ...
class UpdateTaskRequest(BaseModel): ...
class AddCandidatesRequest(BaseModel): ...
class ChecklistSaveRequest(BaseModel): ...
```

### 1.8: `src/dependencies.py` (~10 lines)

Move `get_session()` from app.py:67-69

**Testing**: After each utility module, import in app.py, replace duplicated code, run test suite.

---

## Phase 2: Split API Routes (3 hours)

### API Router Module Template

```python
"""<Domain> API routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from ...models import <Models>
from ...dependencies import get_session
from ...utils import <utilities>

router = APIRouter()

@router.get("/endpoint")
def handler(session: Session = Depends(get_session)):
    """Endpoint docs"""
    pass
```

### 2.1: `src/routes/api/candidates.py` (~80 lines, 5 endpoints)

- POST /api/candidates
- GET /api/candidates
- GET /api/candidates/{candidate_id}
- PUT /api/candidates/{candidate_id}
- DELETE /api/candidates/{candidate_id}

### 2.2: `src/routes/api/task_templates.py` (~135 lines, 5 endpoints)

- GET /api/task-templates
- GET /api/task-templates/{task_id}
- POST /api/task-templates
- PUT /api/task-templates/{task_id}
- DELETE /api/task-templates/{task_id}

### 2.3: `src/routes/api/candidate_tasks.py` (~165 lines, 5 endpoints)

- GET /api/candidates/{email}/tasks
- GET /api/candidates/{email}/tasks/{identifier}
- POST /api/candidates/{email}/tasks/{identifier}
- PUT /api/candidates/{email}/tasks/{identifier}
- DELETE /api/candidates/{email}/tasks/{identifier}

### 2.4: `src/routes/api/spawnable_tasks.py` (~270 lines, 9 endpoints)

- POST /api/task-templates/spawn
- GET /api/tasks
- GET /api/tasks/{task_id}
- POST /api/tasks
- PUT /api/tasks/{task_id}
- DELETE /api/tasks/{task_id}
- GET /api/tasks/{task_id}/candidates
- POST /api/tasks/{task_id}/candidates
- DELETE /api/tasks/{task_id}/candidates/{email}

### 2.5: `src/routes/api/task_template_links.py` (~155 lines, 6 endpoints)

- GET /api/task-templates/{task_id}/templates
- PUT /api/task-templates/{task_id}/templates/{template_id}
- DELETE /api/task-templates/{task_id}/templates/{template_id}
- GET /api/templates/{template_id}/tasks
- PUT /api/templates/{template_id}/tasks/{task_id}
- DELETE /api/templates/{template_id}/tasks/{task_id}

### 2.6: `src/routes/api/kanban.py` (~45 lines, 1 endpoint)

- GET /api/tasks/kanban

**Testing**: Run test suite after each module (37/37 expected)

---

## Phase 3: Split Web UI Routes (4 hours)

### 3.1-3.7: Web Route Modules

Similar pattern to API routes, but for web UI endpoints:

- `candidates.py` - 9 endpoints, ~345 lines
- `task_templates.py` - 6 endpoints, ~165 lines  
- `email_templates.py` - 8 endpoints, ~215 lines
- `checklists.py` - 6 endpoints, ~155 lines
- `checklist_state.py` - 3 endpoints, ~125 lines
- `kanban.py` - 1 endpoint, ~10 lines
- `special_actions.py` - 4 endpoints, ~155 lines

**Testing**: Run test suite + manual UI testing after each module

---

## Phase 4: Simplify Main App (1 hour)

### Final `src/app.py` (~80 lines)

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from .database import Database
from .workflow_loader import WorkflowLoader

# Import all routers
from .routes.api import (
    candidates, task_templates, candidate_tasks,
    spawnable_tasks, task_template_links, kanban
)
from .routes.web import (
    candidates as web_candidates,
    task_templates as web_task_templates,
    email_templates, checklists, checklist_state,
    kanban as web_kanban, special_actions
)

app = FastAPI(title="Hiring Management System", version="1.0.0")

# Setup
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

db = Database()
workflow_loader = WorkflowLoader(db=db)
app.state.db = db
app.state.workflow_loader = workflow_loader
app.state.templates = templates

# Include routers
app.include_router(candidates.router, prefix="/api", tags=["Candidates API"])
app.include_router(task_templates.router, prefix="/api", tags=["Task Templates API"])
# ... (all other routers)

if __name__ == "__main__":
    import uvicorn, argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)
```

---

## Code Deduplication Examples

### Before: Entity Retrieval (38+ instances)
```python
entity = session.get(Model, id)
if not entity:
    raise HTTPException(status_code=404, detail="Entity not found")
```

### After:
```python
entity = get_or_404(session, Model, id, "Entity")
```
**Savings**: 114 lines

### Before: Commit and Refresh (15+ instances)
```python
session.add(entity)
session.commit()
session.refresh(entity)
```

### After:
```python
save_and_refresh(session, entity)
```
**Savings**: 60 lines

### Before: Redirects (22+ instances)
```python
return RedirectResponse(url="/some/path", status_code=302)
```

### After:
```python
return redirect_to("/some/path")
```
**Savings**: Cleaner, more consistent

---

## Testing Strategy

### After Each Phase
1. Run test suite: `./venv/bin/pytest tests/ -v`
2. Manual smoke tests on 5 key endpoints
3. Verify web forms load
4. Git commit: `git commit -m "Phase X: <description>"`

### Final Verification
- Full test suite: 37/37 passing
- Manual testing: All pages and endpoints
- Code review: Check imports
- Update README

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Import errors | Test after each module |
| Circular dependencies | Keep utilities independent |
| Template paths | Use relative paths from BASE_DIR |
| Session management | Centralize in dependencies.py |
| Test failures | Run suite after each phase |

---

## Next Steps

1. ✓ Analyze app.py structure
2. ✓ Create this plan
3. Get approval to proceed
4. Start Phase 1 (utilities)
5. Iterate through phases
6. Document lessons learned

**Ready to begin implementation on approval.**
