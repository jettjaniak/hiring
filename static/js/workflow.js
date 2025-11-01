// Workflow DAG Layout and Rendering

/**
 * Layout and render the DAG (Directed Acyclic Graph) for workflow visualization
 */
function layoutDAG() {
    const container = document.getElementById('dag-container');
    const svg = document.getElementById('dag-svg');
    const taskCards = document.querySelectorAll('.task-card');

    if (!container || !svg || taskCards.length === 0) return;

    const CARD_WIDTH = 220;
    const CARD_HEIGHT = 80;
    const LAYER_SPACING = 200;
    const HORIZONTAL_SPACING = 40;

    // Build task state map
    const taskStates = new Map();
    taskCards.forEach(card => {
        const taskId = card.dataset.taskId;
        const state = card.classList.contains('na') ? 'na' :
                     card.classList.contains('completed') ? 'completed' :
                     card.classList.contains('in_progress') ? 'in_progress' : 'not_started';
        taskStates.set(taskId, state);
    });

    // Calculate positions for each card
    const positions = new Map();

    taskCards.forEach(card => {
        const taskId = card.dataset.taskId;
        const layer = parseInt(card.dataset.layer);
        const index = parseInt(card.dataset.index);
        const total = parseInt(card.dataset.total);

        // Calculate position
        const x = 50 + (index * (CARD_WIDTH + HORIZONTAL_SPACING));
        const y = 50 + (layer * LAYER_SPACING);

        // Position the card
        card.style.left = x + 'px';
        card.style.top = y + 'px';

        // Check if all dependencies are completed
        const deps = card.dataset.deps;
        if (deps && deps.trim() !== '') {
            const depIds = deps.split(',').filter(d => d.trim() !== '');
            const allDepsCompleted = depIds.every(depId => {
                const depState = taskStates.get(depId);
                return depState === 'completed' || depState === 'na';
            });

            if (!allDepsCompleted) {
                card.classList.add('dependencies-not-ready');
            }
        }

        // Store position for arrow drawing
        positions.set(taskId, {
            x: x,
            y: y,
            width: CARD_WIDTH,
            height: CARD_HEIGHT,
            centerX: x + CARD_WIDTH / 2,
            centerY: y + CARD_HEIGHT / 2,
            bottomX: x + CARD_WIDTH / 2,
            bottomY: y + CARD_HEIGHT,
            topX: x + CARD_WIDTH / 2,
            topY: y
        });
    });

    // Calculate container height
    const maxLayer = Math.max(...Array.from(taskCards).map(c => parseInt(c.dataset.layer)));
    const containerHeight = 100 + ((maxLayer + 1) * LAYER_SPACING);
    container.style.minHeight = containerHeight + 'px';
    svg.setAttribute('height', containerHeight);

    // Calculate container width
    let maxX = 0;
    taskCards.forEach(card => {
        const x = parseInt(card.style.left);
        if (x + CARD_WIDTH > maxX) maxX = x + CARD_WIDTH;
    });
    const containerWidth = maxX + 50;
    svg.setAttribute('width', containerWidth);

    // Draw arrows
    svg.innerHTML = '';

    taskCards.forEach(card => {
        const taskId = card.dataset.taskId;
        const deps = card.dataset.deps;

        if (deps && deps.trim() !== '') {
            const depIds = deps.split(',').filter(d => d.trim() !== '');

            depIds.forEach(depId => {
                const fromPos = positions.get(depId);
                const toPos = positions.get(taskId);

                if (fromPos && toPos) {
                    const depState = taskStates.get(depId);
                    let strokeColor, markerUrl;

                    if (depState === 'completed' || depState === 'na') {
                        strokeColor = '#28a745';
                        markerUrl = 'url(#arrowhead-green)';
                    } else if (depState === 'in_progress') {
                        strokeColor = '#ffc107';
                        markerUrl = 'url(#arrowhead-yellow)';
                    } else {
                        strokeColor = '#adb5bd';
                        markerUrl = 'url(#arrowhead-grey)';
                    }

                    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');

                    const startX = fromPos.bottomX;
                    const startY = fromPos.bottomY;
                    const endX = toPos.topX;
                    const endY = toPos.topY;

                    const midY = (startY + endY) / 2;
                    const d = `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`;

                    path.setAttribute('d', d);
                    path.setAttribute('stroke', strokeColor);
                    path.setAttribute('stroke-width', '2');
                    path.setAttribute('fill', 'none');
                    path.setAttribute('marker-end', markerUrl);

                    svg.appendChild(path);
                }
            });
        }
    });

    // Add arrowhead markers
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');

    const markerGreen = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
    markerGreen.setAttribute('id', 'arrowhead-green');
    markerGreen.setAttribute('markerWidth', '10');
    markerGreen.setAttribute('markerHeight', '10');
    markerGreen.setAttribute('refX', '5');
    markerGreen.setAttribute('refY', '3');
    markerGreen.setAttribute('orient', 'auto');
    const polygonGreen = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    polygonGreen.setAttribute('points', '0 0, 10 3, 0 6');
    polygonGreen.setAttribute('fill', '#28a745');
    markerGreen.appendChild(polygonGreen);
    defs.appendChild(markerGreen);

    const markerYellow = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
    markerYellow.setAttribute('id', 'arrowhead-yellow');
    markerYellow.setAttribute('markerWidth', '10');
    markerYellow.setAttribute('markerHeight', '10');
    markerYellow.setAttribute('refX', '5');
    markerYellow.setAttribute('refY', '3');
    markerYellow.setAttribute('orient', 'auto');
    const polygonYellow = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    polygonYellow.setAttribute('points', '0 0, 10 3, 0 6');
    polygonYellow.setAttribute('fill', '#ffc107');
    markerYellow.appendChild(polygonYellow);
    defs.appendChild(markerYellow);

    const markerGrey = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
    markerGrey.setAttribute('id', 'arrowhead-grey');
    markerGrey.setAttribute('markerWidth', '10');
    markerGrey.setAttribute('markerHeight', '10');
    markerGrey.setAttribute('refX', '5');
    markerGrey.setAttribute('refY', '3');
    markerGrey.setAttribute('orient', 'auto');
    const polygonGrey = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
    polygonGrey.setAttribute('points', '0 0, 10 3, 0 6');
    polygonGrey.setAttribute('fill', '#adb5bd');
    markerGrey.appendChild(polygonGrey);
    defs.appendChild(markerGrey);

    svg.insertBefore(defs, svg.firstChild);
}
