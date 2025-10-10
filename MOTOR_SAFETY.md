# Motor Safety Features

## Overview
The Scylla FSM includes multiple layers of motor safety to ensure motors always stop, even in crash scenarios.

## Safety Layers

### 1. Normal Shutdown (Ctrl+C)
- **Trigger**: User presses Ctrl+C
- **Flow**:
  1. `KeyboardInterrupt` caught in `start()` method
  2. Logs "Keyboard interrupt received"
  3. Calls `shutdown()` which stops motors first
  4. Then stops all processes cleanly

### 2. Exception Handling
- **Trigger**: Any unhandled exception in main loop
- **Flow**:
  1. Exception caught in `start()` method
  2. Logs critical error with full traceback
  3. `finally` block ensures `shutdown()` is called
  4. Motors stopped as first step of shutdown

### 3. State Handler Errors
- **Trigger**: Exception in any `state_*` method
- **Flow**:
  1. Exception caught in `_update()` wrapper
  2. Logs error with state name and traceback
  3. Immediately stops motors
  4. Re-raises exception to trigger main loop handler

### 4. Emergency Motor Stop (atexit)
- **Trigger**: Process exit for ANY reason
- **Flow**:
  1. Python's `atexit` handler calls `_emergency_motor_stop()`
  2. Directly calls `motor_controller.stop()`
  3. Safe to call multiple times (idempotent)
  4. Works even if shutdown() wasn't called

### 5. SIGTERM Handler
- **Trigger**: Kill signal (e.g., `kill <pid>`)
- **Flow**:
  1. Signal handler catches SIGTERM
  2. Calls `_emergency_motor_stop()`
  3. Exits cleanly

### 6. Pause/Resume System
- **Trigger**: Any button press
- **Flow**:
  1. Toggle `_is_paused` flag
  2. When pausing: immediately stops motors
  3. When resuming: allows state to resume control

## Testing

### Test Normal Shutdown
```bash
# Start the robot
python hypemage/scylla.py

# Press Ctrl+C
# Expected: "✓ Motors stopped" message before exit
```

### Test Exception Handling
```python
# Add this to any state handler to test:
raise Exception("Test crash")

# Expected: Motors stop, error logged, clean exit
```

### Test Kill Signal
```bash
# Start the robot
python hypemage/scylla.py

# In another terminal
ps aux | grep scylla  # Get PID
kill <PID>

# Expected: Motors stop via atexit handler
```

### Test Pause System
```bash
# Start the robot
python hypemage/scylla.py

# Press any configured button (D13, D19, or D26)
# Expected: "⏸️  PAUSED" message, motors stop
# Press button again
# Expected: "▶️  RESUMED" message, motors resume
```

## Safety Guarantees

✅ **Motors always stop on Ctrl+C** (via shutdown)  
✅ **Motors always stop on crash** (via _update exception handler + atexit)  
✅ **Motors always stop on kill signal** (via SIGTERM handler + atexit)  
✅ **Motors always stop on pause** (via toggle_pause)  
✅ **Multiple safety layers** (redundancy prevents failures)  

## Code Locations

- `_register_shutdown_handlers()`: Registers atexit and signal handlers (line ~186)
- `_emergency_motor_stop()`: Failsafe motor stop (line ~211)
- `start()`: Main loop with KeyboardInterrupt and Exception handling (line ~275)
- `_update()`: State handler exception wrapper (line ~302)
- `shutdown()`: Clean shutdown with motor stop priority (line ~1006)
- `_toggle_pause()`: Pause system with motor stop (line ~538)

## Maintenance Notes

⚠️ **NEVER** remove the `atexit.register()` call  
⚠️ **ALWAYS** keep motor stop as first step in `shutdown()`  
⚠️ **TEST** safety features after any motor control changes  
⚠️ **VERIFY** exception handling covers all state handlers  

## Emergency Stop Checklist

If motors won't stop:
1. Check `motor_controller.stop()` is working
2. Verify hardware emergency stop button (physical safety)
3. Power cycle the robot as last resort
4. Check motor controller logs for initialization errors
