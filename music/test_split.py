#!/usr/bin/env python3
"""
Test script to debug the channel splitting issue
"""

from process_midi import MidiProcessor

# Create a simple test case
processor = MidiProcessor()

# Sample notes data that should be split
test_notes = [
    {'note': 'C4', 'start': 0, 'duration': 1000},
    {'note': 'E4', 'start': 0, 'duration': 1000},  # Overlaps with C4
    {'note': 'G4', 'start': 500, 'duration': 1000},  # Overlaps with E4
    {'note': 'C5', 'start': 1000, 'duration': 1000},
    {'note': 'E5', 'start': 1000, 'duration': 1000},  # Overlaps with C5
]

print("🧪 Testing channel splitting with sample data:")
print(f"Input: {len(test_notes)} notes")
for note in test_notes:
    print(f"  {note}")

print(f"\n🎯 Splitting into 3 tracks:")
result = processor.split_polyphonic_channel(test_notes, 3, 'pitch_priority')

print(f"\n📊 Result: {len(result)} tracks")
for i, track in enumerate(result):
    print(f"Track {i+1}: {len(track)} notes")
    for note in track:
        print(f"  {note}")