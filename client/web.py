#!/usr/bin/env python3
"""
Simple web interface for hiring process client
"""
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import uuid
import argparse
from datetime import datetime
from config import Config
from database import Database
from encryption import EncryptionManager
from workflow_loader import WorkflowLoader
from sync import SyncEngine
import models

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Hiring Process Web Client')
parser.add_argument('--data-dir', default=None, help='Data directory for client files')
parser.add_argument('--port', type=int, default=5001, help='Port to run on (default: 5001)')
args = parser.parse_args()

app = Flask(__name__)
app.secret_key = 'hiring-process-demo-secret'

# Initialize client
config = Config(config_dir=args.data_dir)
if not config.is_initialized():
    print(f"ERROR: Client not initialized. Run './venv/bin/python cli.py {('--data-dir ' + args.data_dir) if args.data_dir else ''} init' first.")
    exit(1)

encryption = EncryptionManager(config.encryption_key)
db = Database(str(config.db_file))
db.init_db()
sync_engine = SyncEngine(config.server_url, encryption)

# Load workflow definitions
workflow_loader = WorkflowLoader()


@app.route('/')
def index():
    """List all candidates"""
    session = db.get_session()
    try:
        candidates = session.query(models.Candidate).filter_by(deleted=False).all()
        return render_template('index.html', candidates=candidates)
    finally:
        session.close()


@app.route('/table')
def table_view():
    """Table view of all candidates and tasks"""
    session = db.get_session()
    try:
        candidates = session.query(models.Candidate).filter_by(deleted=False).all()

        # Collect all unique tasks across all workflows with their metadata
        task_info = {}  # task_identifier -> {name, workflows, min_layer}

        for candidate in candidates:
            workflow = workflow_loader.get_workflow(candidate.workflow_id)
            if not workflow:
                continue

            # Compute layout for this workflow to get topological layers
            layout, _ = compute_dag_layout(workflow)

            for task_def in workflow.tasks:
                if task_def.identifier not in task_info:
                    task_info[task_def.identifier] = {
                        'name': task_def.name,
                        'workflows': set(),
                        'min_layer': float('inf')
                    }

                task_info[task_def.identifier]['workflows'].add(candidate.workflow_id)
                layer = layout.get(task_def.identifier, {}).get('layer', 0)
                task_info[task_def.identifier]['min_layer'] = min(
                    task_info[task_def.identifier]['min_layer'],
                    layer
                )

        # Sort tasks by (min_layer, -popularity, identifier)
        sorted_tasks = sorted(
            task_info.items(),
            key=lambda x: (x[1]['min_layer'], -len(x[1]['workflows']), x[0])
        )

        # Build candidate task status map
        candidate_data = []
        for candidate in candidates:
            workflow = workflow_loader.get_workflow(candidate.workflow_id)
            if not workflow:
                continue

            # Get workflow task identifiers
            workflow_task_ids = {t.identifier for t in workflow.tasks}

            # Get candidate tasks
            candidate_tasks = session.query(models.CandidateTask).filter_by(
                candidate_id=candidate.id
            ).all()
            task_status = {ct.task_identifier: ct for ct in candidate_tasks}

            # Build task states for this candidate
            task_states = {}
            for task_identifier, _ in sorted_tasks:
                if task_identifier not in workflow_task_ids:
                    task_states[task_identifier] = None  # Task not in this workflow
                else:
                    ct = task_status.get(task_identifier)
                    if ct:
                        # Task exists - use status field directly
                        task_states[task_identifier] = {
                            'state': ct.status or 'not_started',
                            'exists': True
                        }
                    else:
                        # Task doesn't exist yet
                        task_states[task_identifier] = {
                            'state': 'not_started',
                            'exists': False
                        }

            candidate_data.append({
                'candidate': candidate,
                'task_states': task_states
            })

        return render_template('table_view.html',
                             candidate_data=candidate_data,
                             sorted_tasks=sorted_tasks)
    finally:
        session.close()


