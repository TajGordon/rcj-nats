# Bot-Specific Configuration System

## Overview

The Hypemage robot system now uses a **centralized, bot-specific configuration** approach. All configuration is stored in `hypemage/config.json`, organized by robot (`storm` and `necron`).

## Configuration Structure

### File: `hypemage/config.json`

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

Each robot has its own complete configuration section, allowing different calibration values, motor settings, etc.

## Robot Identification

The system determines which robot it's running on using the following priority:

1. **Command-line argument**: `--robot storm` or `--robot necron`
2. **Environment variable**: `ROBOT_NAME=storm` or `ROBOT_NAME=necron`
3. **Hostname**: If hostname contains 'storm' or 'necron'
4. **Default**: Falls back to 'storm'

### Examples

```bash
# Explicit robot specification
python -m hypemage.scripts.camera_debug --robot storm
python -m hypemage.scripts.camera_calibrate --robot necron

# Using environment variable
export ROBOT_NAME=necron
python -m hypemage.scripts.camera_debug

# Automatic detection (if hostname is 'storm-robot')
python -m hypemage.scripts.camera_debug
```

## Using the Config System

### In Python Code

```python
from hypemage.config import load_config, save_config, get_robot_id

# Auto-detect robot and load config
robot_id = get_robot_id()  # Returns 'storm' or 'necron'
config = load_config(robot_id)

# Access configuration
camera_width = config['camera']['width']
ball_hsv = config['hsv_ranges']['ball']

# Modify and save
config['camera']['fps_target'] = 60
save_config(robot_id, config)

# Load config for specific robot (override auto-detection)
storm_config = load_config('storm')
necron_config = load_config('necron')
```

### In Camera Module

The `CameraProcess` class automatically loads config for the current robot:

```python
from hypemage.camera import CameraProcess

# Auto-detects robot and loads config
camera = CameraProcess()

# Or specify robot explicitly
camera = CameraProcess(robot_id='necron')
```

### In Web Dashboard

The web interface automatically sends robot_id when saving calibration:

```javascript
// When calibrating Storm robot
saveCalibration('storm')  // Saves to config.json under "storm" section

// When calibrating Necron robot
saveCalibration('necron')  // Saves to config.json under "necron" section
```

## Configuration Sections

### 1. Camera Settings

```json
"camera": {
  "width": 640,
  "height": 480,
  "format": "RGB888",
  "fps_target": 30
}
```

### 2. HSV Ranges (Color Detection)

```json
"hsv_ranges": {
  "ball": {
    "lower": [10, 100, 100],  // H, S, V minimums
    "upper": [20, 255, 255],  // H, S, V maximums
    "min_area": 100,
    "max_area": 50000
  },
  "blue_goal": { ... },
  "yellow_goal": { ... }
}
```

**HSV Format**: OpenCV format (H: 0-180, S: 0-255, V: 0-255)

### 3. Detection Settings

```json
"detection": {
  "proximity_threshold": 5000,
  "angle_tolerance": 15,
  "goal_center_tolerance": 0.15
}
```

### 4. Motor Settings

```json
"motors": {
  "i2c_address": "0x50",
  "max_speed": 255,
  "acceleration": 50
}
```

## HSV Calibration Workflow

### Using Web Dashboard

1. **Start camera_calibrate script** for specific robot
2. **Open calibration widget** in dashboard
3. **Adjust HSV sliders** (real-time mask preview)
4. **Click "Save Calibration"**
5. Configuration saved to `config.json` under robot's section

### Flow Diagram

```
Web Dashboard (Storm)
    ↓ (adjust sliders)
WebSocket → Debug Manager
    ↓
save_config('storm', config)
    ↓
config.json["storm"]["hsv_ranges"] = {...}
```

## Migration from Old System

### What Changed

**Before** (camera_config.json):
```json
{
  "camera": {...},
  "hsv_ranges": {...}
}
```

**After** (config.json):
```json
{
  "storm": {
    "camera": {...},
    "hsv_ranges": {...},
    "motors": {...}
  },
  "necron": {
    "camera": {...},
    "hsv_ranges": {...},
    "motors": {...}
  }
}
```

### Breaking Changes

1. ❌ **Removed**: `camera_config.json` (deleted)
2. ❌ **Removed**: `load_camera_config()` function
3. ✅ **Added**: `config.json` with bot-specific sections
4. ✅ **Added**: `config.py` module (`get_robot_id`, `load_config`, `save_config`)
5. ✅ **Updated**: All camera scripts accept `--robot` argument

### Code Updates Required

**Old Code**:
```python
from hypemage.camera import load_camera_config
config = load_camera_config()
```

