# NanoVNA Backend Module

## โครงสร้างไฟล์ใหม่

```
drc-aten/
├── nanovna_backend.py      # Backend module สำหรับดึงข้อมูลจาก NanoVNA
├── app_new.py              # Flask application ที่ใช้ backend module ใหม่
├── start_new_backend.bat   # Batch file สำหรับรัน backend ใหม่
├── app.py                  # Flask application เดิม
└── start_drc_online.bat    # Batch file เดิม
```

## คุณสมบัติของ Backend ใหม่

### 1. **nanovna_backend.py** - NanoVNA Device Module
- **Class `NanoVNADevice`**: จัดการการเชื่อมต่อและการดึงข้อมูล
- **ฟีเจอร์หลัก**:
  - เชื่อมต่อ/ตัดการเชื่อมต่อกับ COM4
  - ตั้งค่าช่วงความถี่ (Start/Stop Frequency, Points)
  - ดึงข้อมูล S11 และ S21 แยกกัน
  - แปลงข้อมูล raw เป็น dictionary format
  - คำนวณสถิติ (Avg, Max, Min, Phase)
  - มีระบบ retry สำหรับความน่าเชื่อถือ
  - Logging ที่ละเอียด

### 2. **app_new.py** - Flask Application
- ใช้ `NanoVNADevice` จาก `nanovna_backend.py`
- WebSocket สำหรับ real-time updates
- API endpoints:
  - `/` - หน้า dashboard
  - `start_sweep` - เริ่ม sweep
  - `stop_sweep` - หยุด sweep
  - `get_config` - ดึงค่า configuration

## การใช้งาน

### วิธีที่ 1: ใช้ Backend ใหม่ (แนะนำ)
```bash
# รัน backend ใหม่
start_new_backend.bat

# หรือ
python app_new.py
```

### วิธีที่ 2: ทดสอบ Backend Module โดยตรง
```bash
# ทดสอบการเชื่อมต่อและดึงข้อมูล
python nanovna_backend.py
```

### วิธีที่ 3: ใช้ Backend เดิม
```bash
# รัน backend เดิม
start_drc_online.bat

# หรือ
python app.py
```

## ตัวอย่างการใช้งาน Backend Module

### 1. การใช้งานพื้นฐาน
```python
from nanovna_backend import NanoVNADevice

# สร้าง device instance
device = NanoVNADevice(port="COM4")

# เชื่อมต่อ
if device.connect():
    # ตั้งค่าช่วงความถี่
    device.set_frequency_range(0.9e9, 0.95e9, 101)
    
    # ดึงข้อมูล
    s11_data, s21_data = device.get_full_measurement()
    
    # แสดงสถิติ
    s11_stats = device.get_summary_stats(s11_data)
    print(f"S11 Average: {s11_stats['avg_db']:.2f} dB")
    
    # ตัดการเชื่อมต่อ
    device.disconnect()
```

### 2. การใช้งานในลูป
```python
from nanovna_backend import NanoVNADevice
import time

device = NanoVNADevice(port="COM4")

if device.connect():
    device.set_frequency_range(0.9e9, 0.95e9, 101)
    
    try:
        for i in range(10):  # วัด 10 ครั้ง
            s11_data, s21_data = device.get_full_measurement()
            
            if s11_data:
                s11_stats = device.get_summary_stats(s11_data)
                print(f"Sweep {i+1}: S11 Min={s11_stats['min_db']:.2f} dB")
            
            time.sleep(1)  # รอ 1 วินาที
    finally:
        device.disconnect()
```

## ข้อมูลที่ส่งไปยัง Frontend

```javascript
{
    "timestamp": "09:55:33",
    "sweep_count": 1,
    "s11_data": [
        {
            "frequency": 0.900,  // GHz
            "magnitude": 0.123,
            "db": -18.2,
            "phase": -45.5,
            "real": 0.087,
            "imag": -0.087
        },
        // ... อีก 100 points
    ],
    "s21_data": [
        {
            "frequency": 0.900,
            "magnitude": 0.234,
            "db": -12.6,
            "phase": -30.2,
            "real": 0.202,
            "imag": -0.117
        },
        // ... อีก 100 points
    ],
    "summary": {
        "avg_db": -15.5,
        "max_db": -4.8,
        "min_db": -25.3,
        "avg_phase": -42.1,
        "s21_avg_db": -10.2,
        "s21_max_db": -3.5,
        "s21_min_db": -18.9,
        "s21_avg_phase": -28.4
    }
}
```

## ข้อดีของ Backend ใหม่

1. **โครงสร้างชัดเจน**: แยก business logic ออกจาก web framework
2. **ใช้งานง่าย**: สามารถ import และใช้ใน project อื่นได้
3. **ทดสอบง่าย**: สามารถทดสอบ backend แยกจาก frontend
4. **มี Error Handling**: มีระบบจัดการ error ที่ดีกว่า
5. **Logging ละเอียด**: ติดตามการทำงานได้ง่าย
6. **Flexible**: เปลี่ยนแปลง configuration ได้ง่าย
7. **Retry Mechanism**: มีระบบลองใหม่อัตโนมัติ

## การ Configuration

แก้ไขค่าใน `app_new.py`:
```python
PORT = "COM4"              # Serial port
START_FREQ = 0.9e9         # ความถี่เริ่มต้น (Hz)
STOP_FREQ = 0.95e9         # ความถี่สิ้นสุด (Hz)
POINTS = 101               # จำนวนจุดข้อมูล
INTERVAL = 1.0             # ระยะเวลาระหว่าง sweep (วินาที)
```

## Troubleshooting

### ปัญหา: ไม่สามารถเชื่อมต่อกับ COM4
```
✗ ไม่สามารถเชื่อมต่อกับ COM4: [Errno 2] could not open port 'COM4'
```
**แก้ไข**:
- ตรวจสอบว่าอุปกรณ์เสียบอยู่
- ตรวจสอบ Device Manager ว่า COM port ถูกต้อง
- ปิดโปรแกรมอื่นที่ใช้ COM4

### ปัญหา: ได้ข้อมูลไม่ครบ
```
S11: Attempt 1/3, got 95/101 points
```
**แก้ไข**:
- เพิ่ม wait_time ใน `_send_command()`
- ลดจำนวน POINTS
- ตรวจสอบสัญญาณ USB

### ปัญหา: ข้อมูลไม่แสดงที่ frontend
**แก้ไข**:
- ตรวจสอบ console log ใน browser (F12)
- ตรวจสอบว่า WebSocket เชื่อมต่อสำเร็จหรือไม่
- ดู log ใน terminal ว่ามี error หรือไม่

## License
Premier System Engineering Co.ltd
