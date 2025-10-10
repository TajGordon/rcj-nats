# Quick Testing Guide for Chase Ball State

## How to Test

### 1. Start the Robot
```bash
cd c:\Users\GOR0008\gitty\rcj-nats\hypemage
python scylla.py
```

The robot will start in `SEARCH_BALL` state by default (see line 911 of scylla.py).

### 2. What to Observe

#### Initial Behavior
- Robot rotates slowly looking for the ball
- Changes rotation direction every 3 seconds

#### When Ball Detected
- Automatically transitions from `SEARCH_BALL` to `CHASE_BALL`
- Log message: "Ball found during search - transitioning to chase"

#### During Chase
Watch the terminal output for log messages like:
```
Chasing ball: angle=45.2° (raw=47.1°), speed=0.60, rotation=-0.15, 
h_err=-0.30, v_err=0.12, area=750
```

#### Key Behaviors to Verify

1. **Angle Smoothing**
   - `angle` (smoothed) should be less jittery than `raw` angle
   - Should see gradual changes rather than sudden jumps

2. **Speed Adaptation**
   - Far ball (area < 500): speed ≈ 0.8
   - Medium (500-1000): speed ≈ 0.6
   - Close (1000-2000): speed ≈ 0.4
   - Very close (> 2000): speed ≈ 0.25

3. **Rotation Control**
   - Ball on left (h_err < 0): positive rotation (turn left)
   - Ball on right (h_err > 0): negative rotation (turn right)
   - Ball centered (h_err ≈ 0): rotation ≈ 0

4. **Off-Center Behavior**
   - When |h_err| > 0.5, speed should reduce by 50%
   - Log message: "Ball far off-center (X.XX), reducing speed"

5. **State Transitions**
   - Ball close & centered → LINEUP_KICK
   - Ball lost → SEARCH_BALL

### 3. Manual State Changes (for testing)

You can modify line 911 in `scylla.py` to start in different states:

```python
# Start directly in chase mode (if ball is visible)
scylla.transition_to(State.CHASE_BALL)

# Or start in search mode (default)
scylla.transition_to(State.SEARCH_BALL)
```

### 4. Button Controls

Once running, use the physical buttons:
- **D13, D19, or D26**: Pause/Resume robot

### 5. Expected Movement Patterns

#### Scenario 1: Ball Directly Ahead
- `h_err` ≈ 0, `v_err` < 0
- `angle` ≈ 0° (straight forward)
- `rotation` ≈ 0
- Robot moves straight toward ball

#### Scenario 2: Ball to the Right
- `h_err` > 0, `v_err` < 0
- `angle` > 0° (angled right-forward)
- `rotation` < 0 (turning right)
- Robot moves forward-right while rotating right

#### Scenario 3: Ball Far to the Side
- `|h_err|` > 0.5
- Speed reduced by 50%
- Strong rotation toward ball
- Robot prioritizes turning over moving forward

#### Scenario 4: Ball Very Close
- `area` > 2000
- `speed` = 0.25 (very slow)
- Robot approaches carefully for final alignment

## Tuning Tips

### If robot turns too much (oscillates):
```python
rotation_gain = 0.5  # Try reducing to 0.3 or 0.4
```

### If robot doesn't turn enough:
```python
rotation_gain = 0.5  # Try increasing to 0.6 or 0.7
```

### If robot is too slow overall:
```python
# Increase all speed values (lines 611-618)
speed_very_close = 0.35  # was 0.25
speed_close = 0.5        # was 0.4
speed_medium = 0.7       # was 0.6
speed_far = 0.9          # was 0.8
```

### If robot is too jittery:
```python
_chase_max_history = 5  # Try increasing to 7 or 10
```

### If robot is too sluggish to respond:
```python
_chase_max_history = 5  # Try reducing to 3
```

## Troubleshooting

### Problem: Robot doesn't chase ball
**Check:**
1. Is camera process running? Look for "Camera process started"
2. Is ball being detected? Check `ball.detected` in logs
3. Is motor controller initialized? Look for "Motor controller initialized successfully"

### Problem: Robot moves in wrong direction
**Check:**
1. Camera orientation - might be mounted upside down or sideways
2. Motor polarity - motors might be reversed
3. Log values of `h_err`, `v_err`, and `angle`

### Problem: Robot spins in place
**Check:**
1. `rotation_gain` might be too high
2. Ball might be off-center in camera view
3. Check `h_err` values - should be between -1 and 1

### Problem: Ball tracking is jittery
**Check:**
1. Increase `_chase_max_history` for more smoothing
2. Check lighting - poor lighting affects ball detection
3. Verify camera focus is set correctly

## Performance Metrics

### Good Performance
- Smooth approach to ball with minimal oscillation
- Stable angle values (smoothed ≈ raw ± 5°)
- Speed adjusts appropriately as ball gets closer
- Robot keeps ball centered (h_err stays near 0)

### Needs Tuning
- Large oscillations in angle (> 20° changes frame-to-frame)
- Robot misses ball frequently
- Rotation seems too aggressive or too weak
- Speed doesn't change as ball gets closer

## Next Steps

After verifying chase ball works well:
1. Test transition to `LINEUP_KICK` state
2. Test transition to `SEARCH_BALL` when ball is lost
3. Test full game loop: Search → Chase → Lineup → Kick → repeat
4. Add field-relative movement using localization data
5. Implement obstacle avoidance
