#!/usr/bin/env python3
"""
Remove or comment out CandidateTask references from src/app.py
These will be replaced with Task+TaskCandidateLink logic in Phase 4
"""

def remove_candidate_task_refs():
    with open('src/app.py', 'r') as f:
        lines = f.readlines()

    # Track if we're inside a CandidateTask-related endpoint or block
    in_candidate_task_block = False
    skip_lines = set()

    for i, line in enumerate(lines):
        # Check for CandidateTask API endpoints (these will be rewritten in Phase 4)
        if '@app.get("/api/candidates/{candidate_id}/tasks"' in line:
            # Find the end of this endpoint function
            # For now, mark it to be commented
            in_candidate_task_block = True
            skip_lines.add(i)
        elif '@app.get("/api/candidates/{candidate_id}/tasks/{task_identifier}"' in line:
            in_candidate_task_block = True
            skip_lines.add(i)
        elif '@app.put("/api/candidates/{candidate_id}/tasks/{task_identifier}"' in line:
            in_candidate_task_block = True
            skip_lines.add(i)
        elif 'CandidateTask' in line:
            skip_lines.add(i)

    # For now, let's just remove all lines with CandidateTask
    # (They'll be rewritten in Phase 4)
    new_lines = []
    for i, line in enumerate(lines):
        if 'CandidateTask' not in line:
            new_lines.append(line)
        else:
            # Comment out the line
            new_lines.append('# PHASE 4 TODO: ' + line)

    with open('src/app.py', 'w') as f:
        f.writelines(new_lines)

    print("✓ Commented out all CandidateTask references")
    print("Note: These will be rewritten in Phase 4 to use Task+TaskCandidateLink")

if __name__ == "__main__":
    remove_candidate_task_refs()
