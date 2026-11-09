let allProjects = [];
let draggedCard = null;

const STATUSES = ['ide', 'research', 'bygger', 'live', 'pausad', 'skrotad'];

/* ── Kanban board ── */

function initProjects() {
    loadProjects();
    setupDragDrop();
}

function loadProjects() {
    fetch('/api/projects')
        .then(r => r.json())
        .then(data => {
            allProjects = data;
            renderKanban();
        });
}

function renderKanban() {
    STATUSES.forEach(s => {
        document.getElementById('col-' + s).innerHTML = '';
        document.getElementById('count-' + s).textContent = '0';
    });

    allProjects.forEach(p => {
        const col = document.getElementById('col-' + p.status);
        if (!col) return;

        const card = document.createElement('div');
        card.className = 'kanban-card';
        card.draggable = true;
        card.dataset.id = p.id;

        let deadlineHtml = '';
        if (p.deadline) {
            const d = p.deadline;
            const today = new Date().toISOString().slice(0, 10);
            const isOverdue = d < today && p.status !== 'live' && p.status !== 'skrotad';
            deadlineHtml = '<span class="kanban-deadline' + (isOverdue ? ' overdue' : '') + '">' +
                '&#128197; ' + d + '</span>';
        }

        const tasksDone = p.tasks_done || 0;
        const tasksTotal = p.tasks_total || 0;
        let tasksHtml = '';
        if (tasksTotal > 0) {
            const pct = Math.round((tasksDone / tasksTotal) * 100);
            tasksHtml = '<div class="kanban-tasks">' +
                '<div class="kanban-tasks-bar"><div class="kanban-tasks-fill" style="width:' + pct + '%"></div></div>' +
                '<span>' + tasksDone + '/' + tasksTotal + '</span></div>';
        }

        card.innerHTML =
            '<a href="/projects/' + p.id + '" class="kanban-card-link">' +
            '<div class="kanban-card-name">' + esc(p.name) + '</div>' +
            (p.description ? '<div class="kanban-card-desc">' + esc(p.description) + '</div>' : '') +
            '<div class="kanban-card-meta">' + deadlineHtml + tasksHtml + '</div>' +
            '</a>';

        col.appendChild(card);
    });

    STATUSES.forEach(s => {
        const count = document.getElementById('col-' + s).children.length;
        document.getElementById('count-' + s).textContent = count;
    });
}

/* ── Drag & drop ── */

function setupDragDrop() {
    document.addEventListener('dragstart', e => {
        const card = e.target.closest('.kanban-card');
        if (!card) return;
        draggedCard = card;
        card.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', card.dataset.id);
    });

    document.addEventListener('dragend', e => {
        if (draggedCard) {
            draggedCard.classList.remove('dragging');
            draggedCard = null;
        }
        document.querySelectorAll('.kanban-col-body.drag-over').forEach(el =>
            el.classList.remove('drag-over')
        );
    });

    document.querySelectorAll('.kanban-col-body').forEach(col => {
        col.addEventListener('dragover', e => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            col.classList.add('drag-over');
        });

        col.addEventListener('dragleave', e => {
            if (!col.contains(e.relatedTarget)) {
                col.classList.remove('drag-over');
            }
        });

        col.addEventListener('drop', e => {
            e.preventDefault();
            col.classList.remove('drag-over');
            const projectId = e.dataTransfer.getData('text/plain');
            const newStatus = col.dataset.status;
            if (!projectId || !newStatus) return;

            fetch('/api/projects/' + projectId, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus })
            }).then(r => {
                if (r.ok) {
                    const proj = allProjects.find(p => p.id == projectId);
                    if (proj) proj.status = newStatus;
                    renderKanban();
                }
            });
        });
    });
}

/* ── New project modal ── */

function openNewProjectModal() {
    document.getElementById('npName').value = '';
    document.getElementById('npDesc').value = '';
    document.getElementById('npStatus').value = 'ide';
    document.getElementById('npBudget').value = '';
    document.getElementById('npDeadline').value = '';
    document.getElementById('npStore').value = '';
    document.getElementById('newProjectModal').classList.add('active');
}

function closeNewProjectModal() {
    document.getElementById('newProjectModal').classList.remove('active');
}

