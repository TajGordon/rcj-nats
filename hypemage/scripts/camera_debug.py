"""
Camera Debug Script - Streams camera feed with detection overlays

This script continuously captures camera frames, runs ball and goal detection,
and adds visual overlays showing detected objects. The overlaid frames are
sent to the debug manager for display on the web dashboard.

Usage:
    Launch from web interface or run directly:
    python -m hypemage.scripts.camera_debug
"""

import time
import signal

# Import camera module and overlay functions
from hypemage.camera import CameraProcess, add_debug_overlays, VisionData
from hypemage.logger import get_logger

logger = get_logger("camera_debug")

# Global flag for clean shutdown
should_stop = False


def signal_handler(signum, frame):
    """Handle termination signals gracefully"""
    global should_stop
    logger.info(f"Received signal {signum}, stopping camera debug...")
    should_stop = True


def camera_debug_loop(fps_target: int = 30, subsystem_name: str = "camera_debug"):
    """
    Main camera debug loop - captures, detects, overlays, and sends frames
    
    Args:
        fps_target: Target frames per second
        subsystem_name: Name for debug manager subsystem registration
    """
    global should_stop
    
    logger.info("Starting camera debug loop...")
    
    # Initialize camera
    try:
        camera = CameraProcess()
        logger.info("Camera initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize camera: {e}", exc_info=True)
        return
    
    frame_time = 1.0 / fps_target
    frame_count = 0
    
    try:
        while not should_stop:
            loop_start = time.time()
            
            # Capture frame
            frame = camera.capture_frame()
            if frame is None:
                logger.warning("Failed to capture frame")
                time.sleep(0.1)
                continue
            
            # Run detection
            ball_result = camera.detect_ball(frame)
            blue_goal_result, yellow_goal_result = camera.detect_goals(frame)
            
            # Create vision data for overlay function
            vision_data = VisionData(
                timestamp=loop_start,
                frame_id=frame_count,
                ball=ball_result,
                blue_goal=blue_goal_result,
                yellow_goal=yellow_goal_result
            )
            
            # Add debug overlays
            debug_frame = add_debug_overlays(frame, vision_data)
            
            # TODO: Send debug_frame to debug manager via queue/pipe
            # For now, we'll log detection status periodically
            if frame_count % 30 == 0:  # Log every second at 30fps
                detections = []
                if ball_result.detected:
                    detections.append(f"Ball@({ball_result.center_x},{ball_result.center_y})")
                if blue_goal_result.detected:
                    detections.append(f"BlueGoal@({blue_goal_result.center_x},{blue_goal_result.center_y})")
                if yellow_goal_result.detected:
                    detections.append(f"YellowGoal@({yellow_goal_result.center_x},{yellow_goal_result.center_y})")
                
                if detections:
                    logger.info(f"Frame {frame_count}: {', '.join(detections)}")
                else:
                    logger.debug(f"Frame {frame_count}: No detections")
            
            # Frame rate control
            frame_count += 1
            elapsed = time.time() - loop_start
            sleep_time = max(0, frame_time - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            # Log FPS every 100 frames
            if frame_count % 100 == 0:
                actual_fps = 1.0 / (elapsed + sleep_time)
                logger.info(f"Frame {frame_count}, FPS: {actual_fps:.1f}, Elapsed: {elapsed*1000:.1f}ms")
    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Error in camera debug loop: {e}", exc_info=True)
    finally:
        # Cleanup
        if hasattr(camera, 'picam2'):
            camera.picam2.stop()
            logger.info("Picamera2 stopped")
        elif hasattr(camera, 'cap'):
            camera.cap.release()
            logger.info("OpenCV VideoCapture released")
        logger.info("Camera debug loop stopped")


def main():
    """Entry point for camera debug script"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Camera Debug Script starting...")
    
    # Run debug loop
    camera_debug_loop(fps_target=30)
    
    logger.info("Camera Debug Script exited")


if __name__ == '__main__':
    main()
