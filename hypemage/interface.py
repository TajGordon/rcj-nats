"""
Robot Interface Server

Simple, extensible robot control server using FastAPI.

Features:
- WebSocket for commands & status updates
- HTTP REST API for logs/status
- Generic script launcher (add scripts via config, not code)
- Static file serving for web dashboard

Usage:
    python -m hypemage.interface
    
Endpoints:
    WS  ws://robot:8080/ws         - Commands & status
    GET http://robot:8080/         - Dashboard UI
    GET http://robot:8080/status   - JSON status
    GET http://robot:8080/scripts  - Available scripts
    GET http://robot:8080/logs     - Recent logs
"""

import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import subprocess
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
import threading
import time
from dataclasses import dataclass
import socket

from hypemage.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ScriptConfig:
    """Configuration for a runnable script"""
    name: str  # Display name
    module: str  # Python module path (e.g., "hypemage.scylla")
    args: List[str]  # Default arguments
    description: str  # What it does
    category: str  # "robot" | "calibration" | "test" | "utility"


class InterfaceServer:
    """
    Manages robot processes and provides command interface via FastAPI
    """
    
    def __init__(self):
        # Available scripts (easily extensible!)
        self.scripts: Dict[str, ScriptConfig] = {
            # Main robot scripts
            'scylla_debug': ScriptConfig(
                name='Robot (Debug Mode)',
                module='hypemage.scylla',
                args=['--debug'],
                description='Run main robot with debug output and camera streaming',
                category='robot'
            ),
            'scylla_production': ScriptConfig(
                name='Robot (Production Mode)',
                module='hypemage.scylla',
                args=[],
                description='Run main robot in competition mode (no debug overhead)',
                category='robot'
            ),
            
            # Calibration utilities
            'color_calibration': ScriptConfig(
                name='Color Calibration',
                module='hypemage.debug.color_calibration',
                args=[],
                description='Calibrate HSV ranges for ball and goal detection',
                category='calibration'
            ),
            'camera_calibrate': ScriptConfig(
                name='Camera HSV Calibration',
                module='hypemage.scripts.camera_calibrate',
                args=[],
                description='Interactive HSV range calibration with live mask previews',
                category='calibration'
            ),
            'imu_calibration': ScriptConfig(
                name='IMU Calibration',
                module='hypemage.calibrate_imu',  # You'd create this
                args=[],
                description='Calibrate IMU offsets and magnetometer',
                category='calibration'
            ),
            
            # Test scripts
            'camera_debug': ScriptConfig(
                name='Camera Debug View',
                module='hypemage.scripts.camera_debug',
                args=[],
                description='View camera feed with detection overlays (ball, goals)',
                category='test'
            ),
            'camera_stream': ScriptConfig(
                name='Camera Stream',
                module='hypemage.scripts.camera_stream',
                args=[],
                description='Stream raw camera feed to dashboard',
                category='test'
            ),
            'motor_test': ScriptConfig(
                name='Motor Test',
                module='motors.motor',
                args=[],
                description='Test individual motor control and speeds',
                category='test'
            ),
            'camera_test': ScriptConfig(
                name='Camera Test',
                module='camera.camera_test_server',
                args=[],
                description='Test camera feed and view raw frames',
                category='test'
            ),
            'dribbler_test': ScriptConfig(
                name='Dribbler Test',
                module='motors.dribbler_test',
                args=[],
                description='Test dribbler motor speeds',
                category='test'
            ),
            
            # Add more easily!
        }
        
        # Active process tracking
        self.active_process: Optional[subprocess.Popen] = None
        self.active_script: Optional[str] = None
        self.process_lock = threading.Lock()
        
        # WebSocket clients
        self.ws_clients: Set[WebSocket] = set()
        
        # Start process monitor thread
        self.monitor_thread = threading.Thread(target=self._monitor_process, daemon=True)
        self.monitor_thread.start()
    
    def _monitor_process(self):
        """Monitor active process and notify clients when it exits"""
        while True:
            time.sleep(0.5)
            
            with self.process_lock:
                if self.active_process and self.active_process.poll() is not None:
                    exit_code = self.active_process.returncode
                    script_name = self.active_script
                    
                    logger.info(f"Process {script_name} exited with code {exit_code}")
                    
                    # Notify all clients
                    asyncio.run(self._broadcast({
                        'type': 'process_stopped',
                        'script': script_name,
                        'exit_code': exit_code
                    }))
                    
                    self.active_process = None
                    self.active_script = None
    
    async def _broadcast(self, message: Dict[str, Any]):
        """Send message to all connected WebSocket clients"""
        if not self.ws_clients:
            return
        
        message_json = json.dumps(message)
        disconnected = []
        
        for ws in self.ws_clients:
            try:
                await ws.send_text(message_json)
            except Exception:
                disconnected.append(ws)
        
        # Clean up disconnected clients
        for ws in disconnected:
            self.ws_clients.discard(ws)
    
    async def _log_process_output(self, process: subprocess.Popen, script_name: str):
        """Log script output in real-time"""
        try:
            while True:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, process.stdout.readline
                )
                
                if not line:
                    # Process finished
                    break
                
                # Log the output
                logger.info(f"[{script_name}] {line.rstrip()}")
                
        except Exception as e:
            logger.error(f"Error reading process output: {e}")
    
    # ========== Command Handlers ==========
    
    async def run_script(self, script_id: str, extra_args: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generic script launcher - works for ANY script!
        
        Args:
            script_id: Key from self.scripts
            extra_args: Additional arguments to pass
        
        Returns:
            {'success': bool, 'pid': int, 'message': str}
        """
        if script_id not in self.scripts:
            available = list(self.scripts.keys())
            return {
                'success': False,
                'error': f'Unknown script: {script_id}',
                'available_scripts': available
            }
        
        with self.process_lock:
            # Stop existing process if running
            if self.active_process:
                return {
                    'success': False,
                    'error': f'Already running: {self.active_script}',
                    'suggestion': 'Stop current script first'
                }
            
            script = self.scripts[script_id]
            
            # Build command
            cmd = [sys.executable, '-m', script.module] + script.args
            if extra_args:
                cmd.extend(extra_args)
            
            logger.info(f"Launching script: {script.name}")
            logger.debug(f"Command: {' '.join(cmd)}")
            
            try:
                self.active_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Merge stderr into stdout
                    text=True,
                    bufsize=1  # Line buffered
                )
                self.active_script = script_id
                
                # Start background task to log output
                asyncio.create_task(self._log_process_output(self.active_process, script.name))
                
                # Notify clients
                await self._broadcast({
                    'type': 'process_started',
                    'script': script_id,
                    'script_name': script.name,
                    'pid': self.active_process.pid
                })
                
                return {
                    'success': True,
                    'pid': self.active_process.pid,
                    'script': script.name,
                    'command': ' '.join(cmd)
                }
            
            except Exception as e:
                logger.error(f"Failed to launch {script.name}: {e}")
                self.active_process = None
                self.active_script = None
                
                return {
                    'success': False,
                    'error': str(e)
                }
    
    async def stop_script(self) -> Dict[str, Any]:
        """Stop currently running script"""
        with self.process_lock:
            if not self.active_process:
                return {
                    'success': False,
                    'message': 'No script running'
                }
            
            script_name = self.active_script
            pid = self.active_process.pid
            
            logger.info(f"Stopping script: {script_name} (PID {pid})")
            
            try:
                # Try graceful shutdown first
                self.active_process.terminate()
                
                # Wait up to 5 seconds
                try:
                    self.active_process.wait(timeout=5)
                    logger.info(f"Process {pid} terminated gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    logger.warning(f"Process {pid} didn't stop, force killing")
                    self.active_process.kill()
                    self.active_process.wait()
                
                exit_code = self.active_process.returncode
                
                # Notify clients
                await self._broadcast({
                    'type': 'process_stopped',
                    'script': script_name,
                    'exit_code': exit_code
                })
                
                self.active_process = None
                self.active_script = None
                
                return {
                    'success': True,
                    'message': f'Stopped {script_name}',
                    'exit_code': exit_code
                }
            
            except Exception as e:
                logger.error(f"Error stopping process: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current server status"""
        with self.process_lock:
            if self.active_process and self.active_script:
                script = self.scripts[self.active_script]
                return {
                    'running': True,
                    'script_id': self.active_script,
                    'script_name': script.name,
                    'pid': self.active_process.pid,
                    'category': script.category
                }
            else:
                return {
                    'running': False,
                    'script_id': None,
                    'script_name': None,
                    'pid': None,
                    'category': None
                }
    
    def get_available_scripts(self) -> Dict[str, Any]:
        """Get all available scripts grouped by category"""
        by_category = {}
        
        for script_id, script in self.scripts.items():
            if script.category not in by_category:
                by_category[script.category] = []
            
            by_category[script.category].append({
                'id': script_id,
                'name': script.name,
                'description': script.description,
                'args': script.args
            })
        
        return by_category


# ========== FastAPI Application ==========

app = FastAPI(title="Robot Interface Server")
server = InterfaceServer()

# Serve static files (client UI)
client_dir = Path(__file__).parent / 'client'
if client_dir.exists():
    app.mount("/static", StaticFiles(directory=str(client_dir)), name="static")


@app.get('/')
async def index():
    """Serve dashboard UI"""
    html_path = client_dir / 'index.html'
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text())
    else:
        return HTMLResponse(content="""
        <html>
            <head><title>Robot Interface</title></head>
            <body>
                <h1>Robot Interface Server</h1>
                <p>Client files not found. Place UI in hypemage/client/</p>
                <p>WebSocket endpoint: <code>ws://robot:8080/ws</code></p>
            </body>
        </html>
        """)