def compute_dag_layout(workflow):
    """Compute DAG layout with layers based on dependencies"""
    from collections import defaultdict, deque

    # Build dependency graph
    task_deps = {}
    task_by_id = {}
    for task in workflow.tasks:
        task_by_id[task.identifier] = task
        task_deps[task.identifier] = list(task.dependencies)

    # Compute layer for each task (topological sort with levels)
    in_degree = defaultdict(int)
    for task_id, deps in task_deps.items():
        for dep in deps:
            in_degree[task_id] += 1

    # Find all tasks with no dependencies (layer 0)
    queue = deque()
    layers = {}
    for task_id in task_deps.keys():
        if in_degree[task_id] == 0:
            queue.append(task_id)
            layers[task_id] = 0

    # Process tasks level by level
    while queue:
        current = queue.popleft()
        current_layer = layers[current]

        # Check all tasks that depend on current
        for task_id, deps in task_deps.items():
            if current in deps:
                in_degree[task_id] -= 1
                if in_degree[task_id] == 0:
                    # This task's layer is max of all its dependencies + 1
                    max_dep_layer = max(layers[dep] for dep in task_deps[task_id])
                    layers[task_id] = max_dep_layer + 1
                    queue.append(task_id)

    # Group tasks by layer
    layer_groups = defaultdict(list)
    for task_id, layer in layers.items():
        layer_groups[layer].append(task_id)

    # Assign positions within layers
    layout = {}
    for layer, task_ids in layer_groups.items():
        for idx, task_id in enumerate(task_ids):
            layout[task_id] = {
                'layer': layer,
                'index': idx,
                'total_in_layer': len(task_ids)
            }

    return layout, max(layers.values()) if layers else 0


@app.route('/candidate/<candidate_id>/workflow')
def workflow_view(candidate_id):
    """View candidate workflow progress"""
    session = db.get_session()
    try:
        candidate = session.query(models.Candidate).filter_by(id=candidate_id).first()
        if not candidate:
            flash('Candidate not found', 'error')
            return redirect(url_for('index'))

        # Get all tasks for this workflow
        workflow = workflow_loader.get_workflow(candidate.workflow_id)
        if not workflow:
            flash(f'Workflow {candidate.workflow_id} not found', 'error')
            return redirect(url_for('index'))

        # Get all candidate tasks
        candidate_tasks = session.query(models.CandidateTask).filter_by(candidate_id=candidate_id).all()
        task_status = {ct.task_identifier: ct for ct in candidate_tasks}

        # Compute DAG layout
        layout, max_layer = compute_dag_layout(workflow)

        # Build task list with status and layout
        tasks_with_status = []
        for task_def in workflow.tasks:
            ct = task_status.get(task_def.identifier)

            # Determine state
            if ct:
                # Use status field directly
                state = ct.status or 'not_started'
            else:
                state = 'not_started'

            task_info = {
                'definition': task_def,
                'candidate_task': ct,
                'state': state,
                'layout': layout.get(task_def.identifier, {'layer': 0, 'index': 0, 'total_in_layer': 1})
            }
            tasks_with_status.append(task_info)

        return render_template('workflow_view.html',
                             candidate=candidate,
                             workflow=workflow,
                             tasks=tasks_with_status,
                             max_layer=max_layer)
    finally:
        session.close()


@app.route('/candidate/<candidate_id>')
def view_candidate(candidate_id):
    """View candidate details"""
    session = db.get_session()
    try:
        candidate = session.query(models.Candidate).filter_by(id=candidate_id).first()
        if not candidate:
            flash('Candidate not found', 'error')
            return redirect(url_for('index'))

        tasks = session.query(models.CandidateTask).filter_by(candidate_id=candidate_id).all()

        # Get available tasks for this workflow
        workflow_tasks = workflow_loader.get_tasks_for_workflow(candidate.workflow_id)

        return render_template('view.html', candidate=candidate, tasks=tasks, workflow_tasks=workflow_tasks)
    finally:
        session.close()


@app.route('/candidate/add', methods=['GET', 'POST'])
def add_candidate():
    """Add a new candidate"""
    if request.method == 'POST':
        session = db.get_session()
        try:
            candidate_id = f"candidate-{uuid.uuid4().hex[:12]}"

            candidate = models.Candidate(
                id=candidate_id,
                workflow_id=request.form['workflow_id'],
                name=request.form.get('name'),
                email=request.form.get('email'),
                phone=request.form.get('phone'),
                resume_url=request.form.get('resume_url'),
                notes=request.form.get('notes')
            )

            # Mark all set fields as dirty (new candidate needs to be synced)
            if candidate.workflow_id:
                candidate.workflow_id_dirty = True
            if candidate.name:
                candidate.name_dirty = True
            if candidate.email:
                candidate.email_dirty = True
            if candidate.phone:
                candidate.phone_dirty = True
            if candidate.resume_url:
                candidate.resume_url_dirty = True
            if candidate.notes:
                candidate.notes_dirty = True

            session.add(candidate)
            session.commit()

            flash(f'Candidate {candidate.name} added successfully', 'success')
            return redirect(url_for('view_candidate', candidate_id=candidate_id))
        except Exception as e:
            session.rollback()
            flash(f'Error adding candidate: {e}', 'error')
            return redirect(url_for('add_candidate'))
        finally:
            session.close()

    workflows = workflow_loader.get_all_workflows()
    return render_template('add.html', workflows=workflows)


