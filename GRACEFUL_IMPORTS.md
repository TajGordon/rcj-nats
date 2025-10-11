# Graceful Module Import Handling

## Problem
When running `scylla.py`, the camera module import was failing due to OpenCV (cv2) import errors on the Raspberry Pi:

```
ImportError: ... cv2 ...
```

This caused the entire robot to crash before it could even start.

## Solution
Implemented graceful import handling for non-critical modules. The robot will now start even if some modules fail to import.

## Changes Made

### 1. Wrapped Imports in Try-Except Blocks

**Camera Module:**
```python
try:
    from hypemage.camera import CameraProcess, CameraInitializationError
    CAMERA_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Camera module not available: {e}")
    CAMERA_AVAILABLE = False
    CameraProcess = None
    CameraInitializationError = Exception
```

**Dribbler Module:**
```python
try:
    from hypemage.dribbler_control import DribblerController
    DRIBBLER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Dribbler module not available: {e}")
    DRIBBLER_AVAILABLE = False
    DribblerController = None
```

**Kicker Module:**
```python
try:
    from hypemage.kicker_control import KickerController
    KICKER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Kicker module not available: {e}")
    KICKER_AVAILABLE = False
    KickerController = None
```

### 2. Updated Initialization Logic

**Non-Critical Components:**
```python
def _init_non_critical_components(self):
    # Initialize dribbler (NON-CRITICAL)
    if DRIBBLER_AVAILABLE:
        try:
            # Initialize dribbler...
        except Exception as e:
            logger.warning("Dribbler initialization failed")
    else:
        logger.warning("Dribbler module not available - skipping")
    
    # Similar for kicker...
```

**Camera Process:**
```python
def _start_camera_process(self):
    if not CAMERA_AVAILABLE:
        logger.warning("Camera module not available - cannot start camera")
        return
    
    # Start camera process...
```

## Behavior

### With All Modules Available
```
✓ Motor controller initialized
✓ Dribbler controller initialized
✓ Kicker controller initialized
✓ Camera process started
→ Robot fully operational
```

### Without Camera (cv2 import fails)
```
⚠️  Camera module not available: ImportError...
✓ Motor controller initialized
✓ Dribbler controller initialized
✓ Kicker controller initialized
✗ Camera process not started
→ Robot runs in degraded mode (no vision)
```

### Without Dribbler/Kicker (missing dependencies)
```
✓ Motor controller initialized
⚠️  Dribbler module not available - skipping
⚠️  Kicker module not available - skipping
✓ Camera process started (if available)
→ Robot runs without ball control
```

### Only Motors Available
```
✓ Motor controller initialized
⚠️  Camera module not available
⚠️  Dribbler module not available
⚠️  Kicker module not available
→ Robot can move but has no sensors or peripherals
```

## Component Priority

**CRITICAL (robot exits if fails):**
- ✅ Motor Controller

**NON-CRITICAL (robot continues if fails):**
- ⚠️  Camera
- ⚠️  Dribbler
- ⚠️  Kicker
- ⚠️  Localization

## Debugging Import Issues

### Check Which Modules Are Available
Add logging to see what's available:
```python
print(f"Camera available: {CAMERA_AVAILABLE}")
print(f"Dribbler available: {DRIBBLER_AVAILABLE}")
print(f"Kicker available: {KICKER_AVAILABLE}")
```

### Common Import Errors

**Camera (cv2):**
```bash
# Check if OpenCV is installed
python3 -c "import cv2; print(cv2.__version__)"

# Install if missing
pip install opencv-python
# or for Raspberry Pi:
sudo apt-get install python3-opencv
```

**Dribbler:**
```bash
# Check if motors module is available
python3 -c "from motors.motor import Motor"

# Verify I2C is enabled
ls /dev/i2c-*
```

**Kicker:**
```bash
# Check if GPIO libraries are available
python3 -c "import board, digitalio"

# Install if missing
pip install adafruit-blinka
```

## State Machine Behavior Without Camera

States that **require camera** will have limited functionality:
- CHASE_BALL: Cannot see ball (will not work)
- LINEUP_KICK: Cannot align kick (will not work)
- ATTACK_GOAL: Cannot see goal (will not work)
- SEARCH_BALL: Can still rotate but won't detect ball

States that **work without camera**:
- PAUSED: Works normally ✓
- STOPPED: Works normally ✓
- MOVE_IN_SQUARE: Works normally ✓
- MOVE_STRAIGHT: Works normally ✓

## Recommendation

For testing without camera:
```python
# In scylla.py main block:
if __name__ == '__main__':
    scylla = Scylla(config=config)
    # Use states that don't need camera
    scylla.transition_to(State.MOVE_STRAIGHT)
    scylla.start()
```

This allows you to test motor control even without camera functionality.

## Future Improvements

Consider adding:
- [ ] Stub camera data for testing without hardware
- [ ] Command-line flag to disable specific modules
- [ ] Health check endpoint to report module status
- [ ] Automatic fallback to simpler states when camera unavailable
