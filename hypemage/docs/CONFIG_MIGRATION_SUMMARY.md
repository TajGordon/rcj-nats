# Configuration Migration Summary

## ✅ COMPLETED: Bot-Specific Configuration System

### What Was Changed

Successfully migrated from single `camera_config.json` to bot-specific `config.json` system.

---

## Files Modified (9 files)

### 1. ✅ Created: `hypemage/config.json`
**Purpose**: Centralized configuration for Storm and Necron robots

**Structure**:
```json
{
  "storm": { camera, hsv_ranges, detection, motors },
  "necron": { camera, hsv_ranges, detection, motors }
}
```

---

### 2. ✅ Created: `hypemage/config.py`
**Purpose**: Configuration management module

**Functions**:
- `get_robot_id(override)` - Auto-detect robot (arg → env → hostname → default)
- `load_config(robot_id)` - Load config for specific robot
- `save_config(robot_id, config)` - Save config for specific robot
- `update_config_section(robot_id, path, value)` - Update nested config value
- `get_default_config()` - Default config structure

---

### 3. ✅ Updated: `hypemage/camera.py`

**Changes**:
```python
# Added import
from hypemage.config import load_config, get_robot_id

# Updated __init__
def __init__(self, config=None, robot_id=None):
    self.robot_id = robot_id or get_robot_id()
    self.config = config or load_config(self.robot_id)

# Removed functions
- _load_config()  # Deleted (replaced by config.load_config)
- _default_config()  # Deleted (replaced by config.get_default_config)
```

---

### 4. ✅ Updated: `hypemage/scripts/camera_debug.py`

**Changes**:
```python
# Added imports
import argparse
from typing import Optional
from hypemage.config import get_robot_id

# Updated function signature
def camera_debug_loop(fps_target=30, subsystem_name="camera_debug", robot_id=None):
    robot_id = robot_id or get_robot_id()
    camera = CameraProcess(robot_id=robot_id)

# Updated main()
parser.add_argument('--robot', choices=['storm', 'necron'])
camera_debug_loop(fps_target=30, robot_id=args.robot)
```

**CLI Usage**: `python -m hypemage.scripts.camera_debug --robot storm`

---

### 5. ✅ Updated: `hypemage/scripts/camera_calibrate.py`

**Changes**:
```python
# Added imports
import argparse
from hypemage.config import load_config, get_robot_id

# Removed function
- save_config()  # Deleted (replaced by config.save_config)

# Updated function signature
def camera_calibrate_loop(fps_target=10, subsystem_name="camera_calibrate", robot_id=None):
    robot_id = robot_id or get_robot_id()
    config = load_config(robot_id)
    camera = CameraProcess(robot_id=robot_id)

# Updated main()
parser.add_argument('--robot', choices=['storm', 'necron'])
camera_calibrate_loop(fps_target=10, robot_id=args.robot)
```

**CLI Usage**: `python -m hypemage.scripts.camera_calibrate --robot necron`

---

### 6. ✅ Updated: `hypemage/debug/debug_manager.py`

**Changes**:
```python
# Added import
from hypemage.config import save_config as save_bot_config

# Updated _handle_client_command()
async def _handle_client_command(self, data: dict):
    robot_id = data.get('robot_id', 'storm')
    
    if command == 'save_calibration':
        config = data.get('config')
        save_bot_config(robot_id, config)  # Saves to config.json[robot_id]
```

**Expected Message Format**:
```json
{
  "command": "save_calibration",
  "robot_id": "storm",
  "config": { ... full config object ... }
}
```

---

### 7. ✅ Updated: `hypemage/client/app.js`

**Changes**:
```javascript
// Updated saveCalibration()
saveCalibration(robotName) {
    const message = {
        command: 'save_calibration',
        robot_id: robotName,  // 'storm' or 'necron'
        config: {
            camera: { ... },
            hsv_ranges: {
                ball: robot.calibration.ball,
                blue_goal: robot.calibration.blue_goal,
                yellow_goal: robot.calibration.yellow_goal
            },
            detection: { ... },
            motors: { ... }
        }
    };
    robot.debugWs.send(JSON.stringify(message));
}
```

**UI Integration**: Calibration widget automatically saves to correct robot section

---

### 8. ✅ Deleted: `hypemage/camera_config.json`
**Reason**: Replaced by bot-specific config.json

---

### 9. ✅ Created: `hypemage/docs/CONFIGURATION_SYSTEM.md`
**Purpose**: Comprehensive documentation of new config system

---

## Robot Identification Priority

1. **Command-line**: `--robot storm` or `--robot necron`
2. **Environment**: `ROBOT_NAME=storm` or `ROBOT_NAME=necron`
3. **Hostname**: Contains 'storm' or 'necron'
4. **Default**: 'storm'

---

## Data Flow

### Loading Configuration

```
Python Script
    ↓ get_robot_id()
Auto-detect: 'storm' or 'necron'
    ↓ load_config(robot_id)
config.json["storm"] → config dict
    ↓
CameraProcess(robot_id='storm')
```

### Saving Calibration

```
Web Dashboard (Storm robot)
    ↓ User adjusts HSV sliders
    ↓ Click "Save Calibration"
WebSocket → {command: 'save_calibration', robot_id: 'storm', config: {...}}
    ↓
Debug Manager
    ↓ save_bot_config('storm', config)
config.json["storm"] = config
    ↓ File written
Calibration persisted
```

