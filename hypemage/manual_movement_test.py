"""
Manual Movement Test Script

Interactive script to test motor movement by typing direction and speed.
- Enter angle (0-360) and speed (0.0-1.0)
- Robot moves in that direction relative to its current orientation
- Ctrl+C safely stops all motors before exiting

Usage:
    python hypemage/manual_movement_test.py
    
    Then type: <angle> <speed>
    Example: 0 0.5       (move forward at half speed)
    Example: 90 0.3      (move right at 30% speed)
    Example: 270 0.4     (move left at 40% speed)
"""

import sys
import signal
import time
from hypemage.motor_control import MotorController
from hypemage.config import load_config

# Global motor controller for signal handler
motor_controller = None

def signal_handler(sig, frame):
    """Handle Ctrl+C by stopping motors before exit"""
    print("\n\n🛑 Ctrl+C detected - stopping motors...")
    if motor_controller:
        motor_controller.stop()
        print("✓ Motors stopped")
        motor_controller.shutdown()
        print("✓ Motor controller shut down")
    print("Exiting...")
    sys.exit(0)

def main():
    global motor_controller
    
    print("=" * 60)
    print("Manual Movement Test")
    print("=" * 60)
    print("\nInitializing motor controller...")
    
    # Load config
    config = load_config()
    
    # Initialize motor controller
    try:
        motor_controller = MotorController(config=config, threaded=True)
        print("✓ Motor controller initialized\n")
    except Exception as e:
        print(f"✗ Failed to initialize motors: {e}")
        print("Cannot continue without motors")
        sys.exit(1)
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    print("Instructions:")
    print("  - Type: <angle> <speed>")
    print("  - Angle: 0-360 degrees (0=forward, 90=right, 180=back, 270=left)")
    print("  - Speed: 0.0-1.0 (0=stop, 1.0=full speed)")
    print("  - Ctrl+C to exit (motors will stop automatically)")
    print("\nExamples:")
    print("  0 0.5       → Move forward at 50% speed")
    print("  90 0.3      → Move right at 30% speed")
    print("  270 0.4     → Move left at 40% speed")
    print("  180 0.2     → Move backward at 20% speed")
    print("  0 0         → Stop")
    print("\n" + "=" * 60 + "\n")
    
    try:
        while True:
            # Get user input
            try:
                user_input = input("Enter <angle> <speed> (or Ctrl+C to exit): ").strip()
                
                if not user_input:
                    continue
                
                # Parse input
                parts = user_input.split()
                if len(parts) != 2:
                    print("⚠ Error: Please enter exactly 2 values (angle and speed)")
                    continue
                
                try:
                    angle = float(parts[0])
                    speed = float(parts[1])
                except ValueError:
                    print("⚠ Error: Both values must be numbers")
                    continue
                
                # Validate inputs
                if angle < 0 or angle > 360:
                    print("⚠ Warning: Angle should be 0-360 degrees (wrapping around)")
                    angle = angle % 360
                
                if speed < 0 or speed > 1.0:
                    print("⚠ Error: Speed must be between 0.0 and 1.0")
                    continue
                
                # Execute movement
                print(f"→ Moving: angle={angle}°, speed={speed:.2f}")
                
                # Show status
                status = motor_controller.get_status()
                print(f"  Motor speeds before: {[f'{s:.2f}' for s in status.speeds]}")
                
                # Run movement for 2 seconds
                # Note: We need to keep sending commands to prevent watchdog timeout (0.5s default)
                print("  Running for 2 seconds (sending commands every 0.2s to prevent watchdog timeout)...")
                start_time = time.time()
                while (time.time() - start_time) < 2.0:
                    motor_controller.move_robot_relative(angle=angle, speed=speed, rotation=0.0)
                    time.sleep(0.2)  # Send command every 200ms (faster than 500ms watchdog timeout)
                
                # Stop after 2 seconds
                print("  Stopping motors")
                motor_controller.stop()

                
            except EOFError:
                # Handle end of input (Ctrl+D on Unix)
                print("\nEOF detected - stopping motors...")
                break
                
    except KeyboardInterrupt:
        # This shouldn't be reached due to signal handler, but just in case
        print("\n\nStopping motors...")
        motor_controller.stop()
    
    finally:
        # Clean shutdown
        if motor_controller:
            print("\nShutting down motor controller...")
            motor_controller.shutdown()
            print("✓ Shutdown complete")

if __name__ == "__main__":
    main()
