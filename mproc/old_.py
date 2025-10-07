import time
from multiprocessing import Process, Queue
from mproc.old_cam import CameraProc
import cv2

def main():
    cam_in_q, cam_out_q = Queue(), Queue()
    
    # Create an instance of CameraProc and use its start method
    camera_proc = CameraProc(cam_in_q, cam_out_q)
    cam = Process(target=camera_proc.start)
    cam.start()
    cam_in_q.put('start')

    last_time = time.time()
    print("Starting main loop...")
    frame_display_count = 0

    try:
        while True:
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            while not cam_out_q.empty():
                frame = cam_out_q.get()
                frame_display_count += 1
                if frame_display_count % 10 == 0:
                    print(f"Displaying frame #{frame_display_count}")
                cv2.putText(frame, f"dt: {dt:.3f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2)
                cv2.imshow('Camera Feed', frame)

            # This is crucial for OpenCV window to display and respond to events
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):  # Press 'q' to quit
                break
                
            time.sleep(0.001)  # Reduced sleep time for smoother display

    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        print("Cleaning up...")
        cam_in_q.put('stop')
        if cam.is_alive():
            cam.join(timeout=2)
        if cam.is_alive():
            print("Force terminating camera process")
            cam.terminate()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
