# Close Ball Zone Detection (Dribbler Area)

## Overview
Added an extra-sensitive detection zone for when the ball is right in front of the robot, in or near the dribbler. This zone detects the ball even when it's partially obscured.

## Problem Solved
When the ball is being dribbled or is very close to the robot, it can be partially obscured by the dribbler mechanism, making it difficult to detect with normal detection. The close ball zone provides a dedicated, highly sensitive detection area specifically for this scenario.

## Implementation

### 1. Configuration (`config.json`)

Added new configuration section under `detection.close_ball_zone`:

```json
"detection": {
  "proximity_threshold": 5000,
  "angle_tolerance": 15,
  "goal_center_tolerance": 0.15,
  "close_ball_zone": {
    "_comment": "Extra sensitive zone for detecting ball when it's in/near dribbler",
    "enable": true,
    "center_x_offset": 0,
    "_comment_center_x_offset": "Horizontal offset from mirror center (pixels, positive=right)",
    "center_y_offset": -80,
    "_comment_center_y_offset": "Vertical offset from mirror center (pixels, negative=up/forward)",
    "width": 120,
    "_comment_width": "Width of detection zone (pixels)",
    "height": 80,
    "_comment_height": "Height of detection zone (pixels)",
    "min_ball_radius": 1,
    "_comment_min_ball_radius": "Minimum ball radius in pixels (very sensitive, even 1px)",
    "max_ball_area": 10000,
    "_comment_max_ball_area": "Maximum ball area to avoid false positives"
  }
}
```

### 2. Camera Process Updates (`camera.py`)

#### Added to `BallDetectionResult`:
```python
in_close_zone: bool = False  # True if detected in the extra-sensitive close ball zone
```

#### New Detection Method:
```python
def _detect_ball_in_close_zone(self, frame) -> BallDetectionResult
```
- Extracts small region in front of robot (dribbler area)
- Uses same HSV color filtering as normal detection
- **Extra permissive thresholds**:
  - Minimum radius: 1px (vs 2px normal)
  - Checks zone-specific area limits
- Returns result with `in_close_zone=True`

#### Updated `detect_ball()`:
- **Checks close zone FIRST** before normal detection
- If ball found in close zone, returns immediately
- Otherwise, falls back to normal full-frame detection
- Priority: Close zone > Normal detection

#### Helper Method:
```python
def get_close_zone_bounds(self) -> Tuple[int, int, int, int]
```
Returns (x1, y1, x2, y2) for visualization

### 3. Visualization Updates (`test_mirror_visualization.py`)

#### Visual Indicators:
1. **Close Zone Rectangle**:
   - **Purple** (128, 0, 128) when zone is empty
   - **Magenta** (255, 0, 255) when ball detected inside
   - Corner markers for better visibility

2. **Ball Color Coding**:
   - **Orange** (0, 165, 255) - Normal detection
   - **Magenta** (255, 0, 255) - Detected in close zone

3. **HTML Display**:
   - Shows `🎯 IN DRIBBLER ZONE` badge when `in_close_zone=True`
   - Badge displayed in magenta color

#### Legend Updated:
- Magenta Rectangle - Close ball zone (dribbler area, extra sensitive)
- Magenta Ball - Ball detected in close zone

### 4. Data Structure

The `in_close_zone` flag is included in all data transmissions:

```javascript
{
  'ball': {
    'distance': float,
    'angle': float,
    'in_close_zone': bool,  // NEW FLAG
    // ... other fields
  }
}
```

## Configuration Parameters

### Position Parameters

**`center_x_offset`** (default: 0)
- Horizontal offset from mirror center
- Positive = right, negative = left
- Use to align zone with dribbler position

**`center_y_offset`** (default: -80)
- Vertical offset from mirror center  
- **Negative = up/forward** (toward front of robot)
- Default -80 places zone 80px above mirror center

### Size Parameters

**`width`** (default: 120)
- Width of detection rectangle in pixels
- Should cover dribbler width + margin

**`height`** (default: 80)
- Height of detection rectangle in pixels
- Should cover dribbler height + margin

### Sensitivity Parameters

**`min_ball_radius`** (default: 1)
- Minimum ball radius to detect (in pixels)
- **Very sensitive**: Even 1px radius detected
- Normal detection uses 2px minimum

**`max_ball_area`** (default: 10000)
- Maximum area to prevent false positives
- Prevents detecting very large orange objects

**`enable`** (default: true)
- Enable/disable close zone detection
- Set to false to use only normal detection

