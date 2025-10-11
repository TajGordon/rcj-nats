#!/usr/bin/env python3
"""
Enhanced Mirror Visualization Test

Shows a fixed-size square view with:
- Mirror circular mask
- Ball detection
- Line from center to ball
- Forward direction line at heading angle
- Corner masking for clean square display
"""

import cv2
import numpy as np
import sys
import time
import asyncio
import json
import base64
import math
from pathlib import Path
from aiohttp import web

sys.path.insert(0, str(Path(__file__).parent.parent))

from hypemage.camera import CameraProcess
from hypemage.config import load_config, get_robot_id
from hypemage.logger import get_logger

logger = get_logger(__name__)

# Global camera instance
camera = None
active_connections = set()

# Visualization settings
FIXED_SIZE = 600  # Fixed square size for visualization


def create_full_frame_visualization(frame, camera_obj, ball_result=None):
    """
    Create visualization on the full frame with mirror mask and overlays
    NO TEXT - all data displayed in HTML to avoid flip/rotation issues
    
    Args:
        frame: Original full camera frame
        camera_obj: CameraProcess instance
        ball_result: BallDetectionResult if available
        
    Returns:
        Full frame with visual overlays only (no text)
    """
    # Start with full frame copy
    viz = frame.copy()
    
    # Get mirror circle info
    if camera_obj.mirror_circle is None:
        # No mirror detected - just return frame
        return viz
    
    center_x, center_y, radius = camera_obj.mirror_circle
    
    # Apply mirror mask (black outside circle)
    if camera_obj.mirror_mask is not None:
        viz = cv2.bitwise_and(viz, viz, mask=camera_obj.mirror_mask)
    
    # Draw mirror circle outline
    cv2.circle(viz, (center_x, center_y), radius, (0, 255, 0), 3)
    
    # Draw center point
    cv2.circle(viz, (center_x, center_y), 8, (0, 255, 0), -1)
    cv2.circle(viz, (center_x, center_y), 5, (0, 0, 0), -1)
    
    # Draw crosshair at center
    crosshair_size = 15
    cv2.line(viz, (center_x - crosshair_size, center_y), (center_x + crosshair_size, center_y), (0, 255, 0), 2)
    cv2.line(viz, (center_x, center_y - crosshair_size), (center_x, center_y + crosshair_size), (0, 255, 0), 2)
    
    # Draw forward direction line (heading angle)
    forward_rotation = camera_obj.robot_forward_rotation
    # Convert to radians: 0° is up, clockwise positive
    angle_rad = math.radians(-90 + forward_rotation + 180)  # Match camera.py convention
    
    forward_length = radius - 15
    forward_end_x = int(center_x + forward_length * math.cos(angle_rad))
    forward_end_y = int(center_y + forward_length * math.sin(angle_rad))
    
    # Draw thick forward direction line
    cv2.line(viz, (center_x, center_y), (forward_end_x, forward_end_y), 
             (255, 255, 0), 4)  # Cyan line for forward
    
    # Draw arrow head
    arrow_size = 20
    arrow_angle1 = angle_rad + math.radians(150)
    arrow_angle2 = angle_rad - math.radians(150)
    arrow1_x = int(forward_end_x + arrow_size * math.cos(arrow_angle1))
    arrow1_y = int(forward_end_y + arrow_size * math.sin(arrow_angle1))
    arrow2_x = int(forward_end_x + arrow_size * math.cos(arrow_angle2))
    arrow2_y = int(forward_end_y + arrow_size * math.sin(arrow_angle2))
    
    cv2.line(viz, (forward_end_x, forward_end_y), (arrow1_x, arrow1_y), (255, 255, 0), 4)
    cv2.line(viz, (forward_end_x, forward_end_y), (arrow2_x, arrow2_y), (255, 255, 0), 4)
    
    # Draw ball if detected (visual only, no text)
    if ball_result and ball_result.detected:
        ball_x = ball_result.center_x
        ball_y = ball_result.center_y
        ball_radius = ball_result.radius
        
        # Draw ball circle
        cv2.circle(viz, (ball_x, ball_y), ball_radius, (0, 165, 255), 3)  # Orange
        cv2.circle(viz, (ball_x, ball_y), 3, (0, 165, 255), -1)
        
        # Draw line from center to ball
        cv2.line(viz, (center_x, center_y), (ball_x, ball_y),
                (0, 165, 255), 3)  # Orange line to ball
    
    return viz


