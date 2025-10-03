#!/usr/bin/env python3
"""
Startup script for the robot localization server.
Run this to start the web server and view the localization data.
"""

import subprocess
import sys
import os

def check_dependencies():
    """Check if required packages are installed."""
    required_packages = ['fastapi', 'uvicorn', 'websockets', 'jinja2']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Install them with:")
        print("   pip install -r requirements.txt")
        return False
    
    return True

def main():
    print("🤖 Robot Localization Server Startup")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists("main.py"):
        print("❌ Error: main.py not found!")
        print("💡 Please run this script from the localization_server directory:")
        print("   cd localization_server")
        print("   python start_server.py")
        return 1
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    print("✅ All dependencies found")
    print("🚀 Starting localization server...")
    print()
    print("📍 Robot should connect to: ws://localhost:8002/ws/localization")
    print("🌐 View field visualization at: http://localhost:8002")
    print("🛑 Press Ctrl+C to stop the server")
    print()
    
    try:
        # Start the FastAPI server
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", "8002", 
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())