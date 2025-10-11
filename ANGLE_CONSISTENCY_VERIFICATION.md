# Angle Consistency Between Visualization and Chase Ball

## Verification: Same Angle Source

Both the mirror visualization and the chase_ball state use **identical angle data** from the camera.

### Data Flow

```
Camera Detection (camera.py)
    ├─ detect_ball() calculates ball.angle
    │
    ├─→ Visualization (test_mirror_visualization.py)
    │   └─ Displays: ball_result.angle
    │
    └─→ Scylla (scylla.py)
        └─ Uses: ball.angle in move_robot_relative()
```

### Source Verification

**Camera Detection (`camera.py`):**
```python
# Calculate angle from forward direction
angle_rad = math.atan2(dx, -dy)
angle = math.degrees(angle_rad)
angle = angle + 180.0  # 180° offset for camera orientation
if angle > 180.0:
    angle -= 360.0
# Returns: ball.angle
```

**Visualization (`test_mirror_visualization.py`):**
```python
ball_result = camera.detect_ball(frame)
data['ball'] = {
    'angle': round(ball_result.angle, 1),  # ← Same source
    ...
}
```

**Chase Ball (`scylla.py`):**
```python
ball = self.latest_camera_data.ball
movement_angle = ball.angle  # ← Same source
motor_controller.move_robot_relative(
    angle=movement_angle,  # ← Exact angle displayed
    ...
)
```

## Why Angle Changes Frame-to-Frame

The angle **should** change when:

### 1. Ball is Actually Moving
```
Frame 1: Ball at (320, 200) → angle = 0°
Frame 2: Ball at (340, 200) → angle = 6.3° (ball moved right)
Frame 3: Ball at (360, 200) → angle = 12.5° (ball moved more right)
```
✅ **This is correct behavior**

### 2. Robot is Moving
```
Frame 1: Robot stationary, ball ahead → angle = 0°
Frame 2: Robot moved right, ball now appears left → angle = +15°
Frame 3: Robot moved more right, ball more left → angle = +30°
```
✅ **This is correct behavior**

### 3. Ball Detection Jitter
```
Frame 1: Ball detected at (320, 200) → angle = 0°
Frame 2: Ball detected at (322, 201) → angle = 1.1° (detection noise)
Frame 3: Ball detected at (319, 199) → angle = -0.5° (detection noise)
```
⚠️ **This is normal but can be smoothed**

## Enhanced Logging

Updated the chase_ball logging to clearly show the angle being used:

### New Log Format:
```
Chasing ball: USING_ANGLE=12.3° (ball.angle=12.3°) distance=145.2px speed=0.070 ball_pos=(342, 215) h_err=0.069 frame_id=123
```

### Log Fields:
- **USING_ANGLE**: The exact angle passed to `move_robot_relative()`
- **ball.angle**: The angle from camera detection (should match USING_ANGLE)
- **distance**: Distance from center in pixels
- **speed**: Movement speed (0.07)
- **ball_pos**: Ball pixel coordinates (x, y)
- **h_err**: Horizontal error (-1.0 to 1.0)
- **frame_id**: Camera frame number

### Verification Steps:

1. **Compare visualization to log:**
   - Visualization shows: "Ball: 12.3°"
   - Log shows: "USING_ANGLE=12.3°"
   - ✅ Should be identical

2. **Check frame_id:**
   - If frame_id increments, angle can legitimately change
   - Same frame_id = same detection = same angle

3. **Monitor ball_pos:**
   - If ball_pos changes, angle should change
   - Stable ball_pos = stable angle

## Angle Stability Analysis

### Expected Behavior:

**Stationary Ball, Stationary Robot:**
```
Frame 100: angle=12.3°, ball_pos=(342, 215)
Frame 101: angle=12.3°, ball_pos=(342, 215)  ✅ Stable
Frame 102: angle=12.3°, ball_pos=(342, 215)  ✅ Stable
```

**Moving Robot towards Ball:**
```
Frame 100: angle=12.3°, ball_pos=(342, 215)
Frame 101: angle=11.8°, ball_pos=(338, 212)  ✅ Angle decreasing (getting aligned)
Frame 102: angle=11.2°, ball_pos=(334, 210)  ✅ Continuing to align
```

**Detection Jitter (Normal):**
```
Frame 100: angle=12.3°, ball_pos=(342, 215)
Frame 101: angle=12.5°, ball_pos=(343, 216)  ⚠️ Small jitter (±2px)
Frame 102: angle=12.1°, ball_pos=(341, 214)  ⚠️ Small jitter (±2px)
```

