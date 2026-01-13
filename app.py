"""
Flask Web Dashboard for NanoVNA Real-time Monitoring
WebSocket-based real-time chart updates with TimescaleDB storage
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
import os

# Try to import psycopg2, but make it optional
try:
    import psycopg2
    from psycopg2.extras import execute_values
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("⚠ psycopg2 not installed - running without database support")
    print("  Install: pip install psycopg2-binary")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nanovna-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5433'),
    'database': os.getenv('DB_NAME', 'nanovna_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'postgres')
}

# Global database connection
db_conn = None
last_saved_data = {
    'timestamp': None,
    'sweep_count': None,
    's11_rms': None,
    's21_rms': None
}

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


def init_database():
    """Initialize TimescaleDB connection and create tables"""
    global db_conn
    
    if not DB_AVAILABLE:
        print("⚠ Database module not available - skipping database initialization")
        return False
    
    try:
        db_conn = psycopg2.connect(**DB_CONFIG)
        cursor = db_conn.cursor()
        
        # Create measurements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS measurements (
                time TIMESTAMPTZ NOT NULL,
                sweep_count INTEGER,
                frequency DOUBLE PRECISION,
                s11_magnitude DOUBLE PRECISION,
                s11_db DOUBLE PRECISION,
                s11_phase DOUBLE PRECISION,
                s11_real DOUBLE PRECISION,
                s11_imag DOUBLE PRECISION,
                s21_magnitude DOUBLE PRECISION,
                s21_db DOUBLE PRECISION,
                s21_phase DOUBLE PRECISION,
                s21_real DOUBLE PRECISION,
                s21_imag DOUBLE PRECISION
            );
        """)
        
        # Create index for time-based queries on regular table
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_measurements_time 
            ON measurements (time DESC);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_measurements_sweep 
            ON measurements (sweep_count);
        """)
        print("  ✓ Measurements table created with indexes")
        
        # Create summary table for quick access
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS measurement_summary (
                time TIMESTAMPTZ NOT NULL PRIMARY KEY,
                sweep_count INTEGER,
                s11_rms DOUBLE PRECISION,
                s11_max DOUBLE PRECISION,
                s11_min DOUBLE PRECISION,
                s21_rms DOUBLE PRECISION,
                s21_max DOUBLE PRECISION,
                s21_min DOUBLE PRECISION,
                signal_quality DOUBLE PRECISION
            );
        """)
        print("  ✓ Summary table created")
        
        db_conn.commit()
        cursor.close()
        print("✓ Database initialized successfully (PostgreSQL)")
        return True
    except Exception as e:
        print(f"✗ Database initialization error: {e}")
        print("  Note: Make sure TimescaleDB is installed and running")
        db_conn = None
        return False


