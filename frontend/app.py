#!/usr/bin/env python3
"""
Simple web interface for hiring process client
"""
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import uuid
import argparse
from datetime import datetime
from database import Database
from workflow_loader import WorkflowLoader
import models

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Hiring Process Web Client')
parser.add_argument('--data-dir', default=None, help='Data directory for client files (default: ~/.hiring-app)')
parser.add_argument('--port', type=int, default=5001, help='Port to run on (default: 5001)')
args = parser.parse_args()

app = Flask(__name__)
app.secret_key = 'hiring-process-demo-secret'

# Initialize database
import os
data_dir = args.data_dir or os.path.expanduser('~/.hiring-app')
os.makedirs(data_dir, exist_ok=True)
db_file = os.path.join(data_dir, 'hiring.db')

db = Database(db_file)
db.init_db()

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
            # Update fields
            fields_to_update = ['name', 'email', 'phone', 'resume_url', 'notes', 'workflow_id']

            for field in fields_to_update:
                new_value = request.form.get(field)
                setattr(candidate, field, new_value)

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

        session.commit()

        return {'success': True, 'status': new_status}, 200
    except Exception as e:
        session.rollback()
        return {'error': str(e)}, 500
    finally:
        session.close()


if __name__ == '__main__':
    print("=" * 60)
    print("Hiring Process Management - Web Interface")
    print("=" * 60)
    print(f"Database: {db_file}")
    print("=" * 60)
    print(f"\nStarting web server on http://localhost:{args.port}")
    print("Press Ctrl+C to stop\n")

    app.run(host='0.0.0.0', port=args.port, debug=True)
