# Dribbler Troubleshooting Guide

The dribbler motor is not working. Here's how to diagnose and fix it.

## Quick Diagnostic

Run these commands on the Raspberry Pi to identify the issue:

```bash
# 1. Run the diagnostic script
python diagnose_dribbler.py

# 2. If that passes, try the simple test
python test_simple_dribbler.py

# 3. If that works, test with scylla
python -m hypemage.scylla
```

## Common Issues & Solutions

### Issue 1: "Not on Raspberry Pi"
**Symptom:** Error about `board` module not found
**Cause:** Testing on Windows/Mac instead of Raspberry Pi
**Solution:** This will only work on the actual Raspberry Pi robot

### Issue 2: Wrong I2C Address
**Symptom:** Motor initializes but doesn't spin
**Cause:** Wrong address for the robot (f7 vs m7)
**Check:** 
- f7 (storm) should use address **29**
- m7 (necron) should use address **30**

**Fix:** Edit scylla.py if hostname detection is wrong

### Issue 3: Motor Not Connected
**Symptom:** Error during Motor initialization
**Cause:** Dribbler motor not physically connected
**Solution:** 
1. Check I2C wiring to the dribbler motor
2. Verify motor is powered on
3. Check I2C address is configured correctly on motor controller

### Issue 4: I2C Permissions
**Symptom:** Permission denied when accessing I2C
**Solution:**
```bash
# Add user to i2c group
sudo usermod -a -G i2c $USER
# Then logout and login again
```

### Issue 5: Wrong Speed Value
**Symptom:** Motor spins very slowly or not at all
**Cause:** Speed value too low
**Note:** Motor.set_speed() expects range 0-10, not 0-1
- Speed 3.0 in scylla.py = 30% of max speed
- Try increasing to 5.0 or 8.0 if too slow

## What the Code Does

In `scylla.py`, the simple dribbler motor:

1. **Initializes** in `_init_non_critical_components()` (lines 354-381)
   - Auto-detects robot hostname
   - Creates `Motor(address)` instance
   
2. **Starts** in `start()` method (lines 432-438)
   - Sets speed to 3.0 when robot starts
   - Runs continuously throughout game
   
3. **Stops** in two places:
   - `_emergency_motor_stop()` (lines 293-299) - on crashes
   - `shutdown()` (lines 1210-1218) - on normal exit

## Testing Steps

### Step 1: Basic Motor Test
```bash
python test_simple_dribbler.py
```
This tests if the Motor class works at all.

### Step 2: Check Integration
```bash
python diagnose_dribbler.py
```
This checks if scylla.py can access the Motor class.

### Step 3: Run Scylla
```bash
python -m hypemage.scylla
```
Watch the logs for:
- "Initializing simple dribbler motor..."
- "✓ Simple dribbler motor initialized at address XX"
- "Starting simple dribbler motor at speed 3.0..."
- "✓ Dribbler motor running at speed 3.0"

## If Nothing Works

Try the original dribbler_test.py:
```bash
cd motors
python dribbler_test.py
# Enter speed: 3.0
```

If THIS works but scylla doesn't, then the issue is with the integration.
If this DOESN'T work, then the issue is hardware/wiring.

## Manual Override

If you need to disable the simple dribbler temporarily, edit scylla.py:

Find line ~432 in the `start()` method and comment out:
```python
# if self.simple_dribbler_motor:
#     try:
#         logger.info("Starting simple dribbler motor at speed 3.0...")
#         self.simple_dribbler_motor.set_speed(3.0)
#         logger.info("✓ Dribbler motor running at speed 3.0")
#     except Exception as e:
#         logger.warning(f"⚠️  Failed to start dribbler motor: {e}")
```

## Adjusting Speed

To change the dribbler speed, edit scylla.py line ~434:
```python
self.simple_dribbler_motor.set_speed(3.0)  # Change 3.0 to your desired speed (0-10)
```

Recommended speeds:
- 2.0 = gentle (20%)
- 3.0 = moderate (30%)
- 5.0 = fast (50%)
- 8.0 = very fast (80%)
- 10.0 = maximum (100%)
