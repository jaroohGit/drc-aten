"""
Flask Web Dashboard for NanoVNA Real-time Monitoring
WebSocket-based real-time chart updates with TimescaleDB storage
"""

from flask import Flask, render_template, request
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
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='threading',
                   logger=True,
                   engineio_logger=True,
                   ping_timeout=60,
                   ping_interval=25)

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

# Headless mode configuration
HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'false').lower() == 'true'
IDLE_TIMEOUT = int(os.getenv('IDLE_TIMEOUT', '300'))  # 5 minutes default
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'  # Production: false, Development: true
active_clients = 0
last_activity_time = None
idle_check_thread = None

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


def debug_print(*args, **kwargs):
    """Print debug messages only when DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(*args, **kwargs)


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
                s21_imag DOUBLE PRECISION,
                batch_id VARCHAR(50),
                drc_percent DOUBLE PRECISION,
                slip_no VARCHAR(50),
                sampling_no VARCHAR(50),
                test_no VARCHAR(10)
            );
        """)
        
        # Add batch_id and drc_percent columns if they don't exist (for existing databases)
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='measurements' AND column_name='batch_id'
                ) THEN
                    ALTER TABLE measurements ADD COLUMN batch_id VARCHAR(50);
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='measurements' AND column_name='drc_percent'
                ) THEN
                    ALTER TABLE measurements ADD COLUMN drc_percent DOUBLE PRECISION;
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='measurements' AND column_name='slip_no'
                ) THEN
                    ALTER TABLE measurements ADD COLUMN slip_no VARCHAR(50);
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='measurements' AND column_name='sampling_no'
                ) THEN
                    ALTER TABLE measurements ADD COLUMN sampling_no VARCHAR(50);
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='measurements' AND column_name='test_no'
                ) THEN
                    ALTER TABLE measurements ADD COLUMN test_no VARCHAR(10);
                END IF;
            END $$;
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
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_measurements_slip 
            ON measurements (slip_no);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_measurements_sampling 
            ON measurements (sampling_no);
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
                signal_quality DOUBLE PRECISION,
                batch_id VARCHAR(50),
                slip_no VARCHAR(50),
                sampling_no VARCHAR(50),
                test_no VARCHAR(10)
            );
        """)
        print("  ✓ Summary table created")
        
        # Add batch_id column if it doesn't exist (for existing databases)
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='measurement_summary' AND column_name='batch_id'
                ) THEN
                    ALTER TABLE measurement_summary ADD COLUMN batch_id VARCHAR(50);
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='measurement_summary' AND column_name='slip_no'
                ) THEN
                    ALTER TABLE measurement_summary ADD COLUMN slip_no VARCHAR(50);
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='measurement_summary' AND column_name='sampling_no'
                ) THEN
                    ALTER TABLE measurement_summary ADD COLUMN sampling_no VARCHAR(50);
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='measurement_summary' AND column_name='test_no'
                ) THEN
                    ALTER TABLE measurement_summary ADD COLUMN test_no VARCHAR(10);
                END IF;
            END $$;
        """)
        
        # Create DRC batch settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drc_batch_settings (
                id SERIAL PRIMARY KEY,
                batch_id VARCHAR(50) UNIQUE NOT NULL,
                s21_low_db REAL NOT NULL,
                drc1_percent REAL NOT NULL,
                s21_high_db REAL NOT NULL,
                drc2_percent REAL NOT NULL,
                slope_m REAL NOT NULL,
                intercept_b REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("  ✓ DRC batch settings table created")
        
        # Create trained models table for ML model management
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trained_models (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                model_type VARCHAR(50) NOT NULL,
                parameters JSONB NOT NULL,
                training_count INTEGER,
                rmse DOUBLE PRECISION,
                r_squared DOUBLE PRECISION,
                mae DOUBLE PRECISION,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT FALSE,
                notes TEXT
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trained_models_active 
            ON trained_models (is_active);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trained_models_created 
            ON trained_models (created_at DESC);
        """)
        print("  ✓ Trained models table created")
        
        # Create batch_weights table for storing weight data per batch
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_weights (
                slip_no VARCHAR(50) NOT NULL,
                sampling_no VARCHAR(50) NOT NULL,
                weight_gross NUMERIC(10, 2),
                weight_net NUMERIC(10, 2),
                factor NUMERIC(10, 2),
                drc_percent NUMERIC(10, 2),
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (slip_no, sampling_no)
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_weights_slip 
            ON batch_weights (slip_no);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_weights_sampling 
            ON batch_weights (sampling_no);
        """)
        print("  ✓ Batch weights table created")
        
        # Create batch_items table for storing product/item details per batch
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_items (
                id SERIAL PRIMARY KEY,
                slip_no VARCHAR(50) NOT NULL,
                sampling_no VARCHAR(50) NOT NULL,
                item_no INTEGER NOT NULL,
                product_code VARCHAR(100),
                product_name VARCHAR(255),
                quantity NUMERIC(10, 2),
                unit VARCHAR(50),
                unit_price NUMERIC(12, 2),
                total_price NUMERIC(12, 2),
                remarks TEXT,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (slip_no, sampling_no, item_no)
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_items_slip_sampling 
            ON batch_items (slip_no, sampling_no);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_items_product_code 
            ON batch_items (product_code);
        """)
        print("  ✓ Batch items table created")
        
        # Create batch_measurements table for grouping measurements by batch
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_measurements (
                id SERIAL PRIMARY KEY,
                slip_no VARCHAR(50) NOT NULL,
                batch_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                total_samples INTEGER DEFAULT 0,
                avg_drc NUMERIC(10, 2),
                avg_s21 NUMERIC(10, 2),
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (slip_no)
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_measurements_slip 
            ON batch_measurements (slip_no);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_measurements_timestamp 
            ON batch_measurements (batch_timestamp);
        """)
        print("  ✓ Batch measurements table created")
        
        # Create batch_measurement_samples table for individual samples
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_measurement_samples (
                id SERIAL PRIMARY KEY,
                batch_id INTEGER NOT NULL REFERENCES batch_measurements(id) ON DELETE CASCADE,
                slip_no VARCHAR(50) NOT NULL,
                sampling_no VARCHAR(50) NOT NULL,
                weight_gross NUMERIC(10, 2),
                weight_net NUMERIC(10, 2),
                factor NUMERIC(10, 2),
                drc_percent NUMERIC(10, 2),
                s21_avg NUMERIC(10, 2),
                measurement_timestamp TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (slip_no, sampling_no, measurement_timestamp)
            );
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_samples_batch_id 
            ON batch_measurement_samples (batch_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_samples_slip 
            ON batch_measurement_samples (slip_no);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_samples_timestamp 
            ON batch_measurement_samples (measurement_timestamp);
        """)
        print("  ✓ Batch measurement samples table created")
        
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
        
        # Get batch info from data (sent from frontend)
        slip_no = data.get('slip_no', '')
        sampling_no = data.get('sampling_no', '')
        test_no = data.get('test_no', 'Test01')
        
        # Generate batch_id for backward compatibility (optional)
        batch_id = f"{slip_no}_{sampling_no}_{test_no}" if slip_no and sampling_no else timestamp.strftime('%y%m%d%H%M%S')
        
        # Get latest DRC settings for calculation
        cursor.execute("""
            SELECT slope_m, intercept_b, drc1_percent, drc2_percent
            FROM drc_batch_settings
            ORDER BY created_at DESC
            LIMIT 1
        """)
        drc_settings = cursor.fetchone()
        
        # Calculate DRC percent
        drc_percent = None
        if drc_settings and data['summary'].get('s21_avg_db') is not None:
            slope_m, intercept_b, drc1_percent, drc2_percent = drc_settings
            drc_value = slope_m * data['summary']['s21_avg_db'] + intercept_b
            # Clamp to valid range
            min_drc = min(drc1_percent, drc2_percent)
            max_drc = max(drc1_percent, drc2_percent)
            drc_percent = max(min_drc, min(max_drc, drc_value))
        
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
                s21_point.get('imag'),
                batch_id,
                drc_percent,
                slip_no,
                sampling_no,
                test_no
            ))
        
        # Batch insert measurements
        execute_values(cursor, """
            INSERT INTO measurements 
            (time, sweep_count, frequency, s11_magnitude, s11_db, s11_phase, 
             s11_real, s11_imag, s21_magnitude, s21_db, s21_phase, s21_real, s21_imag,
             batch_id, drc_percent, slip_no, sampling_no, test_no)
            VALUES %s
        """, measurement_rows)
        
        # Insert summary
        cursor.execute("""
            INSERT INTO measurement_summary 
            (time, sweep_count, s11_rms, s11_max, s11_min, s21_rms, s21_max, s21_min, signal_quality, batch_id, slip_no, sampling_no, test_no)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            timestamp,
            data['sweep_count'],
            data['summary']['avg_db'],
            data['summary']['max_db'],
            data['summary']['min_db'],
            data['summary']['s21_avg_db'],
            data['summary']['s21_max_db'],
            data['summary']['s21_min_db'],
            data['connection_status']['signal_quality'],
            batch_id,
            slip_no,
            sampling_no,
            test_no
        ))
        
        db_conn.commit()
        cursor.close()
        
        # Update last saved info
        last_saved_data = {
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'sweep_count': data['sweep_count'],
            's11_rms': data['summary']['avg_db'],
            's21_rms': data['summary']['s21_avg_db'],
            'batch_id': batch_id,
            'slip_no': slip_no,
            'sampling_no': sampling_no,
            'test_no': test_no,
            'drc_percent': drc_percent
        }
        
        # Create message based on whether DRC was calculated
        if drc_percent is not None:
            message = f'Saved: {slip_no}/{sampling_no}/{test_no} - DRC: {drc_percent:.2f}%'
        else:
            message = f'Saved: {slip_no}/{sampling_no}/{test_no} (No DRC model)'
        
        return {
            'success': True,
            'message': message,
            'last_saved': last_saved_data,
            'batch_id': batch_id,
            'slip_no': slip_no,
            'sampling_no': sampling_no,
            'test_no': test_no,
            'drc_percent': drc_percent
        }
        
    except Exception as e:
        print(f"Save error: {e}")
        if db_conn:
            db_conn.rollback()
        return {'success': False, 'message': f'Save error: {str(e)}'}