function createProject() {
    const name = document.getElementById('npName').value.trim();
    if (!name) { alert('Ange ett namn.'); return; }

    const body = {
        name: name,
        description: document.getElementById('npDesc').value.trim(),
        status: document.getElementById('npStatus').value,
        budget: parseFloat(document.getElementById('npBudget').value) || null,
        deadline: document.getElementById('npDeadline').value || null,
        store_id: parseInt(document.getElementById('npStore').value) || null,
    };

    fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    })
        .then(r => r.json())
        .then(data => {
            if (data.id) {
                closeNewProjectModal();
                loadProjects();
            }
        });
}

/* ── Project detail ── */

let saveTimeout = null;
let notesSaveTimeout = null;

function initProjectDetail() {
    loadTasks();

    const notesEl = document.getElementById('pdNotes');
    if (notesEl) {
        notesEl.addEventListener('input', () => {
            clearTimeout(notesSaveTimeout);
            notesSaveTimeout = setTimeout(saveNotes, 800);
        });
    }
}

function saveProjectField() {
    const body = {
        name: document.getElementById('pdName').value.trim(),
        description: document.getElementById('pdDesc').value.trim(),
        status: document.getElementById('pdStatus').value,
        budget: parseFloat(document.getElementById('pdBudget').value) || null,
        deadline: document.getElementById('pdDeadline').value || null,
    };

    fetch('/api/projects/' + PROJECT_ID, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    }).then(r => {
        if (r.ok) showSaved('saveIndicator');
    });
}

function saveNotes() {
    fetch('/api/projects/' + PROJECT_ID, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: document.getElementById('pdNotes').value })
    }).then(r => {
        if (r.ok) showSaved('notesSaveIndicator');
    });
}

function showSaved(elId) {
    const el = document.getElementById(elId);
    el.textContent = 'Sparat';
    el.classList.add('visible');
    setTimeout(() => { el.classList.remove('visible'); }, 1500);
}

/* ── Tasks ── */

function loadTasks() {
    fetch('/api/projects/' + PROJECT_ID)
        .then(r => r.json())
        .then(data => {
            renderTasks(data.tasks || []);
        });
}

function renderTasks(tasks) {
    const list = document.getElementById('taskList');
    const done = tasks.filter(t => t.done).length;
    document.getElementById('taskProgress').textContent = done + '/' + tasks.length + ' klara';

    if (tasks.length === 0) {
        list.innerHTML = '<p class="muted" style="padding:8px 0;">Inga uppgifter ännu.</p>';
        return;
    }

    let html = '';
    tasks.forEach(t => {
        html += '<div class="pd-task-item' + (t.done ? ' done' : '') + '">' +
            '<label class="pd-task-check">' +
            '<input type="checkbox"' + (t.done ? ' checked' : '') +
            ' onchange="toggleTask(' + t.id + ', this.checked)">' +
            '<span class="pd-task-text">' + esc(t.text) + '</span>' +
            '</label>' +
            '<button class="pd-task-delete" onclick="deleteTask(' + t.id + ')" title="Ta bort">&times;</button>' +
            '</div>';
    });
    list.innerHTML = html;
}

function addTask() {
    const input = document.getElementById('newTaskInput');
    const text = input.value.trim();
    if (!text) return;

    fetch('/api/projects/' + PROJECT_ID + '/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text })
    }).then(r => {
        if (r.ok) {
            input.value = '';
            loadTasks();
        }
    });
}

function toggleTask(taskId, done) {
    fetch('/api/tasks/' + taskId, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ done: done })
    }).then(() => loadTasks());
}

function deleteTask(taskId) {
    fetch('/api/tasks/' + taskId, {
        method: 'DELETE'
    }).then(() => loadTasks());
}

/* ── Delete project ── */

function confirmDeleteProject(projectId) {
    document.getElementById('deleteModal').classList.add('active');
    document.getElementById('confirmDeleteBtn').onclick = () => {
        fetch('/api/projects/' + projectId, { method: 'DELETE' })
            .then(() => { window.location.href = '/projects'; });
    };
}

function closeDeleteModal() {
    document.getElementById('deleteModal').classList.remove('active');
}

/* ── Util ── */

function esc(s) {
    if (!s) return '';
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}
