# Mirror Visualization Tool

## Overview

Enhanced visualization tool for testing the omnidirectional mirror camera system with ball detection and directional indicators.

## Features

### 🎯 Fixed-Size Square View (600x600px)
- Clean, centered view of the mirror circle
- Automatically crops and scales to fit
- Corner masking for aesthetic square display

### 🔍 Visual Elements

1. **Green Circle** - Mirror boundary detection
2. **Cyan Arrow** - Forward direction (robot heading)
3. **Orange Circle** - Detected ball
4. **Orange Line** - Line from mirror center to ball
5. **Angle/Distance Info** - Ball position metrics

### 📊 Real-time Information
- Mirror center and radius
- Robot heading angle
- Ball position and distance
- Horizontal error for ball tracking
- Live FPS counter

## Usage

### Running the Server

```bash
cd hypemage
python test_mirror_visualization.py
```

The server will start on `http://0.0.0.0:8082`

### Accessing the Visualization

**On the robot:**
```
http://localhost:8082
```

**From another computer:**
```
http://<robot-ip>:8082
# For example:
http://f7.local:8082
http://m7.local:8082
```

### Controls

- **🔄 Redetect Mirror** - Force re-detection of mirror circle
- **⬆️ Forward 0°** - Set heading to 0° (up)
- **➡️ Forward 90°** - Set heading to 90° (right)
- **⬇️ Forward 180°** - Set heading to 180° (down)
- **⬅️ Forward 270°** - Set heading to 270° (left)

## What You'll See

### Original View (Left Panel)
- Full camera frame with mirror circle overlay
- Raw camera feed for reference

### Mirror Square View (Right Panel)
- Fixed 600x600px square
- Circular mask showing only mirror area
- Center point marked
- Forward direction arrow with angle label
- Ball detection (if ball present):
  - Orange circle around ball
  - Line from center to ball
  - Angle to ball (in degrees)
  - Distance to ball (in pixels)

## Visualization Details

### Forward Direction Line
- **Cyan colored** thick arrow
- Points in the direction specified by heading angle
- 0° = up, 90° = right, 180° = down, 270° = left
- Labeled with current heading

### Ball Detection
- **Orange circle** around detected ball
- **Orange line** from mirror center to ball
- Shows:
  - Angle to ball (0-360°, where 0° is up)
  - Distance in pixels
  - Horizontal error (-1 to +1)

### Mirror Mask
- Circular area showing camera view
- Everything outside circle is masked (black)
- Corners of square are softly masked for cleaner look

## Testing Scenarios

### 1. Test Mirror Detection
1. Start the visualization
2. Wait for mirror detection (green circle should appear)
3. Click "Redetect Mirror" to force re-detection
4. Verify circle aligns with physical mirror

### 2. Test Heading Direction
1. Click different "Forward" buttons
2. Observe cyan arrow rotating
3. Verify arrow points in correct direction

### 3. Test Ball Detection
1. Place orange ball in mirror view
2. Observe orange circle around ball
3. Observe line from center to ball
4. Check angle and distance values
5. Move ball around and watch tracking

### 4. Test Ball Tracking for Chase Logic
1. Place ball at different positions:
   - Directly ahead (should show ~0°)
   - To the right (should show ~90°)
   - Behind (should show ~180°)
   - To the left (should show ~270°)
2. Note the horizontal error value
3. This error is used in chase_ball logic for steering

## Configuration

The visualization uses the same config as the main camera system:

**In `config.json`:**
```json
{
  "mirror": {
    "enable": true,
    "detection_method": "hough",
    "min_radius": 150,
    "max_radius": 400,
    "robot_forward_rotation": 0
  }
}
```

## Troubleshooting

### Mirror Not Detected
- Check lighting conditions
- Verify mirror is in frame
- Try different detection_method in config
- Adjust min_radius and max_radius
- Click "Redetect Mirror"

### Ball Not Detected
- Verify ball is orange color
- Check HSV ranges in config
- Ensure ball is within mirror circle
- Improve lighting

### Slow FPS
- Check network connection (if accessing remotely)
- Reduce JPEG quality in code
- Check CPU usage on robot

### Connection Issues
- Verify robot is on network
- Check firewall settings
- Ensure port 8082 is available
- Try accessing from localhost first

## Differences from Original test_mirror_detection.py

**Original** (`test_mirror_detection.py`):
- Port 8080
- Shows cropped mirror bounding box
- Basic visualization

**New** (`test_mirror_visualization.py`):
- Port 8082 (can run simultaneously)
- Fixed 600x600 square view
- Ball detection with angle/distance
- Center-to-ball line
- Forward direction arrow
- Corner masking
- Enhanced UI/UX

## Code Structure

### Main Functions

- `create_square_mirror_view()` - Creates the fixed-size visualization
  - Crops to mirror circle
  - Creates square canvas
  - Draws overlays (circle, arrows, lines)
  - Applies masks

- `frame_broadcaster()` - Captures and broadcasts frames
  - Runs continuously at ~30 FPS
  - Detects ball on each frame
  - Creates visualizations
  - Sends via WebSocket

### Visualization Parameters

```python
FIXED_SIZE = 600  # Square size in pixels
corner_radius = 20  # Corner masking radius
forward_length = viz_radius - 10  # Forward arrow length
arrow_size = 15  # Arrow head size
```

Adjust these in the code if needed.

## Integration with Chase Ball Logic

The visualization shows the same data used by `state_chase_ball()`:

1. **horizontal_error** - Used for steering
2. **Ball angle** - Used for directional movement
3. **Ball distance** - Used for speed adjustment

This makes it perfect for:
- Testing ball tracking
- Debugging chase logic
- Tuning parameters
- Verifying camera calibration

## Next Steps

Once visualization looks good:
1. Verify ball detection is accurate
2. Note the angles when ball is at different positions
3. Use this to tune chase_ball parameters
4. Test actual robot movement with visualization running

---

**Port**: 8082  
**Protocol**: WebSocket  
**Format**: JPEG over base64  
**Update Rate**: ~30 FPS
