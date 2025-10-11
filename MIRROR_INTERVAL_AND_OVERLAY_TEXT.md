# Mirror Detection Interval & Text Overlay Updates

## Changes Made

### 1. Mirror Detection Interval - 30 Seconds

**File: `hypemage/config.json`**

Updated mirror redetection interval from 15 seconds to 30 seconds:

```json
"mirror": {
  "detection_interval": 900,
  "_comment_detection_interval": "Detect mirror circle every N frames (900 frames = ~30 seconds at 30fps)"
}
```

**Previous:** 450 frames (~15 seconds at 30fps)  
**Updated:** 900 frames (~30 seconds at 30fps)

This reduces CPU usage by detecting the mirror circle less frequently. The mirror position is typically stable, so checking every 30 seconds is sufficient.

### 2. Text Overlay on Images

**File: `hypemage/test_mirror_visualization.py`**

Added HTML/CSS text overlays positioned on top of the canvas images instead of using OpenCV's `cv2.putText()`.

#### Changes:

**A. CSS Additions:**
```css
.canvas-container {
    position: relative;
    display: inline-block;
}

.overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    font-family: 'Courier New', monospace;
    font-weight: bold;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.9);
}

.overlay-text {
    position: absolute;
    color: #00ff88;
    font-size: 14px;
    white-space: nowrap;
}

.overlay-text.ball {
    color: #ffa500;
}

.overlay-text.ball.in-close-zone {
    color: #ff00ff;
}

.overlay-text.mirror {
    color: #00ff88;
}

.overlay-text.heading {
    color: #ffff00;
}
```

**B. HTML Structure Updated:**
```html
<div class="view-box">
    <h2>🔍 Full Frame with Mirror Mask & Overlays</h2>
    <div class="canvas-container">
        <canvas id="squareCanvas"></canvas>
        <div class="overlay" id="squareOverlay"></div>
    </div>
</div>
```

**C. JavaScript Function Added:**
```javascript
function updateOverlays(data) {
    // Clear previous overlays
    document.getElementById('squareOverlay').innerHTML = '';
    
    // Get canvas dimensions
    const canvas = document.getElementById('squareCanvas');
    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;
    
    const overlay = document.getElementById('squareOverlay');
    
    // Mirror info overlay (top left)
    if (data.mirror_detected && data.mirror) {
        const m = data.mirror;
        const mirrorText = document.createElement('div');
        mirrorText.className = 'overlay-text mirror';
        mirrorText.style.top = '10px';
        mirrorText.style.left = '10px';
        mirrorText.innerHTML = `Mirror: (${m.center_x}, ${m.center_y}) R=${m.radius}px<br>Heading: ${m.heading}°`;
        overlay.appendChild(mirrorText);
    }
    
    // Ball info overlay (positioned near ball)
    if (data.ball_detected && data.ball) {
        const b = data.ball;
        
        // Transform coordinates for rotated/flipped image
        const displayX = canvasWidth - b.center_x;
        const displayY = canvasHeight - b.center_y;
        
        const ballText = document.createElement('div');
        ballText.className = b.in_close_zone ? 'overlay-text ball in-close-zone' : 'overlay-text ball';
        ballText.style.left = (displayX + b.radius + 10) + 'px';
        ballText.style.top = (displayY - b.radius - 10) + 'px';
        
        const zoneLabel = b.in_close_zone ? '🎯 CLOSE ZONE<br>' : '';
        ballText.innerHTML = 
            zoneLabel +
            `Ball: ${b.angle.toFixed(1)}°<br>` +
            `Dist: ${b.distance.toFixed(0)}px`;
        overlay.appendChild(ballText);
    }
}
```

**D. Called After Data Update:**
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    // ... existing data panel updates ...
    
    // Update overlay text on images
    updateOverlays(data);
};
```

## Benefits

### Mirror Detection Interval:
✅ **Reduced CPU usage** - Mirror detection runs half as often  
✅ **Still responsive** - 30 seconds is frequent enough for stable operation  
✅ **Configurable** - Easy to adjust in config.json if needed  

### Text Overlays:
✅ **Always readable** - Text stays upright regardless of image rotation  
✅ **Positioned correctly** - Text appears near relevant objects  
✅ **Color-coded** - Different colors for different object types  
✅ **Clean design** - Text shadow for better visibility  
✅ **No image manipulation** - Text rendered by browser, not OpenCV  
✅ **Dynamically positioned** - Text follows ball/mirror positions  

## Text Overlay Features

### Mirror Info (Top Left, Green):
- Position: (x, y)
- Radius in pixels
- Heading angle

### Ball Info (Near Ball, Orange/Magenta):
- **Orange** for normal detection
- **Magenta** for close zone detection
- Shows "🎯 CLOSE ZONE" badge if in dribbler area
- Angle from forward direction
- Distance from mirror center

### Coordinate Transformation:
Since images are rotated 180° and flipped horizontally, the overlay function transforms coordinates:
```javascript
const displayX = canvasWidth - b.center_x;
const displayY = canvasHeight - b.center_y;
```

This ensures text appears in the correct position on the transformed image.

## Styling

Text overlays feature:
- **Monospace font** ('Courier New') for technical look
- **Bold weight** for better visibility
- **Text shadow** (2px 2px 4px black) for contrast against any background
- **Pointer-events: none** so overlays don't interfere with mouse events
- **Absolute positioning** for precise placement

## Usage

The overlays update automatically with every frame. No additional configuration needed.

To adjust appearance, modify the CSS in the `<style>` section:
- Font size: `.overlay-text { font-size: 14px; }`
- Colors: `.overlay-text.ball { color: #ffa500; }`
- Shadow: `text-shadow: 2px 2px 4px rgba(0,0,0,0.9);`

## Files Modified

1. **`hypemage/config.json`**
   - Changed `detection_interval` from 450 to 900
   - Updated comment to reflect 30 seconds

2. **`hypemage/test_mirror_visualization.py`**
   - Added CSS for canvas container and overlays
   - Updated HTML to wrap canvas in container with overlay div
   - Added `updateOverlays()` JavaScript function
   - Integrated overlay updates into WebSocket message handler
   - Coordinate transformation for rotated/flipped images

## Testing

Run the visualization:
```bash
python hypemage/test_mirror_visualization.py
```

Open browser to `http://localhost:8082`

You should see:
- Text overlays on the images (not in the data panel)
- Mirror info in top-left (green)
- Ball info near ball position (orange/magenta)
- Text stays upright and readable
- Mirror redetects every 30 seconds instead of 15
