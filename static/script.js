Chart.defaults.color = '#8B94A7';
Chart.defaults.font.family = "'Outfit', sans-serif";
Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.03)';

const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
        duration: 0 // Keep 0 to avoid jitter during real-time streaming
    },
    scales: {
        x: {
            grid: { color: 'rgba(255, 255, 255, 0.03)' },
            ticks: { maxRotation: 0 }
        },
        y: {
            grid: { color: 'rgba(255, 255, 255, 0.03)' },
            beginAtZero: false
        }
    },
    plugins: {
        legend: { display: false },
        tooltip: {
            backgroundColor: 'rgba(15, 23, 42, 0.9)',
            titleFont: { size: 13, family: 'Outfit' },
            bodyFont: { size: 13, family: 'Outfit' },
            padding: 10,
            cornerRadius: 8,
            displayColors: false
        }
    },
    elements: {
        point: { radius: 0, hitRadius: 10, hoverRadius: 4 }
    }
};

let tempCtx = document.getElementById('tempChart');
let vibCtx = document.getElementById('vibChart');
let tempChart, vibChart;

if (tempCtx && vibCtx) {
    const ctxT = tempCtx.getContext('2d');
    const ctxV = vibCtx.getContext('2d');

    // Create Gradients
    const tempGradient = ctxT.createLinearGradient(0, 0, 0, 400);
    tempGradient.addColorStop(0, 'rgba(245, 158, 11, 0.2)');
    tempGradient.addColorStop(1, 'rgba(245, 158, 11, 0)');

    const vibGradient = ctxV.createLinearGradient(0, 0, 0, 400);
    vibGradient.addColorStop(0, 'rgba(56, 189, 248, 0.2)');
    vibGradient.addColorStop(1, 'rgba(56, 189, 248, 0)');

    tempChart = new Chart(ctxT, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Temperature °C',
                data: [],
                borderColor: '#F59E0B',
                backgroundColor: tempGradient,
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }, {
                label: 'Critical Threshold',
                data: [],
                borderColor: 'rgba(239, 68, 68, 0.8)',
                borderWidth: 1,
                borderDash: [5, 5],
                fill: false,
                pointRadius: 0,
                pointHoverRadius: 0
            }]
        },
        options: commonOptions
    });

    vibChart = new Chart(ctxV, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Vibration mm/s',
                data: [],
                borderColor: '#38BDF8',
                backgroundColor: vibGradient,
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }, {
                label: 'Critical Threshold',
                data: [],
                borderColor: 'rgba(239, 68, 68, 0.8)',
                borderWidth: 1,
                borderDash: [5, 5],
                fill: false,
                pointRadius: 0,
                pointHoverRadius: 0
            }]
        },
        options: commonOptions
    });
}

const MAX_DATA_POINTS = 20;

// Initialize SocketIO
const socket = io();

// SocketIO event listeners
socket.on('sensor_update', function(data) {
    const timeStr = new Date().toLocaleTimeString([], { hour12: false });
    updateUI(data);
    updateCharts(timeStr, data);
});

socket.on('anomaly_update', function(data) {
    updateAnomalyButtons(data.type);
});

socket.on('simulation_status', function(data) {
    updateSimulationButtons(data.running);
});

function applyDashboardState(data) {
    if (!data || !data.dashboard) return;
    const stats = data.dashboard;
    const uptimeEl = document.getElementById('val-uptime');
    const recordsEl = document.getElementById('val-records');
    const failureRateEl = document.getElementById('val-failure-rate');
    const avgRiskEl = document.getElementById('val-avg-risk');
    const incidentCountEl = document.getElementById('incident-count');
    const autoModeEl = document.getElementById('auto-mode');

    if (uptimeEl) uptimeEl.innerText = stats.uptime;
    if (recordsEl) recordsEl.innerText = stats.total_records;
    if (failureRateEl) failureRateEl.innerText = stats.failure_rate + '%';
    if (avgRiskEl) avgRiskEl.innerText = stats.avg_risk + '%';
    if (incidentCountEl) incidentCountEl.innerText = `${stats.alerts.length} incidents logged`;
    if (autoModeEl && data.virtual_state) autoModeEl.checked = data.virtual_state.auto_mode;
    updateSimulationButtons(data.virtual_state?.simulation_running || false);
    renderEventFeed(stats.alerts);
}

