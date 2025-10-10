# Configuration System - Defaults and Overrides

## Structure

The `config.json` file now uses a **defaults + overrides** pattern to reduce duplication and make robot-specific calibration clearer.

### File Structure

```json
{
  "defaults": {
    // Values shared by ALL robots
    "camera": { "width": 640, ... },
    "detection": { ... },
    "motors": { ... }
  },
  
  "storm": {
    // Only Storm-specific values
    "hsv_ranges": { ... },
    "motors": { "i2c_address": "0x50" }
  },
  
  "necron": {
    // Only Necron-specific values
    "hsv_ranges": { ... },
    "motors": { "i2c_address": "0x50" }
  }
}
```

## What Goes Where?

### `defaults` Section (Shared Configuration)

Put values here that are **the same for all robots**:

✅ **Camera settings:**
- `width`, `height`, `format`, `fps_target`
- These are hardware/setup constants, not robot-specific

✅ **Detection parameters:**
- `proximity_threshold`, `angle_tolerance`, `goal_center_tolerance`
- Generic thresholds that work for all robots

✅ **Motor parameters:**
- `max_speed`, `acceleration`, `deadzone`
- Physical motor characteristics (same motors on all robots)

✅ **Movement parameters:**
- `default_speed`, `rotation_speed`
- Behavioral defaults that apply universally

### Robot-Specific Sections (Overrides)

Put values here that are **unique to each robot**:

✅ **HSV color ranges:**
- `hsv_ranges.ball`, `hsv_ranges.blue_goal`, `hsv_ranges.yellow_goal`
- **WHY:** Each camera has different calibration due to:
  - Lens differences
  - Mounting angle variations
  - Camera sensor variations

✅ **I2C addresses:**
- `motors.i2c_address`
- **WHY:** Could be different if using different motor controllers

✅ **Localization calibration:**
- `sin_cos_centers`, `angle_offsets`
- **WHY:** Camera position/mounting is unique per robot

✅ **Physical measurements:**
- Wheel diameter, robot dimensions
- **WHY:** Manufacturing tolerances, wear differences

## How It Works

### Loading Configuration

```python
from hypemage.config import load_config

# Automatically merges defaults + robot-specific
config = load_config('storm')

# Result: defaults merged with storm overrides
# {
#   "camera": { "width": 640, ... },      # From defaults
#   "detection": { ... },                  # From defaults
#   "motors": { 
#     "max_speed": 255,                    # From defaults
#     "acceleration": 50,                  # From defaults
#     "i2c_address": "0x50"                # From storm override
#   },
#   "hsv_ranges": { ... }                  # From storm (no default)
# }
```

### Merge Logic

The `deep_merge()` function:
1. Starts with `defaults`
2. Overlays robot-specific values
3. Robot values **override** defaults at any level

**Example:**
```json
// defaults
{
  "motors": {
    "max_speed": 255,
    "acceleration": 50,
    "deadzone": 20
  }
}

// storm override
{
  "motors": {
    "i2c_address": "0x50"
  }
}

// Merged result for storm
{
  "motors": {
    "max_speed": 255,        // From defaults
    "acceleration": 50,      // From defaults
    "deadzone": 20,          // From defaults
    "i2c_address": "0x50"    // From storm
  }
}
```

## Migration Guide

### Before (Duplicated Values)

```json
{
  "storm": {
    "camera": { "width": 640, "height": 640 },
    "detection": { "proximity_threshold": 5000 },
    "hsv_ranges": { ... }
  },
  "necron": {
    "camera": { "width": 640, "height": 640 },  // DUPLICATE!
    "detection": { "proximity_threshold": 5000 },  // DUPLICATE!
    "hsv_ranges": { ... }
  }
}
```

### After (DRY - Don't Repeat Yourself)

