#!/usr/bin/env python3
"""
Remove CandidateTask references from src/app.py.
These features will be reimplemented in Phase 4 using Task+TaskCandidateLink.
"""
import re

def fix_candidate_task_refs():
    with open('src/app.py', 'r') as f:
        content = f.read()

    print("Fixing CandidateTask references...")

    # 1. Stub out ensure_workflow_tasks function
    # Replace its body to be a simple pass
    ensure_tasks_pattern = r'(def ensure_workflow_tasks\([^)]+\):.*?"""[^"]*""")(.*?)(^@app\.|^def\s)'

    def replace_ensure_tasks(match):
        func_def = match.group(1)
        next_section = match.group(3)
        return f'''{func_def}
    # PHASE 6 TODO: Remove auto-creation - users will create tasks manually
    pass


{next_section}'''

    content = re.sub(ensure_tasks_pattern, replace_ensure_tasks, content, flags=re.MULTILINE | re.DOTALL)

    # 2. Remove CandidateTask API endpoints
    # Find and remove @app.get("/api/candidates/{candidate_id}/tasks"...
    # These are lines ~322-409

    # Pattern to match entire endpoint functions with CandidateTask
    candidate_task_endpoint_pattern = r'@app\.(get|put|post|delete)\("/api/candidates/\{candidate_id\}/tasks[^"]*".*?\n(.*?\n)*?    return.*?\n\n'

    content = re.sub(candidate_task_endpoint_pattern,
                     '# PHASE 4 TODO: Reimplement using Task+TaskCandidateLink\n\n',
                     content, flags=re.DOTALL)

    # 3. Replace any remaining CandidateTask references with commented placeholders
    # In select() statements
    content = re.sub(r'select\(CandidateTask\)', '# PHASE 4 TODO: select(Task)', content)
    content = re.sub(r'CandidateTask\.[a-z_]+', '# PHASE 4 TODO', content)
    content = re.sub(r'= CandidateTask\(', '# PHASE 4 TODO: Task(', content)
    content = re.sub(r'List\[CandidateTask\]', '# PHASE 4 TODO: List[Task]', content)
    content = re.sub(r'response_model=CandidateTask', '# PHASE 4 TODO', content)

    # Write back
    with open('src/app.py', 'w') as f:
        f.write(content)

    print("✓ Removed CandidateTask references")
    print("Note: CandidateTask endpoints will be reimplemented in Phase 4")

    # Verify no actual CandidateTask references remain (only in comments)
    if re.search(r'(?<!# )(?<!TODO: )CandidateTask', content):
        print("\n⚠ Warning: Some CandidateTask references may still exist")
    else:
        print("✓ All CandidateTask references removed/commented")

if __name__ == "__main__":
    fix_candidate_task_refs()
