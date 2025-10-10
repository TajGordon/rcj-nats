"""
Motor Controller for Soccer Robot (Multiprocessing/Threading Ready)

This module provides motor control with optional threading for non-blocking operation.
Can run in two modes:
1. Direct mode: Motor commands executed immediately (blocking I2C)
2. Threaded mode: Motor commands queued and executed in background thread (non-blocking)

Design decisions based on analysis of Nationals code and motor.py:
- Uses I2C (busio/smbus2) for motor communication
- No lerping in base implementation (can be added later if needed)
- Simple speed commands only (no complex state machines)
- Thread-based (not process) because I2C objects can't cross process boundaries
- Watchdog safety: auto-stop motors if no commands received for timeout period
- Uses stored calibration values from motor EEPROM (no need to recalibrate each boot)
- Logging instead of print for production/headless operation
- CRITICAL: Raises MotorInitializationError if motors fail to initialize (robot cannot operate safely)
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import time
import threading
import queue
import math

from hypemage.logger import get_logger

# Module logger
logger = get_logger(__name__)

try:
    import board
    import busio
    from steelbar_powerful_bldc_driver import PowerfulBLDCDriver
    _HAS_MOTOR_HARDWARE = True
    logger.info("Motor hardware libraries loaded successfully")
except ImportError as e:
    _HAS_MOTOR_HARDWARE = False
    logger.warning(f"Motor hardware libraries not available: {e}")


class MotorInitializationError(Exception):
    """Raised when motor initialization fails critically"""
    pass


@dataclass
class MotorCommand:
    """Motor command data structure"""
    type: str  # 'set_speeds', 'stop', 'shutdown'
    speeds: Optional[List[float]] = None  # List of speeds for each motor [-1.0 to 1.0]
    timestamp: float = 0.0


@dataclass
class MotorStatus:
    """Motor status/telemetry data"""
    motor_count: int
    speeds: List[float]  # Current commanded speeds
    is_running: bool
    last_command_time: float
    watchdog_active: bool


class MotorController:
    """
    Motor controller that can run in direct or threaded mode
    
    Direct mode: set_speeds() blocks until I2C write completes
    Threaded mode: set_speeds() returns immediately, commands executed in background
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, threaded: bool = True):
        """
        Initialize motor controller
        
        Args:
            config: Configuration dict with motor parameters
            threaded: If True, run motor control in background thread
            
        Raises:
            MotorInitializationError: If hardware libraries unavailable or I2C initialization fails
        """
        self.config = config or self._default_config()
        self.threaded = threaded
        
        # Motor hardware
        self.motors = []
        self.motor_count = 0
        self.i2c = None
        
        # Motor direction multipliers (for inverting motor directions)
        # Default: all motors forward, but can be overridden in config
        self.motor_multipliers = self.config.get('motor_multipliers', [1.0, -1.0, -1.0, 1.0])
        
        # Current state
        self.current_speeds = [0.0, 0.0, 0.0, 0.0]
        self.last_command_time = 0.0
        
        # Threading
        self.cmd_queue = queue.Queue(maxsize=10)
        self.motor_thread = None
        self.stop_event = threading.Event()
        
        # Watchdog safety
        self.watchdog_enabled = self.config.get('watchdog_enabled', True)
        self.watchdog_timeout = self.config.get('watchdog_timeout', 0.5)  # seconds
        
        # Initialize hardware (raises MotorInitializationError on critical failure)
        success = self._init_motors()
        if not success:
            raise MotorInitializationError("Failed to initialize motor controller - cannot operate safely")
        
        # Start thread if in threaded mode
        if self.threaded:
            self.start_thread()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default motor configuration"""
        return {
            'motor_addresses': [26, 27, 29, 25],  # Example addresses
            'max_speed': 400_000_000,
            'current_limit_foc': 65536 * 3,
            'id_pid': {'kp': 1500, 'ki': 200},
            'iq_pid': {'kp': 1500, 'ki': 200},
            'speed_pid': {'kp': 0.04, 'ki': 0.0004, 'kd': 0.03},
            'position_pid': {'kp': 275, 'ki': 0, 'kd': 0},
            'position_region_boundary': 250000,
            'operating_mode': 3,  # FOC
            'sensor_mode': 1,     # Sin/cos encoder
            'command_mode': 12,   # Speed mode
            'watchdog_enabled': True,
            'watchdog_timeout': 0.5,
            'calibration': {
                'elecangleoffset': 1544835584,
                'sincoscentre': 1255
            }
        }
    
    def _init_motors(self) -> bool:
        """
        Initialize motor hardware
        
        Returns:
            True if motors initialized successfully, False if critical failure
        """
        if not _HAS_MOTOR_HARDWARE:
            logger.critical("Motor hardware libraries not available - CANNOT OPERATE")
            logger.critical("Install required libraries: board, busio, steelbar_powerful_bldc_driver") # TODO: make it only say you need libs if u actl need those libs
            return False
        
        try:
            # Initialize I2C
            self.i2c = busio.I2C(board.SCL, board.SDA)
            logger.info("I2C bus initialized")
            
            # Initialize each motor
            motor_addrs = self.config['motor_addresses']
            for i, addr in enumerate(motor_addrs):
                try:
                    motor = PowerfulBLDCDriver(self.i2c, addr)
                    
                    # Check firmware version
                    fw_version = motor.get_firmware_version()
                    if fw_version != 3:
                        logger.warning(f"Motor {i} firmware version {fw_version} (expected 3)")
                    else:
                        logger.debug(f"Motor {i} firmware version {fw_version} OK")
                    
                    # Configure motor
                    self._configure_motor(motor)
                    
                    self.motors.append(motor)
                    logger.info(f"Motor {i} initialized at address 0x{addr:02X}")
                    
                except Exception as e:
                    logger.error(f"Failed to initialize motor {i} at address 0x{addr:02X}: {e}")
                    self.motors.append(None)
            
            self.motor_count = len([m for m in self.motors if m is not None])
            
            # Check if we have enough motors
            if self.motor_count == 0:
                logger.critical("CRITICAL: No motors initialized - robot cannot operate")
                return False
            elif self.motor_count < len(motor_addrs):
                logger.error(f"Only {self.motor_count}/{len(motor_addrs)} motors initialized")
                logger.error("Robot may not operate correctly - missing motors")
                return False  # Treat as critical - need all motors
            else:
                logger.info(f"All {self.motor_count} motors initialized successfully")
                return True
            
        except Exception as e:
            logger.critical(f"CRITICAL: Failed to initialize I2C/motors: {e}", exc_info=True)
            self.motors = [None] * 4
            self.motor_count = 0
            return False
    
    def _configure_motor(self, motor):
        """
        Configure a single motor with PID constants and limits
        
        Uses stored calibration values from motor EEPROM.
        Only sets PID/limits that are explicitly configured.
        """
        cfg = self.config
        
        # Set current and speed limits
        motor.set_current_limit_foc(cfg['current_limit_foc'])
        motor.set_speed_limit(cfg['max_speed'])
        
        # Set PID constants (will be stored in motor EEPROM)
        motor.set_id_pid_constants(cfg['id_pid']['kp'], cfg['id_pid']['ki'])
        motor.set_iq_pid_constants(cfg['iq_pid']['kp'], cfg['iq_pid']['ki'])
        motor.set_speed_pid_constants(
            cfg['speed_pid']['kp'],
            cfg['speed_pid']['ki'],
            cfg['speed_pid']['kd']
        )
        motor.set_position_pid_constants(
            cfg['position_pid']['kp'],
            cfg['position_pid']['ki'],
            cfg['position_pid']['kd']
        )
        motor.set_position_region_boundary(cfg['position_region_boundary'])
        
        # Set operating modes
        motor.configure_operating_mode_and_sensor(
            cfg['operating_mode'],
            cfg['sensor_mode']
        )
        motor.configure_command_mode(cfg['command_mode'])
        
        # Log stored calibration values (read from EEPROM)
        try:
            elec_offset = motor.get_calibration_ELECANGLEOFFSET()
            sincos_centre = motor.get_calibration_SINCOSCENTRE()
            logger.debug(f"Motor calibration - ELECANGLEOFFSET: {elec_offset}, SINCOSCENTRE: {sincos_centre}")
        except Exception as e:
            logger.warning(f"Could not read calibration values: {e}")
        
        # Note: Calibration values are stored in motor EEPROM automatically
        # No need to set them unless you want to override with force_calibration
    
    def start_thread(self):
        """Start the motor control thread"""
        if self.motor_thread is not None:
            return
        
        self.stop_event.clear()
        self.motor_thread = threading.Thread(target=self._motor_worker, daemon=True)
        self.motor_thread.start()
        logger.info("Motor control thread started")
    
    def stop_thread(self):
        """Stop the motor control thread"""
        if self.motor_thread is None:
            return
        
        self.stop_event.set()
        self.motor_thread.join(timeout=2)
        self.motor_thread = None
        logger.info("Motor control thread stopped")
    
    def _motor_worker(self):
        """
        Background thread that processes motor commands
        
        This thread:
        - Processes commands from the queue
        - Implements watchdog safety (auto-stop if no commands)
        - Sends I2C commands to motors
        """
        last_watchdog_check = time.time()
        
        while not self.stop_event.is_set():
            # Try to get a command (non-blocking with timeout)
            try:
                cmd = self.cmd_queue.get(timeout=0.01)
            except queue.Empty:
                cmd = None
            
            # Process command
            if cmd:
                if cmd.type == 'set_speeds':
                    self._execute_set_speeds(cmd.speeds)
                    self.last_command_time = time.time()
                elif cmd.type == 'stop':
                    self._execute_stop()
                    self.last_command_time = time.time()
                elif cmd.type == 'shutdown':
                    break
            
            # Watchdog check
            current_time = time.time()
            if self.watchdog_enabled and (current_time - last_watchdog_check) > 0.05:
                time_since_command = current_time - self.last_command_time
                if time_since_command > self.watchdog_timeout:
                    # No command received in timeout period - safety stop
                    self._execute_stop()
                last_watchdog_check = current_time
            
            # Small sleep to control loop rate (~100 Hz)
            time.sleep(0.01)
        
        # Final stop on shutdown
        self._execute_stop()
    
    def _execute_set_speeds(self, speeds: List[float]):
        """
        Execute motor speed commands
        
        Args:
            speeds: List of speeds [-1.0 to 1.0] for each motor
        """
        if len(speeds) != len(self.motors):
            logger.warning(f"Speed list length {len(speeds)} != motor count {len(self.motors)}")
            return
        
        self.current_speeds = list(speeds)
        
        for i, (motor, speed) in enumerate(zip(self.motors, speeds)):
            if motor is None:
                continue
            
            try:
                # Apply motor multiplier (for direction correction)
                speed = speed * self.motor_multipliers[i]
                
                # Clamp speed to [-1.0, 1.0]
                speed = max(-1.0, min(1.0, speed))
                
                # Scale to motor units
                speed_cmd = int(self.config['max_speed'] * speed)
                
                motor.set_speed(speed_cmd)
                
            except Exception as e:
                logger.error(f"Error setting motor {i} speed: {e}")
    
    def _execute_stop(self):
        """Stop all motors"""
        self._execute_set_speeds([0.0] * len(self.motors))
    
    # ==================== PUBLIC API ====================
    
    def set_speeds(self, speeds: List[float]):
        """
        Set motor speeds
        
        Args:
            speeds: List of speeds [-1.0 to 1.0] for each motor
                    Order: [back_left, back_right, front_left, front_right]
        
        In threaded mode: queues command and returns immediately
        In direct mode: blocks until I2C write completes
        """
        if self.threaded:
            # Queue command (non-blocking)
            cmd = MotorCommand(
                type='set_speeds',
                speeds=list(speeds),
                timestamp=time.time()
            )
            try:
                self.cmd_queue.put(cmd, block=False)
            except queue.Full:
                # Queue full - drop oldest and retry
                try:
                    self.cmd_queue.get_nowait()
                    self.cmd_queue.put(cmd, block=False)
                except Exception:
                    pass
        else:
            # Direct execution (blocking)
            self._execute_set_speeds(speeds)
            self.last_command_time = time.time()
    
    def stop(self):
        """Stop all motors"""
        if self.threaded:
            cmd = MotorCommand(type='stop', timestamp=time.time())
            try:
                self.cmd_queue.put(cmd, block=False)
            except queue.Full:
                pass
        else:
            self._execute_stop()
    
    def move_robot_relative(self, angle: float, speed: float, rotation: float = 0.0):
        """
        Move robot in a direction relative to the robot's current orientation
        
        Uses trigonometry to calculate motor speeds for omnidirectional movement.
        Motor arrangement (looking from above, motor order in array):
            [0] Back-left      [1] Front-left
                    \\  /
                     \\/
                     /\\
                    /  \\
            [2] Front-right    [3] Back-right
        
        Args:
            angle: Direction in degrees (0=forward, 90=right, 180=back, 270=left)
            speed: Speed magnitude [0.0 to 1.0]
            rotation: Rotation component [-1.0 to 1.0] (positive = clockwise)
        
        Example:
            controller.move_robot_relative(0, 0.5)       # Move forward at half speed
            controller.move_robot_relative(90, 0.3)      # Move right at 30% speed
            controller.move_robot_relative(45, 0.5, 0.2) # Move diagonal with slight rotation
        """
        # Convert angle to radians
        angle_rad = math.radians(angle)
        
        # Calculate velocity components
        vx = speed * math.sin(angle_rad)  # Left/right component
        vy = speed * math.cos(angle_rad)  # Forward/back component
        
        # Calculate motor speeds using omniwheel kinematics
        # Each motor contributes to: forward/back, left/right, and rotation
        # Motor order: [back_left, front_left, front_right, back_right]
        back_left = vy - vx + rotation
        front_left = vy + vx + rotation
        front_right = vy - vx - rotation
        back_right = vy + vx - rotation
        
        # Normalize to keep all speeds within [-1.0, 1.0]
        max_speed = max(abs(back_left), abs(front_left), abs(front_right), abs(back_right))
        if max_speed > 1.0:
            back_left /= max_speed
            front_left /= max_speed
            front_right /= max_speed
            back_right /= max_speed
        
        self.set_speeds([back_left, front_left, front_right, back_right])
    
    def move_field_relative(self, angle: float, speed: float, rotation: float, heading: float):
        """
        Move robot in a direction relative to the field (absolute direction)
        
        This compensates for the robot's current heading to move in a field-absolute direction.
        For example, if you want to move "north" on the field regardless of which way
        the robot is facing.
        
        Args:
            angle: Target direction in field coordinates (0=towards enemy goal)
            speed: Speed magnitude [0.0 to 1.0]
            rotation: Rotation component [-1.0 to 1.0]
            heading: Robot's current heading in degrees (from IMU or localization)
        
        Example:
            # Robot is facing 45° right, but we want to move straight towards goal
            controller.move_field_relative(0, 0.5, 0, robot_heading)
            # This will automatically adjust to move "field forward" regardless of robot orientation
        """
        # Compensate for robot heading
        adjusted_angle = angle - heading
        
        # Use robot-relative movement with adjusted angle
        self.move_robot_relative(adjusted_angle, speed, rotation)
    
    def get_status(self) -> MotorStatus:
        """Get current motor status"""
        return MotorStatus(
            motor_count=self.motor_count,
            speeds=list(self.current_speeds),
            is_running=(self.motor_thread is not None and self.motor_thread.is_alive()) if self.threaded else True,
            last_command_time=self.last_command_time,
            watchdog_active=self.watchdog_enabled
        )
    
    def shutdown(self):
        """Shutdown motor controller"""
        if self.threaded:
            cmd = MotorCommand(type='shutdown')
            try:
                self.cmd_queue.put(cmd, timeout=1)
            except Exception:
                pass
            self.stop_thread()
        else:
            self._execute_stop()


# ==================== SIMPLE WRAPPER FOR DIRECT USE ====================

class SimpleMotorController:
    """
    Simplified motor controller for direct use without threading
    
    This matches the pattern from motor.py - simple and blocking.
    Use this if you don't need threading or just want to send commands directly.
    """
    
    def __init__(self, motor_addresses: List[int], max_speed: int = 400_000_000):
        """
        Initialize simple motor controller
        
        Args:
            motor_addresses: List of I2C addresses for motors
            max_speed: Maximum motor speed in controller units
        """
        self.motors = []
        self.max_speed = max_speed
        
        if not _HAS_MOTOR_HARDWARE:
            logger.warning("Running in simulation mode - no motor hardware")
            return
        
        i2c = busio.I2C(board.SCL, board.SDA)
        
        for i, addr in enumerate(motor_addresses):
            try:
                motor = PowerfulBLDCDriver(i2c, addr)
                # Minimal config - just speed mode
                motor.configure_operating_mode_and_sensor(3, 1)  # FOC + encoder
                motor.configure_command_mode(12)  # Speed mode
                motor.set_speed_limit(max_speed)
                self.motors.append(motor)
                logger.debug(f"Simple motor {i} ready at address 0x{addr:02X}")
            except Exception as e:
                logger.error(f"Failed motor {i}: {e}")
                self.motors.append(None)
    
    def set_speeds(self, speeds: List[float]):
        """
        Set motor speeds (blocking I2C write)
        
        Args:
            speeds: List of speeds [-1.0 to 1.0]
        """
        for motor, speed in zip(self.motors, speeds):
            if motor is None:
                continue
            try:
                speed = max(-1.0, min(1.0, speed))
                motor.set_speed(int(self.max_speed * speed))
            except Exception as e:
                logger.error(f"Motor error: {e}")
    
    def stop(self):
        """Stop all motors"""
        self.set_speeds([0.0] * len(self.motors))


if __name__ == '__main__':
    # Test example
    print("Testing motor controller...")
    
    # Example 1: Threaded mode (recommended)
    print("\n=== Threaded Mode Test ===")
    config = {
        'motor_addresses': [26, 27, 29, 25],
        'watchdog_enabled': True,
        'watchdog_timeout': 1.0
    }
    
    controller = MotorController(config=config, threaded=True)
    
    # Send some commands
    print("Sending forward command...")
    controller.set_speeds([0.3, 0.3, 0.3, 0.3])
    time.sleep(2)
    
    print("Sending turn command...")
    controller.set_speeds([0.3, -0.3, 0.3, -0.3])
    time.sleep(2)
    
    print("Stopping...")
    controller.stop()
    time.sleep(1)
    
    # Check status
    status = controller.get_status()
    print(f"Status: {status}")
    
    # Watchdog test - don't send commands, should auto-stop
    print("\nWatchdog test - waiting for timeout...")
    controller.set_speeds([0.2, 0.2, 0.2, 0.2])
    time.sleep(2)  # Watchdog will kick in after 1 second
    
    status = controller.get_status()
    print(f"After watchdog: speeds={status.speeds}")
    
    controller.shutdown()
    print("Test complete!")
