"""
Simple Camera Streamer - Streams raw camera feed to web dashboard

This creates its own WebSocket server to stream camera directly to the dashboard.

Usage:
    python -m hypemage.scripts.camera_stream
"""

import asyncio
import websockets
import json
import base64
import cv2
import time
import socket
import sys

from hypemage.camera import CameraProcess
from hypemage.config import get_robot_id

# Use print for logging since it will be captured by interface.py
def log(msg):
    print(f"[camera_stream] {msg}", flush=True)


def get_debug_port() -> int:
    """Determine debug port based on robot"""
    hostname = socket.gethostname().lower()
    if 'f7' in hostname:
        return 8765  # Storm
    elif 'm7' in hostname:
        return 8766  # Necron
    else:
        return 8765  # Default


class CameraStreamer:
    def __init__(self):
        self.robot_id = get_robot_id()
        self.camera = None
        self.clients = set()
        
    async def handle_client(self, websocket):
        """Handle a WebSocket client connection"""
        client_addr = websocket.remote_address
        log(f"Client connected: {client_addr}")
        self.clients.add(websocket)
        
        try:
            # Keep connection alive and handle any messages
            async for message in websocket:
                pass  # Just keep connection open
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            log(f"Client disconnected: {client_addr}")
    
    async def stream_frames(self):
        """Continuously capture and broadcast frames"""
        try:
            self.camera = CameraProcess(robot_id=self.robot_id)
            log("Camera initialized")
            
            frame_count = 0
            while True:
                start_time = time.time()
                
                # Capture frame
                frame = self.camera.capture_frame()
                if frame is None:
                    await asyncio.sleep(0.1)
                    continue
                
                # Only encode if we have clients
                if not self.clients:
                    await asyncio.sleep(0.1)
                    continue
                
                # Encode to JPEG
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_b64 = base64.b64encode(buffer).decode('ascii')
                
                # Prepare message
                fps = int(1.0 / (time.time() - start_time)) if frame_count > 0 else 0
                message = json.dumps({
                    'type': 'update',
                    'subsystem': 'camera',
                    'data': {
                        'frame_jpeg': frame_b64,
                        'fps': fps,
                        'frame_id': frame_count
                    }
                })
                
                # Send to all clients
                disconnected = []
                for client in self.clients:
                    try:
                        await client.send(message)
                    except:
                        disconnected.append(client)
                
                # Remove disconnected clients
                for client in disconnected:
                    self.clients.discard(client)
                
                frame_count += 1
                if frame_count % 100 == 0:
                    log(f"Streamed {frame_count} frames to {len(self.clients)} clients")
                
                # Limit to ~30 FPS
                elapsed = time.time() - start_time
                if elapsed < 0.033:
                    await asyncio.sleep(0.033 - elapsed)
                    
        except Exception as e:
            log(f"ERROR in stream_frames: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if self.camera:
                del self.camera


async def main():
    """Run the camera stream server"""
    port = get_debug_port()
    robot_id = get_robot_id()
    
    log(f"Starting camera stream server for {robot_id}")
    log(f"WebSocket server: ws://0.0.0.0:{port}")
    
    streamer = CameraStreamer()
    
    # Start WebSocket server
    async with websockets.serve(streamer.handle_client, "0.0.0.0", port):
        log("WebSocket server started")
        
        # Start streaming task
        await streamer.stream_frames()


if __name__ == "__main__":
    log("Camera stream starting...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Camera stream stopped by user")
    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
