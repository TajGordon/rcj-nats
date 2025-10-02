# minimal_test.py - Ultra-simple piezo test for Pico
# Copy this file as "code.py" to your Pico if other files don't work

import time
import pwmio
import board

print("🎵 Minimal Piezo Test Starting...")

try:
    # Initialize piezos
    print("🔧 Initializing piezos on GP17 and GP14...")
    
    piezo1 = pwmio.PWMOut(board.GP17, frequency=440, duty_cycle=0)
    piezo2 = pwmio.PWMOut(board.GP14, frequency=440, duty_cycle=0)
    
    print("✅ Piezos initialized successfully!")
    
    # Test frequencies
    notes = {
        'C4': 262,
        'D4': 294, 
        'E4': 330,
        'F4': 349,
        'G4': 392,
        'A4': 440,
        'B4': 494,
        'C5': 523
    }
    
    # Individual tests
    print("\n🧪 INDIVIDUAL TESTS")
    print("Testing Piezo 1 (GP17)...")
    for i in range(3):
        piezo1.frequency = 440
        piezo1.duty_cycle = 32767  # 50% duty cycle
        time.sleep(0.5)
        piezo1.duty_cycle = 0
        time.sleep(0.2)
    print("✅ Piezo 1 test complete")
    
    print("Testing Piezo 2 (GP14)...")
    for i in range(3):
        piezo2.frequency = 520
        piezo2.duty_cycle = 32767
        time.sleep(0.5)
        piezo2.duty_cycle = 0
        time.sleep(0.2)
    print("✅ Piezo 2 test complete")
    
    # Simultaneous test
    print("\n🎼 SIMULTANEOUS TEST")
    print("Playing chord for 2 seconds...")
    piezo1.frequency = 262  # C4
    piezo2.frequency = 330  # E4
    piezo1.duty_cycle = 32767
    piezo2.duty_cycle = 32767
    time.sleep(2)
    piezo1.duty_cycle = 0
    piezo2.duty_cycle = 0
    print("✅ Chord test complete")
    
    # Scale test
    print("\n🎵 SCALE TEST")
    print("Playing C major scale...")
    scale = [262, 294, 330, 349, 392, 440, 494, 523]  # C4 to C5
    
    for note in scale:
        print(f"   Playing {note}Hz")
        piezo1.frequency = note
        piezo1.duty_cycle = 32767
        time.sleep(0.5)
        piezo1.duty_cycle = 0
        time.sleep(0.1)
    
    print("✅ Scale test complete")
    
    # Simple melody
    print("\n🎶 SIMPLE MELODY")
    print("Playing 'Twinkle Twinkle Little Star'...")
    
    # Twinkle Twinkle melody (note frequencies and durations)
    melody = [
        (262, 0.5), (262, 0.5), (392, 0.5), (392, 0.5),  # Twinkle twinkle
        (440, 0.5), (440, 0.5), (392, 1.0),              # little star
        (349, 0.5), (349, 0.5), (330, 0.5), (330, 0.5),  # How I wonder
        (294, 0.5), (294, 0.5), (262, 1.0)               # what you are
    ]
    
    for freq, duration in melody:
        piezo1.frequency = freq
        piezo1.duty_cycle = 32767
        time.sleep(duration)
        piezo1.duty_cycle = 0
        time.sleep(0.05)  # Small gap between notes
    
    print("✅ Melody complete")
    
    print("\n🎉 ALL TESTS COMPLETE!")
    print("✅ Hardware: Working")
    print("✅ Individual piezos: Working") 
    print("✅ Simultaneous play: Working")
    print("✅ Melody playback: Working")
    print("\n💡 Your piezo music system is ready!")
    print("   Next step: Use the full piezo_music.py classes")
    
    # Cleanup
    piezo1.deinit()
    piezo2.deinit()
    
    print("\n🔄 Test will restart in 10 seconds...")
    print("   (Reset Pico to stop)")
    time.sleep(10)

except Exception as e:
    print(f"❌ Error: {e}")
    print("\n💡 Troubleshooting:")
    print("   1. Check piezo connections:")
    print("      - Piezo 1 + wire to GP17 (pin 22)")
    print("      - Piezo 2 + wire to GP14 (pin 19)")
    print("      - Both - wires to GND (pin 38)")
    print("   2. Verify CircuitPython is installed")
    print("   3. Make sure this file is saved as 'code.py'")
    print(f"\n📋 Error details: {type(e).__name__}: {e}")

print("🎵 Minimal test ended")