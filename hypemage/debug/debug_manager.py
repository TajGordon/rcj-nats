"""
Debug Manager Process

Collects debug data from all robot subsystems and serves it via WebSocket.
Only runs when robot is started with --debug flag.

Usage:
    This is started automatically by scylla.py when --debug flag is set.
    Clients connect to ws://robot:8765 to receive debug data.
"""

import asyncio
import websockets
import json
import base64
import queue
import time
from typing import Dict, Any, Set
from dataclasses import asdict

from hypemage.logger import get_logger

logger = get_logger(__name__)


class DebugManager:
    """
    Collects debug data from all processes and serves via WebSocket
    """
    
    def __init__(self, debug_queues: Dict[str, Any]):
        """
        Args:
            debug_queues: Dict of {subsystem: queue} for debug data
                         e.g., {'camera': Queue(), 'motors': Queue()}
        """
        self.debug_queues = debug_queues
        self.ws_clients: Set[Any] = set()
        
        # Latest data (sent to new clients when they connect)
        self.latest_data = {
            'camera': None,
            'motors': None,
            'localization': None,
            'buttons': None,
            'fsm': None
        }
        
        self.running = True
        logger.info("Debug manager initialized")
    
    async def handle_client(self, websocket, path):
        """Handle WebSocket client connection"""
        client_addr = websocket.remote_address
        logger.info(f"Debug client connected: {client_addr}")
        self.ws_clients.add(websocket)
        
        try:
            # Send initial state to new client
            await websocket.send(json.dumps({
                'type': 'init',
                'data': self._serialize_latest_data()
            }))
            
            # Listen for client messages (future: could add commands)
            async for message in websocket:
                logger.debug(f"Received from client: {message}")
                # Future: handle client commands (e.g., change debug level)
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Debug client disconnected: {client_addr}")
        except Exception as e:
            logger.error(f"Error handling client {client_addr}: {e}")
        finally:
            self.ws_clients.remove(websocket)
    
    def _serialize_latest_data(self):
        """Convert latest data to JSON-serializable format"""
        result = {}
        for subsystem, data in self.latest_data.items():
            if data is not None:
                result[subsystem] = self._serialize_data(data)
        return result
    
    def _serialize_data(self, data):
        """Serialize dataclass to dict, handle bytes (JPEG frames)"""
        result = asdict(data)
        
        # Convert bytes to base64 for JSON transmission
        if 'frame_jpeg' in result and result['frame_jpeg']:
            result['frame_jpeg'] = base64.b64encode(result['frame_jpeg']).decode('ascii')
        
        return result
    
    async def collect_and_broadcast(self):
        """Main loop: collect from queues, broadcast to clients"""
        logger.info("Debug data collection started")
        
        while self.running:
            # Collect from all debug queues
            for subsystem, debug_q in self.debug_queues.items():
                if debug_q is None:
                    continue
                
                try:
                    # Get all available data (non-blocking)
                    while True:
                        data = debug_q.get_nowait()
                        self.latest_data[subsystem] = data
                        
                        # Broadcast to all connected clients
                        if self.ws_clients:
                            message = {
                                'type': 'update',
                                'subsystem': subsystem,
                                'data': self._serialize_data(data)
                            }
                            await self._broadcast(message)
                
                except queue.Empty:
                    pass  # No data available
                except Exception as e:
                    logger.error(f"Error collecting from {subsystem}: {e}")
            
            await asyncio.sleep(0.01)  # 100Hz check rate
    
    async def _broadcast(self, message):
        """Send message to all connected WebSocket clients"""
        if not self.ws_clients:
            return
        
        json_msg = json.dumps(message)
        
        # Send to all clients, handle disconnects gracefully
        disconnected = set()
        for client in self.ws_clients:
            try:
                await client.send(json_msg)
            except Exception:
                disconnected.add(client)
        
        # Remove disconnected clients
        self.ws_clients -= disconnected
    
    async def run(self, host='0.0.0.0', port=8765):
        """Start WebSocket server and data collection"""
        logger.info(f"Starting debug WebSocket server on {host}:{port}")
        
        # Start WebSocket server
        async with websockets.serve(self.handle_client, host, port):
            logger.info(f"Debug server listening on ws://{host}:{port}")
            logger.info(f"Clients can connect to view debug data")
            
            # Run collection loop
            await self.collect_and_broadcast()


def debug_manager_start(debug_queues, stop_evt):
    """
    Entry point for debug manager process
    
    Args:
        debug_queues: Dict of subsystem debug queues
        stop_evt: Multiprocessing Event to signal shutdown
    """
    logger = get_logger(__name__)
    logger.info("Debug manager process starting...")
    
    manager = DebugManager(debug_queues)
    
    # Run async event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(manager.run())
    except KeyboardInterrupt:
        logger.info("Debug manager stopped by user")
    except Exception as e:
        logger.error(f"Debug manager error: {e}", exc_info=True)
    finally:
        manager.running = False
        loop.close()
        logger.info("Debug manager stopped")
