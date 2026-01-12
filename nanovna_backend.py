"""
NanoVNA Backend Module
ดึงค่า S11 และ S21 จากอุปกรณ์ที่ COM4
"""

import serial
import time
import math
from typing import List, Dict, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NanoVNADevice:
    """Class สำหรับจัดการการเชื่อมต่อและดึงข้อมูลจาก NanoVNA"""
    
    def __init__(self, port: str = "COM4", baudrate: int = 115200):
        """
        Initialize NanoVNA device
        
        Args:
            port: Serial port (default: COM4)
            baudrate: Baud rate (default: 115200)
        """
        self.port = port
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None
        self.is_connected = False
        
        # Default sweep parameters
        self.start_freq = 0.9e9   # 900 MHz
        self.stop_freq = 0.95e9   # 950 MHz
        self.points = 101
        
    def connect(self) -> bool:
        """
        เชื่อมต่อกับอุปกรณ์ NanoVNA
        
        Returns:
            bool: True ถ้าเชื่อมต่อสำเร็จ, False ถ้าล้มเหลว
        """
        try:
            logger.info(f"กำลังเชื่อมต่อกับ NanoVNA ที่ {self.port}...")
            self.ser = serial.Serial(self.port, self.baudrate, timeout=2)
            time.sleep(0.5)
            self.ser.reset_input_buffer()
            
            # ตั้งค่าช่วงความถี่
            self._set_sweep_parameters()
            
            self.is_connected = True
            logger.info(f"✓ เชื่อมต่อสำเร็จกับ {self.port}")
            return True
            
        except serial.SerialException as e:
            logger.error(f"✗ ไม่สามารถเชื่อมต่อกับ {self.port}: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"✗ เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> None:
        """ตัดการเชื่อมต่อกับอุปกรณ์"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.is_connected = False
            logger.info("✓ ตัดการเชื่อมต่อแล้ว")
    
    def _set_sweep_parameters(self) -> None:
        """ตั้งค่าพารามิเตอร์สำหรับการ sweep"""
        if not self.ser or not self.ser.is_open:
            return
        
        try:
            cmd = f"sweep {int(self.start_freq)} {int(self.stop_freq)} {self.points}"
            self.ser.write(f"{cmd}\r\n".encode())
            time.sleep(0.3)
            self.ser.read(self.ser.in_waiting)
            logger.info(f"✓ ตั้งค่า sweep: {self.start_freq/1e9:.3f}-{self.stop_freq/1e9:.3f} GHz, {self.points} points")
        except Exception as e:
            logger.error(f"✗ ไม่สามารถตั้งค่า sweep: {e}")
    
    def set_frequency_range(self, start_freq: float, stop_freq: float, points: int = 101) -> None:
        """
        ตั้งค่าช่วงความถี่
        
        Args:
            start_freq: ความถี่เริ่มต้น (Hz)
            stop_freq: ความถี่สิ้นสุด (Hz)
            points: จำนวนจุดข้อมูล
        """
        self.start_freq = start_freq
        self.stop_freq = stop_freq
        self.points = points
        
        if self.is_connected:
            self._set_sweep_parameters()
    
    def _send_command(self, command: str, wait_time: float = 0.5) -> str:
        """
        ส่งคำสั่งไปยังอุปกรณ์และรับ response
        
        Args:
            command: คำสั่งที่จะส่ง
            wait_time: เวลารอ response (วินาที)
            
        Returns:
            str: Response จากอุปกรณ์
        """
        if not self.ser or not self.ser.is_open:
            raise Exception("ไม่ได้เชื่อมต่อกับอุปกรณ์")
        
        self.ser.write(f"{command}\r\n".encode())
        time.sleep(wait_time)
        response = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
        return response
    
    def perform_scan(self) -> bool:
        """
        ทำการ scan
        
        Returns:
            bool: True ถ้าสำเร็จ, False ถ้าล้มเหลว
        """
        try:
            cmd = f"scan {int(self.start_freq)} {int(self.stop_freq)} {self.points}"
            self._send_command(cmd, wait_time=0.5)
            return True
        except Exception as e:
            logger.error(f"✗ Scan ล้มเหลว: {e}")
            return False
    
    def get_s11_data(self, max_retries: int = 3) -> List[str]:
        """
        ดึงข้อมูล S11 (data 0)
        
        Args:
            max_retries: จำนวนครั้งที่จะลองใหม่
            
        Returns:
            List[str]: รายการข้อมูล S11
        """
        for attempt in range(max_retries):
            try:
                response = self._send_command("data 0", wait_time=0.5)
                lines = [l.strip() for l in response.split('\n') 
                        if l.strip() and not l.strip().startswith('ch>') 
                        and not l.strip().startswith('data')]
                
                if len(lines) >= self.points:
                    logger.info(f"✓ ดึงข้อมูล S11 สำเร็จ: {len(lines)} points")
                    return lines[:self.points]
                
                logger.warning(f"S11: Attempt {attempt + 1}/{max_retries}, got {len(lines)}/{self.points} points")
                time.sleep(0.2)
                
            except Exception as e:
                logger.error(f"✗ ข้อผิดพลาดในการดึง S11 (attempt {attempt + 1}): {e}")
                time.sleep(0.2)
        
        logger.error(f"✗ ไม่สามารถดึงข้อมูล S11 ได้หลังจาก {max_retries} ครั้ง")
        return []
    
    def get_s21_data(self, max_retries: int = 3) -> List[str]:
        """
        ดึงข้อมูล S21 (data 1)
        
        Args:
            max_retries: จำนวนครั้งที่จะลองใหม่
            
        Returns:
            List[str]: รายการข้อมูล S21
        """
        for attempt in range(max_retries):
            try:
                response = self._send_command("data 1", wait_time=0.5)
                lines = [l.strip() for l in response.split('\n') 
                        if l.strip() and not l.strip().startswith('ch>') 
                        and not l.strip().startswith('data')]
                
                if len(lines) >= self.points:
                    logger.info(f"✓ ดึงข้อมูล S21 สำเร็จ: {len(lines)} points")
                    return lines[:self.points]
                
                logger.warning(f"S21: Attempt {attempt + 1}/{max_retries}, got {len(lines)}/{self.points} points")
                time.sleep(0.2)
                
            except Exception as e:
                logger.error(f"✗ ข้อผิดพลาดในการดึง S21 (attempt {attempt + 1}): {e}")
                time.sleep(0.2)
        
        logger.error(f"✗ ไม่สามารถดึงข้อมูล S21 ได้หลังจาก {max_retries} ครั้ง")
        return []
    
    def parse_data(self, lines: List[str]) -> List[Dict]:
        """
        แปลงข้อมูลจากรูปแบบ raw เป็น dictionary
        
        Args:
            lines: รายการข้อมูล raw
            
        Returns:
            List[Dict]: รายการข้อมูลที่แปลงแล้ว
        """
        parsed_data = []
        
        for i, line in enumerate(lines[:self.points]):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    real = float(parts[0])
                    imag = float(parts[1])
                    magnitude = (real**2 + imag**2)**0.5
                    db = 20 * math.log10(magnitude) if magnitude > 0 else -999
                    phase = math.degrees(math.atan2(imag, real))
                    
                    # คำนวณความถี่ในหน่วย GHz
                    freq_ghz = self.start_freq/1e9 + (i * (self.stop_freq - self.start_freq) / (self.points - 1)) / 1e9
                    
                    parsed_data.append({
                        'frequency': freq_ghz,
                        'magnitude': magnitude,
                        'db': db,
                        'phase': phase,
                        'real': real,
                        'imag': imag
                    })
                except (ValueError, ZeroDivisionError) as e:
                    logger.warning(f"ข้ามข้อมูลที่ index {i}: {e}")
                    continue
        
        return parsed_data
    
    def get_full_measurement(self) -> Tuple[List[Dict], List[Dict]]:
        """
        ทำการวัดและดึงข้อมูล S11 และ S21 แบบเต็ม
        
        Returns:
            Tuple[List[Dict], List[Dict]]: (s11_data, s21_data)
        """
        if not self.is_connected:
            logger.error("✗ ไม่ได้เชื่อมต่อกับอุปกรณ์")
            return [], []
        
        # ทำการ scan
        if not self.perform_scan():
            return [], []
        
        # ดึงข้อมูล S11
        s11_lines = self.get_s11_data()
        s11_data = self.parse_data(s11_lines) if s11_lines else []
        
        # ดึงข้อมูล S21
        s21_lines = self.get_s21_data()
        s21_data = self.parse_data(s21_lines) if s21_lines else []
        
        logger.info(f"📊 การวัดเสร็จสมบูรณ์: S11={len(s11_data)} points, S21={len(s21_data)} points")
        
        return s11_data, s21_data
    
    def get_summary_stats(self, data: List[Dict]) -> Dict:
        """
        คำนวณสถิติสรุปจากข้อมูล
        
        Args:
            data: รายการข้อมูล
            
        Returns:
            Dict: สถิติสรุป
        """
        if not data:
            return {
                'avg_db': 0,
                'max_db': 0,
                'min_db': 0,
                'avg_phase': 0
            }
        
        db_values = [d['db'] for d in data]
        phase_values = [d['phase'] for d in data]
        
        return {
            'avg_db': sum(db_values) / len(db_values),
            'max_db': max(db_values),
            'min_db': min(db_values),
            'avg_phase': sum(phase_values) / len(phase_values)
        }


def test_device():
    """ฟังก์ชันทดสอบการทำงานของ NanoVNA device"""
    device = NanoVNADevice(port="COM4")
    
    # เชื่อมต่อ
    if not device.connect():
        logger.error("ไม่สามารถเชื่อมต่อได้")
        return
    
    try:
        # ตั้งค่าช่วงความถี่ (900-950 MHz)
        device.set_frequency_range(0.9e9, 0.95e9, 101)
        
        # ทำการวัด
        logger.info("\n" + "="*60)
        logger.info("เริ่มการวัด...")
        logger.info("="*60)
        
        s11_data, s21_data = device.get_full_measurement()
        
        # แสดงผลลัพธ์
        if s11_data:
            s11_stats = device.get_summary_stats(s11_data)
            logger.info(f"\n📊 S11 Statistics:")
            logger.info(f"  Average: {s11_stats['avg_db']:.2f} dB")
            logger.info(f"  Maximum: {s11_stats['max_db']:.2f} dB")
            logger.info(f"  Minimum: {s11_stats['min_db']:.2f} dB")
            logger.info(f"  Avg Phase: {s11_stats['avg_phase']:.2f}°")
        
        if s21_data:
            s21_stats = device.get_summary_stats(s21_data)
            logger.info(f"\n📊 S21 Statistics:")
            logger.info(f"  Average: {s21_stats['avg_db']:.2f} dB")
            logger.info(f"  Maximum: {s21_stats['max_db']:.2f} dB")
            logger.info(f"  Minimum: {s21_stats['min_db']:.2f} dB")
            logger.info(f"  Avg Phase: {s21_stats['avg_phase']:.2f}°")
        
        logger.info("\n" + "="*60)
        
    finally:
        device.disconnect()


if __name__ == "__main__":
    # ทดสอบการทำงาน
    test_device()
