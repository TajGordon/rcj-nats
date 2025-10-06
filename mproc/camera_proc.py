import cv2
import time
from multiprocessing import Queue

class CameraProc:
    def __init__(self, in_q: Queue, out_q: Queue):
        self.in_q = in_q
        self.out_q = out_q
        self.cam_on = True
        self.cam = None  # Will be initialized in start()
    
    def start(self):
        # Initialize camera in the child process to avoid pickling issues
        print("Initializing camera...")
        self.cam = cv2.VideoCapture(0)
        if not self.cam.isOpened():
            print("ERROR: Could not open camera!")
            return
        else:
            print("Camera opened successfully!")
        
        running = True
        frame_count = 0
        while running:
            try:
                cmd = self.in_q.get_nowait()
                if cmd == "stop":
                    running = False
                    break
                elif cmd == "start":
                    self.cam_on = True
                elif cmd == "pause":
                    self.cam_on = False
            except:
                pass

            if self.cam_on and self.cam is not None:
                ret, frame = self.cam.read()
                if ret:
                    frame_count += 1
                    if frame_count % 10 == 0:  # Print every 10 frames
                        print(f"Captured frame #{frame_count}")
                    self.out_q.put(frame)
                else:
                    print("Failed to read frame from camera")

            time.sleep(0.1)
        
        # Clean up camera when stopping
        if self.cam is not None:
            self.cam.release()