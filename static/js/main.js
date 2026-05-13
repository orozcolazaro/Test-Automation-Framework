let currentSessionId = null;
let currentLogs = [];

const targetUrlInput = document.getElementById('target-url');
const testModeSelect = document.getElementById('test-mode');
const startBtn = document.getElementById('start-btn');
const cancelBtn = document.getElementById('cancel-btn');
const progressSection = document.getElementById('progress-section');
const initialState = document.getElementById('initial-state');
const resultsSection = document.getElementById('results-section');
const logsContainer = document.getElementById('logs-container');
const featuresContainer = document.getElementById('features-container');

document.addEventListener('DOMContentLoaded', () => {
    loadFeatures();
    setupEventListeners();
});

function setupEventListeners() {
    startBtn.addEventListener('click', startTesting);
    cancelBtn.addEventListener('click', cancelTesting);
}

function loadFeatures() {
    fetch('/api/features')
        .then(r => r.json())
        .then(features => {
            featuresContainer.innerHTML = features.map(f => `
                <div class="feature-item">
                    ${f.icon} ${f.name}
                </div>
            `).join('');
        });
}

function startTesting() {
    const url = targetUrlInput.value.trim();
    const mode = testModeSelect.value;
    
    if (!url || !url.match(/^https?:\/\/.+/)) {
        alert('URL válida requerida');
        return;
    }
    
    startBtn.disabled = true;
    cancelBtn.disabled = false;
    
    initialState.style.display = 'none';
    resultsSection.style.display = 'none';
    progressSection.style.display = 'block';
    currentLogs = [];
    logsContainer.innerHTML = '';
    
    fetch('/api/start-test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_url: url, mode: mode })
    })
    .then(r => r.json())
    .then(data => {
        if (data.session_id) {
            currentSessionId = data.session_id;
            document.getElementById('session-id').textContent = data.session_id;
            document.getElementById('session-url').textContent = url;
            document.getElementById('session-mode').textContent = mode;
            pollTestStatus();
        }
    });
}

function pollTestStatus() {
    if (!currentSessionId) return;
    
    fetch(`/api/test-status/${currentSessionId}`)
        .then(r => r.json())
        .then(data => {
            updateProgress(data.progress, data.current_phase);
            pollLogs();
            
            if (data.status === 'running') {
                setTimeout(pollTestStatus, 1000);
            } else if (data.status === 'completed') {
                setTimeout(() => {
                    loadResults();
                    resetUI();
                }, 500);
            }
        });
}

function pollLogs() {
    if (!currentSessionId) return;
    
    const offset = currentLogs.length;
    fetch(`/api/test-logs/${currentSessionId}?offset=${offset}`)
        .then(r => r.json())
        .then(data => {
            data.logs.slice(offset).forEach(log => {
                currentLogs.push(log);
                addLogToUI(log);
            });
        });
}

function addLogToUI(log) {
    const logItem = document.createElement('div');
    logItem.className = 'log-item';
    if (log.includes('ERROR') || log.includes('✗')) logItem.classList.add('error');
    if (log.includes('SUCCESS') || log.includes('✓')) logItem.classList.add('success');
    logItem.textContent = log;
    logsContainer.appendChild(logItem);
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

function updateProgress(progress, phase) {
    document.getElementById('progress-fill').style.width = progress + '%';
    document.getElementById('progress-percent').textContent = progress + '%';
    document.getElementById('current-phase').textContent = phase;
}

function loadResults() {
    if (!currentSessionId) return;
    
    fetch(`/api/test-report/${currentSessionId}`)
        .then(r => r.json())
        .then(data => {
            displayResults(data);
            progressSection.style.display = 'none';
            resultsSection.style.display = 'block';
        });
}

function displayResults(data) {
    document.getElementById('total-bugs').textContent = data.total_bugs;
    document.getElementById('critical-count').textContent = data.bugs_by_severity.CRITICAL || 0;
    document.getElementById('high-count').textContent = data.bugs_by_severity.HIGH || 0;
    document.getElementById('medium-count').textContent = data.bugs_by_severity.MEDIUM || 0;
    document.getElementById('low-count').textContent = data.bugs_by_severity.LOW || 0;
    document.getElementById('bugs-count').textContent = data.total_bugs;
    
    const deploymentEl = document.getElementById('deployment-recommendation');
    if (data.bugs_by_severity.CRITICAL > 0) {
        deploymentEl.textContent = '🔴 BLOQUEAR DEPLOYMENT';
        deploymentEl.className = 'deployment-card block';
    } else {
        deploymentEl.textContent = '✅ APROBAR DEPLOYMENT';
        deploymentEl.className = 'deployment-card approve';
    }
    
    document.getElementById('bugs-list').innerHTML = data.bugs.map(bug => `
        <div class="bug-item ${bug.type}">
            <span class="bug-severity ${bug.type}">${bug.type.toUpperCase()}</span>
            <div class="bug-title">${bug.title}</div>
            <div class="bug-description">${bug.description}</div>
            <div style="margin-top: 8px; font-size: 12px;">Servicios: ${(bug.services || []).join(', ')}</div>
        </div>
    `).join('');
}

function cancelTesting() {
    if (currentSessionId) {
        fetch(`/api/cancel-test/${currentSessionId}`, { method: 'POST' });
    }
    resetUI();
}

function resetUI() {
    startBtn.disabled = false;
    cancelBtn.disabled = true;
}

function exportJSON() {
    if (!currentSessionId) return;
    fetch(`/api/test-report/${currentSessionId}`)
        .then(r => r.json())
        .then(data => {
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            downloadBlob(blob, `report-${currentSessionId}.json`);
        });
}

function exportHTML() {
    if (!currentSessionId) return;
    fetch(`/api/test-report-istqb/${currentSessionId}`)
        .then(r => r.text())
        .then(html => {
            const blob = new Blob([html], { type: 'text/html' });
            downloadBlob(blob, `report-${currentSessionId}.html`);
        });
}

function exportPDF() {
    if (!currentSessionId) {
        alert('Sin sesión activa');
        return;
    }
    
    const url = `/api/test-report-pdf/${currentSessionId}`;
    console.log('Descargando PDF:', url);
    
    fetch(url)
        .then(response => {
            console.log('Response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.blob();
        })
        .then(blob => {
            console.log('Blob size:', blob.size);
            downloadBlob(blob, `report-${currentSessionId}-ISTQB.pdf`);
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error: ' + error.message);
        });
}

function downloadBlob(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

function clearAll() {
    if (confirm('¿Limpiar historial?')) {
        fetch('/api/clear-history', { method: 'POST' });
        currentSessionId = null;
        progressSection.style.display = 'none';
        resultsSection.style.display = 'none';
        initialState.style.display = 'block';
    }
}
