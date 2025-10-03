from picamera2 import Picamera2
import cv2

class Camera:
    def __init__(self, idx=0):
        self.idx = idx
        self.picam = Picamera2()
        self.picam.configure(self.picam.create_preview_configuration(main={"format": "RGB888"}))
        self.picam.start()
    def get_frame(self):
        return self.picam.capture_array()

if __name__ == "__main__":
    import asyncio
    from fastapi import FastAPI
    from fastapi.responses import StreamingResponse
    import uvicorn

    app = FastAPI()
    cam1 = Camera(idx=0)
    cam2 = Camera(idx=1)
    
    async def streamer(camera):
        while True:
            frame = camera.get_frame()
            ret, jpg = cv2.imencode('.jpg', frame)
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n")
            await asyncio.sleep(0.05) # set the fps
    
    def get_dual_streams():
        """Return a tuple of streaming responses for both cameras"""
        stream1 = StreamingResponse(streamer(cam1), media_type="multipart/x-mixed-replace; boundary=frame")
        stream2 = StreamingResponse(streamer(cam2), media_type="multipart/x-mixed-replace; boundary=frame")
        return (stream1, stream2)
    
    @app.get('/camera1')
    async def video_stream1():
        return StreamingResponse(streamer(cam1), media_type="multipart/x-mixed-replace; boundary=frame")
    
    @app.get('/camera2')
    async def video_stream2():
        return StreamingResponse(streamer(cam2), media_type="multipart/x-mixed-replace; boundary=frame")
    
    # Test the tuple function
    print("Testing dual camera streams:")
    streams_tuple = get_dual_streams()
    print(f"Returned tuple with {len(streams_tuple)} streaming responses")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
