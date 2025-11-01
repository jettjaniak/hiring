"""
Schema migration system for local and remote data
"""
from sqlalchemy.orm import Session
from typing import Callable, Dict
import models
from config import Config
from encryption import EncryptionManager
from sync import SyncEngine
from datetime import datetime


class MigrationManager:
    """Handle schema migrations"""

    def __init__(self, config: Config, db_session: Session, sync_engine: SyncEngine):
        self.config = config
        self.db = db_session
        self.sync = sync_engine
        self.migrations: Dict[int, Callable] = {
            # Add migrations here
            # 2: self._migrate_v1_to_v2,
            # 3: self._migrate_v2_to_v3,
        }

    def get_current_version(self) -> int:
        """Get current schema version"""
        return self.config.schema_version

    def get_latest_version(self) -> int:
        """Get latest schema version"""
        return max(self.migrations.keys()) if self.migrations else 1

    def needs_migration(self) -> bool:
        """Check if migration is needed"""
        return self.get_current_version() < self.get_latest_version()

    def migrate(self):
        """Run all pending migrations"""
        current = self.get_current_version()
        latest = self.get_latest_version()

        if current >= latest:
            print("Already at latest schema version")
            return

        print(f"Migrating from version {current} to {latest}")

        for version in range(current + 1, latest + 1):
            if version in self.migrations:
                print(f"Running migration to version {version}...")
                self.migrations[version]()
                self.config.schema_version = version
                print(f"✓ Migrated to version {version}")

        print("Migration complete!")

    def _migrate_v1_to_v2(self):
        """Example migration from v1 to v2"""
        # This is a placeholder for when you add new fields
        # For example, if you add a new 'linkedin_url' field:

        # 1. Add the column if it doesn't exist (SQLAlchemy might handle this)
        # 2. Set default values for existing records
        # 3. Push updates to server if needed

        candidates = self.db.query(models.Candidate).all()
        for candidate in candidates:
            # Example: Initialize new field
            if not hasattr(candidate, 'linkedin_url'):
                candidate.linkedin_url = None

        self.db.commit()


class KeyRotationManager:
    """Handle encryption key rotation"""

    def __init__(self, config: Config, db_session: Session, sync_engine: SyncEngine):
        self.config = config
        self.db = db_session
        self.sync = sync_engine

    def rotate_key(self, old_key: str, new_key: str):
        """
        Rotate encryption key:
        1. Pull all data from server with old key
        2. Decrypt with old key
        3. Re-encrypt with new key
        4. Push all data back to server
        """
        print("Starting key rotation...")

        # Verify old key
        old_encryption = EncryptionManager(old_key)
        new_encryption = EncryptionManager(new_key)

        # Create a new sync engine with old key to pull data
        old_sync = SyncEngine(self.config.server_url, old_encryption)

        print("Pulling all data with old key...")
        # Pull everything
        old_sync.pull_candidates(self.db, since=datetime(2000, 1, 1))

        print("Re-encrypting and pushing with new key...")

        # Create new sync engine with new key
        new_sync = SyncEngine(self.config.server_url, new_encryption)

        # Push all candidates with new encryption (including deleted ones - they're still encrypted)
        candidates = self.db.query(models.Candidate).all()
        for candidate in candidates:
            print(f"  Re-encrypting candidate {candidate.id}...")

            # Reset versions to force update
            candidate.field_versions = {k: 0 for k in candidate.field_versions.keys()}

            # Push with new encryption
            new_sync._push_fields(candidate, f"candidates/{candidate.id}/fields")

        # Push all action states with new encryption (including deleted ones)
        action_states = self.db.query(models.ActionState).all()
        for action_state in action_states:
            print(f"  Re-encrypting action state {action_state.action_id}...")

            # Reset versions to force update
            action_state.field_versions = {k: 0 for k in action_state.field_versions.keys()}

            # Push with new encryption
            new_sync.push_action_state(self.db, action_state, create=False)

        # Update config with new key
        self.config.encryption_key = new_key

        print("✓ Key rotation complete!")
        print("NOTE: Make sure all team members get the new key and rotate on their clients too.")
