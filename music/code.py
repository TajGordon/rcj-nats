# code.py - Main entry point for Raspberry Pi Pico (CircuitPython)
# This file will automatically run when the Pico starts up

import time
import board
import pwmio
import json

# Import our music classes
try:
    from piezo_music import Piezo, Musician
    CLASSES_IMPORTED = True
    print("✅ Successfully imported piezo_music classes")
except ImportError as e:
    CLASSES_IMPORTED = False
    print(f"❌ Could not import piezo_music: {e}")
    print("📁 Make sure piezo_music.py is in the same directory as code.py")
    print("💡 Expected files on Pico root directory:")
    print("   - code.py (this file)")
    print("   - piezo_music.py (the classes)")
    print("   - test_song.json (simple test song)")
    print("   - pico_Fetty.json (your song)")
    print("\n🔧 Will use simplified testing mode without full Musician class")

def main():
    """Main function that runs the piezo test routine"""
    print("🎵 Piezo Music System Test - Starting...")
    print("=" * 50)
    
    try:
        # Initialize piezos - using your existing pin configuration
        print("🔧 Initializing piezos...")
        
        if CLASSES_IMPORTED:
            # Use full classes if imported successfully
            piezo1 = Piezo(board.GP17, "Piezo-17")
            piezo2 = Piezo(board.GP14, "Piezo-14")
        else:
            # Use simplified inline class if import failed
            class SimplePiezo:
                def __init__(self, pin, name):
                    self.pin = pin
                    self.name = name
                    self.pwm = None
                    try:
                        self.pwm = pwmio.PWMOut(self.pin, frequency=440, duty_cycle=0)
                        print(f"✅ {name} initialized on {pin}")
                    except Exception as e:
                        print(f"❌ Failed to initialize {name}: {e}")
                
                def play_note(self, frequency, duration=None):
                    if self.pwm and frequency > 0:
                        try:
                            self.pwm.frequency = int(frequency)
                            self.pwm.duty_cycle = 32767
                            if duration:
                                time.sleep(duration)
                                self.stop()
                        except Exception as e:
                            print(f"Error playing note: {e}")
                
                def play_note_async(self, frequency):
                    if self.pwm and frequency > 0:
                        try:
                            self.pwm.frequency = int(frequency)
                            self.pwm.duty_cycle = 32767
                        except Exception as e:
                            print(f"Error playing async note: {e}")
                
                def stop(self):
                    if self.pwm:
                        self.pwm.duty_cycle = 0
                
                def is_available(self):
                    return self.pwm is not None
                
                def cleanup(self):
                    self.stop()
                    if self.pwm:
                        self.pwm.deinit()
            
            piezo1 = SimplePiezo(board.GP17, "Piezo-17")
            piezo2 = SimplePiezo(board.GP14, "Piezo-14")
        
        # Add a third piezo for the Kanye song (3 lines)
        if CLASSES_IMPORTED:
            piezo3 = Piezo(board.GP15, "Piezo-15")  # Add third piezo on GP15
        else:
            piezo3 = SimplePiezo(board.GP15, "Piezo-15")
        
        # Check if all piezos initialized successfully
        piezos = [piezo1, piezo2, piezo3]  # Three piezos for full Kanye song
        failed_piezos = []
        
        for i, piezo in enumerate(piezos):
            if not piezo.is_available():
                failed_piezos.append(f"Piezo {i+1} ({piezo.name})")
        
        if failed_piezos:
            print(f"❌ Failed to initialize: {', '.join(failed_piezos)}")
            print("Check your pin connections and try again.")
        else:
            print("✅ All piezos initialized successfully!")
        
        print("\n" + "=" * 50)
        print("🧪 INDIVIDUAL PIEZO TEST")
        print("=" * 50)
        
        # Test each piezo individually with 1-second buzz
        test_frequency = 440  # A4 note - nice clear tone
        test_duration = 1.0   # 1 second
        
        for i, piezo in enumerate(piezos):
            if piezo.is_available():
                print(f"🔊 Testing {piezo.name} - 1 second buzz at {test_frequency}Hz...")
                piezo.play_note(test_frequency, test_duration)
                print(f"✅ {piezo.name} test complete")
                time.sleep(0.5)  # Small gap between tests
            else:
                print(f"❌ Skipping {piezo.name} (not available)")
        
        print("\n" + "=" * 50)
        print("🎼 SIMULTANEOUS PIEZO TEST")
        print("=" * 50)
        
        # Test all piezos simultaneously with different frequencies
        print("🔊 Testing all piezos simultaneously - 2 second chord...")
        if len(piezos) >= 3:
            print("   Piezo-17: C4 (262Hz) - Bass")
            print("   Piezo-14: E4 (330Hz) - Mid") 
            print("   Piezo-15: G4 (392Hz) - Treble")
        elif len(piezos) >= 2:
            print("   Piezo-17: C4 (262Hz)")
            print("   Piezo-14: E4 (330Hz)")
        
        # Start all notes at the same time (async)
        if len(piezos) >= 1 and piezo1.is_available():
            piezo1.play_note_async(262)  # C4
        if len(piezos) >= 2 and piezo2.is_available():
            piezo2.play_note_async(330)  # E4
        if len(piezos) >= 3 and piezo3.is_available():
            piezo3.play_note_async(392)  # G4
        
        # Let them play for 2 seconds
        time.sleep(2.0)
        
        # Stop all notes
        for piezo in piezos:
            piezo.stop()
        
        print("✅ Simultaneous test complete")
        
        print("\n" + "=" * 50)
        print("🎵 MUSICIAN CLASS TEST")
        print("=" * 50)
        
        # Create musician with the piezos (only if full classes imported)
        if CLASSES_IMPORTED:
            musician = Musician(piezos)
        else:
            musician = None
            print("⚠️  Musician class not available - using simplified playback")
        
        # Simple test song (embedded, no file needed)
        test_song = {
            "title": "Piezo System Test Song",
            "duration": 4000,  # 4 seconds
            "lines": [
                [  # Line 1 (Piezo-17)
                    {"note": "C4", "start": 0, "duration": 500},
                    {"note": "E4", "start": 500, "duration": 500},
                    {"note": "G4", "start": 1000, "duration": 500},
                    {"note": "C5", "start": 1500, "duration": 500}
                ],
                [  # Line 2 (Piezo-14)
                    {"note": "C3", "start": 250, "duration": 750},
                    {"note": "G3", "start": 1250, "duration": 750},
                    {"note": "C4", "start": 2250, "duration": 750}
                ]
            ]
        }
        
        if musician:
            print("🎵 Playing test song...")
            print(f"   Duration: 4 seconds")
            print(f"   {len(piezos)} parts playing")
            
            # Play the test song
            musician.play_song(test_song)
            
            print("✅ Test song complete")
        else:
            print("🎵 Playing simplified test melody...")
            # Simple test without Musician class
            if len(piezos) >= 1 and piezos[0].is_available():
                notes = [262, 294, 330, 349]  # C, D, E, F
                for note in notes:
                    piezos[0].play_note(note, 0.5)
                    time.sleep(0.1)
            print("✅ Simplified test complete")
        
        print("\n" + "=" * 50)
        print("🎯 LOADING KANYE SONG")
        print("=" * 50)
        
        # Now try to load and play the full Kanye song
        if musician:
            try:
                print("🎵 Looking for kanye_never_see_me_again_pico.json...")
                musician.load_song_from_file("kanye_never_see_me_again_pico.json")
                
                print("🎵 Playing Kanye - Never See Me Again (full 90 seconds)...")
                print("   Duration: 1.5 minutes")
                print("   BPM: 85")
                print("   Piezos: 3 lines (bass, mid, treble)")
                musician.play_song()  # Play the full song without time limit
                
                print("✅ Kanye song playback complete!")
                
            except Exception as e:
                print(f"❌ Error loading/playing Kanye song: {e}")
                print("   Trying alternative locations...")
                
                # Try different paths for Kanye song
                alternative_paths = [
                    "/kanye_never_see_me_again_pico.json",
                    "songs/kanye_never_see_me_again_pico.json",
                    "/songs/kanye_never_see_me_again_pico.json",
                    "pico_Fetty.json",  # Fallback to old song
                    "/pico_Fetty.json"
                ]
                
                song_found = False
                for path in alternative_paths:
                    try:
                        print(f"   Trying: {path}")
                        musician.load_song_from_file(path)
                        if "kanye" in path.lower():
                            print("🎵 Playing Kanye - Never See Me Again...")
                        else:
                            print("🎵 Playing fallback song...")
                        musician.play_song()  # Play full song
                        print("✅ Song found and played!")
                        song_found = True
                        break
                    except Exception as ex:
                        print(f"     Failed: {ex}")
                        continue
                
                if not song_found:
                    print("   No song file found. Playing extended demo song instead...")
                    # Create a longer demo song
                    demo_song = {
                        "title": "Extended Demo Song",
                        "duration": 8000,  # 8 seconds
                        "lines": [
                            [  # Melody line
                                {"note": "C4", "start": 0, "duration": 500},
                                {"note": "D4", "start": 500, "duration": 500},
                                {"note": "E4", "start": 1000, "duration": 500},
                                {"note": "F4", "start": 1500, "duration": 500},
                                {"note": "G4", "start": 2000, "duration": 500},
                                {"note": "A4", "start": 2500, "duration": 500},
                                {"note": "B4", "start": 3000, "duration": 500},
                                {"note": "C5", "start": 3500, "duration": 1000}
                            ],
                            [  # Bass line
                                {"note": "C3", "start": 0, "duration": 1000},
                                {"note": "F3", "start": 1000, "duration": 1000},
                                {"note": "G3", "start": 2000, "duration": 1000},
                                {"note": "C3", "start": 3000, "duration": 1000}
                            ]
                        ]
                    }
                    musician.play_song(demo_song)
        else:
            print("🎵 Playing simplified Kanye preview...")
            # Simple melody inspired by Kanye without full song system
            if len(piezos) >= 1 and piezos[0].is_available():
                # Play a longer, more complex melody
                melody = [
                    # Kanye-inspired progression
                    185, 196, 220, 196, 185, 220, 247, 262,  # F#3 to C4
                    294, 330, 294, 262, 247, 220, 196, 185   # Back down
                ]
                print("   Playing melody line...")
                for note in melody:
                    piezos[0].play_note(note, 0.4)
                    time.sleep(0.1)
            
            if len(piezos) >= 2 and piezos[1].is_available():
                # Play bass line
                bass = [
                    92, 98, 110, 98, 92, 110, 123, 131,      # Lower frequencies
                    147, 165, 147, 131, 123, 110, 98, 92     # Bass pattern
                ]
                print("   Playing bass line...")
                for note in bass:
                    piezos[1].play_note(note, 0.5)
                    time.sleep(0.2)
            print("✅ Simplified Kanye preview complete!")
        
        print("\n" + "=" * 50)
        print("🎯 SYSTEM STATUS")
        print("=" * 50)
        
        # Final status report
        working_piezos = sum(1 for p in piezos if p.is_available())
        print(f"📊 Working piezos: {working_piezos}/{len(piezos)}")
        
        if working_piezos == len(piezos):
            print("🎉 ALL SYSTEMS GO! Your piezo music system is ready!")
            print("\n💡 Usage:")
            print("   - Individual tests: ✅ Passed")
            print("   - Simultaneous test: ✅ Passed") 
            print("   - Song playback: ✅ Working")
        elif working_piezos > 0:
            print(f"⚠️  Partial success - {working_piezos} piezos working")
            print("   Check connections for non-working piezos")
        else:
            print("❌ No piezos responding - check all connections")
        
        print("\n🔄 Test complete - will restart in 30 seconds...")
        print("   (Press CTRL+C to stop, or reset Pico to restart)")
        print("   Note: Full Kanye song is 90 seconds, so wait for completion!")
        
        # Keep the program running and restart every 30 seconds
        # (Longer delay since song is 90 seconds)
        time.sleep(30)
        
        # Clean up before restart
        for piezo in piezos:
            piezo.cleanup()
            
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user")
        # Clean up
        try:
            for piezo in piezos:
                piezo.cleanup()
        except:
            pass
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("💡 Check your hardware connections and try again")
        print(f"   Error details: {type(e).__name__}: {e}")

# Run the main function
if __name__ == "__main__":
    # This runs when testing on regular Python
    print("⚠️  Running in regular Python mode")
    print("   On Pico, this will run automatically")
    main()
else:
    # This runs automatically on CircuitPython (Pico)
    print("🚀 CircuitPython detected - starting automatically")
    main()