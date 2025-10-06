#!/usr/bin/env python3
"""
Complete Robot Localization System - Single File Solution
Runs both the localization algorithm and web server in one process.
Just run this one file and everything works!
"""

import asyncio
import json
import math
import time
import threading
from typing import Dict, Any, List
import logging
import config

# FastAPI and web server imports
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect  
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

# Hardware imports with proper path handling
import sys
import os

# Add current directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    import config
except ImportError:
    print("⚠️  config.py not found, using defaults")
    config = None

try:
    import board
    from tof import ToF
    from imu import IMU
    HARDWARE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Hardware imports failed: {e}")
    print("   Running in simulation mode")
    HARDWARE_AVAILABLE = False
    # Create mock classes for testing
    class MockBoard:
        class I2C:
            def __init__(self, scl, sda): pass
        SCL = SDA = None
    class MockToF:
        def __init__(self, *args, **kwargs): 
            self.angle = kwargs.get('angle', 0)
        def next_dist(self): return 500  # Mock distance
    class MockIMU:
        def __init__(self, *args, **kwargs): pass
        def cur_angle(self): return 0.0  # Mock angle
    
    board = MockBoard()
    ToF = MockToF
    IMU = MockIMU

# Global data store for sharing between localization and web server
latest_data: Dict[str, Any] = {
    'position': [0.0, 0.0],
    'angle': 0.0, 
    'error': float('inf'),
    'timestamp': 0,
    'localization_time_ms': 0,
    'sensor_count': 0,
    'status': 'initializing'
}

# WebSocket connections
connections: List[WebSocket] = []

# Create FastAPI app
app = FastAPI(title="Robot Localization System")

# HTML template as string (so we don't need external files)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 Robot Localization</title>
    <style>
        body { 
            font-family: Arial, sans-serif; margin: 0; padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; min-height: 100vh;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 30px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .info-panel { 
            background: rgba(255,255,255,0.1); padding: 20px; border-radius: 15px; 
            margin-bottom: 20px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2);
        }
        .metrics { display: flex; gap: 20px; flex-wrap: wrap; justify-content: center; }
        .metric { 
            background: rgba(255,255,255,0.2); padding: 15px; border-radius: 10px; 
            min-width: 120px; text-align: center; border: 1px solid rgba(255,255,255,0.3);
        }
        .metric-label { font-size: 12px; opacity: 0.8; margin-bottom: 5px; }
        .metric-value { font-size: 18px; font-weight: bold; }
        .canvas-container { text-align: center; }
        canvas { 
            background: white; border-radius: 10px; 
            box-shadow: 0 8px 32px rgba(0,0,0,0.3); border: 2px solid rgba(255,255,255,0.2);
        }
        .status { 
            position: absolute; top: 20px; right: 20px; padding: 10px 20px; 
            border-radius: 25px; font-weight: bold; backdrop-filter: blur(10px);
        }
        .connected { background: rgba(76, 175, 80, 0.8); }
        .disconnected { background: rgba(244, 67, 54, 0.8); }
        .footer { text-align: center; margin-top: 30px; opacity: 0.7; }
    </style>
