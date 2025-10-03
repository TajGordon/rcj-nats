from fastapi.responses import StreamingResponse
from picamera2 import Picamera2
import cv2
import asyncio
from fastapi import FastAPI, WebSocket
import uvicorn

class Camera:
    def __init__(self):
        self.picam = Picamera2()
        self.picam.configure(self.picam.create_video_configuration(
            main={"format": "RGB888"}
        ))
        self.picam.start()
    
    def get_frame(self):
        frame = self.picam.capture_array()
        ret, jpg = cv2.imencode('.jpg', frame)
        return jpg.tobytes()
    
    async def streamer(self):
        while True:
            frame = self.get_frame()
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
            await asyncio.sleep(0.05) # set the fps


app = FastAPI()

cam = Camera()

@app.get('/')
async def video_stream():
    return StreamingResponse(cam.streamer(), media_type="multipart/x-mixed-replace; boundary=frame")
