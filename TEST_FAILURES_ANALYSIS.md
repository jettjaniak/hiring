# Test Failures Analysis

## Summary
19 tests failing. Root causes identified and categorized below.

## Failure Categories

### Category 1: TestAPITasks (4 failures)
**Root Cause**: Missing DELETE endpoint for candidate tasks

**Failures**:
1. `test_create_task` - ACTUAL: Working, but returns 404 (likely data issue)
2. `test_list_tasks` - ACTUAL: Returns 0 tasks instead of 2
3. `test_update_task_status` - ACTUAL: Returns 404 (likely data issue)
4. `test_delete_task` - **MISSING ENDPOINT**: `DELETE /api/candidates/{email}/tasks/{task_identifier}`

**Fix Required**:
- Add DELETE endpoint at src/app.py (missing endpoint)
- Investigate why PUT requests return 404 (may be data/database issue)

### Category 2: TestAPITaskDefinitions (5 failures)
**Root Cause**: Tests call wrong endpoints - using `/api/tasks` instead of `/api/task-templates`

The tests expect to work with TaskTemplate model (task_id, name, description) but call `/api/tasks` which expects Task model (id, title, status).

**Failures**:
1. `test_create_task` - Expects 201, gets 422 (validation error)
2. `test_list_tasks` - Returns 0 items
3. `test_get_task` - Expects 200, gets 422
4. `test_update_task` - Expects 200, gets 422
5. `test_delete_task` - Expects 204, gets 422

**Fix Options**:
A. **Fix the tests** - Change `/api/tasks` to `/api/task-templates` in all tests
B. **Add endpoint aliases** - Make `/api/tasks` work for both models (complex, not recommended)
C. **Keep tests as-is, fix endpoints** - Make `/api/tasks` work with task_id/name/description (breaks existing functionality)

**Recommended Fix**: Option A - Update tests to use correct endpoints (`/api/task-templates`)

### Category 3: TestWorkflowValidation (1 failure)
**Root Cause**: Test tries to create Task records with wrong field names

**Failure**: `test_workflow_with_all_valid_task_ids` - "NOT NULL constraint failed: tasks.title"

**Problem**: Test line 448 creates Task with fields (`task_id`, `name`, `description`) but Task model requires:
- `title` (not `name`) - REQUIRED, NOT NULL
- No `task_id` field (uses auto-increment `id`)

**Fix Required**: Update test to use correct Task model fields:
```python
# WRONG (current):
task1 = Task(task_id="valid_task_1", name="Valid Task 1", description="Test task 1")

# CORRECT (should be):
task1 = Task(title="Valid Task 1", description="Test task 1")
```

### Category 4: TestTaskTemplateWebForms (3 failures)
**Root Cause**: Multiple issues with form submissions and database constraints

**Failures**:
1. `test_create_task_with_templates` - SQLAlchemy warning about EmailTemplateTask.task_template_id
2. `test_edit_task_template_links` - Unknown (need detailed trace)
3. `test_create_template_with_tasks` - SQLAlchemy warning about EmailTemplateTask.task_template_id

**Problem**: EmailTemplateTask table has composite primary key but one column (task_template_id) isn't being set properly

**Investigation Needed**:
- Check POST /tasks/add endpoint (line 1612)
- Check POST /template/add endpoint (line 1376)
- Verify EmailTemplateTask creation logic

### Category 5: TestChecklistOperations (6 failures)
**Root Cause**: Multiple endpoint issues - 404s suggest routing problems

**Failures**:
1. `test_create_checklist` - Expects redirect (302/303), gets 404
2. `test_checklist_one_to_one_constraint` - Unknown
3. `test_edit_checklist` - Expects redirect, gets 404
4. `test_checklist_state_save_and_retrieve` - Expects 200, gets 404
5. `test_checklist_state_update` - Expects 200, gets 404
6. `test_checklist_view_page_loads` - Expects 200, gets 404

**Endpoints Being Tested**:
- `POST /checklists/add` - EXISTS (line 1775)
- `POST /checklists/{id}/edit` - EXISTS (line 1846)
- `POST /api/checklist/{id}/save` - EXISTS (line 1976)
- `GET /checklist/{id}/view` - EXISTS (line 1890)

**Problem**: Endpoints exist but return 404. Likely issues:
- Incorrect parameter names (e.g., test uses `task_id` but endpoint expects `task_template_id`)
- Database foreign key constraints failing
- Test setup issues (missing TaskTemplate records)

**Investigation Needed**:
- Check Checklist model field names (line 30-42 in models.py)
- Verify tests create necessary TaskTemplate records first

## Action Plan

### Phase 1: Quick Wins
1. ✅ Analyze all failures (this document)
2. Fix TestAPITaskDefinitions - change `/api/tasks` to `/api/task-templates` in tests
3. Fix TestWorkflowValidation - use correct Task model fields
4. Add missing DELETE endpoint for candidate tasks

### Phase 2: Investigation Required
5. Debug TestTaskTemplateWebForms - trace form submissions
6. Debug TestChecklistOperations - verify test setup and parameter names
7. Fix root causes identified in Phase 2

### Phase 3: Verification
8. Run full test suite again
9. Verify all 37 tests pass
10. Update documentation

## Files to Modify

### Tests to Fix:
- `tests/test_app.py` lines 501-588 (TestAPITaskDefinitions) - change endpoints
- `tests/test_app.py` lines 426-498 (TestWorkflowValidation) - use correct model fields

### Endpoints to Add:
- `src/app.py` - Add DELETE /api/candidates/{email}/tasks/{task_identifier}

### Endpoints to Debug:
- `src/app.py` lines 1612-1650 (POST /tasks/add)
- `src/app.py` lines 1775-1820 (POST /checklists/add)
- `src/app.py` lines 1890-1935 (GET /checklist/{id}/view)

## Expected Outcome
After fixes: 37/37 tests passing (100%)