## Usage Example

### Adjusting Zone Position
```json
{
  "detection": {
    "close_ball_zone": {
      "center_x_offset": 0,      // Centered horizontally
      "center_y_offset": -100,   // 100px in front of robot
      "width": 150,              // Wider zone
      "height": 100              // Taller zone
    }
  }
}
```

### Making More/Less Sensitive
```json
{
  "detection": {
    "close_ball_zone": {
      "min_ball_radius": 1,      // Detect tiny fragments (very sensitive)
      "max_ball_area": 15000     // Allow larger objects
    }
  }
}
```

### Using in Code
```python
ball_result = camera.detect_ball(frame)

if ball_result.detected:
    if ball_result.in_close_zone:
        logger.info("Ball in dribbler! Ready to kick")
        # Ball is right in front of robot
    else:
        logger.info("Ball detected, moving to capture")
        # Ball visible but not in dribbler yet
```

## Detection Priority

1. **Close zone detection** (checked first)
   - Small focused area
   - Extra sensitive thresholds
   - **NO MIRROR MASK** - Searches raw frame in rectangle
   - Works even if zone extends outside mirror circle
   - Faster processing (smaller region)

2. **Normal detection** (fallback)
   - Full mirror frame
   - **Mirror mask applied** - Only searches inside mirror circle
   - Standard thresholds
   - Used if close zone finds nothing

## Important: No Mirror Mask in Close Zone

The close zone detection intentionally **does NOT apply the mirror mask**. This means:

✅ **Zone can extend outside mirror** - Works even if dribbler area is outside mirror circle  
✅ **Searches full rectangle** - No masking interference  
✅ **More reliable** - Not affected by mirror detection accuracy  
✅ **Dribbler-specific** - Designed for the specific area where ball is captured  

This is different from normal detection which only searches inside the detected mirror circle.

## Visual Feedback

### In Visualization:
- **Zone appears as rectangle** in front of forward arrow
- **Purple** = Zone active, no ball detected
- **Magenta** = Ball detected in zone!
- **Ball circle matches zone color** when detected inside

### In HTML Data Panel:
```
⚽ Ball:
✅ Detected
🎯 IN DRIBBLER ZONE    ← Magenta badge
📏 Distance: 85.3px
🧭 Angle: 2.1°
...
```

## Tuning Guide

### Zone Too Small (Missing Ball):
- Increase `width` and `height`
- Adjust `center_y_offset` (move zone forward/back)

### Too Many False Positives:
- Decrease `max_ball_area`
- Increase `min_ball_radius` to 2 or 3

### Zone Not Aligned with Dribbler:
- Adjust `center_x_offset` (left/right)
- Adjust `center_y_offset` (forward/back)
- Use visualization to see zone position

### Need More Sensitivity:
- Set `min_ball_radius` to 1
- Increase `max_ball_area`

### Need Less Sensitivity:
- Set `min_ball_radius` to 2 or 3
- Decrease `max_ball_area`

## Benefits

✅ **Detects obscured ball**: Works even when dribbler partially blocks view  
✅ **Faster processing**: Small region = faster detection  
✅ **Priority detection**: Checked before normal detection  
✅ **Same metrics**: Returns distance, angle, all standard fields  
✅ **Visual feedback**: Clear indication in visualization  
✅ **Configurable**: Easy to adjust position and sensitivity  
✅ **Flag available**: `in_close_zone` flag for behavior control  

## Files Modified

1. **`hypemage/config.json`**
   - Added `detection.close_ball_zone` configuration section
   - Default values provided

2. **`hypemage/camera.py`**
   - Added `in_close_zone` field to `BallDetectionResult`
   - Added close zone configuration loading in `__init__`
   - Added `_detect_ball_in_close_zone()` method
   - Modified `detect_ball()` to check close zone first
   - Added `get_close_zone_bounds()` helper method

3. **`hypemage/test_mirror_visualization.py`**
   - Added close zone rectangle visualization
   - Color-coded ball based on detection zone (orange vs magenta)
   - Added `in_close_zone` to data transmission
   - Added dribbler zone badge to HTML display
   - Updated legend with close zone indicators

## Testing

Run the visualization to see and configure the close zone:

```bash
python hypemage/test_mirror_visualization.py
```

Open browser to `http://localhost:8082`

You should see:
- Purple/magenta rectangle showing the close zone
- Ball turns magenta when detected in zone
- "IN DRIBBLER ZONE" badge appears in data panel
- Zone position can be configured in real-time by editing config.json
