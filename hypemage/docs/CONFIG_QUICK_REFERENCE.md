# ⚡ Bot-Specific Config Quick Reference

## Setup (One-Time)

### Storm Robot
```bash
export ROBOT_NAME=storm
# OR
sudo hostnamectl set-hostname storm-robot
```

### Necron Robot
```bash
export ROBOT_NAME=necron
# OR
sudo hostnamectl set-hostname necron-robot
```

---

## Python Usage

### Load Config
```python
from hypemage.config import load_config, get_robot_id

# Auto-detect robot
config = load_config(get_robot_id())

# Explicit robot
config = load_config('storm')
config = load_config('necron')
```

### Save Config
```python
from hypemage.config import save_config

save_config('storm', updated_config)
save_config('necron', updated_config)
```

### Use Camera
```python
from hypemage.camera import CameraProcess

# Auto-detect robot
camera = CameraProcess()

# Explicit robot
camera = CameraProcess(robot_id='storm')
camera = CameraProcess(robot_id='necron')
```

---

## CLI Usage

### Camera Debug
```bash
# Auto-detect
python -m hypemage.scripts.camera_debug

# Explicit robot
python -m hypemage.scripts.camera_debug --robot storm
python -m hypemage.scripts.camera_debug --robot necron
```

### Camera Calibration
```bash
# Auto-detect
python -m hypemage.scripts.camera_calibrate

# Explicit robot
python -m hypemage.scripts.camera_calibrate --robot storm
python -m hypemage.scripts.camera_calibrate --robot necron
```

---

## Web Dashboard

1. Select robot (Storm or Necron)
2. Open calibration widget
3. Adjust HSV sliders
4. Click "Save Calibration"
5. ✅ Saved to `config.json[robot_id]`

---

## Config File Structure

```json
{
  "storm": {
    "camera": { ... },
    "hsv_ranges": { ... },
    "detection": { ... },
    "motors": { ... }
  },
  "necron": {
    "camera": { ... },
    "hsv_ranges": { ... },
    "detection": { ... },
    "motors": { ... }
  }
}
```

**Location**: `hypemage/config.json`

---

## Robot Detection Priority

1. CLI arg: `--robot storm`
2. Env var: `ROBOT_NAME=storm`
3. Hostname: contains 'storm' or 'necron'
4. Default: 'storm'

---

## Common Tasks

### Check Robot Identity
```bash
python -c "from hypemage.config import get_robot_id; print(get_robot_id())"
```

### View Storm Config
```bash
python -c "from hypemage.config import load_config; import json; print(json.dumps(load_config('storm'), indent=2))"
```

### View Necron Config
```bash
python -c "from hypemage.config import load_config; import json; print(json.dumps(load_config('necron'), indent=2))"
```

### Test Camera Init
```python
from hypemage.camera import CameraProcess
try:
    camera = CameraProcess(robot_id='storm')
    print("✅ Storm camera initialized")
except Exception as e:
    print(f"❌ Error: {e}")
```

---

## Troubleshooting

### Wrong Robot Detected?
```bash
# Check current detection
python -c "from hypemage.config import get_robot_id; print(get_robot_id())"

# Set explicitly
export ROBOT_NAME=necron
```

### Config Not Saving?
1. Check WebSocket connection (port 8765)
2. Verify debug manager running
3. Check file permissions on config.json

### HSV Not Persisting?
1. Verify correct robot selected
2. Check console for save confirmation
3. Reload config.json to verify

---

## Files Changed

- ✅ `config.json` - Bot-specific config
- ✅ `config.py` - Config management
- ✅ `camera.py` - Uses bot config
- ✅ `camera_debug.py` - CLI arg added
- ✅ `camera_calibrate.py` - CLI arg added
- ✅ `debug_manager.py` - Saves by robot
- ✅ `app.js` - Sends robot_id
- ❌ `camera_config.json` - DELETED

---

## Documentation

- `CONFIGURATION_SYSTEM.md` - Complete guide
- `CONFIG_MIGRATION_SUMMARY.md` - Implementation details
- `BOT_CONFIG_COMPLETE.md` - Executive summary
- `CONFIG_QUICK_REFERENCE.md` - This file

---

## Status

✅ **COMPLETE AND TESTED**  
✅ Ready for hardware deployment  
✅ Supports Storm and Necron independently  

---

*Quick reference for bot-specific configuration system*
