# Camera Stream with Debug Overlays

## Overview
The `camera_stream.py` script is a standalone HTTP MJPEG server that streams camera feed with real-time detection overlays.

## Features
- **Standalone Operation**: Can run independently without the interface server
- **Real-time Detection**: Runs ball and goal detection on every frame
- **Debug Overlays**: Draws visual overlays on the stream:
  - Orange circle around detected ball with center dot and position label
  - Blue rectangle around blue goal with position label
  - Yellow rectangle around yellow goal with position label
  - Frame ID counter in top-left corner
  - Green text showing frame number

## Usage

### Running Standalone
```bash
# Run directly on the robot
python -m hypemage.scripts.camera_stream
```

### Running via Interface (Dashboard Button)
The dashboard has a "Camera" button that launches this script automatically.

## Network Configuration
- **Storm (f7.local)**: Streams on port **8765**
- **Necron (m7.local)**: Streams on port **8766**

The port is automatically detected based on hostname.

## Stream URLs
Once running, the stream is available at:
- Storm: `http://f7.local:8765/stream`
- Necron: `http://m7.local:8766/stream`

You can also visit the root URL for a simple test page:
- Storm: `http://f7.local:8765/`
- Necron: `http://m7.local:8766/`

## Architecture

### Detection Pipeline
```
Camera Frame
    ↓
Capture Frame (capture_frame)
    ↓
Run Ball Detection (detect_ball)
    ↓
Run Goal Detection (detect_goals)
    ↓
Build VisionData Object
    ↓
Add Debug Overlays (add_debug_overlays)
    ↓
Encode as JPEG
    ↓
Stream via HTTP MJPEG
```

### Performance
- Target frame rate: **30 FPS**
- JPEG quality: **85%**
- Logging every **100 frames** with detection summary

## Debug Logging
Every 100 frames, the script logs:
```
[camera_stream] Streamed 100 frames (~28 FPS) - ball@(320,240), blue_goal
```

This shows:
- Frame count
- Approximate FPS
- Active detections with ball position

## Dependencies
- `aiohttp`: HTTP server framework
- `cv2` (OpenCV): Camera capture and image processing
- `hypemage.camera`: CameraProcess, detection functions, overlay rendering
- `hypemage.config`: Robot identification

## Code Structure

### CameraStreamer Class
- `__init__()`: Initialize with robot ID detection
- `mjpeg_handler()`: Async HTTP handler that captures, detects, overlays, and streams

### Main Functions
- `get_debug_port()`: Returns 8765 or 8766 based on hostname
- `log()`: Prints with `[camera_stream]` prefix for interface capture
- `main()`: Entry point - starts camera and HTTP server

## Integration with Dashboard
The dashboard's camera widget uses an `<img>` tag that points directly to the stream:
```html
<img :src="`http://${host}:${debugPort}/stream`">
```

When the "Camera" button is clicked:
1. Dashboard sends `run_script: camera_stream` command to interface
2. Interface launches this script as a subprocess
3. Script starts streaming on the debug port
4. Dashboard's `<img>` tag automatically connects and displays the stream
5. Script output is captured and logged by interface

## Troubleshooting

### No Stream Visible
- Check that script is running: Look for interface logs showing "Camera stream starting..."
- Verify camera is accessible: Check if other apps can use the camera
- Check network: Ensure you can ping f7.local or m7.local
- Check port: Make sure nothing else is using port 8765/8766

### Poor Performance
- Reduce JPEG quality (line 79): Change from 85 to 70
- Reduce frame rate (line 99): Change from 30 FPS to 20 FPS
- Check detection speed: Ball/goal detection should be <30ms per frame

### No Detections Showing
- Check HSV thresholds in config files
- Verify lighting conditions match calibration
- Look at raw camera feed to confirm objects are visible
- Check that objects are within camera's field of view

## Future Enhancements
- Add configurable quality/FPS parameters
- Support multiple simultaneous viewers
- Add timestamp overlay
- Include detection confidence scores
- Add field line detection overlay
