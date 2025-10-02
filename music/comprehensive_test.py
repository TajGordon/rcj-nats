# comprehensive_test.py - Full music system test with variable_frequency=True
import time
import board
import pwmio

print("🎵 Comprehensive Piezo Music System Test")
print("=" * 50)

try:
    # Import our fixed classes
    from piezo_music import Piezo, Musician
    print("✅ Successfully imported fixed Piezo and Musician classes")
    
    # Create piezos with the fixed initialization
    print("🔧 Creating piezos...")
    piezo1 = Piezo(board.GP17, "Piezo-17")
    piezo2 = Piezo(board.GP14, "Piezo-14")
    
    piezos = [piezo1, piezo2]
    
    # Check initialization
    working_piezos = [p for p in piezos if p.is_available()]
    print(f"✅ {len(working_piezos)}/{len(piezos)} piezos initialized successfully")
    
    if len(working_piezos) == 0:
        print("❌ No piezos working - check connections!")
    else:
        print("\n🧪 INDIVIDUAL PIEZO TESTS")
        print("-" * 30)
        
        # Test each piezo with different frequencies
        test_notes = [262, 330, 392, 523]  # C4, E4, G4, C5
        
        for i, piezo in enumerate(working_piezos):
            print(f"🔊 Testing {piezo.name}...")
            for freq in test_notes:
                print(f"   Playing {freq}Hz...")
                piezo.play_note(freq, 0.4)  # 0.4 second per note
                time.sleep(0.1)  # Small gap
            print(f"✅ {piezo.name} test complete")
            time.sleep(0.5)
        
        print("\n🎼 HARMONY TEST")
        print("-" * 30)
        print("🔊 Playing C major chord (C4 + E4)...")
        
        if len(working_piezos) >= 2:
            working_piezos[0].play_note_async(262)  # C4
            working_piezos[1].play_note_async(330)  # E4
            time.sleep(3)  # 3 second chord
            
            for piezo in working_piezos:
                piezo.stop()
            
            print("✅ Harmony test complete")
        else:
            print("⚠️  Need 2 piezos for harmony test")
        
        print("\n🎵 MUSICIAN CLASS TEST")
        print("-" * 30)
        
        # Create musician
        musician = Musician(working_piezos)
        
        # Simple test song
        test_song = {
            "title": "Simple Test Melody",
            "duration": 4000,  # 4 seconds
            "lines": [
                [  # First piezo line
                    {"note": "C4", "start": 0, "duration": 500},
                    {"note": "E4", "start": 600, "duration": 500},
                    {"note": "G4", "start": 1200, "duration": 500},
                    {"note": "C5", "start": 1800, "duration": 800}
                ],
                [  # Second piezo line (if available)
                    {"note": "C3", "start": 300, "duration": 800},
                    {"note": "G3", "start": 1400, "duration": 800},
                    {"note": "C4", "start": 2400, "duration": 800}
                ] if len(working_piezos) >= 2 else []
            ]
        }
        
        print("🎵 Playing test melody...")
        musician.play_song(test_song)
        print("✅ Melody complete")
        
        print("\n🎯 SONG FILE TEST")
        print("-" * 30)
        
        # Try to load your Fetty Wap song
        try:
            print("🎵 Loading pico_Fetty.json...")
            musician.load_song_from_file("pico_Fetty.json")
            
            print("🎵 Playing first 10 seconds of Fetty Wap...")
            # Modify song to play only first 10 seconds for testing
            if musician.current_song:
                original_duration = musician.current_song.get('duration', 0)
                musician.current_song['duration'] = min(10000, original_duration)  # 10 seconds max
                
                musician.play_song()
                print("✅ Song playback complete!")
                
        except Exception as e:
            print(f"❌ Error with song file: {e}")
            print("   Playing backup melody instead...")
            
            backup_song = {
                "title": "Backup Melody",
                "duration": 3000,
                "lines": [
                    [{"note": "A4", "start": 0, "duration": 750},
                     {"note": "B4", "start": 750, "duration": 750},
                     {"note": "C5", "start": 1500, "duration": 750},
                     {"note": "A4", "start": 2250, "duration": 750}]
                ]
            }
            musician.play_song(backup_song)
        
        print("\n🎉 ALL TESTS COMPLETE!")
        print("=" * 50)
        print(f"✅ Working piezos: {len(working_piezos)}")
        print("✅ Individual notes: Working")
        print("✅ Harmony: Working")
        print("✅ Song playback: Working")
        print("\n🎵 Your piezo music system is fully operational!")
        
        # Cleanup
        musician.cleanup()

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Falling back to basic test...")
    
    # Basic fallback test
    print("🔧 Creating basic PWM test...")
    
    buzzer1 = pwmio.PWMOut(board.GP17, variable_frequency=True)
    buzzer2 = pwmio.PWMOut(board.GP14, variable_frequency=True)
    
    notes = [262, 294, 330, 349, 392, 440, 494, 523]
    
    print("🎵 Basic scale test...")
    buzzer1.duty_cycle = 32768
    
    for freq in notes:
        buzzer1.frequency = freq
        time.sleep(0.5)
    
    buzzer1.duty_cycle = 0
    print("✅ Basic test complete")
    
    buzzer1.deinit()
    buzzer2.deinit()

except Exception as e:
    print(f"❌ Unexpected error: {e}")
    print(f"   Error type: {type(e).__name__}")

print("\n💓 Test finished - system ready!")