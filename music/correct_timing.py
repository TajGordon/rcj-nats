#!/usr/bin/env python3
"""
Correct MIDI Timing Calculator

Fix timing based on actual BPM and bar count.
"""

import json
import math

def calculate_correct_duration(bpm, bars, beats_per_bar=4):
    """
    Calculate correct song duration based on musical parameters.
    
    Args:
        bpm: Beats per minute
        bars: Number of bars/measures
        beats_per_bar: Beats per bar (default 4 for 4/4 time)
    
    Returns:
        Duration in milliseconds
    """
    total_beats = bars * beats_per_bar
    duration_minutes = total_beats / bpm
    duration_seconds = duration_minutes * 60
    duration_ms = int(duration_seconds * 1000)
    
    print(f"🎵 Music Math:")
    print(f"   BPM: {bpm}")
    print(f"   Bars: {bars}")
    print(f"   Beats per bar: {beats_per_bar}")
    print(f"   Total beats: {total_beats}")
    print(f"   Duration: {duration_seconds:.1f} seconds = {duration_ms}ms")
    
    return duration_ms

def fix_fetty_timing(input_file, output_file, target_bpm=94, target_bars=22.5):
    """
    Fix the Fetty Wap song timing based on correct musical parameters.
    """
    try:
        with open(input_file, 'r') as f:
            song_data = json.load(f)
        
        print(f"Original song data:")
        original_duration = song_data.get('duration', 0)
        print(f"   Duration: {original_duration}ms ({original_duration/1000:.1f}s)")
        
        # Calculate correct duration
        correct_duration = calculate_correct_duration(target_bpm, target_bars)
        
        # Calculate scaling factor
        if original_duration > 0:
            scale_factor = correct_duration / original_duration
            print(f"   Scale factor: {scale_factor:.3f}")
        else:
            print("❌ Original duration is 0!")
            return None
        
        # Apply scaling
        song_data['duration'] = correct_duration
        
        # Scale all note timings
        if 'lines' in song_data:
            for line_idx, line in enumerate(song_data['lines']):
                print(f"Scaling line {line_idx + 1} ({len(line)} notes)...")
                
                for note in line:
                    if 'start' in note:
                        note['start'] = int(note['start'] * scale_factor)
                    if 'duration' in note:
                        # Note durations might need different scaling
                        # Keep them reasonable (not too long)
                        original_note_duration = note['duration']
                        scaled_duration = int(original_note_duration * scale_factor)
                        
                        # Cap note duration at 2 seconds max
                        max_note_duration = 2000  # 2 seconds
                        note['duration'] = min(scaled_duration, max_note_duration)
        
        # Save corrected version
        with open(output_file, 'w') as f:
            json.dump(song_data, f, indent=2)
        
        print(f"✅ Corrected timing saved to: {output_file}")
        print(f"   New duration: {correct_duration/1000:.1f} seconds")
        
        return song_data
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def analyze_current_timing(json_file):
    """Analyze current timing and suggest corrections."""
    try:
        with open(json_file, 'r') as f:
            song_data = json.load(f)
        
        duration = song_data.get('duration', 0)
        
        print(f"📊 Current Analysis:")
        print(f"   Duration: {duration}ms ({duration/1000:.1f}s)")
        
        # Calculate implied BPM if this were 22.5 bars
        if duration > 0:
            bars = 22.5
            beats = bars * 4  # 4/4 time
            duration_minutes = duration / 60000
            implied_bpm = beats / duration_minutes
            print(f"   Implied BPM (if 22.5 bars): {implied_bpm:.1f}")
        
        # Check against expected values
        expected_duration = calculate_correct_duration(94, 22.5)
        if duration > 0:
            ratio = duration / expected_duration
            print(f"   Current vs Expected ratio: {ratio:.2f}")
            
            if ratio > 2:
                print("🎯 Song is too slow - timing needs to be scaled down")
                suggested_factor = 1 / ratio
                print(f"   Suggested scale factor: {suggested_factor:.3f}")
            elif ratio < 0.5:
                print("🎯 Song is too fast - timing needs to be scaled up")
                suggested_factor = 1 / ratio
                print(f"   Suggested scale factor: {suggested_factor:.3f}")
            else:
                print("✅ Timing looks reasonable")
        
    except Exception as e:
        print(f"❌ Error analyzing: {e}")

if __name__ == "__main__":
    # Analyze the current pico_Fetty.json
    print("🎵 Analyzing Fetty Wap Timing")
    print("=" * 40)
    
    # First check the original file
    print("\n📊 ORIGINAL FILE ANALYSIS:")
    analyze_current_timing("music/pico_Fetty.json")
    
    # Check the "fixed" file too
    try:
        print("\n📊 'FIXED' FILE ANALYSIS:")
        analyze_current_timing("music/pico_Fetty_fixed.json")
    except:
        print("Fixed file not found")
    
    # Calculate what it should be
    print("\n🎯 CORRECT TIMING CALCULATION:")
    correct_duration = calculate_correct_duration(94, 22.5)
    
    print("\n🔧 Creating properly timed version...")
    # Fix based on the original (smaller numbers)
    result = fix_fetty_timing("music/pico_Fetty.json", "music/pico_Fetty_correct.json", 94, 22.5)