// WebSocket connection with reconnection and pywebview support
console.log('Initializing Socket.IO connection...');
const socket = io({
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: Infinity,
    timeout: 20000,
    pingTimeout: 60000,
    pingInterval: 25000
});
console.log('Socket.IO object created:', socket);

// Chart instances
let dbChart = null;
let s21Chart = null;
let historicalChart = null;

// Current measurement data
let currentMeasurement = null;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded');
    console.log('Socket.IO library loaded:', typeof io !== 'undefined');
    console.log('Chart.js library loaded:', typeof Chart !== 'undefined');
    
    initializeCharts();
    setupEventListeners();
    setupWebSocket();
    setupSettingsPage();
    updateTime();
    setInterval(updateTime, 1000);
    
    // Request initial connection status
    console.log('Emitting get_connection_status...');
    socket.emit('get_connection_status');
    
    // Request initial config
    console.log('Emitting get_config...');
    socket.emit('get_config');
});

// Initialize Chart.js charts
function initializeCharts() {
    const dbCtx = document.getElementById('dbChart').getContext('2d');
    dbChart = new Chart(dbCtx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'S11 (dB)',
                data: [],
                borderColor: '#2563eb',
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        font: {
                            size: 10
                        },
                        padding: 5,
                        boxWidth: 15
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: 'Frequency (GHz)',
                        font: {
                            size: 10
                        }
                    },
                    ticks: {
                        font: {
                            size: 9
                        }
                    },
                    max: 0.95
                },
                y: {
                    title: {
                        display: true,
                        text: 'Magnitude (dB)',
                        font: {
                            size: 10
                        }
                    },
                    ticks: {
                        font: {
                            size: 9
                        }
                    },
                    min: -50,
                    max: 0
                }
            },
            animation: {
                duration: 300
            }
        }
    });

    const s21Ctx = document.getElementById('s21Chart').getContext('2d');
    s21Chart = new Chart(s21Ctx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'S21 (dB)',
                data: [],
                borderColor: '#f59e0b',
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        font: {
                            size: 10
                        },
                        padding: 5,
                        boxWidth: 15
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: 'Frequency (GHz)',
                        font: {
                            size: 10
                        }
                    },
                    ticks: {
                        font: {
                            size: 9
                        }
                    },
                    max: 0.95
                },
                y: {
                    title: {
                        display: true,
                        text: 'Magnitude (dB)',
                        font: {
                            size: 10
                        }
                    },
                    ticks: {
                        font: {
                            size: 9
                        }
                    },
                    min: -50,
                    max: 0
                }
            },
            animation: {
                duration: 300
            }
        }
    });

    const historicalCtx = document.getElementById('historicalChart').getContext('2d');
    historicalChart = new Chart(historicalCtx, {
        type: 'line',
        data: {
            datasets: [
                {
                    label: 'S11 Average',
                    data: [],
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.4,
                    fill: false
                },
                {
                    label: 'S11 Max',
                    data: [],
                    borderColor: '#16a34a',
                    backgroundColor: 'rgba(22, 163, 74, 0.1)',
                    borderWidth: 1,
                    pointRadius: 0,
                    tension: 0.4,
                    fill: false,
                    borderDash: [5, 5]
                },
                {
                    label: 'S11 Min',
                    data: [],
                    borderColor: '#dc2626',
                    backgroundColor: 'rgba(220, 38, 38, 0.1)',
                    borderWidth: 1,
                    pointRadius: 0,
                    tension: 0.4,
                    fill: false,
                    borderDash: [5, 5]
                },
                {
                    label: 'S21 Average',
                    data: [],
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.4,
                    fill: false
                },
                {
                    label: 'S21 Max',
                    data: [],
                    borderColor: '#84cc16',
                    backgroundColor: 'rgba(132, 204, 22, 0.1)',
                    borderWidth: 1,
                    pointRadius: 0,
                    tension: 0.4,
                    fill: false,
                    borderDash: [5, 5]
                },
                {
                    label: 'S21 Min',
                    data: [],
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    borderWidth: 1,
                    pointRadius: 0,
                    tension: 0.4,
                    fill: false,
                    borderDash: [5, 5]
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        font: {
                            size: 9
                        },
                        padding: 3,
                        boxWidth: 12
                    }
                },
                annotation: {
                    annotations: {}
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: 'Time (seconds ago)',
                        font: {
                            size: 10
                        }
                    },
                    ticks: {
                        font: {
                            size: 9
                        }
                    },
                    reverse: true
                },
                y: {
                    title: {
                        display: true,
                        text: 'Magnitude (dB)',
                        font: {
                            size: 10
                        }
                    },
                    ticks: {
                        font: {
                            size: 9
                        }
                    }
                }
            },
            animation: {
                duration: 300
            }
        }
    });
    
    // Load reference lines from localStorage
    loadReferenceLines();
}

// Reference Lines Management
function loadReferenceLines() {
    const defaultLines = [
        { enabled: true, label: 'High Level', value: -10, color: '#ef4444' },
        { enabled: true, label: 'Target Level', value: -15, color: '#f59e0b' },
        { enabled: true, label: 'Low Level', value: -20, color: '#10b981' },
        { enabled: true, label: 'Critical Level', value: -25, color: '#8b5cf6' }
    ];
    
    let refLines = [];
    try {
        const stored = localStorage.getItem('referenceLines');
        refLines = stored ? JSON.parse(stored) : defaultLines;
    } catch {
        refLines = defaultLines;
    }
    
    // Update UI
    for (let i = 0; i < 4; i++) {
        const line = refLines[i] || defaultLines[i];
        document.getElementById(`refLine${i+1}Enabled`).checked = line.enabled;
        document.getElementById(`refLine${i+1}Label`).value = line.label;
        document.getElementById(`refLine${i+1}Value`).value = line.value;
        document.getElementById(`refLine${i+1}Color`).value = line.color;
    }
    
    // Update chart
    updateChartReferenceLines();
}

function saveReferenceLines() {
    const refLines = [];
    for (let i = 1; i <= 4; i++) {
        refLines.push({
            enabled: document.getElementById(`refLine${i}Enabled`).checked,
            label: document.getElementById(`refLine${i}Label`).value,
            value: parseFloat(document.getElementById(`refLine${i}Value`).value),
            color: document.getElementById(`refLine${i}Color`).value
        });
    }
    localStorage.setItem('referenceLines', JSON.stringify(refLines));
    updateChartReferenceLines();
    showNotification('Reference lines updated', 'success');
}

function updateChartReferenceLines() {
    if (!historicalChart) return;
    
    const annotations = {};
    
    for (let i = 1; i <= 4; i++) {
        const enabled = document.getElementById(`refLine${i}Enabled`).checked;
        const label = document.getElementById(`refLine${i}Label`).value;
        const value = parseFloat(document.getElementById(`refLine${i}Value`).value);
        const color = document.getElementById(`refLine${i}Color`).value;
        
        if (enabled) {
            annotations[`refLine${i}`] = {
                type: 'line',
                yMin: value,
                yMax: value,
                borderColor: color,
                borderWidth: 2,
                borderDash: [10, 5],
                label: {
                    display: true,
                    content: label,
                    position: 'end',
                    backgroundColor: color,
                    color: '#ffffff',
                    font: {
                        size: 10,
                        weight: 'bold'
                    },
                    padding: 4,
                    borderRadius: 4
                }
            };
        }
    }
    
    historicalChart.options.plugins.annotation.annotations = annotations;
    historicalChart.update('none');
}

// Setup event listeners
function setupEventListeners() {
    // Menu toggle
    const menuToggleBtn = document.getElementById('menuToggle');
    console.log('Menu toggle button:', menuToggleBtn);
    
    if (menuToggleBtn) {
        menuToggleBtn.addEventListener('click', function(e) {
            console.log('Menu clicked!');
            e.stopPropagation();
            const sidebar = document.getElementById('sidebar');
            const mainContent = document.getElementById('mainContent');
            
            console.log('Sidebar:', sidebar);
            console.log('Window width:', window.innerWidth);
            
            // Toggle sidebar visibility (responsive behavior)
            if (window.innerWidth <= 1024) {
                sidebar.classList.toggle('show');
                console.log('Mobile mode - toggled show class');
            } else {
                sidebar.classList.toggle('collapsed');
                mainContent.classList.toggle('expanded');
                console.log('Desktop mode - toggled collapsed class');
            }
        });
    } else {
        console.error('Menu toggle button not found!');
    }
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(event) {
        if (window.innerWidth <= 1024) {
            const sidebar = document.getElementById('sidebar');
            const menuToggle = document.getElementById('menuToggle');
            
            if (!sidebar.contains(event.target) && event.target !== menuToggle && sidebar.classList.contains('show')) {
                sidebar.classList.remove('show');
            }
        }
    });
    
    // Handle window resize
    window.addEventListener('resize', handleResize);

    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.dataset.page;
            switchPage(page);
            
            // Close sidebar on mobile after navigation
            if (window.innerWidth <= 1024) {
                document.getElementById('sidebar').classList.remove('show');
            }
        });
    });

    // Start/Stop buttons
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const saveDataBtn = document.getElementById('saveDataBtn');
    
    if (startBtn) {
        startBtn.addEventListener('click', function() {
            socket.emit('start_sweep');
            this.disabled = true;
            if (stopBtn) stopBtn.disabled = false;
        });
    }

    if (stopBtn) {
        stopBtn.addEventListener('click', function() {
            socket.emit('stop_sweep');
            this.disabled = true;
            if (startBtn) startBtn.disabled = false;
        });
    }
    
    // Analysis button
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', function() {
            analyzeHistoricalData();
        });
    }
    
    // Save Data button
    if (saveDataBtn) {
        saveDataBtn.addEventListener('click', function() {
            saveCurrentMeasurement();
        });
    }
}

// Handle window resize for responsive behavior
function handleResize() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    
    if (window.innerWidth > 1024) {
        // Desktop mode
        sidebar.classList.remove('show');
        if (!sidebar.classList.contains('collapsed')) {
            mainContent.classList.remove('expanded');
        }
    } else {
        // Mobile/Tablet mode
        sidebar.classList.remove('collapsed');
        mainContent.classList.remove('expanded');
    }
    
    // Resize charts to fit new dimensions
    if (dbChart) dbChart.resize();
    if (s21Chart) s21Chart.resize();
    if (historicalChart) historicalChart.resize();
}

