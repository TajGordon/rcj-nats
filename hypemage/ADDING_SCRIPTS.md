# Adding Scripts to the Robot Dashboard

## Quick Guide: How to Add New Test Scripts

The interface system is **100% modular**. Adding new scripts requires **ZERO code changes** to the web dashboard - just edit one Python dictionary!

---

## Step-by-Step: Add a New Script

### 1. Open `hypemage/interface.py`

### 2. Find the `self.scripts` dictionary (around line 59)

### 3. Add your script entry:

```python
self.scripts: Dict[str, ScriptConfig] = {
    # ... existing scripts ...
    
    # YOUR NEW SCRIPT
    'my_new_test': ScriptConfig(
        name='My New Test',                    # Display name in UI
        module='path.to.your.module',          # Python module path
        args=['--debug', '--verbose'],         # Default arguments
        description='What this script does',   # Shown in tooltips
        category='test'                        # 'robot' | 'calibration' | 'test' | 'utility'
    ),
}
```

### 4. Restart the interface server

### 5. **Done!** Script appears in dashboard automatically

---

## Complete Example: Adding a Solenoid Test

```python
'solenoid_test': ScriptConfig(
    name='Solenoid Kick Test',
    module='solenoid.kick',                # Runs: python -m solenoid.kick
    args=['--power', '80'],                # Default to 80% power
    description='Test kicker solenoid with adjustable power',
    category='test'
),
```

---

## Script Categories

Choose the right category for organization:

| Category | Purpose | Examples |
|----------|---------|----------|
| `robot` | Main robot programs | Full robot control, competition mode |
| `calibration` | Calibration utilities | Color calibration, IMU offsets |
| `test` | Hardware/component tests | Motor test, camera test, sensor test |
| `utility` | Helper tools | Log viewer, data recorder |

---

## How Commands Are Sent

### From Web Dashboard:

```javascript
// Dashboard button click
startRobotDebug('storm') {
    this.sendCommand('storm', 'run_script', { 
        script_id: 'scylla_debug'  // Matches key in self.scripts
    });
}
```

### WebSocket Message Flow:

```
1. User clicks "▶️ Debug" button
2. JavaScript sends: {"command": "run_script", "script_id": "scylla_debug"}
3. Python receives message via WebSocket
4. Looks up "scylla_debug" in self.scripts
5. Runs: python -m hypemage.scylla --debug
6. Sends PID back to dashboard
7. Dashboard shows "Running" status
```

---

## Advanced: Custom Arguments

You can pass custom arguments at runtime:

```python
# In interface.py
'motor_speed_test': ScriptConfig(
    name='Motor Speed Test',
    module='motors.motor',
    args=[],  # No defaults
    description='Test motor at specific speed',
    category='test'
),
```

```javascript
// From dashboard (custom implementation)
this.sendCommand('storm', 'run_script', { 
    script_id: 'motor_speed_test',
    args: ['--motor', '0', '--speed', '50']  // Extra args
});
```

Server executes: `python -m motors.motor --motor 0 --speed 50`

---

## Adding a Custom Button to Dashboard

If you want a dedicated button (not just debug mode):

### 1. Add script to `interface.py` as shown above

### 2. Add method to `app.js`:

```javascript
startMotorTest(robotName) {
    this.sendCommand(robotName, 'run_script', { 
        script_id: 'motor_test'  // Must match interface.py key
    });
},
```

### 3. Add button to `index.html`:

```html
<button @click="startMotorTest('storm')" class="btn btn-primary">
    🔧 Motor Test
</button>
```

### 4. **Done!** New button launches your script

---

## Real-World Examples

### Example 1: Line Sensor Calibration

```python
'line_sensor_cal': ScriptConfig(
    name='Line Sensor Calibration',
    module='sensors.line_calibration',
    args=['--duration', '30'],
    description='Calibrate line sensor thresholds over 30 seconds',
    category='calibration'
),
```

### Example 2: Dribbler Speed Test

```python
'dribbler_speed': ScriptConfig(
    name='Dribbler Speed Test',
    module='motors.dribbler_test',
    args=['--ramp'],  # Gradually increase speed
    description='Test dribbler motor with speed ramping',
    category='test'
),
```

### Example 3: IMU Logger

```python
'imu_logger': ScriptConfig(
    name='IMU Data Logger',
    module='sensors.imu_logger',
    args=['--output', 'logs/imu.csv'],
    description='Log IMU data to CSV for analysis',
    category='utility'
),
```

---

## Testing Your New Script

1. **Add script entry to `interface.py`**
2. **Restart interface server:**
   ```bash
   python -m hypemage.interface
   ```
3. **Open dashboard:** `http://localhost:8080`
4. **Check browser console** for connection status
5. **Click your button** and verify script starts
6. **Check terminal** for process output

---

## Debugging

### Script not showing up?

- Check syntax in `interface.py`
- Verify dictionary key is unique
- Restart the server
- Check browser console for errors

### Script won't start?

- Verify module path is correct
- Test manually: `python -m your.module`
- Check server logs for error messages
- Ensure Python can find the module

### Process starts but dashboard doesn't update?

- Check WebSocket connection (green badge in header)
- Verify `script_id` in JavaScript matches Python key
- Check browser console for WebSocket errors

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│ Web Dashboard (Vue.js)                          │
│  • index.html (UI structure)                    │
│  • app.js (WebSocket client)                    │
│  • style.css (styling)                          │
└────────────┬────────────────────────────────────┘
             │ WebSocket (port 8080)
             ↓
┌─────────────────────────────────────────────────┐
│ Interface Server (FastAPI + Python)             │
│  • interface.py                                 │
│    ├─ InterfaceServer class                     │
│    │   └─ self.scripts = {...}  ← ADD HERE!     │
│    ├─ run_script() - launches subprocess        │
│    ├─ stop_script() - kills subprocess          │
│    └─ WebSocket handlers                        │
└────────────┬────────────────────────────────────┘
             │ subprocess.Popen()
             ↓
┌─────────────────────────────────────────────────┐
│ Your Scripts (Python modules)                   │
│  • hypemage.scylla (main robot)                 │
│  • motors.motor (motor tests)                   │
│  • camera.camera_test_server (camera test)      │
│  • YOUR_NEW_SCRIPT.py ← ADD HERE!               │
└─────────────────────────────────────────────────┘
```

---

## Key Files

| File | Purpose | Edit When |
|------|---------|-----------|
| `hypemage/interface.py` | **Script registry** | Adding ANY new script |
| `hypemage/client/app.js` | Dashboard logic | Adding custom buttons |
| `hypemage/client/index.html` | UI structure | Adding custom buttons |
| `hypemage/client/style.css` | Styling | Changing appearance |

---

## The Magic: No Code Generation Needed!

The system is **declarative**:

1. You **declare** what scripts exist (in Python dict)
2. Dashboard **automatically** reads available scripts
3. WebSocket **generically** handles all commands
4. Process launcher **universally** runs any module

**No hardcoding!** No switch statements! No code generation!

Just add to the dictionary and you're done! 🎉

---

## Summary

**To add a new script:**

1. ✅ Add `ScriptConfig` entry to `interface.py`
2. ✅ Restart server
3. ✅ (Optional) Add custom button to HTML/JS

**That's it!** The modular design handles everything else automatically.

**No web app changes needed** for basic script launching!
