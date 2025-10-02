#!/usr/bin/env python3
"""
Fixed MIDI Timing Processor

This script fixes the timing issues in MIDI to JSON conversion.
The issue is likely that the MIDI timing is being processed incorrectly.
"""

import json
import argparse

def fix_timing_in_json(input_file, output_file, time_multiplier=1000):
    """
    Fix timing in an existing JSON file by multiplying all time values.
    
    Args:
        input_file: Path to JSON file with wrong timing
        output_file: Path to save corrected JSON file  
        time_multiplier: Factor to multiply times by (default 1000)
    """
    try:
        with open(input_file, 'r') as f:
            song_data = json.load(f)
        
        print(f"Original duration: {song_data.get('duration', 0)}ms")
        
        # Fix the main duration
        if 'duration' in song_data:
            song_data['duration'] = int(song_data['duration'] * time_multiplier)
        
        # Fix all note timings
        if 'lines' in song_data:
            for line_idx, line in enumerate(song_data['lines']):
                print(f"Fixing line {line_idx + 1} ({len(line)} notes)...")
                
                for note in line:
                    if 'start' in note:
                        note['start'] = int(note['start'] * time_multiplier)
                    if 'duration' in note:
                        note['duration'] = int(note['duration'] * time_multiplier)
        
        print(f"Fixed duration: {song_data.get('duration', 0)}ms ({song_data.get('duration', 0)/1000:.1f}s)")
        
        # Save the fixed version
        with open(output_file, 'w') as f:
            json.dump(song_data, f, indent=2)
        
        print(f"✅ Fixed timing saved to: {output_file}")
        
        return song_data
        
    except Exception as e:
        print(f"❌ Error fixing timing: {e}")
        return None

def analyze_timing_pattern(json_file):
    """Analyze the timing pattern to suggest appropriate multiplier."""
    try:
        with open(json_file, 'r') as f:
            song_data = json.load(f)
        
        total_duration = song_data.get('duration', 0)
        
        # Collect all timestamps
        all_times = []
        if 'lines' in song_data:
            for line in song_data['lines']:
                for note in line:
                    if 'start' in note:
                        all_times.append(note['start'])
        
        if all_times:
            max_time = max(all_times)
            min_time = min(all_times)
            avg_gap = (max_time - min_time) / len(all_times) if len(all_times) > 1 else 0
            
            print(f"Timing Analysis:")
            print(f"  Total duration: {total_duration}")
            print(f"  Time range: {min_time} to {max_time}")
            print(f"  Average gap: {avg_gap:.2f}")
            print(f"  Total notes: {len(all_times)}")
            
            # Suggest multiplier based on analysis
            if total_duration < 1000:  # Less than 1 second
                if total_duration < 200:
                    suggested_multiplier = 1000  # Convert seconds to milliseconds
                    print(f"🎯 Suggested multiplier: {suggested_multiplier} (seems to be in seconds)")
                else:
                    suggested_multiplier = 500
                    print(f"🎯 Suggested multiplier: {suggested_multiplier} (timing too fast)")
            else:
                suggested_multiplier = 1
                print(f"🎯 Timing seems okay, no multiplier needed")
            
            return suggested_multiplier
        
    except Exception as e:
        print(f"❌ Error analyzing: {e}")
        return 1000

def main():
    parser = argparse.ArgumentParser(description='Fix MIDI timing in JSON files')
    parser.add_argument('input', help='Input JSON file with wrong timing')
    parser.add_argument('--output', '-o', help='Output JSON file (default: input_fixed.json)')
    parser.add_argument('--multiplier', '-m', type=float, default=None, 
                       help='Time multiplier (default: auto-detect)')
    parser.add_argument('--analyze', '-a', action='store_true',
                       help='Just analyze timing, don\'t fix')
    
    args = parser.parse_args()
    
    # Determine output filename
    if args.output:
        output_file = args.output
    else:
        input_path = args.input
        if input_path.endswith('.json'):
            output_file = input_path[:-5] + '_fixed.json'
        else:
            output_file = input_path + '_fixed.json'
    
    if args.analyze:
        # Just analyze
        suggested = analyze_timing_pattern(args.input)
        print(f"\nTo fix: python fix_timing.py {args.input} --multiplier {suggested}")
    else:
        # Fix the timing
        if args.multiplier is None:
            multiplier = analyze_timing_pattern(args.input)
        else:
            multiplier = args.multiplier
        
        print(f"\nApplying multiplier: {multiplier}")
        fixed_data = fix_timing_in_json(args.input, output_file, multiplier)
        
        if fixed_data:
            print(f"\n✅ Success! Fixed file ready: {output_file}")
            print(f"   Duration: {fixed_data.get('duration', 0)/1000:.1f} seconds")

if __name__ == "__main__":
    main()