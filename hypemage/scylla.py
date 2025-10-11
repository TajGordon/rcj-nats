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
from hypemage.camera import CameraProcess, CameraInitializationError
from hypemage.dribbler_control import DribblerController
from hypemage.kicker_control import KickerController

logger = get_logger(__name__)


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
    SEARCH_BALL = auto()
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
        State.SEARCH_BALL: StateConfig(
            needs_camera=True,
            needs_localization=True,
            needs_motors=True,
            update_rate_hz=15.0
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
        self.config = config or {}
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
        
        # Timing
        self.last_update_time = 0.0
        
        # Motor controller (critical - must init first)
        self.motor_controller = None
        
        # Dribbler and kicker controllers (non-critical)
        self.dribbler_controller = None
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
        
        # Initialize kicker (NON-CRITICAL)
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
        print("Localization process would start here")
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
            print("Localization process stopped")
    
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
            '_chase_',
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
        Active state: chase the ball
        
        Uses continuous feedback from camera to adjust movement dynamically.
        The robot calculates the angle to the ball and moves in that direction,
        adjusting speed based on distance and adding rotation for better alignment.
        """
        # Check for pause
        if self._is_paused:
            return
        
        if not self.latest_camera_data:
            return
        
        ball = self.latest_camera_data.ball
        
        if ball.detected:
            # Validate ball detection data
            if not hasattr(ball, 'area') or ball.area <= 0:
                logger.warning("Invalid ball detection data - area is zero or missing")
                return
            
            # Check if ball is close and centered - transition to lineup
            if ball.is_close_and_centered:
                logger.info("Ball is close and centered - transitioning to lineup kick")
                self.transition_to(State.LINEUP_KICK)
                return
            
            # Calculate angle to ball for movement
            if self.motor_controller:
                # Calculate angle to ball using the ball's position relative to frame center
                # horizontal_error: -1 (left) to +1 (right)
                # vertical_error: -1 (top) to +1 (bottom)
                
                # For robot-relative movement using move_robot_relative():
                # - 0° = forward, 90° = right, 180° = back, 270° = left
                # - horizontal_error: -1 (left) to +1 (right)
                # - vertical_error: -1 (top/forward) to +1 (bottom/back)
                
                # Calculate angle to ball using atan2(x, y) where:
                # - x = horizontal_error (left/right offset)
                # - y = -vertical_error (forward/back offset, inverted because negative vertical_error = forward)
                # This gives us the angle from the robot's perspective
                raw_ball_angle = math.degrees(math.atan2(
                    ball.horizontal_error,    # x: horizontal offset (-1 to +1)
                    -ball.vertical_error      # y: vertical offset (inverted: -1 to +1)
                ))
                
                # Normalize angle to 0-360° range for consistency
                ball_angle_normalized = raw_ball_angle % 360
                
                # Smooth the angle using a moving average to reduce jitter
                if not hasattr(self, '_chase_angle_history'):
                    self._chase_angle_history = []
                    self._chase_max_history = 5
                
                self._chase_angle_history.append(ball_angle_normalized)
                if len(self._chase_angle_history) > self._chase_max_history:
                    self._chase_angle_history.pop(0)
                
                # Calculate smoothed angle using circular mean to handle angle wrapping
                # Convert to unit vectors, average, then convert back
                avg_x = sum(math.cos(math.radians(a)) for a in self._chase_angle_history)
                avg_y = sum(math.sin(math.radians(a)) for a in self._chase_angle_history)
                ball_angle_raw = math.degrees(math.atan2(avg_y, avg_x))
                
                # FIX: Add 180° to flip direction (robot was going opposite direction)
                ball_angle = (ball_angle_raw + 180) % 360
                
                # Use constant speed for ball chasing
                speed = 0.05
                
                # Proportional rotation control for better alignment
                # The more the ball is off-center horizontally, the more we rotate
                horizontal_error = ball.horizontal_error
                
                # Use a proportional controller for alignment
                # Positive horizontal_error = ball to the right, so we need to rotate right (positive rotation)
                rotation_gain = 0.05  # Reduced gain for slower rotation
                rotation = horizontal_error * rotation_gain
                
                # Clamp rotation to reasonable limits
                max_rotation = 0.1  # Reduced max rotation speed
                rotation = max(-max_rotation, min(max_rotation, rotation))
                
                # If the ball is very off-center, reduce forward speed and prioritize rotation
                if abs(horizontal_error) > 0.6:  # Ball is way off to the side
                    speed *= 0.3  # Significantly slow down to rotate better
                    rotation *= 1.5  # Increase rotation gain when far off-center
                    logger.debug(f"Ball far off-center ({horizontal_error:.2f}), reducing speed and increasing rotation")
                
                # Move towards ball with continuous adjustment
                try:
                    self.motor_controller.move_robot_relative(
                        angle=ball_angle,
                        speed=speed,
                        rotation=rotation
                    )
                    
                    # Logging with detailed feedback
                    logger.info(
                        f"Chasing ball: angle={ball_angle:.1f}° (raw={raw_ball_angle:.1f}°), "
                        f"speed={speed:.2f}, rotation={rotation:.2f}, "
                        f"h_err={horizontal_error:.2f}, v_err={ball.vertical_error:.2f}, "
                        f"area={ball.area:.0f}"
                    )
                except Exception as e:
                    logger.error(f"Error in motor control during ball chase: {e}")
                    # Stop motors on error for safety
                    self.motor_controller.stop()
            else:
                logger.warning("No motor controller available for ball chasing")
        else:
            # Lost ball - transition to search
            logger.info("Ball lost during chase - transitioning to search")
            self.transition_to(State.SEARCH_BALL)
    
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
    
    def state_search_ball(self):
        """Ball lost - search pattern"""
        # Check for pause
        if self._is_paused:
            return
        
        print("Searching for ball...")
        
        # Check if ball is found
        if self.latest_camera_data and self.latest_camera_data.ball.detected:
            print("Ball found during search - transitioning to chase")
            self.transition_to(State.CHASE_BALL)
            return
        
        # Perform search pattern if motor controller is available
        if self.motor_controller:
            # Initialize search state if not already done
            if not hasattr(self, '_search_state_init'):
                self._search_state_init = True
                self._search_start_time = time.time()
                self._search_direction = 1  # 1 for clockwise, -1 for counter-clockwise
                print("Starting ball search pattern")
            
            # Rotate slowly to search for ball
            search_speed = 0.05  # Slow rotation speed (reduced from 0.2)
            self.motor_controller.move_robot_relative(
                angle=0,  # No forward/back movement
                speed=0,  # No translation
                rotation=self._search_direction * search_speed  # Rotate to search
            )
            
            # Change search direction every 3 seconds
            search_duration = 3.0
            if time.time() - self._search_start_time > search_duration:
                self._search_direction *= -1  # Reverse direction
                self._search_start_time = time.time()
                print(f"Changing search direction to {'clockwise' if self._search_direction > 0 else 'counter-clockwise'}")
        else:
            logger.warning("No motor controller available for ball search")
    
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
        logger.info("Entering CHASE_BALL mode")
        
        # Initialize tracking variables for adaptive control
        self._chase_last_ball_angle = None
        self._chase_angle_history = []  # Track recent angles for smoothing
        self._chase_max_history = 5  # Number of frames to average
        
        # Could send camera command to prioritize ball detection
        self.queues['camera_cmd'].put({'type': 'detect_ball'})
    
    def on_exit_chase_ball(self):
        """Called when exiting chase_ball state"""
        logger.info("Exiting CHASE_BALL mode")
        
        # Disable dribbler when exiting chase
        self.disable_dribbler()
        
        # Clean up tracking variables
        if hasattr(self, '_chase_last_ball_angle'):
            delattr(self, '_chase_last_ball_angle')
        if hasattr(self, '_chase_angle_history'):
            delattr(self, '_chase_angle_history')
        if hasattr(self, '_chase_max_history'):
            delattr(self, '_chase_max_history')
    
    def on_exit_search_ball(self):
        """Called when exiting search_ball state"""
        print("Exiting SEARCH_BALL mode")
        # Clean up search state variables
        if hasattr(self, '_search_state_init'):
            delattr(self, '_search_state_init')
        if hasattr(self, '_search_start_time'):
            delattr(self, '_search_start_time')
        if hasattr(self, '_search_direction'):
            delattr(self, '_search_direction')
    
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
    scylla.start()