// Setup WebSocket handlers
function setupWebSocket() {
    socket.on('connect', function() {
        console.log('Connected to server');
        updateConnectionStatus(true);
        socket.emit('get_config');
        showNotification('Connected to server', 'success');
    });

    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        updateConnectionStatus(false);
        showNotification('Disconnected from server', 'warning');
    });
    
    socket.on('connect_error', function(error) {
        console.error('Connection error:', error);
        updateConnectionStatus(false);
        showNotification('Connection error. Retrying...', 'error');
    });
    
    socket.on('reconnect', function(attemptNumber) {
        console.log('Reconnected after', attemptNumber, 'attempts');
        showNotification('Reconnected to server', 'success');
        socket.emit('get_config');
    });
    
    socket.on('reconnect_attempt', function(attemptNumber) {
        console.log('Reconnection attempt', attemptNumber);
    });
    
    socket.on('reconnect_error', function(error) {
        console.error('Reconnection error:', error);
    });
    
    socket.on('reconnect_failed', function() {
        console.error('Reconnection failed');
        showNotification('Failed to reconnect. Please refresh the page.', 'error');
    });

    socket.on('config', function(data) {
        const configPort = document.getElementById('configPort');
        const configFreq = document.getElementById('configFreq');
        const configPoints = document.getElementById('configPoints');
        const configInterval = document.getElementById('configInterval');
        
        if (configPort) configPort.textContent = data.port;
        if (configFreq) configFreq.textContent = 
            `${data.start_freq.toFixed(2)} - ${data.stop_freq.toFixed(2)} GHz`;
        if (configPoints) configPoints.textContent = data.points;
        if (configInterval) configInterval.textContent = `${data.interval} ms`;
    });

    socket.on('sweep_data', function(data) {
        currentMeasurement = data;  // Store current measurement
        updateDashboard(data);
        updateCharts(data);
        updateDataTable(data);
        
        // Update connection status display in Settings page
        if (data.connection_status) {
            updateConnectionStatusDisplay(data.connection_status);
        }
    });

    socket.on('status', function(data) {
        console.log('Status:', data.message);
        if (data.running !== undefined) {
            document.getElementById('startBtn').disabled = data.running;
            document.getElementById('stopBtn').disabled = !data.running;
        }
        
        // Update connection status if available
        if (data.connection_status) {
            updateConnectionStatusDisplay(data.connection_status);
        }
    });

    socket.on('error', function(data) {
        console.error('Error:', data.message);
        // แสดง notification แทน alert
        showNotification('Error: ' + data.message, 'error');
    });
    
    socket.on('save_result', function(data) {
        const saveBtn = document.getElementById('saveDataBtn');
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.textContent = '💾 Save Data';
        }
        
        if (data.success) {
            // Use message from backend (includes DRC info if available)
            showNotification(data.message || 'Data saved successfully!', 'success');
            
            // Update DRC display if DRC was calculated
            if (data.drc_percent !== null && data.drc_percent !== undefined) {
                const drcValueDisplay = document.getElementById('drcValueDisplay');
                if (drcValueDisplay) {
                    drcValueDisplay.textContent = `${data.drc_percent.toFixed(2)}%`;
                    drcValueDisplay.style.color = '#10b981';
                }
            }
            
            // Auto-increment test number (Test01 -> Test02, Test02 -> Test01 for new sample)
            const testNoSelect = document.getElementById('testNoSelect');
            if (testNoSelect) {
                if (testNoSelect.value === 'Test01') {
                    testNoSelect.value = 'Test02';
                    showNotification('📝 Test number changed to Test02 (same sample)', 'info');
                } else if (testNoSelect.value === 'Test02') {
                    // Reset to Test01 for new sample
                    testNoSelect.value = 'Test01';
                    showNotification('✅ Test02 completed! Ready for new sample (Test01)', 'success');
                }
            }
            
            // Store measurement batch_id
            if (data.batch_id) {
                currentMeasurementBatchId = data.batch_id;
                
                // Update DRC display with new batch_id
                const drcBatchDisplay = document.getElementById('drcBatchIdDisplay');
                if (drcBatchDisplay && data.slip_no && data.sampling_no) {
                    drcBatchDisplay.textContent = `${data.slip_no}/${data.sampling_no}`;
                }
                
                const s21RmsElement = document.getElementById('s21AvgDb');
                if (s21RmsElement && s21RmsElement.textContent !== '--') {
                    const s21Rms = parseFloat(s21RmsElement.textContent);
                    updateDrcDisplay(s21Rms);
                    
                    // Hold DRC value for 5 seconds
                    isDrcHeld = true;
                    if (drcHoldTimer) {
                        clearTimeout(drcHoldTimer);
                    }
                    drcHoldTimer = setTimeout(() => {
                        isDrcHeld = false;
                        drcHoldTimer = null;
                    }, 5000);
                }
            }
            
            // Update last saved display
            if (data.last_saved) {
                updateLastSavedDisplay(data.last_saved);
            }
            if (data.timestamp) {
                document.getElementById('lastSavedTime').textContent = new Date(data.timestamp).toLocaleString();
            }
        } else {
            showNotification(data.message || 'Failed to save data', 'error');
        }
    });
}

// Update dashboard stats
function updateDashboard(data) {
    const sweepCount = document.getElementById('sweepCount');
    const avgDb = document.getElementById('avgDb');
    const maxDb = document.getElementById('maxDb');
    const minDb = document.getElementById('minDb');
    const minDbFreq = document.getElementById('minDbFreq');
    const avgS21 = document.getElementById('avgS21');
    const maxS21 = document.getElementById('maxS21');
    const minS21 = document.getElementById('minS21');
    const lastUpdate = document.getElementById('lastUpdate');
    
    if (sweepCount) sweepCount.textContent = data.sweep_count;
    if (avgDb) avgDb.textContent = data.summary.avg_db.toFixed(2);
    if (maxDb) maxDb.textContent = data.summary.max_db.toFixed(2);
    if (minDb) minDb.textContent = data.summary.min_db.toFixed(2);
    
    // Find frequency at minimum S11
    const minS11Point = data.s11_data.find(d => d.db === data.summary.min_db);
    if (minS11Point && minDbFreq) {
        const freqMHz = (minS11Point.frequency * 1000).toFixed(2);
        minDbFreq.textContent = `@ ${freqMHz} MHz`;
    }
    
    // Update S21 stats
    if (data.summary.s21_avg_db !== undefined) {
        if (avgS21) avgS21.textContent = data.summary.s21_avg_db.toFixed(2);
        if (maxS21) maxS21.textContent = data.summary.s21_max_db.toFixed(2);
        if (minS21) minS21.textContent = data.summary.s21_min_db.toFixed(2);
        
        // Update DRC display with current S21 RMS (only if not held)
        if (currentDrcSettings && !isDrcHeld) {
            updateDrcDisplay(data.summary.s21_avg_db);
        }
    }
    
    // Update last update timestamp
    if (lastUpdate) lastUpdate.textContent = `Last update: ${data.timestamp}`;
}

// Update charts with new data
function updateCharts(data) {
    console.log('=== updateCharts called ===');
    console.log('S11 data points:', data.s11_data?.length || 0);
    console.log('S21 data points:', data.s21_data?.length || 0);
    
    // แสดงตัวอย่างข้อมูล S11 และ S21 เพื่อเปรียบเทียบ
    if (data.s11_data && data.s11_data.length > 0) {
        console.log('S11 Sample[0]:', JSON.stringify(data.s11_data[0]));
    }
    
    if (data.s21_data && data.s21_data.length > 0) {
        console.log('S21 Sample[0]:', JSON.stringify(data.s21_data[0]));
        
        // เปรียบเทียบว่าข้อมูล S11 และ S21 เหมือนกันหรือไม่
        if (data.s11_data && data.s11_data.length > 0) {
            const s11_first = data.s11_data[0];
            const s21_first = data.s21_data[0];
            if (s11_first.real === s21_first.real && s11_first.imag === s21_first.imag) {
                console.error('❌ ERROR: S21 data is IDENTICAL to S11 data!');
            } else {
                console.log('✓ S21 data is DIFFERENT from S11 data');
            }
        }
    }
    
    // Update S11 chart - ใช้วิธี update ปกติ
    if (data.s11_data && data.s11_data.length > 0 && dbChart) {
        // สร้าง array ใหม่โดย deep copy เพื่อป้องกันการอ้างอิงเดียวกัน
        const s11Points = data.s11_data.map(d => ({
            x: parseFloat(d.frequency), 
            y: parseFloat(d.db)
        }));
        
        // Update ข้อมูลในกราฟ
        dbChart.data.datasets[0].data = s11Points;
        dbChart.data.datasets[0].label = 'S11 (dB)';
        dbChart.data.datasets[0].borderColor = '#2563eb';
        dbChart.data.datasets[0].backgroundColor = 'rgba(37, 99, 235, 0.1)';
        dbChart.update('none');
        
        console.log(`✓ S11 Chart Updated: ${s11Points.length} points | Range: ${s11Points[0]?.y.toFixed(2)} to ${s11Points[s11Points.length-1]?.y.toFixed(2)} dB`);
    }

    // Update S21 chart - ใช้วิธี update ปกติ (แยกจาก S11 โดยสิ้นเชิง)
    if (data.s21_data && data.s21_data.length > 0 && s21Chart) {
        // สร้าง array ใหม่โดย deep copy เพื่อป้องกันการอ้างอิงเดียวกัน
        const s21Points = data.s21_data.map(d => ({
            x: parseFloat(d.frequency), 
            y: parseFloat(d.db)
        }));
        
        // Update ข้อมูลในกราฟ S21 โดยไม่ยุ่งกับ S11
        s21Chart.data.datasets[0].data = s21Points;
        s21Chart.data.datasets[0].label = 'S21 (dB)';
        s21Chart.data.datasets[0].borderColor = '#f59e0b';
        s21Chart.data.datasets[0].backgroundColor = 'rgba(245, 158, 11, 0.1)';
        s21Chart.update('none');
        
        console.log(`✓ S21 Chart Updated: ${s21Points.length} points | Range: ${s21Points[0]?.y.toFixed(2)} to ${s21Points[s21Points.length-1]?.y.toFixed(2)} dB`);
    } else if (s21Chart) {
        // ถ้าไม่มีข้อมูล S21 ให้ล้างกราฟ
        s21Chart.data.datasets[0].data = [];
        s21Chart.update('none');
        console.log('⚠ S21 Chart: No data available - cleared');
    }
    
    // Update Historical chart
    if (data.historical && historicalChart) {
        const currentTime = Date.now() / 1000;
        const timePoints = data.historical.timestamps.map(t => currentTime - t);
        
        historicalChart.data.datasets[0].data = timePoints.map((t, i) => ({
            x: t,
            y: data.historical.s11_avg[i]
        }));
        
        historicalChart.data.datasets[1].data = timePoints.map((t, i) => ({
            x: t,
            y: data.historical.s11_max[i]
        }));
        
        historicalChart.data.datasets[2].data = timePoints.map((t, i) => ({
            x: t,
            y: data.historical.s11_min[i]
        }));
        
        historicalChart.data.datasets[3].data = timePoints.map((t, i) => ({
            x: t,
            y: data.historical.s21_avg[i]
        }));
        
        historicalChart.data.datasets[4].data = timePoints.map((t, i) => ({
            x: t,
            y: data.historical.s21_max[i]
        }));
        
        historicalChart.data.datasets[5].data = timePoints.map((t, i) => ({
            x: t,
            y: data.historical.s21_min[i]
        }));
        
        historicalChart.update('none');
        console.log(`✓ Historical Chart Updated: ${timePoints.length} points`);
    }
    
    console.log('=== updateCharts completed ===\n');
}

// Update data table
function updateDataTable(data) {
    const tbody = document.getElementById('dataTableBody');
    tbody.innerHTML = '';

    // Show first 20 points to avoid overwhelming the table
    const displayData = data.s21_data && data.s21_data.length > 0 ? data.s21_data.slice(0, 20) : [];

    if (displayData.length === 0) {
        const row = tbody.insertRow();
        row.innerHTML = `<td colspan="6" class="no-data">No S21 data available</td>`;
        return;
    }

    displayData.forEach(point => {
        const row = tbody.insertRow();
        row.innerHTML = `
            <td>${point.frequency.toFixed(3)}</td>
            <td>${point.magnitude.toFixed(6)}</td>
            <td>${point.db.toFixed(2)}</td>
            <td>${point.phase.toFixed(2)}</td>
            <td>${point.real.toFixed(6)}</td>
            <td>${point.imag.toFixed(6)}</td>
        `;
    });

    if (data.s21_data.length > 20) {
        const row = tbody.insertRow();
        row.innerHTML = `<td colspan="6" class="no-data">Showing first 20 of ${data.s21_data.length} points</td>`;
    }
}

// Switch between pages
function switchPage(pageName) {
    console.log('Switching to page:', pageName);
    
    // Update navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === pageName) {
            item.classList.add('active');
        }
    });

    // Update pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    document.getElementById(pageName + 'Page').classList.add('active');
    
    // Load models when switching to models page
    if (pageName === 'models') {
        console.log('Models page activated, loading models...');
        loadTrainedModels();
    }
    
    // Initialize batch mode listener when switching to analysis page
    if (pageName === 'analysis') {
        console.log('Analysis page activated, initializing batch mode listener...');
        setTimeout(() => initBatchModeListener(), 100);
    }
}

// Update connection status
function updateConnectionStatus(connected) {
    const statusIndicator = document.getElementById('connectionStatus');
    const statusText = statusIndicator.querySelector('span:last-child');
    
    if (connected) {
        statusIndicator.classList.add('connected');
        statusText.textContent = 'Connected';
    } else {
        statusIndicator.classList.remove('connected');
        statusText.textContent = 'Disconnected';
    }
}

