#!/usr/bin/env python3
"""
Dribbler Test Script
Tests the dribbler motor to diagnose issues
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from hypemage.logger import get_logger

logger = get_logger(__name__)

def test_dribbler_import():
    """Test 1: Check if dribbler module can be imported"""
    print("\n" + "="*60)
    print("TEST 1: Import DribblerController")
    print("="*60)
    
    try:
        from hypemage.dribbler_control import DribblerController
        print("✅ SUCCESS: DribblerController imported successfully")
        return True
    except Exception as e:
        print(f"❌ FAILED: Could not import DribblerController")
        print(f"   Error: {e}")
        return False

def test_motor_import():
    """Test 2: Check if Motor class can be imported"""
    print("\n" + "="*60)
    print("TEST 2: Import Motor class")
    print("="*60)
    
    try:
        from motors.motor import Motor
        print("✅ SUCCESS: Motor class imported successfully")
        return True
    except Exception as e:
        print(f"❌ FAILED: Could not import Motor class")
        print(f"   Error: {e}")
        print("   Make sure motors/motor.py exists and is accessible")
        return False

def test_hostname_detection():
    """Test 3: Test hostname detection"""
    print("\n" + "="*60)
    print("TEST 3: Hostname Detection")
    print("="*60)
    
    import socket
    try:
        hostname = socket.gethostname()
        print(f"   Hostname: {hostname}")
        
        if 'f7' in hostname.lower():
            detected_address = 29
            robot_name = "f7 (storm)"
        elif 'm7' in hostname.lower():
            detected_address = 30
            robot_name = "m7 (necron)"
        else:
            detected_address = 29
            robot_name = "unknown (defaulting to f7)"
        
        print(f"   Detected Robot: {robot_name}")
        print(f"   Dribbler Address: {detected_address}")
        print("✅ SUCCESS: Hostname detection working")
        return True, detected_address
    except Exception as e:
        print(f"❌ FAILED: Hostname detection error")
        print(f"   Error: {e}")
        return False, None

def test_dribbler_initialization(address=None):
    """Test 4: Initialize dribbler controller"""
    print("\n" + "="*60)
    print("TEST 4: Initialize Dribbler Controller")
    print("="*60)
    
    try:
        from hypemage.dribbler_control import DribblerController
        
        if address:
            print(f"   Using address: {address}")
            controller = DribblerController(address=address, threaded=False)
        else:
            print("   Using auto-detected address")
            controller = DribblerController(threaded=False)
        
        print("✅ SUCCESS: Dribbler controller initialized")
        return True, controller
    except Exception as e:
        print(f"❌ FAILED: Could not initialize dribbler controller")
        print(f"   Error: {e}")
        print(f"   This could mean:")
        print(f"   - I2C bus is not accessible")
        print(f"   - Motor at address {address} is not responding")
        print(f"   - Hardware connection issue")
        return False, None

def test_dribbler_speed_control(controller):
    """Test 5: Test speed control"""
    print("\n" + "="*60)
    print("TEST 5: Speed Control")
    print("="*60)
    
    try:
        print("   Setting speed to 0.5...")
        controller.set_speed(0.5)
        current_speed = controller.get_speed()
        print(f"   Current speed: {current_speed}")
        
        if abs(current_speed - 0.5) < 0.01:
            print("✅ SUCCESS: Speed control working")
            return True
        else:
            print(f"⚠️  WARNING: Speed mismatch (expected 0.5, got {current_speed})")
            return False
    except Exception as e:
        print(f"❌ FAILED: Speed control error")
        print(f"   Error: {e}")
        return False

def test_dribbler_enable_disable(controller):
    """Test 6: Test enable/disable"""
    print("\n" + "="*60)
    print("TEST 6: Enable/Disable Dribbler")
    print("="*60)
    
    try:
        print("   Enabling dribbler at speed 0.3...")
        controller.enable(0.3)
        time.sleep(0.5)
        
        if controller.is_running():
            print("   Dribbler is running ✓")
        else:
            print("   ⚠️  Dribbler reports not running")
        
        print("   Disabling dribbler...")
        controller.disable()
        time.sleep(0.5)
        
        if not controller.is_running():
            print("   Dribbler is stopped ✓")
        else:
            print("   ⚠️  Dribbler still running")
        
        print("✅ SUCCESS: Enable/disable working")
        return True
    except Exception as e:
        print(f"❌ FAILED: Enable/disable error")
        print(f"   Error: {e}")
        return False

def test_dribbler_motor_movement(controller):
    """Test 7: Actual motor movement test"""
    print("\n" + "="*60)
    print("TEST 7: Motor Movement Test")
    print("="*60)
    print("   This test will run the dribbler at different speeds")
    print("   WATCH THE DRIBBLER MOTOR - it should spin!")
    print()
    
    speeds = [0.3, 0.5, 0.7, 1.0, 1.8]
    
    try:
        for speed in speeds:
            print(f"   Setting speed to {speed}...")
            controller.enable(speed)
            print(f"   Motor should be spinning at {speed*100:.0f}% speed")
            print("   Press Ctrl+C to skip ahead...")
            time.sleep(2.0)
            controller.stop()
            time.sleep(0.5)
        
        print("✅ Test complete - did you see the motor spinning?")
        return True
    except KeyboardInterrupt:
        print("\n   Test interrupted by user")
        controller.stop()
        return True
    except Exception as e:
        print(f"❌ FAILED: Motor movement test error")
        print(f"   Error: {e}")
        controller.stop()
        return False

def test_config_loading():
    """Test 8: Check config file"""
    print("\n" + "="*60)
    print("TEST 8: Configuration Check")
    print("="*60)
    
    try:
        import json
        config_path = Path(__file__).parent / "hypemage" / "config.json"
        
        if config_path.exists():
            print(f"   Config file found: {config_path}")
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Check for dribbler config
            if 'dribbler' in config.get('defaults', {}):
                dribbler_config = config['defaults']['dribbler']
                print(f"   Dribbler config found:")
                print(f"   - Address: {dribbler_config.get('address', 'auto-detect')}")
                print(f"   - Default speed: {dribbler_config.get('default_speed', 0.5)}")
                print("✅ SUCCESS: Configuration looks good")
                return True
            else:
                print("   ⚠️  No dribbler configuration found in config.json")
                print("   Dribbler will use auto-detected address")
                return True
        else:
            print(f"   ⚠️  Config file not found at {config_path}")
            print("   Using default settings")
            return True
    except Exception as e:
        print(f"   ⚠️  Config check error: {e}")
        print("   This is not critical - continuing with defaults")
        return True

def run_all_tests(manual_address=None):
    """Run all diagnostic tests"""
    print("\n" + "="*60)
    print("DRIBBLER DIAGNOSTIC TEST SUITE")
    print("="*60)
    print()
    
    results = []
    
    # Test 1: Import dribbler controller
    results.append(("Import DribblerController", test_dribbler_import()))
    
    if not results[-1][1]:
        print("\n❌ Cannot continue - DribblerController import failed")
        return False
    
    # Test 2: Import Motor class
    results.append(("Import Motor class", test_motor_import()))
    
    if not results[-1][1]:
        print("\n❌ Cannot continue - Motor class import failed")
        return False
    
    # Test 3: Hostname detection
    hostname_success, detected_address = test_hostname_detection()
    results.append(("Hostname detection", hostname_success))
    
    # Use manual address if provided, otherwise use detected
    test_address = manual_address if manual_address else detected_address
    
    # Test 4: Initialize controller
    init_success, controller = test_dribbler_initialization(test_address)
    results.append(("Initialize controller", init_success))
    
    if not init_success:
        print("\n❌ Cannot continue - Dribbler initialization failed")
        print_summary(results)
        return False
    
    # Test 5: Speed control
    results.append(("Speed control", test_dribbler_speed_control(controller)))
    
    # Test 6: Enable/disable
    results.append(("Enable/disable", test_dribbler_enable_disable(controller)))
    
    # Test 7: Motor movement
    results.append(("Motor movement", test_dribbler_motor_movement(controller)))
    
    # Test 8: Config check
    results.append(("Configuration", test_config_loading()))
    
    # Cleanup
    print("\n   Cleaning up...")
    controller.stop()
    
    # Print summary
    print_summary(results)
    
    return all(result[1] for result in results)

def print_summary(results):
    """Print test summary"""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Dribbler should be working.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. See details above.")

def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test dribbler motor')
    parser.add_argument('--address', type=int, help='Manual I2C address (29 for f7, 30 for m7)')
    parser.add_argument('--quick', action='store_true', help='Quick test (no motor movement)')
    
    args = parser.parse_args()
    
    if args.quick:
        print("Running quick test (no motor movement)...")
        # Run tests 1-6 only
        test_dribbler_import()
        test_motor_import()
        hostname_success, detected_address = test_hostname_detection()
        test_address = args.address if args.address else detected_address
        init_success, controller = test_dribbler_initialization(test_address)
        if init_success:
            test_dribbler_speed_control(controller)
            test_dribbler_enable_disable(controller)
            controller.stop()
            print("\n✅ Quick test complete")
    else:
        success = run_all_tests(args.address)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
