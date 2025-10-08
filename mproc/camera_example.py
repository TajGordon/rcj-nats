"""
Example: multiprocessing (camera + localizer) + threading (button poller + sensor threads).

Run on Windows. This file demonstrates three processes:
- Camera process: opens cv2.VideoCapture, reads frames, compresses them (JPEG) and puts bytes into a Queue.
- Localizer process: starts sensor-reading threads (simulated ToF and IMU) and consumes frames forwarded by the main process.
- Goal localizer: another process that could be started instead of the main localizer (only one should run at a time).

Main process:
- starts camera process and localizer (or goal_localizer)
- runs a keyboard poller thread (Q to quit, F to toggle forwarding frames to localizer)
- renders camera frames (decoding JPEG bytes) using OpenCV
- optionally forwards every Nth frame to the chosen localizer input queue

Design notes on camera -> localization data flow:
- Two patterns are common:
  1) Camera sends frames to a shared Queue that both the main process and localization process read from. This requires careful coordination (only one reader will get a frame) or using multiple output queues in the camera process.
  2) Camera sends frames to the main process; the main process decides which frames to forward to localization (shown here). This centralizes policy and lets the main UI/filter frames before forwarding.

This example implements option (2): camera->main, main forwards selected compressed frames to localizer. It's simple and avoids duplicating frames in multiple queues from the camera process.

This code is intentionally small/simulated for learning and testing.
"""

from multiprocessing import get_context
import multiprocessing as mp
import threading
import time
import cv2
import numpy as np
import sys

try:
    import msvcrt
    _HAS_MSVCRT = True
except Exception:
    _HAS_MSVCRT = False