@app.get('/status')
async def get_status():
    """Get current status as JSON"""
    return JSONResponse(content=server.get_status())


@app.get('/scripts')
async def get_scripts():
    """Get available scripts"""
    return JSONResponse(content=server.get_available_scripts())


@app.get('/logs')
async def get_logs(lines: int = 100):
    """Get recent log lines"""
    log_file = Path('logs/robot.log')
    
    if not log_file.exists():
        return JSONResponse(content={'logs': [], 'message': 'No log file found'})
    
    try:
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:]
            
        return JSONResponse(content={
            'logs': [line.strip() for line in recent],
            'total_lines': len(all_lines)
        })
    except Exception as e:
        return JSONResponse(content={'error': str(e)}, status_code=500)


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for commands and status updates
    
    Client sends:
        {"command": "run_script", "script_id": "scylla_debug", "args": []}
        {"command": "stop_script"}
        {"command": "get_status"}
        {"command": "get_scripts"}
    
    Server sends:
        {"type": "response", "data": {...}}
        {"type": "process_started", "script": "...", "pid": 123}
        {"type": "process_stopped", "script": "...", "exit_code": 0}
    """
    await websocket.accept()
    server.ws_clients.add(websocket)
    logger.info(f"WebSocket client connected: {websocket.client}")
    
    try:
        # Send initial status
        await websocket.send_json({
            'type': 'init',
            'status': server.get_status(),
            'scripts': server.get_available_scripts()
        })
        
        # Handle messages
        while True:
            message = await websocket.receive_text()
            logger.info(f"Received WebSocket message: {message}")
            
            try:
                data = json.loads(message)
                command = data.get('command')
                args = data.get('args', {})
                
                logger.info(f"Processing command: {command} with args: {args}")
                
                if command == 'run_script':
                    script_id = args.get('script_id')
                    extra_args = args.get('args', [])
                    logger.info(f"Running script: {script_id} with extra_args: {extra_args}")
                    result = await server.run_script(script_id, extra_args)
                    logger.info(f"Script result: {result}")
                    await websocket.send_json({'type': 'response', 'data': result})
                
                elif command == 'stop_script':
                    logger.info("Stopping script")
                    result = await server.stop_script()
                    await websocket.send_json({'type': 'response', 'data': result})
                
                elif command == 'get_status':
                    status = server.get_status()
                    await websocket.send_json({'type': 'response', 'data': status})
                
                elif command == 'get_scripts':
                    scripts = server.get_available_scripts()
                    await websocket.send_json({'type': 'response', 'data': scripts})
                
                else:
                    logger.warning(f"Unknown command: {command}")
                    await websocket.send_json({
                        'type': 'error',
                        'message': f'Unknown command: {command}'
                    })
            
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                await websocket.send_json({
                    'type': 'error',
                    'message': 'Invalid JSON'
                })
            except Exception as e:
                logger.error(f"Error handling message: {e}", exc_info=True)
                await websocket.send_json({
                    'type': 'error',
                    'message': str(e)
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {websocket.client}")
    finally:
        server.ws_clients.discard(websocket)


# TODO: Add camera streaming endpoint (when camera has debug_q)
# @app.get('/camera')
# async def camera_stream():
#     """Stream camera feed via HTTP (faster than WebSocket)"""
#     # Similar to your camera_test_server.py
#     pass


def get_robot_port() -> int:
    """
    Determine which port to use based on hostname.
    
    Returns:
        8080 for Storm (f7), 8081 for Necron (m7), 8080 default
    """
    try:
        hostname = socket.gethostname().lower()
        logger.info(f"Detected hostname: {hostname}")
        
        # Storm uses port 8080
        if 'f7' in hostname:
            logger.info("Detected Storm robot (f7) - using port 8080")
            return 8080
        
        # Necron uses port 8081
        elif 'm7' in hostname:
            logger.info("Detected Necron robot (m7) - using port 8081")
            return 8081
        
        # Default to 8080
        else:
            logger.warning(f"Unknown hostname '{hostname}' - defaulting to port 8080")
            return 8080
            
    except Exception as e:
        logger.error(f"Failed to detect hostname: {e} - defaulting to port 8080")
        return 8080


def main():
    """Run the interface server"""
    import uvicorn
    
    # Determine port based on robot hostname
    port = get_robot_port()
    
    logger.info("Starting Robot Interface Server")
    logger.info(f"Dashboard: http://0.0.0.0:{port}")
    logger.info(f"WebSocket: ws://0.0.0.0:{port}/ws")
    
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=port,
        log_level='info'
    )


if __name__ == '__main__':
    main()
