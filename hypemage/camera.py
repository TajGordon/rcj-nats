"""
Multiprocessing-ready Camera module for Soccer Robot

This module provides a Camera class that can run in a separate process,
communicating via queues. It handles Pi Camera initialization, frame capture,
ball detection, and goal detection.

CRITICAL: Raises CameraInitializationError if camera hardware fails to initialize

Usage:
    from multiprocessing import get_context
    ctx = get_context('spawn')
    cmd_q = ctx.Queue()
    out_q = ctx.Queue()
    stop_evt = ctx.Event()
    
    # Start camera in a separate process
    proc = ctx.Process(target=camera_start, args=(cmd_q, out_q, stop_evt))
    proc.start()
    
    # Send commands
    cmd_q.put({'type': 'detect_ball'})
    cmd_q.put({'type': 'detect_goals'})
    
    # Read results
    data = out_q.get()
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import time
import cv2
import numpy as np
import math
import json

from hypemage.logger import get_logger
from hypemage.config import load_config, get_robot_id

logger = get_logger(__name__)

try:
    from picamera2 import Picamera2
    _HAS_PICAMERA = True
    logger.info("Picamera2 library loaded successfully")
except ImportError as e:
    _HAS_PICAMERA = False
    logger.warning(f"Picamera2 not available: {e}")


class CameraInitializationError(Exception):
    """Raised when camera initialization fails critically"""
    pass


@dataclass
class BallDetectionResult:
    """Ball detection result data"""
    detected: bool = False
    center_x: int = 0
    center_y: int = 0
    radius: int = 0
    area: float = 0.0
    horizontal_error: float = 0.0
    vertical_error: float = 0.0
    is_close: bool = False
    is_centered_horizontally: bool = False
    is_close_and_centered: bool = False


@dataclass
class GoalDetectionResult:
    """Single goal detection result"""
    detected: bool = False
    center_x: int = 0
    center_y: int = 0
    width: int = 0
    height: int = 0
    area: float = 0.0
    horizontal_error: float = 0.0
    vertical_error: float = 0.0
    is_centered_horizontally: bool = False

@dataclass
class VisionData:
    """Complete vision data output from camera process"""
    timestamp: float
    frame_id: int
    ball: BallDetectionResult = field(default_factory=BallDetectionResult)
    blue_goal: GoalDetectionResult = field(default_factory=GoalDetectionResult)
    yellow_goal: GoalDetectionResult = field(default_factory=GoalDetectionResult)
    frame_bytes: Optional[bytes] = None  # compressed JPEG if requested
    raw_frame: Optional[np.ndarray] = None  # only if explicitly requested


class CameraProcess:
    """Camera that can run in a separate process with queue-based communication"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, robot_id: Optional[str] = None):
        """
        Initialize camera with configuration
        
        Args:
            config: Optional configuration dict. If None, loads from config.json for this robot
            robot_id: Robot identifier ('storm' or 'necron'). If None, auto-detects.
                
        Raises:
            CameraInitializationError: If camera hardware fails to initialize
        """
        self.robot_id = robot_id or get_robot_id()
        self.config = config or load_config(self.robot_id)
        
        # Initialize camera
        try:
            if _HAS_PICAMERA:
                logger.info("Initializing Picamera2...")
                self.picam2 = Picamera2()
                cam_cfg = self.config['camera']
                self.picam2.configure(self.picam2.create_video_configuration(
                    main={"size": (cam_cfg["width"], cam_cfg["height"]), 
                          "format": cam_cfg["format"]}
                ))
                self.picam2.start()
                self.capture_fn = self._capture_picamera
                logger.info("Picamera2 initialized successfully")
            else:
                # Fallback to OpenCV
                logger.warning("Picamera2 not available, trying OpenCV VideoCapture...")
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    raise CameraInitializationError("Failed to open camera with OpenCV VideoCapture")
                
                cam_cfg = self.config['camera']
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_cfg["width"])
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_cfg["height"])
                self.capture_fn = self._capture_opencv
                logger.info("OpenCV VideoCapture initialized successfully")
                
        except Exception as e:
            logger.critical(f"CRITICAL: Failed to initialize camera: {e}", exc_info=True)
            raise CameraInitializationError(f"Camera initialization failed: {e}")
        
        # Extract HSV ranges from config
        hsv_ranges = self.config.get('hsv_ranges', {})
        ball_cfg = hsv_ranges.get('ball', {})
        self.lower_orange = np.array(ball_cfg.get("lower", [10, 100, 100]))
        self.upper_orange = np.array(ball_cfg.get("upper", [20, 255, 255]))
        self.min_ball_area = ball_cfg.get("min_area", 100)
        self.max_ball_area = ball_cfg.get("max_area", 50000)
        
        blue_goal_cfg = hsv_ranges.get('blue_goal', {})
        self.lower_blue = np.array(blue_goal_cfg.get("lower", [100, 150, 50]))
        self.upper_blue = np.array(blue_goal_cfg.get("upper", [120, 255, 255]))
        self.min_blue_area = blue_goal_cfg.get("min_area", 500)
        self.max_blue_area = blue_goal_cfg.get("max_area", 100000)
        
        yellow_goal_cfg = hsv_ranges.get('yellow_goal', {})
        self.lower_yellow = np.array(yellow_goal_cfg.get("lower", [20, 100, 100]))
        self.upper_yellow = np.array(yellow_goal_cfg.get("upper", [40, 255, 255]))
        self.min_yellow_area = yellow_goal_cfg.get("min_area", 500)
        self.max_yellow_area = yellow_goal_cfg.get("max_area", 100000)
        
        # Detection parameters
        detection_cfg = self.config.get('detection', {})
        self.proximity_threshold = detection_cfg.get("proximity_threshold", 5000)
        self.angle_tolerance = detection_cfg.get("angle_tolerance", 15)
        
        # Frame center
        cam_cfg = self.config['camera']
        self.frame_center_x = cam_cfg["width"] // 2
        self.frame_center_y = cam_cfg["height"] // 2
        
        # Goal detection configs (kept for compatibility with existing detection methods)
        self.blue_goal_config = {
            'lower': self.lower_blue.tolist(),
            'upper': self.upper_blue.tolist(),
            'min_contour_area': self.min_blue_area,
            'max_contour_area': self.max_blue_area,
            'aspect_ratio_min': 0.3,  # Goals are typically wider than tall
            'aspect_ratio_max': 5.0   # But not extremely wide
        }
        self.yellow_goal_config = {
            'lower': self.lower_yellow.tolist(),
            'upper': self.upper_yellow.tolist(),
            'min_contour_area': self.min_yellow_area,
            'max_contour_area': self.max_yellow_area,
            'aspect_ratio_min': 0.3,
            'aspect_ratio_max': 5.0
        }
        self.goal_detection_params = {
            'min_goal_width': 20,
            'min_goal_height': 20,
            'goal_center_tolerance': detection_cfg.get("goal_center_tolerance", 0.15)
        }
        
        # Circular mask (for field boundary)
        self.mask_center_x = cam_cfg["width"] // 2
        self.mask_center_y = cam_cfg["height"] // 2
        self.mask_radius = 80  # Default radius for field mask
        
        # Frame counter for frame IDs
        self.frame_counter = 0
    
    def _capture_picamera(self):
        """Capture frame from Picamera2"""
        return self.picam2.capture_array()
    
    def _capture_opencv(self):
        """Capture frame from OpenCV VideoCapture"""
        ret, frame = self.cap.read()
        if ret:
            # OpenCV VideoCapture returns BGR, so return as-is for consistency
            return frame
        return None
    
    def capture_frame(self):
        """Capture a frame from the camera"""
        return self.capture_fn()
    
    def detect_ball(self, frame) -> BallDetectionResult:
        """
        Detect orange ball in the frame using HSV color filtering
        
        Args:
            frame: Input frame from camera (BGR from Picamera2)
            
        Returns:
            BallDetectionResult with detection info
        """
        # Convert to HSV (Picamera2 returns BGR format)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        mask = cv2.inRange(hsv, self.lower_orange, self.upper_orange)
        mask = self._apply_circular_mask(mask)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area
        filtered_contours = [x for x in contours if 
                           self.min_ball_area < cv2.contourArea(x) < self.max_ball_area]
        
        if not filtered_contours:
            return BallDetectionResult(detected=False)
        
        largest_contour = max(filtered_contours, key=cv2.contourArea)
        (x, y), radius = cv2.minEnclosingCircle(largest_contour)
        
        center_x = int(x)
        center_y = int(y)
        radius = int(radius)
        
        # Calculate proximity info
        ball_area = math.pi * radius * radius
        horizontal_error = (center_x - self.frame_center_x) / self.frame_center_x
        vertical_error = (center_y - self.frame_center_y) / self.frame_center_y
        is_close = ball_area >= self.proximity_threshold
        is_centered = abs(horizontal_error) <= self.angle_tolerance
        
        return BallDetectionResult(
            detected=True,
            center_x=center_x,
            center_y=center_y,
            radius=radius,
            area=ball_area,
            horizontal_error=horizontal_error,
            vertical_error=vertical_error,
            is_close=is_close,
            is_centered_horizontally=is_centered,
            is_close_and_centered=is_close and is_centered
        )
    
    def detect_goals(self, frame) -> Tuple[GoalDetectionResult, GoalDetectionResult]:
        """
        Detect blue and yellow goals in the frame
        
        Args:
            frame: Input frame from camera (BGR from Picamera2)
            
        Returns:
            Tuple of (blue_goal_result, yellow_goal_result)
        """
        # Convert to HSV (Picamera2 returns BGR format)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        blue_result = self._detect_single_goal(hsv, self.blue_goal_config)
        yellow_result = self._detect_single_goal(hsv, self.yellow_goal_config)
        
        return blue_result, yellow_result
    
    def _detect_single_goal(self, hsv_frame, goal_config) -> GoalDetectionResult:
        """Detect a single goal using HSV filtering"""
        lower = np.array(goal_config["lower"])
        upper = np.array(goal_config["upper"])
        mask = cv2.inRange(hsv_frame, lower, upper)
        mask = self._apply_circular_mask(mask)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter by area
        filtered_contours = [c for c in contours if 
                           goal_config["min_contour_area"] < cv2.contourArea(c) < goal_config["max_contour_area"]]
        
        if not filtered_contours:
            return GoalDetectionResult(detected=False)
        
        largest_contour = max(filtered_contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Check size requirements
        if (w < self.goal_detection_params["min_goal_width"] or 
            h < self.goal_detection_params["min_goal_height"]):
            return GoalDetectionResult(detected=False)
        
        # Check aspect ratio
        aspect_ratio = w / h if h > 0 else 0
        if not (goal_config["aspect_ratio_min"] <= aspect_ratio <= goal_config["aspect_ratio_max"]):
            return GoalDetectionResult(detected=False)
        
        center_x = x + w // 2
        center_y = y + h // 2
        area = cv2.contourArea(largest_contour)
        
        # Calculate navigation info
        horizontal_error = (center_x - self.frame_center_x) / self.frame_center_x
        vertical_error = (center_y - self.frame_center_y) / self.frame_center_y
        is_centered = abs(horizontal_error) <= self.goal_detection_params["goal_center_tolerance"]
        
        return GoalDetectionResult(
            detected=True,
            center_x=center_x,
            center_y=center_y,
            width=w,
            height=h,
            area=area,
            horizontal_error=horizontal_error,
            vertical_error=vertical_error,
            is_centered_horizontally=is_centered
        )
    
    def _apply_circular_mask(self, mask):
        """Apply a circular mask to ignore the center area"""
        mask_with_circle = np.zeros_like(mask)
        cv2.circle(mask_with_circle, (self.mask_center_x, self.mask_center_y), 
                   self.mask_radius, 255, -1)
        circle_mask = cv2.bitwise_not(mask_with_circle)
        return cv2.bitwise_and(mask, circle_mask)
    
    def stop(self):
        """Stop the camera"""
        if _HAS_PICAMERA:
            self.picam2.stop()
        else:
            self.cap.release()


def load_camera_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load camera configuration from JSON file (standalone function for scripts)
    
    Args:
        config_path: Path to config file. If None, uses default location.
        
    Returns:
        Dict containing camera configuration
    """
    if config_path is None:
        path = Path(__file__).parent / "camera_config.json"
    else:
        path = Path(config_path)
    
    if path.exists():
        try:
            with open(path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded camera config from {path}")
            return config
        except Exception as e:
            logger.warning(f"Failed to load config from {path}: {e}")
            return {}
    else:
        logger.warning(f"Config file not found: {path}")
        return {}


def camera_start(cmd_q, out_q, stop_evt, config=None):
    """
    Entry point for camera process - runs continuously and processes commands
    
    Args:
        cmd_q: Queue for incoming commands from main process
        out_q: Queue for outgoing vision data to main process
        stop_evt: Event to signal shutdown
        config: Optional camera configuration dict
    
    Commands (dict messages on cmd_q):
        {'type': 'detect_ball'} - detect ball only
        {'type': 'detect_goals'} - detect goals only
        {'type': 'detect_all'} - detect ball + goals
        {'type': 'capture_frame', 'compress': True/False} - capture and send frame
        {'type': 'stop'} - stop the camera process
        {'type': 'pause'} - pause processing
        {'type': 'resume'} - resume processing
    
    Output (VisionData on out_q):
        VisionData dataclass with timestamp, frame_id, and detection results
    """
    camera = CameraProcess(config)
    paused = False
    
    try:
        while not stop_evt.is_set():
            # Process commands
            cmd = None
            try:
                cmd = cmd_q.get(timeout=0.01)
            except Exception:
                pass
            
            if cmd:
                cmd_type = cmd.get('type', '')
                
                if cmd_type == 'stop':
                    break
                elif cmd_type == 'pause':
                    paused = True
                    continue
                elif cmd_type == 'resume':
                    paused = False
                    continue
            
            if paused:
                time.sleep(0.01)
                continue
            
            # Capture frame
            frame = camera.capture_frame()
            if frame is None:
                time.sleep(0.01)
                continue
            
            # Create vision data
            vision_data = VisionData(
                timestamp=time.time(),
                frame_id=camera.frame_counter
            )
            camera.frame_counter += 1
            
            # Process based on command or default behavior
            if cmd:
                cmd_type = cmd.get('type', 'detect_all')
                
                if cmd_type in ['detect_ball', 'detect_all']:
                    vision_data.ball = camera.detect_ball(frame)
                
                if cmd_type in ['detect_goals', 'detect_all']:
                    blue, yellow = camera.detect_goals(frame)
                    vision_data.blue_goal = blue
                    vision_data.yellow_goal = yellow
                
                if cmd_type == 'capture_frame':
                    compress = cmd.get('compress', True)
                    if compress:
                        # Compress to JPEG (frame is already BGR)
                        ok, jpg = cv2.imencode('.jpg', frame, 
                                              [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                        if ok:
                            vision_data.frame_bytes = jpg.tobytes()
                    else:
                        vision_data.raw_frame = frame
            else:
                # Default: detect all
                vision_data.ball = camera.detect_ball(frame)
                blue, yellow = camera.detect_goals(frame)
                vision_data.blue_goal = blue
                vision_data.yellow_goal = yellow
            
            # Send data to output queue (non-blocking)
            try:
                out_q.put(vision_data, block=False)
            except Exception:
                # Queue full, drop oldest or skip
                pass
            
            # Small sleep to avoid hot loop
            time.sleep(0.01)
    
    finally:
        camera.stop()


# Convenience function for simple usage
def start(cmd_q, out_q, stop_evt=None, config=None):
    """
    Convenience wrapper that matches the camera_example.py pattern
    
    Usage:
        from multiprocessing import get_context
        ctx = get_context('spawn')
        cmd_q, out_q = ctx.Queue(), ctx.Queue()
        stop_evt = ctx.Event()
        proc = ctx.Process(target=start, args=(cmd_q, out_q, stop_evt))
        proc.start()
    """
    if stop_evt is None:
        from multiprocessing import Event
        stop_evt = Event()
    
    camera_start(cmd_q, out_q, stop_evt, config)


def add_debug_overlays(frame: np.ndarray, vision_data: VisionData) -> np.ndarray:
    """
    Add debug overlays to frame showing detection results
    
    Args:
        frame: BGR frame from camera (Picamera2 format)
        vision_data: Detection results to visualize
        
    Returns:
        Frame with overlays drawn (BGR for display)
    """
    # Validate input
    if frame is None or frame.size == 0:
        return frame
    
    # Get frame dimensions for bounds checking
    frame_height, frame_width = frame.shape[:2]
    
    # Frame is already in BGR format from Picamera2, so just copy it
    # Handle cases where frame might be grayscale or other formats
    if len(frame.shape) == 2:
        # Grayscale - convert to BGR
        display_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    elif frame.shape[2] == 4:
        # RGBA - convert to BGR
        display_frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
    elif frame.shape[2] == 3:
        # Already BGR from Picamera2, just copy
        display_frame = frame.copy()
    else:
        display_frame = frame.copy()
    
    # Draw ball detection
    if vision_data.ball.detected:
        center_x = int(vision_data.ball.center_x)
        center_y = int(vision_data.ball.center_y)
        radius = int(vision_data.ball.radius)
        
        # Bounds check
        if 0 <= center_x < frame_width and 0 <= center_y < frame_height and radius > 0:
            center = (center_x, center_y)
            
            # Draw circle around ball
            cv2.circle(display_frame, center, radius, (0, 165, 255), 3)  # Orange circle
            cv2.circle(display_frame, center, 5, (0, 0, 255), -1)  # Red center dot
            
            # Add label with position and radius - ensure text stays in bounds
            label = f"Ball: ({center_x}, {center_y}) r={radius}"
            text_x = max(10, center_x - 80)
            text_y = max(30, center_y - radius - 10)
            text_y = min(frame_height - 10, text_y)
            cv2.putText(display_frame, label, (text_x, text_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
    
    # Draw blue goal detection
    if vision_data.blue_goal.detected:
        center_x = int(vision_data.blue_goal.center_x)
        center_y = int(vision_data.blue_goal.center_y)
        width = int(vision_data.blue_goal.width)
        height = int(vision_data.blue_goal.height)
        
        x = center_x - width // 2
        y = center_y - height // 2
        
        # Bounds check and clamp
        x = max(0, min(x, frame_width - 1))
        y = max(0, min(y, frame_height - 1))
        w = min(width, frame_width - x)
        h = min(height, frame_height - y)
        
        if w > 0 and h > 0:
            # Draw rectangle around blue goal
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (255, 0, 0), 3)  # Blue box
            
            # Add label - ensure text stays in bounds
            label = f"Blue: ({center_x}, {center_y})"
            text_y = max(20, y - 10)
            cv2.putText(display_frame, label, (x, text_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
    
    # Draw yellow goal detection
    if vision_data.yellow_goal.detected:
        center_x = int(vision_data.yellow_goal.center_x)
        center_y = int(vision_data.yellow_goal.center_y)
        width = int(vision_data.yellow_goal.width)
        height = int(vision_data.yellow_goal.height)
        
        x = center_x - width // 2
        y = center_y - height // 2
        
        # Bounds check and clamp
        x = max(0, min(x, frame_width - 1))
        y = max(0, min(y, frame_height - 1))
        w = min(width, frame_width - x)
        h = min(height, frame_height - y)
        
        if w > 0 and h > 0:
            # Draw rectangle around yellow goal
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 255), 3)  # Yellow box
            
            # Add label - ensure text stays in bounds
            label = f"Yellow: ({center_x}, {center_y})"
            text_y = max(20, y - 10)
            cv2.putText(display_frame, label, (x, text_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    
    # Add frame ID
    frame_label = f"Frame: {vision_data.frame_id}"
    cv2.putText(display_frame, frame_label, (10, 30),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    return display_frame


def create_mask_preview(frame: np.ndarray, lower_hsv: np.ndarray, upper_hsv: np.ndarray, 
                       label: str = "") -> np.ndarray:
    """
    Create a mask preview showing what the HSV range captures
    
    Args:
        frame: BGR frame from camera (Picamera2 format)
        lower_hsv: Lower HSV bounds [H, S, V]
        upper_hsv: Upper HSV bounds [H, S, V]
        label: Optional label to add to preview
        
    Returns:
        BGR image showing the mask (white = detected, black = not detected)
    """
    # Convert to HSV (Picamera2 returns BGR format)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Create mask
    mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
    
    # Convert mask to BGR for display (easier to see)
    mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    
    # Add label if provided
    if label:
        cv2.putText(mask_bgr, label, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    return mask_bgr


if __name__ == '__main__':
    # Simple test without multiprocessing
    print("Testing camera in single process mode...")
    from multiprocessing import Queue, Event
    
    cmd_q = Queue()
    out_q = Queue()
    stop_evt = Event()
    
    # Run for 5 seconds
    import threading
    def stopper():
        time.sleep(5)
        stop_evt.set()
        print("Stopping camera...")
    
    threading.Thread(target=stopper, daemon=True).start()
    
    # Start camera
    print("Camera running... will stop in 5 seconds")
    camera_start(cmd_q, out_q, stop_evt)
    
    # Print any output
    while not out_q.empty():
        data = out_q.get()
        print(f"Frame {data.frame_id}: Ball detected={data.ball.detected}, "
              f"Blue goal={data.blue_goal.detected}, Yellow goal={data.yellow_goal.detected}")
    
    print("Test complete!")
