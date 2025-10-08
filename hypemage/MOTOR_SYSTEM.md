# Motor Control System Documentation

## Overview

The motor control system provides two modes of operation:
1. **Threaded Mode** (recommended): Non-blocking, with watchdog safety
2. **Direct Mode**: Blocking I2C writes, simpler but can stall main loop

Based on analysis of Nationals code and motor.py implementations.

---

## Key Design Decisions

### Thread vs Process vs Direct

**✅ Thread (Recommended)**
- Non-blocking motor commands
- Safety watchdog (auto-stop if no commands)
- Low latency (~1ms overhead)
- Can share I2C bus objects
- Easy to add lerping later

**❌ Process**
- Can't share I2C/GPIO hardware objects across processes
- Higher overhead
- More complex IPC
- Not needed for motors

**⚠️ Direct (Simple but risky)**
- Blocking I2C writes (~0.5-2ms each)
- Can stall main FSM loop if I2C has issues
- No watchdog safety
- Simpler code

### Do You Need Threading?

**You DON'T need threading if:**
- Motor I2C commands are always fast (<1ms)
- You're okay with occasional blocking
- You trust your I2C bus won't hang
- You don't want watchdog safety

**You NEED threading if:**
- You want guaranteed non-blocking commands
- You want safety watchdog (motors stop if FSM crashes)
- You might add lerping/smoothing later
- You want to decouple motor timing from FSM

---

## Motor Control Architecture

```
FSM/Main Loop
    ↓
controller.set_speeds([0.3, 0.3, 0.3, 0.3])
    ↓
Queue.put(MotorCommand)  ← Returns immediately (non-blocking)
    ↓
Motor Thread (100 Hz loop)
    ↓
Queue.get() → Process command
    ↓
I2C Write to Motors (blocking but in separate thread)
    ↓
Watchdog Check (auto-stop if no commands)
```

---

## Usage Examples

### 1. Threaded Mode (Recommended for Production)

```python
from hypemage.motor_control import MotorController

# Configuration
config = {
    'motor_addresses': [26, 27, 29, 25],  # I2C addresses
    'max_speed': 400_000_000,
    'watchdog_enabled': True,
    'watchdog_timeout': 0.5,  # Stop motors if no command for 0.5s
}

# Create controller (starts background thread automatically)
motors = MotorController(config=config, threaded=True)

# Send commands (non-blocking, returns immediately)
motors.set_speeds([0.3, 0.3, 0.3, 0.3])  # Forward
motors.set_speeds([0.3, -0.3, 0.3, -0.3])  # Turn
motors.stop()  # Stop all

# Get status
status = motors.get_status()
print(f"Motors running: {status.is_running}")
print(f"Current speeds: {status.speeds}")

# Cleanup
motors.shutdown()
```

### 2. Direct Mode (Simple, Blocking)

```python
from siddak_stuff.motor_control import MotorController

# Create controller without threading
motors = MotorController(config=config, threaded=False)

# Send commands (blocks until I2C write completes, ~1ms)
motors.set_speeds([0.3, 0.3, 0.3, 0.3])
motors.stop()
```

### 3. Simple Mode (Minimal Config)

```python
from siddak_stuff.motor_control import SimpleMotorController

# Bare-bones controller for quick testing
motors = SimpleMotorController(motor_addresses=[26, 27, 29, 25])

motors.set_speeds([0.5, 0.5, 0.5, 0.5])
motors.stop()
```

---

## Integration with Scylla FSM

Add motors to Scylla's `__init__`:

```python
class Scylla:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # ...existing code...
        
        # Initialize motor controller
        motor_config = config.get('motors', {})
        self.motors = MotorController(config=motor_config, threaded=True)
```

Use in state handlers:

```python
def state_chase_ball(self):
    """Active state: chase the ball"""
    if not self.latest_camera_data:
        return
    
    ball = self.latest_camera_data.ball
    
    if ball.detected:
        # Calculate motor speeds based on ball position
        # (You can use your ControlSystem here)
        from siddy_nats.soccer.control_system import ControlSystem
        control = ControlSystem()
        speeds = control.calculate_motor_commands(
            ball.detected,
            ball.center_x,
            ball.center_y
        )
        
        # Send to motors (non-blocking)
        self.motors.set_speeds([s / MAX_SPEED for s in speeds])
    else:
        self.motors.stop()
```

Cleanup in shutdown:

```python
def shutdown(self):
    """Clean shutdown"""
    # ...existing code...
    
    # Stop and shutdown motors
    if hasattr(self, 'motors'):
        self.motors.shutdown()
```

---

## Watchdog Safety Feature

The watchdog automatically stops motors if no commands are received within a timeout period.

**Why this matters:**
- If your FSM crashes, motors stop automatically
- If camera/localization freezes, motors won't keep running blindly
- Safety requirement for competitions

**Configuration:**
```python
config = {
    'watchdog_enabled': True,
    'watchdog_timeout': 0.5,  # seconds
}
```

**Behavior:**
1. Every command resets the watchdog timer
2. If no command received for `watchdog_timeout` seconds:
   - Motors automatically set to speed 0
3. Resume by sending any command

**Testing watchdog:**
```python
motors.set_speeds([0.3, 0.3, 0.3, 0.3])
time.sleep(1.0)  # Wait longer than timeout
# Motors should be stopped by watchdog
status = motors.get_status()
print(status.speeds)  # Should be [0.0, 0.0, 0.0, 0.0]
```

---

## Motor Speed Convention

**Input:** Normalized speeds in range **[-1.0, 1.0]**
- `1.0` = full speed forward
- `-1.0` = full speed backward
- `0.0` = stopped

