# Manual Movement Web Control - Quick Guide

## Start the Web Interface

```bash
python hypemage/manual_movement_web.py
```

Then open in your browser: **http://localhost:8083**

## Features

### Visual Angle Display
- **Dashed green guide lines** every 45 degrees
- **Angle labels** at each guide line (0°, 45°, 90°, etc.)
- **Center crosshair** showing the robot center
- **Orange arrow** showing current movement direction

### How to Use

1. **Click anywhere** on the visualization to move in that direction
   - The robot will move at speed 0.5 in the clicked direction
   - An orange arrow shows the direction
   - Movement continues until stopped

2. **Press SPACE** to stop movement
   - Motors stop immediately
   - Robot waits for next click

3. **View real-time status** in the status bar:
   - Connection status
   - Moving/Stopped
   - Current angle
   - Current speed

### Angle Reference

```
        90° (Left)
          |
    135°  |  45°
       \  |  /
        \ | /
180° ----   ---- 0° (Forward)
        / | \
       /  |  \
    225°  |  315°
          |
       270° (Right)
```

- **0°** = Forward (straight up on screen)
- **90°** = Left
- **180°** = Backward (straight down)
- **270°** = Right

### Controls

| Action | Control |
|--------|---------|
| Move in direction | Click on visualization |
| Stop movement | Press SPACE |
| Exit program | Ctrl+C in terminal |

## Visual Indicators

- **Green dashed lines**: Angle guides (every 45°)
- **Green crosshair**: Robot center point
- **Orange arrow**: Current movement direction (only when moving)
- **Status text**: MOVING (green) or STOPPED (gray)

## Tips

1. **Click near the edge** for precise angle selection
2. **Click near center** still works, but harder to see angle
3. **Watch the orange arrow** - it shows exactly where you're going
4. **Speed is always 0.5** - no need to specify it
5. **Press SPACE anytime** to stop immediately

## Comparison with Old Version

| Feature | Old (Terminal) | New (Web) |
|---------|---------------|-----------|
| Interface | Text commands | Visual clicking |
| Display | None | Real-time visualization |
| Angle selection | Type number | Click direction |
| Speed control | Type speed | Fixed at 0.5 |
| Stop method | Type "0 0" | Press SPACE |
| Visual feedback | Text only | Angle lines + arrow |

## Troubleshooting

**Can't connect to http://localhost:8083**
- Make sure the script is running
- Check terminal for error messages
- Try refreshing the browser page

**Motors not moving**
- Check terminal for motor initialization errors
- Verify motor controller is working
- Try the old manual test: `python hypemage/manual_movement_test.py`

**Wrong direction**
- The visualization shows the direction relative to robot forward (0°)
- If robot is facing wrong way, adjust your clicks accordingly
- Orange arrow shows exactly where robot will move

**Browser shows "Disconnected"**
- The web server stopped or crashed
- Check terminal for errors
- Restart the script

## Keyboard Shortcuts

- **SPACE**: Stop movement
- **Ctrl+C** (in terminal): Emergency stop and exit

## Advanced

The visualization updates at ~30 FPS showing:
- Current angle in degrees
- Movement status
- Speed (always 0.5)
- Direction arrow (when moving)

All angle calculations use the same convention as the rest of the robot code:
- 0° = forward
- Positive angles = counterclockwise
- Negative angles = clockwise (displayed as 270° instead of -90°)
