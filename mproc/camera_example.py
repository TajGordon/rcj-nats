"""
Simple example showing how to combine multiprocessing (camera reader)
with a thread (keyboard button poller) and render frames in the main process.

Usage (Windows):
  python mproc/camera_example.py

Controls:
  - Press 'e' in the console to toggle camera pause/resume
  - Press 'q' in the console to quit the program

Notes:
  - The camera runs in a separate process to avoid GIL issues and allow
    heavy processing without blocking the main loop.
  - The button poller runs as a thread in the main process and uses
    msvcrt.kbhit()/getwch() on Windows to do non-blocking key reads.
  - Frames are transferred over a multiprocessing.Queue (simple/pickle-based).
    For high-throughput production use shared_memory, zmq, or a ring buffer.
"""

import multiprocessing
import threading
import time
import cv2
from queue import Empty
import numpy as np
import queue


def camera_process(cmd_q, out_q, stop_evt):
    """Camera reading loop that runs in a child process.

    It responds to simple text commands from cmd_q: 'start', 'pause', 'stop', 'resume'.
    Frames are placed onto out_q when available.
    """
    cap = cv2.VideoCapture(0)
    cam_on = False
    try:
        while not stop_evt.is_set():
            # handle commands if any
            try:
                cmd = cmd_q.get_nowait()
            except Empty:
                cmd = None

            if cmd:
                if cmd == "start":
                    if not cap.isOpened():
                        cap.open(0)
                    cam_on = True
                elif cmd in ("pause", "stop"):
                    cam_on = False
                elif cmd == "resume":
                    cam_on = True

            if cam_on and cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    # non-blocking put; if queue is full just drop the frame
                    try:
                        out_q.put(frame, block=False)
                    except Exception:
                        # queue full or other issue - drop frame
                        pass
                else:
                    # temporary failure reading frame
                    time.sleep(0.01)

            # small sleep so loop isn't a tight CPU hog
            time.sleep(0.01)
    finally:
        try:
            cap.release()
        except Exception:
            pass


def button_poller(stop_evt, button_q):
    """Thread that polls for keyboard keys non-blocking and sends events.

    On Windows we use msvcrt.kbhit()/getwch(). On other platforms it falls
    back to a blocking input() (not ideal) — this example assumes Windows.
    """
    try:
        import msvcrt
    except Exception:
        msvcrt = None

    print("Button poller started. Press 'e' to toggle camera, 'q' to quit.")
    while not stop_evt.is_set():
        if msvcrt:
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                if not ch:
                    continue
                ch = ch.lower()
                if ch == 'q':
                    button_q.put(("quit", time.time()))
                elif ch == 'e':
                    button_q.put(("toggle", time.time()))
        else:
            # Fallback (blocking) for non-windows; not ideal for real apps
            try:
                line = input()
            except Exception:
                line = ''
            if line.lower().strip() == 'q':
                button_q.put(("quit", time.time()))
            elif line.lower().strip() == 'e':
                button_q.put(("toggle", time.time()))

        time.sleep(0.03)


def main():
    # Use multiprocessing context explicitly on Windows if desired
    ctx = multiprocessing.get_context()

    cam_cmd_q = ctx.Queue(maxsize=4)
    cam_out_q = ctx.Queue(maxsize=2)
    stop_event = ctx.Event()

    button_q = queue.Queue()
    btn_stop = threading.Event()

    # start camera process
    cam_proc = ctx.Process(target=camera_process, args=(cam_cmd_q, cam_out_q, stop_event))
    cam_proc.start()

    # tell camera to start
    cam_cmd_q.put("start")
    cam_paused = False

    # start button poller thread
    btn_thread = threading.Thread(target=button_poller, args=(btn_stop, button_q), daemon=True)
    btn_thread.start()

    last_frame = None
    running = True
    try:
        while running:
            # process button events
            try:
                while True:
                    evt = button_q.get_nowait()
                    name, ts = evt
                    print(f"Button event: {name} @ {ts}")
                    if name == 'quit':
                        running = False
                        break
                    elif name == 'toggle':
                        cam_paused = not cam_paused
                        cam_cmd_q.put('pause' if cam_paused else 'resume')
            except Empty:
                pass

            # get latest frame (drain queue and keep last)
            try:
                while True:
                    frame = cam_out_q.get_nowait()
                    last_frame = frame
            except Empty:
                pass

            if last_frame is not None:
                # OpenCV expects BGR already; display it
                cv2.imshow('Camera (press Q in console to quit)', last_frame)
            else:
                # show an empty black image so window exists immediately
                black = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.imshow('Camera (press Q in console to quit)', black)

            # keep window responsive; small wait
            # (we don't use the return value here because console keys are read by msvcrt)
            if cv2.waitKey(1) & 0xFF == 27:
                # ESC pressed in the OpenCV window -> exit
                running = False

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("KeyboardInterrupt - shutting down")
        running = False
    finally:
        # signal stop to child and thread
        stop_event.set()
        btn_stop.set()

        # ask camera process to stop (also handled by stop_event)
        try:
            cam_cmd_q.put('stop')
        except Exception:
            pass

        # join
        cam_proc.join(timeout=2)
        if cam_proc.is_alive():
            cam_proc.terminate()

        # cleanup OpenCV windows
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass


if __name__ == '__main__':
    main()
