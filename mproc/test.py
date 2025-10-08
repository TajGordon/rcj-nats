# ...existing code...
from multiprocessing import Process, Queue, Event
import threading
import matplotlib.pyplot as plt
import time
import cv2

class CamWorker:
    def __init__(self, cmd_q, out_q):
        # ...existing code...
        self.cmd_q = cmd_q
        self.out_q = out_q
        self.cam = cv2.VideoCapture()
        self.cam_on = False

    def start(self, stop_evt: Event = None):
        running = True
        while running:
            # check stop event for graceful shutdown (if provided)
            if stop_evt and stop_evt.is_set():
                break

            while not self.cmd_q.empty():
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
                    # Put frames into output queue (avoid blocking forever)
                    try:
                        self.out_q.put(frame, block=False)
                    except:
                        pass
                else:
                    print("Failed to read frame from camera")
            time.sleep(0.05)  # camera loop cadence

# lightweight localization worker stub (replace with your real one)
def localization_worker(cmd_q: Queue, out_q: Queue, stop_evt: Event):
    """
    Run localization loop in a separate process.
    Replace body with your real localization initialization and loop
    (e.g. create Localizer and call .localize()).
    """
    import time, math
    while not stop_evt.is_set():
        # simulated localization result
        pos = (math.cos(time.time()), math.sin(time.time()))
        out_q.put({'pos': pos, 'ts': time.time()})
        time.sleep(0.1)  # 10 Hz

def button_poller(stop_evt: threading.Event, button_queue: Queue):
    """Thread: poll buttons periodically and push events to button_queue"""
    try:
        # import your Button class (works in main process)
        from buttons.button import Button
        import board
        # Example: create physical button(s)
        btn = Button(board.D13, name="btn1")
    except Exception:
        btn = None
        print("Button init failed; running in simulated mode")

    while not stop_evt.is_set():
        if btn and btn.is_pressed():
            button_queue.put(("pressed", time.time()))
        time.sleep(0.05)

def main():
    # Queues & events for inter-process comms and shutdown
    cam_cmd_q, cam_out_q = Queue(), Queue()
    loc_cmd_q, loc_out_q = Queue(), Queue()
    stop_event = Event()
    button_q = Queue()

    # Camera process
    cam_worker = CamWorker(cam_cmd_q, cam_out_q)
    cam_proc = Process(target=cam_worker.start, args=(stop_event,))
    cam_proc.start()
    cam_cmd_q.put("start")

    # Localization process (example stub)
    loc_proc = Process(target=localization_worker, args=(loc_cmd_q, loc_out_q, stop_event))
    loc_proc.start()

    # Button poller thread
    btn_stop = threading.Event()
    btn_thread = threading.Thread(target=button_poller, args=(btn_stop, button_q), daemon=True)
    btn_thread.start()

    try:
        while True:
            # handle camera frames (non-blocking)
            while not cam_out_q.empty():
                frame = cam_out_q.get()
                plt.imshow(frame[..., ::-1])  # cv2 BGR->RGB for matplotlib
                plt.pause(0.001)  # non-blocking show

            # handle localization updates
            while not loc_out_q.empty():
                data = loc_out_q.get()
                # process localization data (e.g. update UI, send to server)
                print("LOC:", data)

            # handle button events
            while not button_q.empty():
                evt = button_q.get()
                print("BUTTON:", evt)
                # e.g. toggle camera on/off
                if evt[0] == "pressed":
                    cam_cmd_q.put("pause")

            time.sleep(0.02)

    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        # signal processes/threads to stop
        stop_event.set()
        btn_stop.set()

        # send explicit stop to camera loop if needed
        cam_cmd_q.put("stop")
        loc_cmd_q.put("stop")

        # join processes
        cam_proc.join(timeout=2)
        if cam_proc.is_alive():
            cam_proc.terminate()

        loc_proc.join(timeout=2)
        if loc_proc.is_alive():
            loc_proc.terminate()

        # cleanup local OpenCV capture if we have it in this process (defensive)
        try:
            cam_worker.cam.release()
        except:
            pass

if __name__ == "__main__":
    main()
# ...existing code...