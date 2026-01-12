"""
Flask Web Dashboard for NanoVNA Real-time Monitoring (ใช้ backend module ใหม่)
WebSocket-based real-time chart updates with NanoVNA Backend
"""

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import time
from datetime import datetime
from nanovna_backend import NanoVNADevice
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nanovna-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
PORT = "COM4"
START_FREQ = 0.9e9   # 900 MHz
STOP_FREQ = 0.95e9   # 950 MHz
POINTS = 101
INTERVAL = 1.0       # seconds

# Global variables
is_running = False
device = None
sweep_count = 0


def sweep_loop():
    """Continuous sweep loop ที่ส่งข้อมูลผ่าน WebSocket"""
    global is_running, device, sweep_count
    
    while is_running:
        try:
            sweep_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Sweep #{sweep_count} - {timestamp}")
            logger.info(f"{'='*60}")
            
            # ทำการวัดและดึงข้อมูล
            s11_data, s21_data = device.get_full_measurement()
            
            # ตรวจสอบว่าได้ข้อมูลครบหรือไม่
            if s11_data and len(s11_data) == POINTS:
                # คำนวณสถิติ
                s11_stats = device.get_summary_stats(s11_data)
                s21_stats = device.get_summary_stats(s21_data) if s21_data else {
                    'avg_db': 0, 'max_db': 0, 'min_db': 0, 'avg_phase': 0
                }
                
                # แสดงข้อมูลสถิติ
                logger.info(f"✓ อ่านค่าได้สำเร็จ")
                logger.info(f"  S11: {len(s11_data)} points | Min={s11_stats['min_db']:.2f} dB, Max={s11_stats['max_db']:.2f} dB, Avg={s11_stats['avg_db']:.2f} dB")
                
                if s21_data:
                    logger.info(f"  S21: {len(s21_data)} points | Min={s21_stats['min_db']:.2f} dB, Max={s21_stats['max_db']:.2f} dB, Avg={s21_stats['avg_db']:.2f} dB")
                
                # สร้างข้อมูลสำหรับส่งไปยัง frontend
                data = {
                    'timestamp': timestamp,
                    'sweep_count': sweep_count,
                    's11_data': s11_data,
                    's21_data': s21_data,
                    'summary': {
                        # S11 stats
                        'avg_db': s11_stats['avg_db'],
                        'max_db': s11_stats['max_db'],
                        'min_db': s11_stats['min_db'],
                        'avg_phase': s11_stats['avg_phase'],
                        # S21 stats
                        's21_avg_db': s21_stats['avg_db'],
                        's21_max_db': s21_stats['max_db'],
                        's21_min_db': s21_stats['min_db'],
                        's21_avg_phase': s21_stats['avg_phase']
                    }
                }
                
                # ส่งข้อมูลผ่าน WebSocket
                socketio.emit('sweep_data', data)
                logger.info("✓ ส่งข้อมูลไปยัง frontend สำเร็จ")
                
            else:
                logger.warning(f"✗ ข้อมูลไม่ครบ - Sweep #{sweep_count}: S11={len(s11_data)}/{POINTS} จุด")
                socketio.emit('error', {
                    'message': f'ข้อมูลไม่ครบ: S11={len(s11_data)}/{POINTS} points'
                })
            
            # รอก่อน sweep ครั้งถัดไป
            time.sleep(INTERVAL)
            
        except Exception as e:
            logger.error(f"✗ เกิดข้อผิดพลาดใน sweep: {e}")
            socketio.emit('error', {'message': str(e)})
            time.sleep(INTERVAL)


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('🔌 Client connected')
    emit('status', {
        'message': 'Connected to server',
        'sweep_count': sweep_count
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('🔌 Client disconnected')


@socketio.on('start_sweep')
def handle_start_sweep():
    """Start continuous sweep"""
    global is_running, device
    
    if not is_running:
        logger.info("\n" + "="*60)
        logger.info("🚀 กำลังเริ่ม sweep...")
        logger.info("="*60)
        
        # สร้าง device instance
        device = NanoVNADevice(port=PORT)
        device.set_frequency_range(START_FREQ, STOP_FREQ, POINTS)
        
        # เชื่อมต่อกับอุปกรณ์
        if device.connect():
            is_running = True
            
            # เริ่ม sweep thread
            thread = threading.Thread(target=sweep_loop)
            thread.daemon = True
            thread.start()
            
            logger.info("✓ เริ่ม sweep สำเร็จ")
            emit('status', {
                'message': 'Sweep started',
                'running': True
            })
        else:
            logger.error("✗ ไม่สามารถเชื่อมต่อกับ NanoVNA")
            emit('error', {
                'message': 'ไม่สามารถเชื่อมต่อกับ NanoVNA ได้'
            })
    else:
        logger.warning("⚠ Sweep กำลังทำงานอยู่แล้ว")
        emit('status', {
            'message': 'Already running',
            'running': True
        })


@socketio.on('stop_sweep')
def handle_stop_sweep():
    """Stop continuous sweep"""
    global is_running, device
    
    logger.info("\n" + "="*60)
    logger.info("⏹ กำลังหยุด sweep...")
    logger.info("="*60)
    
    is_running = False
    
    if device:
        device.disconnect()
        device = None
    
    logger.info("✓ หยุด sweep สำเร็จ")
    emit('status', {
        'message': 'Sweep stopped',
        'running': False
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
    print("DRC Online - Premier System Engineering Co.ltd")
    print("NanoVNA Real-time Monitoring Dashboard (New Backend)")
    print("="*60)
    print(f"📡 Port: {PORT}")
    print(f"📊 Frequency: {START_FREQ/1e9:.2f} - {STOP_FREQ/1e9:.2f} GHz")
    print(f"📈 Points: {POINTS}")
    print(f"⏱  Interval: {INTERVAL*1000:.0f} ms")
    print("="*60)
    print("\n🌐 Starting server at http://localhost:5000")
    print("🌐 Open your browser and navigate to the URL above")
    print("="*60 + "\n")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
