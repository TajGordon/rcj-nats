# Chase Ball Simplification & Angle Convention Update

## Changes Made

### 1. Removed SEARCH_BALL State Transitions

**Before:** Chase ball would transition to SEARCH_BALL state after losing ball for 10+ frames

**After:** Chase ball simply stops and waits when ball is lost for extended period

#### Updated Behavior:

```python
if ball.detected:
    # Chase towards ball using ball.angle directly
    motor_controller.move_robot_relative(angle=ball.angle, speed=0.07, rotation=0.0)
    
else:
    # Ball lost
    if frames_without_ball >= 10:
        # Stop and wait (no state transition)
        motor_controller.stop()
    else:
        # Keep moving forward slowly while briefly lost
        motor_controller.move_robot_relative(angle=0, speed=0.03, rotation=0.0)
```

**Key Changes:**
- ✅ No more `transition_to(State.SEARCH_BALL)`
- ✅ Just stops and waits when ball is lost
- ✅ Counter keeps counting (doesn't reset) to show how long we've been waiting
- ✅ Simpler logic - chase or wait, nothing else

### 2. Simplified Movement Logic

**Before:** Used differential steering with forward movement + rotation component
```python
# Old complex logic
rotation = -ball.horizontal_error * rotation_gain
motor_controller.move_robot_relative(angle=0, speed=base_speed, rotation=rotation)
```

**After:** Moves directly towards ball angle
```python
# New simple logic
motor_controller.move_robot_relative(angle=ball.angle, speed=0.07, rotation=0.0)
```

**Benefits:**
- 🎯 More direct path to ball
- 🔧 Simpler code (no rotation calculations)
- 📐 Uses omnidirectional capability fully
- 🚀 Let the hardware do the work

### 3. Standardized Angle Convention (Counterclockwise Positive)

Updated all angle documentation to use **standard mathematical convention**:
- **Positive angles = Counterclockwise (LEFT)**
- **Negative angles = Clockwise (RIGHT)**

#### Updated Locations:

**File: `camera.py`** (3 locations)
- Ball detection (regular)
- Ball detection (close zone)
- Goal detection

**Documentation updated:**
```python
# Standard mathematical convention: positive angles = counterclockwise
# Result: 0° = robot forward, +90° = left (counterclockwise), -90° = right (clockwise), ±180° = backward
```

**File: `motor_control.py`**
```python
# Args:
#   angle: Direction in degrees (0=forward, positive=counterclockwise/left, negative=clockwise/right)
#          Examples: 0=forward, +90=left, -90=right, ±180=backward
```

**File: `scylla.py`**
```python
# ball.angle: 0° = forward, positive = counterclockwise (left), negative = clockwise (right)
```

## Angle Convention Reference

### Standard Mathematical Convention (NOW USED)

```
         +90° (LEFT)
              |
              |
±180° ------(0,0)------ 0° (FORWARD)
 (BACK)       |
              |
         -90° (RIGHT)
```

**Range:** -180° to +180°
- **0°** = Forward (straight ahead)
- **+90°** = Left (counterclockwise)
- **-90°** = Right (clockwise)
- **±180°** = Backward

**Examples:**
- Ball at 0° → Move forward
- Ball at +45° → Move forward-left diagonal
- Ball at -45° → Move forward-right diagonal
- Ball at +90° → Move directly left (strafe left)
- Ball at -90° → Move directly right (strafe right)
- Ball at ±180° → Move backward

### Why This Convention?

1. **Standard Math:** Matches `atan2()` and trigonometric functions
2. **Intuitive:** Left is positive (like turning left on a number line)
3. **Consistent:** Same convention across camera and motor control
4. **Universal:** Common in robotics and mathematics

## State Machine Simplification

### Before (Complex):
```
CHASE_BALL
    ├─ Ball detected → Chase with rotation
    └─ Ball lost > 10 frames → SEARCH_BALL
                                    ├─ Rotate to search
                                    └─ Ball found → CHASE_BALL
```

### After (Simple):
```
CHASE_BALL
    ├─ Ball detected → Move towards ball angle
    └─ Ball lost > 10 frames → Stop and wait
                                    └─ Ball reappears → Continue chasing
```

**Removed:**
- State transitions
- Search state logic
- Complex state management
- Rotation calculations

**Kept:**
- Direct movement towards ball
- Dribbler control when close
- Brief continuation when ball lost
- Simple stop-and-wait when lost too long

## Code Flow

### Ball Detected:
```python
1. Reset frames_without_ball counter
2. Check if ball is close
   - Yes: Enable dribbler (1.8 speed)
   - No: Disable dribbler
3. Move directly towards ball
   - angle=ball.angle (direction to ball)
   - speed=0.07 (constant)
   - rotation=0.0 (no rotation)
```

### Ball Not Detected (< 10 frames):
```python
1. Increment frames_without_ball counter
2. Keep dribbler on if last ball was close
3. Continue moving forward slowly (speed=0.03)
4. Log: "Ball not detected (frame X/10), continuing"
```

### Ball Not Detected (≥ 10 frames):
```python
1. Stop motors (stay still)
2. Keep dribbler on if last ball was close
3. Log: "Ball lost for X frames - stopping and waiting"
4. Wait for ball to reappear
```

### Ball Reappears:
```python
1. Counter resets to 0
2. Resume chasing immediately
3. No state transition needed
```

## Benefits

### ✅ Simpler Code
- Removed ~20 lines of rotation calculation code
- Removed state transition logic
- Removed search state handling
- Single clear responsibility: chase or wait

### ✅ More Direct Movement
- Omnidirectional movement towards ball
- No need to align then move forward
- Uses full robot capability
- Faster ball acquisition

### ✅ Consistent Conventions
- All angles use counterclockwise-positive
- Camera, motors, and control logic aligned
- Easier to reason about movement
- Fewer sign errors

### ✅ Predictable Behavior
- Ball detected → Chase
- Ball lost briefly → Keep moving
- Ball lost long → Stop and wait
- No complex state transitions

## Testing Recommendations

### Test 1: Direct Movement
1. Place ball at various angles (0°, ±45°, ±90°, ±180°)
2. Observe robot movement
3. Expected: Robot moves directly towards ball at each angle

### Test 2: Left/Right Convention
1. Place ball to the left (robot should see +90° angle)
2. Place ball to the right (robot should see -90° angle)
3. Expected: Positive angles = left, negative angles = right

### Test 3: Lost Ball Behavior
1. Chase ball successfully
2. Remove ball from view
3. Expected:
   - Frames 1-9: Continue forward slowly
   - Frame 10+: Stop and wait
   - Ball reappears: Resume chasing immediately

### Test 4: No State Transitions
1. Chase ball
2. Remove ball for extended period (>10 frames)
3. Expected: Robot stops but stays in CHASE_BALL state
4. Add ball back
5. Expected: Resume chasing without state change

## Logging Changes

### New Log Messages:

**Ball detected:**
```
Chasing ball: angle=45.2°, distance=123.4px, speed=0.070, ball_pos=(320, 240)
```

**Ball lost briefly:**
```
Ball not detected (frame 3/10), continuing
```

**Ball lost extended:**
```
Ball lost for 10 frames - stopping and waiting
Ball lost for 15 frames - stopping and waiting  (counter keeps incrementing)
```

## Migration Notes

### Removed Code:
- ❌ `rotation_gain` calculation
- ❌ `rotation` clamping
- ❌ `horizontal_error * rotation_gain` logic
- ❌ `transition_to(State.SEARCH_BALL)`
- ❌ Counter reset when stopping
- ❌ Close state reset when transitioning

### Updated Code:
- ✅ `angle=ball.angle` (was `angle=0`)
- ✅ `rotation=0.0` (was calculated)
- ✅ `motor_controller.stop()` (was state transition)
- ✅ Counter keeps incrementing (was reset)
- ✅ Speed 0.03 when lost briefly (was 0.07)

## Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Movement** | Forward + rotation | Direct to angle |
| **Lost ball** | → SEARCH_BALL | Stop and wait |
| **Angle sign** | Inconsistent docs | Counterclockwise + |
| **Complexity** | ~80 lines | ~60 lines |
| **States used** | 2 (CHASE + SEARCH) | 1 (CHASE only) |
| **Logic** | Complex steering | Simple direction |

The robot now has a single clear behavior in CHASE_BALL state: move directly towards the ball, or stop and wait if it's not visible. No complex state transitions, no rotation calculations, just simple effective chasing! 🎯⚽
