"""
Test script for motor movement functions

This demonstrates:
1. Robot-relative movement (moves relative to robot's orientation)
2. Field-relative movement (moves relative to field, compensating for heading)
3. Example usage patterns

Run this to test the new movement functions without running the full FSM.
"""

import time
from hypemage.motor_control import MotorController
from hypemage.config import load_config

def test_robot_relative_movement():
    """Test robot-relative movement in different directions"""
    print("\n=== Testing Robot-Relative Movement ===")
    
    # Load config
    config = load_config()
    
    # Initialize motor controller
    print("Initializing motors...")
    controller = MotorController(config=config, threaded=True)
    
    try:
        # Move forward
        print("\n1. Moving FORWARD (0°) at 30% speed for 2 seconds")
        controller.move_robot_relative(angle=0, speed=0.3)
        time.sleep(2)
        
        # Move right
        print("\n2. Moving RIGHT (90°) at 30% speed for 2 seconds")
        controller.move_robot_relative(angle=90, speed=0.3)
        time.sleep(2)
        
        # Move back
        print("\n3. Moving BACK (180°) at 30% speed for 2 seconds")
        controller.move_robot_relative(angle=180, speed=0.3)
        time.sleep(2)
        
        # Move left
        print("\n4. Moving LEFT (270°) at 30% speed for 2 seconds")
        controller.move_robot_relative(angle=270, speed=0.3)
        time.sleep(2)
        
        # Move diagonal with rotation
        print("\n5. Moving DIAGONAL (45°) with rotation for 2 seconds")
        controller.move_robot_relative(angle=45, speed=0.3, rotation=0.2)
        time.sleep(2)
        
        # Stop
        print("\n6. Stopping")
        controller.stop()
        time.sleep(1)
        
    finally:
        controller.shutdown()
        print("\nTest complete!")


def test_field_relative_movement():
    """Test field-relative movement with simulated heading"""
    print("\n=== Testing Field-Relative Movement ===")
    
    # Load config
    config = load_config()
    
    # Initialize motor controller
    print("Initializing motors...")
    controller = MotorController(config=config, threaded=True)
    
    try:
        # Simulate robot heading (in a real scenario, this comes from IMU or localization)
        simulated_heading = 45.0  # Robot is facing 45° to the right
        
        print(f"\nSimulated robot heading: {simulated_heading}°")
        print("Goal: Move towards enemy goal (field direction 0°) regardless of robot orientation")
        
        # Move towards enemy goal (field direction 0°)
        print("\n1. Moving towards enemy goal (field 0°) for 3 seconds")
        print("   Robot will automatically compensate for its 45° heading")
        controller.move_field_relative(
            angle=0,           # Target: enemy goal (field direction)
            speed=0.3,
            rotation=0,
            heading=simulated_heading
        )
        time.sleep(3)
        
        # Now simulate robot has rotated
        simulated_heading = 90.0
        print(f"\n2. Robot rotated to {simulated_heading}°")
        print("   Moving towards enemy goal again (field 0°)")
        controller.move_field_relative(
            angle=0,
            speed=0.3,
            rotation=0,
            heading=simulated_heading
        )
        time.sleep(3)
        
        # Stop
        print("\n3. Stopping")
        controller.stop()
        time.sleep(1)
        
    finally:
        controller.shutdown()
        print("\nTest complete!")


def test_square_pattern():
    """Test moving in a square pattern"""
    print("\n=== Testing Square Movement Pattern ===")
    
    # Load config
    config = load_config()
    
    # Initialize motor controller
    print("Initializing motors...")
    controller = MotorController(config=config, threaded=True)
    
    try:
        speed = 0.3
        duration = 1.5  # seconds per side
        
        print(f"\nMoving in square: {duration}s per side at {speed*100}% speed")
        
        # Forward
        print("\n1. Moving FORWARD")
        controller.move_robot_relative(0, speed)
        time.sleep(duration)
        
        # Right
        print("\n2. Moving RIGHT")
        controller.move_robot_relative(90, speed)
        time.sleep(duration)
        
        # Back
        print("\n3. Moving BACK")
        controller.move_robot_relative(180, speed)
        time.sleep(duration)
        
        # Left
        print("\n4. Moving LEFT")
        controller.move_robot_relative(270, speed)
        time.sleep(duration)
        
        # Stop
        print("\n5. Stopping")
        controller.stop()
        time.sleep(1)
        
    finally:
        controller.shutdown()
        print("\nSquare complete!")


if __name__ == "__main__":
    import sys
    
    print("Motor Movement Test Suite")
    print("=" * 50)
    print("\nAvailable tests:")
    print("  1. Robot-relative movement (forward, right, back, left, diagonal)")
    print("  2. Field-relative movement (with heading compensation)")
    print("  3. Square pattern")
    print("  4. Run all tests")
    
    choice = input("\nSelect test (1-4, or q to quit): ").strip()
    
    if choice == "1":
        test_robot_relative_movement()
    elif choice == "2":
        test_field_relative_movement()
    elif choice == "3":
        test_square_pattern()
    elif choice == "4":
        test_robot_relative_movement()
        time.sleep(2)
        test_field_relative_movement()
        time.sleep(2)
        test_square_pattern()
    elif choice.lower() == "q":
        print("Exiting...")
        sys.exit(0)
    else:
        print("Invalid choice")
