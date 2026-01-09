# DRC Online
**Vector Network Analyzer Real-time Monitoring System**

Premeir System Engineering Co.ltd

---

## System Requirements

- **Operating System**: Windows 10/11
- **Python**: 3.8 or higher
- **Hardware**: NanoVNA-F V2 device
- **USB Driver**: Cypress USB-CDC driver (for Windows 10 and earlier)

---

## Installation

### Method 1: Automatic Installation (Recommended)

1. Extract all files to a folder
2. Double-click `install.bat`
3. Wait for installation to complete
4. Run `start_drc_online.bat` to start the application

### Method 2: Manual Installation

1. Install Python from https://www.python.org/ (if not already installed)

2. Open Command Prompt in the application folder

3. Create virtual environment:
   ```
   python -m venv venv
   ```

4. Activate virtual environment:
   ```
   venv\Scripts\activate
   ```

5. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

6. Run application:
   ```
   python app.py
   ```

---

## Usage

1. **Connect NanoVNA** device to USB port

2. **Check COM Port**:
   - Open Device Manager (Win + X)
   - Find COM port under "Ports (COM & LPT)"
   - Note the COM port number (e.g., COM4)

3. **Update Configuration** (if needed):
   - Open `app.py`
   - Change `PORT = "COM4"` to your COM port
   - Change frequency range if needed:
     - `START_FREQ = 4.40e9`  # 4.40 GHz
     - `STOP_FREQ = 5.00e9`   # 5.00 GHz
   - Save the file

4. **Start Application**:
   - Run `start_drc_online.bat`
   - Wait for server to start
   - Open browser to: http://localhost:5000

5. **Begin Monitoring**:
   - Click "▶ Start Sweep" button in the sidebar
   - View real-time charts and data
   - Click "⏹ Stop Sweep" to stop

---

## Features

### Real-time Monitoring
- S11 Magnitude (dB) vs Frequency
- S22 Magnitude (dB) vs Frequency  
- S11 Phase vs Frequency
- Update interval: 200 ms

### Dashboard
- Live sweep count
- Statistical summaries (Avg, Max, Min)
- Connection status indicator
- Real-time clock

### Data Views
- Chart visualization
- Raw data table
- WebSocket-based updates

---

## Configuration

Edit `app.py` to change settings:

```python
PORT = "COM4"              # COM port
BAUDRATE = 115200          # Baud rate
START_FREQ = 4.40e9        # Start frequency (Hz)
STOP_FREQ = 5.00e9         # Stop frequency (Hz)
POINTS = 101               # Number of points
INTERVAL = 0.2             # Update interval (seconds)
```

---

## Troubleshooting

### Device Not Found
- Check USB connection
- Verify COM port in Device Manager
- Install/update Cypress USB-CDC driver
- Try different USB port

### Cannot Connect
- Close other applications using the COM port
- Restart the device
- Check cable connection

### Server Won't Start
- Check if port 5000 is already in use
- Run as Administrator
- Check firewall settings

### Charts Not Updating
- Click "Stop" then "Start" again
- Refresh browser page (F5)
- Check browser console for errors

---

## File Structure

```
drc-aten/
├── app.py                  # Main application
├── requirements.txt        # Python dependencies
├── install.bat            # Installation script
├── start_drc_online.bat   # Startup script (created after install)
├── README.md              # This file
├── templates/
│   └── index.html         # Web interface
└── static/
    ├── css/
    │   └── style.css      # Styles
    └── js/
        └── app.js         # JavaScript
```

---

## Technical Specifications

- **Framework**: Flask + Socket.IO
- **Frontend**: HTML5, CSS3, JavaScript, Chart.js
- **Communication**: WebSocket real-time updates
- **Device Protocol**: Serial (115200 baud)
- **Frequency Range**: 50 kHz - 3 GHz (device limit)
- **Extended Range**: 4.4 - 5.0 GHz (experimental)

---

## Support

**Premeir System Engineering Co.ltd**

For technical support or inquiries, please contact your system administrator.

---

## License

Copyright © 2026 Premeir System Engineering Co.ltd  
All rights reserved.
