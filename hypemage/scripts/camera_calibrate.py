"""
Camera Calibration Script - HSV Range Calibration Tool

This script provides an interactive HSV calibration interface for tuning
ball and goal detection parameters. It captures camera frames and creates
mask previews for each HSV range (ball, blue goal, yellow goal).

The calibration widget on the web dashboard can adjust HSV values,
which are received via queue and immediately reflected in the mask previews.

Usage:
    Launch from web interface or run directly:
    python -m hypemage.scripts.camera_calibrate
"""

import time
import signal
import json
import numpy as np
from pathlib import Path
from typing import Optional

# Import camera module and mask preview function
from hypemage.camera import CameraProcess, create_mask_preview, load_camera_config
from hypemage.logger import get_logger

logger = get_logger("camera_calibrate")

# Global flag for clean shutdown
should_stop = False


def signal_handler(signum, frame):
    """Handle termination signals gracefully"""
    global should_stop
    logger.info(f"Received signal {signum}, stopping camera calibration...")
    should_stop = True


def save_config(config_data: dict, config_path: Optional[str] = None):
    """
    Save updated HSV ranges to camera_config.json
    
    Args:
        config_data: Dict containing hsv_ranges to save
        config_path: Optional path to config file
    """
    if config_path is None:
        path = Path(__file__).parent.parent / "camera_config.json"
    else:
        path = Path(config_path)
    
    try:
        # Load existing config
        if path.exists():
            with open(path, 'r') as f:
                full_config = json.load(f)
        else:
            full_config = {}
        
        # Update HSV ranges
        full_config['hsv_ranges'] = config_data['hsv_ranges']
        
        # Write back
        with open(path, 'w') as f:
            json.dump(full_config, f, indent=2)
        
        logger.info(f"Saved calibration to {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save config: {e}", exc_info=True)
        return False


def camera_calibrate_loop(fps_target: int = 10, subsystem_name: str = "camera_calibrate"):
    """
    Main calibration loop - captures frames and creates mask previews
    
    Args:
        fps_target: Target frames per second (lower than debug since less critical)
        subsystem_name: Name for debug manager subsystem registration
    """
    global should_stop
    
    logger.info("Starting camera calibration loop...")
    
    # Load current config
    config = load_camera_config()
    hsv_ranges = config.get('hsv_ranges', {})
    
    logger.info(f"Loaded HSV ranges: {hsv_ranges}")
    
    # Initialize camera
    try:
        camera = CameraProcess()
        logger.info("Camera initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize camera: {e}", exc_info=True)
        return
    
    frame_time = 1.0 / fps_target
    frame_count = 0
    
    # Current HSV ranges (can be updated via queue/websocket)
    current_ranges = {
        'ball': hsv_ranges.get('ball', {'lower': [10, 100, 100], 'upper': [20, 255, 255]}),
        'blue_goal': hsv_ranges.get('blue_goal', {'lower': [100, 150, 50], 'upper': [120, 255, 255]}),
        'yellow_goal': hsv_ranges.get('yellow_goal', {'lower': [20, 100, 100], 'upper': [40, 255, 255]})
    }
    
    try:
        while not should_stop:
            loop_start = time.time()
            
            # Capture frame
            frame = camera.capture_frame()
            if frame is None:
                logger.warning("Failed to capture frame")
                time.sleep(0.1)
                continue
            
            # TODO: Check queue for HSV range updates from web interface
            # For now, we use the loaded config values
            
            # Create mask previews for each HSV range (need to convert lists to numpy arrays)
            ball_lower = np.array(current_ranges['ball']['lower'])
            ball_upper = np.array(current_ranges['ball']['upper'])
            ball_mask = create_mask_preview(frame, ball_lower, ball_upper, label="Ball")
            
            blue_lower = np.array(current_ranges['blue_goal']['lower'])
            blue_upper = np.array(current_ranges['blue_goal']['upper'])
            blue_goal_mask = create_mask_preview(frame, blue_lower, blue_upper, label="Blue Goal")
            
            yellow_lower = np.array(current_ranges['yellow_goal']['lower'])
            yellow_upper = np.array(current_ranges['yellow_goal']['upper'])
            yellow_goal_mask = create_mask_preview(frame, yellow_lower, yellow_upper, label="Yellow Goal")
            
            # TODO: Send original frame + 3 masks to debug manager
            # For now, log periodically
            if frame_count % 50 == 0:  # Log every 5 seconds at 10fps
                logger.info(f"Frame {frame_count}: Generated mask previews")
                logger.debug(f"Current ranges: ball={current_ranges['ball']}")
            
            # Frame rate control
            frame_count += 1
            elapsed = time.time() - loop_start
            sleep_time = max(0, frame_time - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Error in calibration loop: {e}", exc_info=True)
    finally:
        # Cleanup
        if hasattr(camera, 'picam2'):
            camera.picam2.stop()
            logger.info("Picamera2 stopped")
        elif hasattr(camera, 'cap'):
            camera.cap.release()
            logger.info("OpenCV VideoCapture released")
        logger.info("Camera calibration loop stopped")


def main():
    """Entry point for camera calibration script"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Camera Calibration Script starting...")
    
    # Run calibration loop
    camera_calibrate_loop(fps_target=10)
    
    logger.info("Camera Calibration Script exited")


if __name__ == '__main__':
    main()