def get_available_ports():
    """Get list of available COM ports"""
    ports = []
    try:
        for port in serial.tools.list_ports.comports():
            ports.append({
                'port': port.device,
                'description': port.description,
                'hwid': port.hwid
            })
    except Exception as e:
        print(f"Error scanning ports: {e}")
        # Return empty list if scanning fails
        ports = []
    
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
            
            debug_print(f"\n[S11 Response - {timestamp}] - {len(lines_s11)} points")
            if len(lines_s11) >= 3:
                debug_print(f"  S11 Raw[0]: {lines_s11[0]}")
                debug_print(f"  S11 Raw[1]: {lines_s11[1]}")
                debug_print(f"  S11 Raw[2]: {lines_s11[2]}")
            
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
            
            debug_print(f"[S21 Response - {timestamp}] - {len(lines_s21)} points")
            if len(lines_s21) >= 3:
                debug_print(f"  S21 Raw[0]: {lines_s21[0]}")
                debug_print(f"  S21 Raw[1]: {lines_s21[1]}")
                debug_print(f"  S21 Raw[2]: {lines_s21[2]}")
            
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
                debug_print(f"\n✓ อ่านค่าได้สำเร็จ - Sweep #{sweep_count} [{timestamp}]")
                debug_print(f"  S11: {len(s11_data)}/{POINTS} points | S21: {len(s21_data)}/{POINTS} points")
                debug_print(f"  Signal Quality: {signal_quality:.1f}%")
                debug_print(f"  S11 dB: Min={min(d['db'] for d in s11_data):.2f}, Max={max(d['db'] for d in s11_data):.2f}, RMS={calculate_rms(s11_data):.2f}")
                
                if s21_data:
                    debug_print(f"  S21 dB: Min={min(d['db'] for d in s21_data):.2f}, Max={max(d['db'] for d in s21_data):.2f}, RMS={calculate_rms(s21_data):.2f}")
                    
                    # ตรวจสอบว่าข้อมูล S21 ต่างจาก S11 หรือไม่
                    s11_first_3 = [(s11_data[i]['real'], s11_data[i]['imag']) for i in range(min(3, len(s11_data)))]
                    s21_first_3 = [(s21_data[i]['real'], s21_data[i]['imag']) for i in range(min(3, len(s21_data)))]
                    
                    if s11_first_3 == s21_first_3:
                        debug_print(f"  ⚠ WARNING: S21 data identical to S11! Data may be incorrect!")
                    else:
                        debug_print(f"  ✓ S21 data verified different from S11")
                    
                    if DEBUG_MODE:
                        debug_print(f"\n  === Data Comparison (First 3 points) ===")
                        debug_print(f"  S11[0]: Real={s11_data[0]['real']:.6f}, Imag={s11_data[0]['imag']:.6f}, dB={s11_data[0]['db']:.2f}")
                        debug_print(f"  S21[0]: Real={s21_data[0]['real']:.6f}, Imag={s21_data[0]['imag']:.6f}, dB={s21_data[0]['db']:.2f}")
                        debug_print(f"  S11[1]: Real={s11_data[1]['real']:.6f}, Imag={s11_data[1]['imag']:.6f}, dB={s11_data[1]['db']:.2f}")
                        debug_print(f"  S21[1]: Real={s21_data[1]['real']:.6f}, Imag={s21_data[1]['imag']:.6f}, dB={s21_data[1]['db']:.2f}")
                        debug_print(f"  S11[2]: Real={s11_data[2]['real']:.6f}, Imag={s11_data[2]['imag']:.6f}, dB={s11_data[2]['db']:.2f}")
                        debug_print(f"  S21[2]: Real={s21_data[2]['real']:.6f}, Imag={s21_data[2]['imag']:.6f}, dB={s21_data[2]['db']:.2f}")
                    # Show first 5 and last 5 data points
                    if DEBUG_MODE:
                        debug_print(f"  First 5 points:")
                        for i in range(min(5, len(s21_data))):
                            d = s21_data[i]
                            debug_print(f"    [{i}] Freq: {d['frequency']:.4f} GHz, dB: {d['db']:.2f}, Phase: {d['phase']:.2f}°")
                        if len(s21_data) > 10:
                            debug_print(f"  ...")
                        if len(s21_data) > 5:
                            debug_print(f"  Last 5 points:")
                            for i in range(max(0, len(s21_data)-5), len(s21_data)):
                                d = s21_data[i]
                                debug_print(f"    [{i}] Freq: {d['frequency']:.4f} GHz, dB: {d['db']:.2f}, Phase: {d['phase']:.2f}°")
                
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


@app.route('/favicon.ico')
def favicon():
    """Return 204 No Content for favicon requests"""
    return '', 204


