#!/usr/bin/env python3
"""Test script for the get_template_tasks endpoint"""

import requests
import sys

BASE_URL = "http://localhost:8000"

def test_get_template_tasks():
    """Test the /api/templates/{template_id}/tasks endpoint"""
    print("Testing GET /api/templates/{template_id}/tasks endpoint...")

    # First, get all templates to find a valid template_id
    print("\n1. Getting all templates...")
    response = requests.get(f"{BASE_URL}/api/templates")

    if response.status_code != 200:
        print(f"❌ Failed to get templates: {response.status_code}")
        return False

    templates = response.json()
    if not templates:
        print("⚠️  No templates found in database. Test inconclusive.")
        return True  # Not a failure, just no data

    template_id = templates[0].get("template_id")
    print(f"   Found template: {template_id}")

    # Now test the get_template_tasks endpoint
    print(f"\n2. Getting tasks for template {template_id}...")
    response = requests.get(f"{BASE_URL}/api/templates/{template_id}/tasks")

    if response.status_code != 200:
        print(f"❌ Failed to get template tasks: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

    tasks = response.json()
    print(f"✅ Successfully retrieved {len(tasks)} task(s) for template")

    if tasks:
        print(f"   First task: {tasks[0].get('task_id', 'N/A')} - {tasks[0].get('name', 'N/A')}")

    return True

if __name__ == "__main__":
    try:
        success = test_get_template_tasks()
        sys.exit(0 if success else 1)
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server at http://localhost:8000")
        print("   Make sure the server is running")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
