#!/usr/bin/env python3
"""
Dribbler Diagnostic Script
Checks what's wrong with the dribbler setup
"""

import sys
import socket

print("=" * 60)
print("DRIBBLER DIAGNOSTIC")
print("=" * 60)

# Step 1: Check hostname
print("\n1. Checking hostname...")
hostname = socket.gethostname()
print(f"   Hostname: {hostname}")

if 'f7' in hostname.lower():
    expected_address = 29
    robot = "f7 (storm)"
elif 'm7' in hostname.lower():
    expected_address = 30
    robot = "m7 (necron)"
else:
    expected_address = "unknown"
    robot = "unknown"

print(f"   Robot: {robot}")
print(f"   Expected dribbler address: {expected_address}")

# Step 2: Check if board module is available
print("\n2. Checking if board module is available...")
try:
    import board
    print("   ✓ board module available")
    HAS_BOARD = True
except ImportError as e:
    print(f"   ✗ board module NOT available: {e}")
    print("   This is expected on non-Raspberry Pi systems")
    HAS_BOARD = False

# Step 3: Check if Motor class can be imported
print("\n3. Checking if Motor class can be imported...")
try:
    from motors.motor import Motor
    print("   ✓ Motor class imported")
    HAS_MOTOR = True
except ImportError as e:
    print(f"   ✗ Motor class import failed: {e}")
    HAS_MOTOR = False
except Exception as e:
    print(f"   ✗ Motor class import error: {e}")
    HAS_MOTOR = False

# Step 4: Check if we can create a Motor instance
if HAS_MOTOR:
    print(f"\n4. Trying to create Motor({expected_address})...")
    try:
        motor = Motor(expected_address)
        print("   ✓ Motor instance created successfully!")
        
        # Try to set speed
        print("\n5. Testing set_speed(3.0)...")
        try:
            motor.set_speed(3.0)
            print("   ✓ set_speed(3.0) called successfully")
            print("   Check if the dribbler is spinning!")
            
            input("\nPress Enter to stop the motor...")
            motor.set_speed(0)
            print("   ✓ Motor stopped")
            
        except Exception as e:
            print(f"   ✗ set_speed failed: {e}")
            
    except Exception as e:
        print(f"   ✗ Failed to create Motor instance: {e}")
        print(f"\n   Error details:")
        import traceback
        traceback.print_exc()
else:
    print("\n4. Skipping Motor creation (import failed)")

# Step 5: Check config.json
print("\n6. Checking config.json...")
try:
    import json
    from pathlib import Path
    config_path = Path(__file__).parent / "hypemage" / "config.json"
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        if 'dribbler' in config.get('defaults', {}):
            print(f"   Dribbler config: {config['defaults']['dribbler']}")
        else:
            print("   No dribbler config in config.json")
    else:
        print(f"   Config file not found: {config_path}")
except Exception as e:
    print(f"   Error reading config: {e}")

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Hostname: {hostname} ({robot})")
print(f"Expected Address: {expected_address}")
print(f"Board Module: {'✓' if HAS_BOARD else '✗'}")
print(f"Motor Class: {'✓' if HAS_MOTOR else '✗'}")

if not HAS_BOARD:
    print("\n⚠️  You are NOT on a Raspberry Pi!")
    print("   The Motor class requires 'board' and 'busio' modules")
    print("   which are only available on Raspberry Pi hardware.")
    print("   You cannot test the dribbler motor on this system.")
elif not HAS_MOTOR:
    print("\n⚠️  Motor class could not be imported!")
    print("   Check that motors/motor.py exists and is correct.")
else:
    print("\n✓ Everything looks good!")
    print("  If the dribbler isn't working, check:")
    print("  1. Is the motor physically connected?")
    print("  2. Is the I2C address correct?")
    print("  3. Is the motor powered?")
    print("  4. Try running: python test_simple_dribbler.py")

print("=" * 60)
