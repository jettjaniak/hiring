"""
Sync engine for communicating with the server
"""
import requests
from datetime import datetime
from typing import Dict, List, Any
from sqlalchemy.orm import Session
import models
from encryption import EncryptionManager
import json


class SyncEngine:
    def __init__(self, server_url: str, encryption_manager: EncryptionManager):
        self.server_url = server_url
        self.encryption = encryption_manager

    def _get_data_fields(self, entity: Any):
        """Get list of data field names (excluding metadata columns)"""
        from sqlalchemy.inspection import inspect
        mapper = inspect(entity.__class__)

        data_fields = []
        for column in mapper.columns:
            key = column.key
            # Skip system/metadata columns
            if key in ['id', 'candidate_id', 'task_identifier', 'action_id',
                      'created_at', 'updated_at', 'last_synced', 'deleted', 'deleted_at']:
                continue
            # Skip version and dirty tracking columns
            if key.endswith('_version') or key.endswith('_dirty'):
                continue
            data_fields.append(key)

        return data_fields

    def _push_fields(self, entity: Any, endpoint: str):
        """Generic method to push encrypted fields for any entity - only dirty fields"""
        fields = []

        # Get all data fields
        data_fields = self._get_data_fields(entity)

        for field_name in data_fields:
            # Check if field is dirty
            dirty_attr = f"{field_name}_dirty"
            if not hasattr(entity, dirty_attr) or not getattr(entity, dirty_attr):
                continue  # Skip non-dirty fields

            value = getattr(entity, field_name)

            if value is not None:
                # Handle different data types
                if isinstance(value, dict):
                    # JSON fields (like action state)
                    encrypted_value = self.encryption.encrypt_json(value)
                elif isinstance(value, bool):
                    # Boolean fields
                    encrypted_value = self.encryption.encrypt_string(str(value))
                elif isinstance(value, datetime):
                    # Datetime fields
                    encrypted_value = self.encryption.encrypt_string(value.isoformat())
                elif isinstance(value, str):
                    encrypted_value = self.encryption.encrypt_string(str(value))
                else:
                    raise ValueError(f"unsupported type in _push_fields: {type(value)}")

                # Get current version
                version_attr = f"{field_name}_version"
                version = getattr(entity, version_attr, 0)

                fields.append({
                    "key": field_name,
                    "encrypted_value": encrypted_value.decode('latin1'),
                    "version": version
                })

        if fields:
            response = requests.put(
                f"{self.server_url}/{endpoint}",
                json={"fields": fields}
            )
            response.raise_for_status()

            # Update local versions and clear dirty flags
            result = response.json()
            for field in result['updated']:
                field_name = field['key']
                version_attr = f"{field_name}_version"
                dirty_attr = f"{field_name}_dirty"

                setattr(entity, version_attr, field['version'])
                setattr(entity, dirty_attr, False)

    def _decrypt_and_set_field(self, entity: Any, field_name: str, encrypted_value: bytes):
        """Generic method to decrypt and set a field value"""
        # Determine field type from model
        from sqlalchemy.inspection import inspect
        mapper = inspect(entity.__class__)

        column = None
        for col in mapper.columns:
            if col.key == field_name:
                column = col
                break

        if column is None:
            print(f"WARNING: Unknown field '{field_name}' - add column to models.py")
            return False

        # Decrypt based on column type
        try:
            if str(column.type) == 'JSON':
                # JSON field
                decrypted_value = self.encryption.decrypt_json(encrypted_value)
            elif str(column.type) == 'BOOLEAN':
                # Boolean field
                decrypted_str = self.encryption.decrypt_string(encrypted_value)
                decrypted_value = decrypted_str.lower() == 'true'
            elif 'DATETIME' in str(column.type):
                # DateTime field
                decrypted_str = self.encryption.decrypt_string(encrypted_value)
                decrypted_value = datetime.fromisoformat(decrypted_str) if decrypted_str else None
            else:
                # String/Text field
                decrypted_value = self.encryption.decrypt_string(encrypted_value)

            setattr(entity, field_name, decrypted_value)
            return True
        except Exception as e:
            print(f"WARNING: Failed to decrypt field {field_name}: {e}")
            return False

    def push_candidate(self, db: Session, candidate: models.Candidate):
        """Push a new candidate to server"""
        # Create candidate metadata on server (no fields)
        response = requests.post(
            f"{self.server_url}/candidates",
            json={"id": candidate.id}
        )
        response.raise_for_status()

        # Push encrypted fields
        self._push_fields(candidate, f"candidates/{candidate.id}/fields")

        candidate.last_synced = datetime.utcnow()
        db.commit()

    def pull_candidates(self, db: Session, since: datetime = None):
        """Pull candidates from server and decrypt

        Args:
            since: If provided, only pull changes since this timestamp.
                   If None, performs full pull of all data.

        Returns:
            tuple: (sync_timestamp, stats_dict)
                stats_dict contains counts of what was synced
        """
        # Build params - omit 'since' entirely for full pull
        params = {}
        if since is not None:
            params["since"] = since.isoformat()

        response = requests.get(
            f"{self.server_url}/sync",
            params=params
        )
        response.raise_for_status()
        data = response.json()


        # Track statistics
        stats = {
            'candidates_new': 0,
            'candidates_updated': 0,
            'candidates_list': [],
            'tasks_new': 0,
            'tasks_updated': 0,
            'tasks_list': [],
            'action_states_new': 0,
            'action_states_updated': 0,
            'fields_updated': 0,
            'fields_by_candidate': {}
        }

        # Process candidates (metadata only, no fields)
        # Track which candidates exist locally (not new)
        existing_candidates = set()
        for candidate_data in data['candidates']:
            is_new = self._upsert_candidate(db, candidate_data)
            if is_new:
                stats['candidates_new'] += 1
            else:
                existing_candidates.add(candidate_data['id'])
            stats['candidates_list'].append(candidate_data['id'])

        # Process tasks (metadata only, no fields)
        # Track which tasks exist locally (not new)
        existing_tasks = set()
        for task_data in data['tasks']:
            is_new = self._upsert_task(db, task_data)
            if is_new:
                stats['tasks_new'] += 1
            else:
                task_key = (task_data['candidate_id'], task_data['task_identifier'])
                existing_tasks.add(task_key)
            stats['tasks_list'].append(f"{task_data['candidate_id']}/{task_data['task_identifier']}")

        # Process action states (metadata only, no fields)
        # Track which action states exist locally (not new)
        existing_action_states = set()
        for state_data in data['action_states']:
            is_new = self._upsert_action_state(db, state_data)
            if is_new:
                stats['action_states_new'] += 1
            else:
                action_key = (state_data['candidate_id'], state_data['action_id'])
                existing_action_states.add(action_key)

        # Flush so entities are visible to field queries
        db.flush()

        # Process candidate fields
        fields_by_candidate = {}
        fields_by_candidate_names = {}  # For stats reporting
        for field_data in data['candidate_fields']:
            cid = field_data.get('candidate_id')
            if cid:
                if cid not in fields_by_candidate:
                    fields_by_candidate[cid] = []
                    fields_by_candidate_names[cid] = []
                fields_by_candidate[cid].append(field_data)
                field_key = field_data.get('field_key')
                if field_key and field_key not in fields_by_candidate_names[cid]:
                    fields_by_candidate_names[cid].append(field_key)

        for candidate_id, fields in fields_by_candidate.items():
            updated = self._update_entity_fields(db, models.Candidate, candidate_id, fields)
            stats['fields_updated'] += updated

            # Only count existing candidates as "updated" if fields actually changed
            if updated > 0 and candidate_id in existing_candidates:
                stats['candidates_updated'] += 1

        stats['fields_by_candidate'] = fields_by_candidate_names

        # Process task fields
        fields_by_task = {}
        for field_data in data['task_fields']:
            key = (field_data.get('candidate_id'), field_data.get('task_identifier'))
            if key not in fields_by_task:
                fields_by_task[key] = []
            fields_by_task[key].append(field_data)

        for (candidate_id, task_id), fields in fields_by_task.items():
            task = db.query(models.CandidateTask).filter_by(
                candidate_id=candidate_id,
                task_identifier=task_id
            ).first()
            if task:
                updated = self._update_entity_fields_with_entity(task, fields)
                stats['fields_updated'] += updated

                # Only count existing tasks as "updated" if fields actually changed
                task_key = (candidate_id, task_id)
                if updated > 0 and task_key in existing_tasks:
                    stats['tasks_updated'] += 1

        # Process action state fields
        fields_by_action = {}
        for field_data in data['action_state_fields']:
            key = (field_data.get('candidate_id'), field_data.get('action_id'))
            if key not in fields_by_action:
                fields_by_action[key] = []
            fields_by_action[key].append(field_data)

        for (candidate_id, action_id), fields in fields_by_action.items():
            action = db.query(models.ActionState).filter_by(
                candidate_id=candidate_id,
                action_id=action_id
            ).first()
            if action:
                updated = self._update_entity_fields_with_entity(action, fields)
                stats['fields_updated'] += updated

                # Only count existing action states as "updated" if fields actually changed
                action_key = (candidate_id, action_id)
                if updated > 0 and action_key in existing_action_states:
                    stats['action_states_updated'] += 1

        db.commit()
        return data.get('sync_timestamp'), stats

    def _upsert_candidate(self, db: Session, candidate_data: dict):
        """Insert or update candidate metadata (no field data)

        Returns:
            bool: True if new candidate was created, False if existing was updated
        """
        candidate = db.query(models.Candidate).filter_by(id=candidate_data['id']).first()

        is_new = candidate is None

        if not candidate:
            candidate = models.Candidate(
                id=candidate_data['id']
            )
            db.add(candidate)

        candidate.last_synced = datetime.utcnow()

        return is_new

    def _update_entity_fields(self, db: Session, model_class: Any, entity_id: str, fields: List[dict]):
        """Generic method to update entity fields (for models with single-column PK)

        Returns:
            int: Number of fields updated
        """
        entity = db.query(model_class).filter_by(id=entity_id).first()
        if not entity:
            print(f"WARNING: {model_class.__name__} {entity_id} not found for field update")
            return 0

        return self._update_entity_fields_with_entity(entity, fields)

    def _update_entity_fields_with_entity(self, entity: Any, fields: List[dict]):
        """Generic method to update entity fields when you already have the entity object

        Returns:
            int: Number of fields updated
        """
        updated_count = 0

        for field_data in fields:
            field_name = field_data['field_name']
            encrypted_value = field_data['encrypted_value'].encode('latin1')
            version = field_data['version']

            # Check if we already have this version
            version_attr = f"{field_name}_version"
            current_version = getattr(entity, version_attr, 0)

            if current_version >= version:
                continue  # Skip if we already have this version or newer

            # Decrypt and set using generic method
            if self._decrypt_and_set_field(entity, field_name, encrypted_value):
                # Update version and CLEAR dirty flag (pulled from server, so not dirty)
                setattr(entity, version_attr, version)
                dirty_attr = f"{field_name}_dirty"
                setattr(entity, dirty_attr, False)
                updated_count += 1

        return updated_count

    def _upsert_task(self, db: Session, task_data: dict):
        """Insert or update task metadata (no field data)

        Returns:
            bool: True if new task was created, False if existing was updated
        """
        task = db.query(models.CandidateTask).filter_by(
            candidate_id=task_data['candidate_id'],
            task_identifier=task_data['task_identifier']
        ).first()

        is_new = task is None

        if not task:
            task = models.CandidateTask(
                candidate_id=task_data['candidate_id'],
                task_identifier=task_data['task_identifier']
            )
            db.add(task)

        task.last_synced = datetime.utcnow()

        return is_new

    def _upsert_action_state(self, db: Session, state_data: dict):
        """Insert or update action state metadata (no field data)

        Returns:
            bool: True if new state was created, False if existing was updated
        """
        action_state = db.query(models.ActionState).filter_by(
            candidate_id=state_data['candidate_id'],
            action_id=state_data['action_id']
        ).first()

        is_new = action_state is None

        if not action_state:
            action_state = models.ActionState(
                candidate_id=state_data['candidate_id'],
                action_id=state_data['action_id']
            )
            db.add(action_state)

        action_state.last_synced = datetime.utcnow()

        return is_new

    def push_task(self, db: Session, task: models.CandidateTask, create: bool = False):
        """Push task to server"""
        if create:
            # Create task metadata on server (no fields)
            response = requests.post(
                f"{self.server_url}/candidate-tasks",
                json={
                    "candidate_id": task.candidate_id,
                    "task_identifier": task.task_identifier
                }
            )
            response.raise_for_status()

        # Push encrypted fields
        self._push_fields(
            task,
            f"candidate-tasks/{task.candidate_id}/{task.task_identifier}/fields"
        )

        task.last_synced = datetime.utcnow()
        db.commit()

    def push_action_state(self, db: Session, action_state: models.ActionState, create: bool = False):
        """Push action state to server"""
        if create:
            # Create action state metadata on server (no fields)
            response = requests.post(
                f"{self.server_url}/action-states",
                json={
                    "candidate_id": action_state.candidate_id,
                    "action_id": action_state.action_id
                }
            )
            response.raise_for_status()

        # Push encrypted fields (including state JSON)
        self._push_fields(
            action_state,
            f"action-states/{action_state.candidate_id}/{action_state.action_id}/fields"
        )

        action_state.last_synced = datetime.utcnow()
        db.commit()

    def push_all_dirty(self, db: Session):
        """Find and push all dirty entities (that have local changes)

        Returns:
            Dict with push statistics
        """
        stats = {
            'candidates_pushed': 0,
            'candidates_failed': 0,
            'tasks_pushed': 0,
            'tasks_failed': 0,
            'failed_items': []
        }

        # Push candidates that haven't been synced or were modified since last sync or have dirty fields
        from sqlalchemy import or_
        candidates = db.query(models.Candidate).filter(
            or_(
                models.Candidate.last_synced.is_(None),
                models.Candidate.updated_at > models.Candidate.last_synced,
                models.Candidate.workflow_id_dirty == True,
                models.Candidate.name_dirty == True,
                models.Candidate.email_dirty == True,
                models.Candidate.phone_dirty == True,
                models.Candidate.resume_url_dirty == True,
                models.Candidate.notes_dirty == True
            )
        ).all()

        for candidate in candidates:
            try:
                if candidate.last_synced is None:
                    # New candidate, create on server
                    self.push_candidate(db, candidate)
                else:
                    # Existing candidate, just push field updates
                    self._push_fields(candidate, f"candidates/{candidate.id}/fields")
                    candidate.last_synced = datetime.utcnow()
                    db.commit()
                stats['candidates_pushed'] += 1
            except Exception as e:
                stats['candidates_failed'] += 1
                stats['failed_items'].append({
                    'type': 'candidate',
                    'id': candidate.id,
                    'error': str(e)
                })

        # Push tasks that haven't been synced or were modified since last sync
        # Only push tasks for candidates that have been synced
        synced_candidates = db.query(models.Candidate.id).filter(
            models.Candidate.last_synced != None
        ).all()
        synced_candidate_ids = {c[0] for c in synced_candidates}

        tasks = db.query(models.CandidateTask).filter(
            or_(
                models.CandidateTask.last_synced.is_(None),
                models.CandidateTask.updated_at > models.CandidateTask.last_synced,
                models.CandidateTask.status_dirty == True
            )
        ).all()

        for task in tasks:
            # Skip tasks for unsynced candidates
            if task.candidate_id not in synced_candidate_ids:
                continue

            try:
                create = task.last_synced is None
                self.push_task(db, task, create=create)
                stats['tasks_pushed'] += 1
            except Exception as e:
                stats['tasks_failed'] += 1
                stats['failed_items'].append({
                    'type': 'task',
                    'id': f"{task.candidate_id}/{task.task_identifier}",
                    'error': str(e)
                })

        return stats

    def pull_all(self, db: Session, since: datetime = None):
        """Pull all changes from server

        Args:
            since: If provided, only pull changes since this timestamp.
                   If None, performs full pull of all data.

        Returns:
            Tuple of (sync_timestamp, stats_dict)
        """
        return self.pull_candidates(db, since=since)

    def full_sync(self, db: Session, since: datetime = None):
        """Full sync: pull first (to get latest versions), then push

        This order prevents conflicts when two clients modify different fields
        of the same entity.

        Args:
            since: If provided, only pull changes since this timestamp.

        Returns:
            Dict with combined statistics
        """
        # Pull first to update local versions
        sync_timestamp, pull_stats = self.pull_all(db, since=since)

        # Then push local changes with up-to-date versions
        push_stats = self.push_all_dirty(db)

        # Combine stats
        combined_stats = {
            'sync_timestamp': sync_timestamp,
            'pull': pull_stats,
            'push': push_stats
        }

        return combined_stats
