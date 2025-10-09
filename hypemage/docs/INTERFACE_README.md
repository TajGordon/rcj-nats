# Robot Interface System

## Quick Start

### 1. Start Interface on Robot

```bash
# SSH into your robot
ssh pi@robot.local

# Start the interface server
python -m hypemage.interface
```

**Output:**
```
Starting Robot Interface Server
Dashboard: http://0.0.0.0:8080
WebSocket: ws://0.0.0.0:8080/ws
```

### 2. Open Web Dashboard

```
http://robot-ip:8080
```

You'll see the control dashboard with:
- Start/stop buttons for scripts
- Status indicators
- Log viewer
- Script categories (robot, calibration, test)

---

## How It Works

```
Your Laptop/Phone → Browser → http://robot:8080 → Interface Server → Launches Scripts
                                                   ├─ scylla (debug/production)
                                                   ├─ color_calibration
                                                   ├─ motor_test
                                                   └─ your custom scripts
```

**Communication:**
- WebSocket (ws://robot:8080/ws) - Real-time commands & status
- HTTP REST API - Script list, logs, status

---

## Adding Your Own Scripts

Edit `hypemage/interface.py` and add to the `scripts` dictionary:

```python
class InterfaceServer:
    def __init__(self):
        self.scripts = {
            # Existing scripts...
            
            # YOUR CUSTOM SCRIPT - just add config!
            'imu_calibration': ScriptConfig(
                name='IMU Calibration',
                module='hypemage.calibrate_imu',  # Python module path
                args=[],                           # Default arguments
                description='Calibrate IMU offsets and magnetometer',
                category='calibration'             # Group in UI
            ),
            
            'tof_test': ScriptConfig(
                name='ToF Sensor Test',
                module='test.tof',
                args=[],
                description='Test all ToF sensors',
                category='test'
            ),
        }
```

**That's it!** The generic launcher handles everything. No other code changes needed.

---

## Available Endpoints

### WebSocket (ws://robot:8080/ws)

**Client sends:**
```json
{"command": "run_script", "script_id": "scylla_debug", "args": []}
{"command": "stop_script"}
{"command": "get_status"}
{"command": "get_scripts"}
```

**Server responds:**
```json
{"type": "response", "data": {"success": true, "pid": 12345}}
{"type": "process_started", "script": "scylla_debug", "pid": 12345}
{"type": "process_stopped", "script": "scylla_debug", "exit_code": 0}
```

### HTTP REST API

- `GET /` - Dashboard UI
- `GET /status` - Current status (JSON)
- `GET /scripts` - Available scripts (JSON)
- `GET /logs?lines=100` - Recent log lines (JSON)

---

## Script Categories

Scripts are grouped by category in the UI:

- **robot** - Main robot programs (scylla debug/production)
- **calibration** - Calibration tools (color, IMU, etc.)
- **test** - Hardware tests (motors, camera, sensors)
- **utility** - Other useful scripts

---

## Development vs Competition

### Development (Use Interface ✅)

```bash
# On robot: Start interface
python -m hypemage.interface

# From laptop: Open dashboard
http://robot:8080

# Click buttons to:
# - Start/stop robot
# - Run calibration
# - Test motors
# - View logs
```

### Competition (Skip Interface ❌)

```bash
# Just boot directly to scylla
python -m hypemage.scylla

# Or use systemd auto-start:
[Service]
ExecStart=/usr/bin/python3 -m hypemage.scylla
```

**Why?**
- Faster startup
- Less complexity
- Interface is for development, not competition

---

## Auto-Start on Boot (Optional)

Create systemd service for interface:

```bash
sudo nano /etc/systemd/system/robot-interface.service
```

```ini
[Unit]
Description=Robot Interface Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/rcj-nats
ExecStart=/usr/bin/python3 -m hypemage.interface
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable robot-interface
sudo systemctl start robot-interface
```

---

## Example: Running Scripts

### From Web UI

1. Open `http://robot:8080`
2. Click "Robot (Debug)" button
3. See status update: "Running: scylla_debug (PID: 12345)"
4. Click "Stop" to terminate

### From Code (WebSocket)

```javascript
// Connect to interface
const ws = new WebSocket('ws://robot:8080/ws');

// Send command
ws.send(JSON.stringify({
    command: 'run_script',
    script_id: 'scylla_debug',
    args: []
}));

// Receive response
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data);
    // {type: 'response', data: {success: true, pid: 12345}}
};
```

---

## Troubleshooting

### Port 8080 already in use

```bash
# Find process using port 8080
sudo lsof -i :8080

# Kill it
sudo kill -9 <PID>
```

### Can't connect from laptop

```bash
# Check interface is running
ps aux | grep interface

# Check firewall (if enabled)
sudo ufw allow 8080

# Check IP address
hostname -I
```

### Script won't start

```bash
# Check logs
GET http://robot:8080/logs

# Or SSH and check manually
ssh pi@robot
cat logs/robot.log
```

---

## File Structure

```
hypemage/
├── interface.py              # Main interface server ⭐
├── client/                   # Web dashboard UI
│   ├── index.html           # Dashboard HTML
│   ├── app.js               # WebSocket client logic
│   └── style.css            # Styling
└── docs/
    └── INTERFACE_README.md  # This file
```

---

## Dependencies

```bash
pip install fastapi uvicorn websockets
```

Already installed if you use the localization server or camera test server.

---

## Summary

- ✅ Single interface server (`interface.py`)
- ✅ Generic script launcher (add via config)
- ✅ FastAPI (same as rest of codebase)
- ✅ WebSocket + REST API
- ✅ Easy to extend
- ✅ Web dashboard included

**Start it:** `python -m hypemage.interface`  
**Use it:** `http://robot:8080`  
**Add scripts:** Edit `scripts` dictionary in `interface.py`
