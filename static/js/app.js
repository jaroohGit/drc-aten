// WebSocket connection
const socket = io();

// Chart instances
let dbChart = null;
let s21Chart = null;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
    setupEventListeners();
    setupWebSocket();
    updateTime();
    setInterval(updateTime, 1000);
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
                    position: 'top'
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: 'Frequency (GHz)'
                    },
                    max: 0.95
                },
                y: {
                    title: {
                        display: true,
                        text: 'Magnitude (dB)'
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
                    position: 'top'
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    title: {
                        display: true,
                        text: 'Frequency (GHz)'
                    },
                    max: 0.95
                },
                y: {
                    title: {
                        display: true,
                        text: 'Magnitude (dB)'
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
}

// Setup event listeners
function setupEventListeners() {
    // Menu toggle
    document.getElementById('menuToggle').addEventListener('click', function() {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.getElementById('mainContent');
        sidebar.classList.toggle('collapsed');
        mainContent.classList.toggle('expanded');
    });

    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.dataset.page;
            switchPage(page);
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
    });

    socket.on('status', function(data) {
        console.log('Status:', data.message);
        if (data.running !== undefined) {
            document.getElementById('startBtn').disabled = data.running;
            document.getElementById('stopBtn').disabled = !data.running;
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
