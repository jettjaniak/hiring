#!/usr/bin/env python3
"""Remove duplicate functions from app.py"""

with open('src/app.py', 'r') as f:
    lines = f.readlines()

# Remove lines for each duplicate function
# 1. ensure_workflow_tasks (lines 75-79) - keep it since routes/api/candidates.py uses it
# 2. get_template_tasks (lines 585-607)
# 3. infer_template_variables (lines 1009-1055)

# Find exact line ranges to remove
remove_ranges = []

# Find ensure_workflow_tasks
for i, line in enumerate(lines):
    if i == 74 and 'def ensure_workflow_tasks(' in line:  # Line 75 in 1-indexed
        # Find end of function (next def or end of blank lines)
        end = i + 1
        while end < len(lines) and (lines[end].strip() == '' or lines[end].startswith('   ')):
            end += 1
        remove_ranges.append((i, end))
        print(f"Found ensure_workflow_tasks at lines {i+1}-{end}")
        break

# Find get_template_tasks
for i, line in enumerate(lines):
    if 'def get_template_tasks(' in line and '@app.get("/api/task-templates/{task_id}/templates"' in lines[i-1]:
        # This is an endpoint, not a helper function - skip it
        continue
    elif 'def get_template_tasks(session: Session, task_id: int)' in line:
        # This is the helper function to remove
        end = i + 1
        while end < len(lines) and (lines[end].strip() == '' or lines[end].startswith('   ') or lines[end].startswith('        ')):
            if end+1 < len(lines) and lines[end+1].strip() and not lines[end+1][0].isspace():
                break
            end += 1
        remove_ranges.append((i, end+1))
        print(f"Found get_template_tasks helper at lines {i+1}-{end+1}")
        break

# Find infer_template_variables
for i, line in enumerate(lines):
    if 'def infer_template_variables(content: str, subject: str = ""' in line:
        end = i + 1
        while end < len(lines):
            if lines[end].strip() and not lines[end][0].isspace() and 'def ' not in lines[end]:
                break
            if end+1 < len(lines) and lines[end].strip() == '' and lines[end+1].strip() and not lines[end+1][0].isspace():
                end += 1
                break
            end += 1
        remove_ranges.append((i, end))
        print(f"Found infer_template_variables at lines {i+1}-{end}")
        break

# Sort ranges in reverse order so we can delete from bottom to top
remove_ranges.sort(reverse=True)

# Remove the ranges
new_lines = lines[:]
for start, end in remove_ranges:
    print(f"Removing lines {start+1} to {end}")
    del new_lines[start:end]

# Write back
with open('src/app.py', 'w') as f:
    f.writelines(new_lines)

print(f"\nRemoved {len(remove_ranges)} duplicate functions")
print(f"Original lines: {len(lines)}")
print(f"New lines: {len(new_lines)}")
print(f"Lines removed: {len(lines) - len(new_lines)}")
