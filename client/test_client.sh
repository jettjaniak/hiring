#!/bin/bash
# Test script for the hiring client

set -e

echo "=== Testing Hiring Process Client ==="
echo

# Clean up previous test data
rm -rf ~/.hiring-client-test
export HOME_BACKUP=$HOME
export HOME=$(pwd)/.test-home
mkdir -p $HOME

CLI="./venv/bin/python cli.py"

echo "1. Testing initialization..."
echo -e "test-password-123\ntest-password-123\n" | $CLI init --server http://localhost:8000/api
echo

echo "2. Testing status..."
$CLI status
echo

echo "3. Adding a candidate..."
echo -e "Alice Smith\nalice@example.com\ntech_specialist_v1\n555-1234\n" | $CLI add-candidate
echo

echo "4. Adding another candidate..."
echo -e "Bob Johnson\nbob@example.com\ntech_specialist_v1\n\n" | $CLI add-candidate
echo

echo "5. Listing candidates..."
$CLI list-candidates
echo

echo "6. Syncing..."
$CLI sync
echo

echo "7. Listing candidates again..."
$CLI list-candidates
echo

echo "=== All tests passed! ==="

# Cleanup
export HOME=$HOME_BACKUP
rm -rf $(pwd)/.test-home
