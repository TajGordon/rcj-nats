""" Scylla - Main robot logic FSM (Finite State Machine)

States manage robot behavior. Each state handler receives sensor data
and can transition to other states based on logic.

CRITICAL ERROR HANDLING:
- Motors fail to init: Robot exits immediately (cannot operate safely)
- Camera fails in CHASE_BALL: Robot exits (cannot chase without vision)
- Localization fails: Robot continues with warning (can still move with camera only)
"""

from dataclasses import dataclass, field
from typing import Dict, Set, Callable, Optional, Any, List
from threading import Thread, Event as ThreadEvent
from multiprocessing import Process, Queue, Event, get_context
from enum import Enum, auto
import time
import sys
import math
import atexit
import signal

from hypemage.logger import get_logger
from hypemage.motor_control import MotorController, MotorInitializationError

# Initialize logger early so it's available for import error handling
logger = get_logger(__name__)

# Try to import camera module, but don't fail if cv2 is not available
try:
    from hypemage.camera import CameraProcess, CameraInitializationError
    CAMERA_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Camera module not available: {e}")
    logger.warning("Robot will run without camera support")
    CAMERA_AVAILABLE = False
    CameraProcess = None
    CameraInitializationError = Exception

# Try to import dribbler and kicker, but continue if they fail
try:
    from hypemage.dribbler_control import DribblerController
    DRIBBLER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Dribbler module not available: {e}")
    DRIBBLER_AVAILABLE = False
    DribblerController = None

# Try to import Motor class directly for simple dribbler control
try:
    from motors.motor import Motor
    MOTOR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Motor module not available: {e}")
    MOTOR_AVAILABLE = False
    Motor = None

try:
    from hypemage.kicker_control import KickerController
    KICKER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Kicker module not available: {e}")
    KICKER_AVAILABLE = False
    KickerController = None


@dataclass
class ComponentStatus:
    """Tracks initialization status of critical and non-critical components"""
    # Critical components (robot cannot operate without these)
    motors: bool = False
    camera: bool = False  # Critical if in vision-dependent state
    
    # Non-critical components (robot can operate in degraded mode)
    localization: bool = False
    goal_localizer: bool = False
    imu: bool = False
    tof_sensors: List[bool] = field(default_factory=lambda: [False]*4)
    dribbler: bool = False
    kicker: bool = False
    
    def all_critical_ok(self) -> bool:
        """Check if all critical components are working"""
        return self.motors  # Camera checked per-state
    
    def summary(self) -> str:
        """Get status summary string"""
        critical = f"Motors: {'✓' if self.motors else '✗'}, Camera: {'✓' if self.camera else '✗'}"
        non_critical = f"Localization: {'✓' if self.localization else '✗'}, Dribbler: {'✓' if self.dribbler else '✗'}, Kicker: {'✓' if self.kicker else '✗'}"
        return f"[CRITICAL: {critical}] [NON-CRITICAL: {non_critical}]"
        return f"[CRITICAL: {critical}] [NON-CRITICAL: {non_critical}]"


class State(Enum):
    """All possible robot states"""
    OFF_FIELD = auto()
    PAUSED = auto()
    CHASE_BALL = auto()
    DEFEND_GOAL = auto()
    ATTACK_GOAL = auto()
    LINEUP_KICK = auto()
    STOPPED = auto()
    MOVE_IN_SQUARE = auto()  # Example state for testing movement
    MOVE_STRAIGHT = auto()   # Move forward in straight line


@dataclass
class StateConfig:
    """Configuration for what resources a state needs"""
    needs_camera: bool = False
    needs_localization: bool = False
    needs_motors: bool = False
    update_rate_hz: float = 20.0  # how fast to run this state's logic