@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Shutdown server gracefully (for pywebview)"""
    print("Shutdown request received")
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        # For production servers, signal to stop
        import os
        import signal
        os.kill(os.getpid(), signal.SIGTERM)
    else:
        func()
    return 'Server shutting down...'


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    global active_clients, last_activity_time
    active_clients += 1
    last_activity_time = time.time()
    
    print(f'Client connected (Total clients: {active_clients})')
    emit('status', {
        'message': 'Connected to server',
        'sweep_count': sweep_count,
        'connection_status': connection_status
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    global active_clients, last_activity_time
    active_clients -= 1
    last_activity_time = time.time()
    
    print(f'Client disconnected (Remaining clients: {active_clients})')
    
    # In headless mode, start idle timer when no clients
    if HEADLESS_MODE and active_clients <= 0:
        print(f'⏱ No active clients. Server will shutdown in {IDLE_TIMEOUT} seconds if no new connections...')



@socketio.on('scan_ports')
def handle_scan_ports():
    """Scan for available COM ports"""
    print("Scanning for COM ports...")
    try:
        ports = get_available_ports()
        print(f"Found {len(ports)} ports: {[p['port'] for p in ports]}")
        emit('ports_list', {'ports': ports, 'success': True})
    except Exception as e:
        print(f"Error in handle_scan_ports: {e}")
        emit('ports_list', {'ports': [], 'success': False, 'error': str(e)})


@socketio.on('test_connection')
def handle_test_connection(data):
    """Test connection to specified port"""
    port = data.get('port', PORT)
    print(f"Testing connection to {port}...")
    
    try:
        test_ser = serial.Serial(port, BAUDRATE, timeout=2)
        time.sleep(0.5)
        test_ser.close()
        print(f"Connection to {port} successful")
        emit('connection_test', {
            'success': True,
            'port': port,
            'message': 'Connection successful'
        })
    except Exception as e:
        print(f"Connection to {port} failed: {e}")
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
    print(f"Received save_measurement request: {data.get('slip_no')}/{data.get('sampling_no')}/{data.get('test_no')}")
    result = save_measurement_to_db(data)
    print(f"Save result: {result.get('success')}, {result.get('message')}")
    emit('save_result', result)


@socketio.on('get_last_saved')
def handle_get_last_saved():
    """Get last saved measurement info"""
    emit('last_saved_info', last_saved_data)


@socketio.on('save_drc_settings')
def handle_save_drc_settings(data):
    """
    Save DRC batch settings with linear regression calculation
    
    Business Logic:
    - DRC% = slope_m * S21_RMS(dB) + intercept_b
    - slope_m = (DRC2% - DRC1%) / (S21_high_dB - S21_low_dB)
    - intercept_b = DRC1% - slope_m * S21_low_dB
    """
    if not DB_AVAILABLE or not db_conn:
        emit('drc_save_result', {
            'success': False,
            'message': 'Database not available'
        })
        return
    
    try:
        s21_low_db = float(data.get('s21_low_db'))
        drc1_percent = float(data.get('drc1_percent'))
        s21_high_db = float(data.get('s21_high_db'))
        drc2_percent = float(data.get('drc2_percent'))
        
        # Validation
        if s21_high_db == s21_low_db:
            emit('drc_save_result', {
                'success': False,
                'message': 'S21 High dB must be different from S21 Low dB'
            })
            return
        
        if not (0 <= drc1_percent <= 100) or not (0 <= drc2_percent <= 100):
            emit('drc_save_result', {
                'success': False,
                'message': 'DRC percentages must be between 0 and 100'
            })
            return
        
        # Calculate linear regression coefficients
        slope_m = (drc2_percent - drc1_percent) / (s21_high_db - s21_low_db)
        intercept_b = drc1_percent - slope_m * s21_low_db
        
        cursor = db_conn.cursor()
        
        # Auto-generate batch_id using timestamp (yymmddhhmmss)
        from datetime import datetime
        batch_id = datetime.now().strftime('%y%m%d%H%M%S')
        
        # Insert DRC settings (no conflict handling, always new record)
        cursor.execute("""
            INSERT INTO drc_batch_settings 
            (batch_id, s21_low_db, drc1_percent, s21_high_db, drc2_percent, slope_m, intercept_b)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """, (batch_id, s21_low_db, drc1_percent, s21_high_db, drc2_percent, slope_m, intercept_b))
        
        result = cursor.fetchone()
        db_conn.commit()
        cursor.close()
        
        emit('drc_save_result', {
            'success': True,
            'message': f'DRC settings saved successfully for {batch_id}',
            'batch_id': batch_id,
            's21_low_db': s21_low_db,
            'drc1_percent': drc1_percent,
            's21_high_db': s21_high_db,
            'drc2_percent': drc2_percent,
            'slope_m': round(slope_m, 6),
            'intercept_b': round(intercept_b, 6),
            'created_at': result[1].isoformat() if result else None
        })
        
    except Exception as e:
        db_conn.rollback()
        print(f"DRC save error: {e}")
        import traceback
        traceback.print_exc()
        emit('drc_save_result', {
            'success': False,
            'message': f'Error saving DRC settings: {str(e)}'
        })


@socketio.on('get_drc_settings')
def handle_get_drc_settings(data):
    """Get DRC settings for a specific batch or latest"""
    if not DB_AVAILABLE or not db_conn:
        emit('drc_settings_result', {
            'success': False,
            'message': 'Database not available'
        })
        return
    
    try:
        cursor = db_conn.cursor()
        batch_id = data.get('batch_id') if data else None
        
        if batch_id:
            # Get specific batch
            cursor.execute("""
                SELECT batch_id, s21_low_db, drc1_percent, s21_high_db, drc2_percent, 
                       slope_m, intercept_b, created_at
                FROM drc_batch_settings
                WHERE batch_id = %s
            """, (batch_id,))
        else:
            # Get latest batch
            cursor.execute("""
                SELECT batch_id, s21_low_db, drc1_percent, s21_high_db, drc2_percent, 
                       slope_m, intercept_b, created_at
                FROM drc_batch_settings
                ORDER BY created_at DESC
                LIMIT 1
            """)
        
        row = cursor.fetchone()
        cursor.close()
        
        if row:
            emit('drc_settings_result', {
                'success': True,
                'settings': {
                    'batch_id': row[0],
                    's21_low_db': row[1],
                    'drc1_percent': row[2],
                    's21_high_db': row[3],
                    'drc2_percent': row[4],
                    'slope_m': row[5],
                    'intercept_b': row[6],
                    'created_at': row[7].isoformat()
                }
            })
        else:
            emit('drc_settings_result', {
                'success': False,
                'message': 'No DRC settings found'
            })
        
    except Exception as e:
        print(f"DRC get error: {e}")
        import traceback
        traceback.print_exc()
        emit('drc_settings_result', {
            'success': False,
            'message': f'Error retrieving DRC settings: {str(e)}'
        })


@socketio.on('calculate_drc')
def handle_calculate_drc(data):
    """
    Calculate DRC percentage from S21 RMS using stored settings
    
    Formula: DRC% = slope_m * S21_RMS(dB) + intercept_b
    Clamped to DRC1-DRC2 range
    """
    try:
        s21_rms_db = float(data.get('s21_rms_db'))
        slope_m = float(data.get('slope_m'))
        intercept_b = float(data.get('intercept_b'))
        drc1_percent = float(data.get('drc1_percent', 0))
        drc2_percent = float(data.get('drc2_percent', 100))
        
        # Calculate DRC
        drc_percent = slope_m * s21_rms_db + intercept_b
        
        # Clamp to valid range
        min_drc = min(drc1_percent, drc2_percent)
        max_drc = max(drc1_percent, drc2_percent)
        drc_percent = max(min_drc, min(max_drc, drc_percent))
        
        emit('drc_calculation_result', {
            'success': True,
            'drc_percent': round(drc_percent, 2),
            's21_rms_db': round(s21_rms_db, 2)
        })
        
    except Exception as e:
        print(f"DRC calculation error: {e}")
        emit('drc_calculation_result', {
            'success': False,
            'message': f'Error calculating DRC: {str(e)}'
        })


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
                ms.time,
                ms.sweep_count,
                ms.s11_rms,
                ms.s11_min,
                ms.s11_max,
                ms.s21_rms,
                ms.s21_min,
                ms.s21_max,
                ms.batch_id,
                ms.slip_no,
                ms.sampling_no,
                ms.test_no,
                array_agg(m.s11_db ORDER BY m.frequency) as s11_data,
                array_agg(m.s21_db ORDER BY m.frequency) as s21_data
            FROM measurement_summary ms
            LEFT JOIN measurements m ON 
                ms.time = m.time 
                AND ms.sweep_count = m.sweep_count 
                AND COALESCE(ms.batch_id, '') = COALESCE(m.batch_id, '')
                AND COALESCE(ms.slip_no, '') = COALESCE(m.slip_no, '')
                AND COALESCE(ms.sampling_no, '') = COALESCE(m.sampling_no, '')
                AND COALESCE(ms.test_no, '') = COALESCE(m.test_no, '')
        """
        
        conditions = []
        query_params = []
        
        if start_date:
            conditions.append("ms.time >= %s")
            query_params.append(start_date)
        
        if end_date:
            conditions.append("ms.time <= %s")
            query_params.append(end_date)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " GROUP BY ms.time, ms.sweep_count, ms.s11_rms, ms.s11_min, ms.s11_max, ms.s21_rms, ms.s21_min, ms.s21_max, ms.batch_id, ms.slip_no, ms.sampling_no, ms.test_no"
        query += " ORDER BY ms.time DESC LIMIT %s"
        query_params.append(limit)
        
        cursor.execute(query, query_params)
        rows = cursor.fetchall()
        
        # Get latest DRC settings for calculation
        cursor.execute("""
            SELECT slope_m, intercept_b, drc1_percent, drc2_percent
            FROM drc_batch_settings
            ORDER BY created_at DESC
            LIMIT 1
        """)
        drc_settings = cursor.fetchone()
        
        # Format results
        results = []
        for row in rows:
            result_row = {
                'timestamp': row[0].isoformat(),
                'sweep_count': row[1],
                's11_rms': round(row[2], 2),
                's11_min': round(row[3], 2),
                's11_max': round(row[4], 2),
                's21_rms': round(row[5], 2),
                's21_min': round(row[6], 2),
                's21_max': round(row[7], 2),
                'batch_id': row[8] if row[8] else 'N/A',
                'slip_no': row[9] if row[9] else 'N/A',
                'sampling_no': row[10] if row[10] else 'N/A',
                'test_no': row[11] if row[11] else 'N/A',
                's11_data': [round(v, 2) for v in row[12]] if row[12] else [],
                's21_data': [round(v, 2) for v in row[13]] if row[13] else []
            }
            
            # Calculate DRC if settings available
            if drc_settings and row[5] is not None:
                slope_m, intercept_b, drc1_percent, drc2_percent = drc_settings
                drc_value = slope_m * row[5] + intercept_b
                # Clamp to valid range
                min_drc = min(drc1_percent, drc2_percent)
                max_drc = max(drc1_percent, drc2_percent)
                drc_value = max(min_drc, min(max_drc, drc_value))
                result_row['drc_percent'] = round(drc_value, 2)
            else:
                result_row['drc_percent'] = None
            
            results.append(result_row)
        
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


