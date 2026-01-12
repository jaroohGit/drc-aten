"""
Flask Web Dashboard for NanoVNA Real-time Monitoring
WebSocket-based real-time chart updates
"""

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import serial
import serial.tools.list_ports
import time
import math
from datetime import datetime
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nanovna-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# NanoVNA Configuration
PORT = "COM4"
BAUDRATE = 115200
START_FREQ = 0.9e9   # 0.9 GHz (900 MHz)
STOP_FREQ = 0.95e9   # 0.95 GHz (950 MHz)
POINTS = 101
INTERVAL = 0.5  # seconds (500 ms) - Optimized for faster data acquisition

# Global variables
is_running = False
ser = None
sweep_count = 0
connection_status = {
    'connected': False,
    'port': PORT,
    'error': None,
    'signal_quality': 0,
    'last_sweep_time': None
}

# Historical data storage (5 minutes = 300 data points at 1 second interval)
historical_data = {
    'timestamps': [],
    's11_avg': [],
    's11_max': [],
    's11_min': [],
    's21_avg': [],
    's21_max': [],
    's21_min': []
}
MAX_HISTORY_POINTS = 300  # 5 minutes at 1 second interval


def get_available_ports():
    """Get list of available COM ports"""
    ports = []
    for port in serial.tools.list_ports.comports():
        ports.append({
            'port': port.device,
            'description': port.description,
            'hwid': port.hwid
        })
    return ports


def calculate_signal_quality(s11_data, s21_data):
    """Calculate signal quality based on data consistency"""
    try:
        if not s11_data or len(s11_data) < POINTS:
            return 0
        
        # Check data completeness
        completeness = (len(s11_data) / POINTS) * 40
        
        # Check S11 signal strength (better signal = closer to 0 dB)
        s11_avg = sum(d['db'] for d in s11_data) / len(s11_data)
        signal_strength = max(0, min(30, (s11_avg + 50) / 50 * 30))
        
        # Check S21 availability
        s21_quality = 30 if s21_data and len(s21_data) >= POINTS else 0
        
        quality = completeness + signal_strength + s21_quality
        return min(100, max(0, quality))
    except:
        return 0


def connect_nanovna(port=None):
    """Connect to NanoVNA device"""
    global ser
    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=2)
        time.sleep(0.5)
        ser.reset_input_buffer()
        
        # Set sweep parameters
        cmd = f"sweep {int(START_FREQ)} {int(STOP_FREQ)} {POINTS}"
        ser.write(f"{cmd}\r\n".encode())
        time.sleep(0.3)
        ser.read(ser.in_waiting)
        
        return True
    except Exception as e:
        print(f"Connection error: {e}")
        return False


def disconnect_nanovna():
    """Disconnect from NanoVNA device"""
    global ser, connection_status
    if ser and ser.is_open:
        ser.close()
    connection_status['connected'] = False