async def websocket_handler(request):
    """Handle websocket connections"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    active_connections.add(ws)
    
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data.get('type') == 'redetect':
                    camera.mirror_circle = None
                    camera.mirror_mask = None
                    camera.mirror_detection_counter = 0
                    await ws.send_json({'status': 'redetecting'})
                elif data.get('type') == 'rotate':
                    rotation = data.get('rotation', 0)
                    camera.robot_forward_rotation = rotation
                    await ws.send_json({'status': 'rotated', 'rotation': rotation})
    finally:
        active_connections.discard(ws)
    
    return ws


async def index_handler(request):
    """Serve the HTML page"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Mirror Visualization</title>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #0a0a0a;
            color: #fff;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #00ff88;
            text-shadow: 0 0 10px rgba(0,255,136,0.5);
        }
        .view-container {
            display: flex;
            gap: 20px;
            margin: 20px 0;
            justify-content: center;
            flex-wrap: wrap;
        }
        .view-box {
            background: #1a1a1a;
            border: 2px solid #00ff88;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 0 20px rgba(0,255,136,0.2);
        }
        .view-box h2 {
            margin: 0 0 10px 0;
            color: #00ff88;
            font-size: 18px;
        }
        canvas {
            display: block;
            border-radius: 5px;
            background: #000;
            transform: rotate(180deg) scaleX(-1);
        }
        .controls {
            background: #1a1a1a;
            border: 2px solid #00ff88;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 0 20px rgba(0,255,136,0.2);
        }
        .controls h2 {
            margin: 0 0 15px 0;
            color: #00ff88;
        }
        .button-group {
            display: flex;
            gap: 10px;
            margin: 10px 0;
            flex-wrap: wrap;
        }
        button {
            background: linear-gradient(135deg, #00ff88, #00cc6a);
            border: none;
            color: #000;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            font-size: 14px;
            transition: all 0.3s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,255,136,0.4);
        }
        button:active {
            transform: translateY(0);
        }
        .status {
            background: #222;
            border-radius: 5px;
            padding: 10px;
            margin: 10px 0;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }
        .legend {
            background: #1a1a1a;
            border: 2px solid #00ff88;
            border-radius: 10px;
            padding: 15px;
            margin: 20px 0;
        }
        .legend h3 {
            color: #00ff88;
            margin: 0 0 10px 0;
        }
        .legend-item {
            display: flex;
            align-items: center;
            margin: 8px 0;
        }
        .legend-color {
            width: 30px;
            height: 20px;
            border: 1px solid #fff;
            margin-right: 10px;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Mirror Visualization Dashboard</h1>
        
        <div class="view-container">
            <div class="view-box">
                <h2>📹 Original View (No Overlay)</h2>
                <canvas id="originalCanvas"></canvas>
            </div>
            <div class="view-box">
                <h2>🔍 Full Frame with Mirror Mask & Overlays</h2>
                <canvas id="squareCanvas"></canvas>
            </div>
        </div>
        
        <div class="controls">
            <h2>⚙️ Controls</h2>
            <div class="button-group">
                <button onclick="redetectMirror()">🔄 Redetect Mirror</button>
                <button onclick="rotateForward(0)">⬆️ Forward 0°</button>
                <button onclick="rotateForward(90)">➡️ Forward 90°</button>
                <button onclick="rotateForward(180)">⬇️ Forward 180°</button>
                <button onclick="rotateForward(270)">⬅️ Forward 270°</button>
            </div>
            <div class="status" id="status">
                <div>Connection: <span id="wsStatus">Connecting...</span></div>
                <div>FPS: <span id="fps">0</span></div>
                <div>Mirror: <span id="mirrorInfo">Detecting...</span></div>
                <div>Ball: <span id="ballInfo">Not detected</span></div>
            </div>
        </div>
        
        <div class="legend">
            <h3>📊 Legend</h3>
            <div class="legend-item">
                <div class="legend-color" style="background: #00ff00;"></div>
                <span>Green Circle - Mirror boundary</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #ffff00;"></div>
                <span>Cyan Arrow - Forward direction (heading)</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #ffa500;"></div>
                <span>Orange Circle - Detected ball</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: #ffa500;"></div>
                <span>Orange Line - Line from center to ball</span>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let frameCount = 0;
        let lastFpsUpdate = Date.now();
        
        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                document.getElementById('wsStatus').textContent = 'Connected ✓';
                document.getElementById('wsStatus').style.color = '#00ff88';
            };
            
            ws.onclose = () => {
                document.getElementById('wsStatus').textContent = 'Disconnected ✗';
                document.getElementById('wsStatus').style.color = '#ff4444';
                setTimeout(connect, 2000);
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.frame_original) {
                    drawImage('originalCanvas', data.frame_original);
                }
                
                if (data.frame_square) {
                    drawImage('squareCanvas', data.frame_square);
                }
                
                if (data.mirror_info) {
                    document.getElementById('mirrorInfo').textContent = data.mirror_info;
                }
                
                if (data.ball_info) {
                    document.getElementById('ballInfo').textContent = data.ball_info;
                }
                
                // Update FPS
                frameCount++;
                const now = Date.now();
                if (now - lastFpsUpdate >= 1000) {
                    document.getElementById('fps').textContent = frameCount;
                    frameCount = 0;
                    lastFpsUpdate = now;
                }
            };
        }
        
        function drawImage(canvasId, base64Data) {
            const canvas = document.getElementById(canvasId);
            const ctx = canvas.getContext('2d');
            const img = new Image();
            img.onload = () => {
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);
            };
            img.src = 'data:image/jpeg;base64,' + base64Data;
        }
        
        function redetectMirror() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'redetect'}));
            }
        }
        
        function rotateForward(degrees) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'rotate', rotation: degrees}));
            }
        }
        
        connect();
    </script>
