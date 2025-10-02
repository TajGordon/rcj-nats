# working_test.py - Using the correct variable_frequency parameter
import time
import board
import pwmio

print("🎵 Working Piezo Test - Using variable_frequency=True")

try:
    # Create PWM with variable_frequency=True (this was the missing piece!)
    print("🔧 Creating piezo on GP17 with variable_frequency=True...")
    buzzer1 = pwmio.PWMOut(board.GP17, variable_frequency=True)
    
    print("🔧 Creating piezo on GP14 with variable_frequency=True...")
    buzzer2 = pwmio.PWMOut(board.GP14, variable_frequency=True)
    
    print("✅ Both piezos created successfully!")
    
    # Define musical notes
    TONE_FREQ = [262, 294, 330, 349, 392, 440, 494, 523]  # C4 to C5
    
    print("🎵 Testing GP17 - playing scale...")
    buzzer1.duty_cycle = 2**15  # 50% duty cycle
    
    for i, freq in enumerate(TONE_FREQ):
        print(f"   Note {i+1}: {freq}Hz")
        buzzer1.frequency = freq
        time.sleep(0.5)
    
    buzzer1.duty_cycle = 0  # Stop
    print("✅ GP17 scale complete")
    
    time.sleep(0.5)
    
    print("🎵 Testing GP14 - playing scale...")
    buzzer2.duty_cycle = 2**15  # 50% duty cycle
    
    for i, freq in enumerate(TONE_FREQ):
        print(f"   Note {i+1}: {freq}Hz")
        buzzer2.frequency = freq
        time.sleep(0.5)
    
    buzzer2.duty_cycle = 0  # Stop
    print("✅ GP14 scale complete")
    
    print("🎼 Testing harmony - both piezos together...")
    buzzer1.frequency = 262  # C4
    buzzer2.frequency = 330  # E4
    buzzer1.duty_cycle = 2**15
    buzzer2.duty_cycle = 2**15
    
    time.sleep(3)  # Play chord for 3 seconds
    
    buzzer1.duty_cycle = 0
    buzzer2.duty_cycle = 0
    print("✅ Harmony test complete")
    
    print("🎉 ALL TESTS PASSED!")
    print("🔊 If you heard clear musical notes, hardware is perfect!")
    
    # Cleanup
    buzzer1.deinit()
    buzzer2.deinit()
    
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"Error type: {type(e).__name__}")

print("💓 Test complete - check your piezos!")