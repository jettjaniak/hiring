// Application Initialization

document.addEventListener('DOMContentLoaded', function() {
    // Store original values for table status selects
    document.querySelectorAll('.table-status-select').forEach(select => {
        select.dataset.originalValue = select.value;
    });

    // Store original values for workflow status selects
    document.querySelectorAll('.status-select').forEach(select => {
        select.dataset.originalValue = select.value;
    });

    // Layout DAG if on workflow view page
    if (document.getElementById('dag-container')) {
        layoutDAG();
    }
});