class Scylla:
    """Main robot FSM controller"""
    
    # Define state configurations (what each state needs)
    STATE_CONFIGS: Dict[State, StateConfig] = {
        State.OFF_FIELD: StateConfig(
            needs_camera=False,
            needs_localization=False,
            needs_motors=False,
            update_rate_hz=5.0
        ),
        State.PAUSED: StateConfig(
            needs_camera=False,
            needs_localization=False,
            needs_motors=False,
            update_rate_hz=5.0
        ),
        State.CHASE_BALL: StateConfig(
            needs_camera=True,
            needs_localization=True,
            needs_motors=True,
            update_rate_hz=30.0
        ),
        State.DEFEND_GOAL: StateConfig(
            needs_camera=True,
            needs_localization=True,
            needs_motors=True,
            update_rate_hz=20.0
        ),
        State.ATTACK_GOAL: StateConfig(
            needs_camera=True,
            needs_localization=True,
            needs_motors=True,
            update_rate_hz=30.0
        ),
        State.LINEUP_KICK: StateConfig(
            needs_camera=True,
            needs_localization=True,
            needs_motors=True,
            update_rate_hz=30.0
        ),
        State.STOPPED: StateConfig(
            needs_camera=False,
            needs_localization=False,
            needs_motors=True,  # need motors to send stop command
            update_rate_hz=10.0
        ),
        State.MOVE_IN_SQUARE: StateConfig(
            needs_camera=False,
            needs_localization=False,
            needs_motors=True,
            update_rate_hz=20.0
        ),
        State.MOVE_STRAIGHT: StateConfig(
            needs_camera=False,
            needs_localization=False,
            needs_motors=True,
            update_rate_hz=20.0
        ),
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the FSM and resources
        
        Raises:
            SystemExit: If critical components fail to initialize
        """
        # Apply robot-specific configuration overrides
        from hypemage.robot_detection import get_robot_config_overrides
        
        self.config = config or {}
        
        # Auto-detect robot and apply overrides
        robot_overrides = get_robot_config_overrides()
        logger.info(f"Detected robot: {robot_overrides['robot_name']}")
        logger.info(f"Motor addresses: {robot_overrides['motor_addresses']}")
        
        # Merge robot-specific overrides into config
        # Only override if not explicitly set in provided config
        if 'motor_addresses' not in self.config or not self.config['motor_addresses']:
            self.config['motor_addresses'] = robot_overrides['motor_addresses']
        
        if 'dribbler' not in self.config:
            self.config['dribbler'] = {}
        if 'address' not in self.config['dribbler']:
            self.config['dribbler']['address'] = robot_overrides['dribbler']['address']
        
        self.current_state = State.PAUSED
        self.previous_state = None
        
        # Global pause/play state
        self._is_paused = False  # False = playing, True = paused
        self._pause_state_backup = {}  # Store state variables when pausing
        
        # Component status tracking
        self.status = ComponentStatus()
        
        # Multiprocessing context
        self.ctx = get_context('spawn')
        
        # Process management
        self.processes: Dict[str, Any] = {}  # Type hint relaxed for SpawnProcess
        self.queues: Dict[str, Any] = {}
        self.events: Dict[str, Any] = {}
        
        # Shared state/data
        self.latest_camera_data = None
        self.latest_localization_data = None
        self.latest_button_input = None
        
        # Chase ball tracking
        self._frames_without_ball = 0  # Counter for frames without ball detection
        self._last_ball_was_close = False  # Track if last seen ball was close
        
        # Timing
        self.last_update_time = 0.0
        
        # Motor controller (critical - must init first)
        self.motor_controller = None
        
        # Dribbler and kicker controllers (non-critical)
        self.dribbler_controller = None
        self.simple_dribbler_motor = None  # Simple motor for constant dribbler speed
        self.kicker_controller = None
        
        # Initialize resources
        self._init_queues()
        self._init_events()
        self._init_critical_components()
        self._init_non_critical_components()
        
        # Register emergency shutdown handlers
        self._register_shutdown_handlers()
    
    def _register_shutdown_handlers(self):
        """
        Register handlers to ensure motors stop on any exit condition
        
        This provides multiple layers of safety:
        - atexit: Called on normal Python exit
        - SIGINT: Ctrl+C (handled in main loop)
        - SIGTERM: Kill signal
        """
        # Register atexit handler (called on normal exit)
        atexit.register(self._emergency_motor_stop)
        
        # Register SIGTERM handler (kill signal)
        def sigterm_handler(signum, frame):
            logger.warning(f"SIGTERM received - initiating shutdown")
            self._emergency_motor_stop()
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, sigterm_handler)
        
        logger.info("Emergency shutdown handlers registered")
    
    def _emergency_motor_stop(self):
        """
        Emergency motor stop - called by atexit and signal handlers
        
        This is a failsafe to ensure motors always stop, even on crashes.
        It's safe to call multiple times.
        """
        if hasattr(self, 'motor_controller') and self.motor_controller:
            try:
                self.motor_controller.stop()
                logger.debug("Emergency motor stop executed")
            except Exception as e:
                # Don't let exceptions here crash the shutdown process
                logger.error(f"Emergency motor stop failed: {e}")
        
        # Also stop dribbler
        if hasattr(self, 'dribbler_controller') and self.dribbler_controller:
            try:
                self.dribbler_controller.stop()
                logger.debug("Emergency dribbler stop executed")
            except Exception as e:
                logger.error(f"Emergency dribbler stop failed: {e}")
        
        # Stop simple dribbler motor
        if hasattr(self, 'simple_dribbler_motor') and self.simple_dribbler_motor:
            try:
                self.simple_dribbler_motor.set_speed(0)
                logger.debug("Emergency simple dribbler motor stop executed")
            except Exception as e:
                logger.error(f"Emergency simple dribbler motor stop failed: {e}")
    
    def _init_critical_components(self):
        """
        Initialize critical components (motors)
        Exits immediately if motors fail to initialize
        """
        logger.info("Initializing critical components...")
        
        # Initialize motors (CRITICAL - robot cannot operate without motors)
        try:
            logger.info("Initializing motor controller...")
            motor_config = self.config.get('motors', {})
            self.motor_controller = MotorController(config=motor_config, threaded=True)
            self.status.motors = True
            logger.info("✓ Motor controller initialized successfully")
        except MotorInitializationError as e:
            logger.critical(f"✗ CRITICAL: Motor initialization failed: {e}")
            logger.critical("Robot cannot operate safely without motors")
            logger.critical("Exiting...")
            sys.exit(1)
        except Exception as e:
            logger.critical(f"✗ CRITICAL: Unexpected error initializing motors: {e}", exc_info=True)
            logger.critical("Exiting...")
            sys.exit(1)
        
        # Log component status
        logger.info(f"Component status: {self.status.summary()}")
    
    def _init_non_critical_components(self):
        """
        Initialize non-critical components (dribbler, kicker)
        Robot continues if these fail - they are not essential for basic operation
        """
        logger.info("Initializing non-critical components...")
        
        # Initialize dribbler (NON-CRITICAL)
        if DRIBBLER_AVAILABLE:
            try:
                logger.info("Initializing dribbler controller...")
                dribbler_config = self.config.get('dribbler', {})
                # Auto-detect address based on hostname if not specified
                dribbler_address = dribbler_config.get('address', None)
                self.dribbler_controller = DribblerController(
                    address=dribbler_address,
                    threaded=True
                )
                self.status.dribbler = True
                logger.info("✓ Dribbler controller initialized successfully")
            except Exception as e:
                logger.warning(f"⚠️  Dribbler initialization failed: {e}")
                logger.warning("Robot will continue without dribbler")
                self.dribbler_controller = None
        else:
            logger.warning("Dribbler module not available - skipping initialization")
            self.dribbler_controller = None
        
        # Initialize simple dribbler motor (NON-CRITICAL) - runs at constant speed 3.0
        if MOTOR_AVAILABLE:
            try:
                logger.info("Initializing simple dribbler motor...")
                # Determine dribbler motor address based on hostname
                import socket
                hostname = socket.gethostname()
                if 'f7' in hostname.lower():
                    dribbler_address = 29
                    logger.info("Detected f7 robot - using dribbler address 29")
                elif 'm7' in hostname.lower():
                    dribbler_address = 30
                    logger.info("Detected m7 robot - using dribbler address 30")
                else:
                    dribbler_address = 30  # Default to m7
                    logger.info(f"Unknown hostname '{hostname}' - defaulting to dribbler address 30")
                
                self.simple_dribbler_motor = Motor(dribbler_address)
                logger.info(f"✓ Simple dribbler motor initialized at address {dribbler_address}")
            except Exception as e:
                logger.warning(f"⚠️  Simple dribbler motor initialization failed: {e}")
                logger.warning("Robot will continue without simple dribbler")
                self.simple_dribbler_motor = None
        else:
            logger.warning("Motor module not available - skipping simple dribbler initialization")
            self.simple_dribbler_motor = None
        
        # Initialize kicker (NON-CRITICAL)
        if KICKER_AVAILABLE:
            try:
                logger.info("Initializing kicker controller...")
                kicker_config = self.config.get('kicker', {})
                kick_duration = kicker_config.get('kick_duration', 0.15)
                self.kicker_controller = KickerController(kick_duration=kick_duration)
                self.status.kicker = True
                logger.info("✓ Kicker controller initialized successfully")
            except Exception as e:
                logger.warning(f"⚠️  Kicker initialization failed: {e}")
                logger.warning("Robot will continue without kicker")
                self.kicker_controller = None
        else:
            logger.warning("Kicker module not available - skipping initialization")
            self.kicker_controller = None
        
        # Log updated component status
        logger.info(f"Component status: {self.status.summary()}")
    
    def _init_queues(self):
        """Create all necessary queues"""
        # Camera
        self.queues['camera_cmd'] = self.ctx.Queue()
        self.queues['camera_out'] = self.ctx.Queue()
        
        # Localization
        self.queues['loc_cmd'] = self.ctx.Queue()
        self.queues['loc_out'] = self.ctx.Queue()
        
        # # Motor control (if you decide to make it a process)
        # self.queues['motor_cmd'] = self.ctx.Queue()
        
        # Button input
        self.queues['button_out'] = self.ctx.Queue()
    
    def _init_events(self):
        """Create all necessary events"""
        self.events['stop'] = self.ctx.Event()
        self.events['camera_active'] = self.ctx.Event()
        self.events['loc_active'] = self.ctx.Event()
    
    def start(self):
        """Start the FSM main loop"""
        self._start_always_on_processes()
        
        # Start simple dribbler motor at speed 3.0 (runs throughout the game)
        if self.simple_dribbler_motor:
            try:
                logger.info("Starting simple dribbler motor at speed 3.0...")
                self.simple_dribbler_motor.set_speed(3.0)
                logger.info("✓ Dribbler motor running at speed 3.0")
            except Exception as e:
                logger.warning(f"⚠️  Failed to start dribbler motor: {e}")
        
        try:
            while not self.events['stop'].is_set():
                self._update()
        except KeyboardInterrupt:
            print("\nScylla interrupted by user (Ctrl+C)")
            logger.info("Keyboard interrupt received - initiating shutdown")
        except Exception as e:
            print(f"\n❌ FATAL ERROR: {e}")
            logger.critical(f"Unhandled exception in main loop: {e}", exc_info=True)
        finally:
            self.shutdown()
    
    def _start_always_on_processes(self):
        """Start processes that should always be running (like button input)"""
        # Button poller (always on to detect pause/emergency stop)
        self.button_stop_evt = ThreadEvent()
        self.button_thread = Thread(
            target=self._button_poller,
            args=(self.button_stop_evt, self.queues['button_out']),
            daemon=True
        )
        self.button_thread.start()
    
    def _update(self):
        """Main update loop - runs every iteration"""
        try:
            current_time = time.time()
            state_cfg = self.STATE_CONFIGS[self.current_state]
            
            # Calculate target delta based on state's update rate
            target_dt = 1.0 / state_cfg.update_rate_hz
            
            # Check if enough time has passed for this state's update rate
            if current_time - self.last_update_time < target_dt:
                time.sleep(0.001)  # small sleep to avoid busy-wait
                return
            
            self.last_update_time = current_time
            
            # Manage resources based on current state needs
            self._manage_resources(state_cfg)
            
            # Gather sensor data if state needs it
            if state_cfg.needs_camera:
                self._poll_camera_data()
            
            if state_cfg.needs_localization:
                self._poll_localization_data()
            
            # Always poll button input (for emergency stop, pause, etc.)
            self._poll_button_input()
            
            # Dispatch to current state handler
            state_handler = self._get_state_handler(self.current_state)
            if state_handler:
                state_handler()
        except Exception as e:
            # Catch any exception in state handlers or update loop
            logger.error(f"Error in _update() for state {self.current_state.name}: {e}", exc_info=True)
            # Stop motors immediately for safety
            if self.motor_controller:
                try:
                    self.motor_controller.stop()
                    logger.info("Motors stopped due to error")
                except:
                    pass
            # Re-raise to trigger main loop exception handler
            raise
    
    def _manage_resources(self, state_cfg: StateConfig):
        """Start/stop processes based on state needs"""
        # Camera
        if state_cfg.needs_camera and 'camera' not in self.processes:
            self._start_camera_process()
        elif not state_cfg.needs_camera and 'camera' in self.processes:
            self._stop_camera_process()
        
        # Localization
        if state_cfg.needs_localization and 'localization' not in self.processes:
            self._start_localization_process()
        elif not state_cfg.needs_localization and 'localization' in self.processes:
            self._stop_localization_process()
    
    def _start_camera_process(self):
        """Start the camera process"""
        if not CAMERA_AVAILABLE:
            logger.warning("Camera module not available - cannot start camera process")
            return
        
        from hypemage.camera import start as camera_start
        
        proc = self.ctx.Process(
            target=camera_start,
            args=(
                self.queues['camera_cmd'],
                self.queues['camera_out'],
                self.events['camera_active'],
                self.config.get('camera', None)
            )
        )
        proc.start()
        self.processes['camera'] = proc
        print("Camera process started")
    
    def _stop_camera_process(self):
        """Stop the camera process"""
        if 'camera' in self.processes:
            self.queues['camera_cmd'].put({'type': 'stop'})
            self.events['camera_active'].set()
            self.processes['camera'].join(timeout=2)
            if self.processes['camera'].is_alive():
                self.processes['camera'].terminate()
            del self.processes['camera']
            print("Camera process stopped")
    
    def _start_localization_process(self):
        """Start the localization process"""
        # Import your localization start function
        # from mproc.localization import start as loc_start
        
        # For now, a stub
        # proc = self.ctx.Process(target=loc_start, args=(...))
        # proc.start()
        # self.processes['localization'] = proc
    
    def _stop_localization_process(self):
        """Stop the localization process"""
        if 'localization' in self.processes:
            self.events['loc_active'].set()
            self.processes['localization'].join(timeout=2)
            if self.processes['localization'].is_alive():
                self.processes['localization'].terminate()
            del self.processes['localization']
    
    def _poll_camera_data(self):
        """Get latest camera data from queue (non-blocking)"""
        try:
            while not self.queues['camera_out'].empty():
                self.latest_camera_data = self.queues['camera_out'].get_nowait()
        except:
            pass
    
    def _poll_localization_data(self):
        """Get latest localization data from queue (non-blocking)"""
        try:
            while not self.queues['loc_out'].empty():
                self.latest_localization_data = self.queues['loc_out'].get_nowait()
        except:
            pass
    
    def _poll_button_input(self):
        """Get latest button input from queue (non-blocking)"""
        try:
            while not self.queues['button_out'].empty():
                self.latest_button_input = self.queues['button_out'].get_nowait()
                self._handle_button_input(self.latest_button_input)
        except:
            pass
    
    def _handle_button_input(self, event):
        """
        Dispatch button events to appropriate handlers
        
        Any button press toggles the global pause/play state.
        
        Args:
            event: Dict with 'type': 'button_press', 'action': '<action_name>', 'timestamp': <time>
        """
        action = event.get('action')
        
        # ANY button press toggles pause/play
        if action in ['emergency_stop', 'pause', 'toggle_mode']:
            self._toggle_pause()
        else:
            print(f"Unknown button action: {action}")
    
    def _button_poller(self, stop_evt, button_q):
        """
        Thread that polls GPIO buttons on Raspberry Pi
        
        Reads physical buttons configured in self.config['buttons'] and pushes
        button events to the queue.
        
        Config format:
            config['buttons'] = {
                'pause': board.D13,            # All three buttons now trigger pause
                'emergency_stop': board.D19,   # Also triggers pause
                'toggle_mode': board.D26       # Also triggers pause
            }
        """
        import digitalio
        
        # Get button configuration
        button_config = self.config.get('buttons', {})
        
        if not button_config:
            print("Warning: No buttons configured. Button poller running in stub mode.")
            # Stub mode - just wait
            while not stop_evt.is_set():
                time.sleep(0.1)
            return
        
        # Initialize buttons
        buttons = {}
        button_states = {}  # Track last press times for debouncing
        
        try:
            import board  # noqa: F401 - imported for pin definitions passed in config
        except ImportError:
            print("Warning: board module not available. Button poller disabled.")
            while not stop_evt.is_set():
                time.sleep(0.1)
            return
        
        # Set up each button
        for action_name, pin in button_config.items():
            try:
                btn = digitalio.DigitalInOut(pin)
                btn.direction = digitalio.Direction.INPUT
                btn.pull = digitalio.Pull.UP  # Active low with pull-up
                buttons[action_name] = btn
                button_states[action_name] = {
                    'last_press': 0.0,
                    'last_up': 0.0,
                    'debounce_time': 0.05
                }
                print(f"Button '{action_name}' configured on pin {pin}")
            except Exception as e:
                print(f"Failed to initialize button '{action_name}' on pin {pin}: {e}")
        
        # Poll loop
        while not stop_evt.is_set():
            current_time = time.monotonic()
            
            for action_name, btn in buttons.items():
                state = button_states[action_name]
                
                # Check if button is pressed (active low)
                if not btn.value:
                    # Button is pressed
                    if (state['last_up'] > state['last_press'] and 
                        (current_time - state['last_press']) > state['debounce_time']):
                        # Valid press detected
                        state['last_press'] = current_time
                        
                        # Push button event to queue
                        event = {
                            'type': 'button_press',
                            'action': action_name,
                            'timestamp': current_time
                        }
                        try:
                            button_q.put(event, block=False)
                        except Exception:
                            pass  # Queue full, drop event
                else:
                    # Button is released
                    state['last_up'] = current_time
            
            time.sleep(0.05)  # Poll at ~50 Hz
    
    # ==================== BUTTON ACTION HANDLERS ====================
    
    def _toggle_pause(self):
        """
        Toggle global pause/play state
        
        Any button press toggles between paused and playing.
        When pausing: stops motors and backs up state variables
        When resuming: restores state variables and allows state logic to resume
        """
        self._is_paused = not self._is_paused
        
        if self._is_paused:
            print("⏸️  PAUSED - Press any button to resume")
            # Stop motors immediately
            if self.motor_controller:
                self.motor_controller.stop()
            # Backup current state variables for resume
            self._backup_state_vars()
        else:
            print("▶️  RESUMED - Continuing from saved state")
            # Restore state variables to continue from where we left off
            self._restore_state_vars()
    
    def _backup_state_vars(self):
        """
        Backup state-specific variables before pausing
        
        Stores all instance variables that start with '_' (state variables)
        into _pause_state_backup for later restoration
        """
        self._pause_state_backup.clear()
        
        # Get all state-specific variables (those starting with state name or common patterns)
        state_var_patterns = [
            '_search_',
            '_square_',
            '_lineup_',
            '_defend_',
            '_attack_'
        ]
        
        for attr_name in dir(self):
            # Check if it's a state variable
            if any(attr_name.startswith(pattern) for pattern in state_var_patterns):
                try:
                    value = getattr(self, attr_name)
                    # Only backup data attributes, not methods
                    if not callable(value):
                        self._pause_state_backup[attr_name] = value
                        logger.debug(f"Backed up state variable: {attr_name}")
                except AttributeError:
                    pass
    
    def _restore_state_vars(self):
        """
        Restore state-specific variables after resuming from pause
        
        Restores all variables from _pause_state_backup
        """
        for attr_name, value in self._pause_state_backup.items():
            try:
                setattr(self, attr_name, value)
                logger.debug(f"Restored state variable: {attr_name}")
            except Exception as e:
                logger.warning(f"Failed to restore {attr_name}: {e}")
        
        # Clear the backup after restoration
        self._pause_state_backup.clear()
    
    # ==================== DRIBBLER & KICKER HELPERS ====================
    
    def set_dribbler_speed(self, speed: float):
        """
        Set dribbler motor speed
        
        Args:
            speed: Speed value (-1.0 to 1.0)
                  Positive = forward (pull ball in)
                  Negative = reverse (push ball out)
                  0 = stop
        """
        if self.dribbler_controller:
            self.dribbler_controller.set_speed(speed)
        else:
            logger.warning("Dribbler controller not available")
    
    def enable_dribbler(self, speed: float = None):
        """
        Enable dribbler at configured or specified speed
        
        Args:
            speed: Optional speed override (0.0 to 1.0)
        """
        if self.dribbler_controller:
            if speed is None:
                speed = self.config.get('dribbler', {}).get('default_speed', 0.5)
            self.dribbler_controller.enable(speed)
        else:
            logger.warning("Dribbler controller not available")
    
    def disable_dribbler(self):
        """Stop the dribbler motor"""
        if self.dribbler_controller:
            self.dribbler_controller.stop()
        else:
            logger.warning("Dribbler controller not available")
    
    def kick(self, duration: float = None) -> bool:
        """
        Trigger a kick
        
        Args:
            duration: Optional kick duration override (seconds)
        
        Returns:
            True if kick was triggered, False if failed or unavailable
        """
        if self.kicker_controller:
            return self.kicker_controller.kick(duration)
        else:
            logger.warning("Kicker controller not available")
            return False
    
    def can_kick(self) -> bool:
        """
        Check if robot can kick (cooldown expired)
        
        Returns:
            True if kick is ready, False if still in cooldown or unavailable
        """
        if self.kicker_controller:
            return self.kicker_controller.can_kick()
        else:
            return False
    
    # ==================== STATE TRANSITIONS ====================
    
    def transition_to(self, new_state: State):
        """Transition to a new state with proper cleanup"""
        if new_state == self.current_state:
            return
        
        print(f"Transitioning: {self.current_state.name} -> {new_state.name}")
        
        # Call exit handler for current state
        exit_handler = self._get_exit_handler(self.current_state)
        if exit_handler:
            exit_handler()
        
        # Update state
        self.previous_state = self.current_state
        self.current_state = new_state
        
        # Call enter handler for new state
        enter_handler = self._get_enter_handler(new_state)
        if enter_handler:
            enter_handler()
    
    def _get_state_handler(self, state: State) -> Optional[Callable]:
        """Get the handler function for a state"""
        handler_name = f"state_{state.name.lower()}"
        return getattr(self, handler_name, None)
    
    def _get_enter_handler(self, state: State) -> Optional[Callable]:
        """Get the on-enter handler for a state"""
        handler_name = f"on_enter_{state.name.lower()}"
        return getattr(self, handler_name, None)
    
    def _get_exit_handler(self, state: State) -> Optional[Callable]:
        """Get the on-exit handler for a state"""
        handler_name = f"on_exit_{state.name.lower()}"
        return getattr(self, handler_name, None)
    
    # ==================== STATE HANDLERS ====================
    
    def state_off_field(self):
        """Robot is off the field - minimal processing"""
        # Check for pause
        if self._is_paused:
            return
        
        # Just wait for button input to resume
        pass
    
    def state_paused(self):
        """Robot is paused - no motor control"""
        # Check for pause
        if self._is_paused:
            return
        
        # Could display debug info, wait for unpause
        if self.latest_camera_data:
            print(f"[PAUSED] Camera frame {self.latest_camera_data.frame_id} available")
    
    def state_chase_ball(self):
        """
        Chase ball: Move towards ball if found, do nothing if not found
        Simple behavior - no complex search patterns
        """
        # Check for pause
        if self._is_paused:
            return
        
        if not self.latest_camera_data:
            return
        
        ball = self.latest_camera_data.ball
        
        if ball.detected:
            # Track if ball is close and enable dribbler accordingly
            if ball.is_close:
                self._last_ball_was_close = True
                # Enable dribbler at speed 1.8 when ball is close
                self.enable_dribbler(speed=1.8)
            else:
                self._last_ball_was_close = False
                # Disable dribbler when ball is not close
                self.disable_dribbler()
            
            if self.motor_controller:
                # Use ball angle directly to move towards it
                # ball.angle: 0° = forward, positive = counterclockwise (left), negative = clockwise (right)
                
                base_speed = 0.07
                movement_angle = ball.angle
                
                # Move in the direction of the ball
                try:
                    self.motor_controller.move_robot_relative(
                        angle=movement_angle,  # Move directly towards ball angle
                        speed=base_speed,
                        rotation=0.0  # No rotation, just move towards ball
                    )
                    
                    # Determine general direction for display
                    if -22.5 <= movement_angle <= 22.5:
                        direction = "FORWARD"
                    elif 22.5 < movement_angle <= 67.5:
                        direction = "FORWARD-LEFT"
                    elif 67.5 < movement_angle <= 112.5:
                        direction = "LEFT"
                    elif 112.5 < movement_angle <= 157.5:
                        direction = "BACK-LEFT"
                    elif 157.5 < movement_angle or movement_angle <= -157.5:
                        direction = "BACKWARD"
                    elif -157.5 < movement_angle <= -112.5:
                        direction = "BACK-RIGHT"
                    elif -112.5 < movement_angle <= -67.5:
                        direction = "RIGHT"
                    elif -67.5 < movement_angle <= -22.5:
                        direction = "FORWARD-RIGHT"
                    else:
                        direction = "UNKNOWN"
                    
                    # Color codes for terminal output
                    GREEN = '\033[92m'  # Bright green
                    YELLOW = '\033[93m'  # Bright yellow
                    BLUE = '\033[94m'   # Bright blue
                    MAGENTA = '\033[95m'  # Bright magenta
                    CYAN = '\033[96m'   # Bright cyan
                    WHITE = '\033[97m'  # Bright white
                    BOLD = '\033[1m'    # Bold
                    RESET = '\033[0m'   # Reset to normal
                    
                    # Choose color based on direction
                    if direction == "FORWARD":
                        color = GREEN
                    elif "LEFT" in direction:
                        color = YELLOW
                    elif "RIGHT" in direction:
                        color = BLUE
                    elif "BACK" in direction:
                        color = MAGENTA
                    else:
                        color = CYAN
                    
                    print(f"{BOLD}{color}[CHASE] Moving {direction} (angle={movement_angle:.1f}°){RESET}")
                except Exception as e:
                    self.motor_controller.stop()
            else:
                pass
        else:
            # Ball not detected - do nothing, just wait
            # Keep dribbler on if last seen ball was close (might have it in dribbler)
            if self._last_ball_was_close:
                self.enable_dribbler(speed=1.8)
            
            # Stop motors when ball is not found
            if self.motor_controller:
                self.motor_controller.stop()
    
    def state_defend_goal(self):
        """Defensive positioning"""
        # Check for pause
        if self._is_paused:
            return
        
        if not self.latest_localization_data:
            return
        
        # Use localization to position between ball and own goal
        print(f"Defending... pos={self.latest_localization_data}")
    
    def state_attack_goal(self):
        """Attacking - move ball toward opponent goal"""
        # Check for pause
        if self._is_paused:
            return
        
        if not self.latest_camera_data:
            return
        
        ball = self.latest_camera_data.ball
        yellow_goal = self.latest_camera_data.yellow_goal  # or blue, depending on team
        
        if ball.detected and yellow_goal.detected:
            print(f"Attack: ball={ball.detected}, goal={yellow_goal.detected}")
            # Logic to push ball toward goal
    
    
    def state_lineup_kick(self):
        """Line up for a kick"""
        # Check for pause
        if self._is_paused:
            return
        
        if not self.latest_camera_data:
            return
        
        ball = self.latest_camera_data.ball
        if ball.detected and ball.is_close_and_centered:
            # Ball is in position - kick it!
            if self.can_kick():
                logger.info("⚽ Executing kick!")
                if self.kick():
                    logger.info("✓ Kick successful")
                else:
                    logger.warning("✗ Kick failed")
                
                # Brief delay to let ball leave
                time.sleep(0.2)
            else:
                logger.info("Kick on cooldown, waiting...")
            
            # Transition back to chase after kick
            self.transition_to(State.CHASE_BALL)
        else:
            # Lost alignment, go back to chase
            logger.info("Ball not aligned, returning to chase")
            self.transition_to(State.CHASE_BALL)
    
    def state_stopped(self):
        """Emergency stop - motors stopped"""
        # Check for pause
        if self._is_paused:
            return
        
        # Send stop command to motors
        print("STOPPED - press 'p' to unpause")
    
    def state_move_in_square(self):
        """
        Example state: Move in a square pattern using robot-relative movement
        
        This demonstrates:
        - Using move_robot_relative() for directional movement
        - State transitions based on timing
        - Simple movement pattern without camera/localization
        
        Press any button to pause.
        """
        # Check for pause
        if self._is_paused:
            return
        
        # Initialize state variables on first entry (using hasattr to check)
        if not hasattr(self, '_square_state_init'):
            self._square_state_init = True
            self._square_step = 0  # 0=forward, 1=left, 2=back, 3=right
            self._square_start_time = time.time()
            self._square_step_duration = 1.0  # 1 second per side
            self._square_speed = 0.05
        
        # Calculate which step we're on
        elapsed = time.time() - self._square_start_time
        
        # Check if we need to move to next step
        if elapsed > self._square_step_duration:
            self._square_step = (self._square_step + 1) % 4  # Cycle through 0-3
            self._square_start_time = time.time()
            logger.info(f"Square movement: step {self._square_step}")
        
        # Execute movement based on current step
        if not self.motor_controller:
            logger.warning("No motor controller - cannot move in square")
            return
        
        # Map step to direction:
        # 0 = forward (0°), 1 = left (270°), 2 = back (180°), 3 = right (90°)
        directions = [0, 270, 180, 90]
        current_direction = directions[self._square_step]
        
        # Move in current direction
        self.motor_controller.move_robot_relative(
            angle=current_direction,
            speed=self._square_speed,
            rotation=0.0
        )
        
        print(f"[SQUARE] Step {self._square_step}, Direction {current_direction}°, Speed {self._square_speed}")
    
    def state_move_straight(self):
        """
        Move robot forward in a straight line
        
        This state simply moves the robot forward at a constant speed.
        Press any button to pause.
        """
        # Check for pause
        if self._is_paused:
            return
        
        if not self.motor_controller:
            logger.warning("No motor controller - cannot move straight")
            return
        
        # Move forward
        forward_speed = 0.05
        self.motor_controller.move_robot_relative(
            angle=0,  # 0° = forward
            speed=forward_speed,
            rotation=0.0  # No rotation
        )
        
        print(f"[STRAIGHT] Moving forward at {forward_speed*100:.0f}% speed")
    
    # ==================== STATE ENTER/EXIT HOOKS ====================
    
    def on_enter_chase_ball(self):
        """Called when entering chase_ball state"""
        # Reset ball tracking state
        self._last_ball_was_close = False
        
        # Could send camera command to prioritize ball detection
        self.queues['camera_cmd'].put({'type': 'detect_ball'})
    
    def on_exit_chase_ball(self):
        """Called when exiting chase_ball state"""
        # Disable dribbler when exiting chase
        self.disable_dribbler()
    
    
    def on_exit_move_in_square(self):
        """Called when exiting move_in_square state"""
        logger.info("Exiting MOVE_IN_SQUARE mode")
        # Clean up square state variables
        if hasattr(self, '_square_state_init'):
            delattr(self, '_square_state_init')
        if hasattr(self, '_square_step'):
            delattr(self, '_square_step')
        if hasattr(self, '_square_start_time'):
            delattr(self, '_square_start_time')
        if hasattr(self, '_square_step_duration'):
            delattr(self, '_square_step_duration')
        if hasattr(self, '_square_speed'):
            delattr(self, '_square_speed')
    
    def on_enter_stopped(self):
        """Called when entering stopped state"""
        print("EMERGENCY STOP ACTIVATED")
        # Send immediate stop to motors
        self.queues['motor_cmd'].put({'type': 'stop'})
    
    # ==================== CLEANUP ====================
    
    def shutdown(self):
        """
        Clean shutdown of all processes and hardware
        
        CRITICAL: Always stops motors first to ensure robot safety
        """
        print("\n🛑 Shutting down Scylla...")
        
        # CRITICAL: Stop motors immediately for safety
        if self.motor_controller:
            try:
                logger.info("Stopping motors...")
                self.motor_controller.stop()
                print("✓ Motors stopped")
            except Exception as e:
                logger.error(f"Failed to stop motors during shutdown: {e}")
                print(f"⚠️  Warning: Motor stop failed: {e}")
        
        # Stop dribbler
        if self.dribbler_controller:
            try:
                logger.info("Stopping dribbler...")
                self.dribbler_controller.stop()
                self.dribbler_controller.stop_thread()
                print("✓ Dribbler stopped")
            except Exception as e:
                logger.error(f"Failed to stop dribbler during shutdown: {e}")
                print(f"⚠️  Warning: Dribbler stop failed: {e}")
        
        # Stop simple dribbler motor
        if self.simple_dribbler_motor:
            try:
                logger.info("Stopping simple dribbler motor...")
                self.simple_dribbler_motor.set_speed(0)
                print("✓ Simple dribbler motor stopped")
            except Exception as e:
                logger.error(f"Failed to stop simple dribbler motor during shutdown: {e}")
                print(f"⚠️  Warning: Simple dribbler motor stop failed: {e}")
        
        # Disable kicker
        if self.kicker_controller:
            try:
                logger.info("Disabling kicker...")
                self.kicker_controller.disable()
                print("✓ Kicker disabled")
            except Exception as e:
                logger.error(f"Failed to disable kicker during shutdown: {e}")
                print(f"⚠️  Warning: Kicker disable failed: {e}")
            except Exception as e:
                logger.error(f"Failed to stop motors during shutdown: {e}")
                print(f"⚠️  Warning: Motor stop failed: {e}")
        
        # Stop button thread
        if hasattr(self, 'button_stop_evt'):
            self.button_stop_evt.set()
            if hasattr(self, 'button_thread'):
                self.button_thread.join(timeout=1)
        
        # Stop all processes
        self._stop_camera_process()
        self._stop_localization_process()
        
        # Signal global stop
        self.events['stop'].set()
        
        # Join any remaining processes
        for name, proc in self.processes.items():
            try:
                proc.join(timeout=1)
                if proc.is_alive():
                    logger.warning(f"Process {name} didn't stop cleanly, terminating...")
                    proc.terminate()
            except Exception as e:
                logger.error(f"Error stopping process {name}: {e}")
        
        print("✓ Scylla shutdown complete")


if __name__ == '__main__':
    # Example configuration with button mappings
    try:
        import board
        
        config = {
            'buttons': {
                'pause': board.D13,           # Button 1: Pause/Resume
                'emergency_stop': board.D19,  # Button 2: Emergency Stop (also pauses)
                'toggle_mode': board.D26      # Button 3: Toggle mode (also pauses)
            },
            'camera': {
                # Camera config can go here
            }
        }
    except ImportError:
        print("Warning: board module not available, running without physical buttons")
        config = {}
    
    # Create and start the FSM
    scylla = Scylla(config=config)
    # Start in ball chasing mode to actively seek and move towards the ball
    scylla.transition_to(State.CHASE_BALL)  # Start chasing the ball
    # scylla.transition_to(State.MOVE_STRAIGHT)  # Start chasing the ball
    scylla.start()