def sweep_loop():
    """Continuous sweep loop that sends data via WebSocket"""
    global is_running, ser, sweep_count, connection_status
    
    while is_running:
        try:
            sweep_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            connection_status['last_sweep_time'] = timestamp
            
            # Perform scan
            cmd = f"scan {int(START_FREQ)} {int(STOP_FREQ)} {POINTS}"
            ser.write(f"{cmd}\r\n".encode())
            time.sleep(0.3)  # Wait for scan to complete (optimized)
            ser.read(ser.in_waiting)
            
            # Get S11 data with retry until we get all points
            response_s11 = ""
            for attempt in range(3):  # Try up to 3 times
                ser.reset_input_buffer()  # ล้าง buffer ก่อนอ่าน
                time.sleep(0.15)
                
                ser.write(b"data 0\r\n")
                time.sleep(0.35)  # Wait for data (optimized)
                
                response_s11 = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                lines_s11 = [l.strip() for l in response_s11.split('\n') 
                         if l.strip() and not l.strip().startswith('ch>') 
                         and not l.strip().startswith('data')]
                
                if len(lines_s11) >= POINTS:
                    lines_s11 = lines_s11[:POINTS]  # เอาแค่ POINTS จุดแรก
                    break  # Got all points
                    
                print(f"S11: Attempt {attempt + 1}, got {len(lines_s11)}/{POINTS} points, retrying...")
                time.sleep(0.15)  # Short delay before retry (optimized)
            
            print(f"\n[S11 Response - {timestamp}] - {len(lines_s11)} points")
            if len(lines_s11) >= 3:
                print(f"  S11 Raw[0]: {lines_s11[0]}")
                print(f"  S11 Raw[1]: {lines_s11[1]}")
                print(f"  S11 Raw[2]: {lines_s11[2]}")
            
            # ===== ล้าง buffer หลายครั้งและรอก่อนอ่าน S21 =====
            print(f"\n[Preparing to read S21...]")
            time.sleep(0.3)
            for _ in range(3):  # ล้าง buffer หลายรอบ
                ser.reset_input_buffer()
                time.sleep(0.08)
                ser.read(ser.in_waiting)
            
            # Get S21 data with validation that it's different from S11
            response_s21 = ""
            lines_s21 = []
            max_attempts = 5  # เพิ่มจำนวนครั้งที่ลอง
            
            for attempt in range(max_attempts):
                print(f"\n[S21 Attempt {attempt + 1}/{max_attempts}]")
                
                # ล้าง buffer
                ser.reset_input_buffer()
                time.sleep(0.15)
                
                # สลับไปยัง trace 1 (S21) ทุกครั้ง
                ser.write(b"trace 1\r\n")
                time.sleep(0.3)
                ser.read(ser.in_waiting)
                
                # อ่านข้อมูล S21
                ser.write(b"data 1\r\n")
                time.sleep(0.5)
                
                response_s21 = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                lines_s21 = [l.strip() for l in response_s21.split('\n') 
                         if l.strip() and not l.strip().startswith('ch>') 
                         and not l.strip().startswith('data')
                         and not l.strip().startswith('trace')]
                
                if len(lines_s21) >= POINTS:
                    lines_s21 = lines_s21[:POINTS]
                    
                    # ตรวจสอบว่าข้อมูล S21 ต่างจาก S11 หรือไม่
                    if len(lines_s11) > 0 and len(lines_s21) > 0:
                        s11_parts = lines_s11[0].split()
                        s21_parts = lines_s21[0].split()
                        
                        if len(s11_parts) >= 2 and len(s21_parts) >= 2:
                            s11_real = float(s11_parts[0])
                            s11_imag = float(s11_parts[1])
                            s21_real = float(s21_parts[0])
                            s21_imag = float(s21_parts[1])
                            
                            # เช็คว่าต่างกันมากกว่า 0.01
                            diff = abs(s11_real - s21_real) + abs(s11_imag - s21_imag)
                            
                            if diff > 0.01:
                                print(f"  ✓ S21 data verified DIFFERENT from S11 (diff={diff:.4f})")
                                break
                            else:
                                print(f"  ⚠ S21 data too similar to S11 (diff={diff:.4f}), retrying...")
                                time.sleep(0.3)
                                continue
                    
                    break
                    
                print(f"  S21: Got {len(lines_s21)}/{POINTS} points, retrying...")
                time.sleep(0.2)
            
            print(f"[S21 Response - {timestamp}] - {len(lines_s21)} points")
            if len(lines_s21) >= 3:
                print(f"  S21 Raw[0]: {lines_s21[0]}")
                print(f"  S21 Raw[1]: {lines_s21[1]}")
                print(f"  S21 Raw[2]: {lines_s21[2]}")
            
            # สลับกลับไปยัง trace 0 สำหรับ sweep ครั้งถัดไป
            ser.write(b"trace 0\r\n")
            time.sleep(0.2)
            ser.read(ser.in_waiting)
            
            # Parse S11 data points
            
            s11_data = []
            s21_data = []
            frequencies = []
            
            for i, line in enumerate(lines_s11[:POINTS]):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        real = float(parts[0])
                        imag = float(parts[1])
                        magnitude = (real**2 + imag**2)**0.5
                        db = 20 * math.log10(magnitude) if magnitude > 0 else -999
                        phase = math.degrees(math.atan2(imag, real))
                        
                        freq_ghz = START_FREQ/1e9 + (i * (STOP_FREQ - START_FREQ) / (POINTS - 1)) / 1e9
                        
                        s11_data.append({
                            'frequency': freq_ghz,
                            'magnitude': magnitude,
                            'db': db,
                            'phase': phase,
                            'real': real,
                            'imag': imag
                        })
                        frequencies.append(freq_ghz)
                    except (ValueError, ZeroDivisionError):
                        continue
            
            # Parse S21 data
            for i, line in enumerate(lines_s21[:POINTS]):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        real = float(parts[0])
                        imag = float(parts[1])
                        magnitude = (real**2 + imag**2)**0.5
                        db = 20 * math.log10(magnitude) if magnitude > 0 else -999
                        phase = math.degrees(math.atan2(imag, real))
                        
                        freq_ghz = START_FREQ/1e9 + (i * (STOP_FREQ - START_FREQ) / (POINTS - 1)) / 1e9
                        
                        s21_data.append({
                            'frequency': freq_ghz,
                            'magnitude': magnitude,
                            'db': db,
                            'phase': phase,
                            'real': real,
                            'imag': imag
                        })
                    except (ValueError, ZeroDivisionError):
                        continue
            
            # Calculate signal quality
            signal_quality = calculate_signal_quality(s11_data, s21_data)
            connection_status['signal_quality'] = signal_quality
            
            # Send data via WebSocket - ต้องได้ข้อมูลครบถ้วนถึงจะส่ง
            if s11_data and len(s11_data) == POINTS:
                print(f"\n✓ อ่านค่าได้สำเร็จ - Sweep #{sweep_count} [{timestamp}]")
                print(f"  S11: {len(s11_data)}/{POINTS} points | S21: {len(s21_data)}/{POINTS} points")
                print(f"  Signal Quality: {signal_quality:.1f}%")
                print(f"  S11 dB: Min={min(d['db'] for d in s11_data):.2f}, Max={max(d['db'] for d in s11_data):.2f}, Avg={sum(d['db'] for d in s11_data)/len(s11_data):.2f}")
                
                if s21_data:
                    print(f"  S21 dB: Min={min(d['db'] for d in s21_data):.2f}, Max={max(d['db'] for d in s21_data):.2f}, Avg={sum(d['db'] for d in s21_data)/len(s21_data):.2f}")
                    
                    # ตรวจสอบว่าข้อมูล S21 ต่างจาก S11 หรือไม่
                    s11_first_3 = [(s11_data[i]['real'], s11_data[i]['imag']) for i in range(min(3, len(s11_data)))]
                    s21_first_3 = [(s21_data[i]['real'], s21_data[i]['imag']) for i in range(min(3, len(s21_data)))]
                    
                    if s11_first_3 == s21_first_3:
                        print(f"  ⚠ WARNING: S21 data identical to S11! Data may be incorrect!")
                    else:
                        print(f"  ✓ S21 data verified different from S11")
                    
                    print(f"\n  === Data Comparison (First 3 points) ===")
                    print(f"  S11[0]: Real={s11_data[0]['real']:.6f}, Imag={s11_data[0]['imag']:.6f}, dB={s11_data[0]['db']:.2f}")
                    print(f"  S21[0]: Real={s21_data[0]['real']:.6f}, Imag={s21_data[0]['imag']:.6f}, dB={s21_data[0]['db']:.2f}")
                    print(f"  S11[1]: Real={s11_data[1]['real']:.6f}, Imag={s11_data[1]['imag']:.6f}, dB={s11_data[1]['db']:.2f}")
                    print(f"  S21[1]: Real={s21_data[1]['real']:.6f}, Imag={s21_data[1]['imag']:.6f}, dB={s21_data[1]['db']:.2f}")
                    print(f"  S11[2]: Real={s11_data[2]['real']:.6f}, Imag={s11_data[2]['imag']:.6f}, dB={s11_data[2]['db']:.2f}")
                    print(f"  S21[2]: Real={s21_data[2]['real']:.6f}, Imag={s21_data[2]['imag']:.6f}, dB={s21_data[2]['db']:.2f}")
                    # Show first 5 and last 5 data points
                    print(f"  First 5 points:")
                    for i in range(min(5, len(s21_data))):
                        d = s21_data[i]
                        print(f"    [{i}] Freq: {d['frequency']:.4f} GHz, dB: {d['db']:.2f}, Phase: {d['phase']:.2f}°")
                    if len(s21_data) > 10:
                        print(f"  ...")
                    if len(s21_data) > 5:
                        print(f"  Last 5 points:")
                        for i in range(max(0, len(s21_data)-5), len(s21_data)):
                            d = s21_data[i]
                            print(f"    [{i}] Freq: {d['frequency']:.4f} GHz, dB: {d['db']:.2f}, Phase: {d['phase']:.2f}°")
                
                data = {
                    'timestamp': timestamp,
                    'sweep_count': sweep_count,
                    's11_data': s11_data,
                    's21_data': s21_data,
                    'summary': {
                        'avg_db': sum(d['db'] for d in s11_data) / len(s11_data),
                        'max_db': max(d['db'] for d in s11_data),
                        'min_db': min(d['db'] for d in s11_data),
                        'avg_phase': sum(d['phase'] for d in s11_data) / len(s11_data),
                        's21_avg_db': sum(d['db'] for d in s21_data) / len(s21_data) if s21_data else 0,
                        's21_max_db': max(d['db'] for d in s21_data) if s21_data else 0,
                        's21_min_db': min(d['db'] for d in s21_data) if s21_data else 0
                    },
                    'connection_status': connection_status
                }
                
                # Update historical data
                current_time = time.time()
                historical_data['timestamps'].append(current_time)
                historical_data['s11_avg'].append(data['summary']['avg_db'])
                historical_data['s11_max'].append(data['summary']['max_db'])
                historical_data['s11_min'].append(data['summary']['min_db'])
                historical_data['s21_avg'].append(data['summary']['s21_avg_db'])
                historical_data['s21_max'].append(data['summary']['s21_max_db'])
                historical_data['s21_min'].append(data['summary']['s21_min_db'])
                
                # Keep only last 5 minutes of data
                if len(historical_data['timestamps']) > MAX_HISTORY_POINTS:
                    for key in historical_data:
                        historical_data[key] = historical_data[key][-MAX_HISTORY_POINTS:]
                
                # Add historical data to emit
                data['historical'] = historical_data
                
                socketio.emit('sweep_data', data)
            else:
                print(f"\n✗ ข้อมูลไม่ครบ - Sweep #{sweep_count} [{timestamp}]: S11={len(s11_data)}/{POINTS} จุด (ข้ามการแสดงผล)")
                connection_status['signal_quality'] = 0
            
            time.sleep(INTERVAL)
            
        except Exception as e:
            print(f"Sweep error: {e}")
            connection_status['connected'] = False
            connection_status['error'] = str(e)
            connection_status['signal_quality'] = 0
            socketio.emit('error', {'message': str(e)})
            time.sleep(INTERVAL)


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    emit('status', {
        'message': 'Connected to server',
        'sweep_count': sweep_count,
        'connection_status': connection_status
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')


@socketio.on('scan_ports')
def handle_scan_ports():
    """Scan for available COM ports"""
    ports = get_available_ports()
    emit('ports_list', {'ports': ports})


@socketio.on('test_connection')
def handle_test_connection(data):
    """Test connection to specified port"""
    port = data.get('port', PORT)
    
    try:
        test_ser = serial.Serial(port, BAUDRATE, timeout=2)
        time.sleep(0.5)
        test_ser.close()
        emit('connection_test', {
            'success': True,
            'port': port,
            'message': 'Connection successful'
        })
    except Exception as e:
        emit('connection_test', {
            'success': False,
            'port': port,
            'message': str(e)
        })


@socketio.on('change_port')
def handle_change_port(data):
    """Change COM port"""
    global PORT, is_running
    
    new_port = data.get('port')
    
    if is_running:
        emit('error', {'message': 'Please stop sweep before changing port'})
        return
    
    PORT = new_port
    emit('status', {
        'message': f'Port changed to {PORT}',
        'port': PORT
    })


@socketio.on('update_config')
def handle_update_config(data):
    """Update sweep configuration"""
    global START_FREQ, STOP_FREQ, POINTS, INTERVAL, is_running
    
    if is_running:
        emit('error', {'message': 'Please stop sweep before changing configuration'})
        return
    
    try:
        if 'start_freq' in data:
            START_FREQ = float(data['start_freq']) * 1e9
        if 'stop_freq' in data:
            STOP_FREQ = float(data['stop_freq']) * 1e9
        if 'points' in data:
            POINTS = int(data['points'])
        if 'interval' in data:
            INTERVAL = float(data['interval']) / 1000
        
        config = {
            'port': PORT,
            'start_freq': START_FREQ / 1e9,
            'stop_freq': STOP_FREQ / 1e9,
            'points': POINTS,
            'interval': INTERVAL * 1000
        }
        emit('config', config)
        emit('status', {'message': 'Configuration updated successfully'})
    except Exception as e:
        emit('error', {'message': f'Configuration update failed: {str(e)}'})


@socketio.on('get_connection_status')
def handle_get_connection_status():
    """Send current connection status"""
    emit('connection_status_update', connection_status)


@socketio.on('start_sweep')
def handle_start_sweep():
    """Start continuous sweep"""
    global is_running
    
    if not is_running:
        if connect_nanovna():
            is_running = True
            thread = threading.Thread(target=sweep_loop)
            thread.daemon = True
            thread.start()
            emit('status', {
                'message': 'Sweep started',
                'running': True,
                'connection_status': connection_status
            })
        else:
            emit('error', {
                'message': 'Failed to connect to NanoVNA',
                'connection_status': connection_status
            })
    else:
        emit('status', {'message': 'Already running', 'running': True})


@socketio.on('stop_sweep')
def handle_stop_sweep():
    """Stop continuous sweep"""
    global is_running
    is_running = False
    disconnect_nanovna()
    emit('status', {
        'message': 'Sweep stopped',
        'running': False,
        'connection_status': connection_status
    })


@socketio.on('get_config')
def handle_get_config():
    """Send current configuration"""
    config = {
        'port': PORT,
        'start_freq': START_FREQ / 1e9,
        'stop_freq': STOP_FREQ / 1e9,
        'points': POINTS,
        'interval': INTERVAL * 1000
    }
    emit('config', config)


if __name__ == '__main__':
    print("="*60)
    print("DRC Online - Premeir System Engineering Co.ltd")
    print("="*60)
    print(f"Port: {PORT}")
    print(f"Frequency: {START_FREQ/1e9:.2f} - {STOP_FREQ/1e9:.2f} GHz")
    print(f"Points: {POINTS}")
    print(f"Interval: {INTERVAL*1000:.0f} ms")
    print("="*60)
    print("\nStarting server at http://localhost:5000")
    print("Open your browser and navigate to the URL above")
    print("="*60)
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
