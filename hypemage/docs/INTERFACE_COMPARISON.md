# Interface Architecture Comparison

## The Question

**Should we use FastAPI or raw WebSockets? Why have production mode in interface?**

## TL;DR - Recommendations

1. ✅ **Use FastAPI** (you already use it everywhere else)
2. ✅ **Make script launcher generic** (not hardcoded to scylla)
3. ⚠️ **Production mode is optional** (useful for remote start, but not critical)
4. ✅ **HTTP streaming for camera** (faster than WebSocket for video)

---

## Architecture V1 vs V2

### V1 (Current - `interface.py`)

```python
class InterfaceServer:
    def __init__(self):
        self.commands = {
            'scylla_debug': self._scylla_debug,          # Hardcoded
            'scylla_production': self._scylla_production, # Hardcoded
            'color_calibration': self._color_calibration, # Hardcoded
            'motor_test': self._motor_test,               # Hardcoded
        }
```

**Problems:**
- ❌ Adding new script requires code changes
- ❌ Can't pass custom arguments easily
- ❌ Hardcoded to scylla (what about other scripts?)
- ❌ Raw WebSocket server (reinventing the wheel)

### V2 (Proposed - `interface_v2.py`)

```python
class InterfaceServer:
    def __init__(self):
        self.scripts = {
            'scylla_debug': ScriptConfig(...),
            'color_calibration': ScriptConfig(...),
            'motor_test': ScriptConfig(...),
            'imu_calibration': ScriptConfig(...),
            # Add more easily!
        }
    
    async def run_script(self, script_id: str, extra_args: List[str]):
        """Generic launcher - works for ANY script"""
        ...
```

**Benefits:**
- ✅ Generic script launcher (add via config, not code)
- ✅ Easy to add new scripts (just add to dictionary)
- ✅ Can pass custom arguments
- ✅ Uses FastAPI (standard library you already use)
- ✅ REST API + WebSocket in one server

---

## Performance Comparison

### Video Streaming

| Method | Bandwidth | Latency | Code Complexity |
|--------|-----------|---------|-----------------|
| **HTTP multipart** (V2) | 100% | Low | Simple |
| **WebSocket + base64** (V1) | 133% (+33%) | Medium | Complex |

**Your existing camera servers already use HTTP multipart!**

```python
# camera/camera_test_server.py - YOU ALREADY DO THIS
@app.get('/')
async def video_stream():
    return StreamingResponse(cam.streamer(), 
                            media_type="multipart/x-mixed-replace; boundary=frame")
```

**Verdict:** HTTP streaming is better for video. Use WebSocket only for bundled debug data (FPS + detections + frame).

### Command/Control

| Method | Bidirectional | Auto-reconnect | REST API | Framework Support |
|--------|---------------|----------------|----------|-------------------|
| **FastAPI WebSocket** (V2) | ✅ | ✅ | ✅ | ✅ |
| **Raw WebSockets** (V1) | ✅ | Manual | ❌ | ❌ |

**Verdict:** FastAPI gives you WebSocket + REST API + static files in one package.

---

## "Production Mode in Interface" Question

### Use Cases for Interface

**Good uses (keep interface running):**
- ✅ Remote start/stop for debugging
- ✅ Running calibration scripts
- ✅ Motor/camera tests
- ✅ Monitoring logs remotely
- ✅ Emergency stop button
- ✅ Quick script launcher

