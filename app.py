"""
Flask Web Dashboard for NanoVNA Real-time Monitoring
WebSocket-based real-time chart updates
"""

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import serial
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
INTERVAL = 1.0  # seconds (1000 ms)

# Global variables
is_running = False
ser = None
sweep_count = 0


def connect_nanovna():
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
    global ser
    if ser and ser.is_open:
        ser.close()


def sweep_loop():
    """Continuous sweep loop that sends data via WebSocket"""
    global is_running, ser, sweep_count
    
    while is_running:
        try:
            sweep_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Perform scan
            cmd = f"scan {int(START_FREQ)} {int(STOP_FREQ)} {POINTS}"
            ser.write(f"{cmd}\r\n".encode())
            time.sleep(0.5)  # Wait for scan to complete
            ser.read(ser.in_waiting)
            
            # Get S11 data with retry until we get all points
            response_s11 = ""
            for attempt in range(3):  # Try up to 3 times
                ser.write(b"data 0\r\n")
                time.sleep(0.5)  # Wait for data
                
                response_s11 = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                lines_s11 = [l.strip() for l in response_s11.split('\n') 
                         if l.strip() and not l.strip().startswith('ch>') 
                         and not l.strip().startswith('data')]
                
                if len(lines_s11) >= POINTS:
                    break  # Got all points
                    
                print(f"S11: Attempt {attempt + 1}, got {len(lines_s11)}/{POINTS} points, retrying...")
                time.sleep(0.2)  # Short delay before retry
            
            print(f"\n[S11 Response - {timestamp}] - {len(lines_s11)} points")
            
            # Get S21 data with retry until we get all points
            response_s21 = ""
            for attempt in range(3):  # Try up to 3 times
                ser.write(b"data 1\r\n")
                time.sleep(0.5)  # Wait for data
                
                response_s21 = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                lines_s21 = [l.strip() for l in response_s21.split('\n') 
                         if l.strip() and not l.strip().startswith('ch>') 
                         and not l.strip().startswith('data')]
                
                if len(lines_s21) >= POINTS:
                    break  # Got all points
                    
                print(f"S21: Attempt {attempt + 1}, got {len(lines_s21)}/{POINTS} points, retrying...")
                time.sleep(0.2)  # Short delay before retry
            
            print(f"[S21 Response - {timestamp}] - {len(lines_s21)} points")
            
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
            
            # Send data via WebSocket
            if s11_data and len(s11_data) == POINTS:
                print(f"\n✓ อ่านค่าได้สำเร็จ - Sweep #{sweep_count} [{timestamp}]")
                print(f"  S11: {len(s11_data)} points | S21: {len(s21_data)} points")
                print(f"  S11 dB: Min={min(d['db'] for d in s11_data):.2f}, Max={max(d['db'] for d in s11_data):.2f}, Avg={sum(d['db'] for d in s11_data)/len(s11_data):.2f}")
                if s21_data:
                    print(f"  S21 dB: Min={min(d['db'] for d in s21_data):.2f}, Max={max(d['db'] for d in s21_data):.2f}, Avg={sum(d['db'] for d in s21_data)/len(s21_data):.2f}")
                    print(f"\n  === S21 Data Details ===")
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
                    }
                }
                socketio.emit('sweep_data', data)
            else:
                print(f"\n✗ ข้อมูลไม่ครบ - Sweep #{sweep_count} [{timestamp}]: S11={len(s11_data)}/{POINTS} จุด (ข้ามการแสดงผล)")
            
            time.sleep(INTERVAL)
            
        except Exception as e:
            print(f"Sweep error: {e}")
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
    emit('status', {'message': 'Connected to server', 'sweep_count': sweep_count})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')


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
            emit('status', {'message': 'Sweep started', 'running': True})
        else:
            emit('error', {'message': 'Failed to connect to NanoVNA'})
    else:
        emit('status', {'message': 'Already running', 'running': True})


@socketio.on('stop_sweep')
def handle_stop_sweep():
    """Stop continuous sweep"""
    global is_running
    is_running = False
    disconnect_nanovna()
    emit('status', {'message': 'Sweep stopped', 'running': False})


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
