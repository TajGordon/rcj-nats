# Error Handling and Component Initialization

## Overview

The robot has **critical** and **non-critical** components. Critical failures cause immediate shutdown, while non-critical failures allow degraded operation with warnings.

---

## Component Classification

### **Critical Components** (Robot exits if these fail)

| Component | Why Critical | Failure Action |
|-----------|--------------|----------------|
| **Motors** | Cannot move safely without motor control | Exit with code 1 |
| **Camera** (in vision states) | Cannot chase ball/navigate without vision | Exit with code 1 |
| **I2C Bus** | Motors require I2C communication | Exit with code 1 |

### **Non-Critical Components** (Robot continues with warnings)

| Component | Degraded Behavior | Failure Action |
|-----------|-------------------|----------------|
| **Localization** | Use camera-only navigation (less accurate) | Continue with warning |
| **Goal Localizer** | Skip goal detection, use ball only | Continue with warning |
| **IMU** | No heading data (rely on wheel encoders) | Continue with warning |
| **ToF Sensors** | No distance to walls (less precise positioning) | Continue with warning |

---

## Initialization Flow

```
┌─────────────────────────────────────────────┐
│ 1. Import hardware libraries               │
│    - board, busio (I2C)                    │
│    - picamera2 (camera)                    │
│    - steelbar_powerful_bldc_driver (motors)│
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ 2. Initialize CRITICAL components           │
│    a) Motor Controller                      │
│       - Initialize I2C bus                  │
│       - Detect all 4 motors                 │
│       - Read stored calibration from EEPROM │
│       - Set PID values                      │
│       - Start watchdog thread               │
│    ❌ FAIL → Exit with code 1               │
│    ✓ SUCCESS → status.motors = True        │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ 3. Log component status                     │
│    ComponentStatus.summary()                │
│    → "[CRITICAL: Motors: ✓, Camera: ✗]"    │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ 4. Start FSM main loop                      │
│    state transitions require status checks  │
└─────────────────────────────────────────────┘
```

---

## Error Handling Patterns

### **1. Motor Controller Initialization**

```python
# In motor_control.py
def _init_motors(self) -> bool:
    """Returns False on critical failure"""
    if not _HAS_MOTOR_HARDWARE:
        logger.critical("Motor hardware libraries not available - CANNOT OPERATE")
        return False
    
    try:
        self.i2c = busio.I2C(board.SCL, board.SDA)
        logger.info("I2C bus initialized")
        
        # Initialize all motors...
        if self.motor_count == 0:
            logger.critical("CRITICAL: No motors initialized")
            return False
        elif self.motor_count < 4:
            logger.error(f"Only {self.motor_count}/4 motors initialized")
            return False  # Need ALL motors
        
        return True
    except Exception as e:
        logger.critical(f"I2C/motor init failed: {e}", exc_info=True)
        return False

# In __init__
def __init__(self, ...):
    success = self._init_motors()
    if not success:
        raise MotorInitializationError("Cannot operate safely")
```

**Result**: 
- ✓ All 4 motors working → Continue normally
- ❌ Missing motors or I2C failure → Raise `MotorInitializationError`

---

### **2. Camera Initialization**

```python
# In camera_conversion.py
def __init__(self, config=None):
    try:
        if _HAS_PICAMERA:
            self.picam2 = Picamera2()
            # configure...
            self.picam2.start()
            logger.info("Picamera2 initialized successfully")
        else:
            # Try OpenCV fallback
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise CameraInitializationError("OpenCV camera failed")
            logger.info("OpenCV camera initialized")
    except Exception as e:
        logger.critical(f"Camera init failed: {e}", exc_info=True)
        raise CameraInitializationError(f"Camera failed: {e}")
```

**Result**:
- ✓ Picamera2 works → Use Picamera2
- ⚠️ Picamera2 unavailable → Try OpenCV
- ❌ Both fail → Raise `CameraInitializationError`

---

### **3. FSM Component Initialization**

```python
# In scylla.py
def _init_critical_components(self):
    """Exit immediately if critical components fail"""
    
    # CRITICAL: Motors
    try:
        self.motor_controller = MotorController(config=motor_config)
        self.status.motors = True
        logger.info("✓ Motor controller initialized")
    except MotorInitializationError as e:
        logger.critical(f"✗ CRITICAL: {e}")
        logger.critical("Robot cannot operate - exiting...")
        sys.exit(1)  # Exit immediately
    
    logger.info(f"Status: {self.status.summary()}")
    # Continues to main loop...
```

**Result**:
- ✓ Motors OK → Log success, continue to main loop
- ❌ Motors fail → Log critical error, exit process with code 1

---

## State Transition Validation

Before entering states that need specific components, check status:

```python
def _manage_resources(self):
    """Start/stop processes based on state requirements"""
    required = self.STATE_CONFIGS[self.current_state]
    
    # Check if camera is required but not available
    if required.needs_camera and not self.status.camera:
        logger.critical(f"State {self.current_state} needs camera but camera failed")
        logger.critical("Cannot continue - transitioning to STOPPED")
        self.transition_to(State.STOPPED)
        return
    
    # Start camera if needed and available
    if required.needs_camera and 'camera' not in self.processes:
        if not self._start_camera_process():
            logger.critical("Failed to start camera process")
            self.transition_to(State.STOPPED)
            sys.exit(1)  # Critical for vision states
```