// Update current time
function updateTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', { hour12: false });
    document.getElementById('currentTime').textContent = timeString;
}

// Show notification without blocking
function showNotification(message, type = 'info') {
    // สร้าง notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        padding: 15px 20px;
        background-color: ${type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
        max-width: 400px;
        font-size: 14px;
    `;
    
    // เพิ่ม animation
    const style = document.createElement('style');
    if (!document.getElementById('notification-style')) {
        style.id = 'notification-style';
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(400px); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(400px); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }
    
    // เพิ่ม notification เข้าไปใน body
    document.body.appendChild(notification);
    
    // ลบ notification หลังจาก 5 วินาที
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 5000);
}
// Settings page functionality
function setupSettingsPage() {
    const scanPortsBtn = document.getElementById('scanPortsBtn');
    const testConnectionBtn = document.getElementById('testConnectionBtn');
    const updateConfigBtn = document.getElementById('updateConfigBtn');
    const updateRefLinesBtn = document.getElementById('updateRefLinesBtn');
    const portSelect = document.getElementById('portSelect');
    
    // Scan for available ports
    if (scanPortsBtn) {
        scanPortsBtn.addEventListener('click', () => {
            console.log('Scan Ports button clicked');
            socket.emit('scan_ports');
            showNotification('Scanning for COM ports...', 'info');
        });
    } else {
        console.error('scanPortsBtn element not found');
    }
    
    // Test connection
    if (testConnectionBtn) {
        testConnectionBtn.addEventListener('click', () => {
            const selectedPort = portSelect.value;
            if (!selectedPort) {
                showNotification('Please select a port first', 'error');
                return;
            }
            socket.emit('test_connection', { port: selectedPort });
            showNotification('Testing connection...', 'info');
        });
    }
    
    // Update configuration
    if (updateConfigBtn) {
        updateConfigBtn.addEventListener('click', () => {
            const config = {
                start_freq: parseFloat(document.getElementById('startFreqInput').value),
                stop_freq: parseFloat(document.getElementById('stopFreqInput').value),
                points: parseInt(document.getElementById('pointsInput').value),
                interval: parseInt(document.getElementById('intervalInput').value)
            };
            
            socket.emit('update_config', config);
            showNotification('Updating configuration...', 'info');
        });
    }
    
    // Update reference lines
    if (updateRefLinesBtn) {
        updateRefLinesBtn.addEventListener('click', () => {
            saveReferenceLines();
        });
    }
    
    // Reference line input listeners
    for (let i = 1; i <= 4; i++) {
        ['Enabled', 'Label', 'Value', 'Color'].forEach(prop => {
            const elem = document.getElementById(`refLine${i}${prop}`);
            if (elem) {
                elem.addEventListener('change', () => {
                    // Auto-update chart when values change
                    updateChartReferenceLines();
                });
            }
        });
    }
    
    // Change port when selected
    if (portSelect) {
        portSelect.addEventListener('change', () => {
            const selectedPort = portSelect.value;
            if (selectedPort) {
                socket.emit('change_port', { port: selectedPort });
            }
        });
    }
}

// Handle ports list from server
socket.on('ports_list', (data) => {
    console.log('Received ports_list:', data);
    const portSelect = document.getElementById('portSelect');
    if (!portSelect) {
        console.error('portSelect element not found');
        return;
    }
    
    // Clear existing options except first
    portSelect.innerHTML = '<option value="">-- Select Port --</option>';
    
    // Add available ports
    data.ports.forEach(port => {
        const option = document.createElement('option');
        option.value = port.port;
        option.textContent = `${port.port} - ${port.description}`;
        portSelect.appendChild(option);
    });
    
    showNotification(`Found ${data.ports.length} COM port(s)`, 'success');
});

// Handle connection test result
socket.on('connection_test', (data) => {
    if (data.success) {
        showNotification(`✓ Connection test passed: ${data.port}`, 'success');
    } else {
        showNotification(`✗ Connection test failed: ${data.message}`, 'error');
    }
});

// Update connection status display
function updateConnectionStatusDisplay(status) {
    const deviceStatus = document.getElementById('deviceStatus');
    const statusPort = document.getElementById('statusPort');
    const statusLastSweep = document.getElementById('statusLastSweep');
    const signalQualityFill = document.getElementById('signalQualityFill');
    const signalQualityText = document.getElementById('signalQualityText');
    
    if (!deviceStatus) return;
    
    const indicator = deviceStatus.querySelector('.status-indicator');
    const statusText = deviceStatus.querySelector('.status-text');
    
    if (status.connected) {
        deviceStatus.className = 'status-badge status-connected';
        statusText.textContent = 'Connected';
        indicator.style.backgroundColor = '#10b981';
    } else {
        deviceStatus.className = 'status-badge status-disconnected';
        statusText.textContent = status.error ? 'Error' : 'Disconnected';
        indicator.style.backgroundColor = '#ef4444';
    }
    
    if (statusPort) statusPort.textContent = status.port || '--';
    if (statusLastSweep) statusLastSweep.textContent = status.last_sweep_time || '--';
    
    // Update signal quality bar
    if (signalQualityFill && signalQualityText) {
        const quality = status.signal_quality || 0;
        signalQualityFill.style.width = `${quality}%`;
        signalQualityText.textContent = `${quality.toFixed(0)}%`;
        
        // Color based on quality
        if (quality >= 70) {
            signalQualityFill.style.backgroundColor = '#10b981';
        } else if (quality >= 40) {
            signalQualityFill.style.backgroundColor = '#f59e0b';
        } else {
            signalQualityFill.style.backgroundColor = '#ef4444';
        }
    }
}

// Handle connection status updates
socket.on('connection_status_update', (status) => {
    updateConnectionStatusDisplay(status);
});

// Update config display when received
socket.on('config', (config) => {
    const startFreqInput = document.getElementById('startFreqInput');
    const stopFreqInput = document.getElementById('stopFreqInput');
    const pointsInput = document.getElementById('pointsInput');
    const intervalInput = document.getElementById('intervalInput');
    const portSelect = document.getElementById('portSelect');
    
    if (startFreqInput) startFreqInput.value = config.start_freq;
    if (stopFreqInput) stopFreqInput.value = config.stop_freq;
    if (pointsInput) pointsInput.value = config.points;
    if (intervalInput) intervalInput.value = config.interval;
    if (portSelect && portSelect.options.length > 1) {
        // Set selected port
        for (let i = 0; i < portSelect.options.length; i++) {
            if (portSelect.options[i].value === config.port) {
                portSelect.selectedIndex = i;
                break;
            }
        }
    }
});

// Analysis functions
function analyzeHistoricalData() {
    const analyzeBtn = document.getElementById('analyzeBtn');
    const analysisStatus = document.getElementById('analysisStatus');
    
    analyzeBtn.disabled = true;
    analysisStatus.textContent = '🔄 Analyzing data...';
    analysisStatus.style.color = '#f59e0b';
    
    socket.emit('analyze_measurements', {
        threshold: -8.0,  // S11 threshold to detect measurement
        min_duration: 5   // Minimum points for a valid period
    });
}

socket.on('analysis_result', (result) => {
    const analyzeBtn = document.getElementById('analyzeBtn');
    const analysisStatus = document.getElementById('analysisStatus');
    
    analyzeBtn.disabled = false;
    
    if (!result.success) {
        analysisStatus.textContent = '⚠️ ' + result.message;
        analysisStatus.style.color = '#ef4444';
        return;
    }
    
    analysisStatus.textContent = `✓ Analysis complete: ${result.periods.length} period(s) detected`;
    analysisStatus.style.color = '#10b981';
    
    // Display results
    displayAnalysisResults(result);
});

function displayAnalysisResults(result) {
    // Display periods
    const periodsContainer = document.getElementById('periodsContainer');
    periodsContainer.innerHTML = '';
    
    result.periods.forEach(period => {
        const periodCard = document.createElement('div');
        periodCard.className = 'period-card';
        periodCard.innerHTML = `
            <div class="period-header">
                <h4>Period ${period.id}</h4>
                <span class="period-time">${formatTimeAgo(period.time_ago)}</span>
            </div>
            <div class="period-stats">
                <div class="period-stat">
                    <span class="stat-label">Duration</span>
                    <span class="stat-value">${period.duration.toFixed(1)}s</span>
                </div>
                <div class="period-stat">
                    <span class="stat-label">Points</span>
                    <span class="stat-value">${period.num_points}</span>
                </div>
                <div class="period-stat">
                    <span class="stat-label">S11 RMS</span>
                    <span class="stat-value">${period.s11_rms.toFixed(2)} dB</span>
                </div>
                <div class="period-stat">
                    <span class="stat-label">S21 RMS</span>
                    <span class="stat-value">${period.s21_rms.toFixed(2)} dB</span>
                </div>
                <div class="period-stat">
                    <span class="stat-label">S11 Range</span>
                    <span class="stat-value">${period.s11_range.toFixed(2)} dB</span>
                </div>
                <div class="period-stat">
                    <span class="stat-label">S21 Range</span>
                    <span class="stat-value">${period.s21_range.toFixed(2)} dB</span>
                </div>
            </div>
        `;
        periodsContainer.appendChild(periodCard);
    });
    
    // Display comparisons
    const comparisonsContainer = document.getElementById('comparisonsContainer');
    comparisonsContainer.innerHTML = '';
    
    if (result.comparisons.length === 0) {
        comparisonsContainer.innerHTML = '<div class="no-data">Need at least 2 periods for comparison</div>';
    } else {
        result.comparisons.forEach(comp => {
            const compCard = document.createElement('div');
            compCard.className = `comparison-card ${comp.is_same ? 'same-sample' : 'different-sample'}`;
            compCard.innerHTML = `
                <div class="comparison-header">
                    <h4>Period ${comp.period_1} vs Period ${comp.period_2}</h4>
                    <span class="similarity-badge ${comp.is_same ? 'badge-success' : 'badge-warning'}">
                        ${comp.similarity.toFixed(1)}% ${comp.is_same ? '✓ Same' : '⚠ Different'}
                    </span>
                </div>
                <div class="comparison-details">
                    <div class="comparison-row">
                        <span class="detail-label">S11 RMS:</span>
                        <span class="detail-value">${comp.s11_rms_1.toFixed(2)} dB vs ${comp.s11_rms_2.toFixed(2)} dB (Δ ${comp.s11_diff.toFixed(2)} dB)</span>
                    </div>
                    <div class="comparison-row">
                        <span class="detail-label">S21 RMS:</span>
                        <span class="detail-value">${comp.s21_rms_1.toFixed(2)} dB vs ${comp.s21_rms_2.toFixed(2)} dB (Δ ${comp.s21_diff.toFixed(2)} dB)</span>
                    </div>
                </div>
            `;
            comparisonsContainer.appendChild(compCard);
        });
    }
    
    // Update summary
    document.getElementById('totalPeriods').textContent = result.summary.total_periods;
    document.getElementById('totalComparisons').textContent = result.summary.total_comparisons;
    document.getElementById('sameSampleCount').textContent = result.summary.same_sample_count;
    document.getElementById('avgSimilarity').textContent = result.summary.avg_similarity.toFixed(1) + '%';
}

function formatTimeAgo(seconds) {
    if (seconds < 60) {
        return `${Math.round(seconds)}s ago`;
    } else if (seconds < 3600) {
        return `${Math.round(seconds / 60)}m ago`;
    } else {
        return `${Math.round(seconds / 3600)}h ago`;
    }
}

// Save measurement functions
function saveCurrentMeasurement() {
    if (!currentMeasurement) {
        showNotification('No measurement data available to save', 'warning');
        return;
    }
    
    // Get batch info from input fields
    const slipNo = document.getElementById('slipNoInput').value.trim();
    const samplingNo = document.getElementById('samplingNoInput').value.trim();
    const testNo = document.getElementById('testNoSelect').value;
    
    // Validate inputs
    if (!slipNo) {
        showNotification('Please enter Slip No.', 'warning');
        document.getElementById('slipNoInput').focus();
        return;
    }
    
    if (!samplingNo) {
        showNotification('Please enter Sampling No.', 'warning');
        document.getElementById('samplingNoInput').focus();
        return;
    }
    
    const saveBtn = document.getElementById('saveDataBtn');
    saveBtn.disabled = true;
    saveBtn.textContent = '💾 Saving...';
    
    // Add batch info to measurement data
    const measurementData = {
        ...currentMeasurement,
        slip_no: slipNo,
        sampling_no: samplingNo,
        test_no: testNo
    };
    
    console.log('Saving measurement:', measurementData);
    socket.emit('save_measurement', measurementData);
}

socket.on('last_saved_info', (info) => {
    if (info && info.timestamp) {
        updateLastSavedDisplay(info);
    }
});

function updateLastSavedDisplay(info) {
    const lastSavedTime = document.getElementById('lastSavedTime');
    if (info && info.timestamp) {
        const timeStr = new Date(info.timestamp).toLocaleString();
        const batchInfo = info.slip_no && info.sampling_no 
            ? `${info.slip_no}/${info.sampling_no}/${info.test_no}` 
            : (info.batch_id || '');
        
        // Build display text with DRC if available
        let displayText = `${timeStr} (${batchInfo})`;
        
        // Build tooltip with measurement details
        let tooltip = `Sweep #${info.sweep_count} - S11: ${info.s11_rms.toFixed(2)} dB, S21: ${info.s21_rms.toFixed(2)} dB`;
        if (info.drc_percent !== null && info.drc_percent !== undefined) {
            tooltip += `, DRC: ${info.drc_percent.toFixed(2)}%`;
        }
        
        lastSavedTime.textContent = displayText;
        lastSavedTime.title = tooltip;
    }
}