**Motor order:** `[back_left, back_right, front_left, front_right]`

**Example movements:**
```python
# Forward
motors.set_speeds([0.5, 0.5, 0.5, 0.5])

# Backward
motors.set_speeds([-0.5, -0.5, -0.5, -0.5])

# Turn right (clockwise)
motors.set_speeds([0.5, -0.5, 0.5, -0.5])

# Turn left (counter-clockwise)
motors.set_speeds([-0.5, 0.5, -0.5, 0.5])

# Strafe right (omniwheel)
# (depends on wheel orientation - adjust per robot)
motors.set_speeds([0.5, -0.5, -0.5, 0.5])
```

---

## Adding Lerping (Optional)

If you want smooth speed transitions (lerping) later:

**Option 1: In motor thread (recommended)**
```python
# In _motor_worker:
target_speeds = cmd.speeds
current_speeds = self.current_speeds

# Lerp towards target
for i in range(len(current_speeds)):
    current_speeds[i] += (target_speeds[i] - current_speeds[i]) * 0.2
    
self._execute_set_speeds(current_speeds)
```

**Option 2: In FSM state (higher level)**
```python
# In Scylla state handler:
target_speed = 0.5
self.motor_lerp_state = getattr(self, 'motor_lerp_state', 0.0)
self.motor_lerp_state += (target_speed - self.motor_lerp_state) * 0.1
self.motors.set_speeds([self.motor_lerp_state] * 4)
```

**Note from Nationals code:**
- They tried lerping but "doesn't work properly apparently"
- Direct speed commands are simpler and more reliable
- Only add lerping if you have a specific need

---

## Critical Insights from Nationals Code

### ✅ What They Do Well

1. **Simple speed commands** - no complex state machines
2. **Direct I2C access** - minimal abstraction
3. **Clamping speeds** - always clamp to [-1.0, 1.0]
4. **Per-motor error handling** - one motor failure doesn't crash system

### ⚠️ What to Watch For

1. **No watchdog** - if code crashes, motors keep running
2. **Blocking I2C** - can stall main loop if I2C hangs
3. **No thread safety** - assumes single-threaded access
4. **Lerping issues** - "doesn't work properly apparently"

### Key Lessons

- **Keep it simple** - direct speed commands work best
- **Add safety** - watchdog prevents runaway robots
- **Test I2C** - motor I2C can occasionally hang
- **Avoid lerping** - unless you have time to debug it properly

---

## Issues in motor.py You Should Know About

### 1. Speed Scaling Issue
```python
# motor.py line 63:
def set_speed(self, speed):
    speed /= 10  # scale to range [-1.0, 1.0]
```
**Problem:** Expects input in [-10, 10] but docstring suggests otherwise.

**Fix:** Always pass speeds in [-1.0, 1.0] to our MotorController.

### 2. No Error Recovery
```python
# If I2C fails, motor object becomes unusable
```
**Our fix:** Per-motor try/except, continue on error.

### 3. No Watchdog Safety
```python
# If loop crashes, last motor command keeps running
```
**Our fix:** Watchdog auto-stops motors after timeout.

---

## Performance Characteristics

**Thread Mode:**
- Command latency: < 1ms (queue put)
- I2C write: ~0.5-2ms (in thread, doesn't block main)
- Update rate: 100 Hz (motor thread loop)
- Memory: ~10 queued commands max

**Direct Mode:**
- Command latency: 0.5-2ms (blocking I2C)
- Can block FSM if I2C issues occur
- No memory overhead

**Recommendation:** Use threaded mode unless you have a very good reason not to.

---

## Configuration Reference

```python
config = {
    # Hardware
    'motor_addresses': [26, 27, 29, 25],  # I2C addresses
    
    # Speed limits
    'max_speed': 400_000_000,  # Motor controller units
    
    # PID tuning
    'current_limit_foc': 65536 * 3,
    'id_pid': {'kp': 1500, 'ki': 200},
    'iq_pid': {'kp': 1500, 'ki': 200},
    'speed_pid': {'kp': 0.04, 'ki': 0.0004, 'kd': 0.03},
    'position_pid': {'kp': 275, 'ki': 0, 'kd': 0},
    'position_region_boundary': 250000,
    
    # Operating modes
    'operating_mode': 3,  # 3 = FOC (Field-Oriented Control)
    'sensor_mode': 1,     # 1 = Sin/cos encoder
    'command_mode': 12,   # 12 = Speed mode
    
    # Safety
    'watchdog_enabled': True,
    'watchdog_timeout': 0.5,  # seconds
    
    # Calibration (stored in motor EEPROM, usually don't need to set)
    'calibration': {
        'elecangleoffset': 1544835584,
        'sincoscentre': 1255
    }
}
```

---

## Troubleshooting

**Motors don't move:**
1. Check I2C addresses are correct
2. Check motor power supply
3. Check firmware version (should be 3)
4. Check calibration values

**Motors stop unexpectedly:**
1. Watchdog timeout - send commands more frequently
2. I2C communication failure - check wiring
3. Power supply issue - check voltage

**Jerky movement:**
1. Don't use lerping (known issue)
2. Send commands at consistent rate (20-50 Hz recommended)
3. Check PID tuning

**I2C errors:**
1. Reduce I2C clock speed
2. Check pull-up resistors
3. Shorten I2C cables
4. Add error handling (our code does this)

---

## Summary

**Recommendation: Use threaded mode with watchdog enabled.**

This gives you:
- ✅ Non-blocking motor commands
- ✅ Safety watchdog
- ✅ Easy to use from FSM
- ✅ Can add lerping later if needed
- ✅ Handles I2C errors gracefully

The motor system is now ready to integrate with Scylla FSM!
