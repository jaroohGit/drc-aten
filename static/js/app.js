// WebSocket connection
const socket = io();

// Chart instances
let dbChart = null;
let s21Chart = null;
let historicalChart = null;

// Current measurement data
let currentMeasurement = null;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
    setupEventListeners();
    setupWebSocket();
    setupSettingsPage();
    updateTime();
    setInterval(updateTime, 1000);
    
    // Request initial connection status
    socket.emit('get_connection_status');
    
    // Request initial config
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
    document.getElementById('startBtn').addEventListener('click', function() {
        socket.emit('start_sweep');
        this.disabled = true;
        document.getElementById('stopBtn').disabled = false;
    });

    document.getElementById('stopBtn').addEventListener('click', function() {
        socket.emit('stop_sweep');
        this.disabled = true;
        document.getElementById('startBtn').disabled = false;
    });
    
    // Analysis button
    document.getElementById('analyzeBtn').addEventListener('click', function() {
        analyzeHistoricalData();
    });
    
    // Save Data button
    document.getElementById('saveDataBtn').addEventListener('click', function() {
        saveCurrentMeasurement();
    });
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
    });

    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        updateConnectionStatus(false);
    });

    socket.on('config', function(data) {
        document.getElementById('configPort').textContent = data.port;
        document.getElementById('configFreq').textContent = 
            `${data.start_freq.toFixed(2)} - ${data.stop_freq.toFixed(2)} GHz`;
        document.getElementById('configPoints').textContent = data.points;
        document.getElementById('configInterval').textContent = `${data.interval} ms`;
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
            showNotification(data.message || 'Data saved successfully!', 'success');
            
            // Store measurement batch_id
            if (data.batch_id) {
                currentMeasurementBatchId = data.batch_id;
                
                // Update DRC display with new batch_id
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
    document.getElementById('sweepCount').textContent = data.sweep_count;
    document.getElementById('avgDb').textContent = data.summary.avg_db.toFixed(2);
    document.getElementById('maxDb').textContent = data.summary.max_db.toFixed(2);
    document.getElementById('minDb').textContent = data.summary.min_db.toFixed(2);
    
    // Find frequency at minimum S11
    const minS11Point = data.s11_data.find(d => d.db === data.summary.min_db);
    if (minS11Point) {
        const freqMHz = (minS11Point.frequency * 1000).toFixed(2);
        document.getElementById('minDbFreq').textContent = `@ ${freqMHz} MHz`;
    }
    
    // Update S21 stats
    if (data.summary.s21_avg_db !== undefined) {
        document.getElementById('avgS21').textContent = data.summary.s21_avg_db.toFixed(2);
        document.getElementById('maxS21').textContent = data.summary.s21_max_db.toFixed(2);
        document.getElementById('minS21').textContent = data.summary.s21_min_db.toFixed(2);
        
        // Update DRC display with current S21 RMS (only if not held)
        if (currentDrcSettings && !isDrcHeld) {
            updateDrcDisplay(data.summary.s21_avg_db);
        }
    }
    
    document.getElementById('lastUpdate').textContent = `Last update: ${data.timestamp}`;
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
            socket.emit('scan_ports');
            showNotification('Scanning for COM ports...', 'info');
        });
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
    const portSelect = document.getElementById('portSelect');
    if (!portSelect) return;
    
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
    
    const saveBtn = document.getElementById('saveDataBtn');
    saveBtn.disabled = true;
    saveBtn.textContent = '💾 Saving...';
    
    socket.emit('save_measurement', currentMeasurement);
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
        lastSavedTime.textContent = timeStr;
        lastSavedTime.title = `Sweep #${info.sweep_count} - S11: ${info.s11_rms.toFixed(2)} dB, S21: ${info.s21_rms.toFixed(2)} dB`;
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
            result.data.forEach(row => {
                const tr = document.createElement('tr');
                const timestamp = new Date(row.timestamp).toLocaleString();
                const drcDisplay = row.drc_percent !== null ? row.drc_percent : '--';
                
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
                    <td>
                        <button class="btn-small btn-view" onclick="viewDetails('${row.timestamp}')" title="View Details">👁️</button>
                    </td>
                `;
                tableBody.appendChild(tr);
            });
        } else {
            tableBody.innerHTML = '<tr><td colspan="11" class="no-data">No records found for the selected criteria.</td></tr>';
        }
    } else {
        errorMsg.textContent = '❌ ' + result.message;
        errorMsg.style.display = 'block';
        recordCount.textContent = '0 records';
        tableBody.innerHTML = '<tr><td colspan="11" class="no-data">Query failed. Check database connection.</td></tr>';
    }
});

function exportToCsv() {
    const table = document.getElementById('historyTable');
    const rows = table.querySelectorAll('tr');
    
    if (rows.length <= 1) {
        alert('No data to export');
        return;
    }
    
    let csv = [];
    
    // Get headers
    const headers = [];
    rows[0].querySelectorAll('th').forEach(th => {
        if (th.textContent !== 'Actions') {
            headers.push(th.textContent);
        }
    });
    csv.push(headers.join(','));
    
    // Get data rows
    for (let i = 1; i < rows.length; i++) {
        const row = rows[i];
        const cells = row.querySelectorAll('td');
        
        if (cells.length > 1) {
            const rowData = [];
            for (let j = 0; j < cells.length - 1; j++) {
                rowData.push(`"${cells[j].textContent}"`);
            }
            csv.push(rowData.join(','));
        }
    }
    
    // Download
    const csvContent = csv.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
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
        
        // Update form fields
        document.getElementById('drcBatchId').value = settings.batch_id;
        document.getElementById('s21LowDb').value = settings.s21_low_db;
        document.getElementById('drc1Percent').value = settings.drc1_percent;
        document.getElementById('s21HighDb').value = settings.s21_high_db;
        document.getElementById('drc2Percent').value = settings.drc2_percent;
        
        showNotification(`Loaded settings for ${settings.batch_id}`, 'success');
        
        // Update "Next Batch ID" display (timestamp format)
        document.getElementById('drcNextBatchId').textContent = 'Auto-generated on save';
        
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

// Auto-load DRC settings on page load to get next batch ID
setTimeout(() => {
    loadDrcSettings();
}, 1000);

// Reset Scan UI
function resetScanUI() {
    document.getElementById('scanProgressSection').style.display = 'none';
    document.getElementById('startScanBtn').disabled = false;
    scanCollectedData = [];
}