**Competition use (don't need interface):**
- ❌ Just run `python -m hypemage.scylla` directly on boot
- ❌ Interface adds overhead (extra process)
- ❌ Interface isn't needed once robot is running

### Recommended Architecture

**Development/Testing:**
```bash
# On Pi: Start interface server
python -m hypemage.interface_v2

# In browser: Use dashboard to:
# - Run scylla_debug
# - Run color_calibration
# - Run motor_test
# - View logs
# - Stop/restart
```

**Competition:**
```bash
# On Pi: Systemd auto-starts robot directly
[Service]
ExecStart=/usr/bin/python3 -m hypemage.scylla
# No interface needed!
```

**Verdict:** Interface is for **development**, not competition. Production mode is optional (nice to have for remote start, but not critical).

---

## Modularity Comparison

### V1 - Adding a new script requires code changes:

```python
# interface.py - BEFORE
def __init__(self):
    self.commands = {
        'scylla_debug': self._scylla_debug,
        'scylla_production': self._scylla_production,
        'color_calibration': self._color_calibration,
        'motor_test': self._motor_test,
    }

# Need to add a method for each script!
def _imu_calibration(self, args):
    self.robot_process = subprocess.Popen([
        sys.executable, '-m', 'hypemage.calibrate_imu'
    ])
    return {'success': True}
```

### V2 - Adding a new script is just config:

```python
# interface_v2.py - AFTER
def __init__(self):
    self.scripts = {
        'scylla_debug': ScriptConfig(...),
        'color_calibration': ScriptConfig(...),
        'motor_test': ScriptConfig(...),
        
        # NEW SCRIPT - Just add config!
        'imu_calibration': ScriptConfig(
            name='IMU Calibration',
            module='hypemage.calibrate_imu',
            args=[],
            description='Calibrate IMU offsets',
            category='calibration'
        ),
    }
    
    # No new code needed! Generic launcher handles it.
```

**Verdict:** V2 is **much more modular**.

---

## Technology Stack Comparison

### Your Existing Codebase

```
✅ localization_server/main.py         → FastAPI
✅ camera/camera_test_server.py        → FastAPI
✅ test/localization/localization_system.py → FastAPI
❌ hypemage/interface.py               → Raw websockets
```

**Consistency:** You already use FastAPI everywhere. Why reinvent the wheel for interface.py?

### Dependencies

**V1 (Raw WebSockets):**
```
websockets==12.0
```

**V2 (FastAPI):**
```
fastapi==0.104.1
uvicorn==0.24.0
websockets==12.0  # (included with FastAPI)
```

**Verdict:** FastAPI is already a dependency (you use it). No extra bloat.

---

## Migration Path

### Option 1: Keep both (recommended for now)

```bash
# Old interface (if you want to keep it)
python -m hypemage.interface

# New interface (test it out)
python -m hypemage.interface_v2
```

**Benefits:**
- Test V2 without breaking V1
- Migrate gradually
- Compare performance

### Option 2: Replace entirely

```bash
# Rename files
mv hypemage/interface.py hypemage/interface_old.py
mv hypemage/interface_v2.py hypemage/interface.py

# Update systemd
[Service]
ExecStart=/usr/bin/python3 -m hypemage.interface
```

---

## Final Recommendations

### ✅ DO

1. **Use FastAPI** - You already use it everywhere else
2. **Generic script launcher** - Don't hardcode script names
3. **HTTP streaming for camera** - Faster than WebSocket
4. **Keep interface for development** - Super useful for testing
5. **Boot directly to scylla in competition** - Skip interface overhead

### ❌ DON'T

1. **Don't reinvent WebSocket server** - FastAPI does it better
2. **Don't hardcode script names** - Use ScriptConfig pattern
3. **Don't use interface in production** - Direct launch is simpler
4. **Don't use WebSocket for video** - HTTP multipart is faster

### 🤷 OPTIONAL

1. **Production mode command** - Nice to have, not critical
2. **Keep both versions** - Migrate when ready
3. **Add HTTP camera endpoint** - Only if you need it

---

## Example Usage (V2)

### Client sends:

```json
// Run main robot with debug
{"command": "run_script", "script_id": "scylla_debug", "args": []}

// Run color calibration
{"command": "run_script", "script_id": "color_calibration", "args": []}

// Run custom script with extra args
{"command": "run_script", "script_id": "motor_test", "args": ["--motor", "0", "--speed", "0.5"]}

// Stop current script
{"command": "stop_script"}

// Get status
{"command": "get_status"}

// List all available scripts
{"command": "get_scripts"}
```

### Server responds:

```json
// Success
{"type": "response", "data": {"success": true, "pid": 12345, "script": "Robot (Debug Mode)"}}

// Process started notification (broadcast to all clients)
{"type": "process_started", "script": "scylla_debug", "pid": 12345}

// Process stopped notification
{"type": "process_stopped", "script": "scylla_debug", "exit_code": 0}

// Available scripts
{
  "type": "response",
  "data": {
    "robot": [
      {"id": "scylla_debug", "name": "Robot (Debug Mode)", "description": "..."},
      {"id": "scylla_production", "name": "Robot (Production Mode)", "description": "..."}
    ],
    "calibration": [
      {"id": "color_calibration", "name": "Color Calibration", "description": "..."},
      {"id": "imu_calibration", "name": "IMU Calibration", "description": "..."}
    ],
    "test": [
      {"id": "motor_test", "name": "Motor Test", "description": "..."}
    ]
  }
}
```

---

## Code Comparison

### Adding IMU Calibration Script

**V1 (interface.py) - 20 lines of code:**

```python
def __init__(self):
    self.commands = {
        # ... existing commands
        'imu_calibration': self._imu_calibration,  # Add here
    }

def _imu_calibration(self, args):
    """Launch IMU calibration script"""
    with self.process_lock:
        if self.robot_process:
            return {'success': False, 'error': 'Robot already running'}
        
        logger.info("Launching IMU calibration")
        self.robot_process = subprocess.Popen([
            sys.executable, '-m', 'hypemage.calibrate_imu'
        ])
        
        return {
            'success': True,
            'pid': self.robot_process.pid,
            'message': 'IMU calibration started'
        }
```

**V2 (interface_v2.py) - 7 lines of config:**

```python
def __init__(self):
    self.scripts = {
        # ... existing scripts
        'imu_calibration': ScriptConfig(
            name='IMU Calibration',
            module='hypemage.calibrate_imu',
            args=[],
            description='Calibrate IMU offsets and magnetometer',
            category='calibration'
        ),
    }
    # Done! Generic launcher handles everything.
```

**Verdict:** V2 is **65% less code** and **more maintainable**.

---

## Summary Table

| Feature | V1 (interface.py) | V2 (interface_v2.py) |
|---------|-------------------|----------------------|
| **Framework** | Raw websockets | FastAPI |
| **Script Addition** | Code changes | Config only |
| **Custom Arguments** | Hard | Easy |
| **HTTP Endpoints** | No | Yes |
| **Static Files** | Manual | Built-in |
| **Camera Streaming** | WebSocket (slow) | HTTP (fast) |
| **Consistency** | Different from rest | Same as rest |
| **Code for New Script** | ~20 lines | ~7 lines |
| **Modularity** | Medium | High |
| **Extensibility** | Hard | Easy |

**Winner:** V2 (FastAPI) ✅

---

## Next Steps

1. **Test interface_v2.py** - Run it, see if you like it
2. **Update client UI** - Use new WebSocket API
3. **Add camera endpoint** - HTTP streaming like camera_test_server.py
4. **Decide on migration** - Keep both or switch entirely
5. **Add your custom scripts** - IMU calibration, etc.

**Try it now:**

```bash
# Install FastAPI if not already
pip install fastapi uvicorn

# Run new interface
python -m hypemage.interface_v2

# Open browser
http://localhost:8080
```