---

## Logging Performance Impact

### **File Writes (to SD card)**

| Operation | Time | Impact |
|-----------|------|--------|
| **Buffered write** (default) | ~5-15μs | ✓ Negligible |
| **Flush to SD card** | ~1-10ms | ❌ Significant (200x slower) |
| **Buffer fill** | Writes every ~4KB | ✓ Automatic, optimized |

**Best Practice**: Let Python handle buffering. Only flush on critical errors:
```python
logger.critical("Robot shutting down")
logging.shutdown()  # Flushes all logs
```

### **Colored Terminal Output**

| Library | Time per log | Notes |
|---------|--------------|-------|
| **No color** | ~5μs | Simple string formatting |
| **colorlog** | ~5.2μs | Just adds ANSI codes (~0.2μs overhead) |
| **Manual ANSI** | ~5.1μs | Equivalent to colorlog |

**Verdict**: Color adds **~0.1-0.2μs overhead** (essentially free).

---

## ComponentStatus Tracking

```python
@dataclass
class ComponentStatus:
    # Critical
    motors: bool = False
    camera: bool = False
    
    # Non-critical
    localization: bool = False
    goal_localizer: bool = False
    imu: bool = False
    tof_sensors: List[bool] = field(default_factory=lambda: [False]*4)
    
    def all_critical_ok(self) -> bool:
        return self.motors  # Camera checked per-state
    
    def summary(self) -> str:
        return f"[Motors: {'✓' if self.motors else '✗'}] ..."
```

**Usage**:
```python
# In FSM
self.status = ComponentStatus()

# After motor init
self.status.motors = True

# Before state transition
if not self.status.motors:
    logger.critical("Cannot operate without motors")
    sys.exit(1)

# Log status
logger.info(self.status.summary())
# → "[CRITICAL: Motors: ✓, Camera: ✗] [NON-CRITICAL: ...]"
```

---

## Exit Codes

| Code | Meaning | Example |
|------|---------|---------|
| **0** | Normal shutdown | User pressed emergency stop |
| **1** | Critical component failure | Motors failed to initialize |
| **2** | Configuration error | Invalid config.json |
| **130** | KeyboardInterrupt (Ctrl+C) | User terminated |

**Systemd Behavior**:
- Exit code 0 → Don't restart
- Exit code 1 → Restart after delay (see `DEPLOYMENT.md`)
- Exit code 130 → Don't restart (manual termination)

---

## Testing Component Failures

### **Simulate Motor Failure**

Temporarily rename library import:
```python
# In motor_control.py
try:
    import board_DISABLED  # Will fail
    import busio
    ...
```

**Expected**:
```
CRITICAL - Motor hardware libraries not available - CANNOT OPERATE
CRITICAL - Robot cannot operate safely without motors
CRITICAL - Exiting...
Process exited with code 1
```

### **Simulate Camera Failure**

Disconnect camera ribbon cable or disable library:
```python
# In camera_conversion.py
try:
    from picamera2_DISABLED import Picamera2  # Will fail
```

**Expected** (if in CHASE_BALL state):
```
CRITICAL - Camera init failed: No module named 'picamera2_DISABLED'
CRITICAL - State CHASE_BALL needs camera but camera failed
CRITICAL - Cannot continue - transitioning to STOPPED
Process exited with code 1
```

### **Simulate Non-Critical Failure**

```python
# In scylla.py - localization init
try:
    # Start localization process
    ...
except Exception as e:
    logger.warning(f"Localization failed to start: {e}")
    self.status.localization = False
    logger.warning("Continuing without localization (degraded mode)")
    # DO NOT exit - continue operation
```

**Expected**:
```
WARNING - Localization failed to start: ...
WARNING - Continuing without localization (degraded mode)
INFO - Robot operating in degraded mode
```

---

## Summary

### **Critical Failures → EXIT**
1. No motor hardware libraries
2. I2C bus initialization fails
3. Zero motors detected (need all 4)
4. Camera fails when in vision-dependent state

### **Non-Critical Failures → WARN**
1. Localization process fails (use camera only)
2. IMU not detected (skip heading data)
3. ToF sensors missing (skip wall distance)
4. Goal localizer error (skip goal detection)

### **Performance**
- File logging (buffered): ~5-15μs ✓
- File flushing: ~1-10ms ❌ (only on critical errors)
- Colored terminal: +0.1-0.2μs ✓ (essentially free)

### **Implementation Status**
- ✅ Motor controller raises `MotorInitializationError`
- ✅ Camera raises `CameraInitializationError`
- ✅ FSM tracks `ComponentStatus`
- ✅ FSM exits on critical motor failure
- ✅ Colored logging support (via colorlog)
- ⚠️ TODO: Add state transition validation (check camera before CHASE_BALL)
- ⚠️ TODO: Add localization/IMU/ToF graceful degradation