@socketio.on('query_data_view')
def handle_query_data_view(params):
    """Query saved measurements with summary info"""
    if not DB_AVAILABLE or not db_conn:
        emit('data_view_result', {
            'success': False,
            'message': 'Database not available. Please configure PostgreSQL/TimescaleDB.'
        })
        return
    
    try:
        cursor = db_conn.cursor()
        
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        slip_no = params.get('slip_no')
        sampling_no = params.get('sampling_no')
        test_no = params.get('test_no')
        limit = params.get('limit', 50)
        
        # Build query for summary data
        query = """
            SELECT 
                time,
                batch_id,
                s11_rms,
                s21_rms,
                signal_quality,
                slip_no,
                sampling_no,
                test_no
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
        
        if slip_no:
            conditions.append("slip_no = %s")
            query_params.append(slip_no)
        
        if sampling_no:
            conditions.append("sampling_no = %s")
            query_params.append(sampling_no)
        
        if test_no:
            conditions.append("test_no = %s")
            query_params.append(test_no)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY time DESC LIMIT %s"
        query_params.append(limit)
        
        cursor.execute(query, query_params)
        rows = cursor.fetchall()
        
        # Get latest DRC settings for calculation
        cursor.execute("""
            SELECT slope_m, intercept_b, drc1_percent, drc2_percent
            FROM drc_batch_settings
            ORDER BY created_at DESC
            LIMIT 1
        """)
        drc_settings = cursor.fetchone()
        
        # Format results
        results = []
        for row in rows:
            result_row = {
                'timestamp': row[0].isoformat(),
                'batch_id': row[1] if row[1] else 'N/A',
                's11_rms': round(row[2], 2),
                's21_rms': round(row[3], 2),
                'signal_quality': round(row[4], 2) if row[4] else 0,
                'slip_no': row[5] if row[5] else 'N/A',
                'sampling_no': row[6] if row[6] else 'N/A',
                'test_no': row[7] if row[7] else 'N/A'
            }
            
            # Calculate DRC if settings available
            if drc_settings and row[3] is not None:
                slope_m, intercept_b, drc1_percent, drc2_percent = drc_settings
                drc_value = slope_m * row[3] + intercept_b
                # Clamp to valid range
                min_drc = min(drc1_percent, drc2_percent)
                max_drc = max(drc1_percent, drc2_percent)
                drc_value = max(min_drc, min(max_drc, drc_value))
                result_row['drc_percent'] = round(drc_value, 2)
            else:
                result_row['drc_percent'] = None
            
            results.append(result_row)
        
        cursor.close()
        
        emit('data_view_result', {
            'success': True,
            'data': results,
            'count': len(results)
        })
        
    except Exception as e:
        print(f"Data view query error: {e}")
        import traceback
        traceback.print_exc()
        emit('data_view_result', {
            'success': False,
            'message': f'Query error: {str(e)}'
        })


@socketio.on('get_measurement_details')
def handle_get_measurement_details(params):
    """Get all 101 data points for a specific measurement"""
    if not DB_AVAILABLE or not db_conn:
        emit('measurement_details_result', {
            'success': False,
            'message': 'Database not available'
        })
        return
    
    try:
        cursor = db_conn.cursor()
        timestamp = params.get('timestamp')
        
        # Get all 101 points
        cursor.execute("""
            SELECT 
                frequency,
                s11_db,
                s11_phase,
                s11_real,
                s11_imag,
                s21_db,
                s21_phase,
                s21_real,
                s21_imag,
                batch_id,
                drc_percent
            FROM measurements
            WHERE time = %s
            ORDER BY frequency ASC
        """, (timestamp,))
        
        rows = cursor.fetchall()
        cursor.close()
        
        if rows:
            # Format results
            data_points = []
            batch_id = rows[0][9] if rows[0][9] else 'N/A'
            drc_percent = rows[0][10]
            
            for row in rows:
                data_points.append({
                    'frequency': round(row[0], 4),
                    's11_db': round(row[1], 2),
                    's11_phase': round(row[2], 2),
                    's11_real': round(row[3], 6),
                    's11_imag': round(row[4], 6),
                    's21_db': round(row[5], 2) if row[5] else None,
                    's21_phase': round(row[6], 2) if row[6] else None,
                    's21_real': round(row[7], 6) if row[7] else None,
                    's21_imag': round(row[8], 6) if row[8] else None
                })
            
            emit('measurement_details_result', {
                'success': True,
                'data': data_points,
                'batch_id': batch_id,
                'drc_percent': round(drc_percent, 2) if drc_percent else None,
                'count': len(data_points)
            })
        else:
            emit('measurement_details_result', {
                'success': False,
                'message': 'No data found for this timestamp'
            })
            
    except Exception as e:
        print(f"Get measurement details error: {e}")
        import traceback
        traceback.print_exc()
        emit('measurement_details_result', {
            'success': False,
            'message': f'Error: {str(e)}'
        })


# ==================== Batch Data Management for Analysis ====================

@socketio.on('search_batch_data')
def handle_search_batch_data(params):
    """Search batch data by Slip No. and Sampling No."""
    if not DB_AVAILABLE or not db_conn:
        emit('batch_search_result', {
            'success': False,
            'message': 'Database not available'
        })
        return
    
    try:
        cursor = db_conn.cursor()
        slip_no = params.get('slip_no', '').strip()
        sampling_no = params.get('sampling_no', '').strip()
        
        # Build query - JOIN with batch_weights to get weight data
        query = """
            SELECT DISTINCT
                ms.slip_no,
                ms.sampling_no,
                ms.test_no,
                bw.weight_gross,
                bw.weight_net,
                bw.factor,
                bw.drc_percent,
                ms.s21_rms,
                ms.time,
                ms.batch_id
            FROM measurement_summary ms
            LEFT JOIN batch_weights bw ON ms.slip_no = bw.slip_no AND ms.sampling_no = bw.sampling_no
            WHERE ms.slip_no IS NOT NULL AND ms.sampling_no IS NOT NULL
        """
        params_list = []
        
        if slip_no:
            query += " AND ms.slip_no = %s"
            params_list.append(slip_no)
        if sampling_no:
            query += " AND ms.sampling_no = %s"
            params_list.append(sampling_no)
        
        query += " ORDER BY ms.time DESC LIMIT 100"
        
        cursor.execute(query, params_list)
        rows = cursor.fetchall()
        cursor.close()
        
        results = []
        for row in rows:
            # Calculate DRC if missing but weight data available
            calculated_drc = None
            if row[3] and row[4] and row[5]:  # weight_gross, weight_net, factor
                try:
                    calculated_drc = round((row[4] * row[5]) / row[3] * 100, 1)
                except:
                    calculated_drc = None
            
            results.append({
                'slip_no': row[0],
                'sampling_no': row[1],
                'test_no': row[2],
                'weight_gross': float(row[3]) if row[3] else None,
                'weight_net': float(row[4]) if row[4] else None,
                'factor': float(row[5]) if row[5] else None,
                'drc_percent': float(row[6]) if row[6] else calculated_drc,
                's21_avg': round(row[7], 2) if row[7] else None,
                'timestamp': row[8].isoformat() if row[8] else None,
                'batch_id': row[9],
                'is_complete': bool(row[3] and row[4] and row[5])
            })
        
        emit('batch_search_result', {
            'success': True,
            'data': results,
            'count': len(results)
        })
        
    except Exception as e:
        print(f"Batch search error: {e}")
        import traceback
        traceback.print_exc()
        emit('batch_search_result', {
            'success': False,
            'message': f'Search error: {str(e)}'
        })


@socketio.on('load_all_batch_data')
def handle_load_all_batch_data(params):
    """Load all batch data from database"""
    if not DB_AVAILABLE or not db_conn:
        emit('batch_load_result', {
            'success': False,
            'message': 'Database not available'
        })
        return
    
    try:
        cursor = db_conn.cursor()
        limit = params.get('limit', 200)
        
        query = """
            SELECT DISTINCT
                ms.slip_no,
                ms.sampling_no,
                ms.test_no,
                bw.weight_gross,
                bw.weight_net,
                bw.factor,
                bw.drc_percent,
                ms.s21_rms,
                ms.time,
                ms.batch_id
            FROM measurement_summary ms
            LEFT JOIN batch_weights bw ON ms.slip_no = bw.slip_no AND ms.sampling_no = bw.sampling_no
            WHERE ms.slip_no IS NOT NULL AND ms.sampling_no IS NOT NULL
            ORDER BY ms.time DESC
            LIMIT %s
        """
        
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        cursor.close()
        
        results = []
        for row in rows:
            # Calculate DRC if missing but weight data available
            calculated_drc = None
            if row[3] and row[4] and row[5]:  # weight_gross, weight_net, factor
                try:
                    calculated_drc = round((row[4] * row[5]) / row[3] * 100, 1)
                except:
                    calculated_drc = None
            
            results.append({
                'slip_no': row[0],
                'sampling_no': row[1],
                'test_no': row[2],
                'weight_gross': float(row[3]) if row[3] else None,
                'weight_net': float(row[4]) if row[4] else None,
                'factor': float(row[5]) if row[5] else None,
                'drc_percent': float(row[6]) if row[6] else calculated_drc,
                's21_avg': round(row[7], 2) if row[7] else None,
                'timestamp': row[8].isoformat() if row[8] else None,
                'batch_id': row[9],
                'is_complete': bool(row[3] and row[4] and row[5])
            })
        
        emit('batch_load_result', {
            'success': True,
            'data': results,
            'count': len(results)
        })
        
    except Exception as e:
        print(f"Batch load error: {e}")
        import traceback
        traceback.print_exc()
        emit('batch_load_result', {
            'success': False,
            'message': f'Load error: {str(e)}'
        })


@socketio.on('update_batch_data')
def handle_update_batch_data(params):
    """Update weight data for a batch (applies to both Test01 and Test02)"""
    if not DB_AVAILABLE or not db_conn:
        emit('batch_update_result', {
            'success': False,
            'message': 'Database not available'
        })
        return
    
    try:
        slip_no = params.get('slip_no')
        sampling_no = params.get('sampling_no')
        weight_gross = params.get('weight_gross')
        weight_net = params.get('weight_net')
        factor = params.get('factor')
        
        if not slip_no or not sampling_no:
            emit('batch_update_result', {
                'success': False,
                'message': 'Slip No. and Sampling No. are required'
            })
            return
        
        # Calculate DRC
        drc_percent = None
        if weight_gross and weight_net and factor:
            try:
                drc_percent = round((weight_net * factor) / weight_gross * 100, 1)
            except:
                pass
        
        cursor = db_conn.cursor()
        
        # Insert or update batch_weights table (one row per batch)
        # This is the primary storage for weight data
        cursor.execute("""
            INSERT INTO batch_weights (slip_no, sampling_no, weight_gross, weight_net, factor, drc_percent, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (slip_no, sampling_no) 
            DO UPDATE SET
                weight_gross = EXCLUDED.weight_gross,
                weight_net = EXCLUDED.weight_net,
                factor = EXCLUDED.factor,
                drc_percent = EXCLUDED.drc_percent,
                updated_at = CURRENT_TIMESTAMP
        """, (slip_no, sampling_no, weight_gross, weight_net, factor, drc_percent))
        
        batch_weights_updated = 1  # Always 1 because it's upsert
        
        # Also update measurement_summary for backward compatibility
        # (both Test01 and Test02 records get updated)
        cursor.execute("""
            UPDATE measurement_summary
            SET weight_gross = %s,
                weight_net = %s,
                factor = %s,
                drc_percent = %s
            WHERE slip_no = %s AND sampling_no = %s
        """, (weight_gross, weight_net, factor, drc_percent, slip_no, sampling_no))
        
        summary_updated = cursor.rowcount
        
        # Also update measurements table for backward compatibility
        cursor.execute("""
            UPDATE measurements
            SET weight_gross = %s,
                weight_net = %s,
                factor = %s,
                drc_percent = %s
            WHERE slip_no = %s AND sampling_no = %s
        """, (weight_gross, weight_net, factor, drc_percent, slip_no, sampling_no))
        
        measurements_updated = cursor.rowcount
        
        db_conn.commit()
        cursor.close()
        
        emit('batch_update_result', {
            'success': True,
            'message': f'Saved batch weight data (1 row per batch)',
            'drc_percent': drc_percent,
            'records_updated': {
                'batch_weights': batch_weights_updated,
                'summary': summary_updated,
                'measurements': measurements_updated
            }
        })
        
    except Exception as e:
        db_conn.rollback()
        print(f"Batch update error: {e}")
        import traceback
        traceback.print_exc()
        emit('batch_update_result', {
            'success': False,
            'message': f'Update error: {str(e)}'
        })


# ==================== Batch Items Management ====================

@socketio.on('save_batch_items')
def handle_save_batch_items(data):
    """Save product/item details for a batch"""
    if not DB_AVAILABLE or not db_conn:
        emit('batch_items_result', {
            'success': False,
            'message': 'Database not available'
        })
        return
    
    try:
        slip_no = data.get('slip_no')
        sampling_no = data.get('sampling_no')
        items = data.get('items', [])
        
        if not slip_no or not sampling_no:
            emit('batch_items_result', {
                'success': False,
                'message': 'Slip No. and Sampling No. are required'
            })
            return
        
        cursor = db_conn.cursor()
        
        # Delete existing items for this batch
        cursor.execute("""
            DELETE FROM batch_items 
            WHERE slip_no = %s AND sampling_no = %s
        """, (slip_no, sampling_no))
        
        # Insert new items
        items_saved = 0
        for idx, item in enumerate(items, start=1):
            cursor.execute("""
                INSERT INTO batch_items 
                (slip_no, sampling_no, item_no, product_code, product_name, 
                 quantity, unit, unit_price, total_price, remarks)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                slip_no, 
                sampling_no, 
                idx,
                item.get('product_code'),
                item.get('product_name'),
                item.get('quantity'),
                item.get('unit'),
                item.get('unit_price'),
                item.get('total_price'),
                item.get('remarks')
            ))
            items_saved += 1
        
        db_conn.commit()
        cursor.close()
        
        emit('batch_items_result', {
            'success': True,
            'message': f'Saved {items_saved} items',
            'items_saved': items_saved
        })
        
    except Exception as e:
        db_conn.rollback()
        print(f"Save batch items error: {e}")
        import traceback
        traceback.print_exc()
        emit('batch_items_result', {
            'success': False,
            'message': f'Save error: {str(e)}'
        })


