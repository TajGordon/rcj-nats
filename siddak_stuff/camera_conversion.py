"""
Multiprocessing-ready Camera module for Soccer Robot

This module provides a Camera class that can run in a separate process,
communicating via queues. It handles Pi Camera initialization, frame capture,
ball detection, and goal detection.

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
import time
import cv2
import numpy as np
import math

try:
    from picamera2 import Picamera2
    _HAS_PICAMERA = True
except ImportError:
    _HAS_PICAMERA = False
    print("Warning: picamera2 not available, falling back to cv2.VideoCapture")


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
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize camera with configuration
        
        Args:
            config: Optional configuration dict with keys:
                - camera: width, height, format
                - ball_detection: HSV ranges, thresholds
                - goal_detection: blue/yellow goal params
                - circular_mask: center_x, center_y, radius
                - frame_config: center_x, center_y
        """
        self.config = config or self._default_config()
        
        # Initialize camera
        if _HAS_PICAMERA:
            self.picam2 = Picamera2()
            cam_cfg = self.config['camera']
            self.picam2.configure(self.picam2.create_video_configuration(
                main={"size": (cam_cfg["width"], cam_cfg["height"]), 
                      "format": cam_cfg["format"]}
            ))
            self.picam2.start()
            self.capture_fn = self._capture_picamera
        else:
            # Fallback to OpenCV
            self.cap = cv2.VideoCapture(0)
            cam_cfg = self.config['camera']
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_cfg["width"])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_cfg["height"])
            self.capture_fn = self._capture_opencv
        
        # Extract config parameters
        ball_cfg = self.config['ball_detection']
        self.lower_orange = np.array(ball_cfg["lower_orange"])
        self.upper_orange = np.array(ball_cfg["upper_orange"])
        self.proximity_threshold = ball_cfg["proximity_threshold"]
        self.angle_tolerance = ball_cfg["angle_tolerance"]
        self.min_ball_area = ball_cfg["min_contour_area"]
        self.max_ball_area = ball_cfg["max_contour_area"]
        
        mask_cfg = self.config['circular_mask']
        self.mask_center_x = mask_cfg["center_x"]
        self.mask_center_y = mask_cfg["center_y"]
        self.mask_radius = mask_cfg["radius"]
        
        frame_cfg = self.config['frame_config']
        self.frame_center_x = frame_cfg["center_x"]
        self.frame_center_y = frame_cfg["center_y"]
        
        self.blue_goal_config = self.config['goal_detection']["blue_goal"]
        self.yellow_goal_config = self.config['goal_detection']["yellow_goal"]
        self.goal_detection_params = self.config['goal_detection']
        
        # Frame counter for frame IDs
        self.frame_counter = 0
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration if none provided"""
        return {
            'camera': {
                'width': 640,
                'height': 480,
                'format': 'RGB888'
            },
            'ball_detection': {
                'lower_orange': [5, 150, 150],
                'upper_orange': [15, 255, 255],
                'proximity_threshold': 5000,
                'angle_tolerance': 0.1,
                'min_contour_area': 100,
                'max_contour_area': 50000
            },
            'circular_mask': {
                'center_x': 320,
                'center_y': 240,
                'radius': 80
            },
            'frame_config': {
                'center_x': 320,
                'center_y': 240
            },
            'goal_detection': {
                'blue_goal': {
                    'lower': [100, 150, 0],
                    'upper': [130, 255, 255],
                    'min_contour_area': 500,
                    'max_contour_area': 100000,
                    'aspect_ratio_min': 0.3,
                    'aspect_ratio_max': 3.0
                },
                'yellow_goal': {
                    'lower': [20, 100, 100],
                    'upper': [30, 255, 255],
                    'min_contour_area': 500,
                    'max_contour_area': 100000,
                    'aspect_ratio_min': 0.3,
                    'aspect_ratio_max': 3.0
                },
                'min_goal_width': 20,
                'min_goal_height': 20,
                'goal_center_tolerance': 0.15
            }
        }
    
    def _capture_picamera(self):
        """Capture frame from Picamera2"""
        return self.picam2.capture_array()
    
    def _capture_opencv(self):
        """Capture frame from OpenCV VideoCapture"""
        ret, frame = self.cap.read()
        if ret:
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return None
    
    def capture_frame(self):
        """Capture a frame from the camera"""
        return self.capture_fn()
    
    def detect_ball(self, frame) -> BallDetectionResult:
        """
        Detect orange ball in the frame using HSV color filtering
        
        Args:
            frame: Input frame from camera (RGB)
            
        Returns:
            BallDetectionResult with detection info
        """
        # Convert to HSV (handle both RGB and BGR)
        if frame.shape[2] == 3:
            hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        else:
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
            frame: Input frame from camera (RGB)
            
        Returns:
            Tuple of (blue_goal_result, yellow_goal_result)
        """
        # Convert to HSV
        if frame.shape[2] == 3:
            hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        else:
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
                        # Compress to JPEG
                        ok, jpg = cv2.imencode('.jpg', cv2.cvtColor(frame, cv2.COLOR_RGB2BGR), 
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