def save_measurement_to_db(data):
    """Save measurement data to TimescaleDB"""
    global db_conn, last_saved_data
    
    if not db_conn:
        return {'success': False, 'message': 'Database not connected'}
    
    try:
        cursor = db_conn.cursor()
        timestamp = datetime.now()
        
        # Prepare data for batch insert
        measurement_rows = []
        for i, s11_point in enumerate(data['s11_data']):
            s21_point = data['s21_data'][i] if i < len(data['s21_data']) else {}
            
            measurement_rows.append((
                timestamp,
                data['sweep_count'],
                s11_point['frequency'],
                s11_point['magnitude'],
                s11_point['db'],
                s11_point['phase'],
                s11_point['real'],
                s11_point['imag'],
                s21_point.get('magnitude'),
                s21_point.get('db'),
                s21_point.get('phase'),
                s21_point.get('real'),
                s21_point.get('imag')
            ))
        
        # Batch insert measurements
        execute_values(cursor, """
            INSERT INTO measurements 
            (time, sweep_count, frequency, s11_magnitude, s11_db, s11_phase, 
             s11_real, s11_imag, s21_magnitude, s21_db, s21_phase, s21_real, s21_imag)
            VALUES %s
        """, measurement_rows)
        
        # Insert summary
        cursor.execute("""
            INSERT INTO measurement_summary 
            (time, sweep_count, s11_rms, s11_max, s11_min, s21_rms, s21_max, s21_min, signal_quality)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            timestamp,
            data['sweep_count'],
            data['summary']['avg_db'],
            data['summary']['max_db'],
            data['summary']['min_db'],
            data['summary']['s21_avg_db'],
            data['summary']['s21_max_db'],
            data['summary']['s21_min_db'],
            data['connection_status']['signal_quality']
        ))
        
        db_conn.commit()
        cursor.close()
        
        # Update last saved info
        last_saved_data = {
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'sweep_count': data['sweep_count'],
            's11_rms': data['summary']['avg_db'],
            's21_rms': data['summary']['s21_avg_db']
        }
        
        return {
            'success': True,
            'message': 'Data saved successfully',
            'last_saved': last_saved_data
        }
        
    except Exception as e:
        print(f"Save error: {e}")
        if db_conn:
            db_conn.rollback()
        return {'success': False, 'message': f'Save error: {str(e)}'}


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


def calculate_rms(data_points, key='db'):
    """Calculate RMS (Root Mean Square) for better RF measurement consistency
    RMS = sqrt(mean(x^2)) - More stable than arithmetic mean for RF signals
    
    For dB values: RMS_dB = 10 * log10(mean(10^(dB/10)))
    This converts dB to linear (power), averages, then converts back to dB
    """
    try:
        if not data_points or len(data_points) == 0:
            return 0.0
        
        # Convert dB to linear scale (power), calculate mean, convert back to dB
        linear_values = [10 ** (d[key] / 10) for d in data_points]
        mean_linear = sum(linear_values) / len(linear_values)
        rms_db = 10 * math.log10(mean_linear) if mean_linear > 0 else -100
        
        return rms_db
    except Exception as e:
        print(f"RMS calculation error: {e}")
        return 0.0


def calculate_signal_quality(s11_data, s21_data):
    """Calculate signal quality based on data consistency"""
    try:
        if not s11_data or len(s11_data) < POINTS:
            return 0
        
        # Check data completeness
        completeness = (len(s11_data) / POINTS) * 40
        
        # Check S11 signal strength (better signal = closer to 0 dB) - use RMS
        s11_rms = calculate_rms(s11_data)
        signal_strength = max(0, min(30, (s11_rms + 50) / 50 * 30))
        
        # Check S21 availability
        s21_quality = 30 if s21_data and len(s21_data) >= POINTS else 0
        
        quality = completeness + signal_strength + s21_quality
        return min(100, max(0, quality))
    except:
        return 0


def detect_measurement_periods(historical_data, threshold=-8.0, min_duration=5):
    """Detect measurement periods from historical data
    Filters out spikes (no sample) and identifies actual measurement windows"""
    
    if not historical_data['timestamps'] or len(historical_data['timestamps']) < min_duration:
        return []
    
    periods = []
    current_period = None
    
    for i, (timestamp, s11_avg) in enumerate(zip(
        historical_data['timestamps'], 
        historical_data['s11_avg']
    )):
        is_measuring = s11_avg < threshold  # Below threshold = measuring
        
        if is_measuring:
            if current_period is None:
                # Start new measurement period
                current_period = {
                    'start_idx': i,
                    'start_time': timestamp,
                    'data_points': []
                }
            current_period['data_points'].append({
                'timestamp': timestamp,
                's11_avg': s11_avg,
                's11_max': historical_data['s11_max'][i],
                's11_min': historical_data['s11_min'][i],
                's21_avg': historical_data['s21_avg'][i],
                's21_max': historical_data['s21_max'][i],
                's21_min': historical_data['s21_min'][i],
            })
        else:
            if current_period and len(current_period['data_points']) >= min_duration:
                # End measurement period
                current_period['end_idx'] = i - 1
                current_period['end_time'] = historical_data['timestamps'][i-1]
                current_period['duration'] = current_period['end_time'] - current_period['start_time']
                periods.append(current_period)
            current_period = None
    
    # Handle last period
    if current_period and len(current_period['data_points']) >= min_duration:
        current_period['end_idx'] = len(historical_data['timestamps']) - 1
        current_period['end_time'] = historical_data['timestamps'][-1]
        current_period['duration'] = current_period['end_time'] - current_period['start_time']
        periods.append(current_period)
    
    return periods


def calculate_rms_from_values(db_values):
    """Calculate RMS from dB values directly"""
    if not db_values:
        return 0.0
    try:
        linear_values = [10 ** (db / 10) for db in db_values]
        mean_linear = sum(linear_values) / len(linear_values)
        return 10 * math.log10(mean_linear) if mean_linear > 0 else -100
    except:
        return 0.0


def calculate_period_fingerprint(period_data):
    """Calculate fingerprint for a measurement period"""
    try:
        s11_values = [d['s11_avg'] for d in period_data['data_points']]
        s21_values = [d['s21_avg'] for d in period_data['data_points']]
        
        # Calculate statistics
        s11_mean = sum(s11_values) / len(s11_values)
        s21_mean = sum(s21_values) / len(s21_values)
        
        s11_variance = sum((x - s11_mean) ** 2 for x in s11_values) / len(s11_values)
        s21_variance = sum((x - s21_mean) ** 2 for x in s21_values) / len(s21_values)
        
        fingerprint = {
            'duration': period_data['duration'],
            'num_points': len(period_data['data_points']),
            's11_rms': calculate_rms_from_values(s11_values),
            's21_rms': calculate_rms_from_values(s21_values),
            's11_std': math.sqrt(s11_variance),
            's21_std': math.sqrt(s21_variance),
            's11_range': max(s11_values) - min(s11_values),
            's21_range': max(s21_values) - min(s21_values),
            's11_min': min(s11_values),
            's11_max': max(s11_values),
            's21_min': min(s21_values),
            's21_max': max(s21_values),
        }
        
        return fingerprint
    except Exception as e:
        print(f"Fingerprint calculation error: {e}")
        return None


def compare_measurements(periods):
    """Compare all measurement periods"""
    if len(periods) < 2:
        return []
    
    fingerprints = []
    for p in periods:
        fp = calculate_period_fingerprint(p)
        if fp:
            fingerprints.append(fp)
    
    if len(fingerprints) < 2:
        return []
    
    comparisons = []
    
    for i in range(len(fingerprints)):
        for j in range(i + 1, len(fingerprints)):
            fp1, fp2 = fingerprints[i], fingerprints[j]
            
            # Calculate differences
            s11_diff = abs(fp1['s11_rms'] - fp2['s11_rms'])
            s21_diff = abs(fp1['s21_rms'] - fp2['s21_rms'])
            std_diff = abs(fp1['s11_std'] - fp2['s11_std'])
            
            # Similarity scores (0-100%)
            s11_similarity = max(0, 100 - (s11_diff * 10))  # Allow 10dB difference
            s21_similarity = max(0, 100 - (s21_diff * 10))
            std_similarity = max(0, 100 - (std_diff * 20))
            
            overall_similarity = (s11_similarity * 0.4 + 
                                s21_similarity * 0.4 + 
                                std_similarity * 0.2)
            
            comparisons.append({
                'period_1': i + 1,
                'period_2': j + 1,
                'similarity': round(overall_similarity, 1),
                'is_same': overall_similarity > 85,
                's11_rms_1': round(fp1['s11_rms'], 2),
                's11_rms_2': round(fp2['s11_rms'], 2),
                's21_rms_1': round(fp1['s21_rms'], 2),
                's21_rms_2': round(fp2['s21_rms'], 2),
                's11_diff': round(s11_diff, 2),
                's21_diff': round(s21_diff, 2),
            })
    
    return comparisons


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
                print(f"  S11 dB: Min={min(d['db'] for d in s11_data):.2f}, Max={max(d['db'] for d in s11_data):.2f}, RMS={calculate_rms(s11_data):.2f}")
                
                if s21_data:
                    print(f"  S21 dB: Min={min(d['db'] for d in s21_data):.2f}, Max={max(d['db'] for d in s21_data):.2f}, RMS={calculate_rms(s21_data):.2f}")
                    
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
                        'avg_db': calculate_rms(s11_data),  # Use RMS instead of arithmetic mean
                        'max_db': max(d['db'] for d in s11_data),
                        'min_db': min(d['db'] for d in s11_data),
                        'avg_phase': sum(d['phase'] for d in s11_data) / len(s11_data),
                        's21_avg_db': calculate_rms(s21_data) if s21_data else 0,  # Use RMS for S21
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


@socketio.on('analyze_measurements')
def handle_analyze_measurements(data):
    """Analyze historical data for measurement periods and similarities"""
    try:
        threshold = data.get('threshold', -8.0)
        min_duration = data.get('min_duration', 5)
        
        # Detect measurement periods
        periods = detect_measurement_periods(historical_data, threshold, min_duration)
        
        if not periods:
            emit('analysis_result', {
                'success': False,
                'message': 'No measurement periods detected. Try adjusting the threshold or collect more data.'
            })
            return
        
        # Calculate fingerprints and comparisons
        comparisons = compare_measurements(periods)
        
        # Prepare period summaries
        period_summaries = []
        for i, period in enumerate(periods):
            fp = calculate_period_fingerprint(period)
            if fp:
                # Calculate time ago
                time_ago = time.time() - period['end_time']
                
                period_summaries.append({
                    'id': i + 1,
                    'start_time': period['start_time'],
                    'end_time': period['end_time'],
                    'duration': round(period['duration'], 1),
                    'time_ago': round(time_ago, 0),
                    'num_points': fp['num_points'],
                    's11_rms': fp['s11_rms'],
                    's21_rms': fp['s21_rms'],
                    's11_std': fp['s11_std'],
                    's21_std': fp['s21_std'],
                    's11_range': fp['s11_range'],
                    's21_range': fp['s21_range'],
                    's11_min': fp['s11_min'],
                    's11_max': fp['s11_max'],
                    's21_min': fp['s21_min'],
                    's21_max': fp['s21_max'],
                })
        
        # Calculate summary statistics
        same_sample_count = sum(1 for c in comparisons if c['is_same'])
        avg_similarity = sum(c['similarity'] for c in comparisons) / len(comparisons) if comparisons else 0
        
        emit('analysis_result', {
            'success': True,
            'periods': period_summaries,
            'comparisons': comparisons,
            'summary': {
                'total_periods': len(periods),
                'total_comparisons': len(comparisons),
                'same_sample_count': same_sample_count,
                'avg_similarity': round(avg_similarity, 1)
            }
        })
        
    except Exception as e:
        print(f"Analysis error: {e}")
        import traceback
        traceback.print_exc()
        emit('analysis_result', {
            'success': False,
            'message': f'Analysis error: {str(e)}'
        })


@socketio.on('save_measurement')
def handle_save_measurement(data):
    """Save current measurement to database"""
    result = save_measurement_to_db(data)
    emit('save_result', result)


@socketio.on('get_last_saved')
def handle_get_last_saved():
    """Get last saved measurement info"""
    emit('last_saved_info', last_saved_data)


@socketio.on('query_historical_data')
def handle_query_historical_data(params):
    """Query historical data from database"""
    if not DB_AVAILABLE or not db_conn:
        emit('historical_data_result', {
            'success': False,
            'message': 'Database not available. Please configure PostgreSQL/TimescaleDB.'
        })
        return
    
    try:
        cursor = db_conn.cursor()
        
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        limit = params.get('limit', 100)
        
        # Build query
        query = """
            SELECT 
                time,
                sweep_count,
                s11_rms,
                s11_min,
                s11_max,
                s21_rms,
                s21_min,
                s21_max
            FROM measurement_summary
        """
        
        conditions = []
        query_params = []
        
        if start_date:
            conditions.append("time >= %s")
            query_params.append(start_date)
        
        if end_date:
            conditions.append("time <= %s")
            query_params.append(end_date)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY time DESC LIMIT %s"
        query_params.append(limit)
        
        cursor.execute(query, query_params)
        rows = cursor.fetchall()
        
        # Format results
        results = []
        for row in rows:
            results.append({
                'timestamp': row[0].isoformat(),
                'sweep_count': row[1],
                's11_rms': round(row[2], 2),
                's11_min': round(row[3], 2),
                's11_max': round(row[4], 2),
                's21_rms': round(row[5], 2),
                's21_min': round(row[6], 2),
                's21_max': round(row[7], 2)
            })
        
        cursor.close()
        
        emit('historical_data_result', {
            'success': True,
            'data': results,
            'count': len(results)
        })
        
    except Exception as e:
        print(f"Query error: {e}")
        import traceback
        traceback.print_exc()
        emit('historical_data_result', {
            'success': False,
            'message': f'Query error: {str(e)}'
        })


if __name__ == '__main__':
    print("="*60)
    print("DRC Online - Premeir System Engineering Co.ltd")
    print("="*60)
    print(f"Port: {PORT}")
    print(f"Frequency: {START_FREQ/1e9:.2f} - {STOP_FREQ/1e9:.2f} GHz")
    print(f"Points: {POINTS}")
    print(f"Interval: {INTERVAL*1000:.0f} ms")
    print("="*60)
    
    # Initialize database
    print("\nInitializing TimescaleDB connection...")
    if init_database():
        print("✓ Database ready")
    else:
        print("⚠ Running without database (data will not be saved)")
    
    print("\nStarting server at http://localhost:5000")
    print("Open your browser and navigate to the URL above")
    print("="*60)
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
