#!/bin/bash
# Script to update model references in app.py

# Backup original
cp src/app.py src/app.py.bak

# Step 1: Replace SpawnedTask with Task (using sed with word boundaries)
sed -i.tmp 's/\bSpawnedTask\b/Task/g' src/app.py

# Step 2: Replace old Task with TaskTemplate (but not UpdateTaskRequest, CreateTaskRequest, etc.)
# We need to be careful to only replace the model name, not request/response types
sed -i.tmp 's/\bTask\b,/TaskTemplate,/g' src/app.py
sed -i.tmp 's/\bTask\b)/TaskTemplate)/g' src/app.py
sed -i.tmp 's/\bTask\b )/TaskTemplate )/g' src/app.py
sed -i.tmp 's/select(Task)/select(TaskTemplate)/g' src/app.py
sed -i.tmp 's/\.get(Task,/.get(TaskTemplate,/g' src/app.py
sed -i.tmp 's/= Task(/= TaskTemplate(/g' src/app.py
sed -i.tmp 's/: Task /: TaskTemplate /g' src/app.py
sed -i.tmp 's/\[Task\]/[TaskTemplate]/g' src/app.py

# Step 3: Remove CandidateTask from import and mark other references
sed -i.tmp 's/CandidateTask, //g' src/app.py
sed -i.tmp 's/, CandidateTask//g' src/app.py
sed -i.tmp 's/\bCandidateTask\b/# REMOVED_CandidateTask/g' src/app.py

# Clean up tmp files
rm src/app.py.tmp

echo "✓ Updated src/app.py (backup saved as src/app.py.bak)"
