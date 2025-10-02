#!/usr/bin/env python3
"""
Song Recommendation System for Piezo Music

This script helps you choose and convert songs that work well on piezo buzzers.
"""

# Song database with piezo-friendly characteristics
RECOMMENDED_SONGS = {
    "video_game": {
        "Super Mario Bros Theme": {
            "difficulty": "Easy",
            "bpm": 120,
            "duration_bars": 32,
            "frequency_range": "C4-C6",
            "why_good": "Originally designed for simple sound chips",
            "piezo_rating": 10
        },
        "Tetris Theme": {
            "difficulty": "Medium", 
            "bpm": 144,
            "duration_bars": 64,
            "frequency_range": "G3-G5",
            "why_good": "Clear melody, moderate tempo, very recognizable",
            "piezo_rating": 9
        },
        "Legend of Zelda": {
            "difficulty": "Medium",
            "bpm": 120,
            "duration_bars": 48,
            "frequency_range": "D4-D6",
            "why_good": "Epic melody, great for multiple piezos",
            "piezo_rating": 9
        }
    },
    
    "classical": {
        "Für Elise": {
            "difficulty": "Medium",
            "bpm": 120,
            "duration_bars": 80,
            "frequency_range": "E4-E6",
            "why_good": "Beautiful melody, well-known, good piezo range",
            "piezo_rating": 8
        },
        "Ode to Joy": {
            "difficulty": "Easy",
            "bpm": 100,
            "duration_bars": 32,
            "frequency_range": "G3-G5",
            "why_good": "Simple harmony, powerful melody",
            "piezo_rating": 9
        },
        "Canon in D": {
            "difficulty": "Hard",
            "bpm": 60,
            "duration_bars": 56,
            "frequency_range": "D4-D6",
            "why_good": "Perfect for multiple piezo harmony",
            "piezo_rating": 8
        }
    },
    
    "pop_culture": {
        "Star Wars Main Theme": {
            "difficulty": "Medium",
            "bpm": 108,
            "duration_bars": 64,
            "frequency_range": "G3-C6",
            "why_good": "Iconic, epic, great melody",
            "piezo_rating": 9
        },
        "Imperial March": {
            "difficulty": "Easy",
            "bpm": 108,
            "duration_bars": 32,
            "frequency_range": "G3-G5",
            "why_good": "Dramatic, simple rhythm, recognizable",
            "piezo_rating": 10
        },
        "Pirates of Caribbean": {
            "difficulty": "Medium",
            "bpm": 140,
            "duration_bars": 48,
            "frequency_range": "A3-A5",
            "why_good": "Adventurous, good energy for piezos",
            "piezo_rating": 8
        }
    },
    
    "simple_classics": {
        "Happy Birthday": {
            "difficulty": "Easy",
            "bpm": 120,
            "duration_bars": 16,
            "frequency_range": "C4-C5",
            "why_good": "Everyone knows it, super simple",
            "piezo_rating": 10
        },
        "Twinkle Twinkle": {
            "difficulty": "Easy",
            "bpm": 120,
            "duration_bars": 8,
            "frequency_range": "C4-C5",
            "why_good": "Perfect for testing, very simple",
            "piezo_rating": 9
        },
        "Mary Had a Little Lamb": {
            "difficulty": "Easy",
            "bpm": 120,
            "duration_bars": 8,
            "frequency_range": "E4-G4",
            "why_good": "Minimal notes, great for beginners",
            "piezo_rating": 8
        }
    }
}

def calculate_song_duration(bpm, bars):
    """Calculate song duration in seconds."""
    beats = bars * 4  # Assuming 4/4 time
    minutes = beats / bpm
    return minutes * 60

def print_song_recommendations():
    """Print all song recommendations organized by category."""
    
    print("🎵 PIEZO BUZZER SONG RECOMMENDATIONS")
    print("=" * 60)
    
    for category, songs in RECOMMENDED_SONGS.items():
        print(f"\n🎯 {category.upper().replace('_', ' ')} SONGS:")
        print("-" * 40)
        
        # Sort by piezo rating (best first)
        sorted_songs = sorted(songs.items(), key=lambda x: x[1]['piezo_rating'], reverse=True)
        
        for song_name, info in sorted_songs:
            duration = calculate_song_duration(info['bpm'], info['duration_bars'])
            
            print(f"\n🎵 {song_name}")
            print(f"   ⭐ Piezo Rating: {info['piezo_rating']}/10")
            print(f"   📊 Difficulty: {info['difficulty']}")
            print(f"   🥁 BPM: {info['bpm']}")
            print(f"   ⏱️  Duration: {duration:.1f}s ({info['duration_bars']} bars)")
            print(f"   🎼 Range: {info['frequency_range']}")
            print(f"   💡 Why Good: {info['why_good']}")

def get_songs_by_difficulty(difficulty):
    """Get songs filtered by difficulty level."""
    result = []
    for category, songs in RECOMMENDED_SONGS.items():
        for song_name, info in songs.items():
            if info['difficulty'].lower() == difficulty.lower():
                result.append((song_name, info, category))
    
    return sorted(result, key=lambda x: x[1]['piezo_rating'], reverse=True)

def get_songs_by_duration(max_duration_seconds):
    """Get songs that are shorter than max_duration."""
    result = []
    for category, songs in RECOMMENDED_SONGS.items():
        for song_name, info in songs.items():
            duration = calculate_song_duration(info['bpm'], info['duration_bars'])
            if duration <= max_duration_seconds:
                result.append((song_name, info, category, duration))
    
    return sorted(result, key=lambda x: x[1]['piezo_rating'], reverse=True)

def recommend_for_beginners():
    """Recommend best songs for beginners."""
    print("🎯 BEST SONGS FOR BEGINNERS:")
    print("=" * 40)
    
    beginner_songs = get_songs_by_difficulty("Easy")
    
    for song_name, info, category in beginner_songs[:5]:  # Top 5
        duration = calculate_song_duration(info['bpm'], info['duration_bars'])
        print(f"\n✅ {song_name}")
        print(f"   Category: {category.replace('_', ' ').title()}")
        print(f"   Duration: {duration:.1f}s")
        print(f"   Why: {info['why_good']}")

def recommend_quick_songs():
    """Recommend songs under 30 seconds for quick testing."""
    print("⚡ QUICK SONGS (Under 30s):")
    print("=" * 30)
    
    quick_songs = get_songs_by_duration(30)
    
    for song_name, info, category, duration in quick_songs:
        print(f"🎵 {song_name}: {duration:.1f}s (Rating: {info['piezo_rating']}/10)")

if __name__ == "__main__":
    print_song_recommendations()
    
    print("\n" + "=" * 60)
    recommend_for_beginners()
    
    print("\n" + "=" * 60)
    recommend_quick_songs()
    
    print("\n🎵 CONVERSION TIPS:")
    print("=" * 20)
    print("✅ Use simple melodies (avoid complex chords)")
    print("✅ Stay in C4-C6 range for best piezo sound")
    print("✅ Keep note durations 200-2000ms")
    print("✅ Use 2-3 piezos max for harmony")
    print("✅ Test with short songs first")
    print("✅ Video game music works great!")
    
    print("\n🔧 TO CONVERT YOUR OWN SONGS:")
    print("1. Find MIDI file of the song")
    print("2. Use process_midi.py to convert")
    print("3. Fix timing with correct_timing.py")
    print("4. Test on your piezos!")
    
    print("\n🎤 Happy music making! 🎵")