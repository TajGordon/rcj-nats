# Quick Reference: Robot Dashboard

## Start the Server

```bash
cd hypemage
python -m hypemage.interface
```

Server runs on: `http://localhost:8080`

---

## Add a New Script (30 seconds!)

### 1. Edit `hypemage/interface.py`

Find line ~59 where `self.scripts` is defined, add:

```python
'my_script': ScriptConfig(
    name='My Script Name',           # Shows in UI
    module='path.to.module',         # python -m path.to.module
    args=['--arg1', 'value'],        # Default args
    description='What it does',      # Tooltip text
    category='test'                  # test|robot|calibration|utility
),
```

### 2. Restart server

```bash
python -m hypemage.interface
```

### 3. Done! ✅

Script now available via dashboard!

---

## Web Dashboard Features

### Views
- **Both**: Storm and Necron side-by-side
- **Storm**: Storm only (detailed view)
- **Necron**: Necron only (detailed view)

### Widgets
- **Controls**: Start/Stop robot
- **Camera**: Live camera feed (resizable)
- **Motors**: 5 motor speeds + temps
- **Logs**: Scrolling log output (resizable)
- **Status**: Connection info

### Controls
- **Resize**: Drag corner on Camera/Logs widgets
- **Drag-Drop**: Click and drag widgets (single view only)
- **Toggle**: Click widget buttons to show/hide

---

## File Structure

```
hypemage/
├── interface.py          ← ADD SCRIPTS HERE!
├── scylla.py             ← Main robot code
├── ADDING_SCRIPTS.md     ← Full documentation
├── client/
│   ├── index.html        ← Dashboard UI
│   ├── app.js            ← Dashboard logic
│   └── style.css         ← Dashboard styling
└── debug/
    └── ...
```

---

## Common Tasks

### Add Motor Test Script

```python
'motor_speed': ScriptConfig(
    name='Motor Speed Test',
    module='motors.motor',
    args=['--test'],
    description='Test individual motors',
    category='test'
),
```

### Add Camera Calibration

```python
'camera_cal': ScriptConfig(
    name='Camera Calibration',
    module='camera.calibrate',
    args=['--interactive'],
    description='Calibrate camera parameters',
    category='calibration'
),
```

### Add Sensor Logger

```python
'sensor_log': ScriptConfig(
    name='Sensor Logger',
    module='sensors.logger',
    args=['--output', 'logs/sensors.csv'],
    description='Log all sensor data to CSV',
    category='utility'
),
```

---

## Troubleshooting

### Dashboard won't connect?
1. Check server is running: `python -m hypemage.interface`
2. Check URL: `http://localhost:8080`
3. Check browser console (F12) for errors

### Script won't start?
1. Verify module path: `python -m your.module.path`
2. Check server terminal for error messages
3. Verify script_id matches interface.py key

### Widgets layout broken?
1. Hard refresh: Ctrl+Shift+R (Windows) / Cmd+Shift+R (Mac)
2. Clear browser cache
3. Check browser console for CSS errors

---

## Architecture

```
Browser ←WebSocket→ interface.py ←subprocess→ Your Scripts
```

1. User clicks button in browser
2. WebSocket sends command to `interface.py`
3. `interface.py` launches script via `subprocess.Popen()`
4. Process runs, dashboard shows status
5. User clicks stop, process terminates

---

## Key Files

| File | Purpose |
|------|---------|
| `interface.py` | Script registry + WebSocket server |
| `client/index.html` | Dashboard UI |
| `client/app.js` | WebSocket client + Vue logic |
| `client/style.css` | Styling |
| `ADDING_SCRIPTS.md` | Full documentation |

---

## That's It!

**No complex setup. No configuration files. No build step.**

Just add scripts to the Python dictionary and they work! 🎉

See `ADDING_SCRIPTS.md` for detailed examples and advanced usage.
