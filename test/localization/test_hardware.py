#!/usr/bin/env python3
"""
Simple ToF hardware detection test
"""
import sys
import os

# Add current directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    import test.localization.tconf as tconf
    print("✅ Config loaded successfully")
    print(f"   tof_addrs: {tconf.tof_addrs}")
    print(f"   tof_offsets: {tconf.tof_offsets}")
    print(f"   tof_angles: {tconf.tof_angles}")
except ImportError as e:
    print(f"❌ Config import failed: {e}")
    exit(1)

try:
    import board
    print("✅ Board module available")
except ImportError as e:
    print(f"❌ Board module not available: {e}")
    print("   This is expected on non-hardware platforms")

try:
    from tof import ToF
    print("✅ ToF class available")
except ImportError as e:
    print(f"❌ ToF class not available: {e}")
    print("   Make sure tof.py is in the correct path")

try:
    from imu import IMU
    print("✅ IMU class available")
except ImportError as e:
    print(f"❌ IMU class not available: {e}")
    print("   Make sure imu.py is in the correct path")

# Test config parsing
print("\n🔧 Testing config parsing...")
if hasattr(tconf, 'tof_addrs') and tconf.tof_addrs:
    for i, addr in enumerate(tconf.tof_addrs):
        offset = tconf.tof_offsets[i] if i < len(tconf.tof_offsets) else 0
        angle = tconf.tof_angles[i] if i < len(tconf.tof_angles) else 0
        print(f"   ToF {i}: addr=0x{addr:02x}, offset={offset}mm, angle={angle}°")
else:
    print("   No tof_addrs found in config")