socket.on('dashboard_status', function(data) {
    applyDashboardState(data);
});

function renderEventFeed(alerts) {
    const feed = document.getElementById('event-feed');
    if (!feed) return;
    if (!alerts || alerts.length === 0) {
        feed.innerHTML = '<div class="event-card"><h4>No incidents yet</h4><span>Live critical alerts and AI recommendations will appear here.</span></div>';
        return;
    }
    feed.innerHTML = alerts.slice().reverse().map(alert => `
        <div class="event-card">
            <div style="display: flex; justify-content: space-between; align-items: center; gap: 10px;">
                <h4>${alert.message}</h4>
                <span class="event-pill">${alert.level}</span>
            </div>
            <span>${alert.timestamp} • Risk ${alert.risk}%</span>
        </div>
    `).join('');
}

function updateCharts(timeStr, data) {
    if(!tempChart || !vibChart) return;

    if (tempChart.data.labels.length > MAX_DATA_POINTS) {
        tempChart.data.labels.shift();
        tempChart.data.datasets[0].data.shift();
        tempChart.data.datasets[1].data.shift();
        
        vibChart.data.labels.shift();
        vibChart.data.datasets[0].data.shift();
        vibChart.data.datasets[1].data.shift();
    }

    tempChart.data.labels.push(timeStr);
    tempChart.data.datasets[0].data.push(data.temperature);
    tempChart.data.datasets[1].data.push(75); // Safe threshold
    
    vibChart.data.labels.push(timeStr);
    vibChart.data.datasets[0].data.push(data.vibration);
    vibChart.data.datasets[1].data.push(7.5); // Safe threshold
    
    tempChart.update();
    vibChart.update();
}

let activeFailure = false;

function updateUI(data) {
    const tempEl = document.getElementById('val-temp');
    const vibEl = document.getElementById('val-vib');
    const currEl = document.getElementById('val-curr');
    const pressureEl = document.getElementById('val-pressure');
    const rpmEl = document.getElementById('val-rpm');

    if (tempEl) tempEl.innerText = data.temperature;
    if (vibEl) vibEl.innerText = data.vibration;
    if (currEl) currEl.innerText = data.current;
    if (pressureEl && data.pressure !== undefined) pressureEl.innerText = data.pressure;
    if (rpmEl && data.rpm !== undefined) rpmEl.innerText = data.rpm;

    const riskVal = document.getElementById('ai-risk-val');
    const riskBar = document.getElementById('ai-risk-bar');
    const aiRec = document.getElementById('ai-recommendation');
    const aiRootCause = document.getElementById('ai-root-cause');
    const virtualMotor = document.getElementById('virtual-motor');
    const statusBadge = document.getElementById('system-status-badge');
    const statusText = document.getElementById('status-text');
    const floatingAlert = document.getElementById('prediction-alert');

    if (riskBar) riskBar.style.width = data.risk + '%';
    if (riskVal) riskVal.innerText = data.risk + '%';
    if (aiRec) aiRec.innerText = data.recommendation;
    if (aiRootCause && data.root_cause) aiRootCause.innerText = data.root_cause;

    if (data.risk > 50) {
        if (riskBar) riskBar.style.background = 'var(--danger)';
        if (riskVal) riskVal.style.color = 'var(--danger)';
        if (aiRec) aiRec.style.color = 'var(--danger)';
        if (aiRootCause) aiRootCause.style.color = 'var(--danger)';
    } else {
        if (riskBar) riskBar.style.background = 'var(--success)';
        if (riskVal) riskVal.style.color = 'var(--success)';
        if (aiRec) aiRec.style.color = 'white';
        if (aiRootCause) aiRootCause.style.color = 'var(--text-secondary)';
    }

    if (data.prediction === 'Failure Predicted' && !activeFailure) {
        if (statusBadge) statusBadge.classList.add('failure');
        if (statusText) statusText.innerText = 'Failure Imminent';
        if (floatingAlert) floatingAlert.classList.add('show');
        if (virtualMotor) virtualMotor.classList.add('stalled');
        activeFailure = true;
        
        const smsContainer = document.getElementById('sms-status-container');
        const smsText = document.getElementById('sms-status-text');
        if (smsContainer && smsText) {
            smsContainer.style.display = 'flex';
            smsText.innerText = 'Dispatching SMS Alert to Maintenance Team...';
            
            setTimeout(() => {
                if(activeFailure) {
                    smsText.innerText = 'SMS Sent ✓';
                    smsText.style.color = 'var(--success)';
                    const pulse = smsContainer.querySelector('.pulse');
                    if (pulse) {
                        pulse.style.background = 'var(--success)';
                        pulse.style.boxShadow = '0 0 8px var(--success)';
                    }
                }
            }, 2000);
        }
    }
}

