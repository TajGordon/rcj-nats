#!/usr/bin/env python3
"""
Test script to verify robot detection functionality.

This script tests the robot_detection module to ensure it correctly:
1. Detects the robot name from hostname
2. Returns the correct motor addresses for the detected robot
3. Returns the correct dribbler address for the detected robot
4. Provides complete robot configuration overrides

Usage:
    python test_robot_detection.py
    
Expected output on m7 (necron):
    Robot Name: m7
    Motor Addresses: [27, 29, 25, 26]
    Dribbler Address: 30
    
Expected output on f7 (storm):
    Robot Name: f7
    Motor Addresses: [28, 30, 26, 27]
    Dribbler Address: 29
"""

import sys
from pathlib import Path

# Add parent directory to path to import robot_detection
sys.path.insert(0, str(Path(__file__).parent))

from robot_detection import (
    get_robot_name,
    get_motor_addresses,
    get_dribbler_address,
    get_robot_config_overrides
)

def test_robot_detection():
    """Test all robot detection functions."""
    print("=" * 60)
    print("Robot Detection Test")
    print("=" * 60)
    
    # Test robot name detection
    robot_name = get_robot_name()
    print(f"\n1. Robot Name Detection:")
    print(f"   Detected: {robot_name}")
    print(f"   Expected: 'f7' or 'm7'")
    print(f"   Status: {'✓ PASS' if robot_name in ['f7', 'm7'] else '✗ FAIL'}")
    
    # Test motor address detection
    motor_addresses = get_motor_addresses()
    print(f"\n2. Motor Addresses Detection:")
    print(f"   Detected: {motor_addresses}")
    if robot_name == 'm7':
        expected = [27, 29, 25, 26]
        print(f"   Expected for m7: {expected}")
    else:  # f7
        expected = [28, 30, 26, 27]
        print(f"   Expected for f7: {expected}")
    print(f"   Status: {'✓ PASS' if motor_addresses == expected else '✗ FAIL'}")
    
    # Test dribbler address detection
    dribbler_address = get_dribbler_address()
    print(f"\n3. Dribbler Address Detection:")
    print(f"   Detected: {dribbler_address}")
    if robot_name == 'm7':
        expected_dribbler = 30
        print(f"   Expected for m7: {expected_dribbler}")
    else:  # f7
        expected_dribbler = 29
        print(f"   Expected for f7: {expected_dribbler}")
    print(f"   Status: {'✓ PASS' if dribbler_address == expected_dribbler else '✗ FAIL'}")
    
    # Test complete config overrides
    config_overrides = get_robot_config_overrides()
    print(f"\n4. Complete Configuration Overrides:")
    print(f"   Robot Name: {config_overrides['robot_name']}")
    print(f"   Motor Addresses: {config_overrides['motor_addresses']}")
    print(f"   Dribbler Address: {config_overrides['dribbler']['address']}")
    
    # Verify consistency
    all_consistent = (
        config_overrides['robot_name'] == robot_name and
        config_overrides['motor_addresses'] == motor_addresses and
        config_overrides['dribbler']['address'] == dribbler_address
    )
    print(f"   Status: {'✓ PASS - All values consistent' if all_consistent else '✗ FAIL - Inconsistent values'}")
    
    # Test address mapping (f7 specific)
    if robot_name == 'f7':
        print(f"\n5. Address Mapping Verification (f7 only):")
        m7_base = [27, 29, 25, 26]
        mapping = {25: 26, 26: 27, 27: 28, 29: 30}
        expected_f7 = [mapping[addr] for addr in m7_base]
        print(f"   m7 base addresses: {m7_base}")
        print(f"   Mapping: {mapping}")
        print(f"   Expected f7 addresses: {expected_f7}")
        print(f"   Detected f7 addresses: {motor_addresses}")
        print(f"   Status: {'✓ PASS - Mapping correct' if motor_addresses == expected_f7 else '✗ FAIL - Mapping incorrect'}")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    test_robot_detection()
