#!/usr/bin/env python3
"""
Quick test script to check if the localization system works
"""

import os
import sys

def check_dependencies():
    """Check if required packages are available"""
    required = ['fastapi', 'uvicorn']
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
            print(f"✅ {pkg}")
        except ImportError:
            print(f"❌ {pkg} - missing")
            missing.append(pkg)
    
    if missing:
        print(f"\n💡 Install missing packages:")
        print(f"   pip install {' '.join(missing)}")
        return False
    return True

def check_files():
    """Check if required files exist"""
    files = [
        'localization_system.py',
        'localizer.py', 
        'config.py',
        'tof.py',
        'imu.py'
    ]
    
    for file in files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"⚠️  {file} - not found (may cause issues)")

def main():
    print("🔧 Localization System Test")
    print("=" * 30)
    
    print("\n📦 Checking dependencies:")
    deps_ok = check_dependencies()
    
    print("\n📁 Checking files:")
    check_files()
    
    print("\n🚀 Test completed!")
    
    if deps_ok:
        print("✅ Ready to run: python localization_system.py")
    else:
        print("❌ Install missing dependencies first")
    
    print("\n💡 Troubleshooting:")
    print("   - Make sure you're in the localization directory")
    print("   - Install: pip install fastapi uvicorn")
    print("   - For hardware issues, check I2C connections")

if __name__ == "__main__":
    main()