def camera_process_main(cmd_q, out_q, stop_evt):
    """Camera capture loop that runs in a separate process.

    It listens to cmd_q for simple commands ('start','pause','stop') and pushes
    compressed JPEG bytes into out_q. Using JPEG keeps queues smaller.
    """
    cap = cv2.VideoCapture(0)
    cam_on = True

    # set a modest size to reduce data sent over Queue
    target_w, target_h = 320, 240

    try:
        while True:
            if stop_evt is not None and stop_evt.is_set():
                break

            # process commands if any
            while not cmd_q.empty():
                try:
                    cmd = cmd_q.get_nowait()
                except Exception:
                    break
                if cmd == "stop":
                    cam_on = False
                    break
                elif cmd == "start":
                    cam_on = True
                elif cmd == "pause":
                    cam_on = False

            if cam_on and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    # tiny sleep to avoid hot loop on camera failure
                    time.sleep(0.05)
                    continue

                # resize and compress
                frame_small = cv2.resize(frame, (target_w, target_h))
                ok, jpg = cv2.imencode('.jpg', frame_small, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                if ok:
                    try:
                        out_q.put(jpg.tobytes(), block=False)
                    except Exception:
                        # queue full or broken pipe: drop frame
                        pass

            else:
                time.sleep(0.05)

    finally:
        try:
            cap.release()
        except Exception:
            pass


def localizer_process_main(cmd_q, cam_in_q, out_q, stop_evt):
    """Localizer running in its own process. Starts internal threads for sensors.

    cam_in_q: Queue where main process forwards frames for localization.
    """
    import math

    # internal thread-safe storage for sensor values
    sensor_state = {
        'tof': None,
        'imu': None,
    }

    def tof_thread():
        # Simulate ToF sensor sampling at 10 Hz
        while not stop_evt.is_set():
            # put simulated distance
            sensor_state['tof'] = (time.time(), 123 + int(10 * (0.5 - time.time() % 1)))
            time.sleep(0.1)

    def imu_thread():
        # Simulate IMU sampling at 50 Hz
        while not stop_evt.is_set():
            sensor_state['imu'] = (time.time(), math.sin(time.time()))
            time.sleep(0.02)

    # start sensor threads
    t1 = threading.Thread(target=tof_thread, daemon=True)
    t2 = threading.Thread(target=imu_thread, daemon=True)
    t1.start()
    t2.start()

    try:
        while not stop_evt.is_set():
            # consume commands
            while not cmd_q.empty():
                try:
                    c = cmd_q.get_nowait()
                except Exception:
                    break
                if c == 'stop':
                    stop_evt.set()

            # process forwarded camera frames (if any)
            try:
                frame_bytes = cam_in_q.get(timeout=0.05)
            except Exception:
                frame_bytes = None

            if frame_bytes is not None:
                # decode and run a trivial detection (here: compute mean color)
                nparr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    mean = frame.mean(axis=(0, 1))
                    out_q.put({'ts': time.time(), 'mean_color': mean.tolist(), 'sensors': sensor_state.copy()})

            # idle small sleep so thread sensors keep sampling
            time.sleep(0.01)

    finally:
        stop_evt.set()


def goal_localizer_process_main(cmd_q, cam_in_q, out_q, stop_evt):
    """Alternate localizer process example. Replace logic with goal-specific code."""
    # This is a simplified stand-in for a different localization strategy
    while not stop_evt.is_set():
        while not cmd_q.empty():
            try:
                c = cmd_q.get_nowait()
            except Exception:
                break
            if c == 'stop':
                stop_evt.set()

        try:
            frame_bytes = cam_in_q.get(timeout=0.1)
        except Exception:
            frame_bytes = None

        if frame_bytes is not None:
            # pretend we're doing heavy goal-specific image processing
            time.sleep(0.05)
            out_q.put({'ts': time.time(), 'goal': True})

        time.sleep(0.01)


def keyboard_poller(stop_evt, key_q):
    """Thread in main process to poll keyboard keys (Q to quit, F to toggle forwarding).

    Uses msvcrt on Windows; falls back to a blocking input() if not available.
    """
    if _HAS_MSVCRT:
        while not stop_evt.is_set():
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                key_q.put(ch)
            time.sleep(0.02)
    else:
        # fallback: blocking input in a thread
        while not stop_evt.is_set():
            try:
                line = input()
            except Exception:
                break
            for ch in line:
                key_q.put(ch)


def main():
    ctx = get_context('spawn')

    cam_cmd_q = ctx.Queue()
    cam_out_q = ctx.Queue(maxsize=8)  # camera -> main

    # queue main -> localizer (forwarded frames)
    loc_in_q = ctx.Queue(maxsize=4)
    loc_cmd_q = ctx.Queue()
    loc_out_q = ctx.Queue()

    stop_event = ctx.Event()

    # start camera process
    cam_proc = ctx.Process(target=camera_process_main, args=(cam_cmd_q, cam_out_q, stop_event), daemon=True)
    cam_proc.start()
    cam_cmd_q.put('start')

    # start localizer process
    loc_proc = ctx.Process(target=localizer_process_main, args=(loc_cmd_q, loc_in_q, loc_out_q, stop_event), daemon=True)
    loc_proc.start()

    # NOTE: if you want to run goal_localizer instead, start goal_localizer_process_main
    # and ensure loc_proc above is not running (only one should run at a time).

    key_q = mp.Queue()
    kb_stop = threading.Event()
    kb_thread = threading.Thread(target=keyboard_poller, args=(kb_stop, key_q), daemon=True)
    kb_thread.start()

    forward_to_loc = True
    frame_counter = 0

    try:
        while True:
            # keyboard handling
            try:
                while not key_q.empty():
                    k = key_q.get_nowait()
                    if isinstance(k, str):
                        k_low = k.lower()
                    else:
                        k_low = str(k).lower()
                    if k_low == 'q':
                        print('Quit requested')
                        raise KeyboardInterrupt()
                    if k_low == 'f':
                        forward_to_loc = not forward_to_loc
                        print('Forwarding to localizer:', forward_to_loc)

            except Exception:
                pass

            # show camera frames (decode jpeg bytes)
            try:
                frame_bytes = cam_out_q.get(timeout=0.02)
            except Exception:
                frame_bytes = None

            if frame_bytes is not None:
                nparr = np.frombuffer(frame_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    cv2.imshow('camera', frame)
                    # forward every 3rd frame (example policy) if enabled
                    if forward_to_loc and (frame_counter % 3 == 0):
                        try:
                            loc_in_q.put(frame_bytes, block=False)
                        except Exception:
                            pass
                    frame_counter += 1
                    # keep UI responsive
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        raise KeyboardInterrupt()

            # consume messages from localizer
            try:
                while not loc_out_q.empty():
                    msg = loc_out_q.get_nowait()
                    print('LOCALIZER:', msg)
            except Exception:
                pass

            time.sleep(0.005)

    except KeyboardInterrupt:
        print('Shutting down...')

    finally:
        # signal everything to stop
        stop_event.set()
        kb_stop.set()

        cam_cmd_q.put('stop')
        loc_cmd_q.put('stop')

        # join processes
        cam_proc.join(timeout=2)
        if cam_proc.is_alive():
            cam_proc.terminate()

        loc_proc.join(timeout=2)
        if loc_proc.is_alive():
            loc_proc.terminate()

        try:
            cv2.destroyAllWindows()
        except Exception:
            pass


if __name__ == '__main__':
    main()
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

from typing import Optional
from dataclasses import dataclass

@dataclass
class VisionData:
    # TODO: add stuff for like ball/goal radius / estimated distance from a regression function
    ball_found: bool # irrelevant since we have optional for pos
    ball_pos: Optional[list]
    ball_angle: Optional[float] # could use last angle theoretically, but that can be stored locally
    goal_localization: np.ndarray # 0 is a goal, and 1 is a goal, set own_goal_idx and opp_goal_idx or something to index

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
