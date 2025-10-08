from multiprocessing import Process, Queue, Event
import matplotlib.pyplot as plt
import time
import cv2

class CamWorker:
    def __init__(self, cmd_q, out_q):
        self.cam = cv2.VideoCapture()
        self.cam_on = False
        self.cmd_q = cmd_q
        self.out_q = out_q

    def start(self, stop_evt = None):
        running = True
        while running:
            while not self.cmd_q.empty():
                if stop_evt and stop_evt.is_set():
                    break
                cmd = self.cmd_q.get()
                if cmd == "stop":
                    running = False
                    break
                elif cmd == "start":
                    self.cam.open(0)
                    self.cam_on = True
                elif cmd == "pause":
                    self.cam_on = False
                
                if self.cam_on and self.cam.isOpened():
                    ret, frame = self.cam.read()
                    if ret:
                        self.out_q.put(frame)
                    else:
                        print("Failed to read frame from camera")
                time.sleep(0.1)

def main():
    cmd_q, out_q = Queue(), Queue()
    cam = CamWorker(cmd_q, out_q)
    proc = Process(target=cam.start)
    proc.start()
    cmd_q.put("start")
    while True:
        while not out_q.empty():
            frame = out_q.get()
            plt.imshow(frame)
            plt.show()
        time.sleep(0.05)
    proc.join()
    cam.cam.release()
        



if __name__ == "__main__":
    main()