// Task API Functions

/**
 * Save scroll positions before reload
 */
function saveScrollPosition() {
    // Save window scroll
    sessionStorage.setItem('scrollY', window.scrollY.toString());
    sessionStorage.setItem('scrollX', window.scrollX.toString());

    // Save table wrapper scroll if it exists (for table view)
    const tableWrapper = document.querySelector('.table-wrapper');
    if (tableWrapper) {
        sessionStorage.setItem('tableScrollLeft', tableWrapper.scrollLeft.toString());
        sessionStorage.setItem('tableScrollTop', tableWrapper.scrollTop.toString());
    }
}

/**
 * Restore scroll positions after page load
 */
function restoreScrollPosition() {
    // Restore window scroll
    const scrollY = sessionStorage.getItem('scrollY');
    const scrollX = sessionStorage.getItem('scrollX');
    if (scrollY !== null && scrollX !== null) {
        window.scrollTo(parseInt(scrollX), parseInt(scrollY));
        sessionStorage.removeItem('scrollY');
        sessionStorage.removeItem('scrollX');
    }

    // Restore table wrapper scroll if it exists
    const tableWrapper = document.querySelector('.table-wrapper');
    const tableScrollLeft = sessionStorage.getItem('tableScrollLeft');
    const tableScrollTop = sessionStorage.getItem('tableScrollTop');
    if (tableWrapper && tableScrollLeft !== null && tableScrollTop !== null) {
        tableWrapper.scrollLeft = parseInt(tableScrollLeft);
        tableWrapper.scrollTop = parseInt(tableScrollTop);
        sessionStorage.removeItem('tableScrollLeft');
        sessionStorage.removeItem('tableScrollTop');
    }
}

/**
 * Create a task
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
            saveScrollPosition();
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
 * Update task status
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
            saveScrollPosition();
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
