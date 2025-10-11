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
    from libcamera import controls
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
    frame_center_x: int = 320  # Frame center X coordinate
    frame_center_y: int = 320  # Frame center Y coordinate
    mirror_detected: bool = False  # Whether mirror circle was detected
    mirror_center_x: Optional[int] = None  # Mirror center X if detected
    mirror_center_y: Optional[int] = None  # Mirror center Y if detected
    mirror_radius: Optional[int] = None  # Mirror radius if detected


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
                
                # Set camera focus after initialization
                self._focus_camera()
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
        self.lower_orange = np.array(ball_cfg.get("lower", [0, 180, 170]))
        self.upper_orange = np.array(ball_cfg.get("upper", [50, 255, 255]))
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
        
        # Mirror detection and masking
        mirror_cfg = self.config.get('mirror', {})
        self.enable_mirror_detection = mirror_cfg.get('enable', True)
        self.mirror_detection_method = mirror_cfg.get('detection_method', 'hough')  # 'hough' or 'contour'
        self.mirror_min_radius = mirror_cfg.get('min_radius', 100)
        self.mirror_max_radius = mirror_cfg.get('max_radius', 400)
        self.mirror_canny_threshold1 = mirror_cfg.get('canny_threshold1', 50)
        self.mirror_canny_threshold2 = mirror_cfg.get('canny_threshold2', 150)
        self.mirror_hough_param1 = mirror_cfg.get('hough_param1', 100)
        self.mirror_hough_param2 = mirror_cfg.get('hough_param2', 30)
        
        # Robot forward direction (for visualization and angle calculations)
        # This is the rotation offset in degrees to align camera coordinate system with robot
        # 0 = camera up is robot forward, 90 = camera right is robot forward, etc.
        self.robot_forward_rotation = mirror_cfg.get('robot_forward_rotation', 0)
        
        # Detected mirror properties (updated each frame or cached)
        self.mirror_circle = None  # (center_x, center_y, radius)
        self.mirror_mask = None  # Binary mask for the mirror area
        self.mirror_crop_region = None  # (x1, y1, x2, y2) bounding box for cropping
        self.mirror_detection_interval = mirror_cfg.get('detection_interval', 30)  # Detect every N frames
        self.mirror_detection_counter = 0
        
        # Fallback circular mask (for when mirror not detected or disabled)
        self.mask_center_x = cam_cfg["width"] // 2
        self.mask_center_y = cam_cfg["height"] // 2
        self.mask_radius = mirror_cfg.get('fallback_radius', 200)  # Default radius if mirror not found
        
        # Frame counter for frame IDs
        self.frame_counter = 0
    
    def _focus_camera(self):
        """Set camera focus to manual mode with optimal lens position"""
        if _HAS_PICAMERA and hasattr(self, 'picam2'):
            try:
                # Set manual focus mode with lens position 18.0 (optimal for soccer field)
                self.picam2.set_controls({
                    'AfMode': controls.AfModeEnum.Manual, 
                    'LensPosition': 18.0
                })
                time.sleep(2)  # Allow time for focus adjustment
                logger.info("Camera focus set to manual mode with lens position 18.0")
            except Exception as e:
                logger.warning(f"Failed to set camera focus: {e}")
    
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
    
    def draw_forward_direction(self, frame, center_x=None, center_y=None, radius=None):
        """
        Draw the robot's forward direction (0 degrees) on the frame
        
        Args:
            frame: Frame to draw on
            center_x: Center X coordinate (uses frame_center_x if None)
            center_y: Center Y coordinate (uses frame_center_y if None)
            radius: Length of the direction line (uses 80% of mirror radius if None)
            
        Returns:
            Frame with forward direction overlay
        """
        if center_x is None:
            center_x = self.frame_center_x
        if center_y is None:
            center_y = self.frame_center_y
        
        # Default radius to 80% of mirror radius or 80 pixels
        if radius is None:
            if self.mirror_circle is not None:
                radius = int(self.mirror_circle[2] * 0.8)
            else:
                radius = 80
        
        # Calculate forward direction with rotation offset
        # The big yellow arrow is at 180° from the heading, so we add 180° to flip it
        # 0 degrees = up (negative Y), rotated by robot_forward_rotation, then add 180° to flip
        angle_rad = math.radians(-90 + self.robot_forward_rotation + 180)  # -90 because 0° is up, +180 to flip
        
        # Calculate end point
        end_x = int(center_x + radius * math.cos(angle_rad))
        end_y = int(center_y + radius * math.sin(angle_rad))
        
        # Draw the forward direction line (bright cyan/yellow)
        cv2.arrowedLine(frame, (center_x, center_y), (end_x, end_y), 
                       (0, 255, 255), 3, tipLength=0.2)
        
        # Add text label
        label_x = int(center_x + (radius * 1.1) * math.cos(angle_rad))
        label_y = int(center_y + (radius * 1.1) * math.sin(angle_rad))
        cv2.putText(frame, "0°", (label_x - 15, label_y + 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Draw additional angle markers (90°, 180°, 270°)
        for marker_angle, label in [(90, "90°"), (180, "180°"), (270, "270°")]:
            angle_rad = math.radians(-90 + self.robot_forward_rotation + 180 + marker_angle)
            marker_radius = int(radius * 0.6)
            marker_x = int(center_x + marker_radius * math.cos(angle_rad))
            marker_y = int(center_y + marker_radius * math.sin(angle_rad))
            cv2.circle(frame, (marker_x, marker_y), 3, (0, 200, 200), -1)
            cv2.putText(frame, label, (marker_x - 15, marker_y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 200), 1)
        
        return frame
    
    def detect_mirror_circle(self, frame) -> Optional[Tuple[int, int, int]]:
        """
        Detect the circular mirror in the frame
        
        CRITICAL: This function MUST receive the full original camera frame,
        NOT a cropped version. Mirror detection requires the complete frame
        to accurately locate the mirror circle.
        
        Args:
            frame: Input frame from camera (BGR) - MUST be full original frame
            
        Returns:
            Tuple of (center_x, center_y, radius) if detected, None otherwise
        """
        if not self.enable_mirror_detection:
            logger.debug("Mirror detection disabled, using fallback")
            return None
        
        # Validate frame is likely the full original frame
        # This prevents accidentally passing cropped frames
        height, width = frame.shape[:2]
        if hasattr(self, '_expected_frame_size'):
            exp_h, exp_w = self._expected_frame_size
            if (width, height) != (exp_w, exp_h):
                logger.warning(f"Frame size mismatch: got {width}x{height}, expected {exp_w}x{exp_h}. "
                             f"Mirror detection may fail if frame is cropped!")
        else:
            # Store expected frame size on first run
            self._expected_frame_size = (height, width)
            logger.debug(f"Stored expected frame size: {width}x{height}")
        
        # Convert to grayscale for circle detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.mirror_detection_method == 'hough':
            # Use Hough Circle Transform for robust circle detection
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (9, 9), 2)
            
            # Detect circles using Hough transform
            circles = cv2.HoughCircles(
                blurred,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=gray.shape[0] // 2,  # Minimum distance between circles (expect only 1 mirror)
                param1=self.mirror_hough_param1,  # Canny edge detector high threshold
                param2=self.mirror_hough_param2,  # Accumulator threshold for circle centers
                minRadius=self.mirror_min_radius,
                maxRadius=self.mirror_max_radius
            )
            
            if circles is not None:
                # Convert to integer coordinates
                circles = np.round(circles[0, :]).astype("int")
                
                # Take the largest circle (most likely the mirror)
                largest_circle = max(circles, key=lambda c: c[2])  # Sort by radius
                center_x, center_y, radius = largest_circle
                
                logger.info(f"Mirror detected (Hough): center=({center_x}, {center_y}), radius={radius}")
                return (int(center_x), int(center_y), int(radius))
            else:
                logger.debug("No mirror circle detected with Hough transform")
                return None
        
        elif self.mirror_detection_method == 'contour':
            # Alternative: Use contour detection for the mirror
            # Apply edge detection
            edges = cv2.Canny(gray, self.mirror_canny_threshold1, self.mirror_canny_threshold2)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                logger.debug("No contours found for mirror detection")
                return None
            
            # Find the most circular contour
            best_circle = None
            best_circularity = 0
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < math.pi * self.mirror_min_radius ** 2:
                    continue
                if area > math.pi * self.mirror_max_radius ** 2:
                    continue
                
                # Calculate circularity: 4π(area/perimeter²)
                # Perfect circle = 1.0
                perimeter = cv2.arcLength(contour, True)
                if perimeter == 0:
                    continue
                    
                circularity = 4 * math.pi * area / (perimeter * perimeter)
                
                if circularity > best_circularity and circularity > 0.7:  # Must be reasonably circular
                    # Fit a circle to this contour
                    (x, y), radius = cv2.minEnclosingCircle(contour)
                    if self.mirror_min_radius <= radius <= self.mirror_max_radius:
                        best_circle = (int(x), int(y), int(radius))
                        best_circularity = circularity
            
            if best_circle:
                logger.info(f"Mirror detected (Contour): center=({best_circle[0]}, {best_circle[1]}), "
                          f"radius={best_circle[2]}, circularity={best_circularity:.2f}")
                return best_circle
            else:
                logger.debug("No circular contour found for mirror")
                return None
        
        else:
            logger.warning(f"Unknown mirror detection method: {self.mirror_detection_method}")
            return None
    
    def update_mirror_mask(self, frame):
        """
        Update the mirror mask if needed (every N frames or if not yet detected)
        
        IMPORTANT: This function ALWAYS uses the original full frame for detection
        to prevent losing the mirror when it's already been detected.
        
        Args:
            frame: Current camera frame (MUST be the full original frame, not cropped)
        """
        # Only detect mirror periodically to save computation
        self.mirror_detection_counter += 1
        
        if (self.mirror_circle is None or 
            self.mirror_detection_counter >= self.mirror_detection_interval):
            
            self.mirror_detection_counter = 0
            
            # CRITICAL: Always detect from the original full frame
            # This ensures we don't lose the mirror if detection temporarily fails
            detected_circle = self.detect_mirror_circle(frame)
            
            if detected_circle is not None:
                # Successfully detected - update mirror circle
                self.mirror_circle = detected_circle
                center_x, center_y, radius = detected_circle
                
                # Calculate crop region (bounding box around circle)
                # Ensure we don't go out of frame bounds
                height, width = frame.shape[:2]
                x1 = max(0, center_x - radius)
                y1 = max(0, center_y - radius)
                x2 = min(width, center_x + radius)
                y2 = min(height, center_y + radius)
                
                # Store crop region
                self.mirror_crop_region = (x1, y1, x2, y2)
                
                # Calculate new frame center (relative to cropped region)
                # The mirror center becomes the center of the cropped frame
                self.frame_center_x = center_x - x1
                self.frame_center_y = center_y - y1
                
                # Create a binary mask for the mirror area (in original frame coordinates)
                # The mask is white (255) inside the circle, black (0) outside
                self.mirror_mask = np.zeros((height, width), dtype=np.uint8)
                cv2.circle(self.mirror_mask, (center_x, center_y), radius, 255, -1)
                
                logger.info(f"Mirror updated: center=({center_x}, {center_y}), radius={radius}, "
                          f"crop=({x1},{y1},{x2},{y2}), new_frame_center=({self.frame_center_x}, {self.frame_center_y})")
            else:
                # Detection failed this time
                if self.mirror_circle is not None:
                    # We had a previous detection - KEEP IT, don't lose it!
                    logger.debug(f"Mirror detection failed this frame, keeping previous detection: "
                               f"center={self.mirror_circle[0:2]}, radius={self.mirror_circle[2]}")
                    # Don't reset mirror_circle - keep using the last good detection
                else:
                    # Never detected before - use fallback circular mask
                    height, width = frame.shape[:2]
                    self.mirror_mask = np.zeros((height, width), dtype=np.uint8)
                    cv2.circle(self.mirror_mask, 
                             (self.mask_center_x, self.mask_center_y), 
                             self.mask_radius, 255, -1)
                    
                    # Set default crop region (no crop)
                    self.mirror_crop_region = (0, 0, width, height)
                    
                    logger.warning(f"Mirror never detected, using fallback mask: "
                                 f"center=({self.mask_center_x}, {self.mask_center_y}), "
                                 f"radius={self.mask_radius}")
    
    def crop_to_mirror(self, image):
        """
        Crop image to the mirror bounding box
        
        Args:
            image: Input image to crop
            
        Returns:
            Cropped image (bounding box around mirror circle)
        """
        if not hasattr(self, 'mirror_crop_region') or self.mirror_crop_region is None:
            logger.warning("Mirror crop region not set, returning original image")
            return image
        
        x1, y1, x2, y2 = self.mirror_crop_region
        return image[y1:y2, x1:x2]
    
    def apply_mirror_mask(self, image):
        """
        Apply the mirror mask to an image (keeps only the mirror area)
        
        Args:
            image: Input image (can be BGR, grayscale, or binary mask)
            
        Returns:
            Masked image (black outside mirror, original inside)
        """
        if self.mirror_mask is None:
            logger.warning("Mirror mask not initialized, returning original image")
            return image
        
        # Apply mask using bitwise AND
        if len(image.shape) == 3:
            # Color image - apply mask to all channels
            return cv2.bitwise_and(image, image, mask=self.mirror_mask)
        else:
            # Grayscale or binary image
            return cv2.bitwise_and(image, image, mask=self.mirror_mask)
    
    def detect_ball(self, frame) -> BallDetectionResult:
        """
        Detect orange ball in the frame using HSV color filtering
        
        Args:
            frame: Input frame from camera (BGR from Picamera2)
            
        Returns:
            BallDetectionResult with detection info
        """
        # Update mirror mask if needed
        self.update_mirror_mask(frame)
        
        # Crop frame to mirror bounding box
        cropped_frame = self.crop_to_mirror(frame)
        
        # Convert to HSV (Picamera2 returns BGR format)
        hsv = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2HSV)
        
        # Create color mask for orange ball
        mask = cv2.inRange(hsv, self.lower_orange, self.upper_orange)
        
        # Find contours in the masked region
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        logger.debug(f"Ball detection: Found {len(contours)} contours")
        
        # Filter contours by area (only max area to avoid huge objects)
        filtered_contours = [x for x in contours if 
                           cv2.contourArea(x) < self.max_ball_area]
        
        logger.debug(f"Ball detection: {len(filtered_contours)} contours after max area filter (max_area={self.max_ball_area})")
        
        if not filtered_contours:
            logger.debug("Ball detection: No contours found after filtering")
            return BallDetectionResult(detected=False)
        
        largest_contour = max(filtered_contours, key=cv2.contourArea)
        (x, y), radius = cv2.minEnclosingCircle(largest_contour)
        
        center_x = int(x)
        center_y = int(y)
        radius = int(radius)
        
        logger.debug(f"Ball detection: Largest contour at ({center_x}, {center_y}) with radius {radius}")
        
        # Filter by minimum radius (more intuitive than area)
        min_radius = 2  # Minimum 2 pixel radius
        if radius < min_radius:
            logger.debug(f"Ball detection: Radius {radius} below minimum {min_radius}, rejecting")
            return BallDetectionResult(detected=False)
        
        # Calculate proximity info
        # Note: center_x and center_y are now relative to the CROPPED frame
        # frame_center_x and frame_center_y are the mirror center in cropped coordinates
        ball_area = math.pi * radius * radius
        horizontal_error = (center_x - self.frame_center_x) / self.frame_center_x
        vertical_error = (center_y - self.frame_center_y) / self.frame_center_y
        is_close = ball_area >= self.proximity_threshold
        is_centered = abs(horizontal_error) <= self.angle_tolerance
        
        logger.info(f"Ball detected: pos=({center_x}, {center_y}) radius={radius} area={ball_area:.1f} "
                   f"close={is_close} centered={is_centered}")
        
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
        # Update mirror mask if needed (will be cached if already done this frame)
        self.update_mirror_mask(frame)
        
        # Crop frame to mirror bounding box
        cropped_frame = self.crop_to_mirror(frame)
        
        # Convert to HSV (Picamera2 returns BGR format)
        hsv = cv2.cvtColor(cropped_frame, cv2.COLOR_BGR2HSV)
        
        blue_result = self._detect_single_goal(hsv, self.blue_goal_config)
        yellow_result = self._detect_single_goal(hsv, self.yellow_goal_config)
        
        return blue_result, yellow_result
    
    def _detect_single_goal(self, hsv_frame, goal_config) -> GoalDetectionResult:
        """
        Detect a single goal using HSV filtering
        
        Args:
            hsv_frame: HSV frame (already masked for mirror area)
            goal_config: Goal detection configuration
        """
        lower = np.array(goal_config["lower"])
        upper = np.array(goal_config["upper"])
        mask = cv2.inRange(hsv_frame, lower, upper)
        
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
            
            # Create vision data with frame and mirror info
            vision_data = VisionData(
                timestamp=time.time(),
                frame_id=camera.frame_counter,
                frame_center_x=camera.frame_center_x,
                frame_center_y=camera.frame_center_y
            )
            
            # Add mirror detection info if available
            if camera.mirror_circle is not None:
                vision_data.mirror_detected = True
                vision_data.mirror_center_x = camera.mirror_circle[0]
                vision_data.mirror_center_y = camera.mirror_circle[1]
                vision_data.mirror_radius = camera.mirror_circle[2]
            
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
    
    # Add "none detected" in center if no detections
    if not (vision_data.ball.detected or vision_data.blue_goal.detected or vision_data.yellow_goal.detected):
        center_x = frame_width // 2
        center_y = frame_height // 2
        
        # Get text size for centering
        text = "none detected"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        
        # Center the text
        text_x = center_x - text_width // 2
        text_y = center_y + text_height // 2
        
        # Draw text with outline for better visibility
        cv2.putText(display_frame, text, (text_x, text_y),
                   font, font_scale, (0, 0, 0), thickness + 2)  # Black outline
        cv2.putText(display_frame, text, (text_x, text_y),
                   font, font_scale, (255, 255, 255), thickness)  # White text
    
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
