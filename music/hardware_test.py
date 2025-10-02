# hardware_test.py - Copy as code.py to test HARDWARE
# This will work even if imports fail

try:
    print("🔧 HARDWARE TEST STARTING")
    
    # Test basic functionality first
    import time
    print("✅ Time module works")
    
    # Test board access
    import board
    print("✅ Board module works")
    print("Available pins:", [p for p in dir(board) if p.startswith('GP')])
    
    # Test PWM
    import pwmio
    print("✅ PWMio module works")
    
    # Test specific pins
    print("🔍 Testing GP17...")
    try:
        test1 = pwmio.PWMOut(board.GP17, frequency=1000, duty_cycle=0)
        print("✅ GP17 PWM created successfully")
        test1.deinit()
    except Exception as e:
        print(f"❌ GP17 failed: {e}")
    
    print("🔍 Testing GP14...")
    try:
        test2 = pwmio.PWMOut(board.GP14, frequency=1000, duty_cycle=0)  
        print("✅ GP14 PWM created successfully")
        test2.deinit()
    except Exception as e:
        print(f"❌ GP14 failed: {e}")
    
    print("🎉 HARDWARE TEST COMPLETE")
    
except Exception as e:
    print(f"❌ CRITICAL ERROR: {e}")
    print(f"Error type: {type(e).__name__}")

print("💓 Script finished - check results above!")

# Keep running so you can see output
while True:
    time.sleep(10)
    print("💓 Still running...")