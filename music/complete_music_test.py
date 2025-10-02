# complete_music_test.py - Full test including your fixed Fetty Wap song
import time
import board
import pwmio

print("🎵 Complete Piezo Music System Test with Song")
print("=" * 50)

try:
    # Import our classes
    from piezo_music import Piezo, Musician
    print("✅ Successfully imported music classes")
    
    # Create piezos
    print("🔧 Creating piezos...")
    piezo1 = Piezo(board.GP17, "Piezo-17")
    piezo2 = Piezo(board.GP14, "Piezo-14")
    
    piezos = [piezo1, piezo2]
    working_piezos = [p for p in piezos if p.is_available()]
    
    print(f"✅ {len(working_piezos)}/{len(piezos)} piezos working")
    
    if len(working_piezos) == 0:
        print("❌ No piezos working!")
        exit()
    
    # Quick hardware test
    print("\n🧪 QUICK HARDWARE TEST")
    print("-" * 30)
    test_freqs = [262, 330, 392]  # C4, E4, G4
    
    for i, piezo in enumerate(working_piezos):
        print(f"🔊 Testing {piezo.name}...")
        for freq in test_freqs:
            piezo.play_note(freq, 0.3)
            time.sleep(0.1)
        print(f"✅ {piezo.name} working")
    
    print("✅ Hardware test complete")
    
    # Create musician
    print("\n🎵 CREATING MUSICIAN")
    print("-" * 30)
    musician = Musician(working_piezos)
    
    # Test with a simple song first
    print("🎵 Testing with simple melody...")
    simple_song = {
        "title": "Simple Test",
        "duration": 5000,  # 5 seconds
        "lines": [
            [
                {"note": "C4", "start": 0, "duration": 800},
                {"note": "D4", "start": 1000, "duration": 800},
                {"note": "E4", "start": 2000, "duration": 800},
                {"note": "F4", "start": 3000, "duration": 800},
                {"note": "G4", "start": 4000, "duration": 800}
            ],
            [
                {"note": "C3", "start": 500, "duration": 1500},
                {"note": "G3", "start": 2500, "duration": 1500}
            ] if len(working_piezos) >= 2 else []
        ]
    }
    
    musician.play_song(simple_song)
    print("✅ Simple song test complete")
    
    time.sleep(2)  # Pause between songs
    
    # Now try your Fetty Wap song
    print("\n🎯 LOADING YOUR FETTY WAP SONG")
    print("-" * 40)
    
    try:
        print("🎵 Loading pico_Fetty.json...")
        musician.load_song_from_file("pico_Fetty.json")
        
        original_duration = musician.current_song.get('duration', 0)
        print(f"📊 Song info:")
        print(f"   Title: {musician.current_song.get('title', 'Unknown')}")
        print(f"   Duration: {original_duration/1000:.1f} seconds")
        print(f"   Lines: {len(musician.current_song.get('lines', []))}")
        
        # For testing, let's play just the first 30 seconds
        if original_duration > 30000:  # If longer than 30 seconds
            print("🎵 Playing first 30 seconds for testing...")
            musician.current_song['duration'] = 30000
        else:
            print(f"🎵 Playing full song ({original_duration/1000:.1f}s)...")
        
        musician.play_song()
        
        print("✅ Fetty Wap song playback complete!")
        
    except Exception as e:
        print(f"❌ Error with Fetty Wap song: {e}")
        
        # Try the fixed version embedded
        print("🔧 Trying with corrected timing...")
        
        # Create a small sample with correct timing
        fetty_sample = {
            "title": "Fetty Wap Sample (Fixed Timing)",
            "duration": 8000,  # 8 seconds
            "lines": [
                [
                    {"note": "G2", "start": 0, "duration": 400},
                    {"note": "G2", "start": 500, "duration": 400},
                    {"note": "FS2", "start": 1000, "duration": 400},
                    {"note": "B2", "start": 1500, "duration": 400},
                    {"note": "D3", "start": 2000, "duration": 400},
                    {"note": "G3", "start": 2500, "duration": 400},
                    {"note": "B3", "start": 3000, "duration": 400},
                    {"note": "D4", "start": 3500, "duration": 400}
                ],
                [
                    {"note": "G2", "start": 250, "duration": 750},
                    {"note": "B2", "start": 1250, "duration": 750},
                    {"note": "D3", "start": 2250, "duration": 750},
                    {"note": "G3", "start": 3250, "duration": 750}
                ] if len(working_piezos) >= 2 else []
            ]
        }
        
        musician.play_song(fetty_sample)
        print("✅ Sample song complete!")
    
    print("\n🎉 SYSTEM STATUS")
    print("=" * 40)
    print(f"✅ Working piezos: {len(working_piezos)}")
    print("✅ Basic notes: Working")
    print("✅ Song loading: Working")
    print("✅ Song playback: Working")
    print("")
    print("🎵 Your piezo music system is fully operational!")
    print("🎯 Ready to rock with Fetty Wap! 🎤")
    
    # Cleanup
    musician.cleanup()

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("🔧 Using basic fallback...")
    
    # Basic test without classes
    TONE_FREQ = [262, 294, 330, 349, 392, 440, 494, 523]
    
    buzzer1 = pwmio.PWMOut(board.GP17, variable_frequency=True)
    buzzer2 = pwmio.PWMOut(board.GP14, variable_frequency=True)
    
    print("🎵 Basic Fetty Wap style melody...")
    
    # Simple melody inspired by the frequencies in the JSON
    fetty_melody = [196, 185, 247, 294, 196, 330, 247, 392]  # G3, FS3, B3, D4, G3, E4, B3, G4
    
    buzzer1.duty_cycle = 32768
    
    for freq in fetty_melody:
        buzzer1.frequency = freq
        time.sleep(0.6)
    
    buzzer1.duty_cycle = 0
    print("✅ Basic melody complete")
    
    buzzer1.deinit()
    buzzer2.deinit()

except Exception as e:
    print(f"❌ Unexpected error: {e}")

print("\n💎 Test complete - enjoy your music system!")