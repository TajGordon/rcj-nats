# Interface System - Quick Start

## One Command Setup

### On the Robot

```bash
# 1. Install dependencies (if not already)
pip install fastapi uvicorn

# 2. Start the interface
python -m hypemage.interface
```

**Output:**
```
Starting Robot Interface Server
Dashboard: http://0.0.0.0:8080
WebSocket: ws://0.0.0.0:8080/ws
```

### On Your Laptop/Phone

```
Open browser to: http://robot-ip:8080
```

**Done!** You can now control the robot from the web dashboard.

---

## What You Can Do

### Start Robot in Debug Mode

1. Click **"Robot (Debug)"** button
2. Robot starts with debug output
3. See camera feed and motor status (when implemented)

### Run Calibration

1. Click **"Color Calibration"** button  
2. Calibrate HSV ranges for ball/goal detection

### Test Motors

1. Click **"Motor Test"** button
2. Test individual motor control

### Stop Everything

1. Click **"Stop"** button
2. Current process terminates gracefully

---

## Adding Your Own Scripts

Edit `hypemage/interface.py`:

```python
# Around line 58, add to self.scripts:
'my_script': ScriptConfig(
    name='My Cool Script',
    module='path.to.my_script',
    args=[],
    description='What it does',
    category='test'  # or 'calibration', 'robot', 'utility'
),
```

Restart interface, script appears in dashboard automatically!

---

## Auto-Start on Boot

```bash
sudo nano /etc/systemd/system/robot-interface.service
```

Paste:
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

Enable:
```bash
sudo systemctl enable robot-interface
sudo systemctl start robot-interface
```

---

## Competition Mode

**Don't use interface in competition!** Just boot directly to scylla:

```bash
# Remove interface from startup
sudo systemctl disable robot-interface

# Create scylla service instead
sudo nano /etc/systemd/system/robot.service
```

```ini
[Service]
ExecStart=/usr/bin/python3 -m hypemage.scylla
```

Interface is for **development**, not competition.

---

## File Structure

```
hypemage/
├── interface.py              # ⭐ Main server (run this)
├── client/                   # Web dashboard
│   ├── index.html
│   ├── app.js
│   └── style.css
└── docs/
    ├── INTERFACE_README.md   # Detailed guide
    └── QUICK_START.md        # This file
```

---

## That's It!

- **Start:** `python -m hypemage.interface`
- **Use:** `http://robot:8080`
- **Add scripts:** Edit `interface.py` → `self.scripts` dictionary

Simple, clean, one file. No version confusion. 🎯
