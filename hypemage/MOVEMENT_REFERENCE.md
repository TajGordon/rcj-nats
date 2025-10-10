# Motor Movement Control - Quick Reference

## Overview

The motor controller now includes high-level movement functions for omnidirectional robot control:

- **Robot-relative movement**: Move in a direction relative to the robot's current orientation
- **Field-relative movement**: Move in an absolute direction on the field, compensating for robot heading
- **Example FSM state**: `MOVE_IN_SQUARE` demonstrates movement patterns with GPIO button control

## Movement Functions

### `move_robot_relative(angle, speed, rotation=0.0)`

Move the robot in a direction relative to its current orientation.

**Parameters:**
- `angle` (float): Direction in degrees
  - `0°` = forward
  - `90°` = right
  - `180°` = back
  - `270°` = left
- `speed` (float): Speed magnitude, range `[0.0, 1.0]`
- `rotation` (float): Rotation component, range `[-1.0, 1.0]`
  - Positive = clockwise
  - Negative = counter-clockwise

**Examples:**
```python
# Move forward at half speed
controller.move_robot_relative(0, 0.5)

# Move right at 30% speed
controller.move_robot_relative(90, 0.3)

# Move diagonal forward-right with slight rotation
controller.move_robot_relative(45, 0.5, rotation=0.2)

# Strafe left while rotating clockwise
controller.move_robot_relative(270, 0.4, rotation=0.3)
```

### `move_field_relative(angle, speed, rotation, heading)`

Move in an absolute direction on the field, automatically compensating for robot's heading.

**Parameters:**
- `angle` (float): Target direction in field coordinates
  - `0°` = towards enemy goal
  - `180°` = towards own goal
- `speed` (float): Speed magnitude, range `[0.0, 1.0]`
- `rotation` (float): Rotation component, range `[-1.0, 1.0]`
- `heading` (float): Current robot heading in degrees (from IMU or localization)

**Examples:**
```python
# Always move towards enemy goal, regardless of robot orientation
controller.move_field_relative(0, 0.5, 0, robot_heading)

# Move to the left side of the field
controller.move_field_relative(270, 0.4, 0, robot_heading)

# Move towards enemy goal while rotating to face it
controller.move_field_relative(0, 0.5, 0.2, robot_heading)
```

## Omniwheel Kinematics

The movement functions use trigonometry to calculate individual motor speeds:

```
Motor Layout (top view):
    M1 (front-left)    M2 (front-right)
            \  /
             \/
             /\
            /  \
    M3 (back-left)     M4 (back-right)

Calculations:
    vx = speed * sin(angle)  # Left/right component
    vy = speed * cos(angle)  # Forward/back component
    
    m1 = vy + vx + rotation
    m2 = vy - vx - rotation
    m3 = vy - vx + rotation
    m4 = vy + vx - rotation
    
    (Normalized to keep all speeds within [-1.0, 1.0])
```

## Example FSM State: `MOVE_IN_SQUARE`

A demonstration state that moves the robot in a square pattern:

**Features:**
- Cycles through: forward → left → back → right
- 1 second per side at 30% speed
- Press button on GPIO D26 to exit
- Transitions to `STOPPED` state on button press

**Usage:**
```python
# In your main robot code
fsm = Scylla(config)
fsm.transition_to(State.MOVE_IN_SQUARE)
fsm.run()
```

**State Implementation:**
```python
def state_move_in_square(self):
    # Automatic square pattern
    # Step 0: forward (0°)
    # Step 1: left (270°)
    # Step 2: back (180°)
    # Step 3: right (90°)
    
    # Check GPIO D26 button to exit
    if button_pressed:
        transition_to(State.STOPPED)
```

## Testing

Use the test script to try out the movement functions:

```bash
python hypemage/test_movement.py
```

**Test Options:**
1. Robot-relative movement (all directions)
2. Field-relative movement (with heading simulation)
3. Square pattern
4. Run all tests

## Integration Examples

### Using in FSM States

```python
def state_chase_ball(self):
    """Chase the ball using robot-relative movement"""
    if not self.latest_camera_data:
        return
    
    ball = self.latest_camera_data.ball
    if ball.detected:
        # Calculate angle to ball
        ball_angle = math.degrees(math.atan2(
            ball.center_x - frame_center_x,
            frame_center_y - ball.center_y
        ))
        
        # Move towards ball
        self.motor_controller.move_robot_relative(
            angle=ball_angle,
            speed=0.5,
            rotation=0.0
        )
```

### Using with Localization

```python
def state_defend_goal(self):
    """Position between ball and own goal"""
    if not self.latest_localization_data:
        return
    
    # Get robot heading from localization or IMU
    robot_heading = self.latest_localization_data.heading
    
    # Calculate field direction to defensive position
    target_angle = calculate_defensive_angle()  # Your logic here
    
    # Move in field coordinates
    self.motor_controller.move_field_relative(
        angle=target_angle,
        speed=0.4,
        rotation=0.0,
        heading=robot_heading
    )
```

## Notes

- Motor speeds are automatically normalized if the requested movement would exceed motor limits
- The watchdog safety feature still applies - motors auto-stop if no commands received for 0.5 seconds
- All movement commands are non-blocking when using threaded mode
- Use `controller.stop()` to immediately stop all motors

## GPIO Button Configuration

The `MOVE_IN_SQUARE` state uses GPIO D26 for exit control:

```python
import board
import digitalio
from buttons.button import Button

exit_button = Button(board.D26, name="Exit", pull=digitalio.Pull.UP)

if exit_button.is_pressed():
    controller.stop()
    fsm.transition_to(State.STOPPED)
```

**Button Details:**
- Pin: `board.D26`
- Pull: `digitalio.Pull.UP` (active low - button connects to ground)
- Debounce: 50ms (built into Button class)
- Method: `is_pressed()` returns `True` on press edge (not held state)
