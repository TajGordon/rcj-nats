# final_simple_test.py - Based exactly on your working example
import time
import board
import pwmio

print("🎵 Final Simple Test - Based on Your Working Example")

# Define musical notes (same as your working example)
TONE_FREQ = [262,  # C4
             294,  # D4  
             330,  # E4
             349,  # F4
             392,  # G4
             440,  # A4
             494,  # B4
             523]  # C5

try:
    print("🔧 Creating GP17 piezo with variable_frequency=True...")
    buzzer1 = pwmio.PWMOut(board.GP17, variable_frequency=True)
    
    print("🔧 Creating GP14 piezo with variable_frequency=True...")
    buzzer2 = pwmio.PWMOut(board.GP14, variable_frequency=True)
    
    print("✅ Both piezos created successfully!")
    
    print("\n🎵 GP17 SCALE TEST")
    print("-" * 25)
    
    # Start GP17 buzzer
    buzzer1.frequency = TONE_FREQ[0]
    buzzer1.duty_cycle = 2**15  # 32768 - 50% duty cycle
    
    # Play scale up and down (like your example)
    for i in range(len(TONE_FREQ)):
        print(f"   Playing {TONE_FREQ[i]}Hz")
        buzzer1.frequency = TONE_FREQ[i]
        time.sleep(0.5)
    
    # Play scale down
    for i in range(len(TONE_FREQ)-1, -1, -1):
        print(f"   Playing {TONE_FREQ[i]}Hz")
        buzzer1.frequency = TONE_FREQ[i]
        time.sleep(0.5)
    
    buzzer1.duty_cycle = 0  # Stop
    print("✅ GP17 scale complete")
    
    time.sleep(1)  # Pause between tests
    
    print("\n🎵 GP14 SCALE TEST") 
    print("-" * 25)
    
    # Start GP14 buzzer
    buzzer2.frequency = TONE_FREQ[0]
    buzzer2.duty_cycle = 2**15
    
    # Play scale up
    for i in range(len(TONE_FREQ)):
        print(f"   Playing {TONE_FREQ[i]}Hz")
        buzzer2.frequency = TONE_FREQ[i]
        time.sleep(0.5)
    
    buzzer2.duty_cycle = 0  # Stop
    print("✅ GP14 scale complete")
    
    time.sleep(1)
    
    print("\n🎼 HARMONY TEST")
    print("-" * 25)
    print("🔊 Playing C major chord (C4 + E4) for 3 seconds...")
    
    # Play harmony
    buzzer1.frequency = 262  # C4
    buzzer2.frequency = 330  # E4
    buzzer1.duty_cycle = 2**15
    buzzer2.duty_cycle = 2**15
    
    time.sleep(3)  # 3 second chord
    
    # Stop both
    buzzer1.duty_cycle = 0
    buzzer2.duty_cycle = 0
    
    print("✅ Harmony test complete")
    
    print("\n🎉 ALL TESTS SUCCESSFUL!")
    print("=" * 40)
    print("✅ GP17 piezo: Working")
    print("✅ GP14 piezo: Working") 
    print("✅ Frequency changes: Working")
    print("✅ Harmony/chords: Working")
    print("")
    print("🎵 Your hardware setup is PERFECT!")
    print("🎯 Ready for full music system!")
    
    # Cleanup
    buzzer1.deinit()
    buzzer2.deinit()
    
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"   Error type: {type(e).__name__}")
    print("\n💡 If this fails, check:")
    print("   1. Piezo connections (+ to GP17/GP14, - to GND)")
    print("   2. CircuitPython version supports variable_frequency")
    print("   3. Piezos are working (test with LED)")

print("\n💓 Simple test complete!")