</head>
<body>
    <div class="status disconnected" id="status">🔄 Connecting...</div>
    <div class="container">
        <h1>🤖 Robot Localization System</h1>
        
        <div class="info-panel">
            <div class="metrics">
                <div class="metric">
                    <div class="metric-label">X Position</div>
                    <div class="metric-value" id="posX">-- mm</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Y Position</div>
                    <div class="metric-value" id="posY">-- mm</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Angle</div>
                    <div class="metric-value" id="angle">-- °</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Error</div>
                    <div class="metric-value" id="error">--</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Sensors</div>
                    <div class="metric-value" id="sensors">--</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Update Time</div>
                    <div class="metric-value" id="updateTime">-- ms</div>
                </div>
            </div>
        </div>
        
        <div class="canvas-container">
            <canvas id="fieldCanvas" width="800" height="600"></canvas>
        </div>
        
        <div class="footer">
            <p>🚀 Real-time robot localization with ToF sensors and IMU</p>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('fieldCanvas');
        const ctx = canvas.getContext('2d');
        
        // Field dimensions (mm)
        const FIELD_WIDTH = 2430, FIELD_HEIGHT = 1820, GOAL_WIDTH = 450;
        const SCALE = Math.min(canvas.width / FIELD_WIDTH, canvas.height / FIELD_HEIGHT);
        const OFFSET_X = (canvas.width - FIELD_WIDTH * SCALE) / 2;
        const OFFSET_Y = (canvas.height - FIELD_HEIGHT * SCALE) / 2;
        
        function fieldToCanvas(x, y) {
            return [OFFSET_X + (x + FIELD_WIDTH/2) * SCALE, OFFSET_Y + (-y + FIELD_HEIGHT/2) * SCALE];
        }
        
        function drawField() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Field background
            ctx.fillStyle = "#2d8a2f";
            const [fieldX, fieldY] = fieldToCanvas(-FIELD_WIDTH/2, FIELD_HEIGHT/2);
            ctx.fillRect(fieldX, fieldY, FIELD_WIDTH * SCALE, FIELD_HEIGHT * SCALE);
            
            // Field border
            ctx.strokeStyle = "white";
            ctx.lineWidth = 3;
            ctx.strokeRect(fieldX, fieldY, FIELD_WIDTH * SCALE, FIELD_HEIGHT * SCALE);
            
            // Center line and circle
            ctx.beginPath();
            const [centerX, centerY] = fieldToCanvas(0, 0);
            ctx.moveTo(centerX, fieldToCanvas(0, FIELD_HEIGHT/2)[1]);
            ctx.lineTo(centerX, fieldToCanvas(0, -FIELD_HEIGHT/2)[1]);
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(centerX, centerY, 200 * SCALE, 0, 2 * Math.PI);
            ctx.stroke();
            
            // Goals
            [-1, 1].forEach(side => {
                const goalX = side * (FIELD_WIDTH/2 - 74);
                const goalBackX = side * FIELD_WIDTH/2;
                
                ctx.strokeStyle = "white";
                ctx.lineWidth = 4;
                
                // Goal frame
                const [p1X, p1Y] = fieldToCanvas(goalBackX, GOAL_WIDTH/2);
                const [p2X, p2Y] = fieldToCanvas(goalBackX, -GOAL_WIDTH/2);
                const [p3X, p3Y] = fieldToCanvas(goalX, GOAL_WIDTH/2);
                const [p4X, p4Y] = fieldToCanvas(goalX, -GOAL_WIDTH/2);
                
                ctx.beginPath();
                ctx.moveTo(p1X, p1Y);
                ctx.lineTo(p2X, p2Y);
                ctx.lineTo(p4X, p4Y);
                ctx.lineTo(p3X, p3Y);
                ctx.closePath();
                ctx.stroke();
                
                // Goal area color
                ctx.fillStyle = side > 0 ? "rgba(74, 144, 226, 0.3)" : "rgba(245, 212, 66, 0.3)";
                ctx.fill();
            });
        }
        
        function drawRobot(pos, angle) {
            const [canvasX, canvasY] = fieldToCanvas(pos[0], pos[1]);
            
            // Robot body
            ctx.fillStyle = "#333333";
            ctx.beginPath();
            ctx.arc(canvasX, canvasY, 40 * SCALE, 0, 2 * Math.PI);
            ctx.fill();
            
            // Direction indicator
            ctx.strokeStyle = "#ff4444";
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.moveTo(canvasX, canvasY);
            const dirX = canvasX + Math.cos(angle) * 50 * SCALE;
            const dirY = canvasY - Math.sin(angle) * 50 * SCALE;
            ctx.lineTo(dirX, dirY);
            ctx.stroke();
            
            // Robot outline
            ctx.strokeStyle = "#666666";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(canvasX, canvasY, 40 * SCALE, 0, 2 * Math.PI);
            ctx.stroke();
        }
        
        // WebSocket connection
        const ws = new WebSocket(`ws://${window.location.host}/ws/data`);
        const statusEl = document.getElementById('status');
        
        ws.onopen = () => {
            statusEl.textContent = '✅ Connected';
            statusEl.className = 'status connected';
        };
        
        ws.onclose = () => {
            statusEl.textContent = '❌ Disconnected';
            statusEl.className = 'status disconnected';
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            // Update metrics
            document.getElementById('posX').textContent = `${data.position[0].toFixed(1)} mm`;
            document.getElementById('posY').textContent = `${data.position[1].toFixed(1)} mm`;
            document.getElementById('angle').textContent = `${(data.angle * 180 / Math.PI).toFixed(1)}°`;
            document.getElementById('error').textContent = data.error.toFixed(2);
            document.getElementById('sensors').textContent = data.sensor_count;
            document.getElementById('updateTime').textContent = `${data.localization_time_ms.toFixed(1)} ms`;
            
            // Draw field with robot
            drawField();
            drawRobot(data.position, data.angle);
        };
        
        // Initial draw
        drawField();
    </script>
