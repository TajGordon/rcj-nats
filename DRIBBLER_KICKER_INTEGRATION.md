# Dribbler and Kicker Integration

## Overview
The robot now has integrated control for:
- **Dribbler**: A motor that spins to grip and control the ball
- **Kicker**: A solenoid that fires to shoot the ball

Both components are **non-critical** - the robot will continue operating even if they fail to initialize.

## Components

### Dribbler Controller (`hypemage/dribbler_control.py`)

**Hardware:**
- Motor on I2C bus
- Address is robot-specific:
  - **f7 (storm)**: Address 29
  - **m7 (necron)**: Address 30
  - Auto-detected based on hostname

**Features:**
- Thread-safe speed control
- Continuous operation in background thread
- Speed range: -1.0 (reverse) to +1.0 (forward)
- Automatic address detection by hostname

**Usage:**
```python
# In Scylla FSM
self.enable_dribbler(0.5)      # Enable at 50% speed
self.set_dribbler_speed(0.7)   # Change to 70% speed
self.disable_dribbler()        # Stop dribbler
```

**Standalone Testing:**
```bash
python hypemage/dribbler_control.py

Commands:
  speed 0.5      # Set speed to 0.5
  enable 0.7     # Enable at 0.7 speed
  stop           # Stop dribbler
  quit           # Exit
```

### Kicker Controller (`hypemage/kicker_control.py`)

**Hardware:**
- Solenoid controlled by relay on GPIO D16
- Relay logic: LOW = kick, HIGH = no kick

**Features:**
- Thread-safe kick triggering
- Configurable kick duration (default: 0.15s)
- Safety cooldown: minimum 0.5s between kicks
- Automatic relay deactivation

**Usage:**
```python
# In Scylla FSM
if self.can_kick():           # Check if ready
    self.kick()               # Kick with default duration
    self.kick(0.2)            # Kick with 0.2s duration
```

**Standalone Testing:**
```bash
python hypemage/kicker_control.py

⚠️  WARNING: This will trigger the physical kicker!

Commands:
  kick           # Kick with default duration
  kick 0.2       # Kick with 0.2s duration
  status         # Show kick readiness
  quit           # Exit
```

## Configuration

### config.json

**Defaults Section:**
```json
"dribbler": {
  "default_speed": 0.5,
  "max_speed": 1.0
},

"kicker": {
  "kick_duration": 0.15,
  "gpio_pin": "D16"
}
```

**Robot-Specific:**
```json
"storm": {
  "dribbler": {
    "address": 29
  }
},

"necron": {
  "dribbler": {
    "address": 30
  }
}
```

## Integration with Scylla FSM

### Initialization
- **Critical components** (motors) initialize first - robot exits if they fail
- **Non-critical components** (dribbler, kicker) initialize after - robot continues if they fail
- Component status tracked in `ComponentStatus` dataclass

### Helper Methods

| Method | Description |
|--------|-------------|
| `set_dribbler_speed(speed)` | Set dribbler speed (-1.0 to 1.0) |
| `enable_dribbler(speed=None)` | Enable dribbler at speed (default from config) |
| `disable_dribbler()` | Stop dribbler |
| `kick(duration=None)` | Trigger kick (returns True/False) |
| `can_kick()` | Check if kick is ready (cooldown expired) |

### State Behavior

**CHASE_BALL:**
- Dribbler automatically enabled when chasing
- Speed varies based on ball distance:
  - Ball very close (area > 2000): 70% dribbler speed
  - Ball close (area > 1000): 60% dribbler speed
  - Ball medium (area > 500): 50% dribbler speed
  - Ball far: 40% dribbler speed
- Dribbler disabled when exiting chase state

**LINEUP_KICK:**
- When ball is close and centered:
  1. Check if kick is ready (`can_kick()`)
  2. Trigger kick
  3. Wait 0.2s for ball to leave
  4. Return to CHASE_BALL
- If ball not aligned: return to CHASE_BALL

**PAUSE:**
- When pausing: motors stop, dribbler stops
- When resuming: motors resume, dribbler resumes if in CHASE_BALL

### Emergency Shutdown

All shutdown handlers now include dribbler and kicker:

1. **Emergency Motor Stop** (atexit):
   - Stops motors
   - Stops dribbler
   
2. **Normal Shutdown** (Ctrl+C):
   - Stops motors
   - Stops dribbler thread
   - Disables kicker relay

3. **Exception Handler**:
   - Stops motors
   - Stops dribbler
   - Then re-raises exception

## Safety Features

### Dribbler
- ✅ Stops on pause
- ✅ Stops on shutdown
- ✅ Stops on crash (atexit)
- ✅ Thread-safe speed control
- ✅ Non-blocking operation

### Kicker
- ✅ Cooldown prevents rapid firing
- ✅ Relay always deactivated after kick
- ✅ Disabled on shutdown
- ✅ Safe to call multiple times
- ✅ Duration limits (0.05-0.5s)

## Troubleshooting

### Dribbler Not Working
```python
# Check status
print(f"Dribbler available: {scylla.dribbler_controller is not None}")
print(f"Dribbler running: {scylla.dribbler_controller.is_running()}")
print(f"Dribbler speed: {scylla.dribbler_controller.get_speed()}")

# Common issues:
# 1. Wrong hostname detection - check logs for "Detected hostname"
# 2. I2C address conflict - verify address with i2cdetect
# 3. Motor not responding - test with standalone dribbler_test.py
```

### Kicker Not Working
```python
# Check status
print(f"Kicker available: {scylla.kicker_controller is not None}")
print(f"Can kick: {scylla.can_kick()}")
print(f"Time since last kick: {scylla.kicker_controller.get_time_since_last_kick()}")

# Common issues:
# 1. GPIO not initialized - check for board import errors
# 2. Relay wiring - verify GPIO D16 connection
# 3. Cooldown active - wait 0.5s between kicks
```

### Hostname Detection
```bash
# Check current hostname
hostname

# Expected:
# - f7.local or containing 'f7' -> uses address 29
# - m7.local or containing 'm7' -> uses address 30
```

## Testing Checklist

- [ ] Dribbler initializes on both f7 and m7
- [ ] Correct address selected for each robot
- [ ] Dribbler speed adjusts during chase
- [ ] Dribbler stops when exiting chase
- [ ] Dribbler stops on pause
- [ ] Dribbler stops on shutdown
- [ ] Kicker fires when ball aligned
- [ ] Kicker cooldown works (0.5s minimum)
- [ ] Kicker relay deactivates after kick
- [ ] Both work during full game sequence

## Future Enhancements

Potential improvements:
- [ ] Adaptive dribbler speed based on ball capture status
- [ ] Variable kick power based on distance to goal
- [ ] Dribbler reverse mode for ball ejection
- [ ] Kick trajectory prediction
- [ ] Ball possession detection using current sensing
