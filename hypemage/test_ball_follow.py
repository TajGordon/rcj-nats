#!/usr/bin/env python3
"""
Ball Following Test Script

Simple ball follower that:
- Gets ball angle from camera
- Moves robot toward ball
- Updates direction every 2 seconds
- Streams debug info to web interface
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
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from hypemage.camera import CameraProcess
from hypemage.motor_control import MotorController
from hypemage.config import load_config, get_robot_id
from hypemage.logger import get_logger

logger = get_logger(__name__)

# Global instances
camera = None
motor_controller = None
active_connections = set()

# Ball following state
is_paused = True  # Start paused by default
current_ball_angle = None
current_movement_angle = None
last_update_time = 0.0
UPDATE_INTERVAL = 2.0  # Update direction every 2 seconds
MOVEMENT_SPEED = 0.05

# Debug stats
stats = {
    'frames_processed': 0,
    'ball_detections': 0,
    'direction_changes': 0,
    'last_ball_seen': None,
    'uptime_start': time.time()
}


async def websocket_handler(request):
    """Handle websocket connections"""
    global is_paused
    
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    active_connections.add(ws)
    logger.info(f"Client connected. Total connections: {len(active_connections)}")
    
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                
                if data.get('type') == 'toggle_pause':
                    is_paused = not is_paused
                    state = "PAUSED" if is_paused else "RUNNING"
                    logger.info(f"Ball following {state}")
                    
                    # Stop motors when pausing
                    if is_paused and motor_controller:
                        motor_controller.stop()
                    
                    await ws.send_json({'status': 'paused' if is_paused else 'running'})
                    
    finally:
        active_connections.discard(ws)
        logger.info(f"Client disconnected. Total connections: {len(active_connections)}")
    
    return ws


async def index_handler(request):
    """Serve the HTML page"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Ball Following Test</title>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #0a0a0a;
            color: #0f0;
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
        .main-view {
            display: flex;
            gap: 20px;
            margin: 20px 0;
            justify-content: center;
        }
        .view-box {
            background: #1a1a1a;
            border: 2px solid #00ff88;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 0 20px rgba(0,255,136,0.2);
        }
        canvas {
            display: block;
            border-radius: 5px;
            background: #000;
            max-width: 100%;
        }
        .stats-panel {
            background: #1a1a1a;
            border: 2px solid #00ff88;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .stat-item {
            background: #0a0a0a;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #00ff88;
        }
        .stat-label {
            color: #888;
            font-size: 12px;
            margin-bottom: 5px;
        }
        .stat-value {
            color: #00ff88;
            font-size: 24px;
            font-weight: bold;
        }
        .debug-log {
            background: #001100;
            border: 1px solid #00ff88;
            border-radius: 5px;
            padding: 15px;
            margin-top: 15px;
            height: 200px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }
        .log-entry {
            margin: 2px 0;
            padding: 2px 0;
            border-bottom: 1px solid #003300;
        }
        .log-time {
            color: #666;
            margin-right: 10px;
        }
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        .status-on { background: #00ff88; box-shadow: 0 0 10px #00ff88; }
        .status-off { background: #333; }
        .controls {
            background: #1a1a1a;
            border: 2px solid #00ff88;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            text-align: center;
        }
        .control-button {
            background: linear-gradient(135deg, #00ff88, #00cc6a);
            border: none;
            color: #000;
            padding: 15px 30px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            font-size: 18px;
            margin: 10px;
            transition: all 0.3s;
            min-width: 150px;
        }
        .control-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,255,136,0.4);
        }
        .control-button:active {
            transform: translateY(0);
        }
        .control-button.paused {
            background: linear-gradient(135deg, #ff8800, #cc6600);
        }
        .control-button.running {
            background: linear-gradient(135deg, #00ff88, #00cc6a);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚽ Ball Following Test Dashboard</h1>
        
        <div class="controls">
            <h2>🎮 Controls</h2>
            <button id="pauseButton" class="control-button paused" onclick="togglePause()">
                ▶️ START FOLLOWING
            </button>
            <div id="pauseStatus" style="margin-top: 10px; font-size: 16px; color: #ff8800;">
                ⏸ PAUSED - Click START to begin ball following
            </div>
        </div>
        
        <div class="main-view">
            <div class="view-box">
                <h2>📹 Camera View with Ball Detection</h2>
                <canvas id="videoCanvas"></canvas>
            </div>
        </div>
        
        <div class="stats-panel">
            <h2>📊 Statistics & State</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-label">Connection Status</div>
                    <div class="stat-value" id="wsStatus">
                        <span class="status-indicator status-off"></span>Disconnected
                    </div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Ball Detected</div>
                    <div class="stat-value" id="ballDetected">❌ NO</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Current Ball Angle</div>
                    <div class="stat-value" id="ballAngle">---</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Movement Angle</div>
                    <div class="stat-value" id="movementAngle">---</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Time Until Next Update</div>
                    <div class="stat-value" id="nextUpdate">---</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Ball Distance</div>
                    <div class="stat-value" id="ballDistance">---</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Frames Processed</div>
                    <div class="stat-value" id="framesProcessed">0</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Ball Detections</div>
                    <div class="stat-value" id="ballDetections">0</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Direction Changes</div>
                    <div class="stat-value" id="directionChanges">0</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Uptime</div>
                    <div class="stat-value" id="uptime">0s</div>
                </div>
            </div>
            
            <div class="debug-log" id="debugLog">
                <div class="log-entry">Waiting for connection...</div>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let isPaused = true;  // Start paused
        
        function togglePause() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({type: 'toggle_pause'}));
            }
        }
        
        function updatePauseButton(paused) {
            const button = document.getElementById('pauseButton');
            const status = document.getElementById('pauseStatus');
            
            isPaused = paused;
            
            if (paused) {
                button.className = 'control-button paused';
                button.innerHTML = '▶️ START FOLLOWING';
                status.innerHTML = '⏸ PAUSED - Click START to begin ball following';
                status.style.color = '#ff8800';
            } else {
                button.className = 'control-button running';
                button.innerHTML = '⏸ PAUSE FOLLOWING';
                status.innerHTML = '▶️ RUNNING - Robot is following the ball';
                status.style.color = '#00ff88';
            }
        }
        
        function log(message) {
            const logDiv = document.getElementById('debugLog');
            const time = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.innerHTML = `<span class="log-time">[${time}]</span>${message}`;
            logDiv.appendChild(entry);
            logDiv.scrollTop = logDiv.scrollHeight;
            
            // Keep only last 50 entries
            while (logDiv.children.length > 50) {
                logDiv.removeChild(logDiv.firstChild);
            }
        }
        
        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                document.getElementById('wsStatus').innerHTML = 
                    '<span class="status-indicator status-on"></span>Connected';
                log('✓ Connected to server');
            };
            
            ws.onclose = () => {
                document.getElementById('wsStatus').innerHTML = 
                    '<span class="status-indicator status-off"></span>Disconnected';
                log('✗ Disconnected from server, reconnecting...');
                setTimeout(connect, 2000);
            };
            
            ws.onerror = (error) => {
                log('✗ Connection error');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                // Handle pause state response
                if (data.status) {
                    updatePauseButton(data.status === 'paused');
                    log(data.status === 'paused' ? '⏸ PAUSED' : '▶️ RUNNING');
                    return;
                }
                
                // Update pause button state
                if (data.is_paused !== undefined) {
                    updatePauseButton(data.is_paused);
                }
                
                // Update video frame
                if (data.frame) {
                    drawImage(data.frame);
                }
                
                // Update ball detection status
                if (data.ball_detected) {
                    document.getElementById('ballDetected').textContent = '✅ YES';
                    document.getElementById('ballDetected').style.color = '#00ff88';
                    document.getElementById('ballAngle').textContent = data.ball_angle.toFixed(1) + '°';
                    document.getElementById('ballDistance').textContent = data.ball_distance.toFixed(0) + 'px';
                } else {
                    document.getElementById('ballDetected').textContent = '❌ NO';
                    document.getElementById('ballDetected').style.color = '#ff4444';
                    document.getElementById('ballAngle').textContent = '---';
                    document.getElementById('ballDistance').textContent = '---';
                }
                
                // Update movement angle
                if (data.movement_angle !== null && !data.is_paused) {
                    document.getElementById('movementAngle').textContent = data.movement_angle.toFixed(1) + '°';
                    document.getElementById('movementAngle').style.color = '#00ff88';
                } else {
                    document.getElementById('movementAngle').textContent = data.is_paused ? 'PAUSED' : 'STOPPED';
                    document.getElementById('movementAngle').style.color = data.is_paused ? '#ff8800' : '#ff4444';
                }
                
                // Update time until next update
                const timeLeft = data.time_until_update.toFixed(1);
                document.getElementById('nextUpdate').textContent = data.is_paused ? 'PAUSED' : timeLeft + 's';
                
                // Update stats
                document.getElementById('framesProcessed').textContent = data.stats.frames_processed;
                document.getElementById('ballDetections').textContent = data.stats.ball_detections;
                document.getElementById('directionChanges').textContent = data.stats.direction_changes;
                document.getElementById('uptime').textContent = data.stats.uptime;
                
                // Log direction changes
                if (data.direction_changed) {
                    log(`🔄 Direction changed to ${data.movement_angle.toFixed(1)}° (ball at ${data.ball_angle.toFixed(1)}°)`);
                }
                
                // Log when ball is lost
                if (data.ball_lost) {
                    log('⚠ Ball lost - stopping movement');
                }
            };
        }
        
        function drawImage(base64Data) {
            const canvas = document.getElementById('videoCanvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();
            img.onload = () => {
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);
            };
            img.src = 'data:image/jpeg;base64,' + base64Data;
        }
        
        connect();
    </script>
