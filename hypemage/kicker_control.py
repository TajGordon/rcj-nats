"""Kicker Solenoid Control

Controls the kicker solenoid for shooting the ball.
Uses a relay on GPIO D16 to trigger the solenoid.
"""

import time
from threading import Lock
from hypemage.logger import get_logger

logger = get_logger(__name__)


class KickerController:
    """
    Controls the kicker solenoid via relay
    
    The kicker uses a solenoid activated by a relay on GPIO D16.
    When triggered, it fires a short pulse to kick the ball.
    """
    
    DEFAULT_KICK_DURATION = 0.15  # seconds
    MIN_KICK_INTERVAL = 0.5  # Minimum time between kicks (safety)
    
    def __init__(self, gpio_pin=None, kick_duration: float = None):
        """
        Initialize kicker controller
        
        Args:
            gpio_pin: GPIO pin for relay (default: board.D16)
            kick_duration: Duration of kick pulse in seconds (default: 0.15)
        """
        self._lock = Lock()
        self._last_kick_time = 0.0
        self.kick_duration = kick_duration or self.DEFAULT_KICK_DURATION
        
        logger.info("Initializing kicker controller")
        
        # Initialize GPIO
        try:
            import board
            import digitalio
            
            # Use provided pin or default to D16
            pin = gpio_pin if gpio_pin is not None else board.D16
            
            self.relay = digitalio.DigitalInOut(pin)
            self.relay.switch_to_output(value=False, drive_mode=digitalio.DriveMode.PUSH_PULL)
            
            # Set relay to inactive state (don't kick)
            self.relay.value = True  # True = relay OFF = no kick
            
            logger.info(f"✓ Kicker relay initialized on pin {pin}")
        except Exception as e:
            logger.error(f"Failed to initialize kicker relay: {e}")
            raise
    
    def kick(self, duration: float = None) -> bool:
        """
        Trigger a kick
        
        Args:
            duration: Kick duration in seconds (default: use configured duration)
        
        Returns:
            True if kick was triggered, False if too soon after last kick
        """
        with self._lock:
            current_time = time.time()
            
            # Safety: Don't kick too frequently
            if current_time - self._last_kick_time < self.MIN_KICK_INTERVAL:
                logger.warning(f"Kick blocked: too soon after last kick "
                             f"({current_time - self._last_kick_time:.2f}s < {self.MIN_KICK_INTERVAL}s)")
                return False
            
            kick_time = duration if duration is not None else self.kick_duration
            
            try:
                logger.info(f"⚽ KICK! (duration: {kick_time:.3f}s)")
                
                # Activate relay (kick)
                self.relay.value = False  # False = relay ON = kick!
                time.sleep(kick_time)
                
                # Deactivate relay (stop kick)
                self.relay.value = True  # True = relay OFF = no kick
                
                self._last_kick_time = current_time
                logger.info("Kick complete")
                return True
                
            except Exception as e:
                logger.error(f"Error during kick: {e}")
                # Safety: ensure relay is off
                try:
                    self.relay.value = True
                except:
                    pass
                return False
    
    def can_kick(self) -> bool:
        """
        Check if enough time has passed since last kick
        
        Returns:
            True if robot can kick now, False if still in cooldown
        """
        with self._lock:
            return (time.time() - self._last_kick_time) >= self.MIN_KICK_INTERVAL
    
    def get_time_since_last_kick(self) -> float:
        """Get time in seconds since last kick"""
        with self._lock:
            return time.time() - self._last_kick_time
    
    def set_kick_duration(self, duration: float):
        """
        Set the default kick duration
        
        Args:
            duration: Kick duration in seconds (typically 0.1 - 0.2s)
        """
        if 0.05 <= duration <= 0.5:
            self.kick_duration = duration
            logger.info(f"Kick duration set to {duration:.3f}s")
        else:
            logger.warning(f"Invalid kick duration {duration}s (must be 0.05-0.5s)")
    
    def disable(self):
        """Ensure kicker is disabled (relay off)"""
        try:
            self.relay.value = True
            logger.info("Kicker disabled")
        except Exception as e:
            logger.error(f"Error disabling kicker: {e}")
    
    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.disable()
        except:
            pass


if __name__ == '__main__':
    # Test kicker controller
    print("Testing Kicker Controller")
    print("=" * 40)
    print("⚠️  WARNING: This will trigger the physical kicker!")
    print("Make sure the robot is safe to kick!")
    
    response = input("\nContinue? (yes/no): ").strip().lower()
    if response != 'yes':
        print("Aborted")
        exit(0)
    
    try:
        kicker = KickerController()
        
        print("\nKicker initialized")
        print("Commands: kick [duration], status, quit")
        
        while True:
            cmd = input("\n> ").strip().lower()
            
            if cmd == 'quit' or cmd == 'q':
                break
            elif cmd == 'kick':
                if kicker.kick():
                    print("✓ Kick executed")
                else:
                    print("✗ Kick blocked (cooldown)")
            elif cmd.startswith('kick '):
                try:
                    duration = float(cmd.split()[1])
                    if kicker.kick(duration):
                        print(f"✓ Kick executed ({duration:.3f}s)")
                    else:
                        print("✗ Kick blocked (cooldown)")
                except (ValueError, IndexError):
                    print("Invalid duration. Use: kick <0.05-0.5>")
            elif cmd == 'status':
                can_kick = kicker.can_kick()
                time_since = kicker.get_time_since_last_kick()
                print(f"Can kick: {can_kick}")
                print(f"Time since last kick: {time_since:.2f}s")
                print(f"Kick duration: {kicker.kick_duration:.3f}s")
            else:
                print("Unknown command")
                print("Available: kick [duration], status, quit")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'kicker' in locals():
            kicker.disable()
            print("\nKicker disabled")