**Excessive Jitter (Problem):**
```
Frame 100: angle=12.3°, ball_pos=(342, 215)
Frame 101: angle=25.7°, ball_pos=(380, 230)  ❌ Large jump (detection issue)
Frame 102: angle=3.2°,  ball_pos=(310, 200)  ❌ Large jump (detection issue)
```

## Debugging Angle Issues

### Issue: "Angle is moving around"

#### Check 1: Is the ball actually moving?
```bash
# Watch the ball_pos in logs
grep "ball_pos" logs.txt

# If ball_pos is stable but angle changes → detection problem
# If ball_pos is changing → ball or robot is moving (correct)
```

#### Check 2: Is the robot moving?
```bash
# When robot moves, ball position in camera changes
# This causes angle to change (expected behavior)

# Stop robot movement and check if angle stabilizes
```

#### Check 3: Detection jitter amount?
```bash
# Calculate angle change between frames:
Frame N:   angle=12.3°
Frame N+1: angle=12.5°
Jitter: 0.2° (acceptable)

Frame N:   angle=12.3°
Frame N+1: angle=18.7°
Jitter: 6.4° (problem!)
```

### Potential Causes of Large Angle Changes:

1. **Multiple ball detections:**
   - Camera switches between detecting different orange objects
   - Solution: Improve color filtering, increase min_ball_radius

2. **Mirror mask issues:**
   - Ball detection near mirror edge
   - Partial occlusion causing contour to jump
   - Solution: Check mirror detection is stable

3. **Lighting changes:**
   - Shadows or reflections causing false detections
   - Solution: Adjust HSV thresholds

4. **Ball partially obscured:**
   - Dribbler or robot body blocking ball
   - Close zone detection vs normal detection switching
   - Solution: Check in_close_zone flag in logs

## Verification Commands

### 1. Check Angle Consistency:
```bash
# Run visualization and scylla simultaneously
# Compare displayed angle to logged USING_ANGLE
# They should always match for the same frame_id
```

### 2. Monitor Angle Stability:
```bash
# With stationary ball and robot:
grep "USING_ANGLE" logs.txt | tail -20

# Angle should be very stable (±1° max)
```

### 3. Track Angle During Movement:
```bash
# While robot chases ball:
grep "USING_ANGLE" logs.txt | tail -20

# Angle should smoothly decrease towards 0° as robot aligns
```

## Configuration for Angle Stability

### In `config.json`:

**Increase minimum ball radius to reduce false detections:**
```json
"detection": {
    "min_ball_radius": 3  // Increase from 2 to 3
}
```

**Adjust HSV thresholds for better ball isolation:**
```json
"ball": {
    "lower_orange": [5, 150, 150],   // More restrictive
    "upper_orange": [15, 255, 255]
}
```

**Ensure mirror detection is stable:**
```json
"mirror": {
    "detection_interval": 900  // Detect every 30 seconds
}
```

## Expected Log Output

### Good (Stable Tracking):
```
[INFO] Chasing ball: USING_ANGLE=12.3° (ball.angle=12.3°) distance=145.2px speed=0.070 ball_pos=(342, 215) h_err=0.069 frame_id=100
[INFO] Chasing ball: USING_ANGLE=12.2° (ball.angle=12.2°) distance=144.8px speed=0.070 ball_pos=(341, 214) h_err=0.067 frame_id=101
[INFO] Chasing ball: USING_ANGLE=12.1° (ball.angle=12.1°) distance=144.3px speed=0.070 ball_pos=(340, 213) h_err=0.065 frame_id=102
```
✅ Smooth angle changes, decreasing towards 0° as robot aligns

### Bad (Jittery Detection):
```
[INFO] Chasing ball: USING_ANGLE=12.3° (ball.angle=12.3°) distance=145.2px speed=0.070 ball_pos=(342, 215) h_err=0.069 frame_id=100
[INFO] Chasing ball: USING_ANGLE=23.7° (ball.angle=23.7°) distance=178.4px speed=0.070 ball_pos=(395, 240) h_err=0.172 frame_id=101
[INFO] Chasing ball: USING_ANGLE=5.4°  (ball.angle=5.4°)  distance=98.6px  speed=0.070 ball_pos=(315, 195) h_err=0.016 frame_id=102
```
❌ Large jumps in angle and position → detection problem

## Summary

✅ **Visualization angle = Chase ball angle** (both use `ball.angle`)  
✅ **Enhanced logging shows exact angle being used**  
✅ **Angle changes are normal if ball/robot is moving**  
✅ **Use logs to verify angle stability and diagnose issues**  

The angle displayed in the visualization is **guaranteed to be identical** to the angle used in chase_ball because they both read from the same `ball.angle` field calculated by `camera.detect_ball()`. Any differences in angle between frames are due to actual ball movement, robot movement, or detection jitter, not from using different angle sources! 🎯