</body>
</html>
    """
    return web.Response(text=html, content_type='text/html')


def draw_ball_following_overlay(frame, ball_result, movement_angle, time_until_update):
    """Draw debug overlay on frame"""
    viz = frame.copy()
    h, w = viz.shape[:2]
    center_x, center_y = w // 2, h // 2
    
    # Draw center crosshair
    cv2.line(viz, (center_x - 20, center_y), (center_x + 20, center_y), (0, 255, 0), 2)
    cv2.line(viz, (center_x, center_y - 20), (center_x, center_y + 20), (0, 255, 0), 2)
    cv2.circle(viz, (center_x, center_y), 5, (0, 255, 0), -1)
    
    # Draw ball if detected
    if ball_result and ball_result.detected:
        ball_x = ball_result.center_x
        ball_y = ball_result.center_y
        ball_radius = ball_result.radius
        
        # Draw ball circle
        cv2.circle(viz, (ball_x, ball_y), ball_radius, (0, 165, 255), 3)
        cv2.circle(viz, (ball_x, ball_y), 3, (0, 165, 255), -1)
        
        # Draw line from center to ball
        cv2.line(viz, (center_x, center_y), (ball_x, ball_y), (0, 165, 255), 2)
        
        # Draw ball info
        info_text = f"Ball: {ball_result.angle:.1f}deg, {ball_result.distance:.0f}px"
        cv2.putText(viz, info_text, (ball_x + ball_radius + 10, ball_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
    
    # Draw movement direction arrow
    if movement_angle is not None:
        # Convert angle to radians (0° is up)
        angle_rad = math.radians(-90 + movement_angle)
        arrow_length = 80
        
        end_x = int(center_x + arrow_length * math.cos(angle_rad))
        end_y = int(center_y + arrow_length * math.sin(angle_rad))
        
        # Draw thick arrow
        cv2.arrowedLine(viz, (center_x, center_y), (end_x, end_y), 
                       (0, 255, 255), 4, tipLength=0.3)
        
        # Draw movement angle text
        move_text = f"Moving: {movement_angle:.1f}deg"
        cv2.putText(viz, move_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    else:
        cv2.putText(viz, "STOPPED", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    
    # Draw update timer
    timer_text = f"Next update: {time_until_update:.1f}s"
    cv2.putText(viz, timer_text, (10, 60), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    return viz


async def ball_following_loop():
    """Main ball following loop"""
    global current_ball_angle, current_movement_angle, last_update_time, stats, is_paused
    
    print("Ball following loop started!")
    
    # Wait for camera to be initialized
    while camera is None:
        print("Waiting for camera initialization...")
        await asyncio.sleep(0.5)
    
    print("Camera ready! Ball following paused by default - click START in web interface")
    
    last_ball_detected = False
    last_pause_state = is_paused
    
    while True:
        try:
            # Get current time
            current_time = time.time()
            
            # Check if pause state changed
            if is_paused != last_pause_state:
                if is_paused:
                    print("\n⏸ PAUSED - Stopping motors")
                    current_movement_angle = None
                    if motor_controller:
                        motor_controller.stop()
                else:
                    print("\n▶️ RESUMED - Ball following active")
                    last_update_time = current_time  # Reset timer when resuming
                last_pause_state = is_paused
            
            # Capture frame (always capture, even when paused)
            frame = camera.capture_frame()
            if frame is None:
                await asyncio.sleep(0.01)
                continue
            
            stats['frames_processed'] += 1
            
            # Update mirror mask
            camera.update_mirror_mask(frame)
            
            # Detect ball (always detect, even when paused)
            ball_result = camera.detect_ball(frame)
            
            direction_changed = False
            ball_lost = False
            
            # Only update movement if NOT paused
            if not is_paused:
                if ball_result and ball_result.detected:
                    stats['ball_detections'] += 1
                    stats['last_ball_seen'] = datetime.now().strftime('%H:%M:%S')
                    
                    current_ball_angle = ball_result.angle
                    
                    # Check if it's time to update movement direction
                    time_since_update = current_time - last_update_time
                    
                    if time_since_update >= UPDATE_INTERVAL:
                        # Update movement direction
                        old_angle = current_movement_angle
                        current_movement_angle = ball_result.angle
                        last_update_time = current_time
                        stats['direction_changes'] += 1
                        direction_changed = True
                        
                        print("\n" + "="*70)
                        print(f"DIRECTION UPDATE #{stats['direction_changes']}")
                        print("="*70)
                        print(f"Time: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
                        print(f"Ball angle: {ball_result.angle:.2f}°")
                        print(f"Ball distance: {ball_result.distance:.1f}px")
                        print(f"Old movement angle: {old_angle}")
                        print(f"New movement angle: {current_movement_angle:.2f}°")
                        print(f"Speed: {MOVEMENT_SPEED}")
                        print("="*70 + "\n")
                        
                        # Send movement command (keep sending to prevent watchdog timeout)
                        if motor_controller:
                            motor_controller.move_robot_relative(
                                angle=current_movement_angle, 
                                speed=MOVEMENT_SPEED, 
                                rotation=0.0
                            )
                    else:
                        # Keep sending the current movement command to prevent watchdog timeout
                        if motor_controller and current_movement_angle is not None:
                            motor_controller.move_robot_relative(
                                angle=current_movement_angle, 
                                speed=MOVEMENT_SPEED, 
                                rotation=0.0
                            )
                    
                    last_ball_detected = True
                    
                else:
                    # Ball not detected
                    if last_ball_detected:
                        # Just lost the ball
                        print("\n⚠ BALL LOST - Stopping movement")
                        current_movement_angle = None
                        ball_lost = True
                        
                        if motor_controller:
                            motor_controller.stop()
                        
                        last_ball_detected = False
            
            # Calculate time until next update
            time_until_update = max(0, UPDATE_INTERVAL - (current_time - last_update_time))
            
            # Create visualization
            viz_frame = draw_ball_following_overlay(
                frame, ball_result, current_movement_angle, time_until_update
            )
            
            # Apply transformations (180° rotation + horizontal flip)
            viz_frame = cv2.rotate(viz_frame, cv2.ROTATE_180)
            viz_frame = cv2.flip(viz_frame, 1)
            
            # Encode frame
            _, jpg = cv2.imencode('.jpg', viz_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_b64 = base64.b64encode(jpg).decode('utf-8')
            
            # Calculate uptime
            uptime = int(time.time() - stats['uptime_start'])
            uptime_str = f"{uptime//60}m {uptime%60}s" if uptime >= 60 else f"{uptime}s"
            
            # Prepare data for clients
            data = {
                'frame': frame_b64,
                'ball_detected': ball_result.detected if ball_result else False,
                'ball_angle': ball_result.angle if (ball_result and ball_result.detected) else None,
                'ball_distance': ball_result.distance if (ball_result and ball_result.detected) else None,
                'movement_angle': current_movement_angle if not is_paused else None,
                'time_until_update': time_until_update,
                'direction_changed': direction_changed and not is_paused,
                'ball_lost': ball_lost,
                'is_paused': is_paused,
                'stats': {
                    'frames_processed': stats['frames_processed'],
                    'ball_detections': stats['ball_detections'],
                    'direction_changes': stats['direction_changes'],
                    'uptime': uptime_str
                }
            }
            
            # Broadcast to all connected clients
            for ws in list(active_connections):
                try:
                    await ws.send_json(data)
                except:
                    active_connections.discard(ws)
            
            await asyncio.sleep(0.033)  # ~30 fps
            
        except Exception as e:
            logger.error(f"Error in ball following loop: {e}", exc_info=True)
            await asyncio.sleep(0.1)


async def start_background_tasks(app):
    """Start background tasks"""
    app['ball_following'] = asyncio.create_task(ball_following_loop())


async def cleanup_background_tasks(app):
    """Cleanup background tasks"""
    app['ball_following'].cancel()
    try:
        await app['ball_following']
    except asyncio.CancelledError:
        pass


def main():
    global camera, motor_controller
    
    print("="*70)
    print("Ball Following Test")
    print("="*70)
    
    robot_id = get_robot_id()
    config = load_config(robot_id)
    
    print(f"Robot ID: {robot_id}")
    print(f"Update interval: {UPDATE_INTERVAL} seconds")
    print(f"Movement speed: {MOVEMENT_SPEED}")
    
    # Initialize camera
    try:
        camera = CameraProcess(config)
        print("✓ Camera initialized successfully")
        
        test_frame = camera.capture_frame()
        if test_frame is None:
            print("⚠ Warning: Camera not capturing frames yet")
        else:
            print(f"✓ Camera capturing frames: {test_frame.shape}")
    except Exception as e:
        print(f"✗ Failed to initialize camera: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Initialize motor controller
    try:
        motor_controller = MotorController(config)
        print("✓ Motor controller initialized successfully")
    except Exception as e:
        print(f"⚠ Warning: Motor controller failed to initialize: {e}")
        print("  (Will run in camera-only mode)")
    
    # Create web application
    app = web.Application()
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', websocket_handler)
    
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    
    print("\n" + "="*70)
    print("Server starting on http://0.0.0.0:8084")
    print("Open in browser to view ball following dashboard")
    print("="*70)
    print("\nBehavior:")
    print(f"  - Detects ball every frame")
    print(f"  - Updates movement direction every {UPDATE_INTERVAL} seconds")
    print(f"  - Stops when ball is lost")
    print(f"  - Shows live debug visualization")
    print("="*70 + "\n")
    
    input("Press Enter to start the server...")
    try:
        web.run_app(app, host='0.0.0.0', port=8084)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        if camera:
            camera.stop()
        if motor_controller:
            motor_controller.stop()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
