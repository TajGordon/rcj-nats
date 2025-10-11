"""
Manual Movement Test - Web Visualization

Interactive web interface to test motor movement with visual angle display.
Click on the visualization to set direction, robot moves until space is pressed.
Speed is fixed at 0.5 for all movements.

Usage:
    python hypemage/manual_movement_web.py
    
    Then open: http://localhost:8083
    Click anywhere to move in that direction
    Press SPACE to stop
"""

import sys
import asyncio
import signal
import base64
import io
from threading import Thread, Event
from aiohttp import web
import numpy as np
import cv2

from hypemage.motor_control import MotorController
from hypemage.config import load_config
from hypemage.logger import get_logger

logger = get_logger(__name__)

# Global state
motor_controller = None
active_connections = set()
current_angle = 0
current_speed = 0.0
is_moving = False
stop_event = Event()

# Constants
FIXED_SPEED = 0.5
VIZ_SIZE = 640


def create_visualization(angle, speed, is_moving):
    """Create a visualization canvas showing the movement direction"""
    # Create black canvas
    viz = np.zeros((VIZ_SIZE, VIZ_SIZE, 3), dtype=np.uint8)
    
    center_x = VIZ_SIZE // 2
    center_y = VIZ_SIZE // 2
    radius = VIZ_SIZE // 2 - 50
    
    # Draw angle guide lines every 45 degrees
    angles_deg = [0, 45, 90, 135, 180, 225, 270, 315]
    angle_labels = ['0°\nForward', '45°', '90°\nLeft', '135°', '180°\nBack', '225°', '270°\nRight', '315°']
    
    for angle_deg, label in zip(angles_deg, angle_labels):
        # Convert to radians (0° = up/forward)
        radians = np.radians(angle_deg - 90)
        
        # Calculate line endpoints
        start_x = int(center_x + np.cos(radians) * 30)
        start_y = int(center_y + np.sin(radians) * 30)
        end_x = int(center_x + np.cos(radians) * radius)
        end_y = int(center_y + np.sin(radians) * radius)
        
        # Draw dashed line
        color = (0, 255, 136)  # Green
        thickness = 2
        line_type = cv2.LINE_AA
        
        # Draw dashed line manually
        num_dashes = 20
        for i in range(num_dashes):
            if i % 2 == 0:  # Only draw every other segment
                t1 = i / num_dashes
                t2 = (i + 1) / num_dashes
                x1 = int(start_x + (end_x - start_x) * t1)
                y1 = int(start_y + (end_y - start_y) * t1)
                x2 = int(start_x + (end_x - start_x) * t2)
                y2 = int(start_y + (end_y - start_y) * t2)
                cv2.line(viz, (x1, y1), (x2, y2), color, thickness, line_type)
        
        # Draw angle label
        label_x = int(center_x + np.cos(radians) * (radius + 35))
        label_y = int(center_y + np.sin(radians) * (radius + 35))
        
        # Split label by newline
        lines = label.split('\n')
        for i, line in enumerate(lines):
            text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            text_x = int(label_x - text_size[0] // 2)
            text_y = int(label_y + (i - 0.5) * 20)
            
            # Draw shadow
            cv2.putText(viz, line, (text_x + 2, text_y + 2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
            # Draw text
            cv2.putText(viz, line, (text_x, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)
    
    # Draw center circle
    cv2.circle(viz, (center_x, center_y), 15, (0, 255, 136), 2, cv2.LINE_AA)
    
    # Draw center crosshair
    cv2.line(viz, (center_x - 20, center_y), (center_x + 20, center_y), 
             (0, 255, 136), 2, cv2.LINE_AA)
    cv2.line(viz, (center_x, center_y - 20), (center_x, center_y + 20), 
             (0, 255, 136), 2, cv2.LINE_AA)
    
    # Draw current direction arrow if moving
    if is_moving and speed > 0:
        # Convert angle to radians (0° = up/forward)
        radians = np.radians(angle - 90)
        
        # Arrow properties
        arrow_length = radius * 0.8
        arrow_start_x = int(center_x + np.cos(radians) * 20)
        arrow_start_y = int(center_y + np.sin(radians) * 20)
        arrow_end_x = int(center_x + np.cos(radians) * arrow_length)
        arrow_end_y = int(center_y + np.sin(radians) * arrow_length)
        
        # Draw thick arrow
        cv2.arrowedLine(viz, (arrow_start_x, arrow_start_y), (arrow_end_x, arrow_end_y),
                       (0, 165, 255), 8, cv2.LINE_AA, tipLength=0.15)  # Orange arrow
        
        # Draw angle text at center
        angle_text = f"{angle:.0f}°"
        text_size = cv2.getTextSize(angle_text, cv2.FONT_HERSHEY_BOLD, 1.5, 3)[0]
        text_x = int(center_x - text_size[0] // 2)
        text_y = int(center_y + text_size[1] // 2)
        
        # Draw shadow
        cv2.putText(viz, angle_text, (text_x + 3, text_y + 3), 
                   cv2.FONT_HERSHEY_BOLD, 1.5, (0, 0, 0), 5, cv2.LINE_AA)
        # Draw text
        cv2.putText(viz, angle_text, (text_x, text_y), 
                   cv2.FONT_HERSHEY_BOLD, 1.5, (0, 165, 255), 3, cv2.LINE_AA)
    
    # Draw status text
    status_text = "MOVING" if is_moving else "STOPPED"
    status_color = (0, 255, 0) if is_moving else (100, 100, 100)
    cv2.putText(viz, status_text, (20, 40), 
               cv2.FONT_HERSHEY_BOLD, 1.2, status_color, 3, cv2.LINE_AA)
    
    # Draw speed text
    speed_text = f"Speed: {speed:.2f}"
    cv2.putText(viz, speed_text, (20, 80), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    
    # Draw instructions at bottom
    instructions = [
        "Click anywhere to move in that direction",
        "Press SPACE to stop movement"
    ]
    y_pos = VIZ_SIZE - 60
    for instruction in instructions:
        cv2.putText(viz, instruction, (20, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
        y_pos += 30
    
    return viz


async def websocket_handler(request):
    """Handle WebSocket connections"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    active_connections.add(ws)
    logger.info(f"Client connected. Total connections: {len(active_connections)}")
    
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = msg.json()
                
                if data['type'] == 'click':
                    # Calculate angle from click position
                    click_x = data['x']
                    click_y = data['y']
                    canvas_width = data['width']
                    canvas_height = data['height']
                    
                    # Convert to centered coordinates
                    center_x = canvas_width / 2
                    center_y = canvas_height / 2
                    dx = click_x - center_x
                    dy = click_y - center_y
                    
                    # Calculate angle (atan2 gives angle from positive x-axis)
                    # We need to rotate 90° to make 0° point up
                    angle_rad = np.arctan2(dy, dx)
                    angle_deg = np.degrees(angle_rad) + 90
                    
                    # Normalize to 0-360
                    if angle_deg < 0:
                        angle_deg += 360
                    
                    # Start movement
                    await start_movement(angle_deg)
                    
                elif data['type'] == 'stop':
                    # Stop movement
                    await stop_movement()
                    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        active_connections.discard(ws)
        logger.info(f"Client disconnected. Total connections: {len(active_connections)}")
    
    return ws


async def start_movement(angle):
    """Start moving in the specified direction"""
    global current_angle, current_speed, is_moving
    
    current_angle = angle
    current_speed = FIXED_SPEED
    is_moving = True
    
    logger.info(f"Starting movement: angle={angle:.1f}°, speed={FIXED_SPEED}")
    
    if motor_controller:
        motor_controller.move_robot_relative(angle=angle, speed=FIXED_SPEED, rotation=0.0)


async def stop_movement():
    """Stop all movement"""
    global current_speed, is_moving
    
    current_speed = 0.0
    is_moving = False
    
    logger.info("Stopping movement")
    
    if motor_controller:
        motor_controller.stop()


async def index_handler(request):
    """Serve the main HTML page"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Manual Movement Control</title>
    <style>
        body {
            margin: 0;
            padding: 20px;
            background: #1a1a1a;
            color: #ffffff;
            font-family: 'Segoe UI', Arial, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        
        h1 {
            margin: 0 0 20px 0;
            color: #00ff88;
            text-align: center;
        }
        
        .status-bar {
            background: #2a2a2a;
            padding: 15px 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            gap: 30px;
            align-items: center;
        }
        
        .status-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-label {
            color: #888;
            font-size: 14px;
        }
        
        .status-value {
            color: #00ff88;
            font-weight: bold;
            font-size: 16px;
        }
        
        .canvas-container {
            position: relative;
            display: inline-block;
            border: 3px solid #00ff88;
            border-radius: 10px;
            overflow: hidden;
            cursor: crosshair;
        }
        
        canvas {
            display: block;
            max-width: 90vw;
            max-height: 70vh;
        }
        
        .instructions {
            margin-top: 20px;
            background: #2a2a2a;
            padding: 20px;
            border-radius: 10px;
            max-width: 640px;
        }
        
        .instructions h3 {
            margin-top: 0;
            color: #00ff88;
        }
        
        .instructions ul {
            margin: 10px 0;
            padding-left: 20px;
        }
        
        .instructions li {
            margin: 8px 0;
            line-height: 1.5;
        }
        
        .key {
            display: inline-block;
            background: #444;
            padding: 2px 8px;
            border-radius: 4px;
            font-family: monospace;
            font-weight: bold;
            color: #00ff88;
        }
    </style>
</head>
<body>
    <h1>🤖 Manual Movement Control</h1>
    
    <div class="status-bar">
        <div class="status-item">
            <span class="status-label">Connection:</span>
            <span class="status-value" id="wsStatus">Connecting...</span>
        </div>
        <div class="status-item">
            <span class="status-label">Status:</span>
            <span class="status-value" id="moveStatus">STOPPED</span>
        </div>
        <div class="status-item">
            <span class="status-label">Angle:</span>
            <span class="status-value" id="angleValue">0°</span>
        </div>
        <div class="status-item">
            <span class="status-label">Speed:</span>
            <span class="status-value" id="speedValue">0.00</span>
        </div>
    </div>
    
    <div class="canvas-container">
        <canvas id="vizCanvas"></canvas>
    </div>
    
    <div class="instructions">
        <h3>Instructions:</h3>
        <ul>
            <li><strong>Click anywhere</strong> on the visualization to move in that direction</li>
            <li>Press <span class="key">SPACE</span> to stop movement</li>
            <li>Speed is fixed at <strong>0.5</strong> for all movements</li>
            <li><strong>0°</strong> = Forward (up), <strong>90°</strong> = Left, <strong>180°</strong> = Back, <strong>270°</strong> = Right</li>
        </ul>
    </div>
    
    <script>
        let ws = null;
        let currentAngle = 0;
        let currentSpeed = 0.0;
        let isMoving = false;
        
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
                
                if (data.frame) {
                    drawImage(data.frame);
                }
                
                if (data.angle !== undefined) {
                    currentAngle = data.angle;
                    document.getElementById('angleValue').textContent = `${data.angle.toFixed(1)}°`;
                }
                
                if (data.speed !== undefined) {
                    currentSpeed = data.speed;
                    document.getElementById('speedValue').textContent = data.speed.toFixed(2);
                }
                
                if (data.is_moving !== undefined) {
                    isMoving = data.is_moving;
                    const statusEl = document.getElementById('moveStatus');
                    statusEl.textContent = isMoving ? 'MOVING' : 'STOPPED';
                    statusEl.style.color = isMoving ? '#00ff00' : '#888888';
                }
            };
        }
        
        function drawImage(base64Data) {
            const canvas = document.getElementById('vizCanvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();
            img.onload = () => {
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);
            };
            img.src = 'data:image/jpeg;base64,' + base64Data;
        }
        
        // Handle canvas clicks
        document.getElementById('vizCanvas').addEventListener('click', (event) => {
            const canvas = event.target;
            const rect = canvas.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            
            // Scale to actual canvas size (not display size)
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            const actualX = x * scaleX;
            const actualY = y * scaleY;
            
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'click',
                    x: actualX,
                    y: actualY,
                    width: canvas.width,
                    height: canvas.height
                }));
            }
        });
        
        // Handle spacebar to stop
        document.addEventListener('keydown', (event) => {
            if (event.code === 'Space') {
                event.preventDefault();
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({type: 'stop'}));
                }
            }
        });
        
        connect();
    </script>
</body>
</html>
    """
    return web.Response(text=html, content_type='text/html')


async def frame_broadcaster():
    """Continuously create and broadcast visualization frames"""
    while not stop_event.is_set():
        try:
            if not active_connections:
                await asyncio.sleep(0.1)
                continue
            
            # Create visualization
            viz = create_visualization(current_angle, current_speed, is_moving)
            
            # Encode as JPEG
            _, jpg = cv2.imencode('.jpg', viz, [cv2.IMWRITE_JPEG_QUALITY, 90])
            
            # Convert to base64
            b64 = base64.b64encode(jpg).decode('utf-8')
            
            # Prepare data
            data = {
                'frame': b64,
                'angle': float(current_angle),
                'speed': float(current_speed),
                'is_moving': is_moving
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


def signal_handler(sig, frame):
    """Handle Ctrl+C by stopping motors before exit"""
    print("\n\n🛑 Ctrl+C detected - stopping motors...")
    if motor_controller:
        motor_controller.stop()
        print("✓ Motors stopped")
        motor_controller.shutdown()
        print("✓ Motor controller shut down")
    stop_event.set()
    print("Exiting...")
    sys.exit(0)


def main():
    global motor_controller
    
    print("=" * 60)
    print("Manual Movement Control - Web Interface")
    print("=" * 60)
    print("\nInitializing motor controller...")
    
    # Load config
    config = load_config()
    
    # Initialize motor controller
    try:
        motor_controller = MotorController(config=config, threaded=True)
        print("✓ Motor controller initialized\n")
    except Exception as e:
        print(f"✗ Failed to initialize motors: {e}")
        print("Cannot continue without motors")
        sys.exit(1)
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create web application
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', websocket_handler)
    
    # Register startup/cleanup handlers
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    
    print("Starting web server on http://localhost:8083")
    print("Open your browser and navigate to: http://localhost:8083")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 60)
    
    # Run web server
    try:
        web.run_app(app, host='0.0.0.0', port=8083, print=None)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        if motor_controller:
            print("\nShutting down motor controller...")
            motor_controller.shutdown()
            print("✓ Shutdown complete")


if __name__ == "__main__":
    main()