</body>
</html>
    """
    return web.Response(text=html, content_type='text/html')


async def frame_broadcaster():
    """Continuously capture and broadcast frames"""
    global camera
    
    while True:
        try:
            if not active_connections:
                await asyncio.sleep(0.1)
                continue
            
            frame = camera.capture_frame()
            if frame is None:
                await asyncio.sleep(0.01)
                continue
            
            # Update mirror mask
            camera.update_mirror_mask(frame)
            
            # Detect ball
            ball_result = camera.detect_ball(frame)
            
            # Create original view with basic overlay
            original = frame.copy()
            if camera.mirror_circle:
                cx, cy, r = camera.mirror_circle
                cv2.circle(original, (cx, cy), r, (0, 255, 0), 2)
                cv2.circle(original, (cx, cy), 3, (0, 255, 0), -1)
            
            # Create full frame visualization with all overlays
            full_viz = create_full_frame_visualization(frame, camera, ball_result)
            
            # Encode frames as JPEG
            _, orig_jpg = cv2.imencode('.jpg', original, [cv2.IMWRITE_JPEG_QUALITY, 85])
            _, viz_jpg = cv2.imencode('.jpg', full_viz, [cv2.IMWRITE_JPEG_QUALITY, 90])
            
            # Convert to base64
            orig_b64 = base64.b64encode(orig_jpg).decode('utf-8')
            viz_b64 = base64.b64encode(viz_jpg).decode('utf-8')
            
            # Prepare info strings
            mirror_info = "Not detected"
            if camera.mirror_circle:
                cx, cy, r = camera.mirror_circle
                mirror_info = f"Center: ({cx}, {cy}), Radius: {r}px, Heading: {camera.robot_forward_rotation}°"
            
            ball_info = "Not detected"
            if ball_result.detected:
                ball_info = f"Position: ({ball_result.center_x}, {ball_result.center_y}), Radius: {ball_result.radius:.0f}px, H-Error: {ball_result.horizontal_error:.2f}"
            
            data = {
                'frame_original': orig_b64,
                'frame_square': viz_b64,
                'mirror_info': mirror_info,
                'ball_info': ball_info
            }
            
            # Broadcast to all connections
            for ws in list(active_connections):
                try:
                    await ws.send_json(data)
                except:
                    active_connections.discard(ws)
            
            await asyncio.sleep(0.033)  # ~30 fps
            
        except Exception as e:
            logger.error(f"Error in frame broadcaster: {e}", exc_info=True)
            await asyncio.sleep(0.1)


async def start_background_tasks(app):
    """Start background tasks"""
    app['frame_broadcaster'] = asyncio.create_task(frame_broadcaster())


async def cleanup_background_tasks(app):
    """Cleanup background tasks"""
    app['frame_broadcaster'].cancel()
    await app['frame_broadcaster']


def main():
    global camera
    
    print("="*60)
    print("Enhanced Mirror Visualization - WebSocket Server")
    print("="*60)
    
    robot_id = get_robot_id()
    config = load_config(robot_id)
    
    print(f"Robot ID: {robot_id}")
    print(f"Visualization size: {FIXED_SIZE}x{FIXED_SIZE} pixels")
    print(f"Mirror detection: {config.get('mirror', {}).get('enable', True)}")
    
    try:
        camera = CameraProcess(config)
        print("✓ Camera initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize camera: {e}")
        return 1
    
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', websocket_handler)
    
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    
    print("\nServer starting on http://0.0.0.0:8082")
    print("Open in browser to view mirror visualization")
    print("\nFeatures:")
    print("  - Fixed-size square view (600x600)")
    print("  - Circular mirror mask")
    print("  - Ball detection with angle/distance")
    print("  - Center-to-ball line")
    print("  - Forward direction indicator")
    print("  - Corner masking for clean display")
    
    try:
        web.run_app(app, host='0.0.0.0', port=8082)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        camera.stop()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