```json
{
  "defaults": {
    "camera": { "width": 640, "height": 640 },
    "detection": { "proximity_threshold": 5000 }
  },
  "storm": {
    "hsv_ranges": { ... }  // Only unique values
  },
  "necron": {
    "hsv_ranges": { ... }  // Only unique values
  }
}
```

## Benefits

### 1. Less Duplication
- Change default camera resolution once, applies to all robots
- No risk of inconsistent values between robots

### 2. Clearer Intent
- Robot sections show ONLY what's unique to that robot
- Easy to see what's been calibrated/customized

### 3. Easier Maintenance
- Add new robot: Just specify HSV ranges and addresses
- Update detection params: Change once in defaults

### 4. Better Documentation
- Defaults serve as documentation of standard values
- Overrides highlight what's been tuned per-robot

## Adding a New Robot

To add a new robot (e.g., "hydra"):

```json
{
  "defaults": { ... },
  "storm": { ... },
  "necron": { ... },
  
  "hydra": {
    "_comment": "Hydra-specific configuration",
    
    "hsv_ranges": {
      "ball": {
        "lower": [0, 220, 140],
        "upper": [5, 255, 255],
        "min_area": 100,
        "max_area": 50000
      },
      // ... calibrate other colors
    },
    
    "motors": {
      "i2c_address": "0x51"  // If different
    },
    
    "localization": {
      "sin_cos_centers": {
        "blue": [320, 240],
        "yellow": [320, 240]
      },
      "angle_offsets": {
        "blue": 0.0,
        "yellow": 180.0
      }
    }
  }
}
```

Then update `get_robot_id()` in `config.py` to recognize the new robot's hostname.

## Updating Configuration

### Update Defaults (All Robots)

```python
# Edit config.json manually or:
from hypemage.config import CONFIG_PATH
import json

with open(CONFIG_PATH, 'r') as f:
    config = json.load(f)

config['defaults']['detection']['proximity_threshold'] = 6000

with open(CONFIG_PATH, 'w') as f:
    json.dump(config, f, indent=2)
```

### Update Robot-Specific

```python
from hypemage.config import update_config_section

# Update Storm's HSV range
update_config_section('storm', 'hsv_ranges.ball.lower', [0, 225, 150])

# Update Necron's motor address
update_config_section('necron', 'motors.i2c_address', '0x52')
```

## Best Practices

### ✅ DO put in defaults:
- Hardware specs (camera resolution, format)
- Universal constants (max motor speed)
- Default behaviors (movement speeds)
- Detection thresholds that work universally

### ❌ DON'T put in defaults:
- HSV color ranges (camera-specific calibration)
- I2C addresses (could vary by robot)
- Localization calibration (mounting-specific)
- Physical measurements (tolerances vary)

### 🤔 When in doubt:
Ask: "If I build a new robot with identical hardware, would this value be the same?"
- **YES** → Put in defaults
- **NO** → Put in robot-specific section

## Troubleshooting

### "My robot-specific value isn't being used"

Check merge priority:
1. Robot-specific values OVERRIDE defaults
2. But only at the key level they're specified
3. Nested dicts are merged recursively

Example:
```json
// defaults
{ "motors": { "max_speed": 255, "acceleration": 50 } }

// robot override
{ "motors": { "i2c_address": "0x50" } }

// Result: ALL motor keys present (merged)
{ "motors": { "max_speed": 255, "acceleration": 50, "i2c_address": "0x50" } }
```

### "Changes to defaults aren't reflected"

Make sure to:
1. Edit the `defaults` section, not robot sections
2. Restart any running processes (they cache config on load)
3. Check that robot section isn't overriding that key

### "New robot not recognized"

1. Add robot section to `config.json`
2. Update `get_robot_id()` in `config.py` to recognize hostname
3. Set `ROBOT_NAME` environment variable as temporary workaround

## See Also

- `config.py` - Configuration loading code
- `CONFIG_MIGRATION.md` - Migration from old format (if needed)
- RoboCup Junior calibration guide - HSV calibration procedures
