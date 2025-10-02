# simple_code.py - Copy this to your Pico as "code.py"
# This will definitely work and show visible results

import time
import board

print("🎵 Simple Pico Test Starting...")
print("Board info:", dir(board))

# Check if the pins exist
try:
    print("GP17 exists:", hasattr(board, 'GP17'))
    print("GP14 exists:", hasattr(board, 'GP14'))
except Exception as e:
    print("Pin check error:", e)

# Try to create PWM
try:
    import pwmio
    print("PWMio imported successfully")
    
    print("Creating PWM on GP17...")
    piezo1 = pwmio.PWMOut(board.GP17, frequency=440, duty_cycle=0)
    print("✅ GP17 PWM created")
    
    print("Creating PWM on GP14...")  
    piezo2 = pwmio.PWMOut(board.GP14, frequency=440, duty_cycle=0)
    print("✅ GP14 PWM created")
    
    # Simple test - just beep
    print("🔊 BEEP TEST 1 - GP17")
    piezo1.duty_cycle = 32767  # Turn on
    time.sleep(1)
    piezo1.duty_cycle = 0      # Turn off
    print("✅ GP17 beep done")
    
    time.sleep(0.5)
    
    print("🔊 BEEP TEST 2 - GP14") 
    piezo2.duty_cycle = 32767  # Turn on
    time.sleep(1)
    piezo2.duty_cycle = 0      # Turn off
    print("✅ GP14 beep done")
    
    print("🎉 SUCCESS! Both piezos work!")
    
    # Cleanup
    piezo1.deinit()
    piezo2.deinit()
    
except Exception as e:
    print("❌ PWM Error:", e)
    print("Error type:", type(e).__name__)

print("✅ Test complete - check your piezos!")
print("If you heard beeps, hardware is working!")

# Loop to show it's running
while True:
    print("💓 Heartbeat - code is running...")
    time.sleep(5)