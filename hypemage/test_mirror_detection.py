#!/usr/bin/env python3
"""Mirror detection test over websocket"""

import cv2
import numpy as np
import sys
import time
import asyncio
import json
import base64
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


def draw_mirror_info(frame, camera_obj):
    """Draw mirror detection info on frame"""
    display = frame.copy()
    
    if camera_obj.mirror_circle is not None:
        center_x, center_y, radius = camera_obj.mirror_circle
        cv2.circle(display, (center_x, center_y), radius, (0, 255, 0), 2)
        cv2.circle(display, (center_x, center_y), 5, (0, 255, 0), -1)
        cv2.line(display, (center_x - 20, center_y), (center_x + 20, center_y), (0, 255, 0), 1)
        cv2.line(display, (center_x, center_y - 20), (center_x, center_y + 20), (0, 255, 0), 1)
        
        info_text = f"Mirror: ({center_x}, {center_y}) r={radius}"
        cv2.putText(display, info_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    else:
        cv2.putText(display, "Mirror: NOT DETECTED", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    frame_center_x = camera_obj.frame_center_x
    frame_center_y = camera_obj.frame_center_y
    cv2.circle(display, (frame_center_x, frame_center_y), 3, (255, 0, 0), -1)
    
    return display


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
    finally:
        active_connections.discard(ws)
    
    return ws


async def index_handler(request):
    """Serve the HTML page"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Mirror Detection Test</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #1a1a1a;
            color: #fff;
        }
        .container {
            max-width: 1800px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #4CAF50;
        }
        .controls {
            text-align: center;
            margin: 20px 0;
        }
        button {
            padding: 10px 20px;
            margin: 5px;
            font-size: 16px;
            cursor: pointer;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
        }
        button:hover {
            background: #45a049;
        }
        .frames {
            display: flex;
            gap: 20px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .frame-container {
            text-align: center;
        }
        canvas {
            border: 2px solid #4CAF50;
            max-width: 100%;
            height: auto;
        }
        .info {
            background: #2a2a2a;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            font-family: monospace;
        }
        .status {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 3px;
            margin-left: 10px;
        }
        .status.connected {
            background: #4CAF50;
        }
        .status.disconnected {
            background: #f44336;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Mirror Detection Test</h1>
        
        <div class="info">
            <strong>Status:</strong> 
            <span class="status disconnected" id="status">Disconnected</span>
            <br>
            <strong>FPS:</strong> <span id="fps">0</span>
            <br>
            <strong>Mirror:</strong> <span id="mirror-info">N/A</span>
        </div>
        
        <div class="controls">
            <button onclick="redetectMirror()">Re-detect Mirror</button>
            <button onclick="toggleView()">Toggle View</button>
        </div>
        
        <div class="frames">
            <div class="frame-container">
                <h3>Original + Detection</h3>
                <canvas id="original"></canvas>
            </div>
            <div class="frame-container">
                <h3>Masked (Mirror Only)</h3>
                <canvas id="masked"></canvas>
            </div>
        </div>
    </div>

    <script>
        let ws;
        let frameCount = 0;
        let lastTime = Date.now();
        let showView = true;

        function connect() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            ws.onopen = () => {
                document.getElementById('status').textContent = 'Connected';
                document.getElementById('status').className = 'status connected';
            };
            
            ws.onclose = () => {
                document.getElementById('status').textContent = 'Disconnected';
                document.getElementById('status').className = 'status disconnected';
                setTimeout(connect, 1000);
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.frame_original && data.frame_masked) {
                    if (showView) {
                        drawImage('original', data.frame_original);
                        drawImage('masked', data.frame_masked);
                    }
                    
                    if (data.mirror_info) {
                        document.getElementById('mirror-info').textContent = data.mirror_info;
                    } else {
                        document.getElementById('mirror-info').textContent = 'NOT DETECTED';
                    }
                    
                    // Update FPS
                    frameCount++;
                    const now = Date.now();
                    if (now - lastTime > 1000) {
                        const fps = Math.round(frameCount * 1000 / (now - lastTime));
                        document.getElementById('fps').textContent = fps;
                        frameCount = 0;
                        lastTime = now;
                    }
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

        function toggleView() {
            showView = !showView;
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
            
            camera.update_mirror_mask(frame)
            
            # Create original with overlay
            original = draw_mirror_info(frame, camera)
            
            # Create masked version
            masked = camera.apply_mirror_mask(frame)
            
            # Encode frames as JPEG
            _, orig_jpg = cv2.imencode('.jpg', original, [cv2.IMWRITE_JPEG_QUALITY, 80])
            _, mask_jpg = cv2.imencode('.jpg', masked, [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            # Convert to base64
            orig_b64 = base64.b64encode(orig_jpg).decode('utf-8')
            mask_b64 = base64.b64encode(mask_jpg).decode('utf-8')
            
            # Prepare mirror info
            mirror_info = None
            if camera.mirror_circle:
                cx, cy, r = camera.mirror_circle
                mirror_info = f"({cx}, {cy}) radius={r}"
            
            data = {
                'frame_original': orig_b64,
                'frame_masked': mask_b64,
                'mirror_info': mirror_info
            }
            
            # Broadcast to all connections
            for ws in list(active_connections):
                try:
                    await ws.send_json(data)
                except:
                    active_connections.discard(ws)
            
            await asyncio.sleep(0.033)  # ~30 fps
            
        except Exception as e:
            logger.error(f"Error in frame broadcaster: {e}")
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
    print("Mirror Detection Test - WebSocket Server")
    print("="*60)
    
    robot_id = get_robot_id()
    config = load_config(robot_id)
    
    print(f"Robot ID: {robot_id}")
    print(f"Mirror detection enabled: {config.get('mirror', {}).get('enable', True)}")
    
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
    
    print("\nServer starting on http://0.0.0.0:8080")
    print("Open in browser to view mirror detection")
    
    try:
        web.run_app(app, host='0.0.0.0', port=8080)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        camera.stop()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
