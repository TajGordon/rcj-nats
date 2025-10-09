# Quick Start Guide - Interface System

## 🚀 Getting Started in 5 Minutes

### On the Robot (Raspberry Pi)

```bash
# 1. Navigate to project
cd ~/rcj-nats

# 2. Start interface server
python -m hypemage.interface

# You should see:
# INFO - Interface server listening on ws://0.0.0.0:8080
# INFO - Clients can connect to control robot
```

### On Your Laptop/Phone

```bash
# Option 1: If you have the client files on robot
# Just open browser to: http://robot.local:8080

# Option 2: If you need to copy client files to robot first
scp -r hypemage/client/* pi@robot.local:~/rcj-nats/hypemage/client/
```

**Then open browser**: `http://robot.local:8080/client/index.html`

---

## 📱 Using the Dashboard

### Starting the Robot

1. Click **"▶️ Start Robot (Debug)"**
   - Robot starts with debug enabled
   - Camera feed will appear
   - Motor status will update

2. OR click **"▶️ Start Robot (Production)"**
   - Robot starts without debug overhead
   - Use for competition

### Stopping the Robot

- Click **"⏹️ Stop Robot"**
- Robot will shut down gracefully

### Utilities

- **🎨 Calibrate Ball Color**: Opens HSV color calibration tool
- **🎨 Calibrate Blue/Yellow Goal**: Same for goals
- **⚙️ Motor Test**: Launches motor test script

---

## 🔧 Auto-Start on Boot

To make interface start automatically when robot boots:

```bash
# 1. Create systemd service file
sudo nano /etc/systemd/system/robot-interface.service
```

Paste this:
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
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 2. Enable and start
sudo systemctl enable robot-interface.service
sudo systemctl start robot-interface.service

# 3. Check status
sudo systemctl status robot-interface.service
```

Now interface starts automatically on boot!

---

## 🤖 Multiple Robots (Necron & Storm)

### Setup

**On Necron**:
```bash
ssh pi@necron.local
cd ~/rcj-nats
python -m hypemage.interface
```

**On Storm**:
```bash
ssh pi@storm.local
cd ~/rcj-nats
python -m hypemage.interface
```

### Access

Open browser with **two tabs**:
- Tab 1: `http://necron.local:8080/client/index.html`
- Tab 2: `http://storm.local:8080/client/index.html`

Control each independently!

---

## 🛠️ Adding Custom Scripts

Edit `hypemage/interface.py`:

```python
def __init__(self):
    self.commands = {
        # ... existing commands ...
        'my_custom_script': self._my_custom_script,  # Add this
    }

def _my_custom_script(self, args):
    """Launch custom script"""
    try:
        proc = subprocess.Popen([
            sys.executable, 
            '-m', 
            'my_module.my_script'
        ])
        return {'success': True, 'pid': proc.pid}
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

Use from client JavaScript:
```javascript
// Add button in index.html
<button id="btn-custom">My Script</button>

// Add handler in app.js
document.getElementById('btn-custom').addEventListener('click', () => {
    sendCommand('my_custom_script');
});
```

---

## 📊 Debug Data

When robot is started with debug:

### WebSocket Ports
- **8080**: Commands & status (interface server)
- **8765**: Debug data (camera, motors, etc.)

### Client Auto-Connects
- Client connects to both ports automatically
- Camera feed updates in real-time
- Motor speeds show as gauges

### Debug Data Types
- `CameraDebugData`: Frame, FPS, detections, HSV ranges
- `MotorDebugData`: Speeds, watchdog status
- `LocalizationDebugData`: Position, heading, confidence
- `ButtonDebugData`: Button states, last press
- `FSMDebugData`: Current state, component status

---

## 🔒 Security (Competition Mode)

For competition (public networks):

1. **Bind to localhost only**:
   ```python
   # In interface.py main():
   asyncio.run(server.run(host='127.0.0.1', port=8080))
   ```

2. **SSH tunnel from laptop**:
   ```bash
   ssh -L 8080:localhost:8080 pi@robot.local
   ```

3. **Access via tunnel**:
   - Browser: `http://localhost:8080`
   - Tunnels to robot securely

---

## 🐛 Troubleshooting

### "Cannot connect to interface server"

```bash
# Check interface is running
ssh pi@robot.local
ps aux | grep interface.py

# If not running, start it
python -m hypemage.interface
```

### "No camera feed in debug mode"

```bash
# Check robot is running in debug mode
# Look for: "Debug server listening on ws://0.0.0.0:8765"

# Check browser console (F12)
# Should see: "Connected to debug server"
```

### "Robot won't stop"

```bash
# Force stop
ssh pi@robot.local
pkill -f scylla.py

# Check what's running
ps aux | grep python
```

### Check Logs

```bash
# On robot
tail -f ~/robot_logs/robot.log

# Or from client
# Click "🔄 Refresh" in Logs panel
```

---

## 📝 Example Workflow

**Testing a new feature**:

1. SSH to robot, start interface
2. Open dashboard on laptop
3. Click "Start Robot (Debug)"
4. Watch camera feed, see detections
5. Adjust code, click "Stop Robot"
6. Restart to test changes
7. Review logs for errors

**Competition day**:

1. Set interface to auto-start on boot
2. Turn on robot, interface starts automatically
3. Connect laptop to robot's network
4. Open dashboard
5. Click "Start Robot (Production)"
6. Robot runs, no debug overhead

---

## ✅ What You Have Now

- ✅ Interface server (`interface.py`)
- ✅ Web dashboard (`client/`)
- ✅ Start/stop robot remotely
- ✅ Debug data streaming (camera, motors)
- ✅ Extensible command system
- ✅ Multi-robot ready
- ✅ Auto-start on boot (systemd)
- ✅ Secure tunnel option

**Everything works with simplicity at heart** ❤️
