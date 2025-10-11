# Chase Ball Logic Fix

## Problem

The robot was **not moving towards the ball** during the CHASE_BALL state. It was only moving forward (angle=0) while trying to turn, which meant:
- If ball was to the left/right, robot would just spin in place
- Robot wouldn't actively approach the ball
- Ball chasing was ineffective

## Root Cause

The old implementation used:
```python
self.motor_controller.move_robot_relative(
    angle=0,  # Always forward - WRONG!
    speed=forward_speed,
    rotation=rotation  # Just turning
)
```

This meant the robot **always moved straight forward** and only added rotation to steer. This is like trying to drive a car by only using the steering wheel while keeping the throttle constant - you'll just go in circles!

## Solution

Changed to **calculate the angle to the ball** and **move in that direction**:

```python
# Calculate angle to ball from its horizontal position in frame
ball_angle_from_center = ball.horizontal_error * 90.0  # Maps [-1,+1] to [-90°,+90°]

# Move towards that angle
self.motor_controller.move_robot_relative(
    angle=ball_angle_from_center,  # Move TOWARDS the ball
    speed=speed,
    rotation=rotation
)
```

## How It Works Now

### 1. **Angle Calculation**
- `horizontal_error` ranges from -1 (far left) to +1 (far right)
- Multiply by 90° to get angle: 
  - Ball at far left (-1) → angle = -90° (move left)
  - Ball centered (0) → angle = 0° (move forward)
  - Ball at far right (+1) → angle = +90° (move right)

### 2. **Adaptive Speed**
```python
alignment_factor = 1.0 - abs(ball.horizontal_error)
speed = base_speed * (0.3 + 0.7 * alignment_factor)
```
- When ball is centered: alignment_factor = 1.0 → speed = 100% of base
- When ball is at edge: alignment_factor = 0.0 → speed = 30% of base
- This allows robot to slow down when turning sharply

### 3. **Rotation Component**
```python
rotation = -ball.horizontal_error * rotation_gain
```
- Still adds rotation to help align with ball
- Negative because: ball on right (+) → turn right (negative rotation)
- Works in conjunction with directional movement

## Benefits

✅ **Active pursuit**: Robot moves directly towards ball, not just forward  
✅ **Better tracking**: Follows ball even when it's off to the side  
✅ **Smoother motion**: Combines translation and rotation naturally  
✅ **Speed adaptation**: Slows down when making sharp turns  
✅ **Better logging**: Shows actual angle and ball position  

## Testing

To verify the fix works:

1. **Place ball to the left of robot**
   - Expected: Robot should move diagonally left-forward (angle ≈ -45° to -90°)
   - Old behavior: Would move forward and turn left

2. **Place ball to the right of robot**
   - Expected: Robot should move diagonally right-forward (angle ≈ +45° to +90°)
   - Old behavior: Would move forward and turn right

3. **Place ball directly ahead**
   - Expected: Robot should move straight forward (angle ≈ 0°)
   - Old behavior: Same (this case worked before)

4. **Move ball around**
   - Expected: Robot should continuously track and approach ball
   - Old behavior: Would struggle to follow ball movements

## Log Output

The new logging shows:
```
Chasing ball: angle=-45.0°, speed=0.035, rotation=0.020, h_err=-0.50, ball_pos=(200, 300)
```

Where:
- `angle`: Direction robot is moving towards (-90° to +90°)
- `speed`: Current movement speed
- `rotation`: Rotation component
- `h_err`: Horizontal error from camera (-1 to +1)
- `ball_pos`: Ball center in camera frame

## Parameters

Current tuning:
- `base_speed = 0.05` - Base movement speed
- `rotation_gain = 0.04` - How much to rotate based on ball position
- `max_rotation = 0.08` - Maximum rotation speed
- Speed range: 30%-100% of base (0.015 - 0.05)

Adjust these if:
- Robot too slow → Increase `base_speed`
- Robot wobbles too much → Decrease `rotation_gain`
- Robot turns too slowly → Increase `max_rotation`

## Related Files

- `hypemage/scylla.py` - Main FSM with chase_ball state (lines ~850-920)
- `hypemage/motor_control.py` - Motor control with move_robot_relative()
- `hypemage/camera.py` - Ball detection with horizontal_error

---

**Status**: ✅ Fixed and ready for testing
**Date**: October 11, 2025