function showNotification(message, type = 'info') {
    const prefix = type === 'success' ? '✓' : type === 'error' ? '✗' : type === 'warning' ? '⚠' : 'ℹ';
    console.log(`${prefix} ${message}`);
    
    // Create toast notification
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };
    
    const titles = {
        success: 'Success',
        error: 'Error',
        warning: 'Warning',
        info: 'Info'
    };
    
    toast.innerHTML = `
        <div class="toast-icon">${icons[type] || icons.info}</div>
        <div class="toast-content">
            <div class="toast-title">${titles[type] || titles.info}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    container.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 300);
    }, 5000);
}

// Request last saved info on load
socket.on('connect', () => {
    socket.emit('get_last_saved');
});

// Historical Data functions
function queryHistoricalData() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const limit = parseInt(document.getElementById('limitRecords').value);
    
    const loadingMsg = document.getElementById('historyLoadingMsg');
    const errorMsg = document.getElementById('historyErrorMsg');
    const queryBtn = document.getElementById('queryDataBtn');
    
    loadingMsg.style.display = 'block';
    errorMsg.style.display = 'none';
    queryBtn.disabled = true;
    queryBtn.textContent = '⏳ Querying...';
    
    socket.emit('query_historical_data', {
        start_date: startDate || null,
        end_date: endDate || null,
        limit: limit
    });
}

socket.on('historical_data_result', (result) => {
    const loadingMsg = document.getElementById('historyLoadingMsg');
    const errorMsg = document.getElementById('historyErrorMsg');
    const queryBtn = document.getElementById('queryDataBtn');
    const recordCount = document.getElementById('recordCount');
    const tableBody = document.getElementById('historyTableBody');
    
    loadingMsg.style.display = 'none';
    queryBtn.disabled = false;
    queryBtn.textContent = '🔍 Query Data';
    
    if (result.success) {
        recordCount.textContent = `${result.count} records`;
        
        if (result.data && result.data.length > 0) {
            tableBody.innerHTML = '';
            window.historicalDataCache = result.data; // Cache for export
            result.data.forEach((row, index) => {
                const tr = document.createElement('tr');
                const timestamp = new Date(row.timestamp).toLocaleString();
                const drcDisplay = row.drc_percent !== null ? row.drc_percent : '--';
                const s11Count = row.s11_data ? row.s11_data.length : 0;
                const s21Count = row.s21_data ? row.s21_data.length : 0;
                
                tr.innerHTML = `
                    <td>${timestamp}</td>
                    <td>${row.sweep_count}</td>
                    <td>${row.batch_id}</td>
                    <td>${row.s11_rms}</td>
                    <td>${row.s11_min}</td>
                    <td>${row.s11_max}</td>
                    <td>${row.s21_rms}</td>
                    <td>${row.s21_min}</td>
                    <td>${row.s21_max}</td>
                    <td>${drcDisplay}</td>
                    <td class="s11-array-cell" title="Click to view ${s11Count} values">
                        <span class="array-count">${s11Count} values</span>
                        <button class="btn-small btn-view" onclick="viewArrayData(${index}, 's11')" title="View S11 Data">📊</button>
                    </td>
                    <td class="s21-array-cell" title="Click to view ${s21Count} values">
                        <span class="array-count">${s21Count} values</span>
                        <button class="btn-small btn-view" onclick="viewArrayData(${index}, 's21')" title="View S21 Data">📊</button>
                    </td>
                    <td>
                        <button class="btn-small btn-view" onclick="viewDetails('${row.timestamp}')" title="View Details">👁️</button>
                    </td>
                `;
                tableBody.appendChild(tr);
            });
        } else {
            tableBody.innerHTML = '<tr><td colspan="13" class="no-data">No records found for the selected criteria.</td></tr>';
        }
    } else {
        errorMsg.textContent = '❌ ' + result.message;
        errorMsg.style.display = 'block';
        recordCount.textContent = '0 records';
        tableBody.innerHTML = '<tr><td colspan="11" class="no-data">Query failed. Check database connection.</td></tr>';
    }
});

function viewArrayData(index, type) {
    if (!window.historicalDataCache || !window.historicalDataCache[index]) {
        alert('Data not available');
        return;
    }
    
    const row = window.historicalDataCache[index];
    const data = type === 's11' ? row.s11_data : row.s21_data;
    const timestamp = new Date(row.timestamp).toLocaleString();
    
    if (!data || data.length === 0) {
        alert('No data available');
        return;
    }
    
    // Create modal content
    let content = `<div class="array-modal">
        <h3>${type.toUpperCase()} Data - ${timestamp}</h3>
        <p>Sweep Count: ${row.sweep_count}</p>
        <table class="array-table">
            <thead>
                <tr>
                    <th>Index</th>
                    <th>Value (dB)</th>
                </tr>
            </thead>
            <tbody>`;
    
    data.forEach((value, i) => {
        content += `<tr><td>${i + 1}</td><td>${value}</td></tr>`;
    });
    
    content += `</tbody></table>
        <button onclick="exportArrayToCsv(${index}, '${type}')" class="btn-primary">📥 Export to CSV</button>
        <button onclick="closeArrayModal()" class="btn-secondary">Close</button>
    </div>`;
    
    // Create modal
    const modal = document.createElement('div');
    modal.id = 'arrayModal';
    modal.className = 'modal';
    modal.innerHTML = `<div class="modal-content">${content}</div>`;
    document.body.appendChild(modal);
    modal.style.display = 'block';
}

function closeArrayModal() {
    const modal = document.getElementById('arrayModal');
    if (modal) {
        modal.remove();
    }
}

function exportArrayToCsv(index, type) {
    if (!window.historicalDataCache || !window.historicalDataCache[index]) {
        alert('Data not available');
        return;
    }
    
    const row = window.historicalDataCache[index];
    const data = type === 's11' ? row.s11_data : row.s21_data;
    const timestamp = new Date(row.timestamp).toISOString().replace(/[:.]/g, '-');
    
    let csv = `Index,${type.toUpperCase()} (dB)\n`;
    data.forEach((value, i) => {
        csv += `${i + 1},${value}\n`;
    });
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${type}_data_${timestamp}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

function exportToCsv() {
    if (!window.historicalDataCache || window.historicalDataCache.length === 0) {
        alert('No data to export');
        return;
    }
    
    const data = window.historicalDataCache;
    
    // Build CSV with headers
    let csv = 'Timestamp,Sweep Count,Batch ID,S11 RMS,S11 Min,S11 Max,S21 RMS,S21 Min,S21 Max,DRC %';
    
    // Add S11 columns (101 values)
    for (let i = 1; i <= 101; i++) {
        csv += `,S11_${i}`;
    }
    
    // Add S21 columns (101 values)
    for (let i = 1; i <= 101; i++) {
        csv += `,S21_${i}`;
    }
    csv += '\n';
    
    // Add data rows
    data.forEach(row => {
        const timestamp = new Date(row.timestamp).toLocaleString();
        const drcDisplay = row.drc_percent !== null ? row.drc_percent : '';
        
        let rowData = `"${timestamp}",${row.sweep_count},"${row.batch_id}",${row.s11_rms},${row.s11_min},${row.s11_max},${row.s21_rms},${row.s21_min},${row.s21_max},${drcDisplay}`;
        
        // Add S11 data (pad with empty if less than 101)
        const s11Data = row.s11_data || [];
        for (let i = 0; i < 101; i++) {
            rowData += `,${s11Data[i] !== undefined ? s11Data[i] : ''}`;
        }
        
        // Add S21 data (pad with empty if less than 101)
        const s21Data = row.s21_data || [];
        for (let i = 0; i < 101; i++) {
            rowData += `,${s21Data[i] !== undefined ? s21Data[i] : ''}`;
        }
        
        csv += rowData + '\n';
    });
    
    // Download
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `historical_data_${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
}

// ===== DRC Calculation Functions =====

// Global DRC settings
let currentDrcSettings = null;
let currentMeasurementBatchId = null;
let drcHoldTimer = null;
let isDrcHeld = false;

// Get next batch ID
function getNextBatchId() {
    socket.emit('get_drc_settings', {});
}

// Save DRC Settings
function saveDrcSettings() {
    const s21LowDb = parseFloat(document.getElementById('s21LowDb').value);
    const drc1Percent = parseFloat(document.getElementById('drc1Percent').value);
    const s21HighDb = parseFloat(document.getElementById('s21HighDb').value);
    const drc2Percent = parseFloat(document.getElementById('drc2Percent').value);
    
    // Validation
    if (isNaN(s21LowDb) || isNaN(drc1Percent) || isNaN(s21HighDb) || isNaN(drc2Percent)) {
        showNotification('Please fill in all DRC settings with valid numbers', 'error');
        return;
    }
    
    if (s21HighDb === s21LowDb) {
        showNotification('S21 High dB must be different from S21 Low dB', 'error');
        return;
    }
    
    if (drc1Percent < 0 || drc1Percent > 100 || drc2Percent < 0 || drc2Percent > 100) {
        showNotification('DRC percentages must be between 0 and 100', 'error');
        return;
    }
    
    // Send to server (batch_id will be auto-generated)
    socket.emit('save_drc_settings', {
        s21_low_db: s21LowDb,
        drc1_percent: drc1Percent,
        s21_high_db: s21HighDb,
        drc2_percent: drc2Percent
    });
}

// Load DRC Settings
function loadDrcSettings() {
    socket.emit('get_drc_settings', {});
}

// Calculate and Update DRC Display
function updateDrcDisplay(s21RmsDb) {
    if (!currentDrcSettings) {
        document.getElementById('drcResultCard').style.display = 'none';
        return;
    }
    
    const { slope_m, intercept_b, drc1_percent, drc2_percent } = currentDrcSettings;
    
    // Calculate DRC
    let drcPercent = slope_m * s21RmsDb + intercept_b;
    
    // Clamp to valid range
    const minDrc = Math.min(drc1_percent, drc2_percent);
    const maxDrc = Math.max(drc1_percent, drc2_percent);
    drcPercent = Math.max(minDrc, Math.min(maxDrc, drcPercent));
    
    // Use measurement batch_id if available, otherwise use calibration batch_id
    const displayBatchId = currentMeasurementBatchId || currentDrcSettings.batch_id || 'N/A';
    
    // Update display in stat-card format
    document.getElementById('drcResultCard').style.display = 'block';
    document.getElementById('drcBatchIdDisplay').textContent = `Batch: ${displayBatchId}`;
    document.getElementById('drcValueDisplay').textContent = `${drcPercent.toFixed(2)}%`;
    document.getElementById('drcFormulaDisplay').textContent = 
        `DRC% = ${slope_m.toFixed(2)} × S21 + ${intercept_b.toFixed(0)}`;
}

