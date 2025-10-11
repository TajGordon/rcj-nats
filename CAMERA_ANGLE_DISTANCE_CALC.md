# Camera Process: Angle & Distance Calculation

## Overview
The camera process now calculates **distance** and **angle** for detected objects (ball and goals) instead of requiring the main loop to compute them.

## Changes Made

### 1. Updated Data Classes

#### `BallDetectionResult`
Added fields:
- `distance: float` - Distance from mirror center in pixels (Pythagorean: √(dx² + dy²))
- `angle: float` - Angle from forward direction in degrees (-180° to 180°)

#### `GoalDetectionResult`
Added fields:
- `distance: float` - Distance from mirror center in pixels (Pythagorean: √(dx² + dy²))
- `angle: float` - Angle from forward direction in degrees (-180° to 180°)

### 2. Calculation Method

#### Distance Calculation
```python
dx = center_x - self.frame_center_x
dy = center_y - self.frame_center_y
distance = math.sqrt(dx * dx + dy * dy)
```

#### Angle Calculation
```python
# Note: In image coordinates, y increases downward
# Forward direction is upward in the mirror (negative y direction)
angle_rad = math.atan2(dx, -dy)  # atan2(x, -y) gives angle from upward direction
angle = math.degrees(angle_rad)  # Convert to degrees (-180 to 180)
```

**Angle Convention:**
- **0°** = Forward (up in mirror)
- **90°** = Right
- **-90°** = Left  
- **±180°** = Backward (down in mirror)

### 3. Updated Methods

**`camera.py`:**
- `detect_ball()` - Now calculates and returns `distance` and `angle`
- `_detect_single_goal()` - Now calculates and returns `distance` and `angle` for both goals

**`scylla.py`:**
- `state_chase_ball()` - Simplified to use `ball.angle` directly instead of calculating `ball_angle_from_center`
- Removed manual angle calculation: ~~`ball_angle_from_center = ball.horizontal_error * 90.0`~~
- Now uses: `angle=ball.angle` (from camera process)

### 4. Benefits

✅ **Single source of truth**: All angle/distance calculations in one place (camera.py)  
✅ **Consistent coordinate system**: All objects use the same angle calculation  
✅ **Simpler main loop**: No manual calculations needed in scylla.py  
✅ **Better accuracy**: Uses proper atan2 instead of linear approximation  
✅ **Available for goals**: Goals now have angle/distance too (not just ball)

### 5. Usage Example

```python
# Old way (main loop calculated angle):
ball_angle_from_center = ball.horizontal_error * 90.0
self.motor_controller.move_robot_relative(angle=ball_angle_from_center, ...)

# New way (camera process provides angle):
self.motor_controller.move_robot_relative(angle=ball.angle, ...)

# Also available:
logger.info(f"Ball at {ball.distance:.1f}px, angle {ball.angle:.1f}°")
logger.info(f"Blue goal at {blue_goal.distance:.1f}px, angle {blue_goal.angle:.1f}°")
```

### 6. Coordinate System

```
        -90° (Left)
             |
             |
   180° -----+----- 0° (Forward/Up)
             |
             |
        90° (Right)
```

### 7. Modified Files

1. **`hypemage/camera.py`**
   - Added `distance` and `angle` fields to `BallDetectionResult`
   - Added `distance` and `angle` fields to `GoalDetectionResult`
   - Updated `detect_ball()` to calculate distance and angle
   - Updated `_detect_single_goal()` to calculate distance and angle

2. **`hypemage/scylla.py`**
   - Updated `state_chase_ball()` to use `ball.angle` directly
   - Added `ball.distance` to logging output
   - Removed manual `ball_angle_from_center` calculation

## Notes

- The old `horizontal_error` and `vertical_error` fields are still available for legacy code
- Distance is in **pixels** (not real-world units)
- Angle calculation accounts for image coordinate system (y increases downward)
- Forward direction is **upward** in the mirror view (negative y direction)
