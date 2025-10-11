# Mirror Visualizer - Quick Reference

## Command to Start

```bash
python hypemage/test_mirror_visualization.py
```

Then open in your browser: **http://localhost:8082**

## What's New

### Angle Guide Lines
- **Lines drawn every 45 degrees** with dashed green lines
- **Labels showing the angle** at each line
- **Reference labels** for key directions:
  - **0°** = Forward (up)
  - **90°** = Left
  - **180°** = Back (down)
  - **270°** = Right

### Center Crosshair
- Green circle and crosshair marking the exact center
- All angles are measured from this center point

## How to Use

1. **Start the visualizer:**
   ```bash
   python hypemage/test_mirror_visualization.py
   ```

2. **Open browser:** http://localhost:8082

3. **Check angles:**
   - Place the ball at different positions
   - The angle guide lines show what angle the ball should be at
   - Compare the displayed angle in the info panel to the guide lines
   - The angle shown should match the closest guide line

## Angle Convention

- **0°** = Straight ahead (forward)
- **Positive angles** = Counterclockwise (left side)
- **Negative angles** = Clockwise (right side)
- **±180°** = Straight behind (backward)

Example:
- Ball at 90° → Should be on the left guide line
- Ball at -90° (or 270°) → Should be on the right guide line
- Ball at 45° → Should be between forward and left lines
- Ball at 0° → Should be on the forward (up) line

## Visual Layout

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

## Troubleshooting

**If angles don't match the guide lines:**
1. Check if camera is mounted correctly (180° offset should be applied)
2. Verify the angle displayed matches what you expect
3. Try placing ball at exactly 0° (forward) - should be straight up
4. Try placing ball at exactly 90° (left) - should be to the left

**If you can't see the guide lines:**
- Refresh the browser page
- They appear as dashed green lines on the square (right) canvas
- They're drawn on top of the video feed
