"""
Interface Server

Central control point for managing robot processes and scripts.
Provides WebSocket interface for client apps to:
- Start/stop robot with different configurations
- Launch utility scripts (color calibration, motor tests, etc.)
- Monitor robot status and logs
- Forward debug data to clients

Usage:
    python -m hypemage.interface
    
    Then connect client to:
    - WebSocket: ws://robot:8080 (for commands and status)
    - HTTP: http://robot:8080 (serves client web UI)
"""

import asyncio
import websockets
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Set
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

from hypemage.logger import get_logger

logger = get_logger(__name__)


class InterfaceServer:
    """
    Manages robot processes and provides command interface
    """
    
    def __init__(self):
        # Command handlers (easily extensible)
        self.commands = {
            'scylla_debug': self._scylla_debug,
            'scylla_production': self._scylla_production,
            'stop_robot': self._stop_robot,
            'get_status': self._get_status,
            'color_calibration': self._color_calibration,
            'motor_test': self._motor_test,
            'get_logs': self._get_logs,
        }
        
        # Active processes
        self.robot_process: Optional[subprocess.Popen] = None
        self.utility_process: Optional[subprocess.Popen] = None
        
        # WebSocket clients
        self.ws_clients: Set[Any] = set()
        
        # Status
        self.robot_running = False
        self.debug_enabled = False
        
        # Monitor thread
        self.monitor_thread = None
        self.running = True
        
        logger.info("Interface server initialized")
    
    # ========== Command Handlers ==========
    
    def _scylla_debug(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Start robot with debug enabled"""
        if self.robot_running:
            return {'success': False, 'error': 'Robot already running'}
        
        try:
            logger.info("Starting robot in DEBUG mode...")
            
            # Build command
            cmd = [sys.executable, '-m', 'hypemage.scylla', '--debug']
            
            # Add config if provided
            if 'config' in args:
                cmd.extend(['--config', args['config']])
            
            # Start process
            self.robot_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.robot_running = True
            self.debug_enabled = True
            
            # Start monitoring
            if self.monitor_thread is None or not self.monitor_thread.is_alive():
                self.monitor_thread = threading.Thread(target=self._monitor_robot, daemon=True)
                self.monitor_thread.start()
            
            logger.info(f"Robot started in DEBUG mode (PID: {self.robot_process.pid})")
            
            return {
                'success': True,
                'pid': self.robot_process.pid,
                'debug_enabled': True,
                'message': 'Robot started in debug mode. Connect to ws://robot:8765 for debug data.'
            }
        
        except Exception as e:
            logger.error(f"Failed to start robot: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _scylla_production(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Start robot without debug (production mode)"""
        if self.robot_running:
            return {'success': False, 'error': 'Robot already running'}
        
        try:
            logger.info("Starting robot in PRODUCTION mode...")
            
            # Build command (no --debug flag)
            cmd = [sys.executable, '-m', 'hypemage.scylla']
            
            if 'config' in args:
                cmd.extend(['--config', args['config']])
            
            # Start process
            self.robot_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.robot_running = True
            self.debug_enabled = False
            
            # Start monitoring
            if self.monitor_thread is None or not self.monitor_thread.is_alive():
                self.monitor_thread = threading.Thread(target=self._monitor_robot, daemon=True)
                self.monitor_thread.start()
            
            logger.info(f"Robot started in PRODUCTION mode (PID: {self.robot_process.pid})")
            
            return {
                'success': True,
                'pid': self.robot_process.pid,
                'debug_enabled': False,
                'message': 'Robot started in production mode'
            }
        
        except Exception as e:
            logger.error(f"Failed to start robot: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _stop_robot(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Stop robot gracefully"""
        if not self.robot_running or self.robot_process is None:
            return {'success': False, 'error': 'Robot not running'}
        
        try:
            logger.info(f"Stopping robot (PID: {self.robot_process.pid})...")
            
            # Send SIGTERM for graceful shutdown
            self.robot_process.terminate()
            
            # Wait up to 5 seconds
            try:
                self.robot_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Robot didn't stop gracefully, force killing...")
                self.robot_process.kill()
                self.robot_process.wait()
            
            exit_code = self.robot_process.returncode
            self.robot_process = None
            self.robot_running = False
            self.debug_enabled = False
            
            logger.info(f"Robot stopped (exit code: {exit_code})")
            
            return {
                'success': True,
                'exit_code': exit_code,
                'message': 'Robot stopped'
            }
        
        except Exception as e:
            logger.error(f"Error stopping robot: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _get_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get current robot status"""
        status = {
            'robot_running': self.robot_running,
            'debug_enabled': self.debug_enabled,
            'pid': self.robot_process.pid if self.robot_process else None,
            'utility_running': self.utility_process is not None and self.utility_process.poll() is None
        }
        
        return {'success': True, 'status': status}
    
    def _color_calibration(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Launch color calibration tool"""
        if self.utility_process and self.utility_process.poll() is None:
            return {'success': False, 'error': 'Utility already running'}
        
        try:
            target = args.get('target', 'ball')
            logger.info(f"Starting color calibration for {target}...")
            
            cmd = [sys.executable, '-m', 'hypemage.debug.color_calibration', '--target', target]
            
            self.utility_process = subprocess.Popen(cmd)
            
            return {
                'success': True,
                'pid': self.utility_process.pid,
                'message': f'Color calibration started for {target}'
            }
        
        except Exception as e:
            logger.error(f"Failed to start color calibration: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _motor_test(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Launch motor test script"""
        if self.utility_process and self.utility_process.poll() is None:
            return {'success': False, 'error': 'Utility already running'}
        
        try:
            logger.info("Starting motor test...")
            
            cmd = [sys.executable, '-m', 'motors.motor']
            
            self.utility_process = subprocess.Popen(cmd)
            
            return {
                'success': True,
                'pid': self.utility_process.pid,
                'message': 'Motor test started'
            }
        
        except Exception as e:
            logger.error(f"Failed to start motor test: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _get_logs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get recent log entries"""
        try:
            log_file = Path.home() / 'robot_logs' / 'robot.log'
            
            if not log_file.exists():
                return {'success': True, 'logs': []}
            
            # Get last N lines (default 100)
            num_lines = args.get('lines', 100)
            
            with open(log_file, 'r') as f:
                lines = f.readlines()
                recent_lines = lines[-num_lines:]
            
            return {'success': True, 'logs': recent_lines}
        
        except Exception as e:
            logger.error(f"Failed to read logs: {e}")
            return {'success': False, 'error': str(e)}
    
    # ========== Process Monitoring ==========
    
    def _monitor_robot(self):
        """Monitor robot process and broadcast status changes"""
        logger.info("Process monitor started")
        
        while self.running and self.robot_process:
            # Check if process is still alive
            exit_code = self.robot_process.poll()
            
            if exit_code is not None:
                # Process exited
                logger.warning(f"Robot process exited with code {exit_code}")
                
                self.robot_running = False
                self.debug_enabled = False
                self.robot_process = None
                
                # Broadcast to clients
                asyncio.run(self._broadcast_status({
                    'type': 'robot_stopped',
                    'exit_code': exit_code,
                    'timestamp': time.time()
                }))
                
                break
            
            time.sleep(1)
        
        logger.info("Process monitor stopped")
    
    # ========== WebSocket Handling ==========
    
    async def handle_client(self, websocket, path):
        """Handle WebSocket client connection"""
        client_addr = websocket.remote_address
        logger.info(f"Client connected: {client_addr}")
        self.ws_clients.add(websocket)
        
        try:
            # Send initial status
            await websocket.send(json.dumps({
                'type': 'status',
                'data': (await self._handle_command({'command': 'get_status', 'args': {}}))
            }))
            
            # Handle client messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    response = await self._handle_command(data)
                    await websocket.send(json.dumps(response))
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        'success': False,
                        'error': 'Invalid JSON'
                    }))
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    await websocket.send(json.dumps({
                        'success': False,
                        'error': str(e)
                    }))
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_addr}")
        finally:
            self.ws_clients.remove(websocket)
    
    async def _handle_command(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch command to handler"""
        command = data.get('command')
        args = data.get('args', {})
        
        if not command:
            return {'success': False, 'error': 'No command specified'}
        
        if command in self.commands:
            # Run handler (in thread pool to avoid blocking)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.commands[command], args)
            return result
        else:
            return {'success': False, 'error': f'Unknown command: {command}'}
    
    async def _broadcast_status(self, message: Dict[str, Any]):
        """Broadcast status update to all clients"""
        if not self.ws_clients:
            return
        
        json_msg = json.dumps(message)
        
        disconnected = set()
        for client in self.ws_clients:
            try:
                await client.send(json_msg)
            except Exception:
                disconnected.add(client)
        
        self.ws_clients -= disconnected
    
    # ========== Server Run ==========
    
    async def run(self, host='0.0.0.0', port=8080):
        """Start interface server"""
        logger.info(f"Starting interface server on {host}:{port}")
        
        async with websockets.serve(self.handle_client, host, port):
            logger.info(f"Interface server listening on ws://{host}:{port}")
            logger.info("Clients can connect to control robot")
            
            # Keep running
            while self.running:
                await asyncio.sleep(1)
    
    def shutdown(self):
        """Shutdown server and stop robot"""
        logger.info("Shutting down interface server...")
        self.running = False
        
        if self.robot_process:
            logger.info("Stopping robot...")
            self._stop_robot({})


def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Robot Interface Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    
    args = parser.parse_args()
    
    server = InterfaceServer()
    
    try:
        asyncio.run(server.run(host=args.host, port=args.port))
    except KeyboardInterrupt:
        logger.info("Stopped by user")
        server.shutdown()
    except Exception as e:
        logger.critical(f"Server error: {e}", exc_info=True)
        server.shutdown()
        sys.exit(1)


if __name__ == '__main__':
    main()
