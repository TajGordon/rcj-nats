# Mirror Detection Setup

## What Changed

The camera now automatically detects the circular mirror and only processes the area inside it.

### Key Updates:

1. **Mirror Detection** - Every 15 seconds (450 frames at 30fps)
   - Uses Hough Circle Transform
   - Detects circular mirror in frame
   - Falls back to default radius if not detected

2. **Automatic Masking** - Applied to all detections
   - Ball detection only looks inside mirror
   - Goal detection only looks inside mirror
   - Everything outside mirror is ignored (black)

3. **VisionData Enhanced** - Now includes:
   - `frame_center_x`, `frame_center_y` - Frame center coordinates
   - `mirror_detected` - Whether mirror was found
   - `mirror_center_x`, `mirror_center_y`, `mirror_radius` - Mirror info

## Configuration

Edit `hypemage/config.json`:

```json
"mirror": {
  "enable": true,
  "detection_method": "hough",
  "min_radius": 150,
  "max_radius": 400,
  "detection_interval": 450,  // 15 seconds at 30fps
  "fallback_radius": 250
}
```

## Testing

Run the websocket viewer:
```bash
python hypemage/test_mirror_detection.py
```

Open browser: `http://<robot-ip>:8080`

## How It Works

1. First frame: Detect mirror circle
2. Create mask (white inside circle, black outside)
3. Apply mask to all HSV frames before color detection
4. Re-detect mirror every 15 seconds to handle camera movement
5. If detection fails, use fallback circular mask
