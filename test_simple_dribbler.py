#!/usr/bin/env python3
"""
Simple Dribbler Test - Direct Motor Control
Tests the dribbler motor directly without any complex logic
"""

import sys
import time
import socket

# Try to import Motor class
try:
    from motors.motor import Motor
    print("✓ Motor class imported successfully")
except ImportError as e:
    print(f"✗ Failed to import Motor class: {e}")
    print("Make sure motors/motor.py exists")
    sys.exit(1)

def main():
    print("=" * 60)
    print("Simple Dribbler Motor Test")
    print("=" * 60)
    
    # Detect robot and determine address
    hostname = socket.gethostname()
    print(f"\nHostname: {hostname}")
    
    if 'f7' in hostname.lower():
        address = 29
        robot_name = "f7 (storm)"
    elif 'm7' in hostname.lower():
        address = 30
        robot_name = "m7 (necron)"
    else:
        print(f"\nUnknown hostname '{hostname}'")
        print("Please enter the dribbler motor address manually:")
        print("  29 for f7 (storm)")
        print("  30 for m7 (necron)")
        try:
            address = int(input("Address: "))
        except:
            print("Invalid input, defaulting to 30")
            address = 30
        robot_name = "unknown"
    
    print(f"Robot: {robot_name}")
    print(f"Using dribbler address: {address}")
    
    # Try to initialize motor
    try:
        print(f"\nInitializing Motor({address})...")
        motor = Motor(address)
        print("✓ Motor initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize motor: {e}")
        print("\nPossible issues:")
        print("  - I2C bus not available")
        print("  - Motor not connected at this address")
        print("  - Wrong address for this robot")
        print("  - Permissions issue (try running with sudo)")
        sys.exit(1)
    
    # Test motor at different speeds
    print("\n" + "=" * 60)
    print("Testing motor at different speeds")
    print("Watch the dribbler motor - it should spin!")
    print("Press Ctrl+C to stop early")
    print("=" * 60)
    
    speeds = [1.0, 2.0, 3.0, 4.0, 5.0]
    
    try:
        for speed in speeds:
            print(f"\n→ Setting speed to {speed}...")
            motor.set_speed(speed)
            print(f"  Motor should be spinning at speed {speed}")
            print(f"  Running for 3 seconds...")
            time.sleep(3.0)
        
        print("\n→ Stopping motor...")
        motor.set_speed(0)
        print("✓ Motor stopped")
        
        print("\n" + "=" * 60)
        print("Test Complete!")
        print("Did you see the motor spinning?")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        print("Stopping motor...")
        motor.set_speed(0)
        print("✓ Motor stopped")
    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        print("Attempting to stop motor...")
        try:
            motor.set_speed(0)
            print("✓ Motor stopped")
        except:
            print("✗ Could not stop motor")
        sys.exit(1)

if __name__ == "__main__":
    main()
