"""
Workflow utility functions for DAG layout and task status management
"""
from collections import defaultdict, deque
from typing import Dict, Tuple
from fastapi import HTTPException


def compute_dag_layout(workflow) -> Tuple[Dict, int]:
    """
    Compute DAG layout with layers based on dependencies.

    Uses Kahn's algorithm (topological sort based on in-degrees) to assign
    tasks to horizontal layers, where each task can only depend on tasks
    in previous layers.

    Args:
        workflow: WorkflowDefinition object with tasks and dependencies

    Returns:
        Tuple of (layout_dict, max_layer):
            - layout_dict: Maps task_id to {layer, index, total_in_layer}
            - max_layer: Maximum layer number (int)

    Raises:
        HTTPException: 400 if a circular dependency is detected.
                      Error message includes the cycle path and workflow name.
    """
    # Build dependency graph
    task_deps = {}
    task_by_id = {}
    for task in workflow.tasks:
        task_by_id[task.identifier] = task
        task_deps[task.identifier] = list(task.dependencies)

    # Calculate in-degrees (number of dependencies for each task)
    in_degree = defaultdict(int)
    for task_id, deps in task_deps.items():
        for dep in deps:
            in_degree[task_id] += 1

    # Topological sort using Kahn's algorithm
    queue = deque()
    layers = {}

    # Start with tasks that have no dependencies (in-degree = 0)
    for task_id in task_deps.keys():
        if in_degree[task_id] == 0:
            queue.append(task_id)
            layers[task_id] = 0

    # Process tasks level by level
    while queue:
        current = queue.popleft()
        current_layer = layers[current]

        # For each task that depends on current task
        for task_id, deps in task_deps.items():
            if current in deps:
                in_degree[task_id] -= 1
                if in_degree[task_id] == 0:
                    # Place task in layer after all its dependencies
                    max_dep_layer = max(layers[dep] for dep in task_deps[task_id])
                    layers[task_id] = max_dep_layer + 1
                    queue.append(task_id)

    # Cycle detection: If not all tasks were processed, there's a cycle
    if len(layers) < len(task_deps):
        # Find tasks that weren't processed (these are in the cycle)
        unprocessed = [task_id for task_id in task_deps.keys() if task_id not in layers]

        # Find a cycle path using DFS
        def find_cycle(start, path, visited):
            if start in path:
                # Found cycle - return the cycle portion
                cycle_start = path.index(start)
                return path[cycle_start:]
            if start in visited:
                return None

            visited.add(start)
            path.append(start)

            for dep in task_deps.get(start, []):
                cycle = find_cycle(dep, path[:], visited)
                if cycle:
                    return cycle

            return None

        # Find an actual cycle
        cycle_path = None
        for task_id in unprocessed:
            cycle_path = find_cycle(task_id, [], set())
            if cycle_path:
                break

        # Format error message
        if cycle_path:
            cycle_str = " -> ".join(cycle_path) + " -> " + cycle_path[0]
            error_msg = f"Circular dependency detected in workflow '{workflow.name}': {cycle_str}"
        else:
            error_msg = f"Circular dependency detected in workflow '{workflow.name}'. Tasks involved: {', '.join(unprocessed)}"

        raise HTTPException(status_code=400, detail=error_msg)

    # Group tasks by layer
    layer_groups = defaultdict(list)
    for task_id, layer in layers.items():
        layer_groups[layer].append(task_id)

    # Build final layout with position information
    layout = {}
    for layer, task_ids in layer_groups.items():
        for idx, task_id in enumerate(task_ids):
            layout[task_id] = {
                'layer': layer,
                'index': idx,
                'total_in_layer': len(task_ids)
            }

    return layout, max(layers.values()) if layers else 0
