"""Dribbler Motor Control

Controls the dribbler motor for ball manipulation.
The dribbler address is robot-specific:
- f7 (storm): address 29
- m7 (necron): address 30
"""

import socket
from threading import Thread, Lock
from hypemage.logger import get_logger

logger = get_logger(__name__)


class DribblerController:
    """
    Controls the dribbler motor with thread-safe speed control
    
    The dribbler is a single motor that spins to grip and control the ball.
    Different robots have different I2C addresses for the dribbler motor.
    """
    
    # Robot-specific dribbler addresses
    DRIBBLER_ADDRESSES = {
        'f7': 29,  # Storm
        'm7': 30   # Necron
    }
    
    def __init__(self, address: int = None, threaded: bool = True):
        """
        Initialize dribbler controller
        
        Args:
            address: I2C address of dribbler motor. If None, auto-detect based on hostname
            threaded: Whether to run motor control in a separate thread
        """
        self._lock = Lock()
        self._current_speed = 0.0
        self._target_speed = 0.0
        self._running = False
        self._thread = None
        
        # Auto-detect address based on hostname if not provided
        if address is None:
            address = self._detect_dribbler_address()
        
        self.address = address
        logger.info(f"Initializing dribbler controller at address {self.address}")
        
        # Import and initialize motor
        try:
            from motors.motor import Motor
            self.motor = Motor(self.address)
            logger.info(f"✓ Dribbler motor initialized at address {self.address}")
        except Exception as e:
            logger.error(f"Failed to initialize dribbler motor: {e}")
            raise
        
        # Start control thread if requested
        if threaded:
            self.start_thread()
    
    def _detect_dribbler_address(self) -> int:
        """
        Detect dribbler address based on hostname
        
        Returns:
            I2C address for dribbler motor
        """
        try:
            hostname = socket.gethostname().lower()
            logger.info(f"Detected hostname: {hostname}")
            
            # Check for f7 or m7 in hostname
            if 'f7' in hostname:
                logger.info("Detected robot: f7 (storm)")
                return self.DRIBBLER_ADDRESSES['f7']
            elif 'm7' in hostname:
                logger.info("Detected robot: m7 (necron)")
                return self.DRIBBLER_ADDRESSES['m7']
            else:
                # Default to f7 if unknown
                logger.warning(f"Unknown hostname '{hostname}', defaulting to f7 address")
                return self.DRIBBLER_ADDRESSES['f7']
        except Exception as e:
            logger.error(f"Failed to detect hostname: {e}, defaulting to f7 address")
            return self.DRIBBLER_ADDRESSES['f7']
    
    def start_thread(self):
        """Start the dribbler control thread"""
        if self._thread is None or not self._thread.is_alive():
            self._running = True
            self._thread = Thread(target=self._control_loop, daemon=True)
            self._thread.start()
            logger.info("Dribbler control thread started")
    
    def stop_thread(self):
        """Stop the dribbler control thread"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            logger.info("Dribbler control thread stopped")
    
    def _control_loop(self):
        """
        Main control loop (runs in separate thread)
        
        Continuously updates motor speed based on target speed
        """
        import time
        
        while self._running:
            try:
                with self._lock:
                    if self._current_speed != self._target_speed:
                        self._current_speed = self._target_speed
                        self.motor.set_speed(self._current_speed)
                
                time.sleep(0.05)  # 20 Hz update rate
            except Exception as e:
                logger.error(f"Error in dribbler control loop: {e}")
                time.sleep(0.1)
    
    def set_speed(self, speed: float):
        """
        Set dribbler speed
        
        Args:
            speed: Speed value (-1.0 to 1.0)
                  Positive = forward (pull ball in)
                  Negative = reverse (push ball out)
                  0 = stop
        """
        # Clamp speed to valid range
        speed = max(-1.0, min(1.0, speed))
        
        with self._lock:
            self._target_speed = speed
        
        logger.debug(f"Dribbler speed set to {speed:.2f}")
    
    def stop(self):
        """Stop the dribbler motor"""
        self.set_speed(0.0)
        logger.info("Dribbler stopped")
    
    def enable(self, speed: float = 0.5):
        """
        Enable dribbler at specified speed
        
        Args:
            speed: Speed to run dribbler (0.0 to 1.0), default 0.5
        """
        self.set_speed(abs(speed))
        logger.info(f"Dribbler enabled at speed {abs(speed):.2f}")
    
    def disable(self):
        """Disable dribbler (same as stop)"""
        self.stop()
    
    def is_running(self) -> bool:
        """Check if dribbler is currently running"""
        with self._lock:
            return abs(self._current_speed) > 0.01
    
    def get_speed(self) -> float:
        """Get current dribbler speed"""
        with self._lock:
            return self._current_speed
    
    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.stop()
            self.stop_thread()
        except:
            pass


if __name__ == '__main__':
    # Test dribbler controller
    print("Testing Dribbler Controller")
    print("=" * 40)
    
    try:
        dribbler = DribblerController(threaded=True)
        
        print(f"\nDribbler initialized at address: {dribbler.address}")
        print("Commands: speed <value>, stop, quit")
        
        while True:
            cmd = input("\n> ").strip().lower()
            
            if cmd == 'quit' or cmd == 'q':
                break
            elif cmd == 'stop':
                dribbler.stop()
                print("Dribbler stopped")
            elif cmd.startswith('speed '):
                try:
                    speed = float(cmd.split()[1])
                    dribbler.set_speed(speed)
                    print(f"Dribbler speed set to {speed:.2f}")
                except (ValueError, IndexError):
                    print("Invalid speed value. Use: speed <-1.0 to 1.0>")
            elif cmd.startswith('enable'):
                parts = cmd.split()
                speed = float(parts[1]) if len(parts) > 1 else 0.5
                dribbler.enable(speed)
                print(f"Dribbler enabled at {speed:.2f}")
            else:
                print("Unknown command")
                print("Available: speed <value>, enable [speed], stop, quit")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'dribbler' in locals():
            dribbler.stop()
            print("\nDribbler stopped")