function dismissAlert() {
    const floatingAlert = document.getElementById('prediction-alert');
    const statusBadge = document.getElementById('system-status-badge');
    const statusText = document.getElementById('status-text');
    const virtualMotor = document.getElementById('virtual-motor');

    floatingAlert.classList.remove('show');
    statusBadge.classList.remove('failure');
    statusText.innerText = 'Operations Normal';
    virtualMotor.classList.remove('stalled'); // RESTART MOTOR
    activeFailure = false;
    
    const smsContainer = document.getElementById('sms-status-container');
    const smsText = document.getElementById('sms-status-text');
    if (smsContainer && smsText) {
        smsContainer.style.display = 'none';
        smsText.style.color = '#38bdf8'; // reset color
        smsContainer.querySelector('.pulse').style.background = '#38bdf8';
        smsContainer.querySelector('.pulse').style.boxShadow = '0 0 8px #38bdf8';
    }
}

// Manual Inject Controls
async function setAnomaly(type) {
    // UI Update
    updateAnomalyButtons(type);
    
    // Backend API Call
    try {
        await fetch('/api/trigger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: type })
        });
    } catch(err) {
        console.error("Failed to trigger anomaly", err);
    }
}

function updateAnomalyButtons(activeType) {
    document.querySelectorAll('.btn-control').forEach(btn => {
        if (btn.classList.contains('anomaly-' + activeType)) {
            btn.classList.add('active');
        } else if (btn.classList.contains('anomaly-none') || btn.classList.contains('anomaly-heat') || btn.classList.contains('anomaly-vib')) {
            btn.classList.remove('active');
        }
    });
}

// Simulation Control
async function startSimulation() {
    try {
        await fetch('/api/simulation/start', { method: 'POST' });
        updateSimulationButtons(true);
    } catch(err) {
        console.error("Failed to start simulation", err);
    }
}

async function stopSimulation() {
    try {
        await fetch('/api/simulation/stop', { method: 'POST' });
        updateSimulationButtons(false);
    } catch(err) {
        console.error("Failed to stop simulation", err);
    }
}

function updateSimulationButtons(running) {
    const startBtn = document.getElementById('start-sim');
    const stopBtn = document.getElementById('stop-sim');
    
    if (running) {
        startBtn.style.display = 'none';
        stopBtn.style.display = 'inline-block';
    } else {
        startBtn.style.display = 'inline-block';
        stopBtn.style.display = 'none';
    }
}

async function toggleAutoMode() {
    const autoModeCheckbox = document.getElementById('auto-mode');
    const enabled = autoModeCheckbox ? autoModeCheckbox.checked : false;
    try {
        await fetch('/api/auto-mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: enabled })
        });
    } catch(err) {
        console.error("Failed to toggle auto mode", err);
    }
}

async function refreshDashboardState() {
    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();
        if (!data || !data.dashboard) return;

        applyDashboardState(data);
    } catch (err) {
        console.error('Failed to refresh dashboard state', err);
    }
}

window.addEventListener('load', () => {
    if (document.getElementById('start-sim') || document.getElementById('auto-mode')) {
        refreshDashboardState();
    }
});

// Start Stream if we are on Dashboard Page
if (document.getElementById('tempChart')) {
    // WebSocket connection established above
}