// Socket event handlers for DRC
socket.on('drc_save_result', (result) => {
    if (result.success) {
        showNotification(result.message, 'success');
        
        // Store complete settings
        currentDrcSettings = {
            batch_id: result.batch_id,
            s21_low_db: result.s21_low_db,
            drc1_percent: result.drc1_percent,
            s21_high_db: result.s21_high_db,
            drc2_percent: result.drc2_percent,
            slope_m: result.slope_m,
            intercept_b: result.intercept_b
        };
        
        // Immediately update DRC display with new batch ID
        const s21RmsElement = document.getElementById('s21AvgDb');
        if (s21RmsElement && s21RmsElement.textContent !== '--') {
            const s21Rms = parseFloat(s21RmsElement.textContent);
            updateDrcDisplay(s21Rms);
        }
    } else {
        showNotification(result.message, 'error');
    }
});

socket.on('drc_settings_result', (result) => {
    if (result.success) {
        const settings = result.settings;
        currentDrcSettings = settings;
        
        // Update form fields with null checks
        const drcBatchId = document.getElementById('drcBatchId');
        const s21LowDb = document.getElementById('s21LowDb');
        const drc1Percent = document.getElementById('drc1Percent');
        const s21HighDb = document.getElementById('s21HighDb');
        const drc2Percent = document.getElementById('drc2Percent');
        const drcNextBatchId = document.getElementById('drcNextBatchId');
        
        if (drcBatchId) drcBatchId.value = settings.batch_id;
        if (s21LowDb) s21LowDb.value = settings.s21_low_db;
        if (drc1Percent) drc1Percent.value = settings.drc1_percent;
        if (s21HighDb) s21HighDb.value = settings.s21_high_db;
        if (drc2Percent) drc2Percent.value = settings.drc2_percent;
        
        showNotification(`Loaded settings for ${settings.batch_id}`, 'success');
        
        // Update "Next Batch ID" display (timestamp format)
        if (drcNextBatchId) drcNextBatchId.textContent = 'Auto-generated on save';
        
        // Update DRC display with current S21 RMS if available
        const s21RmsElement = document.getElementById('s21AvgDb');
        if (s21RmsElement && s21RmsElement.textContent !== '--') {
            const s21Rms = parseFloat(s21RmsElement.textContent);
            updateDrcDisplay(s21Rms);
        }
    } else {
        // No settings found
        document.getElementById('drcNextBatchId').textContent = 'Auto-generated on save';
        showNotification('No previous settings. Ready for first batch.', 'info');
    }
});

// Event listeners for DRC buttons
document.getElementById('saveDrcSettingsBtn')?.addEventListener('click', saveDrcSettings);
document.getElementById('loadDrcSettingsBtn')?.addEventListener('click', loadDrcSettings);

// Event listener for Apply Batch Info button
document.getElementById('applyManualBatchBtn')?.addEventListener('click', function() {
    const slipNo = document.getElementById('slipNoInput').value.trim();
    const samplingNo = document.getElementById('samplingNoInput').value.trim();
    
    if (slipNo && samplingNo) {
        showNotification(`Batch Info Applied: ${slipNo}/${samplingNo}`, 'success');
        
        // Update DRC display with batch info
        document.getElementById('drcBatchIdDisplay').textContent = `Batch: ${slipNo}/${samplingNo}`;
        
        // If there's current S21 data, update DRC display
        const s21RmsElement = document.getElementById('avgS21');
        if (s21RmsElement && s21RmsElement.textContent !== '--') {
            const s21Rms = parseFloat(s21RmsElement.textContent);
            if (!isNaN(s21Rms)) {
                updateDrcDisplay(s21Rms);
            }
        }
    } else {
        // Show warning if fields are empty
        if (!slipNo && !samplingNo) {
            showNotification('Please enter both Slip No. and Sampling No.', 'warning');
        } else if (!slipNo) {
            showNotification('Please enter Slip No.', 'warning');
            document.getElementById('slipNoInput').focus();
        } else {
            showNotification('Please enter Sampling No.', 'warning');
            document.getElementById('samplingNoInput').focus();
        }
    }
});

// Event listener for Train Model button
document.getElementById('trainModelBtn')?.addEventListener('click', function() {
    console.log('Train Model button clicked');
    const selectedModel = document.getElementById('drcModelSelect').value;
    console.log('Selected model:', selectedModel);
    console.log('Dataset records count:', datasetRecords.length);
    
    // Check if we have dataset
    if (datasetRecords.length === 0) {
        console.warn('No dataset records available');
        showNotification('No training data available. Please generate sample data first in Analysis page.', 'warning');
        switchPage('analysis');
        return;
    }
    
    // Count valid records (must have both s21_avg and drc_evaluate)
    const validRecords = datasetRecords.filter(r => 
        r.s21_avg && r.drc_evaluate && 
        !isNaN(parseFloat(r.s21_avg)) && !isNaN(parseFloat(r.drc_evaluate))
    );
    
    console.log('Valid records for training:', validRecords.length);
    console.log('Sample record:', validRecords[0]);
    
    if (validRecords.length < 2) {
        showNotification(`Need at least 2 complete records for training. Found ${validRecords.length}. Please add more data in Analysis page.`, 'error');
        switchPage('analysis');
        return;
    }
    
    // Generate model name
    const timestamp = new Date().toISOString().slice(0,19).replace(/[-:T]/g, '');
    const modelName = `${selectedModel}_${timestamp}`;
    
    console.log('Training model:', modelName);
    showNotification(`Training ${selectedModel} model with ${validRecords.length} records...`, 'info');
    
    // Send training request
    socket.emit('train_model', {
        model_type: selectedModel,
        model_name: modelName,
        dataset: validRecords
    });
    console.log('Training request sent');
});

// Auto-load DRC settings on page load to get next batch ID
setTimeout(() => {
    loadDrcSettings();
}, 1000);

// ===== Dataset Preparation Functions =====
let datasetRecords = [];

// Load dataset from database
// ==================== Batch Data Management for Analysis ====================

let batchDataRecords = [];
let batchDataRecordsOriginal = []; // Store original unfiltered data
let selectedBatches = new Set();

// Apply load mode filter and render
function applyLoadModeFilterAndRender() {
    batchDataRecords = applyLoadModeFilter(batchDataRecordsOriginal);
    renderBatchDataTable();
    updateBatchStatistics();
    
    const loadMode = document.querySelector('input[name="batchLoadMode"]:checked')?.value || 'all';
    const modeText = loadMode === 'complete' ? 'Complete records' : 
                     loadMode === 'incomplete' ? 'Incomplete records' : 'All records';
    showNotification(`Showing ${batchDataRecords.length} ${modeText.toLowerCase()}`, 'info');
}

// Initialize batch load mode change listener
function initBatchModeListener() {
    const modeRadios = document.querySelectorAll('input[name="batchLoadMode"]');
    if (modeRadios.length > 0) {
        modeRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                if (batchDataRecordsOriginal.length > 0) {
                    applyLoadModeFilterAndRender();
                }
            });
        });
    }
}

// Search batch data by Slip No. and Sampling No.
function searchBatchData() {
    const slipNo = document.getElementById('searchSlipNo').value.trim();
    const samplingNo = document.getElementById('searchSamplingNo').value.trim();
    
    if (!slipNo && !samplingNo) {
        showNotification('Please enter Slip No. or Sampling No. to search', 'warning');
        return;
    }
    
    const loadMode = document.querySelector('input[name="batchLoadMode"]:checked')?.value || 'all';
    
    socket.emit('search_batch_data', {
        slip_no: slipNo,
        sampling_no: samplingNo,
        mode: loadMode
    });
    
    showNotification('Searching...', 'info');
}

// Load all batch data
function loadAllBatchData() {
    const loadMode = document.querySelector('input[name="batchLoadMode"]:checked')?.value || 'all';
    
    socket.emit('load_all_batch_data', { 
        limit: 200,
        mode: loadMode
    });
    showNotification('Loading all batches...', 'info');
}

// Handle batch search result
socket.on('batch_search_result', function(data) {
    if (data.success) {
        batchDataRecordsOriginal = data.data; // Store original
        batchDataRecords = applyLoadModeFilter(data.data);
        renderBatchDataTable();
        updateBatchStatistics();
        showNotification(`Found ${batchDataRecords.length} records`, 'success');
    } else {
        showNotification(data.message || 'Search failed', 'error');
    }
});

// Handle batch load result
socket.on('batch_load_result', function(data) {
    if (data.success) {
        batchDataRecordsOriginal = data.data; // Store original
        batchDataRecords = applyLoadModeFilter(data.data);
        renderBatchDataTable();
        updateBatchStatistics();
        showNotification(`Loaded ${batchDataRecords.length} records`, 'success');
    } else {
        showNotification(data.message || 'Load failed', 'error');
    }
});

// Apply load mode filter to data
function applyLoadModeFilter(data) {
    const loadMode = document.querySelector('input[name="batchLoadMode"]:checked')?.value || 'all';
    
    if (loadMode === 'complete') {
        return data.filter(record => record.is_complete);
    } else if (loadMode === 'incomplete') {
        return data.filter(record => !record.is_complete);
    } else {
        return data; // all
    }
}

