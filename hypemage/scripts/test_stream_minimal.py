"""
Minimal camera stream test - Shows exactly what's happening
Run this to debug camera stream issues
"""
import asyncio
from aiohttp import web
import cv2
import numpy as np
import time
import socket
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from camera import CameraProcess
from config import get_robot_id

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def get_debug_port():
    """Determine debug port based on robot"""
    hostname = socket.gethostname().lower()
    if 'f7' in hostname:
        return 8765  # Storm
    elif 'm7' in hostname:
        return 8766  # Necron
    else:
        return 8765  # Default

class SimpleStreamer:
    def __init__(self):
        self.robot_id = get_robot_id()
        self.camera = None
        self.frame_count = 0
        
    async def stream_handler(self, request):
        """Minimal MJPEG stream handler with debug output"""
        log(f"Client connected from {request.remote}")
        
        response = web.StreamResponse()
        response.content_type = 'multipart/x-mixed-replace; boundary=frame'
        await response.prepare(request)
        
        try:
            while True:
                # Capture frame
                frame = self.camera.capture_frame()
                
                if frame is None:
                    log("WARNING: Got None frame")
                    await asyncio.sleep(0.1)
                    continue
                
                log(f"Frame {self.frame_count}: shape={frame.shape}, dtype={frame.dtype}")
                
                # Convert RGB to BGR for JPEG encoding
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                else:
                    bgr_frame = frame
                
                # Add simple text overlay to confirm it's working
                cv2.putText(bgr_frame, f"Frame: {self.frame_count}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(bgr_frame, f"Robot: {self.robot_id}", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # Encode to JPEG
                success, buffer = cv2.imencode('.jpg', bgr_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                
                if not success:
                    log("ERROR: Failed to encode frame")
                    await asyncio.sleep(0.1)
                    continue
                
                log(f"Encoded JPEG size: {len(buffer)} bytes")
                
                # Send frame
                try:
                    await response.write(
                        b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' +
                        buffer.tobytes() +
                        b'\r\n'
                    )
                    log(f"Sent frame {self.frame_count}")
                except Exception as e:
                    log(f"ERROR sending frame: {e}")
                    break
                
                self.frame_count += 1
                await asyncio.sleep(1/10)  # 10 FPS for easier debugging
                
        except Exception as e:
            log(f"Stream ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            log("Client disconnected")
        
        return response
    
    async def test_handler(self, request):
        """Simple test page"""
        html = f"""
        <html>
        <head>
            <title>Minimal Camera Test - {self.robot_id}</title>
            <style>
                body {{ font-family: monospace; background: #222; color: #0f0; padding: 20px; }}
                img {{ border: 2px solid #0f0; }}
                .info {{ background: #333; padding: 10px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <h1>Minimal Camera Stream Test</h1>
            <div class="info">
                <div>Robot: {self.robot_id}</div>
                <div>Port: {request.host}</div>
                <div>Time: {time.strftime('%H:%M:%S')}</div>
            </div>
            <img src="/stream" width="640" height="480">
            <div class="info">
                Stream URL: <code>http://{request.host}/stream</code>
            </div>
            <div class="info">
                If you see a green frame counter, the stream is working!
            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

async def main():
    port = get_debug_port()
    robot_id = get_robot_id()
    
    log("=" * 60)
    log("MINIMAL CAMERA STREAM TEST")
    log("=" * 60)
    log(f"Robot ID: {robot_id}")
    log(f"Port: {port}")
    
    streamer = SimpleStreamer()
    
    # Initialize camera
    log("Initializing camera...")
    try:
        streamer.camera = CameraProcess(robot_id=robot_id)
        log("✓ Camera initialized")
    except Exception as e:
        log(f"✗ FAILED to initialize camera: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test capture
    log("Testing frame capture...")
    try:
        test_frame = streamer.camera.capture_frame()
        if test_frame is None:
            log("✗ Got None frame - camera not working!")
            return
        log(f"✓ Test frame: shape={test_frame.shape}, dtype={test_frame.dtype}")
    except Exception as e:
        log(f"✗ Frame capture failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Create web app
    log("Starting HTTP server...")
    app = web.Application()
    app.router.add_get('/', streamer.test_handler)
    app.router.add_get('/stream', streamer.stream_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    log("=" * 60)
    log("✓ SERVER RUNNING")
    log("=" * 60)
    log(f"Test page: http://m7.local:{port}/")
    log(f"Stream URL: http://m7.local:{port}/stream")
    log("")
    log("Watch the log output when you connect...")
    log("Press Ctrl+C to stop")
    log("=" * 60)
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        log("Shutting down...")
    finally:
        await runner.cleanup()
        if streamer.camera:
            streamer.camera.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
