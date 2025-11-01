#!/usr/bin/env python3
"""
Demo test for the client - simulates user interactions
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Set up test environment
TEST_HOME = Path.cwd() / ".test-home"
if TEST_HOME.exists():
    shutil.rmtree(TEST_HOME)
TEST_HOME.mkdir()

os.environ['HOME'] = str(TEST_HOME)

CLI = ["./venv/bin/python", "cli.py"]

def run_cli(args, input_data=None):
    """Run CLI command"""
    result = subprocess.run(
        CLI + args,
        input=input_data,
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        print(f"Command failed with code {result.returncode}")
        sys.exit(1)
    return result

print("=== Hiring Process Client Demo ===\n")

# 1. Initialize
print("1. Initializing client...")
run_cli(["init", "--key", "test-key-123"])

# 2. Check status
print("\n2. Checking status...")
run_cli(["status"])

# 3. Add a candidate
print("\n3. Adding candidate Alice Smith...")
run_cli(
    ["add-candidate", "--name", "Alice Smith", "--email", "alice@example.com",
     "--workflow", "tech_specialist_v1", "--phone", "555-1234"]
)

# 4. Add another candidate
print("\n4. Adding candidate Bob Johnson...")
run_cli(
    ["add-candidate", "--name", "Bob Johnson", "--email", "bob@example.com",
     "--workflow", "senior_engineer_v2"]
)

# 5. List candidates
print("\n5. Listing all candidates...")
run_cli(["list-candidates"])

# 6. Show candidate details
print("\n6. Showing Alice's details...")
# Get the first candidate ID from list
result = subprocess.run(
    CLI + ["list-candidates"],
    capture_output=True,
    text=True
)
lines = result.stdout.strip().split('\n')
if len(lines) > 2:  # Skip header lines
    candidate_id = lines[2].split()[0]
    run_cli(["show-candidate", candidate_id])

# 7. Update candidate
print("\n7. Updating Alice's notes...")
run_cli(["update-candidate", candidate_id, "--notes", "Great candidate!"])

# 8. Sync
print("\n8. Syncing with server...")
run_cli(["sync"])

# 9. Final status
print("\n9. Final status check...")
run_cli(["status"])

print("\n=== Demo Complete! ===")
print(f"\nTest data stored in: {TEST_HOME / '.hiring-client'}")
print("Server data can be inspected via API at http://localhost:8000/docs")

# Don't clean up so we can inspect
print(f"\nTo clean up test data, run: rm -rf {TEST_HOME}")
