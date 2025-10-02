#!/usr/bin/env python3
"""
Fix timing for compressed MIDI files that have all notes in first few milliseconds.
This script stretches the timing to a reasonable musical duration.
"""

import json
import sys
import argparse

def fix_compressed_timing(input_file, output_file, target_duration_seconds=60, target_bpm=85):
    """
    Fix timing for MIDI files where all notes are compressed into first few milliseconds.
    
    Args:
        input_file: Path to JSON file with compressed timing
        output_file: Path to save fixed JSON file
        target_duration_seconds: How long the song should be
        target_bpm: Target BPM for the song
    """
    
    print(f"🔧 Fixing compressed timing in: {input_file}")
    print(f"📊 Target duration: {target_duration_seconds}s at {target_bpm} BPM")
    
    # Load the compressed song
    with open(input_file, 'r') as f:
        song = json.load(f)
    
    print(f"📝 Original duration: {song['duration']}ms")
    print(f"📝 Lines: {len(song['lines'])}")
    
    # Find the actual time span of notes
    all_notes = []
    for line_idx, line in enumerate(song['lines']):
        for note in line:
            all_notes.append({
                'line': line_idx,
                'note': note['note'],
                'start': note['start'],
                'duration': note['duration'],
                'end': note['start'] + note['duration']
            })
    
    if not all_notes:
        print("❌ No notes found!")
        return
    
    # Find original time span
    original_start = min(note['start'] for note in all_notes)
    original_end = max(note['end'] for note in all_notes)
    original_span = original_end - original_start
    
    print(f"📊 Original time span: {original_start}ms to {original_end}ms ({original_span}ms total)")
    
    # Calculate stretch factor
    target_duration_ms = target_duration_seconds * 1000
    stretch_factor = target_duration_ms / original_span if original_span > 0 else 1
    
    print(f"🔢 Stretch factor: {stretch_factor:.2f}x")
    
    # Calculate note durations based on BPM
    # At 85 BPM, quarter note = 60/85 = 0.706 seconds = 706ms
    quarter_note_ms = (60 / target_bpm) * 1000
    eighth_note_ms = quarter_note_ms / 2
    sixteenth_note_ms = quarter_note_ms / 4
    
    print(f"🎵 Note durations: Quarter={quarter_note_ms:.0f}ms, Eighth={eighth_note_ms:.0f}ms, Sixteenth={sixteenth_note_ms:.0f}ms")
    
    # Apply timing fix to each line
    fixed_lines = []
    for line_idx, line in enumerate(song['lines']):
        fixed_line = []
        
        for note in line:
            # Stretch the timing
            new_start = int((note['start'] - original_start) * stretch_factor)
            
            # Set reasonable note duration (use eighth notes for most notes)
            new_duration = int(eighth_note_ms)
            
            # Don't let notes go negative
            new_start = max(0, new_start)
            
            fixed_note = {
                'note': note['note'],
                'start': new_start,
                'duration': new_duration
            }
            
            fixed_line.append(fixed_note)
        
        # Sort notes by start time
        fixed_line.sort(key=lambda x: x['start'])
        fixed_lines.append(fixed_line)
        
        print(f"📝 Line {line_idx}: {len(fixed_line)} notes, span {fixed_line[0]['start']}ms to {fixed_line[-1]['start']}ms")
    
    # Create fixed song
    fixed_song = {
        'title': song['title'] + ' (Timing Fixed)',
        'duration': target_duration_ms,
        'lines': fixed_lines
    }
    
    # Save fixed song
    with open(output_file, 'w') as f:
        json.dump(fixed_song, f, indent=2)
    
    print(f"✅ Fixed song saved to: {output_file}")
    print(f"📊 New duration: {target_duration_ms}ms ({target_duration_seconds}s)")
    
    # Show first few notes as example
    print(f"\n🎵 Example notes from Line 0:")
    for i, note in enumerate(fixed_lines[0][:5]):
        print(f"   {i+1}. {note['note']} at {note['start']}ms for {note['duration']}ms")
    
    return fixed_song

def main():
    parser = argparse.ArgumentParser(description='Fix compressed MIDI timing')
    parser.add_argument('input_file', help='Input JSON file with compressed timing')
    parser.add_argument('--output', '-o', help='Output JSON file', required=True)
    parser.add_argument('--duration', '-d', type=int, default=60, help='Target duration in seconds (default: 60)')
    parser.add_argument('--bpm', '-b', type=int, default=85, help='Target BPM (default: 85)')
    
    args = parser.parse_args()
    
    fix_compressed_timing(args.input_file, args.output, args.duration, args.bpm)

if __name__ == '__main__':
    main()