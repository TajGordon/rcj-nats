"""
Debug Data Structures

Dataclasses for debug information from each subsystem.
Only used when debug mode is enabled (--debug flag).
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import time


@dataclass
class CameraDebugData:
    """Debug data from camera process"""
    timestamp: float
    frame_id: int
    fps: float
    processing_time_ms: float
    
    # Frame (JPEG compressed for network efficiency)
    frame_jpeg: Optional[bytes] = None
    
    # Ball detection
    ball_detected: bool = False
    ball_x: int = 0
    ball_y: int = 0
    ball_radius: int = 0
    ball_area: float = 0.0
    
    # Goal detection
    blue_goal_detected: bool = False
    blue_goal_x: int = 0
    blue_goal_width: int = 0
    
    yellow_goal_detected: bool = False
    yellow_goal_x: int = 0
    yellow_goal_width: int = 0
    
    # HSV ranges (for debugging color calibration)
    ball_hsv_lower: Optional[List[int]] = None
    ball_hsv_upper: Optional[List[int]] = None


@dataclass
class MotorDebugData:
    """Debug data from motor controller"""
    timestamp: float
    
    # Commanded speeds [-1.0, 1.0]
    motor_speeds: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    
    # Status
    watchdog_active: bool = True
    last_command_age_ms: float = 0.0
    
    # Motor health (if available from firmware)
    motor_temps: Optional[List[float]] = None
    motor_currents: Optional[List[float]] = None


@dataclass
class LocalizationDebugData:
    """Debug data from localization system"""
    timestamp: float
    
    # Position estimate
    x: float = 0.0
    y: float = 0.0
    heading: float = 0.0
    confidence: float = 0.0
    
    # Sensor readings
    imu_heading: Optional[float] = None
    tof_distances: Optional[List[float]] = None
    
    processing_time_ms: float = 0.0


@dataclass
class ButtonDebugData:
    """Debug data from button system"""
    timestamp: float
    button_states: Dict[str, bool] = field(default_factory=dict)
    last_press: Optional[str] = None
    last_press_time: Optional[float] = None


@dataclass
class FSMDebugData:
    """Debug data from main FSM (Scylla)"""
    timestamp: float
    current_state: str
    previous_state: str
    time_in_state: float
    component_status: Dict[str, bool] = field(default_factory=dict)
