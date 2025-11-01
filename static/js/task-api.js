// Task API Functions

/**
 * Create a task in table view
 */
async function createTableTask(candidateId, taskIdentifier) {
    try {
        const response = await fetch(`/api/candidates/${candidateId}/tasks/${taskIdentifier}?status=not_started`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            location.reload();
        } else {
            const data = await response.json();
            alert('Error: ' + (data.detail || 'Failed to create task'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

/**
 * Update task status in table view
 */
async function updateTableTaskStatus(candidateId, taskIdentifier, select) {
    const newStatus = select.value;
    const originalValue = select.dataset.originalValue || select.value;
    select.disabled = true;

    try {
        const response = await fetch(`/api/candidates/${candidateId}/tasks/${taskIdentifier}?status=${newStatus}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            location.reload();
        } else {
            const data = await response.json();
            alert('Error: ' + (data.detail || 'Failed to update task'));
            select.value = originalValue;
            select.disabled = false;
        }
    } catch (error) {
        alert('Error: ' + error.message);
        select.value = originalValue;
        select.disabled = false;
    }
}

/**
 * Create a task in workflow view
 */
async function createTask(candidateId, taskIdentifier) {
    try {
        const response = await fetch(`/api/candidates/${candidateId}/tasks/${taskIdentifier}?status=not_started`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            location.reload();
        } else {
            const data = await response.json();
            alert('Error: ' + (data.detail || 'Failed to create task'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

/**
 * Update task status in workflow view
 */
async function updateTaskStatus(candidateId, taskIdentifier, select) {
    const newStatus = select.value;
    const originalValue = select.dataset.originalValue || select.value;
    select.disabled = true;

    try {
        const response = await fetch(`/api/candidates/${candidateId}/tasks/${taskIdentifier}?status=${newStatus}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            location.reload();
        } else {
            const data = await response.json();
            alert('Error: ' + (data.detail || 'Failed to update task'));
            select.value = originalValue;
            select.disabled = false;
        }
    } catch (error) {
        alert('Error: ' + error.message);
        select.value = originalValue;
        select.disabled = false;
    }
}
