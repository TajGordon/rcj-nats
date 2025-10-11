# Motor and Dribbler Updates

## Changes Made

### 1. Right Motor Speed Multiplier (1.3x)

Applied a **1.3x speed multiplier** to the right motors to compensate for hardware differences or drift.

**Location:** `hypemage/motor_control.py` in `move_robot_relative()`

**Affected Motors:**
- `front_right` (motor index 2)
- `back_right` (motor index 3)

**Implementation:**
```python
# After calculating initial motor speeds
front_right *= 1.3
back_right *= 1.3

# Then normalize to keep within [-1.0, 1.0] range
```

**Why this works:**
The multiplier is applied **before normalization**, so:
1. Right motors get 1.3x boost
2. All motors are normalized together to stay within valid range
3. Right motors maintain their proportional boost relative to left motors

**Example:**
If the raw calculation gives:
- Left motors: 0.5
- Right motors: 0.5

After multiplier:
- Left motors: 0.5
- Right motors: 0.65

After normalization (if needed):
- Left motors: 0.5 / 0.65 = 0.77
- Right motors: 0.65 / 0.65 = 1.0

The right motors still spin faster proportionally!

### 2. Auto-Dribbler when Ball is Close

Automatically enables the dribbler at **speed 1.8** when the ball is close to the robot.

**Location:** `hypemage/scylla.py` in `state_chase_ball()`

**Behavior:**

#### Ball Detected and Close:
```python
if ball.is_close:
    self.enable_dribbler(speed=1.8)
```
- Dribbler turns ON at speed 1.8
- Prepares to capture the ball

#### Ball Detected but Not Close:
```python
else:
    self.disable_dribbler()
```
- Dribbler turns OFF
- Saves power when ball is far away

#### Ball Lost but Was Close:
```python
if self._last_ball_was_close:
    self.enable_dribbler(speed=1.8)
```
- **Keeps dribbler running** even if ball is briefly lost
- Assumes ball might be in the dribbler area
- Continues for up to 10 frames (~0.33 seconds)

#### Ball Lost for 10+ Frames:
```python
if self._frames_without_ball >= 10:
    self._last_ball_was_close = False  # Reset
    self.transition_to(State.SEARCH_BALL)
```
- Resets the close state
- Transitions to search mode

## State Tracking

### New State Variables

Added to `__init__`:
```python
self._last_ball_was_close = False  # Track if last seen ball was close
```

### State Reset

In `on_enter_chase_ball()`:
```python
self._frames_without_ball = 0
self._last_ball_was_close = False
```

Ensures clean state when entering chase mode.

## Dribbler Speed: Why 1.8?

The dribbler speed is set to **1.8** which is:
- Higher than normal (1.0)
- Provides stronger grip on the ball
- Compensates for the robot moving at 0.10 speed
- Ensures ball stays in dribbler area

**Note:** The actual motor controller may clamp this to a max value (usually 1.0) or scale it appropriately.

## Flow Diagram

```
┌─────────────────┐
│  CHASE_BALL     │
│  State Entered  │
└────────┬────────┘
         │
         ▼
┌────────────────────────┐
│  Ball Detected?        │
└────┬──────────────┬────┘
     │ YES          │ NO
     ▼              ▼
┌─────────────┐  ┌──────────────────┐
│ Ball Close? │  │ Was Last Close?  │
└──┬─────┬────┘  └───┬──────────┬───┘
   │YES  │NO         │YES       │NO
   ▼     ▼           ▼          ▼
[Drib  [Drib     [Keep Drib] [No Drib]
 ON]    OFF]        ON 1.8]
1.8]
```

## Testing Recommendations

### Test 1: Motor Balance
1. Drive forward in a straight line
2. Observe if robot drifts left or right
3. Expected: Should move straighter with 1.3x multiplier on right motors

### Test 2: Dribbler Activation
1. Approach ball slowly
2. Watch for dribbler to turn on when ball is close
3. Expected: Dribbler spins at 1.8 speed when `ball.is_close` is True

### Test 3: Dribbler Persistence
1. Get ball close (dribbler on)
2. Cover camera briefly (ball lost)
3. Expected: Dribbler stays on for up to 10 frames

### Test 4: Dribbler Deactivation
1. Chase ball from far away
2. Expected: Dribbler is OFF when ball is far
3. Stop chasing (ball far for 10+ frames)
4. Expected: Dribbler turns OFF

## Configuration

### Adjusting Right Motor Multiplier

In `motor_control.py`, change this line:
```python
right_motor_multiplier = 1.3  # Adjust this value
```

**Values:**
- `1.0` = No compensation (normal)
- `1.1` = 10% faster
- `1.3` = 30% faster (current)
- `1.5` = 50% faster

### Adjusting Dribbler Speed

In `scylla.py`, change this value:
```python
self.enable_dribbler(speed=1.8)  # Adjust this value
```

**Values:**
- `0.5` = Half speed
- `1.0` = Normal speed
- `1.8` = 80% over normal (current)
- `2.0` = Double speed

### Proximity Threshold

The `ball.is_close` flag is determined by the proximity threshold in `config.json`:
```json
"detection": {
  "proximity_threshold": 5000
}
```

This is based on ball area (pixels²). Adjust this to change when dribbler activates.

## Benefits

### ✅ Right Motor Compensation
- Corrects for hardware imbalance
- Straighter movement
- Better control

### ✅ Smart Dribbler Control
- Automatic activation when needed
- Saves power when ball is far
- Persists through brief ball loss
- High speed (1.8) for secure ball grip

### ✅ Improved Ball Control
- Dribbler ready when ball arrives
- Continues spinning if ball captured but hidden
- Prevents ball escape during approach

## Logging

Watch for these log messages:

```
Chasing ball: ... ball_pos=(320, 280)
[INFO] Dribbler enabled at speed 1.8
```

When ball is close and dribbler activates.

```
Ball not detected (frame 3/10), continuing forward
[INFO] Dribbler enabled at speed 1.8
```

When ball is lost but dribbler stays on (was close).
