"""
Direct camera test - verify camera works before trying to stream
Run this on the robot to test if camera is accessible
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from camera import CameraProcess
from config import get_robot_id
import cv2

def test_camera():
    print("=" * 60)
    print("CAMERA DIRECT TEST")
    print("=" * 60)
    
    # Get robot ID
    robot_id = get_robot_id()
    print(f"Robot ID: {robot_id}")
    
    # Try to initialize camera
    print("\n1. Initializing CameraProcess...")
    try:
        camera = CameraProcess(robot_id=robot_id)
        print("   ✓ Camera initialized successfully")
    except Exception as e:
        print(f"   ✗ FAILED to initialize camera: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Try to capture a frame
    print("\n2. Capturing test frame...")
    try:
        frame = camera.capture_frame()
        if frame is None:
            print("   ✗ capture_frame() returned None")
            return
        else:
            print(f"   ✓ Frame captured: shape={frame.shape}, dtype={frame.dtype}")
    except Exception as e:
        print(f"   ✗ FAILED to capture frame: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Try ball detection
    print("\n3. Testing ball detection...")
    try:
        ball = camera.detect_ball(frame)
        print(f"   ✓ Ball detection ran: detected={ball.detected}")
        if ball.detected:
            print(f"     Position: ({ball.center_x}, {ball.center_y}), radius={ball.radius}")
    except Exception as e:
        print(f"   ✗ FAILED ball detection: {e}")
        import traceback
        traceback.print_exc()
    
    # Try goal detection
    print("\n4. Testing goal detection...")
    try:
        blue_goal, yellow_goal = camera.detect_goals(frame)
        print(f"   ✓ Goal detection ran")
        print(f"     Blue goal: detected={blue_goal.detected}")
        print(f"     Yellow goal: detected={yellow_goal.detected}")
    except Exception as e:
        print(f"   ✗ FAILED goal detection: {e}")
        import traceback
        traceback.print_exc()
    
    # Try to capture multiple frames
    print("\n5. Capturing 10 frames to test reliability...")
    success_count = 0
    for i in range(10):
        try:
            frame = camera.capture_frame()
            if frame is not None and frame.size > 0:
                success_count += 1
            else:
                print(f"   Frame {i+1}: None or empty")
        except Exception as e:
            print(f"   Frame {i+1}: ERROR - {e}")
    
    print(f"   ✓ Captured {success_count}/10 frames successfully")
    
    # Cleanup
    print("\n6. Cleaning up...")
    try:
        camera.stop()
        print("   ✓ Camera stopped")
    except Exception as e:
        print(f"   Warning: cleanup error: {e}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    
    if success_count >= 8:
        print("✓ Camera is working properly!")
        print("  If stream still doesn't work, check:")
        print("  1. Is the script actually running? Check terminal output")
        print("  2. Are you using the correct URL? http://m7.local:8766/stream")
        print("  3. Is port 8766 accessible? Try: curl http://m7.local:8766/")
        print("  4. Check firewall settings on the robot")
    else:
        print("✗ Camera is having issues - see errors above")
        print("  Common fixes:")
        print("  1. Check camera cable connection")
        print("  2. Restart the robot")
        print("  3. Check if another process is using the camera")
        print("  4. Verify camera permissions: sudo usermod -a -G video $USER")

if __name__ == "__main__":
    test_camera()