@socketio.on('save_batch_measurement')
def handle_save_batch_measurement(data):
    """Save batch measurement with samples (grouped by slip_no)"""
    if not DB_AVAILABLE or not db_conn:
        emit('batch_measurement_result', {
            'success': False,
            'message': 'Database not available'
        })
        return
    
    try:
        slip_no = data.get('slip_no')
        samples = data.get('samples', [])
        
        if not slip_no:
            emit('batch_measurement_result', {
                'success': False,
                'message': 'Slip No. is required'
            })
            return
        
        if not samples or len(samples) == 0:
            emit('batch_measurement_result', {
                'success': False,
                'message': 'At least one sample is required'
            })
            return
        
        cursor = db_conn.cursor()
        
        # Calculate averages
        valid_drc = [s.get('drc_percent') for s in samples if s.get('drc_percent') is not None]
        valid_s21 = [s.get('s21_avg') for s in samples if s.get('s21_avg') is not None]
        
        avg_drc = sum(valid_drc) / len(valid_drc) if valid_drc else None
        avg_s21 = sum(valid_s21) / len(valid_s21) if valid_s21 else None
        
        # Insert or update batch_measurements
        cursor.execute("""
            INSERT INTO batch_measurements 
            (slip_no, total_samples, avg_drc, avg_s21, batch_timestamp, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (slip_no) 
            DO UPDATE SET 
                total_samples = EXCLUDED.total_samples,
                avg_drc = EXCLUDED.avg_drc,
                avg_s21 = EXCLUDED.avg_s21,
                batch_timestamp = EXCLUDED.batch_timestamp,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """, (slip_no, len(samples), avg_drc, avg_s21))
        
        batch_id = cursor.fetchone()[0]
        
        # Delete existing samples for this batch
        cursor.execute("""
            DELETE FROM batch_measurement_samples 
            WHERE batch_id = %s
        """, (batch_id,))
        
        # Insert new samples
        samples_saved = 0
        for sample in samples:
            cursor.execute("""
                INSERT INTO batch_measurement_samples 
                (batch_id, slip_no, sampling_no, weight_gross, weight_net, 
                 factor, drc_percent, s21_avg, measurement_timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                batch_id,
                slip_no,
                sample.get('sampling_no'),
                sample.get('weight_gross'),
                sample.get('weight_net'),
                sample.get('factor'),
                sample.get('drc_percent'),
                sample.get('s21_avg'),
                sample.get('timestamp')
            ))
            samples_saved += 1
        
        db_conn.commit()
        cursor.close()
        
        emit('batch_measurement_result', {
            'success': True,
            'message': f'Saved batch {slip_no} with {samples_saved} samples',
            'batch_id': batch_id,
            'samples_saved': samples_saved,
            'avg_drc': float(avg_drc) if avg_drc else None,
            'avg_s21': float(avg_s21) if avg_s21 else None
        })
        
    except Exception as e:
        db_conn.rollback()
        print(f"Save batch measurement error: {e}")
        import traceback
        traceback.print_exc()
        emit('batch_measurement_result', {
            'success': False,
            'message': f'Save error: {str(e)}'
        })


@socketio.on('load_batch_measurement')
def handle_load_batch_measurement(params):
    """Load batch measurement with all samples"""
    if not DB_AVAILABLE or not db_conn:
        emit('batch_measurement_loaded', {
            'success': False,
            'message': 'Database not available'
        })
        return
    
    try:
        slip_no = params.get('slip_no')
        
        if not slip_no:
            emit('batch_measurement_loaded', {
                'success': False,
                'message': 'Slip No. is required'
            })
            return
        
        cursor = db_conn.cursor()
        
        # Get batch info
        cursor.execute("""
            SELECT 
                id, slip_no, batch_timestamp, total_samples, 
                avg_drc, avg_s21, created_at, updated_at
            FROM batch_measurements
            WHERE slip_no = %s
        """, (slip_no,))
        
        batch_row = cursor.fetchone()
        
        if not batch_row:
            emit('batch_measurement_loaded', {
                'success': False,
                'message': f'No batch found for slip_no: {slip_no}'
            })
            cursor.close()
            return
        
        batch_info = {
            'id': batch_row[0],
            'slip_no': batch_row[1],
            'batch_timestamp': batch_row[2].isoformat() if batch_row[2] else None,
            'total_samples': batch_row[3],
            'avg_drc': float(batch_row[4]) if batch_row[4] else None,
            'avg_s21': float(batch_row[5]) if batch_row[5] else None,
            'created_at': batch_row[6].isoformat() if batch_row[6] else None,
            'updated_at': batch_row[7].isoformat() if batch_row[7] else None
        }
        
        # Get samples
        cursor.execute("""
            SELECT 
                id, sampling_no, weight_gross, weight_net, factor,
                drc_percent, s21_avg, measurement_timestamp, created_at
            FROM batch_measurement_samples
            WHERE batch_id = %s
            ORDER BY measurement_timestamp ASC
        """, (batch_info['id'],))
        
        sample_rows = cursor.fetchall()
        cursor.close()
        
        samples = []
        for row in sample_rows:
            samples.append({
                'id': row[0],
                'sampling_no': row[1],
                'weight_gross': float(row[2]) if row[2] else None,
                'weight_net': float(row[3]) if row[3] else None,
                'factor': float(row[4]) if row[4] else None,
                'drc_percent': float(row[5]) if row[5] else None,
                's21_avg': float(row[6]) if row[6] else None,
                'measurement_timestamp': row[7].isoformat() if row[7] else None,
                'created_at': row[8].isoformat() if row[8] else None
            })
        
        emit('batch_measurement_loaded', {
            'success': True,
            'batch': batch_info,
            'samples': samples,
            'sample_count': len(samples)
        })
        
    except Exception as e:
        print(f"Load batch measurement error: {e}")
        import traceback
        traceback.print_exc()
        emit('batch_measurement_loaded', {
            'success': False,
            'message': f'Load error: {str(e)}'
        })


@socketio.on('query_batch_measurements')
def handle_query_batch_measurements(params):
    """Query batch measurements with pagination"""
    if not DB_AVAILABLE or not db_conn:
        emit('batch_measurements_result', {
            'success': False,
            'message': 'Database not available'
        })
        return
    
    try:
        limit = params.get('limit', 50)
        offset = params.get('offset', 0)
        
        cursor = db_conn.cursor()
        
        # Get batches with sample count
        cursor.execute("""
            SELECT 
                bm.id, bm.slip_no, bm.batch_timestamp, bm.total_samples,
                bm.avg_drc, bm.avg_s21, bm.created_at, bm.updated_at,
                COUNT(bms.id) as actual_sample_count
            FROM batch_measurements bm
            LEFT JOIN batch_measurement_samples bms ON bm.id = bms.batch_id
            GROUP BY bm.id, bm.slip_no, bm.batch_timestamp, bm.total_samples,
                     bm.avg_drc, bm.avg_s21, bm.created_at, bm.updated_at
            ORDER BY bm.batch_timestamp DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        
        rows = cursor.fetchall()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM batch_measurements")
        total_count = cursor.fetchone()[0]
        
        cursor.close()
        
        batches = []
        for row in rows:
            batches.append({
                'id': row[0],
                'slip_no': row[1],
                'batch_timestamp': row[2].isoformat() if row[2] else None,
                'total_samples': row[3],
                'avg_drc': float(row[4]) if row[4] else None,
                'avg_s21': float(row[5]) if row[5] else None,
                'created_at': row[6].isoformat() if row[6] else None,
                'updated_at': row[7].isoformat() if row[7] else None,
                'actual_sample_count': row[8]
            })
        
        emit('batch_measurements_result', {
            'success': True,
            'batches': batches,
            'total': total_count,
            'limit': limit,
            'offset': offset
        })
        
    except Exception as e:
        print(f"Query batch measurements error: {e}")
        import traceback
        traceback.print_exc()
        emit('batch_measurements_result', {
            'success': False,
            'message': f'Query error: {str(e)}'
        })


@socketio.on('load_batch_items')
def handle_load_batch_items(params):
    """Load product/item details for a batch"""
    if not DB_AVAILABLE or not db_conn:
        emit('batch_items_loaded', {
            'success': False,
            'message': 'Database not available'
        })
        return
    
    try:
        slip_no = params.get('slip_no')
        sampling_no = params.get('sampling_no')
        
        if not slip_no or not sampling_no:
            emit('batch_items_loaded', {
                'success': False,
                'message': 'Slip No. and Sampling No. are required'
            })
            return
        
        cursor = db_conn.cursor()
        
        cursor.execute("""
            SELECT 
                item_no, product_code, product_name, quantity, unit,
                unit_price, total_price, remarks, created_at
            FROM batch_items
            WHERE slip_no = %s AND sampling_no = %s
            ORDER BY item_no ASC
        """, (slip_no, sampling_no))
        
        rows = cursor.fetchall()
        cursor.close()
        
        items = []
        for row in rows:
            items.append({
                'item_no': row[0],
                'product_code': row[1],
                'product_name': row[2],
                'quantity': float(row[3]) if row[3] else None,
                'unit': row[4],
                'unit_price': float(row[5]) if row[5] else None,
                'total_price': float(row[6]) if row[6] else None,
                'remarks': row[7],
                'created_at': row[8].isoformat() if row[8] else None
            })
        
        emit('batch_items_loaded', {
            'success': True,
            'items': items,
            'count': len(items)
        })
        
    except Exception as e:
        print(f"Load batch items error: {e}")
        import traceback
        traceback.print_exc()
        emit('batch_items_loaded', {
            'success': False,
            'message': f'Load error: {str(e)}'
        })


@socketio.on('get_batch_with_items')
def handle_get_batch_with_items(params):
    """Get batch weight data with items in one query"""
    if not DB_AVAILABLE or not db_conn:
        emit('batch_with_items_result', {
            'success': False,
            'message': 'Database not available'
        })
        return
    
    try:
        slip_no = params.get('slip_no')
        sampling_no = params.get('sampling_no')
        
        if not slip_no or not sampling_no:
            emit('batch_with_items_result', {
                'success': False,
                'message': 'Slip No. and Sampling No. are required'
            })
            return
        
        cursor = db_conn.cursor()
        
        # Get batch weights
        cursor.execute("""
            SELECT weight_gross, weight_net, factor, drc_percent, updated_at
            FROM batch_weights
            WHERE slip_no = %s AND sampling_no = %s
        """, (slip_no, sampling_no))
        
        weight_row = cursor.fetchone()
        
        # Get items
        cursor.execute("""
            SELECT 
                item_no, product_code, product_name, quantity, unit,
                unit_price, total_price, remarks
            FROM batch_items
            WHERE slip_no = %s AND sampling_no = %s
            ORDER BY item_no ASC
        """, (slip_no, sampling_no))
        
        item_rows = cursor.fetchall()
        
        # Get measurement summary for S21 data
        cursor.execute("""
            SELECT s21_rms, time
            FROM measurement_summary
            WHERE slip_no = %s AND sampling_no = %s
            ORDER BY time DESC
            LIMIT 1
        """, (slip_no, sampling_no))
        
        summary_row = cursor.fetchone()
        cursor.close()
        
        # Format response
        batch_data = {
            'slip_no': slip_no,
            'sampling_no': sampling_no,
            'weight_gross': float(weight_row[0]) if weight_row and weight_row[0] else None,
            'weight_net': float(weight_row[1]) if weight_row and weight_row[1] else None,
            'factor': float(weight_row[2]) if weight_row and weight_row[2] else None,
            'drc_percent': float(weight_row[3]) if weight_row and weight_row[3] else None,
            's21_avg': float(summary_row[0]) if summary_row and summary_row[0] else None,
            'timestamp': summary_row[1].isoformat() if summary_row and summary_row[1] else None
        }
        
        items = []
        for row in item_rows:
            items.append({
                'item_no': row[0],
                'product_code': row[1],
                'product_name': row[2],
                'quantity': float(row[3]) if row[3] else None,
                'unit': row[4],
                'unit_price': float(row[5]) if row[5] else None,
                'total_price': float(row[6]) if row[6] else None,
                'remarks': row[7]
            })
        
        emit('batch_with_items_result', {
            'success': True,
            'batch': batch_data,
            'items': items
        })
        
    except Exception as e:
        print(f"Get batch with items error: {e}")
        import traceback
        traceback.print_exc()
        emit('batch_with_items_result', {
            'success': False,
            'message': f'Error: {str(e)}'
        })


@socketio.on('load_dataset')
def handle_load_dataset(params):
    """Load dataset from measurement_summary for Analysis page"""
    if not DB_AVAILABLE or not db_conn:
        emit('dataset_loaded', {
            'success': False,
            'message': 'Database not available'
        })
        return
    
    try:
        # Ensure clean transaction state
        db_conn.rollback()
        
        cursor = db_conn.cursor()
        mode = params.get('mode', 'complete')
        
        # Build query based on mode - using batch_weights JOIN with measurement_summary
        if mode == 'complete':
            # Load only records with all required fields
            query = """
                SELECT DISTINCT
                    bw.slip_no,
                    bw.sampling_no,
                    bw.weight_gross,
                    bw.weight_net,
                    bw.factor,
                    bw.drc_percent,
                    ms.s21_rms as s21_avg,
                    ms.time as timestamp
                FROM batch_weights bw
                INNER JOIN measurement_summary ms ON bw.slip_no = ms.slip_no AND bw.sampling_no = ms.sampling_no
                WHERE bw.weight_gross IS NOT NULL 
                  AND bw.weight_net IS NOT NULL 
                  AND bw.factor IS NOT NULL
                  AND bw.drc_percent IS NOT NULL
                  AND ms.s21_rms IS NOT NULL
                ORDER BY ms.time DESC
                LIMIT 200
            """
        elif mode == 'for_input':
            # Load records with S21 data but missing weight fields
            query = """
                SELECT DISTINCT
                    ms.slip_no,
                    ms.sampling_no,
                    bw.weight_gross,
                    bw.weight_net,
                    bw.factor,
                    bw.drc_percent,
                    ms.s21_rms as s21_avg,
                    ms.time as timestamp
                FROM measurement_summary ms
                LEFT JOIN batch_weights bw ON ms.slip_no = bw.slip_no AND ms.sampling_no = bw.sampling_no
                WHERE ms.s21_rms IS NOT NULL
                  AND ms.slip_no IS NOT NULL
                  AND ms.sampling_no IS NOT NULL
                  AND (bw.weight_gross IS NULL OR bw.weight_net IS NULL OR bw.factor IS NULL)
                ORDER BY ms.time DESC
                LIMIT 200
            """
        else:  # all
            query = """
                SELECT DISTINCT
                    COALESCE(bw.slip_no, ms.slip_no) as slip_no,
                    COALESCE(bw.sampling_no, ms.sampling_no) as sampling_no,
                    bw.weight_gross,
                    bw.weight_net,
                    bw.factor,
                    bw.drc_percent,
                    ms.s21_rms as s21_avg,
                    ms.time as timestamp
                FROM measurement_summary ms
                FULL OUTER JOIN batch_weights bw ON ms.slip_no = bw.slip_no AND ms.sampling_no = bw.sampling_no
                WHERE COALESCE(bw.slip_no, ms.slip_no) IS NOT NULL
                  AND COALESCE(bw.sampling_no, ms.sampling_no) IS NOT NULL
                ORDER BY ms.time DESC NULLS LAST
                LIMIT 200
            """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        
        # Format results
        records = []
        for row in rows:
            # Calculate DRC if missing but weight data available
            drc_calc = None
            if row[2] and row[3] and row[4]:  # weight_gross, weight_net, factor
                try:
                    drc_calc = round((row[3] * row[4]) / row[2] * 100, 1)
                except:
                    drc_calc = None
            
            records.append({
                'slip_no': row[0],
                'sampling_no': row[1],
                'weight_gross': float(row[2]) if row[2] else None,
                'weight_net': float(row[3]) if row[3] else None,
                'factor': float(row[4]) if row[4] else None,
                'drc_percent': float(row[5]) if row[5] else drc_calc,
                's21_avg': round(row[6], 2) if row[6] else None,
                'timestamp': row[7].isoformat() if row[7] else None
            })
        
        emit('dataset_loaded', {
            'success': True,
            'records': records,
            'count': len(records),
            'mode': mode
        })
        
    except Exception as e:
        db_conn.rollback()
        print(f"Load dataset error: {e}")
        import traceback
        traceback.print_exc()
        emit('dataset_loaded', {
            'success': False,
            'message': f'Load error: {str(e)}'
        })


@socketio.on('save_single_record')
def handle_save_single_record(data):
    """Save or update a single record in measurement_summary"""
    if not DB_AVAILABLE or not db_conn:
        emit('record_save_result', {
            'success': False,
            'message': 'Database not available'
        })
        return
    
    try:
        # Ensure clean transaction state
        db_conn.rollback()
        
        cursor = db_conn.cursor()
        
        batch_id = data.get('batch_id')
        weight_gross = data.get('weight_gross')
        weight_net = data.get('weight_net')
        factor = data.get('factor')
        drc_evaluate = data.get('drc_evaluate')
        s21_avg = data.get('s21_avg')
        
        # Calculate DRC if weight data available
        drc_calculate = None
        if weight_gross and weight_net and factor:
            try:
                drc_calculate = round((float(weight_net) * float(factor)) / float(weight_gross) * 100, 1)
            except:
                pass
        
        # Check if record exists
        cursor.execute(
            "SELECT id FROM measurement_summary WHERE batch_id = %s",
            (batch_id,)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Update existing record
            update_query = """
                UPDATE measurement_summary 
                SET weight_gross = %s,
                    weight_net = %s,
                    factor = %s,
                    drc_percent = COALESCE(%s, drc_percent)
                WHERE batch_id = %s
            """
            cursor.execute(update_query, (
                weight_gross,
                weight_net,
                factor,
                drc_evaluate or drc_calculate,
                batch_id
            ))
        else:
            # Insert new record
            insert_query = """
                INSERT INTO measurement_summary 
                (batch_id, weight_gross, weight_net, factor, drc_percent, s21_rms, time)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(insert_query, (
                batch_id,
                weight_gross,
                weight_net,
                factor,
                drc_evaluate or drc_calculate,
                s21_avg
            ))
        
        db_conn.commit()
        cursor.close()
        
        emit('record_save_result', {
            'success': True,
            'batch_id': batch_id,
            'drc_calculate': drc_calculate
        })
        
    except Exception as e:
        print(f"Save single record error: {e}")
        import traceback
        traceback.print_exc()
        emit('record_save_result', {
            'success': False,
            'message': f'Save error: {str(e)}'
        })


# ==================== Model Training & Management ====================

@socketio.on('train_model')
def handle_train_model(data):
    """Train a machine learning model with provided dataset"""
    try:
        from datetime import datetime
        import json
        import math
        
        model_type = data.get('model_type', 'linear_regression')
        model_name = data.get('model_name')
        dataset = data.get('dataset', [])
        
        if not dataset or len(dataset) < 2:
            emit('model_train_result', {
                'success': False,
                'message': 'Insufficient data for training. Need at least 2 records.'
            })
            return
        
        # Extract features (S21) and targets (DRC)
        X = [float(record['s21_avg']) for record in dataset]
        y = [float(record['drc_evaluate']) for record in dataset]
        
        # Train model based on type
        if model_type == 'linear_regression':
            # Calculate linear regression: y = mx + b using pure Python
            n = len(X)
            sum_x = sum(X)
            sum_y = sum(y)
            sum_xy = sum(x * y_val for x, y_val in zip(X, y))
            sum_x2 = sum(x * x for x in X)
            
            # Calculate slope and intercept
            denominator = (n * sum_x2 - sum_x * sum_x)
            if denominator == 0:
                emit('model_train_result', {
                    'success': False,
                    'message': 'Cannot train: all S21 values are identical'
                })
                return
                
            m = (n * sum_xy - sum_x * sum_y) / denominator
            b = (sum_y - m * sum_x) / n
            
            # Calculate predictions
            y_pred = [m * x + b for x in X]
            
            # Calculate metrics
            mean_y = sum(y) / n
            ss_res = sum((y_val - pred) ** 2 for y_val, pred in zip(y, y_pred))
            ss_tot = sum((y_val - mean_y) ** 2 for y_val in y)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            mse = sum((y_val - pred) ** 2 for y_val, pred in zip(y, y_pred)) / n
            rmse = math.sqrt(mse)
            mae = sum(abs(y_val - pred) for y_val, pred in zip(y, y_pred)) / n
            
            parameters = {
                'slope': float(m),
                'intercept': float(b),
                'formula': f'DRC = {m:.6f} * S21 + {b:.6f}'
            }
            
        else:
            emit('model_train_result', {
                'success': False,
                'message': f'Model type {model_type} not yet implemented'
            })
            return
        
        # Save to database
        if db_conn:
            cursor = db_conn.cursor()
            cursor.execute("""
                INSERT INTO trained_models 
                (name, model_type, parameters, training_count, rmse, r_squared, mae, created_at, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                model_name,
                model_type,
                json.dumps(parameters),
                len(dataset),
                float(rmse),
                float(r_squared),
                float(mae),
                datetime.now(),
                False  # New models start as inactive
            ))
            model_id = cursor.fetchone()[0]
            db_conn.commit()
            
            emit('model_train_result', {
                'success': True,
                'model': {
                    'id': model_id,
                    'name': model_name,
                    'type': model_type,
                    'parameters': parameters,
                    'training_count': len(dataset),
                    'rmse': float(rmse),
                    'r_squared': float(r_squared),
                    'mae': float(mae),
                    'created_at': datetime.now().isoformat()
                },
                'message': f'Model trained successfully! R²={r_squared:.4f}, RMSE={rmse:.4f}'
            })
        else:
            emit('model_train_result', {
                'success': False,
                'message': 'Database not connected'
            })
            
    except Exception as e:
        print(f"Model training error: {e}")
        import traceback
        traceback.print_exc()
        emit('model_train_result', {
            'success': False,
            'message': f'Training error: {str(e)}'
        })


@socketio.on('get_trained_models')
def handle_get_trained_models(data=None):
    """Get all trained models from database"""
    try:
        print("Getting trained models...")
        if not db_conn:
            print("Database not connected!")
            emit('trained_models_result', {'success': False, 'message': 'Database not connected'})
            return
            
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT id, name, model_type, parameters, training_count, 
                   rmse, r_squared, mae, created_at, is_active, notes
            FROM trained_models
            ORDER BY created_at DESC
        """)
        
        models = []
        for row in cursor.fetchall():
            models.append({
                'id': row[0],
                'name': row[1],
                'type': row[2],
                'parameters': row[3],
                'training_count': row[4],
                'rmse': float(row[5]) if row[5] else 0,
                'r_squared': float(row[6]) if row[6] else 0,
                'mae': float(row[7]) if row[7] else 0,
                'created_at': row[8].isoformat() if row[8] else None,
                'is_active': row[9],
                'notes': row[10]
            })
        
        print(f"Found {len(models)} trained models")
        if models:
            print(f"First model: {models[0]['name']}")
        
        emit('trained_models_result', {
            'success': True,
            'models': models
        })
        
    except Exception as e:
        print(f"Get trained models error: {e}")
        import traceback
        traceback.print_exc()
        emit('trained_models_result', {
            'success': False,
            'message': f'Error: {str(e)}'
        })


@socketio.on('activate_model')
def handle_activate_model(data):
    """Set a model as active (deactivate others)"""
    try:
        model_name = data.get('model_name')
        if not db_conn or not model_name:
            emit('model_activated', {'success': False})
            return
            
        cursor = db_conn.cursor()
        # Deactivate all models
        cursor.execute("UPDATE trained_models SET is_active = FALSE")
        # Activate selected model
        cursor.execute("UPDATE trained_models SET is_active = TRUE WHERE name = %s", (model_name,))
        db_conn.commit()
        
        emit('model_activated', {'success': True, 'model_name': model_name})
        
    except Exception as e:
        print(f"Activate model error: {e}")
        emit('model_activated', {'success': False, 'message': str(e)})


@socketio.on('deactivate_model')
def handle_deactivate_model(data):
    """Deactivate a model"""
    try:
        model_name = data.get('model_name')
        if not db_conn or not model_name:
            emit('model_deactivated', {'success': False})
            return
            
        cursor = db_conn.cursor()
        cursor.execute("UPDATE trained_models SET is_active = FALSE WHERE name = %s", (model_name,))
        db_conn.commit()
        
        emit('model_deactivated', {'success': True, 'model_name': model_name})
        
    except Exception as e:
        print(f"Deactivate model error: {e}")
        emit('model_deactivated', {'success': False, 'message': str(e)})


@socketio.on('delete_model')
def handle_delete_model(data):
    """Delete a model from database"""
    try:
        model_name = data.get('model_name')
        if not db_conn or not model_name:
            emit('model_deleted', {'success': False})
            return
            
        cursor = db_conn.cursor()
        cursor.execute("DELETE FROM trained_models WHERE name = %s", (model_name,))
        db_conn.commit()
        
        emit('model_deleted', {'success': True, 'model_name': model_name})
        
    except Exception as e:
        print(f"Delete model error: {e}")
        emit('model_deleted', {'success': False, 'message': str(e)})


@socketio.on('update_model_notes')
def handle_update_model_notes(data):
    """Update model notes/description"""
    try:
        model_name = data.get('model_name')
        notes = data.get('notes', '')
        
        if not db_conn or not model_name:
            emit('model_notes_updated', {'success': False})
            return
            
        cursor = db_conn.cursor()
        cursor.execute("UPDATE trained_models SET notes = %s WHERE name = %s", (notes, model_name))
        db_conn.commit()
        
        emit('model_notes_updated', {'success': True, 'model_name': model_name})
        
    except Exception as e:
        print(f"Update model notes error: {e}")
        emit('model_notes_updated', {'success': False, 'message': str(e)})


def check_idle_timeout():
    """Monitor idle time and stop backend when no clients (headless mode only)"""
    global active_clients, last_activity_time, is_running
    
    while True:
        time.sleep(10)  # Check every 10 seconds
        
        if not HEADLESS_MODE:
            continue
            
        if active_clients <= 0 and last_activity_time:
            idle_time = time.time() - last_activity_time
            if idle_time >= IDLE_TIMEOUT:
                print(f"\n{'='*60}")
                print(f"⏱ Idle timeout reached ({IDLE_TIMEOUT}s)")
                print(f"🛑 No active clients - Stopping backend...")
                print(f"{'='*60}\n")
                
                # Stop sweep if running
                if is_running:
                    is_running = False
                    print("✓ Sweep stopped")
                    time.sleep(1)
                
                # Disconnect NanoVNA if connected
                if ser and ser.is_open:
                    disconnect_nanovna()
                    print("✓ NanoVNA disconnected")
                
                print(f"{'='*60}")
                print("ℹ️ Backend stopped. Server still running.")
                print("   Connect from browser to resume.")
                print(f"{'='*60}\n")
                
                # Reset timer and wait for new connections
                last_activity_time = None


if __name__ == '__main__':
    print("="*60)
    print("DRC Online - Premeir System Engineering Co.ltd")
    print("="*60)
    print(f"Port: {PORT}")
    print(f"Frequency: {START_FREQ/1e9:.2f} - {STOP_FREQ/1e9:.2f} GHz")
    print(f"Points: {POINTS}")
    print(f"Interval: {INTERVAL*1000:.0f} ms")
    
    # Show headless mode status
    if HEADLESS_MODE:
        print(f"Mode: HEADLESS (Auto-shutdown after {IDLE_TIMEOUT}s idle)")
    else:
        print(f"Mode: NORMAL (Manual control)")
    
    print("="*60)
    
    # Initialize database
    print("\nInitializing TimescaleDB connection...")
    if init_database():
        print("✓ Database ready")
    else:
        print("⚠ Running without database (data will not be saved)")
    
    # Start idle timeout monitor in headless mode
    if HEADLESS_MODE:
        last_activity_time = time.time()
        idle_check_thread = threading.Thread(target=check_idle_timeout, daemon=True)
        idle_check_thread.start()
        print(f"✓ Idle timeout monitor started ({IDLE_TIMEOUT}s)")
    
    print("\nStarting server at http://localhost:5000")
    print("Open your browser and navigate to the URL above")
    print("="*60)
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
