"""
Simple Camera Streamer - Streams raw camera feed to web dashboard

Captures camera frames and sends them to the debug manager for display.
No detection overlays - just the raw camera feed.

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
from pathlib import Path

from hypemage.camera import CameraProcess
from hypemage.config import get_robot_id
from hypemage.logger import get_logger

logger = get_logger(__name__)


async def camera_stream_handler(websocket):
    """Handle WebSocket client and stream camera frames"""
    client_addr = websocket.remote_address
    logger.info(f"Camera stream client connected: {client_addr}")
    
    robot_id = get_robot_id()
    camera = None
    
    try:
        camera = CameraProcess(robot_id=robot_id)
        logger.info(f"Camera initialized for {robot_id}")
        
        frame_count = 0
        while True:
            start_time = time.time()
            
            # Capture frame
            frame = camera.capture_frame()
            if frame is None:
                await asyncio.sleep(0.1)
                continue
            
            # Encode to JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_b64 = base64.b64encode(buffer).decode('ascii')
            
            # Send to client
            message = {
                'type': 'update',
                'subsystem': 'camera',
                'data': {
                    'frame_jpeg': frame_b64,
                    'fps': int(1.0 / (time.time() - start_time)) if frame_count > 0 else 0,
                    'frame_id': frame_count
                }
            }
            
            await websocket.send(json.dumps(message))
            frame_count += 1
            
            # Limit to ~30 FPS
            elapsed = time.time() - start_time
            if elapsed < 0.033:
                await asyncio.sleep(0.033 - elapsed)
                
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Camera stream client disconnected: {client_addr}")
    except Exception as e:
        logger.error(f"Camera stream error: {e}", exc_info=True)
    finally:
        if camera:
            del camera


def get_robot_port() -> int:
    """Determine debug port based on robot"""
    hostname = socket.gethostname().lower()
    if 'f7' in hostname:
        return 8765  # Storm
    elif 'm7' in hostname:
        return 8766  # Necron
    else:
        return 8765  # Default


async def main():
    """Run the camera stream server"""
    port = get_robot_port()
    robot_id = get_robot_id()
    
    logger.info(f"Starting camera stream server for {robot_id}")
    logger.info(f"Camera stream: ws://0.0.0.0:{port}")
    
    async with websockets.serve(camera_stream_handler, "0.0.0.0", port):
        logger.info("Camera stream server running")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())