// Render batch data table
function renderBatchDataTable() {
    const tbody = document.getElementById('datasetTableBody');
    
    if (batchDataRecords.length === 0) {
        tbody.innerHTML = `
            <tr class="no-data">
                <td colspan="11" style="text-align: center; padding: 40px; color: #9ca3af;">
                    No data loaded. Use search or "Load All Batches" to start.
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = batchDataRecords.map((record, index) => {
        const isComplete = record.is_complete;
        const statusClass = isComplete ? 'complete' : 'incomplete';
        const statusText = isComplete ? '✓ Complete' : '✗ Incomplete';
        const statusColor = isComplete ? '#10b981' : '#f59e0b';
        
        const drcDisplay = record.drc_percent != null ? record.drc_percent.toFixed(1) : '--';
        const s21Display = record.s21_avg != null ? record.s21_avg.toFixed(2) : '--';
        
        return `
            <tr data-index="${index}" ${!isComplete ? 'style="background: #fef3c7;"' : ''}>
                <td>
                    <input type="checkbox" class="batch-checkbox" data-index="${index}"
                           ${selectedBatches.has(index) ? 'checked' : ''}
                           onchange="toggleBatchSelection(${index}, this.checked)">
                </td>
                <td>${record.slip_no || '--'}</td>
                <td>${record.sampling_no || '--'}</td>
                <td>${record.test_no || '--'}</td>
                <td>${record.weight_gross != null ? record.weight_gross.toFixed(2) : '--'}</td>
                <td>${record.weight_net != null ? record.weight_net.toFixed(2) : '--'}</td>
                <td>${record.factor != null ? record.factor.toFixed(2) : '--'}</td>
                <td><strong>${drcDisplay}</strong></td>
                <td>${s21Display}</td>
                <td style="font-size: 0.85em;">${new Date(record.timestamp).toLocaleString()}</td>
                <td style="color: ${statusColor}; font-weight: 600; font-size: 0.85em;">${statusText}</td>
            </tr>
        `;
    }).join('');
}

// Toggle batch selection
function toggleBatchSelection(index, checked) {
    if (checked) {
        selectedBatches.add(index);
        
        // Auto-fill input fields with first selected batch data
        if (selectedBatches.size === 1) {
            const record = batchDataRecords[index];
            document.getElementById('inputWeightGross').value = record.weight_gross || '';
            document.getElementById('inputWeightNet').value = record.weight_net || '';
            document.getElementById('inputFactor').value = record.factor || '';
        }
    } else {
        selectedBatches.delete(index);
        
        // Clear input fields if no selection
        if (selectedBatches.size === 0) {
            document.getElementById('inputWeightGross').value = '';
            document.getElementById('inputWeightNet').value = '';
            document.getElementById('inputFactor').value = '';
        }
    }
}

// Toggle select all batches
function toggleSelectAll(checkbox) {
    const checkboxes = document.querySelectorAll('.batch-checkbox');
    selectedBatches.clear();
    
    checkboxes.forEach((cb, index) => {
        cb.checked = checkbox.checked;
        if (checkbox.checked) {
            selectedBatches.add(index);
        }
    });
    
    // Auto-fill with first record if selecting all
    if (checkbox.checked && batchDataRecords.length > 0) {
        const first = batchDataRecords[0];
        document.getElementById('inputWeightGross').value = first.weight_gross || '';
        document.getElementById('inputWeightNet').value = first.weight_net || '';
        document.getElementById('inputFactor').value = first.factor || '';
    } else {
        document.getElementById('inputWeightGross').value = '';
        document.getElementById('inputWeightNet').value = '';
        document.getElementById('inputFactor').value = '';
    }
}

// Update batch data
function updateBatchData() {
    if (selectedBatches.size === 0) {
        showNotification('Please select at least one batch to update', 'warning');
        return;
    }
    
    const weightGross = parseFloat(document.getElementById('inputWeightGross').value);
    const weightNet = parseFloat(document.getElementById('inputWeightNet').value);
    const factor = parseFloat(document.getElementById('inputFactor').value);
    
    if (!weightGross || !weightNet || !factor) {
        showNotification('Please fill all weight fields (Weight-Gross, Weight-Net, Factor)', 'warning');
        return;
    }
    
    // Calculate DRC
    const calculatedDrc = ((weightNet * factor) / weightGross * 100).toFixed(1);
    
    // Get unique batches (slip_no + sampling_no combinations)
    const uniqueBatches = new Set();
    const batchesToUpdate = [];
    
    selectedBatches.forEach(index => {
        const record = batchDataRecords[index];
        const batchKey = `${record.slip_no}_${record.sampling_no}`;
        if (!uniqueBatches.has(batchKey)) {
            uniqueBatches.add(batchKey);
            batchesToUpdate.push({
                slip_no: record.slip_no,
                sampling_no: record.sampling_no
            });
        }
    });
    
    // Update each unique batch
    let completed = 0;
    const total = batchesToUpdate.length;
    
    document.getElementById('updateStatus').textContent = `Updating ${total} batch(es)...`;
    
    batchesToUpdate.forEach((batch, index) => {
        socket.emit('update_batch_data', {
            slip_no: batch.slip_no,
            sampling_no: batch.sampling_no,
            weight_gross: weightGross,
            weight_net: weightNet,
            factor: factor
        });
    });
}

// Handle batch update result
socket.on('batch_update_result', function(data) {
    if (data.success) {
        showNotification(data.message, 'success');
        
        // Refresh data after update
        setTimeout(() => {
            if (document.getElementById('searchSlipNo').value || document.getElementById('searchSamplingNo').value) {
                searchBatchData();
            } else {
                loadAllBatchData();
            }
        }, 500);
        
        // Clear selections
        selectedBatches.clear();
        document.getElementById('selectAllBatches').checked = false;
        document.getElementById('updateStatus').textContent = '';
    } else {
        showNotification(data.message || 'Update failed', 'error');
        document.getElementById('updateStatus').textContent = 'Update failed';
    }
});

// Update batch statistics
function updateBatchStatistics() {
    const total = batchDataRecords.length;
    const complete = batchDataRecords.filter(r => r.is_complete).length;
    const incomplete = total - complete;
    
    // Calculate average DRC for complete records
    const completeRecords = batchDataRecords.filter(r => r.is_complete && r.drc_percent != null);
    const avgDrc = completeRecords.length > 0
        ? (completeRecords.reduce((sum, r) => sum + r.drc_percent, 0) / completeRecords.length).toFixed(1)
        : '--';
    
    document.getElementById('datasetTotalRecords').textContent = total;
    document.getElementById('datasetCompleteRecords').textContent = complete;
    document.getElementById('datasetIncompleteRecords').textContent = incomplete;
    document.getElementById('datasetAvgDrc').textContent = avgDrc === '--' ? avgDrc : avgDrc + '%';
}

// Export batch dataset to CSV
function exportBatchDataset() {
    if (batchDataRecords.length === 0) {
        showNotification('No data to export', 'warning');
        return;
    }
    
    // Create CSV content
    const headers = ['Slip No.', 'Sampling No.', 'Test No.', 'Weight-Gross (g)', 'Weight-Net (g)', 'Factor', 'DRC (%)', 'S21 Avg (dB)', 'Timestamp', 'Status'];
    const csvRows = [headers.join(',')];
    
    batchDataRecords.forEach(row => {
        const values = [
            row.slip_no || '',
            row.sampling_no || '',
            row.test_no || '',
            row.weight_gross != null ? row.weight_gross.toFixed(2) : '',
            row.weight_net != null ? row.weight_net.toFixed(2) : '',
            row.factor != null ? row.factor.toFixed(2) : '',
            row.drc_percent != null ? row.drc_percent.toFixed(1) : '',
            row.s21_avg != null ? row.s21_avg.toFixed(2) : '',
            row.timestamp || '',
            row.is_complete ? 'Complete' : 'Incomplete'
        ];
        csvRows.push(values.join(','));
    });
    
    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `batch_dataset_${new Date().toISOString().slice(0,10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    showNotification('Dataset exported successfully', 'success');
}

// ==================== Old Dataset Management (Deprecated) ====================

function loadDatasetFromDB() {
    // Get selected load mode
    const loadMode = document.querySelector('input[name="loadMode"]:checked').value;
    
    document.getElementById('datasetStatus').textContent = 'Loading...';
    socket.emit('load_dataset', { mode: loadMode });
}

// Export dataset to CSV
function exportDataset() {
    if (datasetRecords.length === 0) {
        showNotification('No data to export', 'warning');
        return;
    }
    
    // Create CSV content
    const headers = ['Batch ID', 'Weight-Gross', 'Weight-Net', 'Factor', 'DRC-Evaluate', 'DRC-Calculate', 'S21 Avg', 'Timestamp'];
    const csvRows = [headers.join(',')];
    
    datasetRecords.forEach(row => {
        const values = [
            row.batch_id || '',
            row.weight_gross || '',
            row.weight_net || '',
            row.factor || '',
            row.drc_evaluate || '',
            row.drc_calculate || '',
            row.s21_avg || '',
            row.timestamp || ''
        ];
        csvRows.push(values.join(','));
    });
    
    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `dataset_${new Date().toISOString().slice(0,10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    showNotification('Dataset exported successfully', 'success');
}

// Add new empty row to dataset
function addDatasetRow() {
    const newRow = {
        id: Date.now(),
        slip_no: '',
        sampling_no: '',
        weight_gross: '',
        weight_net: '',
        factor: '',
        drc_percent: '',
        s21_avg: '',
        timestamp: new Date().toISOString()
    };
    datasetRecords.push(newRow);
    renderDatasetTable();
    updateDatasetStats();
}

// Generate sample data for testing
function generateSampleData() {
    const sampleCount = 8;
    const baseDate = new Date();
    
    const samples = [
        { batchSuffix: '00057', wGross: 18.78, wNet: 16.91, factor: 0.72, drcEval: 64.8, s21: -31.5 },
        { batchSuffix: '00054', wGross: 18.71, wNet: 16.11, factor: 0.72, drcEval: 62.0, s21: -33.2 },
        { batchSuffix: '00059', wGross: 19.28, wNet: 17.75, factor: 0.72, drcEval: 66.3, s21: -29.8 },
        { batchSuffix: '00058', wGross: 18.93, wNet: 17.20, factor: 0.72, drcEval: 65.4, s21: -30.9 },
        { batchSuffix: '00097', wGross: 19.51, wNet: 17.28, factor: 0.72, drcEval: 63.8, s21: -32.4 },
        { batchSuffix: '00029', wGross: 20.00, wNet: 16.24, factor: 0.72, drcEval: 58.5, s21: -36.8 },
        { batchSuffix: '00045', wGross: 20.00, wNet: 16.68, factor: 0.72, drcEval: 60.0, s21: -35.0 },
        { batchSuffix: '00099', wGross: 19.89, wNet: 17.84, factor: 0.72, drcEval: 64.6, s21: -31.2 }
    ];
    
    const newRecords = samples.map((sample, index) => {
        const timestamp = new Date(baseDate.getTime() - (sampleCount - index) * 3600000);
        const drcCalc = (sample.drcEval * 0.98 + Math.random() * 2).toFixed(2);
        
        return {
            id: Date.now() + index,
            batch_id: `26KBI${sample.batchSuffix}`,
            weight_gross: sample.wGross.toFixed(2),
            weight_net: sample.wNet.toFixed(2),
            factor: sample.factor.toFixed(2),
            drc_evaluate: sample.drcEval.toFixed(1),
            drc_calculate: drcCalc,
            s21_avg: sample.s21.toFixed(2),
            timestamp: timestamp.toISOString()
        };
    });
    
    datasetRecords = [...datasetRecords, ...newRecords];
    renderDatasetTable();
    updateDatasetStats();
    showNotification(`Generated ${sampleCount} sample records`, 'success');
}

// Save single record to database (using batch_weights table)
function saveSingleRecord(id) {
    const row = datasetRecords.find(r => r.id === id);
    if (!row) {
        showNotification('Record not found', 'error');
        return;
    }
    
    if (!row.slip_no || !row.sampling_no) {
        showNotification('Slip No. and Sampling No. are required', 'warning');
        return;
    }
    
    // Validate weight data
    if (!row.weight_gross && !row.weight_net && !row.factor) {
        showNotification('Please enter at least one weight field', 'warning');
        return;
    }
    
    // Visual feedback
    const rowElement = document.getElementById(`row-${id}`);
    if (rowElement) {
        rowElement.style.backgroundColor = '#fef3c7';
    }
    
    // Use batch_update to save to batch_weights table
    socket.emit('batch_update', {
        slip_no: row.slip_no,
        sampling_no: row.sampling_no,
        weight_gross: row.weight_gross ? parseFloat(row.weight_gross) : null,
        weight_net: row.weight_net ? parseFloat(row.weight_net) : null,
        factor: row.factor ? parseFloat(row.factor) : null
    });
}

// Remove row from dataset
function removeDatasetRow(id) {
    datasetRecords = datasetRecords.filter(r => r.id !== id);
    renderDatasetTable();
    updateDatasetStats();
}

// Update dataset row
function updateDatasetRow(id, field, value) {
    const row = datasetRecords.find(r => r.id === id);
    if (row) {
        row[field] = value;
        updateDatasetStats();
    }
}

// Render dataset table
function renderDatasetTable() {
    const tbody = document.getElementById('datasetTableBody');
    
    if (datasetRecords.length === 0) {
        tbody.innerHTML = `
            <tr class="no-data">
                <td colspan="10" style="text-align: center; padding: 40px; color: #9ca3af;">
                    No data loaded. Click "Load from Database" or "Add Row" to start.
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = datasetRecords.map((row, index) => {
        const drcValue = row.drc_percent || (row.weight_gross && row.weight_net && row.factor ? 
            ((parseFloat(row.weight_net) * parseFloat(row.factor)) / parseFloat(row.weight_gross) * 100).toFixed(1) : '--');
        
        return `
        <tr id="row-${row.id}">
            <td>${index + 1}</td>
            <td><input type="text" class="dataset-input" value="${row.slip_no || ''}" 
                onchange="updateDatasetRow(${row.id}, 'slip_no', this.value)" placeholder="Slip No." /></td>
            <td><input type="text" class="dataset-input" value="${row.sampling_no || ''}" 
                onchange="updateDatasetRow(${row.id}, 'sampling_no', this.value)" placeholder="Sampling No." /></td>
            <td><input type="number" class="dataset-input" step="0.01" value="${row.weight_gross || ''}" 
                onchange="updateDatasetRow(${row.id}, 'weight_gross', this.value)" /></td>
            <td><input type="number" class="dataset-input" step="0.01" value="${row.weight_net || ''}" 
                onchange="updateDatasetRow(${row.id}, 'weight_net', this.value)" /></td>
            <td><input type="number" class="dataset-input" step="0.01" value="${row.factor || ''}" 
                onchange="updateDatasetRow(${row.id}, 'factor', this.value)" /></td>
            <td style="background: #f3f4f6; font-weight: 600;">${drcValue}</td>
            <td><input type="number" class="dataset-input" step="0.01" value="${row.s21_avg || ''}" readonly 
                style="background: #f9fafb;" /></td>
            <td style="font-size: 0.75em;">${row.timestamp ? new Date(row.timestamp).toLocaleString() : '--'}</td>
            <td>
                <button class="btn btn-success btn-sm" onclick="saveSingleRecord(${row.id})" title="Save" style="margin-right: 5px;">💾</button>
                <button class="btn btn-danger btn-sm" onclick="removeDatasetRow(${row.id})" title="Delete">🗑️</button>
            </td>
        </tr>
        `;
    }).join('');
}

// Update dataset statistics
function updateDatasetStats() {
    const total = datasetRecords.length;
    const complete = datasetRecords.filter(r => 
        r.slip_no && r.sampling_no && r.weight_gross && r.weight_net && 
        r.factor && r.s21_avg
    ).length;
    
    const drcValues = datasetRecords
        .map(r => {
            if (r.drc_percent) return parseFloat(r.drc_percent);
            if (r.weight_gross && r.weight_net && r.factor) {
                return (parseFloat(r.weight_net) * parseFloat(r.factor)) / parseFloat(r.weight_gross) * 100;
            }
            return NaN;
        })
        .filter(v => !isNaN(v));
    const avgDrc = drcValues.length > 0 
        ? (drcValues.reduce((a, b) => a + b, 0) / drcValues.length).toFixed(2)
        : '--';
    
    const s21Values = datasetRecords
        .map(r => parseFloat(r.s21_avg))
        .filter(v => !isNaN(v));
    const avgS21 = s21Values.length > 0 
        ? (s21Values.reduce((a, b) => a + b, 0) / s21Values.length).toFixed(2)
        : '--';
    
    document.getElementById('datasetTotalRecords').textContent = total;
    document.getElementById('datasetCompleteRecords').textContent = complete;
    document.getElementById('datasetAvgDrcEval').textContent = avgDrc !== '--' ? avgDrc + '%' : avgDrc;
    document.getElementById('datasetAvgS21').textContent = avgS21 !== '--' ? avgS21 + ' dB' : avgS21;
}

// Clear all dataset
function clearDataset() {
    if (confirm('Are you sure you want to clear all dataset records?')) {
        datasetRecords = [];
        renderDatasetTable();
        updateDatasetStats();
        showNotification('Dataset cleared', 'info');
    }
}

// Save dataset
function saveDataset() {
    if (datasetRecords.length === 0) {
        showNotification('No data to save', 'warning');
        return;
    }
    
    document.getElementById('datasetStatus').textContent = 'Saving...';
    socket.emit('save_dataset', { records: datasetRecords });
}

// Socket event handlers for dataset
socket.on('dataset_loaded', (data) => {
    if (data.success) {
        const loadMode = data.mode || 'all';
        
        datasetRecords = data.records.map(r => ({
            id: Date.now() + Math.random(),
            slip_no: r.slip_no || '',
            sampling_no: r.sampling_no || '',
            weight_gross: r.weight_gross || '',
            weight_net: r.weight_net || '',
            factor: r.factor || '',
            drc_percent: r.drc_percent || '',
            s21_avg: r.s21_avg || '',
            timestamp: r.timestamp || new Date().toISOString()
        }));
        renderDatasetTable();
        updateDatasetStats();
        
        let statusMsg = `Loaded ${datasetRecords.length} records`;
        if (loadMode === 'complete') {
            statusMsg += ' (complete only)';
        } else if (loadMode === 'for_input') {
            statusMsg += ' (for input)';
        }
        
        document.getElementById('datasetStatus').textContent = statusMsg;
        showNotification(statusMsg, 'success');
    } else {
        document.getElementById('datasetStatus').textContent = 'Load failed';
        showNotification(data.message || 'Failed to load dataset', 'error');
    }
});

socket.on('dataset_saved', (data) => {
    if (data.success) {
        document.getElementById('datasetStatus').textContent = 'Saved successfully';
        showNotification(data.message || 'Dataset saved successfully', 'success');
    } else {
        document.getElementById('datasetStatus').textContent = 'Save failed';
        showNotification(data.message || 'Failed to save dataset', 'error');
    }
});

socket.on('record_save_result', (data) => {
    if (data.success) {
        showNotification(`Saved: ${data.batch_id || 'Record'}`, 'success');
        
        // Update DRC calculate if returned
        if (data.drc_calculate) {
            const row = datasetRecords.find(r => r.batch_id === data.batch_id);
            if (row) {
                row.drc_percent = data.drc_calculate;
                renderDatasetTable();
            }
        }
        
        // Remove highlight
        setTimeout(() => {
            const rows = document.querySelectorAll('tr[id^="row-"]');
            rows.forEach(r => r.style.backgroundColor = '');
        }, 500);
    } else {
        showNotification(data.message || 'Save failed', 'error');
    }
});

// Handle batch_update_result from Analysis page saves
socket.on('batch_update_result', (data) => {
    if (data.success) {
        showNotification(data.message || 'Saved successfully', 'success');
        
        // Update DRC if returned
        if (data.drc_percent) {
            // Find and update the row
            const rows = document.querySelectorAll('tr[id^="row-"]');
            rows.forEach(rowEl => {
                const inputs = rowEl.querySelectorAll('input');
                if (inputs.length >= 2) {
                    // Check if this row has matching slip_no and sampling_no (would need to track this better)
                    renderDatasetTable();
                }
            });
        }
        
        // Remove highlight
        setTimeout(() => {
            const rows = document.querySelectorAll('tr[id^="row-"]');
            rows.forEach(r => r.style.backgroundColor = '');
        }, 500);
    } else {
        showNotification(data.message || 'Save failed', 'error');
        // Remove highlight on error too
        setTimeout(() => {
            const rows = document.querySelectorAll('tr[id^="row-"]');
            rows.forEach(r => r.style.backgroundColor = '');
        }, 500);
    }
});

// Event listeners for dataset buttons
document.getElementById('loadDatasetBtn')?.addEventListener('click', loadDatasetFromDB);
document.getElementById('addDatasetRowBtn')?.addEventListener('click', addDatasetRow);
document.getElementById('generateSampleBtn')?.addEventListener('click', generateSampleData);
document.getElementById('clearDatasetBtn')?.addEventListener('click', clearDataset);
document.getElementById('saveDatasetBtn')?.addEventListener('click', saveDataset);
document.getElementById('exportDatasetBtn')?.addEventListener('click', exportDataset);

// Reset Scan UI
function resetScanUI() {
    document.getElementById('scanProgressSection').style.display = 'none';
    document.getElementById('startScanBtn').disabled = false;
    scanCollectedData = [];
}

// Data View functions
let detailChartInstance = null;

function queryDataView() {
    const startDate = document.getElementById('dataViewStartDate').value;
    const endDate = document.getElementById('dataViewEndDate').value;
    const limit = document.getElementById('dataViewLimitRecords').value;
    
    const loadingMsg = document.getElementById('dataViewLoadingMsg');
    const errorMsg = document.getElementById('dataViewErrorMsg');
    const queryBtn = document.getElementById('queryDataViewBtn');
    
    loadingMsg.style.display = 'block';
    errorMsg.style.display = 'none';
    queryBtn.disabled = true;
    queryBtn.textContent = '⏳ Loading...';
    
    socket.emit('query_data_view', {
        start_date: startDate || null,
        end_date: endDate || null,
        limit: parseInt(limit)
    });
}

socket.on('data_view_result', (result) => {
    const loadingMsg = document.getElementById('dataViewLoadingMsg');
    const errorMsg = document.getElementById('dataViewErrorMsg');
    const queryBtn = document.getElementById('queryDataViewBtn');
    const recordCount = document.getElementById('dataViewRecordCount');
    const tableBody = document.getElementById('dataViewTableBody');
    
    loadingMsg.style.display = 'none';
    queryBtn.disabled = false;
    queryBtn.textContent = '🔍 Query Saved Data';
    
    if (result.success) {
        recordCount.textContent = `${result.count} records`;
        
        if (result.data && result.data.length > 0) {
            tableBody.innerHTML = '';
            result.data.forEach(row => {
                const tr = document.createElement('tr');
                const timestamp = new Date(row.timestamp).toLocaleString();
                const drcDisplay = row.drc_percent !== null ? row.drc_percent + '%' : '--';
                
                tr.innerHTML = `
                    <td>${timestamp}</td>
                    <td>${row.batch_id}</td>
                    <td>${drcDisplay}</td>
                    <td>${row.s11_rms}</td>
                    <td>${row.s21_rms}</td>
                    <td>${row.signal_quality}%</td>
                    <td>
                        <button class="btn-small btn-view" onclick="viewMeasurementDetails('${row.timestamp}')" title="View 101 Points">👁️ View</button>
                    </td>
                `;
                tableBody.appendChild(tr);
            });
        } else {
            tableBody.innerHTML = '<tr><td colspan="7" class="no-data">No records found for the selected criteria.</td></tr>';
        }
    } else {
        errorMsg.textContent = '❌ ' + result.message;
        errorMsg.style.display = 'block';
        recordCount.textContent = '0 records';
        tableBody.innerHTML = '<tr><td colspan="7" class="no-data">Query failed. Check database connection.</td></tr>';
    }
});

function viewMeasurementDetails(timestamp) {
    socket.emit('get_measurement_details', { timestamp: timestamp });
    document.getElementById('detailModal').style.display = 'flex';
}

socket.on('measurement_details_result', (result) => {
    if (result.success) {
        const titleText = `101-Point Data - Batch: ${result.batch_id}${result.drc_percent ? ` | DRC: ${result.drc_percent}%` : ''}`;
        document.getElementById('detailModalTitle').textContent = titleText;
        
        // Populate table
        const tableBody = document.getElementById('detailTableBody');
        tableBody.innerHTML = '';
        
        result.data.forEach((point, index) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${index + 1}</td>
                <td>${point.frequency}</td>
                <td>${point.s11_db}</td>
                <td>${point.s11_phase}</td>
                <td>${point.s21_db !== null ? point.s21_db : '--'}</td>
                <td>${point.s21_phase !== null ? point.s21_phase : '--'}</td>
            `;
            tableBody.appendChild(tr);
        });
        
        // Create chart
        const ctx = document.getElementById('detailChart').getContext('2d');
        
        if (detailChartInstance) {
            detailChartInstance.destroy();
        }
        
        detailChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: result.data.map(p => p.frequency.toFixed(4)),
                datasets: [
                    {
                        label: 'S11 (dB)',
                        data: result.data.map(p => p.s11_db),
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        borderWidth: 2,
                        pointRadius: 1
                    },
                    {
                        label: 'S21 (dB)',
                        data: result.data.map(p => p.s21_db),
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        borderWidth: 2,
                        pointRadius: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    title: {
                        display: true,
                        text: 'S11 and S21 vs Frequency'
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Frequency (GHz)'
                        },
                        ticks: {
                            maxTicksLimit: 10
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Magnitude (dB)'
                        }
                    }
                }
            }
        });
    } else {
        showNotification('Failed to load measurement details: ' + result.message, 'error');
    }
});

function closeDetailModal() {
    document.getElementById('detailModal').style.display = 'none';
    if (detailChartInstance) {
        detailChartInstance.destroy();
        detailChartInstance = null;
    }
}

// Reset Scan UI
function resetScanUI() {
    document.getElementById('scanProgressSection').style.display = 'none';
    document.getElementById('startScanBtn').disabled = false;
    scanCollectedData = [];
}

// ===== Models Management Functions =====
let currentModels = [];
let selectedModelForDetail = null;

// Load trained models
function loadTrainedModels() {
    console.log('Loading trained models...');
    socket.emit('get_trained_models', {});
}

// Render models grid
function renderModelsGrid(models) {
    const grid = document.getElementById('modelsGrid');
    
    if (!models || models.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 60px; color: #9ca3af;">
                <div style="font-size: 3em; margin-bottom: 15px;">🤖</div>
                <div style="font-size: 1.1em; margin-bottom: 10px;">No models found</div>
                <div style="font-size: 0.9em;">Train a model from the Analysis page to get started</div>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = models.map(model => {
        const typeClass = model.type.replace('_', '-');
        const isActive = model.is_active;
        const rSquared = model.r_squared || 0;
        const rmse = model.rmse || 0;
        const mae = model.mae || 0;
        
        let perfLevel = 'poor';
        if (rSquared >= 0.95) perfLevel = 'excellent';
        else if (rSquared >= 0.85) perfLevel = 'good';
        else if (rSquared >= 0.70) perfLevel = 'fair';
        
        const formula = model.parameters?.formula || 'N/A';
        const createdDate = new Date(model.created_at).toLocaleString();
        
        return `
            <div class="model-card ${isActive ? 'active-model' : 'inactive-model'}" data-model-id="${model.id}">
                <div class="performance-indicator ${perfLevel}"></div>
                
                <div class="model-card-header">
                    <div>
                        <div class="model-card-title">${model.name}</div>
                        <div class="model-card-meta">
                            <span class="model-badge ${typeClass}">${formatModelType(model.type)}</span>
                            <span class="model-badge ${isActive ? 'active' : 'inactive'}">${isActive ? '✓ Active' : '○ Inactive'}</span>
                        </div>
                    </div>
                </div>
                
                <div class="model-metrics-grid">
                    <div class="metric-item">
                        <div class="metric-label">R² Score</div>
                        <div class="metric-value" style="color: ${rSquared >= 0.85 ? '#10b981' : '#6b7280'}">
                            ${rSquared.toFixed(4)}
                        </div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">RMSE</div>
                        <div class="metric-value" style="color: ${rmse <= 2 ? '#10b981' : '#6b7280'}">
                            ${rmse.toFixed(4)}
                        </div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">MAE</div>
                        <div class="metric-value" style="color: ${mae <= 1.5 ? '#10b981' : '#6b7280'}">
                            ${mae.toFixed(4)}
                        </div>
                    </div>
                </div>
                
                <div style="margin: 10px 0;">
                    <div style="font-size: 0.75em; color: #6b7280; margin-bottom: 5px; font-weight: 600;">
                        Training Data: ${model.training_count} samples
                    </div>
                </div>
                
                <div class="model-formula">${formula}</div>
                
                <div style="font-size: 0.7em; color: #9ca3af; margin-top: 10px;">
                    Created: ${createdDate}
                </div>
                
                <div class="model-actions">
                    <button onclick="viewModelDetails('${model.name}')" style="background: #3b82f6; color: white;">📊 Details</button>
                    <button onclick="useModelForCalculation('${model.name}')" style="background: #10b981; color: white;">🔄 Use Model</button>
                    ${!isActive ? `<button onclick="activateModel('${model.name}')" style="background: #f59e0b; color: white;">✓ Activate</button>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

function formatModelType(type) {
    const types = {
        'linear_regression': 'Linear Regression',
        'polynomial': 'Polynomial Regression',
        'svr': 'Support Vector Regression',
        'random_forest': 'Random Forest'
    };
    return types[type] || type;
}

function viewModelDetails(modelName) {
    const model = currentModels.find(m => m.name === modelName);
    if (!model) return;
    
    selectedModelForDetail = model;
    
    document.getElementById('modalModelName').textContent = model.name;
    document.getElementById('modalModelType').textContent = formatModelType(model.type);
    document.getElementById('modalCreatedAt').textContent = new Date(model.created_at).toLocaleString();
    document.getElementById('modalTrainingCount').textContent = model.training_count;
    document.getElementById('modalRSquared').textContent = (model.r_squared || 0).toFixed(4);
    document.getElementById('modalRMSE').textContent = (model.rmse || 0).toFixed(4);
    document.getElementById('modalMAE').textContent = (model.mae || 0).toFixed(4);
    document.getElementById('modalParameters').textContent = JSON.stringify(model.parameters, null, 2);
    document.getElementById('modalFormula').textContent = model.parameters?.formula || 'N/A';
    document.getElementById('modalNotes').value = model.notes || '';
    
    document.getElementById('activateModelBtn').style.display = model.is_active ? 'none' : 'block';
    document.getElementById('deactivateModelBtn').style.display = model.is_active ? 'block' : 'none';
    
    document.getElementById('modelDetailModal').style.display = 'flex';
}

function closeModelDetailModal() {
    document.getElementById('modelDetailModal').style.display = 'none';
    selectedModelForDetail = null;
}

function useModelForCalculation(modelName) {
    const modelSelector = document.getElementById('drcCalculationModelSelect');
    if (modelSelector) {
        for (let i = 0; i < modelSelector.options.length; i++) {
            if (modelSelector.options[i].value === modelName) {
                modelSelector.selectedIndex = i;
                break;
            }
        }
        switchPage('dashboard');
        showNotification(`Model "${modelName}" selected for DRC calculation`, 'success');
    }
}

function activateModel(modelName) {
    socket.emit('activate_model', { model_name: modelName });
}

function deactivateModel(modelName) {
    socket.emit('deactivate_model', { model_name: modelName });
}

function deleteModel(modelName) {
    if (confirm(`Are you sure you want to delete the model "${modelName}"? This action cannot be undone.`)) {
        socket.emit('delete_model', { model_name: modelName });
    }
}

function saveModelNotes() {
    if (!selectedModelForDetail) return;
    socket.emit('update_model_notes', {
        model_name: selectedModelForDetail.name,
        notes: document.getElementById('modalNotes').value
    });
}

function filterAndSortModels() {
    const typeFilter = document.getElementById('modelTypeFilter')?.value || 'all';
    const statusFilter = document.getElementById('modelStatusFilter')?.value || 'all';
    const sortBy = document.getElementById('modelSortBy')?.value || 'created_desc';
    
    let filtered = [...currentModels];
    
    if (typeFilter !== 'all') {
        filtered = filtered.filter(m => m.type === typeFilter);
    }
    
    if (statusFilter === 'active') {
        filtered = filtered.filter(m => m.is_active);
    } else if (statusFilter === 'inactive') {
        filtered = filtered.filter(m => !m.is_active);
    }
    
    filtered.sort((a, b) => {
        switch (sortBy) {
            case 'created_desc': return new Date(b.created_at) - new Date(a.created_at);
            case 'created_asc': return new Date(a.created_at) - new Date(b.created_at);
            case 'r_squared_desc': return (b.r_squared || 0) - (a.r_squared || 0);
            case 'rmse_asc': return (a.rmse || 999) - (b.rmse || 999);
            case 'name_asc': return a.name.localeCompare(b.name);
            default: return 0;
        }
    });
    
    renderModelsGrid(filtered);
}

// Update models dropdown for DRC calculation
function updateModelsList(models) {
    const modelSelector = document.getElementById('drcCalculationModelSelect');
    if (modelSelector && models) {
        const currentValue = modelSelector.value;
        modelSelector.innerHTML = '<option value="">Use Default (Linear from Settings)</option>';
        
        models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.name;
            option.textContent = `${model.name} (${formatModelType(model.type)}, R²=${(model.r_squared || 0).toFixed(3)})`;
            if (model.is_active) {
                option.textContent += ' ★';
            }
            modelSelector.appendChild(option);
        });
        
        // Restore previous selection if it still exists
        if (currentValue) {
            for (let i = 0; i < modelSelector.options.length; i++) {
                if (modelSelector.options[i].value === currentValue) {
                    modelSelector.selectedIndex = i;
                    break;
                }
            }
        }
    }
}

// Handle model training result
socket.on('model_train_result', (result) => {
    if (result.success) {
        const model = result.model;
        showNotification(
            `✓ Model trained: ${model.name}\nR²: ${model.r_squared.toFixed(4)}, RMSE: ${model.rmse.toFixed(4)}`,
            'success'
        );
        
        // Refresh models list and switch to Models page
        loadTrainedModels();
        
        // Switch to Models page to see the new model
        setTimeout(() => {
            switchPage('models');
        }, 500);
    } else {
        showNotification(`Model training failed: ${result.message}`, 'error');
    }
});

socket.on('trained_models_result', (result) => {
    console.log('Received trained models result:', result);
    if (result.success) {
        currentModels = result.models || [];
        const count = currentModels.length;
        console.log(`Loaded ${count} models:`, currentModels);
        
        const modelsCountEl = document.getElementById('modelsCount');
        if (modelsCountEl) {
            modelsCountEl.textContent = count;
        }
        
        filterAndSortModels();
        updateModelsList(currentModels);
        updateActiveModelDisplay();
    } else {
        console.error('Failed to load models:', result.message);
        showNotification(`Failed to load models: ${result.message}`, 'error');
    }
});

socket.on('model_activated', (result) => {
    if (result.success) {
        showNotification(`Model "${result.model_name}" activated`, 'success');
        loadTrainedModels();
        updateActiveModelDisplay();
    } else {
        showNotification(`Failed to activate model: ${result.message}`, 'error');
    }
});

socket.on('model_deactivated', (result) => {
    if (result.success) {
        showNotification(`Model "${result.model_name}" deactivated`, 'success');
        loadTrainedModels();
        updateActiveModelDisplay();
    } else {
        showNotification(`Failed to deactivate model: ${result.message}`, 'error');
    }
});

socket.on('model_deleted', (result) => {
    if (result.success) {
        showNotification('Model deleted successfully', 'success');
        closeModelDetailModal();
        loadTrainedModels();
    } else {
        showNotification(`Failed to delete model: ${result.message}`, 'error');
    }
});

socket.on('model_notes_updated', (result) => {
    if (result.success) {
        showNotification('Model notes saved', 'success');
        loadTrainedModels();
    } else {
        showNotification(`Failed to save notes: ${result.message}`, 'error');
    }
});

document.getElementById('refreshModelsBtn')?.addEventListener('click', loadTrainedModels);

document.getElementById('modelTypeFilter')?.addEventListener('change', filterAndSortModels);
document.getElementById('modelStatusFilter')?.addEventListener('change', filterAndSortModels);
document.getElementById('modelSortBy')?.addEventListener('change', filterAndSortModels);

// Function to update active model status display on Dashboard
function updateActiveModelDisplay() {
    const activeModel = currentModels.find(m => m.is_active);
    
    const nameEl = document.getElementById('activeModelName');
    const typeEl = document.getElementById('activeModelType');
    const r2El = document.getElementById('activeModelR2');
    const rmseEl = document.getElementById('activeModelRMSE');
    
    if (activeModel) {
        nameEl.textContent = activeModel.name;
        nameEl.style.color = '#059669';
        typeEl.textContent = formatModelType(activeModel.type);
        r2El.textContent = `R²: ${activeModel.r_squared.toFixed(4)}`;
        rmseEl.textContent = `RMSE: ${activeModel.rmse.toFixed(4)}`;
    } else {
        nameEl.textContent = 'No model selected';
        nameEl.style.color = '#9ca3af';
        typeEl.textContent = '--';
        r2El.textContent = 'R²: --';
        rmseEl.textContent = 'RMSE: --';
    }
}

document.getElementById('saveModelNotesBtn')?.addEventListener('click', saveModelNotes);
document.getElementById('activateModelBtn')?.addEventListener('click', () => {
    if (selectedModelForDetail) activateModel(selectedModelForDetail.name);
});
document.getElementById('deactivateModelBtn')?.addEventListener('click', () => {
    if (selectedModelForDetail) deactivateModel(selectedModelForDetail.name);
});
document.getElementById('deleteModelBtn')?.addEventListener('click', () => {
    if (selectedModelForDetail) deleteModel(selectedModelForDetail.name);
});

setTimeout(() => {
    loadTrainedModels();
}, 2000);