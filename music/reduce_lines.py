#!/usr/bin/env python3
"""
Reduce the number of lines in a song to match available piezos.
"""

import json
import sys

def reduce_lines(input_file, output_file, max_lines=3):
    """
    Reduce song to max_lines by combining similar pitch ranges.
    """
    
    print(f"🔧 Reducing lines in: {input_file}")
    print(f"📊 Target lines: {max_lines}")
    
    # Load the song
    with open(input_file, 'r') as f:
        song = json.load(f)
    
    print(f"📝 Original lines: {len(song['lines'])}")
    
    if len(song['lines']) <= max_lines:
        print(f"✅ Song already has {len(song['lines'])} lines, no reduction needed!")
        return
    
    # Analyze pitch ranges for each line
    line_stats = []
    for i, line in enumerate(song['lines']):
        if not line:
            continue
            
        # Convert notes to MIDI numbers for analysis
        midi_nums = []
        for note in line:
            note_name = note['note']
            # Simple conversion (approximate)
            if 'C' in note_name:
                base = 0
            elif 'CS' in note_name or 'DF' in note_name:
                base = 1
            elif 'D' in note_name:
                base = 2
            elif 'DS' in note_name or 'EF' in note_name:
                base = 3
            elif 'E' in note_name:
                base = 4
            elif 'F' in note_name:
                base = 5
            elif 'FS' in note_name or 'GF' in note_name:
                base = 6
            elif 'G' in note_name:
                base = 7
            elif 'GS' in note_name or 'AF' in note_name:
                base = 8
            elif 'A' in note_name:
                base = 9
            elif 'AS' in note_name or 'BF' in note_name:
                base = 10
            elif 'B' in note_name:
                base = 11
            else:
                base = 0
            
            # Extract octave
            octave = int(''.join(filter(str.isdigit, note_name))) if any(c.isdigit() for c in note_name) else 4
            midi_num = base + (octave * 12)
            midi_nums.append(midi_num)
        
        if midi_nums:
            avg_pitch = sum(midi_nums) / len(midi_nums)
            min_pitch = min(midi_nums)
            max_pitch = max(midi_nums)
            
            line_stats.append({
                'index': i,
                'note_count': len(line),
                'avg_pitch': avg_pitch,
                'min_pitch': min_pitch,
                'max_pitch': max_pitch,
                'pitch_range': max_pitch - min_pitch,
                'notes': line
            })
            
            print(f"📊 Line {i}: {len(line)} notes, avg pitch {avg_pitch:.1f}, range {min_pitch}-{max_pitch}")
    
    # Group lines by pitch range (bass, mid, treble)
    line_stats.sort(key=lambda x: x['avg_pitch'])
    
    # Create groups
    if max_lines == 2:
        # Bass and treble
        mid_point = len(line_stats) // 2
        groups = [
            line_stats[:mid_point],  # Lower half (bass)
            line_stats[mid_point:]   # Upper half (treble)
        ]
    elif max_lines == 3:
        # Bass, mid, treble
        third = len(line_stats) // 3
        groups = [
            line_stats[:third],                    # Low third (bass)
            line_stats[third:third*2],            # Middle third
            line_stats[third*2:]                  # High third (treble)
        ]
    else:
        # Just take the lines with most notes
        line_stats.sort(key=lambda x: x['note_count'], reverse=True)
        groups = [[stat] for stat in line_stats[:max_lines]]
    
    # Combine lines in each group
    combined_lines = []
    for group_idx, group in enumerate(groups):
        if not group:
            continue
            
        print(f"\n🎵 Group {group_idx + 1}: Combining {len(group)} lines")
        for stat in group:
            print(f"   Line {stat['index']}: {stat['note_count']} notes, avg pitch {stat['avg_pitch']:.1f}")
        
        # Combine all notes from this group
        combined_notes = []
        for stat in group:
            combined_notes.extend(stat['notes'])
        
        # Sort by start time and remove overlaps
        combined_notes.sort(key=lambda x: x['start'])
        
        # Remove notes that are too close together (< 100ms apart)
        filtered_notes = []
        last_start = -1000
        for note in combined_notes:
            if note['start'] - last_start >= 100:  # At least 100ms gap
                filtered_notes.append(note)
                last_start = note['start']
        
        combined_lines.append(filtered_notes)
        print(f"   Result: {len(filtered_notes)} notes after combining and filtering")
    
    # Create reduced song
    reduced_song = {
        'title': song['title'] + f' ({max_lines} Piezos)',
        'duration': song['duration'],
        'lines': combined_lines
    }
    
    # Save reduced song
    with open(output_file, 'w') as f:
        json.dump(reduced_song, f, indent=2)
    
    print(f"\n✅ Reduced song saved to: {output_file}")
    print(f"📊 Lines: {len(song['lines'])} → {len(combined_lines)}")
    
    for i, line in enumerate(combined_lines):
        print(f"📝 Piezo {i+1}: {len(line)} notes")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python reduce_lines.py input.json output.json [max_lines]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    max_lines = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    
    reduce_lines(input_file, output_file, max_lines)