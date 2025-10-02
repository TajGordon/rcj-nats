# fixed_test.py - Simple test with the PWM fix
print("🎵 Fixed Piezo Test Starting...")

try:
    import time
    import pwmio
    import board
    
    print("✅ Modules imported")
    
    # Test the fixed approach - recreate PWM for each frequency
    class FixedPiezo:
        def __init__(self, pin, name):
            self.pin = pin
            self.name = name
            self.pwm = None
            self.current_freq = 440
            
        def play_note(self, frequency, duration=1.0):
            try:
                # Always recreate PWM with new frequency
                if self.pwm:
                    self.pwm.deinit()
                
                self.pwm = pwmio.PWMOut(self.pin, frequency=int(frequency), duty_cycle=0)
                self.current_freq = frequency
                
                # Turn on
                self.pwm.duty_cycle = 32767
                print(f"✅ {self.name} playing {frequency}Hz")
                
                if duration:
                    time.sleep(duration)
                    self.pwm.duty_cycle = 0
                    
            except Exception as e:
                print(f"❌ Error on {self.name}: {e}")
        
        def stop(self):
            if self.pwm:
                self.pwm.duty_cycle = 0
        
        def cleanup(self):
            if self.pwm:
                self.pwm.deinit()
    
    # Test both piezos
    print("🔧 Creating piezos...")
    piezo1 = FixedPiezo(board.GP17, "GP17")
    piezo2 = FixedPiezo(board.GP14, "GP14")
    
    print("🎵 Testing different frequencies...")
    
    # Test scale
    notes = [262, 294, 330, 349, 392, 440, 494, 523]  # C4 to C5
    
    for freq in notes:
        print(f"Playing {freq}Hz...")
        piezo1.play_note(freq, 0.5)
        time.sleep(0.1)
    
    print("🎼 Testing harmony...")
    # Test both at once
    piezo1.play_note(262, 0)  # C4 - no duration (async)
    piezo2.play_note(330, 0)  # E4 - no duration (async)
    
    time.sleep(2)  # Let them play together
    
    piezo1.stop()
    piezo2.stop()
    
    print("✅ Fixed PWM test complete!")
    
    # Cleanup
    piezo1.cleanup()
    piezo2.cleanup()
    
except Exception as e:
    print(f"❌ Error: {e}")
    print(f"Type: {type(e).__name__}")

print("🎉 Test finished!")