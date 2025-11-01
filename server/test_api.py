#!/usr/bin/env python3
"""
Simple test script to demonstrate API usage
Run the server first with: python run.py
Then run this script in another terminal: python test_api.py
"""
import requests
import json
from datetime import datetime
import base64

BASE_URL = "http://localhost:8000/api"


def print_response(response):
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
    print()


def main():
    print("=== Testing Hiring Process API ===\n")

    # 1. Create a candidate
    print("1. Creating a candidate...")
    candidate_data = {
        "id": "candidate-001",
        "workflow_id": "tech_specialist_v1"
    }
    response = requests.post(f"{BASE_URL}/candidates", json=candidate_data)
    print_response(response)

    # 2. Add encrypted fields to the candidate
    print("2. Adding encrypted candidate fields...")
    # Simulating encrypted data (in real usage, this would be encrypted client-side)
    encrypted_name = base64.b64encode(b"John Doe").decode()
    encrypted_email = base64.b64encode(b"john@example.com").decode()

    fields_data = {
        "fields": [
            {
                "key": "name",
                "encrypted_value": encrypted_name,
                "version": 0  # First update, expect version 0 (will become 1)
            },
            {
                "key": "email",
                "encrypted_value": encrypted_email,
                "version": 0
            }
        ]
    }
    response = requests.put(f"{BASE_URL}/candidates/candidate-001/fields", json=fields_data)
    print_response(response)

    # 3. Get candidate with fields
    print("3. Getting candidate with all fields...")
    response = requests.get(f"{BASE_URL}/candidates/candidate-001")
    print_response(response)

    # 4. Create a candidate task
    print("4. Creating a candidate task...")
    task_data = {
        "candidate_id": "candidate-001",
        "task_identifier": "initial_screening_v1",
        "completed": False
    }
    response = requests.post(f"{BASE_URL}/candidate-tasks", json=task_data)
    print_response(response)

    # 5. Update the task
    print("5. Updating the task to completed...")
    task_update = {
        "completed": True,
        "version": 1,
        "completed_at": datetime.utcnow().isoformat()
    }
    response = requests.put(
        f"{BASE_URL}/candidate-tasks/candidate-001/initial_screening_v1",
        json=task_update
    )
    print_response(response)

    # 6. Test version conflict
    print("6. Testing version conflict (should fail)...")
    task_update_wrong_version = {
        "completed": False,
        "version": 1  # Wrong version, should be 2 now
    }
    response = requests.put(
        f"{BASE_URL}/candidate-tasks/candidate-001/initial_screening_v1",
        json=task_update_wrong_version
    )
    print_response(response)

    # 7. Create action state
    print("7. Creating action state...")
    encrypted_state = base64.b64encode(json.dumps({
        "step": 1,
        "notes": "Called candidate"
    }).encode()).decode()

    action_state_data = {
        "candidate_id": "candidate-001",
        "action_id": "phone_screen_v1",
        "encrypted_state": encrypted_state
    }
    response = requests.post(f"{BASE_URL}/action-states", json=action_state_data)
    print_response(response)

    # 8. Test sync endpoint
    print("8. Testing sync endpoint...")
    # Get changes from 1 hour ago
    sync_time = datetime.utcnow().replace(microsecond=0).isoformat()
    response = requests.get(f"{BASE_URL}/sync?since=2024-01-01T00:00:00")
    print_response(response)

    # 9. List all candidates
    print("9. Listing all candidates...")
    response = requests.get(f"{BASE_URL}/candidates")
    print_response(response)


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the API server.")
        print("Make sure the server is running with: python run.py")
    except Exception as e:
        print(f"ERROR: {e}")