</body>
</html>
"""

class LocalizationSystem:
    def __init__(self):
        self.localizer = None
        self.running = False
        
    async def initialize_hardware(self):
        """Initialize all hardware components"""
        global latest_data
        
        try:
            print("🔧 Initializing hardware...")
            latest_data['status'] = 'initializing_hardware'
            
            # Initialize I2C
            i2c = board.I2C(board.SCL, board.SDA)
            
            # Initialize IMU
            print("🧭 Initializing IMU...")
            imu = IMU(i2c=i2c)
            
            # Initialize ToF sensors
            print("📡 Initializing ToF sensors...")
            tofs = []
            
            if config and hasattr(config, 'tof_addrs') and config.tof_addrs:
                # Use config if available
                for i, addr in enumerate(config.tof_addrs):
                    try:
                        # Handle both list and dict formats for offsets and angles
                        if hasattr(config, 'tof_offsets'):
                            if isinstance(config.tof_offsets, list) and i < len(config.tof_offsets):
                                offset = config.tof_offsets[i]
                            elif isinstance(config.tof_offsets, dict):
                                offset = config.tof_offsets.get(addr, 0)
                            else:
                                offset = 0
                        else:
                            offset = 0
                            
                        if hasattr(config, 'tof_angles'):
                            if isinstance(config.tof_angles, list) and i < len(config.tof_angles):
                                angle = math.radians(config.tof_angles[i])
                            elif isinstance(config.tof_angles, dict):
                                angle = math.radians(config.tof_angles.get(addr, 0))
                            else:
                                angle = 0
                        else:
                            angle = 0
                            
                        tof = ToF(addr, offset, angle, i2c)
                        tofs.append(tof)
                        print(f"  ✅ ToF sensor at 0x{addr:02x} (offset: {offset}mm, angle: {math.degrees(angle):.1f}°)")
                    except Exception as e:
                        print(f"  ❌ Failed ToF at 0x{addr:02x}: {e}")
            else:
                print("⚠️  Using default ToF configuration...")
                # Default sensor setup
                default_sensors = [(0x29, 0), (0x2A, 45), (0x2B, 90), (0x2C, 135)]
                
                for addr, angle_deg in default_sensors:
                    try:
                        tof = ToF(addr, 0, math.radians(angle_deg), i2c)
                        tofs.append(tof)
                        print(f"  ✅ ToF sensor at 0x{addr:02x}, {angle_deg}°")
                    except Exception as e:
                        print(f"  ⚠️  Skipping ToF at 0x{addr:02x}: {e}")
            
            if not tofs:
                if HARDWARE_AVAILABLE:
                    raise Exception("No ToF sensors initialized!")
                else:
                    # Create mock sensors for testing
                    for addr, angle_deg in [(0x29, 0), (0x2A, 90)]:
                        tof = ToF(addr, 0, math.radians(angle_deg))
                        tofs.append(tof)
                    print("  🔧 Using mock sensors for testing")
            
            # Create localizer - handle import properly
            try:
                from localizer import Localizer
            except ImportError:
                # Try different import paths
                localizer_path = os.path.join(current_dir, "localizer.py")
                if os.path.exists(localizer_path):
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("localizer", localizer_path)
                    if spec and spec.loader:
                        localizer_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(localizer_module)
                        Localizer = localizer_module.Localizer
                    else:
                        raise ImportError("Could not load localizer module")
                else:
                    raise ImportError(f"localizer.py not found at {localizer_path}")
            
            # Create localizer instance (type: ignore for mock compatibility)
            self.localizer = Localizer(i2c=i2c, tofs=tofs, imu=imu)  # type: ignore
            
            latest_data.update({
                'sensor_count': len(tofs),
                'status': 'ready'
            })
            
            print(f"✅ Hardware initialized: {len(tofs)} ToF sensors + IMU")
            return True
            
        except Exception as e:
            print(f"❌ Hardware initialization failed: {e}")
            latest_data['status'] = f'hardware_error: {e}'
            return False
    
    async def localization_loop(self):
        """Main localization loop"""
        global latest_data
        
        if not self.localizer:
            print("❌ Localizer not initialized!")
            return
        
        print("🚀 Starting localization loop...")
        self.running = True
        
        while self.running:
            try:
                start_time = time.time()
                
                # Perform localization
                position, error = self.localizer.localize()
                angle = self.localizer.imu.cur_angle()
                localization_time = (time.time() - start_time) * 1000
                
                # Update global data
                latest_data.update({
                    'position': position,
                    'angle': angle,
                    'error': error,
                    'timestamp': time.time(),
                    'localization_time_ms': localization_time,
                    'status': 'running'
                })
                
                # Send to all connected websockets
                await self.broadcast_data()
                
                # Print status
                print(f"📍 Pos: ({position[0]:.1f}, {position[1]:.1f}), "
                      f"Angle: {math.degrees(angle):.1f}°, "
                      f"Error: {error:.2f}, "
                      f"Time: {localization_time:.1f}ms")
                
                # Wait for next update (10 Hz)
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"❌ Localization error: {e}")
                latest_data['status'] = f'localization_error: {e}'
                await asyncio.sleep(1)
    
    async def broadcast_data(self):
        """Send data to all connected websockets"""
        if not connections:
            return
            
        message = json.dumps(latest_data)
        disconnected = []
        
        for ws in connections:
            try:
                await ws.send_text(message)
            except:
                disconnected.append(ws)
        
        # Remove disconnected clients
        for ws in disconnected:
            connections.remove(ws)
    
    def stop(self):
        """Stop the localization system"""
        self.running = False

# Create global system instance
localization_system = LocalizationSystem()

# FastAPI routes
@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTMLResponse(content=HTML_TEMPLATE)

@app.websocket("/ws/data")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)
    
    try:
        # Send initial data
        await websocket.send_text(json.dumps(latest_data))
        
        # Keep connection alive
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in connections:
            connections.remove(websocket)

async def main():
    """Main function that runs everything"""
    print("🤖 Robot Localization System - Single File Edition")
    print("=" * 50)
    
    # Find available port
    import socket
    def find_free_port(start_port=8000):
        for port in range(start_port, start_port + 10):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port
            except OSError:
                continue
        return 8000  # fallback
    
    port = find_free_port()
    
    # Initialize hardware
    hardware_ok = await localization_system.initialize_hardware()
    if not hardware_ok:
        print("⚠️  Hardware initialization failed, running in demo mode")
        latest_data.update({
            'status': 'demo_mode',
            'position': [0.0, 0.0],
            'angle': 0.0,
            'error': 0.0,
            'sensor_count': 0,
            'localization_time_ms': 0
        })
    
    # Start localization in background (only if hardware is OK)
    localization_task = None
    if hardware_ok:
        localization_task = asyncio.create_task(localization_system.localization_loop())
    else:
        # Start demo mode
        localization_task = asyncio.create_task(demo_mode())
    
    # Start web server
    config_server = uvicorn.Config(
        app=app,
        host="0.0.0.0", 
        port=port,
        log_level="warning"  # Reduce log noise
    )
    server = uvicorn.Server(config_server)
    
    print(f"🌐 Web server starting on http://localhost:{port}")
    if not hardware_ok:
        print("🎮 Running in DEMO MODE (no hardware detected)")
    print("📱 Open your browser to see the visualization!")
    print("🛑 Press Ctrl+C to stop everything")
    print()
    
    try:
        # Run server (this blocks)
        await server.serve()
    except KeyboardInterrupt:
        print("\n🛑 Stopping system...")
    except Exception as e:
        print(f"❌ Server error: {e}")
    finally:
        localization_system.stop()
        if localization_task:
            localization_task.cancel()
            try:
                await localization_task
            except asyncio.CancelledError:
                pass

async def demo_mode():
    """Demo mode that simulates robot movement when no hardware is available"""
    print("🎮 Starting demo mode - simulated robot movement")
    
    t = 0
    while True:
        # Simulate robot moving in a circle
        x = 400 * math.cos(t * 0.1)
        y = 300 * math.sin(t * 0.1)
        angle = t * 0.1 + math.pi/2
        
        latest_data.update({
            'position': [x, y],
            'angle': angle,
            'error': 5.0 + 2.0 * math.sin(t * 0.05),
            'timestamp': time.time(),
            'localization_time_ms': 15.0 + 5.0 * math.sin(t * 0.1),
            'sensor_count': 4,
            'status': 'demo_mode'
        })
        
        # Broadcast to connected clients
        await localization_system.broadcast_data()
        
        t += 1
        await asyncio.sleep(0.1)  # 10 Hz

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 System stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
    finally:
        print("🔧 Cleanup complete")