**New Code**:
```python
from hypemage.config import load_config, get_robot_id
robot_id = get_robot_id()
config = load_config(robot_id)
```

## File Locations

- **Config file**: `hypemage/config.json`
- **Config module**: `hypemage/config.py`
- **Camera module**: `hypemage/camera.py` (updated)
- **Debug scripts**: `hypemage/scripts/camera_debug.py`, `camera_calibrate.py`
- **Debug manager**: `hypemage/debug/debug_manager.py`
- **Web interface**: `hypemage/client/app.js`

## Environment Setup

### On Storm Robot

```bash
# Option 1: Set hostname
sudo hostnamectl set-hostname storm-robot

# Option 2: Set environment variable (in .bashrc or systemd service)
export ROBOT_NAME=storm

# Option 3: Always pass --robot flag
python -m hypemage.scylla --robot storm
```

### On Necron Robot

```bash
# Option 1: Set hostname
sudo hostnamectl set-hostname necron-robot

# Option 2: Set environment variable
export ROBOT_NAME=necron

# Option 3: Pass --robot flag
python -m hypemage.scylla --robot necron
```

## Testing

### Verify Robot Detection

```bash
python -c "from hypemage.config import get_robot_id; print(f'Detected robot: {get_robot_id()}')"
```

### Load Config

```bash
python -c "from hypemage.config import load_config; import json; print(json.dumps(load_config('storm'), indent=2))"
```

### Test Camera with Specific Robot

```bash
python -m hypemage.scripts.camera_debug --robot storm
python -m hypemage.scripts.camera_calibrate --robot necron
```

## Adding New Configuration Sections

To add new configuration parameters:

1. **Update `config.json`** for both robots:
```json
{
  "storm": {
    "camera": {...},
    "new_section": {
      "parameter1": value1,
      "parameter2": value2
    }
  },
  "necron": {
    "camera": {...},
    "new_section": {
      "parameter1": value1,
      "parameter2": value2
    }
  }
}
```

2. **Update `get_default_config()`** in `config.py`:
```python
def get_default_config() -> Dict[str, Any]:
    return {
        "camera": {...},
        "new_section": {
            "parameter1": default1,
            "parameter2": default2
        }
    }
```

3. **Access in code**:
```python
config = load_config(robot_id)
value = config['new_section']['parameter1']
```

## Troubleshooting

### Config File Not Found

**Error**: `FileNotFoundError: Configuration file not found`

**Solution**: Ensure `config.json` exists in `hypemage/` directory

### Wrong Robot Detected

**Error**: Loading storm config when expecting necron

**Solutions**:
1. Check hostname: `hostname`
2. Set ROBOT_NAME: `export ROBOT_NAME=necron`
3. Pass --robot flag: `python script.py --robot necron`

### Save Calibration Not Working

**Check**:
1. WebSocket connection to debug manager (port 8765)
2. Debug manager running
3. robot_id sent in save command
4. File permissions on config.json

### HSV Calibration Not Persisting

**Check**:
1. Correct robot selected in web dashboard
2. Calibration saved to correct robot section
3. Scripts loading from correct robot section

## Best Practices

1. ✅ **Always set robot identity** (hostname, env var, or arg)
2. ✅ **Use `get_robot_id()`** to auto-detect before loading config
3. ✅ **Test config on both robots** after changes
4. ✅ **Backup config.json** before manual edits
5. ✅ **Validate JSON** after manual edits (use `json.load()`)
6. ✅ **Keep sections synchronized** (add new keys to both robots)
7. ❌ **Don't hardcode robot names** (use get_robot_id())
8. ❌ **Don't mix old and new config systems**

## Future Enhancements

### Planned Features

1. **Config validation** - Schema validation on load
2. **Config versioning** - Migration system for config updates
3. **Dynamic config reload** - Hot-reload without restart
4. **Config backup** - Automatic backups before saves
5. **Config history** - Track calibration changes over time
6. **Remote config** - Load config from cloud/server

### Extending to Other Components

The bot-specific config pattern can be extended to:

- **Localization settings** (field dimensions, camera calibration)
- **FSM parameters** (state thresholds, timeouts)
- **Network settings** (IP addresses, ports)
- **Hardware calibration** (sensor offsets, motor PID values)

## Summary

The new bot-specific configuration system provides:

✅ **Centralized** - Single config.json for all settings  
✅ **Bot-specific** - Different calibration for Storm and Necron  
✅ **Automatic** - Auto-detects robot identity  
✅ **Web-integrated** - Calibration widget saves to correct robot  
✅ **Extensible** - Easy to add new configuration sections  
✅ **Type-safe** - Python config module with type hints  

All scripts and modules have been updated to use the new system.
