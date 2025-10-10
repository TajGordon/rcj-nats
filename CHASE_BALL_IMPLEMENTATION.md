# Chase Ball State Implementation

## Overview
The `state_chase_ball()` method has been enhanced with advanced control algorithms for precise ball tracking and approach.

## Key Features

### 1. **Angle Smoothing**
- Uses a moving average filter (5 frames) to smooth the calculated ball angle
- Prevents jittery movement from camera noise or ball detection variance
- Properly handles angle wrapping using vector averaging (converts to unit vectors, averages, then converts back)

### 2. **Adaptive Speed Control**
The robot adjusts its speed based on the ball's distance (approximated by ball area):

| Ball Area | Distance | Speed | Purpose |
|-----------|----------|-------|---------|
| > 2000 | Very close | 0.25 | Precise final approach |
| > 1000 | Close | 0.4 | Moderate speed for control |
| > 500 | Medium | 0.6 | Good balance |
| < 500 | Far | 0.8 | Fast to close distance |

### 3. **Proportional Rotation Control**
- Continuously adjusts rotation based on horizontal error from ball position
- Rotation gain: 0.5 (adjustable for tuning)
- Maximum rotation: ±0.6 (clamped to prevent spinning)
- Negative feedback (rotation = -horizontal_error * gain) to center the ball

### 4. **Off-Center Handling**
When the ball is significantly off-center (|horizontal_error| > 0.5):
- Speed is reduced by 50% to prioritize rotation over translation
- Helps keep the ball in view while turning
- Prevents overshooting when approaching from the side

### 5. **Continuous Adjustment**
- Updates every frame at 30 Hz (configured in STATE_CONFIGS)
- Uses real-time camera feedback for reactive control
- No fixed motion patterns - purely feedback-driven

## Control Flow

```
1. Check if ball is detected
   ├─ Yes → Continue to step 2
   └─ No → Transition to SEARCH_BALL

2. Check if ball is close and centered
   ├─ Yes → Transition to LINEUP_KICK
   └─ No → Continue to step 3

3. Calculate raw angle to ball
   - Use atan2(horizontal_error, -vertical_error)

4. Apply angle smoothing
   - Add to 5-frame history
   - Average using vector method

5. Calculate adaptive speed
   - Based on ball area (distance proxy)

6. Calculate proportional rotation
   - Based on horizontal error
   - Clamp to ±0.6

7. Reduce speed if ball is far off-center
   - If |horizontal_error| > 0.5, speed *= 0.5

8. Send movement command to motors
   - move_robot_relative(angle, speed, rotation)

9. Log detailed state for debugging
```

## Camera Data Used

### BallDetectionResult Fields
- `detected` (bool): Whether ball is found
- `horizontal_error` (float): -1 (left) to +1 (right)
- `vertical_error` (float): -1 (top) to +1 (bottom)
- `area` (float): Pixel area of detected ball
- `is_close_and_centered` (bool): Ready for kick?

## State Transitions

### Entry (`on_enter_chase_ball`)
- Initializes tracking variables:
  - `_chase_angle_history`: List for angle smoothing
  - `_chase_max_history`: History buffer size (5)
- Sends camera command to prioritize ball detection

### Exit (`on_exit_chase_ball`)
- Cleans up tracking variables
- Prevents memory buildup from state variables

### Automatic Transitions
1. **To LINEUP_KICK**: When ball is close and centered
2. **To SEARCH_BALL**: When ball is lost (not detected)

## Tuning Parameters

You can adjust these values in the code to tune behavior:

```python
# Angle smoothing
_chase_max_history = 5  # Number of frames to average (line 773)

# Speed thresholds
area_very_close = 2000   # line 611
area_close = 1000        # line 613
area_medium = 500        # line 615

# Speed values
speed_very_close = 0.25  # line 612
speed_close = 0.4        # line 614
speed_medium = 0.6       # line 616
speed_far = 0.8          # line 618

# Rotation control
rotation_gain = 0.5      # line 627
max_rotation = 0.6       # line 631

# Off-center threshold
off_center_threshold = 0.5  # line 635
off_center_speed_mult = 0.5 # line 636
```

## Debug Logging

The state logs detailed information every frame:

```
Chasing ball: angle=45.2° (raw=47.1°), speed=0.60, rotation=-0.15, 
h_err=-0.30, v_err=0.12, area=750
```

### Log Fields
- `angle`: Smoothed angle to ball (degrees)
- `raw`: Raw calculated angle before smoothing
- `speed`: Current movement speed (0-1)
- `rotation`: Current rotation speed (-0.6 to +0.6)
- `h_err`: Horizontal error (-1 to +1)
- `v_err`: Vertical error (-1 to +1)
- `area`: Ball area in pixels

## Testing Recommendations

1. **Start in open area** with clear view of ball
2. **Observe logging** to verify:
   - Angles are reasonable
   - Speed adjusts as ball gets closer
   - Rotation responds to off-center ball
3. **Test edge cases**:
   - Ball far to the side (should rotate while slowing)
   - Ball very close (should move slowly)
   - Ball lost (should transition to search)
4. **Tune parameters** if needed:
   - Increase rotation_gain if robot doesn't turn enough
   - Decrease rotation_gain if robot oscillates
   - Adjust speed thresholds based on actual ball areas seen in logs

## Future Enhancements

Possible improvements:
1. Add field-relative movement using localization data
2. Implement predictive tracking for moving balls
3. Add obstacle avoidance using ToF sensors
4. Use PID controller instead of simple proportional control
5. Add acceleration limiting for smoother motion
