# Direction Arrow Spacing - Non-Obscuring View

## Problem
The forward direction arrow was extending almost to the edge of the mirror circle (`radius - 15`), which could obscure the ball when it's in the forward area, especially in the close ball zone.

## Solution
Modified the arrow to be:
1. **Shorter** - Only 50% of radius length instead of nearly 100%
2. **Spaced from center** - Starts 10% away from center instead of at center
3. **Smaller arrow head** - Reduced from 20px to 15px

## Changes Made

### File: `hypemage/test_mirror_visualization.py`

**Before:**
```python
forward_length = radius - 15
forward_end_x = int(center_x + forward_length * math.cos(angle_rad))
forward_end_y = int(center_y + forward_length * math.sin(angle_rad))

cv2.line(viz, (center_x, center_y), (forward_end_x, forward_end_y), 
         (255, 255, 0), 4)

arrow_size = 20
```

**After:**
```python
# Make arrow shorter and spaced back from edge to not obscure ball
forward_length = int(radius * 0.5)  # Only 50% of radius, not extending to edge
forward_start_offset = int(radius * 0.1)  # Start 10% away from center

forward_start_x = int(center_x + forward_start_offset * math.cos(angle_rad))
forward_start_y = int(center_y + forward_start_offset * math.sin(angle_rad))
forward_end_x = int(center_x + forward_length * math.cos(angle_rad))
forward_end_y = int(center_y + forward_length * math.sin(angle_rad))

cv2.line(viz, (forward_start_x, forward_start_y), (forward_end_x, forward_end_y), 
         (255, 255, 0), 4)

arrow_size = 15  # Slightly smaller arrow
```

## Arrow Positioning

### Old Behavior:
```
Center ═══════════════════════════► Edge
       |<-------- radius - 15 ----->|
```
- Started at exact center
- Extended to edge minus 15px
- Could obscure ball in forward area

### New Behavior:
```
Center   ══════════►     (Clear space)
       |<- 50% ->|
       10% offset
```
- Starts 10% away from center (leaves center clear)
- Only extends 50% of radius (doesn't reach edge)
- Leaves forward area clear for ball detection visibility

## Benefits

✅ **Ball visibility** - Ball in forward area no longer hidden by arrow  
✅ **Close zone clarity** - Dribbler area detection zone visible  
✅ **Still clear direction** - Arrow remains obvious for orientation  
✅ **Less visual clutter** - Shorter arrow is cleaner on display  

## Example Measurements

For a typical mirror radius of 280px:
- **Old arrow**: Started at center, ended at 265px (95% of radius)
- **New arrow**: Starts at 28px (10%), ends at 140px (50%)
- **Clear forward space**: 140px to edge = 140px clear area for ball

This gives plenty of room for ball detection without obscuring the view! 🎯

## Color Code
The arrow remains **yellow/cyan** (255, 255, 0) to indicate forward direction.

## Testing
Run the visualization to verify:
```bash
python hypemage/test_mirror_visualization.py
```

The arrow should now:
- Be clearly visible for orientation
- Not hide balls in the forward area
- Not overlap with the close ball detection zone
- Leave the center crosshair clearly visible
