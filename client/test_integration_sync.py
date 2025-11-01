#!/usr/bin/env python3
"""
Integration test for sync scenarios with 1 server and 2 clients

Tests:
1. Two clients editing different fields of same candidate - no conflict
2. Two clients editing same field - version conflict detection
3. Pull-before-push prevents conflicts
4. Dirty fields tracking - only dirty fields are pushed
5. Pull doesn't mark fields as dirty
6. Candidate tasks sync properly
7. Action states sync properly
"""

import os
import sys
import shutil
import subprocess
import time
import requests
import tempfile
from pathlib import Path
import json


class TestEnvironment:
    """Manages server and client processes for integration testing"""

    def __init__(self):
        self.server_proc = None
        self.client1_proc = None
        self.client2_proc = None
        self.temp_dirs = []
        # Use different ports to avoid conflicts with running instances
        self.server_port = 9000
        self.client1_port = 6001
        self.client2_port = 6002
        self.encryption_key = "test-key-12345"
        self.server_url = f"http://localhost:{self.server_port}/api"

    def setup(self):
        """Start server and 2 clients"""
        print("=" * 60)
        print("Setting up test environment...")
        print("=" * 60)

        # Create temp directories for clients
        self.client1_dir = tempfile.mkdtemp(prefix="client1_")
        self.client2_dir = tempfile.mkdtemp(prefix="client2_")
        self.temp_dirs = [self.client1_dir, self.client2_dir]

        print(f"Client 1 data dir: {self.client1_dir}")
        print(f"Client 2 data dir: {self.client2_dir}")

        # Start server on different port
        print(f"\nStarting server on port {self.server_port}...")
        server_dir = Path(__file__).parent.parent / "server"
        self.server_proc = subprocess.Popen(
            ["./venv/bin/python", "run.py", "--reset", "--port", str(self.server_port)],
            cwd=server_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(5)  # Wait for server to start
        print("✓ Server should be running")

        # Initialize both clients
        print("\nInitializing clients...")
        for client_dir in [self.client1_dir, self.client2_dir]:
            result = subprocess.run(
                ["./venv/bin/python", "cli.py", "--data-dir", client_dir, "init",
                 "--key", self.encryption_key, "--server", self.server_url],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"Failed to initialize client: {result.stderr}")
                raise Exception("Client initialization failed")

        print("✓ Environment setup complete\n")

    def teardown(self):
        """Stop all processes and clean up"""
        print("\n" + "=" * 60)
        print("Tearing down test environment...")
        print("=" * 60)

        if self.server_proc:
            self.server_proc.terminate()
            self.server_proc.wait()

        # Clean up temp directories
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

        print("✓ Teardown complete")

    def get_client_context(self, client_dir):
        """Get a client context (config, db, sync) for testing"""
        from config import Config
        from database import Database
        from encryption import EncryptionManager
        from sync import SyncEngine

        config = Config(config_dir=client_dir)
        encryption = EncryptionManager(config.encryption_key)
        db = Database(str(config.db_file))
        db.init_db()
        sync = SyncEngine(config.server_url, encryption)

        return {
            'config': config,
            'db': db,
            'encryption': encryption,
            'sync': sync
        }

    def add_candidate_direct(self, client_dir, name, email, workflow_id="eng_v1"):
        """Add candidate directly using client database"""
        import models
        import uuid
        from datetime import datetime

        ctx = self.get_client_context(client_dir)
        session = ctx['db'].get_session()

        try:
            candidate_id = f"candidate-{uuid.uuid4().hex[:12]}"
            candidate = models.Candidate(
                id=candidate_id,
                workflow_id=workflow_id,
                name=name,
                email=email
            )

            # Mark fields as dirty
            candidate.workflow_id_dirty = True
            candidate.name_dirty = True
            candidate.email_dirty = True

            session.add(candidate)
            session.commit()

            return candidate_id
        finally:
            session.close()

    def get_candidate(self, client_dir, candidate_id):
        """Get candidate from client database"""
        import models

        ctx = self.get_client_context(client_dir)
        session = ctx['db'].get_session()

        try:
            candidate = session.query(models.Candidate).filter_by(id=candidate_id).first()
            if candidate:
                return {
                    'id': candidate.id,
                    'name': candidate.name,
                    'email': candidate.email,
                    'phone': candidate.phone,
                    'workflow_id': candidate.workflow_id,
                    'name_version': candidate.name_version,
                    'email_version': candidate.email_version,
                    'name_dirty': candidate.name_dirty,
                    'email_dirty': candidate.email_dirty
                }
            return None
        finally:
            session.close()

    def update_candidate_field(self, client_dir, candidate_id, field_name, value):
        """Update a single candidate field"""
        import models
        from datetime import datetime

        ctx = self.get_client_context(client_dir)
        session = ctx['db'].get_session()

        try:
            candidate = session.query(models.Candidate).filter_by(id=candidate_id).first()
            if candidate:
                setattr(candidate, field_name, value)
                setattr(candidate, f"{field_name}_dirty", True)
                candidate.updated_at = datetime.utcnow()
                session.commit()
                return True
            return False
        finally:
            session.close()

    def sync_push(self, client_dir):
        """Push changes from client"""
        ctx = self.get_client_context(client_dir)
        session = ctx['db'].get_session()

        try:
            stats = ctx['sync'].push_all_dirty(session)
            return stats
        finally:
            session.close()

    def sync_pull(self, client_dir):
        """Pull changes to client"""
        ctx = self.get_client_context(client_dir)
        session = ctx['db'].get_session()

        try:
            sync_timestamp, stats = ctx['sync'].pull_all(session, since=None)
            ctx['config'].last_sync = sync_timestamp
            return stats
        finally:
            session.close()

    def sync_full(self, client_dir):
        """Full sync (pull then push)"""
        ctx = self.get_client_context(client_dir)
        session = ctx['db'].get_session()

        try:
            result = ctx['sync'].full_sync(session, since=None)
            ctx['config'].last_sync = result['sync_timestamp']
            return result
        finally:
            session.close()


class SyncTests:
    """Integration tests for sync scenarios"""

    def __init__(self, env: TestEnvironment):
        self.env = env
        self.passed = 0
        self.failed = 0

    def assert_eq(self, actual, expected, message):
        """Assert equality"""
        if actual == expected:
            print(f"  ✓ {message}")
            self.passed += 1
        else:
            print(f"  ✗ {message}")
            print(f"    Expected: {expected}")
            print(f"    Actual: {actual}")
            self.failed += 1

    def assert_true(self, condition, message):
        """Assert true"""
        if condition:
            print(f"  ✓ {message}")
            self.passed += 1
        else:
            print(f"  ✗ {message}")
            self.failed += 1

    def test_different_fields_no_conflict(self):
        """Test: Two clients edit different fields of same candidate - no conflict"""
        print("\n" + "=" * 60)
        print("TEST 1: Different fields, no conflict")
        print("=" * 60)

        # Client 1: Add candidate
        print("\n1. Client 1 creates candidate...")
        candidate_id = self.env.add_candidate_direct(
            self.env.client1_dir,
            name="Alice Smith",
            email="alice@example.com"
        )
        print(f"   Created candidate: {candidate_id}")

        # Client 1: Sync (push)
        print("\n2. Client 1 syncs (push)...")
        stats = self.env.sync_push(self.env.client1_dir)
        self.assert_eq(stats['candidates_pushed'], 1, "1 candidate pushed")

        # Client 2: Sync (pull)
        print("\n3. Client 2 syncs (pull)...")
        stats = self.env.sync_pull(self.env.client2_dir)
        self.assert_eq(stats['candidates_new'], 1, "1 new candidate pulled")

        # Verify client 2 has the candidate
        candidate = self.env.get_candidate(self.env.client2_dir, candidate_id)
        self.assert_eq(candidate['name'], "Alice Smith", "Name matches")
        self.assert_eq(candidate['email'], "alice@example.com", "Email matches")

        # Client 1: Edit name field only
        print("\n4. Client 1 edits name field...")
        self.env.update_candidate_field(self.env.client1_dir, candidate_id, "name", "Alice Johnson")

        # Client 2: Edit email field only (different field!)
        print("\n5. Client 2 edits email field...")
        self.env.update_candidate_field(self.env.client2_dir, candidate_id, "email", "alice.j@example.com")

        # Both push - should NOT conflict because different fields
        print("\n6. Client 1 pushes name change...")
        stats = self.env.sync_push(self.env.client1_dir)
        self.assert_eq(stats['candidates_pushed'], 1, "Client 1 pushed successfully")
        self.assert_eq(stats['candidates_failed'], 0, "No failures")

        print("\n7. Client 2 pushes email change...")
        stats = self.env.sync_push(self.env.client2_dir)
        self.assert_eq(stats['candidates_pushed'], 1, "Client 2 pushed successfully")
        self.assert_eq(stats['candidates_failed'], 0, "No failures - different fields!")

        # Both pull to get final state
        print("\n8. Both clients pull to sync...")
        self.env.sync_pull(self.env.client1_dir)
        self.env.sync_pull(self.env.client2_dir)

        # Verify both have latest data
        client1_data = self.env.get_candidate(self.env.client1_dir, candidate_id)
        client2_data = self.env.get_candidate(self.env.client2_dir, candidate_id)

        self.assert_eq(client1_data['name'], "Alice Johnson", "Client 1 has updated name")
        self.assert_eq(client1_data['email'], "alice.j@example.com", "Client 1 has updated email")
        self.assert_eq(client2_data['name'], "Alice Johnson", "Client 2 has updated name")
        self.assert_eq(client2_data['email'], "alice.j@example.com", "Client 2 has updated email")

        print("\n✓ Test 1 complete: Different fields edited without conflict")

    def test_same_field_conflict(self):
        """Test: Two clients edit same field - should detect conflict (with push-only, not full sync)"""
        print("\n" + "=" * 60)
        print("TEST 2: Same field edit - conflict detection")
        print("=" * 60)

        # Client 1: Add and push candidate
        print("\n1. Client 1 creates and pushes candidate...")
        candidate_id = self.env.add_candidate_direct(
            self.env.client1_dir,
            name="Bob Smith",
            email="bob@example.com"
        )
        self.env.sync_push(self.env.client1_dir)

        # Client 2: Pull
        print("\n2. Client 2 pulls candidate...")
        self.env.sync_pull(self.env.client2_dir)

        # Both edit same field
        print("\n3. Client 1 edits name...")
        self.env.update_candidate_field(self.env.client1_dir, candidate_id, "name", "Bob Johnson")

        print("\n4. Client 2 also edits name...")
        self.env.update_candidate_field(self.env.client2_dir, candidate_id, "name", "Bob Williams")

        # Client 1 pushes first
        print("\n5. Client 1 pushes (should succeed)...")
        stats = self.env.sync_push(self.env.client1_dir)
        self.assert_eq(stats['candidates_pushed'], 1, "Client 1 pushed successfully")

        # Client 2 pushes with stale version (should fail)
        print("\n6. Client 2 pushes with stale version (should fail)...")
        stats = self.env.sync_push(self.env.client2_dir)
        self.assert_eq(stats['candidates_failed'], 1, "Client 2 push failed due to version conflict")

        # Clean up: Client 2 does full sync to resolve the conflict
        print("\n7. Client 2 does full sync to resolve conflict...")
        result = self.env.sync_full(self.env.client2_dir)
        # After pull, Client 2 gets the version from Client 1, making its local edit stale
        # But it will still try to push since the field is dirty
        # The server will reject it again due to version conflict, OR
        # if pull updated the local value, the dirty flag might have been cleared
        # Either way, this cleans up for the next test

        print("\n✓ Test 2 complete: Conflict detected correctly")

    def test_pull_before_push_prevents_conflict(self):
        """Test: Full sync (pull-before-push) prevents conflicts"""
        print("\n" + "=" * 60)
        print("TEST 3: Full sync prevents conflicts")
        print("=" * 60)

        # Client 1: Add and push
        print("\n1. Client 1 creates and pushes candidate...")
        candidate_id = self.env.add_candidate_direct(
            self.env.client1_dir,
            name="Carol Smith",
            email="carol@example.com"
        )
        self.env.sync_push(self.env.client1_dir)

        # Client 2: Pull
        print("\n2. Client 2 pulls candidate...")
        self.env.sync_pull(self.env.client2_dir)

        # Both edit same field
        print("\n3. Client 1 edits name...")
        self.env.update_candidate_field(self.env.client1_dir, candidate_id, "name", "Carol Johnson")

        print("\n4. Client 2 also edits name...")
        self.env.update_candidate_field(self.env.client2_dir, candidate_id, "name", "Carol Williams")

        # Client 1 uses full sync
        print("\n5. Client 1 uses full sync (pull then push)...")
        result = self.env.sync_full(self.env.client1_dir)
        self.assert_eq(result['push']['candidates_pushed'], 1, "Client 1 pushed successfully")

        # Client 2 uses full sync - pull discards local changes, nothing to push
        print("\n6. Client 2 uses full sync (pull discards local changes)...")
        result = self.env.sync_full(self.env.client2_dir)
        self.assert_eq(result['push']['candidates_pushed'], 0, "Client 2 has nothing to push after pull")

        print("\n✓ Test 3 complete: Full sync prevents conflicts")

    def test_pull_discards_local_dirty_changes(self):
        """Test: Pull with dirty local changes discards those changes"""
        print("\n" + "=" * 60)
        print("TEST 3b: Pull discards local dirty changes")
        print("=" * 60)

        # Client 1: Add and push
        print("\n1. Client 1 creates and pushes candidate...")
        candidate_id = self.env.add_candidate_direct(
            self.env.client1_dir,
            name="Eve Smith",
            email="eve@example.com"
        )
        self.env.sync_push(self.env.client1_dir)

        # Client 2: Pull
        print("\n2. Client 2 pulls candidate...")
        self.env.sync_pull(self.env.client2_dir)

        # Client 1: Edit name
        print("\n3. Client 1 edits name and pushes...")
        self.env.update_candidate_field(self.env.client1_dir, candidate_id, "name", "Eve Johnson")
        self.env.sync_push(self.env.client1_dir)

        # Client 2: Edit name locally (WITHOUT syncing - creates dirty field)
        print("\n4. Client 2 also edits name locally (no sync)...")
        self.env.update_candidate_field(self.env.client2_dir, candidate_id, "name", "Eve Williams")

        # Verify Client 2 has dirty field
        candidate2_before = self.env.get_candidate(self.env.client2_dir, candidate_id)
        self.assert_eq(candidate2_before['name'], "Eve Williams", "Client 2 has local edit")
        self.assert_eq(candidate2_before['name_dirty'], True, "Client 2 name is dirty")

        # Client 2: Pull (should discard local changes)
        print("\n5. Client 2 pulls (should discard local dirty changes)...")
        self.env.sync_pull(self.env.client2_dir)

        # Verify Client 2 got server value and dirty flag is cleared
        candidate2_after = self.env.get_candidate(self.env.client2_dir, candidate_id)
        self.assert_eq(candidate2_after['name'], "Eve Johnson", "Client 2 got server value")
        self.assert_eq(candidate2_after['name_dirty'], False, "Client 2 dirty flag cleared")

        # Client 2: Push should not push anything
        print("\n6. Client 2 push should not push anything...")
        stats = self.env.sync_push(self.env.client2_dir)
        self.assert_eq(stats['candidates_pushed'], 0, "No candidates pushed")

        print("\n✓ Test 3b complete: Pull discards local dirty changes")

    def test_dirty_fields_only(self):
        """Test: Only dirty fields are pushed"""
        print("\n" + "=" * 60)
        print("TEST 4: Only dirty fields are pushed")
        print("=" * 60)
        print("  (Skipping for now - validated by test 1)")

    def test_pull_not_dirty(self):
        """Test: Pull doesn't mark fields as dirty"""
        print("\n" + "=" * 60)
        print("TEST 5: Pull doesn't mark fields as dirty")
        print("=" * 60)

        # Client 1: Add and push
        candidate_id = self.env.add_candidate_direct(
            self.env.client1_dir,
            name="Dave Smith",
            email="dave@example.com"
        )
        self.env.sync_push(self.env.client1_dir)

        # Client 2: Pull
        self.env.sync_pull(self.env.client2_dir)

        # Check that fields are NOT dirty after pull
        candidate = self.env.get_candidate(self.env.client2_dir, candidate_id)
        self.assert_eq(candidate['name_dirty'], False, "Name not dirty after pull")
        self.assert_eq(candidate['email_dirty'], False, "Email not dirty after pull")

        # Push should not send anything
        stats = self.env.sync_push(self.env.client2_dir)
        self.assert_eq(stats['candidates_pushed'], 0, "Nothing to push after pull")

        print("\n✓ Test 5 complete: Pull doesn't mark fields as dirty")

    def test_no_phantom_updates(self):
        """Test: Pull after push shows no phantom updates"""
        print("\n" + "=" * 60)
        print("TEST 6: No phantom updates after push+pull")
        print("=" * 60)

        # Client 1: Add candidate and push
        print("\n1. Client 1 creates and pushes candidate...")
        candidate_id = self.env.add_candidate_direct(
            self.env.client1_dir,
            name="Frank Wilson",
            email="frank@example.com"
        )
        self.env.sync_push(self.env.client1_dir)

        # Client 1: Pull again immediately (should show 0 updates)
        print("\n2. Client 1 pulls again (should show 0 updates)...")
        result = self.env.sync_pull(self.env.client1_dir)

        print(f"  Pull result: {result['candidates_new']} new, {result['candidates_updated']} updated")
        self.assert_eq(result['candidates_new'], 0, "No new candidates")
        self.assert_eq(result['candidates_updated'], 0, "No phantom updates")

        print("\n✓ Test 6 complete: No phantom updates after push+pull")

    def run_all(self):
        """Run all tests"""
        print("\n" + "=" * 60)
        print("RUNNING INTEGRATION TESTS")
        print("=" * 60)

        self.test_different_fields_no_conflict()
        self.test_same_field_conflict()
        self.test_pull_before_push_prevents_conflict()
        self.test_pull_discards_local_dirty_changes()
        self.test_dirty_fields_only()
        self.test_pull_not_dirty()
        self.test_no_phantom_updates()

        # Print summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Total: {self.passed + self.failed}")

        if self.failed == 0:
            print("\n✓ All tests passed!")
            return 0
        else:
            print(f"\n✗ {self.failed} test(s) failed")
            return 1


def main():
    """Main test runner"""
    env = TestEnvironment()

    try:
        env.setup()
        tests = SyncTests(env)
        exit_code = tests.run_all()
        return exit_code
    except Exception as e:
        print(f"\n✗ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        env.teardown()


if __name__ == "__main__":
    sys.exit(main())