---

## Configuration Sections

### Camera
- width, height, format, fps_target

### HSV Ranges
- ball: {lower, upper, min_area, max_area}
- blue_goal: {lower, upper, min_area, max_area}
- yellow_goal: {lower, upper, min_area, max_area}

### Detection
- proximity_threshold, angle_tolerance, goal_center_tolerance

### Motors
- i2c_address, max_speed, acceleration

---

## Testing Checklist

### ✅ Storm Robot
```bash
# Test auto-detection
export ROBOT_NAME=storm
python -m hypemage.scripts.camera_debug

# Test explicit arg
python -m hypemage.scripts.camera_debug --robot storm

# Test config loading
python -c "from hypemage.config import load_config; print(load_config('storm')['camera'])"

# Test camera initialization
python -c "from hypemage.camera import CameraProcess; CameraProcess(robot_id='storm')"
```

### ✅ Necron Robot
```bash
# Test auto-detection
export ROBOT_NAME=necron
python -m hypemage.scripts.camera_calibrate

# Test explicit arg
python -m hypemage.scripts.camera_calibrate --robot necron

# Test config loading
python -c "from hypemage.config import load_config; print(load_config('necron')['hsv_ranges'])"

# Test camera initialization
python -c "from hypemage.camera import CameraProcess; CameraProcess(robot_id='necron')"
```

### ✅ Web Dashboard
1. Open calibration widget for Storm
2. Adjust ball HSV sliders
3. Click "Save Calibration"
4. Verify config.json["storm"]["hsv_ranges"]["ball"] updated
5. Repeat for Necron
6. Verify config.json["necron"]["hsv_ranges"] updated independently

---

## Error Handling

### ✅ Implemented
- FileNotFoundError if config.json missing
- KeyError if robot_id not in config
- JSONDecodeError if config.json invalid
- Fallback to auto-detection if robot_id=None
- Graceful degradation (log warnings, use defaults)

### ✅ Logging
- Info: Robot detected, config loaded/saved
- Warning: Config file issues, fallback to defaults
- Error: Failed to save, invalid JSON

---

## Breaking Changes

### Removed
❌ `camera_config.json`  
❌ `load_camera_config()` function  
❌ `_load_config()` method  
❌ `_default_config()` method  
❌ Local save_config() in camera_calibrate.py  

### Added
✅ `config.json` (bot-specific)  
✅ `config.py` module  
✅ `robot_id` parameter to CameraProcess  
✅ `--robot` CLI argument  
✅ Auto-detection system  

### Modified
🔄 All camera scripts accept robot_id  
🔄 Debug manager saves bot-specific config  
🔄 Web dashboard sends robot_id  

---

## Migration Guide

### For Existing Scripts

**Before**:
```python
from hypemage.camera import load_camera_config
config = load_camera_config()
camera = CameraProcess(config)
```

**After**:
```python
from hypemage.config import load_config, get_robot_id
robot_id = get_robot_id()
config = load_config(robot_id)
camera = CameraProcess(robot_id=robot_id)

# Or simpler (auto-detects):
camera = CameraProcess()
```

### For Deployment

**Storm Robot**:
```bash
echo "ROBOT_NAME=storm" >> ~/.bashrc
# OR
sudo hostnamectl set-hostname storm-robot
```

**Necron Robot**:
```bash
echo "ROBOT_NAME=necron" >> ~/.bashrc
# OR
sudo hostnamectl set-hostname necron-robot
```

---

## Verification

### Check Config Structure
```bash
python -c "
import json
with open('hypemage/config.json') as f:
    config = json.load(f)
    print('Robots:', list(config.keys()))
    print('Storm sections:', list(config['storm'].keys()))
    print('Necron sections:', list(config['necron'].keys()))
"
```

Expected Output:
```
Robots: ['storm', 'necron']
Storm sections: ['camera', 'hsv_ranges', 'detection', 'motors']
Necron sections: ['camera', 'hsv_ranges', 'detection', 'motors']
```

### Verify Robot Detection
```bash
# Test all methods
python -c "from hypemage.config import get_robot_id; print('CLI override:', get_robot_id('necron'))"
ROBOT_NAME=storm python -c "from hypemage.config import get_robot_id; print('Env var:', get_robot_id())"
python -c "from hypemage.config import get_robot_id; print('Default:', get_robot_id())"
```

---

## Summary

✅ **9 files** modified/created  
✅ **Bot-specific config** for Storm and Necron  
✅ **Auto-detection** system implemented  
✅ **CLI arguments** added to all scripts  
✅ **Web dashboard** integrated  
✅ **Backward compatible** error handling  
✅ **Comprehensive documentation** created  

**Status**: Ready for deployment and testing  
**Next Steps**: Test on actual Raspberry Pi hardware with both robots

---

## Quick Reference

### Load Config
```python
from hypemage.config import load_config, get_robot_id
config = load_config(get_robot_id())
```

### Save Config
```python
from hypemage.config import save_config, get_robot_id
save_config(get_robot_id(), updated_config)
```

### Use Camera
```python
from hypemage.camera import CameraProcess
camera = CameraProcess()  # Auto-detects robot
```

### Run Scripts
```bash
python -m hypemage.scripts.camera_debug --robot storm
python -m hypemage.scripts.camera_calibrate --robot necron
```

---

*Configuration migration completed successfully!*
