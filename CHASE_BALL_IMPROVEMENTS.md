# Chase Ball Improvements - Speed & Lost Ball Handling

## Changes Made

### 1. Doubled Speed
**Before:** `base_speed = 0.05`  
**After:** `base_speed = 0.10`

The robot now moves twice as fast when chasing the ball, making it more aggressive in pursuit.

### 2. Lost Ball Tolerance (10 Frame Buffer)
Added frame-based tracking to prevent immediate transition to search mode when ball is briefly lost.

**New Behavior:**
- Ball detected → Reset counter, continue chasing
- Ball not detected → Increment counter, keep moving forward
- Counter reaches 10 → Transition to SEARCH_BALL

This prevents the robot from giving up too quickly when the ball is momentarily obscured or detection has a brief hiccup.

## Implementation Details

### Added State Variable
```python
# In __init__
self._frames_without_ball = 0  # Counter for frames without ball detection
```

### Updated `state_chase_ball()` Logic

#### When Ball IS Detected:
```python
if ball.detected:
    # Reset counter
    self._frames_without_ball = 0
    
    # Move at 0.10 speed with rotation
    self.motor_controller.move_robot_relative(
        angle=0,
        speed=0.10,  # Doubled from 0.05
        rotation=rotation
    )
```

#### When Ball NOT Detected:
```python
else:
    # Increment counter
    self._frames_without_ball += 1
    
    # Only give up after 10 frames
    if self._frames_without_ball >= 10:
        logger.info(f"Ball lost for {self._frames_without_ball} frames - transitioning to search")
        self._frames_without_ball = 0
        self.transition_to(State.SEARCH_BALL)
    else:
        # Keep moving forward while briefly losing ball
        logger.debug(f"Ball not detected (frame {self._frames_without_ball}/10), continuing forward")
        self.motor_controller.move_robot_relative(
            angle=0,
            speed=0.10,
            rotation=0.0
        )
```

### State Entry Handler
```python
def on_enter_chase_ball(self):
    # Reset counter when entering chase state
    self._frames_without_ball = 0
```

This ensures clean state when transitioning into chase mode.

## Benefits

### 🚀 Faster Pursuit
- **2x speed increase** (0.05 → 0.10)
- More aggressive ball chasing
- Faster approach to ball

### 🎯 More Reliable Tracking
- **10 frame buffer** before giving up
- At 30 fps, this is ~0.33 seconds of tolerance
- Prevents false transitions from:
  - Brief occlusion
  - Momentary detection failures
  - Ball passing through blind spots
  - Camera processing hiccups

### 🔄 Smoother State Transitions
- Counter reset on state entry
- Counter reset when ball reappears
- Clean state management

## Example Scenario

```
Frame 1: Ball detected → Chase (counter = 0)
Frame 2: Ball detected → Chase (counter = 0)
Frame 3: Ball NOT detected → Continue forward (counter = 1)
Frame 4: Ball NOT detected → Continue forward (counter = 2)
Frame 5: Ball detected → Chase (counter = 0)  ← Ball reappeared!
...
Frame 20: Ball NOT detected → Continue forward (counter = 1)
Frame 21-29: Ball NOT detected → Continue forward (counter = 2-10)
Frame 30: Ball NOT detected → SEARCH MODE (counter = 10, transition!)
```

## Logging

### Ball Detected:
```
Chasing ball: angle=12.3°, distance=145.2px, speed=0.100, rotation=0.012, h_err=-0.42, ball_pos=(289, 315)
```

### Ball Lost (Buffering):
```
Ball not detected (frame 3/10), continuing forward
```

### Ball Lost (Transition):
```
Ball lost for 10 frames - transitioning to search
```

## Testing Recommendations

1. **Test with ball occlusion**: Put hand in front of ball briefly
   - Expected: Robot continues forward, doesn't give up immediately
   
2. **Test with ball removal**: Remove ball completely
   - Expected: Robot continues ~0.33s, then transitions to search
   
3. **Test speed**: Observe chase speed
   - Expected: Noticeably faster than before (2x)

4. **Test reacquisition**: Let ball disappear briefly then reappear
   - Expected: Counter resets, continues chasing smoothly

## Configuration

If you want to adjust the tolerance, modify this line in `state_chase_ball()`:

```python
if self._frames_without_ball >= 10:  # Change 10 to desired frame count
```

**Frame count to time conversion** (at 30 fps):
- 5 frames = ~0.17 seconds
- 10 frames = ~0.33 seconds  ← Current setting
- 15 frames = ~0.50 seconds
- 30 frames = ~1.00 second
