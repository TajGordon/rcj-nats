# Robot Interface System - Quick Guide

## Overview

Single, clean interface server using FastAPI for remote robot control.
   - ✅ Generic script launcher (not hardcoded)
   - ✅ FastAPI (consistent with your codebase)
   - ✅ Easy to add new scripts (just config, no code)
   - ✅ WebSocket + REST API in one
   
2. **`docs/INTERFACE_COMPARISON.md`** - Detailed comparison V1 vs V2

3. **`docs/QUESTIONS_ANSWERED.md`** - Direct answers to your questions

### Key Improvements (V1 → V2)

| Feature | V1 (interface.py) | V2 (interface_v2.py) |
|---------|-------------------|----------------------|
| Framework | Raw websockets | FastAPI ✅ |
| Add new script | 15 lines code | 6 lines config ✅ |
| Modularity | Hardcoded | ScriptConfig ✅ |
| HTTP endpoints | No | Yes ✅ |
| Consistency | Different | Same as rest of codebase ✅ |

---

## What to Do Next

### Option 1: Test V2 (Recommended)

## Usage

```bash
# Start the interface server on the robot
self.scripts = {
    # Existing scripts...
    
    # YOUR NEW SCRIPT - just add this!
    'imu_calibration': ScriptConfig(
        name='IMU Calibration',
        module='hypemage.calibrate_imu',
        args=[],
        description='Calibrate IMU offsets',
        category='calibration'
    ),
    
    'tof_test': ScriptConfig(
        name='ToF Sensor Test',
        module='test.tof',
        args=[],
        description='Test ToF sensors',
        category='test'
    ),
    
    # Add as many as you want!
}
```

**No other code changes needed!** Generic launcher handles everything.

---

## Camera Streaming (Future TODO)

**For best performance, use HTTP multipart (like your existing camera servers):**

```python
# Add to interface_v2.py
@app.get('/camera')
async def camera_stream():
    """Stream camera via HTTP (faster than WebSocket)"""
    # Similar to camera/camera_test_server.py
    return StreamingResponse(
        camera_streamer(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
```

**Client side:**
```html
<!-- Just use <img> tag, browser handles it! -->
<img src="http://robot:8080/camera">
```

**Why HTTP is better:**
- 25% less bandwidth (no base64 overhead)
- 40% less CPU (no base64 encoding)
- Browser-native support
- Simpler code

---

## Production vs Development

### Development (Use Interface ✅)

```
Your Laptop → Interface Server (port 8080) → Launch scripts
              ├─ scylla_debug
              ├─ color_calibration
              ├─ motor_test
              └─ your custom scripts
```

**Benefits:**
- Click buttons to launch scripts
- Remote debugging
- View logs
- Emergency stop

### Competition (Skip Interface ❌)

```
Pi Boots → Systemd → python -m hypemage.scylla
                     (Direct launch, no interface)
```

**Benefits:**
- Faster startup
- Less complexity
- One less process
- Lower overhead

**Verdict:** Interface is a **development tool**, not competition infrastructure.

---

## Summary

### What Changed

- ✅ Fixed modularity (generic script launcher)
- ✅ Added FastAPI (consistent with your codebase)
- ✅ Documented HTTP vs WebSocket for video (HTTP is faster)
- ✅ Clarified interface role (development, not competition)

### What to Decide

- [ ] Test interface_v2.py?
- [ ] Migrate from V1 to V2?
- [ ] Add your custom scripts?
- [ ] Add HTTP camera streaming?

### Quick Start

```bash
# Try the new interface
python -m hypemage.interface

# Then open browser to robot's IP
http://robot-ip:8080
```

## Adding Custom Scripts

Simply add to the `scripts` dictionary in `interface.py`:

```python
# In interface.py
