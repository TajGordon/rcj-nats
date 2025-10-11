# Robot-Specific Configuration - Quick Reference

## Summary

Motor addresses and dribbler addresses are now **automatically detected** based on the robot's hostname. No manual configuration required!

## Detection Logic

**Hostname Check**: Uses `socket.gethostname()` to identify robot

| Robot Name | Hostnames Detected | Motor Addresses | Dribbler Address |
|------------|-------------------|-----------------|------------------|
| **f7** (storm) | 'f7', 'storm' | `[28, 30, 26, 27]` | `29` |
| **m7** (necron) | 'f7', 'necron', or anything else | `[27, 29, 25, 26]` | `30` |

## Motor Address Mapping (m7 → f7)

The f7 motor addresses are derived from m7 base addresses using this mapping:

```
m7 address → f7 address
    25     →     26
    26     →     27
    27     →     28
    29     →     30
```

Applied to position array `[back_left, front_left, front_right, back_right]`:
- m7: `[27, 29, 25, 26]`
- f7: `[28, 30, 26, 27]`

## Files Modified

### 1. **Created Files**
- `hypemage/robot_detection.py` - Core detection module
- `hypemage/test_robot_detection.py` - Testing script
- `ROBOT_DETECTION.md` - Complete implementation guide
- `ROBOT_DETECTION_QUICK_REFERENCE.md` - This file

### 2. **Modified Files**
- `hypemage/motor_control.py` - Auto-detects motor addresses
- `hypemage/scylla.py` - Applies robot config overrides on startup
- `hypemage/config.json` - Updated with auto-detect settings and documentation

### 3. **Unchanged (Already Had Detection)**
- `hypemage/dribbler_control.py` - Already had hostname detection

## Quick Test

### On the Robot:
```bash
# Check hostname
hostname
# Should return: f7.local, m7.local, storm, or necron

# Test detection
cd ~/rcj-nats/hypemage
python test_robot_detection.py

# Or quick test
python robot_detection.py
```

### Expected Output:
```
Detected robot: f7 (or m7)
Motor addresses: [28, 30, 26, 27] (or [27, 29, 25, 26])
Dribbler address: 29 (or 30)
```

## Override Auto-Detection

If you need to **manually override** auto-detection (for testing):

### In config.json:
```json
{
  "motor_addresses": [27, 29, 25, 26],  // Explicit addresses
  "dribbler": {
    "address": 30  // Explicit dribbler address
  }
}
```

### In code:
```python
# Pass explicit config to scylla
config = {
    'motor_addresses': [27, 29, 25, 26],
    'dribbler': {'address': 30}
}
fsm = Scylla(config=config)

# Or to motor controller
motor_controller = MotorController(
    motor_addresses=[27, 29, 25, 26]
)
```

## Logging

The system logs detection results during startup:

```
INFO: Detected robot: f7
INFO: Motor addresses: [28, 30, 26, 27]
INFO: Auto-detected motor addresses: [28, 30, 26, 27]
INFO: Using dribbler address: 29 (auto-detected from hostname)
```

Or if config override is used:
```
INFO: Using motor addresses from config: [27, 29, 25, 26]
```

## Troubleshooting

### Problem: Wrong addresses detected

**Check hostname**:
```bash
hostname
# Should contain 'f7' or 'm7'
```

**Fix hostname** (if needed):
```bash
sudo raspi-config
# System Options → Hostname → Set to 'f7' or 'm7'
sudo reboot
```

### Problem: Auto-detection not working

**Check if config has explicit addresses**:
```bash
grep -A5 "motor_addresses" hypemage/config.json
```

**Remove explicit addresses** to enable auto-detection:
- Change `"motor_addresses": [27, 29, 25, 26]` to `"motor_addresses": "_AUTO_DETECT_"`
- Or remove the line entirely

### Problem: Motors moving in wrong direction

**This is likely a wiring issue, not detection issue**:
1. Verify correct motor addresses are detected (check logs)
2. Check motor multipliers in config.json
3. Verify physical motor connections match expected layout

## Configuration Priority

The system uses this priority order:

1. **Explicit config parameter** (highest priority)
   ```python
   fsm = Scylla(config={'motor_addresses': [27, 29, 25, 26]})
   ```

2. **config.json robot-specific section**
   ```json
   "necron": { "motor_addresses": [27, 29, 25, 26] }
   ```

3. **Auto-detection based on hostname** (default)
   ```python
   # Automatically uses get_motor_addresses()
   ```

## Benefits

✓ **Zero configuration** - Works automatically on both robots  
✓ **No manual setup** - Just deploy code and run  
✓ **Impossible to mix up** - Hostname determines everything  
✓ **Easy to verify** - Just check hostname  
✓ **Override when needed** - Config still works for special cases  
✓ **Well documented** - Clear mapping and detection logic  

## Next Steps

1. **Deploy to both robots** - Same codebase works on both
2. **Verify hostname** - Ensure each robot has correct hostname
3. **Run test script** - Confirm detection works correctly
4. **Check motor movement** - Verify motors respond correctly
5. **Monitor logs** - Watch for any detection errors

---

**For detailed information**, see `ROBOT_DETECTION.md`
