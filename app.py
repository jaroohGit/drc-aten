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
                ser.reset_input_buffer()  # ล้าง buffer ก่อนอ่าน
                time.sleep(0.2)
                
                ser.write(b"data 0\r\n")
                time.sleep(0.5)  # Wait for data
                
                response_s11 = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                lines_s11 = [l.strip() for l in response_s11.split('\n') 
                         if l.strip() and not l.strip().startswith('ch>') 
                         and not l.strip().startswith('data')]
                
                if len(lines_s11) >= POINTS:
                    lines_s11 = lines_s11[:POINTS]  # เอาแค่ POINTS จุดแรก
                    break  # Got all points
                    
                print(f"S11: Attempt {attempt + 1}, got {len(lines_s11)}/{POINTS} points, retrying...")
                time.sleep(0.2)  # Short delay before retry
            
            print(f"\n[S11 Response - {timestamp}] - {len(lines_s11)} points")
            if len(lines_s11) >= 3:
                print(f"  S11 Raw[0]: {lines_s11[0]}")
                print(f"  S11 Raw[1]: {lines_s11[1]}")
                print(f"  S11 Raw[2]: {lines_s11[2]}")
            
            # ===== ล้าง buffer หลายครั้งและรอก่อนอ่าน S21 =====
            print(f"\n[Preparing to read S21...]")
            time.sleep(0.5)
            for _ in range(3):  # ล้าง buffer หลายรอบ
                ser.reset_input_buffer()
                time.sleep(0.1)
                ser.read(ser.in_waiting)
            
            # Get S21 data with validation that it's different from S11
            response_s21 = ""
            lines_s21 = []
            max_attempts = 5  # เพิ่มจำนวนครั้งที่ลอง
            
            for attempt in range(max_attempts):
                print(f"\n[S21 Attempt {attempt + 1}/{max_attempts}]")
                
                # ล้าง buffer
                ser.reset_input_buffer()
                time.sleep(0.2)
                
                # สลับไปยัง trace 1 (S21) ทุกครั้ง
                ser.write(b"trace 1\r\n")
                time.sleep(0.4)
                ser.read(ser.in_waiting)
                
                # อ่านข้อมูล S21
                ser.write(b"data 1\r\n")
                time.sleep(0.7)
                
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
                                time.sleep(0.5)
                                continue
                    
                    break
                    
                print(f"  S21: Got {len(lines_s21)}/{POINTS} points, retrying...")
                time.sleep(0.3)
            
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
            
            # Send data via WebSocket - ต้องได้ข้อมูลครบถ้วนถึงจะส่ง
            if s11_data and len(s11_data) == POINTS:
                print(f"\n✓ อ่านค่าได้สำเร็จ - Sweep #{sweep_count} [{timestamp}]")
                print(f"  S11: {len(s11_data)}/{POINTS} points | S21: {len(s21_data)}/{POINTS} points")
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
