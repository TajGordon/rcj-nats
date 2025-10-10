"""
Standalone Camera Streamer with Debug Overlays

This creates an HTTP server that streams MJPEG video with detection overlays to the dashboard.
Runs ball and goal detection on each frame and draws debug info (bounding boxes, labels, frame ID).

Usage:
    python -m hypemage.scripts.camera_stream
"""

import asyncio
from aiohttp import web
import cv2
import numpy as np
import time
import socket
import sys

from hypemage.camera import CameraProcess, add_debug_overlays, VisionData, BallDetectionResult, GoalDetectionResult
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
        self.camera: CameraProcess | None = None
        
    async def mjpeg_handler(self, request):
        """Handle MJPEG stream requests"""
        log(f"Client connected: {request.remote}")
        
        response = web.StreamResponse()
        response.content_type = 'multipart/x-mixed-replace; boundary=frame'
        await response.prepare(request)
        
        try:
            frame_count = 0
            while True:
                start_time = time.time()
                
                # Capture frame from camera
                try:
                    frame = self.camera.capture_frame()
                except Exception as e:
                    log(f"ERROR capturing frame: {e}")
                    await asyncio.sleep(0.1)
                    continue
                
                if frame is None:
                    await asyncio.sleep(0.1)
                    continue
                
                # Validate frame
                if not isinstance(frame, np.ndarray) or frame.size == 0:
                    log(f"WARNING: Invalid frame type or empty frame")
                    await asyncio.sleep(0.1)
                    continue
                
                try:
                    # Run detections (detections expect BGR input from Picamera2)
                    ball = self.camera.detect_ball(frame)
                    blue_goal, yellow_goal = self.camera.detect_goals(frame)
                    
                    # Build vision data object
                    vision_data = VisionData(
                        timestamp=time.time(),
                        frame_id=frame_count,
                        raw_frame=frame,
                        ball=ball,
                        blue_goal=blue_goal,
                        yellow_goal=yellow_goal
                    )
                    
                    # Add debug overlays safely
                    # add_debug_overlays expects BGR and returns BGR
                    debug_frame = add_debug_overlays(frame, vision_data)
                    
                except Exception as e:
                    log(f"ERROR in detection/overlay: {e}")
                    import traceback
                    traceback.print_exc()
                    # Fall back to plain frame
                    # Frame is already in BGR format from Picamera2
                    debug_frame = frame.copy()
                
                try:
                    # Encode to JPEG (expects BGR)
                    _, buffer = cv2.imencode('.jpg', debug_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    
                    # Send as multipart
                    await response.write(
                        b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + 
                        buffer.tobytes() + 
                        b'\r\n'
                    )
                except Exception as e:
                    log(f"ERROR encoding/sending frame: {e}")
                    await asyncio.sleep(0.1)
                    continue
                
                frame_count += 1
                if frame_count % 100 == 0:
                    fps = int(1.0 / max(time.time() - start_time, 0.001))
                    try:
                        detections = []
                        if vision_data.ball.detected:
                            detections.append(f"ball@({vision_data.ball.center_x},{vision_data.ball.center_y})")
                        if vision_data.blue_goal.detected:
                            detections.append(f"blue_goal")
                        if vision_data.yellow_goal.detected:
                            detections.append(f"yellow_goal")
                        det_str = ", ".join(detections) if detections else "no detections"
                        log(f"Streamed {frame_count} frames (~{fps} FPS) - {det_str}")
                    except:
                        log(f"Streamed {frame_count} frames (~{fps} FPS)")
                
                # Limit to ~30 FPS
                elapsed = time.time() - start_time
                if elapsed < 0.033:
                    await asyncio.sleep(0.033 - elapsed)
                    
        except asyncio.CancelledError:
            log(f"Client disconnected: {request.remote}")
        except Exception as e:
            log(f"ERROR in stream: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await response.write_eof()
        
        return response
    
    async def index_handler(self, request):
        """Simple test page"""
        html = f"""
        <html>
        <head><title>Camera Stream - {self.robot_id}</title></head>
        <body>
            <h1>Camera Stream - {self.robot_id.upper()}</h1>
            <img src="/stream" width="640" height="480">
            <p>Stream URL: <code>http://{request.host}/stream</code></p>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')


async def main():
    """Run the camera stream server"""
    port = get_debug_port()
    robot_id = get_robot_id()
    
    log(f"Starting camera stream HTTP server for {robot_id}")
    log(f"HTTP server: http://0.0.0.0:{port}")
    
    streamer = CameraStreamer()
    
    # Initialize camera
    try:
        streamer.camera = CameraProcess(robot_id=robot_id)
        log("Camera initialized")
    except Exception as e:
        log(f"ERROR: Failed to initialize camera: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Create HTTP app
    app = web.Application()
    app.router.add_get('/', streamer.index_handler)
    app.router.add_get('/stream', streamer.mjpeg_handler)
    
    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    log(f"HTTP server started on port {port}")
    log(f"Stream URL: http://0.0.0.0:{port}/stream")
    
    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        log("Shutting down...")
    finally:
        await runner.cleanup()
        if streamer.camera:
            del streamer.camera


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