@app.route('/candidate/<candidate_id>/edit', methods=['GET', 'POST'])
def edit_candidate(candidate_id):
    """Edit candidate"""
    session = db.get_session()
    try:
        candidate = session.query(models.Candidate).filter_by(id=candidate_id).first()
        if not candidate:
            flash('Candidate not found', 'error')
            return redirect(url_for('index'))

        if request.method == 'POST':
            # Update fields and mark as dirty
            fields_to_update = ['name', 'email', 'phone', 'resume_url', 'notes', 'workflow_id']

            for field in fields_to_update:
                new_value = request.form.get(field)
                setattr(candidate, field, new_value)
                # Mark field as dirty
                setattr(candidate, f'{field}_dirty', True)

            # Manually set updated_at for user-initiated changes
            candidate.updated_at = datetime.utcnow()

            session.commit()
            flash('Candidate updated successfully', 'success')
            return redirect(url_for('view_candidate', candidate_id=candidate_id))

        workflows = workflow_loader.get_all_workflows()
        return render_template('edit.html', candidate=candidate, workflows=workflows)
    finally:
        session.close()


@app.route('/candidate/<candidate_id>/delete', methods=['POST'])
def delete_candidate(candidate_id):
    """Delete candidate"""
    session = db.get_session()
    try:
        candidate = session.query(models.Candidate).filter_by(id=candidate_id).first()
        if not candidate:
            flash('Candidate not found', 'error')
            return redirect(url_for('index'))

        name = candidate.name
        # Soft delete
        candidate.deleted = True
        candidate.deleted_at = datetime.utcnow()
        session.commit()

        flash(f'Candidate {name} deleted successfully', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        session.rollback()
        flash(f'Error deleting candidate: {e}', 'error')
        return redirect(url_for('view_candidate', candidate_id=candidate_id))
    finally:
        session.close()






@app.route('/api/candidate/<candidate_id>/task/<task_identifier>/update', methods=['POST'])
def api_update_task(candidate_id, task_identifier):
    """API endpoint to update task status

    Accepts JSON body with 'status' field. Valid values: 'not_started', 'in_progress', 'completed', 'na'
    If task doesn't exist and status is provided, creates it with that status.
    """
    session = db.get_session()
    try:
        # Check if candidate exists
        candidate = session.query(models.Candidate).filter_by(id=candidate_id).first()
        if not candidate:
            return {'error': 'Candidate not found'}, 404

        # Get status from request
        data = request.get_json() or {}
        new_status = data.get('status')

        if not new_status:
            return {'error': 'status field required'}, 400

        if new_status not in ['not_started', 'in_progress', 'completed', 'na']:
            return {'error': 'Invalid status. Must be one of: not_started, in_progress, completed, na'}, 400

        # Get or create task
        task = session.query(models.CandidateTask).filter_by(
            candidate_id=candidate_id,
            task_identifier=task_identifier
        ).first()

        if not task:
            # Create new task with the requested status
            task = models.CandidateTask(
                candidate_id=candidate_id,
                task_identifier=task_identifier,
                status=new_status
            )
            session.add(task)
        else:
            # Update existing task status
            task.status = new_status

        # Mark status as dirty
        task.status_dirty = True

        # Manually set updated_at for user-initiated changes
        task.updated_at = datetime.utcnow()

        session.commit()

        return {'success': True, 'status': new_status}, 200
    except Exception as e:
        session.rollback()
        return {'error': str(e)}, 500
    finally:
        session.close()


@app.route('/sync')
def sync_view():
    """Sync management console"""
    session = db.get_session()
    try:
        # Get sync status
        last_sync = config.last_sync
        if last_sync:
            last_sync_dt = datetime.fromisoformat(last_sync)
            last_sync_str = last_sync_dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            last_sync_str = "Never"

        # Count local changes
        unsynced_candidates = session.query(models.Candidate).filter(
            (models.Candidate.last_synced == None) |
            (models.Candidate.updated_at > models.Candidate.last_synced)
        ).count()

        unsynced_tasks = session.query(models.CandidateTask).filter(
            (models.CandidateTask.last_synced == None) |
            (models.CandidateTask.updated_at > models.CandidateTask.last_synced)
        ).count()

        return render_template('sync.html',
                             last_sync=last_sync_str,
                             unsynced_candidates=unsynced_candidates,
                             unsynced_tasks=unsynced_tasks)
    finally:
        session.close()


@app.route('/api/sync/push', methods=['POST'])
def sync_push():
    """Push local changes to server"""
    session = db.get_session()
    logs = []

    try:
        logs.append("🔄 Starting push operation...")

        stats = sync_engine.push_all_dirty(session)

        # Report results
        if stats['candidates_pushed'] > 0:
            logs.append(f"📤 Pushed {stats['candidates_pushed']} candidate(s)")
        else:
            logs.append("✓ No candidates to push")

        if stats['tasks_pushed'] > 0:
            logs.append(f"📤 Pushed {stats['tasks_pushed']} task(s)")
        else:
            logs.append("✓ No tasks to push")

        if stats['candidates_failed'] > 0 or stats['tasks_failed'] > 0:
            logs.append(f"⚠️  Failures: {stats['candidates_failed']} candidates, {stats['tasks_failed']} tasks")
            for failed in stats['failed_items'][:3]:  # Show first 3 failures
                logs.append(f"  ✗ {failed['type']} {failed['id']}: {failed['error']}")

        logs.append("✅ Push complete")
        return jsonify({"success": True, "logs": logs})

    except Exception as e:
        logs.append(f"❌ Push failed: {str(e)}")
        return jsonify({"success": False, "logs": logs}), 500
    finally:
        session.close()


@app.route('/api/sync/pull', methods=['POST'])
def sync_pull():
    """Pull changes from server"""
    session = db.get_session()
    logs = []

    try:
        logs.append("🔄 Starting pull operation...")

        last_sync = config.last_sync
        if last_sync:
            since = datetime.fromisoformat(last_sync)
            logs.append(f"📥 Pulling changes since {since.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            since = None
            logs.append("📥 Performing initial pull (all data)")

        sync_timestamp, stats = sync_engine.pull_all(session, since=since)
        config.last_sync = sync_timestamp

        logs.append("")
        # Report candidates
        if stats['candidates_new'] > 0 or stats['candidates_updated'] > 0:
            logs.append(f"👤 Candidates: {stats['candidates_new']} new, {stats['candidates_updated']} updated")
            for cid in stats['candidates_list'][:5]:  # Show first 5
                logs.append(f"  • {cid}")
            if len(stats['candidates_list']) > 5:
                logs.append(f"  ... and {len(stats['candidates_list']) - 5} more")
        else:
            logs.append("✓ No candidate changes")

        # Report fields
        if stats['fields_updated'] > 0:
            logs.append(f"📝 Fields: {stats['fields_updated']} updated")
            for cid, fields in list(stats['fields_by_candidate'].items())[:3]:  # Show first 3
                logs.append(f"  • {cid}: {', '.join(fields)}")
            if len(stats['fields_by_candidate']) > 3:
                logs.append(f"  ... and {len(stats['fields_by_candidate']) - 3} more candidates")
        else:
            logs.append("✓ No field changes")

        # Report tasks
        if stats['tasks_new'] > 0 or stats['tasks_updated'] > 0:
            logs.append(f"✅ Tasks: {stats['tasks_new']} new, {stats['tasks_updated']} updated")
            for task in stats['tasks_list'][:5]:  # Show first 5
                logs.append(f"  • {task}")
            if len(stats['tasks_list']) > 5:
                logs.append(f"  ... and {len(stats['tasks_list']) - 5} more")
        else:
            logs.append("✓ No task changes")

        # Report action states
        if stats['action_states_new'] > 0 or stats['action_states_updated'] > 0:
            logs.append(f"⚙️  Action states: {stats['action_states_new']} new, {stats['action_states_updated']} updated")
        else:
            logs.append("✓ No action state changes")

        logs.append("")
        logs.append(f"✅ Pull complete at {sync_timestamp}")
        return jsonify({"success": True, "logs": logs})

    except Exception as e:
        logs.append(f"❌ Pull failed: {str(e)}")
        return jsonify({"success": False, "logs": logs}), 500
    finally:
        session.close()


@app.route('/api/sync/full', methods=['POST'])
def sync_full():
    """Full sync: pull first (to get latest versions), then push"""
    session = db.get_session()
    logs = []

    try:
        logs.append("🔄 Starting full sync...")
        logs.append("")

        last_sync = config.last_sync
        if last_sync:
            since = datetime.fromisoformat(last_sync)
            logs.append(f"Syncing changes since {since.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            since = datetime(2000, 1, 1)
            logs.append("Performing initial sync...")

        # Full sync: pull first (to get latest versions), then push
        result = sync_engine.full_sync(session, since=since)

        # Report results
        push_stats = result['push']
        pull_stats = result['pull']

        logs.append("")
        logs.append("=== PULL PHASE ===")
        if pull_stats['candidates_new'] > 0 or pull_stats['candidates_updated'] > 0:
            logs.append(f"📥 Pulled: {pull_stats['candidates_new']} new, {pull_stats['candidates_updated']} updated candidates")
        else:
            logs.append("✓ No candidate changes")

        if pull_stats['fields_updated'] > 0:
            logs.append(f"📝 Updated {pull_stats['fields_updated']} fields")
        else:
            logs.append("✓ No field changes")

        if pull_stats['tasks_new'] > 0 or pull_stats['tasks_updated'] > 0:
            logs.append(f"✅ Pulled: {pull_stats['tasks_new']} new, {pull_stats['tasks_updated']} updated tasks")
        else:
            logs.append("✓ No task changes")

        if pull_stats['action_states_new'] > 0 or pull_stats['action_states_updated'] > 0:
            logs.append(f"⚙️  Pulled: {pull_stats['action_states_new']} new, {pull_stats['action_states_updated']} updated action states")

        logs.append("")
        logs.append("=== PUSH PHASE ===")
        if push_stats['candidates_pushed'] > 0 or push_stats['tasks_pushed'] > 0:
            logs.append(f"📤 Pushed: {push_stats['candidates_pushed']} candidates, {push_stats['tasks_pushed']} tasks")
        else:
            logs.append("✓ Nothing to push")

        if push_stats['candidates_failed'] > 0 or push_stats['tasks_failed'] > 0:
            logs.append(f"⚠️  Failures: {push_stats['candidates_failed']} candidates, {push_stats['tasks_failed']} tasks")
            for failed in push_stats['failed_items'][:3]:  # Show first 3 failures
                logs.append(f"  ✗ {failed['type']} {failed['id']}: {failed['error']}")

        config.last_sync = result['sync_timestamp']
        logs.append("")
        logs.append(f"✅ Full sync complete at {result['sync_timestamp']}")
        return jsonify({"success": True, "logs": logs})

    except Exception as e:
        logs.append(f"❌ Sync failed: {str(e)}")
        return jsonify({"success": False, "logs": logs}), 500
    finally:
        session.close()


@app.route('/api/sync/reset', methods=['POST'])
def sync_reset():
    """NUCLEAR RESET: Delete all local data and re-download from server"""
    session = db.get_session()
    logs = []

    try:
        logs.append("☢️  NUCLEAR RESET - DELETING ALL LOCAL DATA")
        logs.append("This will DELETE everything and re-download from server")
        logs.append("")

        # Count before deletion
        before_candidates = session.query(models.Candidate).count()
        before_tasks = session.query(models.CandidateTask).count()
        before_action_states = session.query(models.ActionState).count()

        logs.append(f"📊 Before: {before_candidates} candidates, {before_tasks} tasks, {before_action_states} action states")
        logs.append("")

        # DELETE ALL DATA
        logs.append("🗑️  Deleting all local data...")
        session.query(models.ActionState).delete()
        logs.append("  ✓ Deleted action states")
        session.query(models.CandidateTask).delete()
        logs.append("  ✓ Deleted tasks")
        session.query(models.Candidate).delete()
        logs.append("  ✓ Deleted candidates")
        session.commit()
        logs.append("")

        # Pull everything from server
        logs.append("📥 Downloading ALL data from server...")
        sync_timestamp, stats = sync_engine.pull_candidates(session, since=None)
        config.last_sync = sync_timestamp

        logs.append("")
        logs.append(f"✅ Reset complete!")
        logs.append(f"👤 Downloaded {stats['candidates_new']} candidates")
        logs.append(f"📝 Downloaded {stats['fields_updated']} field values")
        logs.append(f"✅ Downloaded {stats['tasks_new']} tasks")
        logs.append(f"⚙️  Downloaded {stats['action_states_new'] + stats['action_states_updated']} action states")
        logs.append(f"  • Sync timestamp: {sync_timestamp}")
        logs.append("")
        logs.append("☢️  Local database is now a clean copy of server")

        return jsonify({"success": True, "logs": logs})

    except Exception as e:
        session.rollback()
        logs.append(f"❌ Reset failed: {str(e)}")
        return jsonify({"success": False, "logs": logs}), 500
    finally:
        session.close()


if __name__ == '__main__':
    print("=" * 60)
    print("Hiring Process Management - Web Interface")
    print("=" * 60)
    print(f"Server URL: {config.server_url}")
    print(f"Database: {config.db_file}")
    print("=" * 60)
    print(f"\nStarting web server on http://localhost:{args.port}")
    print("Press Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=args.port, debug=True)
