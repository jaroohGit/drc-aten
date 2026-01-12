// WebSocket connection
const socket = io();

// Chart instances
let dbChart = null;
let s21Chart = null;
let historicalChart = null;

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
}

// Setup event listeners
function setupEventListeners() {
    // Menu toggle
    document.getElementById('menuToggle').addEventListener('click', function() {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.getElementById('mainContent');
        
        // Toggle sidebar visibility (responsive behavior)
        if (window.innerWidth <= 1024) {
            sidebar.classList.toggle('show');
        } else {
            sidebar.classList.toggle('collapsed');
            mainContent.classList.toggle('expanded');
        }
    });
    
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
    const statusText = statusIndicator.querySelector('.status-text');
    
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