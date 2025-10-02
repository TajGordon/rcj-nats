#!/usr/bin/env python3
"""
MIDI to JSON Converter for Piezo Music Player

This script converts MIDI files into JSON format compatible with the Musician class.
Supports multiple approaches:
1. Single MIDI file with multiple channels -> multiple piezo lines
2. Multiple MIDI files -> combine into single JSON with multiple lines
3. Track-based separation within a single MIDI file

Usage:
    python process_midi.py song.mid --output songs/song.json
    python process_midi.py melody.mid bass.mid harmony.mid --output songs/song.json
    python process_midi.py song.mid --channels 0,1,2 --output songs/song.json
"""

import argparse
import json
import os
from pathlib import Path

try:
    import mido
except ImportError:
    print("Error: mido library not installed. Install with: pip install mido")
    exit(1)

try:
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("matplotlib not available - visual previews disabled")

try:
    import pretty_midi
    PRETTY_MIDI_AVAILABLE = True
except ImportError:
    PRETTY_MIDI_AVAILABLE = False
    print("pretty_midi not available - enhanced analysis disabled")


# Note number to note name mapping (MIDI note numbers)
MIDI_NOTE_NAMES = {
    0: 'C-1', 1: 'CS-1', 2: 'D-1', 3: 'DS-1', 4: 'E-1', 5: 'F-1',
    6: 'FS-1', 7: 'G-1', 8: 'GS-1', 9: 'A-1', 10: 'AS-1', 11: 'B-1',
    12: 'C0', 13: 'CS0', 14: 'D0', 15: 'DS0', 16: 'E0', 17: 'F0',
    18: 'FS0', 19: 'G0', 20: 'GS0', 21: 'A0', 22: 'AS0', 23: 'B0',
    24: 'C1', 25: 'CS1', 26: 'D1', 27: 'DS1', 28: 'E1', 29: 'F1',
    30: 'FS1', 31: 'G1', 32: 'GS1', 33: 'A1', 34: 'AS1', 35: 'B1',
    36: 'C2', 37: 'CS2', 38: 'D2', 39: 'DS2', 40: 'E2', 41: 'F2',
    42: 'FS2', 43: 'G2', 44: 'GS2', 45: 'A2', 46: 'AS2', 47: 'B2',
    48: 'C3', 49: 'CS3', 50: 'D3', 51: 'DS3', 52: 'E3', 53: 'F3',
    54: 'FS3', 55: 'G3', 56: 'GS3', 57: 'A3', 58: 'AS3', 59: 'B3',
    60: 'C4', 61: 'CS4', 62: 'D4', 63: 'DS4', 64: 'E4', 65: 'F4',
    66: 'FS4', 67: 'G4', 68: 'GS4', 69: 'A4', 70: 'AS4', 71: 'B4',
    72: 'C5', 73: 'CS5', 74: 'D5', 75: 'DS5', 76: 'E5', 77: 'F5',
    78: 'FS5', 79: 'G5', 80: 'GS5', 81: 'A5', 82: 'AS5', 83: 'B5',
    84: 'C6', 85: 'CS6', 86: 'D6', 87: 'DS6', 88: 'E6', 89: 'F6',
    90: 'FS6', 91: 'G6', 92: 'GS6', 93: 'A6', 94: 'AS6', 95: 'B6',
    96: 'C7', 97: 'CS7', 98: 'D7', 99: 'DS7', 100: 'E7', 101: 'F7',
    102: 'FS7', 103: 'G7', 104: 'GS7', 105: 'A7', 106: 'AS7', 107: 'B7',
    108: 'C8', 109: 'CS8', 110: 'D8', 111: 'DS8', 112: 'E8', 113: 'F8',
    114: 'FS8', 115: 'G8', 116: 'GS8', 117: 'A8', 118: 'AS8', 119: 'B8',
    120: 'C9', 121: 'CS9', 122: 'D9', 123: 'DS9', 124: 'E9', 125: 'F9',
    126: 'FS9', 127: 'G9'
}


def midi_note_to_name(note_number):
    """Convert MIDI note number to note name."""
    return MIDI_NOTE_NAMES.get(note_number, f'NOTE{note_number}')


class MidiAnalyzer:
    """Analyze and visualize MIDI files to help choose channels and understand structure."""
    
    def __init__(self):
        self.default_tempo = 500000  # 120 BPM
        
        # General MIDI instrument names for channels
        self.gm_instruments = {
            0: "Acoustic Grand Piano", 1: "Bright Acoustic Piano", 2: "Electric Grand Piano",
            3: "Honky-tonk Piano", 4: "Electric Piano 1", 5: "Electric Piano 2",
            6: "Harpsichord", 7: "Clavi", 8: "Celesta", 9: "Glockenspiel",
            10: "Music Box", 11: "Vibraphone", 12: "Marimba", 13: "Xylophone",
            14: "Tubular Bells", 15: "Dulcimer", 16: "Drawbar Organ", 17: "Percussive Organ",
            # ... (would include all 128, but abbreviated for space)
            24: "Acoustic Guitar (nylon)", 25: "Acoustic Guitar (steel)", 26: "Electric Guitar (jazz)",
            27: "Electric Guitar (clean)", 28: "Electric Guitar (muted)", 29: "Overdriven Guitar",
            30: "Distortion Guitar", 31: "Guitar harmonics", 32: "Acoustic Bass", 33: "Electric Bass (finger)",
            34: "Electric Bass (pick)", 35: "Fretless Bass", 36: "Slap Bass 1", 37: "Slap Bass 2",
            # Add more as needed...
        }
    
    def analyze_midi_file(self, midi_file):
        """
        Analyze a MIDI file and return detailed information about each channel.
        
        Returns:
            Dictionary with channel analysis
        """
        print(f"\n=== ANALYZING MIDI FILE: {midi_file} ===")
        
        try:
            mid = mido.MidiFile(midi_file)
        except Exception as e:
            print(f"Error loading MIDI file: {e}")
            return None
        
        ticks_per_beat = mid.ticks_per_beat
        current_tempo = self.default_tempo
        
        # Track info for each channel
        channel_info = {}
        for i in range(16):
            channel_info[i] = {
                'notes': [],
                'program': 0,  # Instrument number
                'instrument_name': 'Acoustic Grand Piano',
                'note_count': 0,
                'duration_ms': 0,
                'pitch_range': [127, 0],  # [min, max]
                'active_time_ms': 0,
                'has_activity': False
            }
        
        current_time = 0
        active_notes = {}  # Track note_on events waiting for note_off
        
        # First pass: collect all events
        for msg in mid:
            current_time += msg.time
            current_ms = ticks_to_milliseconds(current_time, ticks_per_beat, current_tempo)
            
            if msg.type == 'set_tempo':
                current_tempo = msg.tempo
            
            elif msg.type == 'program_change':
                channel_info[msg.channel]['program'] = msg.program
                channel_info[msg.channel]['instrument_name'] = self.gm_instruments.get(
                    msg.program, f"Program {msg.program}"
                )
            
            elif msg.type == 'note_on' and msg.velocity > 0:
                channel = msg.channel
                channel_info[channel]['has_activity'] = True
                active_notes[(channel, msg.note)] = current_ms
                
                # Update pitch range
                pitch_range = channel_info[channel]['pitch_range']
                pitch_range[0] = min(pitch_range[0], msg.note)
                pitch_range[1] = max(pitch_range[1], msg.note)
            
            elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
                key = (msg.channel, msg.note)
                if key in active_notes:
                    start_ms = active_notes[key]
                    duration = current_ms - start_ms
                    
                    channel_info[msg.channel]['notes'].append({
                        'note': msg.note,
                        'start': start_ms,
                        'duration': duration,
                        'velocity': getattr(msg, 'velocity', 64)
                    })
                    
                    channel_info[msg.channel]['note_count'] += 1
                    channel_info[msg.channel]['duration_ms'] = max(
                        channel_info[msg.channel]['duration_ms'], current_ms
                    )
                    
                    del active_notes[key]
        
        # Handle remaining active notes
        total_time_ms = ticks_to_milliseconds(current_time, ticks_per_beat, current_tempo)
        for (channel, note), start_ms in active_notes.items():
            duration = total_time_ms - start_ms
            channel_info[channel]['notes'].append({
                'note': note,
                'start': start_ms,
                'duration': duration,
                'velocity': 64
            })
            channel_info[channel]['note_count'] += 1
        
        # Calculate active time for each channel
        for channel in range(16):
            if channel_info[channel]['notes']:
                notes = channel_info[channel]['notes']
                # Calculate total time where notes are playing
                events = []
                for note in notes:
                    events.append((note['start'], 'start'))
                    events.append((note['start'] + note['duration'], 'end'))
                
                events.sort()
                active_time = 0
                active_count = 0
                last_time = 0
                
                for time, event_type in events:
                    if active_count > 0:
                        active_time += time - last_time
                    
                    if event_type == 'start':
                        active_count += 1
                    else:
                        active_count -= 1
                    
                    last_time = time
                
                channel_info[channel]['active_time_ms'] = active_time
        
        return {
            'file_info': {
                'filename': midi_file,
                'total_duration_ms': total_time_ms,
                'ticks_per_beat': ticks_per_beat,
                'estimated_bpm': 60000000 // current_tempo
            },
            'channels': channel_info
        }
    
    def print_analysis(self, analysis):
        """Print a detailed text analysis of the MIDI file."""
        if not analysis:
            return
        
        file_info = analysis['file_info']
        print(f"\nFile: {file_info['filename']}")
        print(f"Duration: {file_info['total_duration_ms']/1000:.1f}s")
        print(f"Estimated BPM: {file_info['estimated_bpm']}")
        print(f"Ticks per beat: {file_info['ticks_per_beat']}")
        
        print(f"\n{'Ch':<3} {'Instrument':<25} {'Notes':<6} {'Active%':<8} {'Pitch Range':<12} {'Recommended'}")
        print("-" * 80)
        
        # Sort channels by activity (most active first)
        active_channels = []
        for ch, info in analysis['channels'].items():
            if info['has_activity']:
                activity_percent = (info['active_time_ms'] / file_info['total_duration_ms']) * 100
                active_channels.append((ch, info, activity_percent))
        
        active_channels.sort(key=lambda x: x[2], reverse=True)
        
        recommendations = []
        
        for ch, info, activity_percent in active_channels:
            if info['note_count'] > 0:
                pitch_min = midi_note_to_name(info['pitch_range'][0])
                pitch_max = midi_note_to_name(info['pitch_range'][1])
                pitch_range = f"{pitch_min}-{pitch_max}"
                
                # Determine recommendation
                recommendation = ""
                if ch == 9:
                    recommendation = "❌ DRUMS (skip)"
                elif activity_percent > 50:
                    if info['pitch_range'][1] < 60:  # Below middle C
                        recommendation = "🎵 BASS"
                        recommendations.append(('bass', ch))
                    elif info['pitch_range'][0] > 72:  # Above C5
                        recommendation = "🎶 MELODY"
                        recommendations.insert(0, ('melody', ch))
                    else:
                        recommendation = "🎼 HARMONY"
                        recommendations.append(('harmony', ch))
                elif activity_percent > 10:
                    recommendation = "🎵 Secondary"
                else:
                    recommendation = "〰️ Minimal"
                
                print(f"{ch:<3} {info['instrument_name'][:24]:<25} {info['note_count']:<6} "
                      f"{activity_percent:6.1f}% {pitch_range:<12} {recommendation}")
        
        # Analyze conflicts
        conflict_analysis = self.analyze_conflicts(analysis)
        
        # Show conflict information
        channels_with_conflicts = []
        for ch, conflict_info in conflict_analysis.items():
            if conflict_info['needs_splitting']:
                channels_with_conflicts.append((ch, conflict_info))
        
        if channels_with_conflicts:
            print(f"\n⚠️  POLYPHONIC CONFLICTS DETECTED:")
            print(f"{'Ch':<3} {'Max Notes':<10} {'Conflict%':<10} {'Recommended Split'}")
            print("-" * 45)
            
            for ch, conflict_info in channels_with_conflicts:
                print(f"{ch:<3} {conflict_info['max_simultaneous']:<10} "
                      f"{conflict_info['conflict_percentage']:<9.1f}% "
                      f"{conflict_info['recommended_splits']} tracks")
            
            # Generate split command
            split_suggestions = []
            for ch, conflict_info in channels_with_conflicts[:3]:  # Top 3 conflicted channels
                split_suggestions.append(f"{ch}:{conflict_info['recommended_splits']}")
            
            if split_suggestions:
                print(f"\n🔧 SUGGESTED SPLIT COMMAND:")
                channels_list = ','.join([str(ch) for ch, _ in channels_with_conflicts[:3]])
                split_list = ','.join(split_suggestions)
                print(f"   python process_midi.py {file_info['filename']} --channels {channels_list} --split '{split_list}' --output songs/output.json")
        
        # Print recommendations
        if recommendations:
            print(f"\n🎯 RECOMMENDED CHANNELS FOR PIEZOS:")
            suggested_channels = []
            for i, (role, channel) in enumerate(recommendations[:3]):  # Top 3 channels
                conflict_note = ""
                if channel in conflict_analysis and conflict_analysis[channel]['needs_splitting']:
                    conflict_note = f" ⚠️  (has {conflict_analysis[channel]['max_simultaneous']} overlapping notes)"
                print(f"   Piezo {i+1}: Channel {channel} ({role}){conflict_note}")
                suggested_channels.append(str(channel))
            
            if suggested_channels:
                print(f"\n💡 BASIC COMMAND (may have note conflicts):")
                print(f"   python process_midi.py {file_info['filename']} --channels {','.join(suggested_channels)} --output songs/output.json")
    
    def visualize_individual_notes(self, analysis, channels=None, output_file=None, max_notes=200):
        """Create a detailed visualization showing individual notes with labels."""
        if not MATPLOTLIB_AVAILABLE:
            print("❌ matplotlib not available - install with: pip install matplotlib")
            return
        
        if not analysis:
            return
        
        file_info = analysis['file_info']
        
        # Determine which channels to show
        if channels is None:
            channels = [ch for ch, info in analysis['channels'].items() 
                       if info['has_activity'] and info['note_count'] > 0]
        
        if not channels:
            print("No active channels to visualize")
            return
        
        # Check total notes across all channels
        total_notes = sum(analysis['channels'][ch]['note_count'] for ch in channels)
        if total_notes > max_notes:
            print(f"⚠️  Too many notes ({total_notes}) for individual note view.")
            print(f"   Using standard channel view instead (limit: {max_notes})")
            self.visualize_channels(analysis, channels, output_file)
            return
        
        print(f"📝 Creating detailed individual note view ({total_notes} notes)")
        
        # Create larger figure for detail
        fig_height = max(10, 3 * len(channels))
        fig, axes = plt.subplots(len(channels), 1, figsize=(20, fig_height))
        if len(channels) == 1:
            axes = [axes]
        
        fig.suptitle(f"Individual Notes: {Path(file_info['filename']).name}", 
                    fontsize=18, fontweight='bold', y=0.98)
        
        total_duration_sec = file_info['total_duration_ms'] / 1000
        x_max = total_duration_sec * 1.02
        
        for i, channel in enumerate(channels):
            ax = axes[i]
            info = analysis['channels'][channel]
            
            # Sort notes by start time for better visualization
            sorted_notes = sorted(info['notes'], key=lambda x: x['start'])
            
            # Plot each note with detailed information
            for j, note_data in enumerate(sorted_notes):
                start_sec = note_data['start'] / 1000
                duration_sec = max(note_data['duration'] / 1000, 0.05)
                pitch = note_data['note']
                velocity = note_data['velocity']
                
                # Color based on velocity
                velocity_norm = velocity / 127
                if pitch < 48:
                    color = plt.get_cmap('Reds')(0.5 + velocity_norm * 0.5)
                elif pitch < 72:
                    color = plt.get_cmap('Blues')(0.5 + velocity_norm * 0.5)
                else:
                    color = plt.get_cmap('Greens')(0.5 + velocity_norm * 0.5)
                
                # Create note rectangle with border
                rect = ax.barh(pitch, duration_sec, left=start_sec, height=0.9,
                              color=color, edgecolor='black', linewidth=0.8, alpha=0.8)
                
                # Always show note names for individual view
                note_name = midi_note_to_name(pitch)
                text_x = start_sec + duration_sec / 2
                
                # Add note name
                ax.text(text_x, pitch, note_name, 
                       ha='center', va='center', 
                       fontsize=9, fontweight='bold', color='white')
                
                # Add timing info for longer notes
                if duration_sec > 0.5:
                    timing_text = f"{start_sec:.1f}s"
                    ax.text(start_sec + 0.02, pitch + 0.3, timing_text,
                           fontsize=7, color='black', alpha=0.7)
                
                # Add velocity info
                if velocity != 64:  # Only show if not default
                    vel_text = f"v{velocity}"
                    ax.text(start_sec + duration_sec - 0.02, pitch - 0.3, vel_text,
                           fontsize=7, color='gray', ha='right')
            
            # Enhanced formatting for individual notes
            instrument_name = info['instrument_name']
            if len(instrument_name) > 20:
                instrument_name = instrument_name[:17] + "..."
            
            ax.set_ylabel(f"Channel {channel}\n{instrument_name}\n({info['note_count']} notes)", 
                         fontsize=12, fontweight='bold')
            
            ax.set_xlim(0, x_max)
            
            # Set pitch range with more padding for individual notes
            if info['pitch_range'][1] > info['pitch_range'][0]:
                pitch_padding = 1
                ax.set_ylim(info['pitch_range'][0] - pitch_padding, 
                           info['pitch_range'][1] + pitch_padding)
            
            # Show all semitones for individual note view
            all_pitches = sorted(set(note['note'] for note in info['notes']))
            ax.set_yticks(all_pitches)
            ax.set_yticklabels([midi_note_to_name(p) for p in all_pitches], fontsize=9)
            
            # Add minor grid lines
            ax.grid(True, alpha=0.4, linestyle='-', linewidth=0.3)
            ax.grid(True, which='minor', alpha=0.2, linestyle=':', linewidth=0.2)
            
            # Enhanced time axis
            if total_duration_sec > 30:
                time_step = max(5, int(total_duration_sec / 15))
                time_ticks = list(range(0, int(total_duration_sec) + 1, time_step))
                ax.set_xticks(time_ticks)
                ax.set_xticklabels([f"{t//60}:{t%60:02d}" for t in time_ticks])
            else:
                time_step = max(1, int(total_duration_sec / 20))
                time_ticks = [i * time_step for i in range(int(total_duration_sec / time_step) + 2)]
                ax.set_xticks(time_ticks)
                ax.set_xticklabels([f"{t:.1f}s" for t in time_ticks])
            
            # Add detailed statistics
            avg_velocity = sum(n['velocity'] for n in info['notes']) / len(info['notes'])
            avg_duration = sum(n['duration'] for n in info['notes']) / len(info['notes']) / 1000
            
            stats_text = (f"Avg Velocity: {avg_velocity:.0f}\n"
                         f"Avg Duration: {avg_duration:.2f}s\n"
                         f"Pitch Range: {info['pitch_range'][1] - info['pitch_range'][0]} semitones")
            
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   fontsize=9, verticalalignment='top',
                   bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow", alpha=0.9))
        
        plt.xlabel("Time", fontsize=14, fontweight='bold')
        plt.tight_layout(rect=(0, 0, 1, 0.96))
        
        if output_file:
            plt.savefig(output_file, dpi=200, bbox_inches='tight')
            print(f"📊 Individual notes visualization saved to: {output_file}")
        else:
            plt.show()
    
    def visualize_channels(self, analysis, channels=None, output_file=None):
        """Create a visual plot of the MIDI channels."""
        if not MATPLOTLIB_AVAILABLE:
            print("❌ matplotlib not available - install with: pip install matplotlib")
            return
        
        if not analysis:
            return
        
        file_info = analysis['file_info']
        
        # Determine which channels to show
        if channels is None:
            # Show channels with activity
            channels = [ch for ch, info in analysis['channels'].items() 
                       if info['has_activity'] and info['note_count'] > 0]
        
        if not channels:
            print("No active channels to visualize")
            return
        
        # Create the plot with better sizing
        fig_height = max(8, 2.5 * len(channels))  # Minimum 8 inches, more for many channels
        fig, axes = plt.subplots(len(channels), 1, figsize=(16, fig_height))
        if len(channels) == 1:
            axes = [axes]
        
        fig.suptitle(f"MIDI Channel Timeline: {Path(file_info['filename']).name}", 
                    fontsize=16, fontweight='bold', y=0.98)
        
        # Calculate total duration with some padding
        total_duration_sec = file_info['total_duration_ms'] / 1000
        x_max = total_duration_sec * 1.02  # Add 2% padding
        
        for i, channel in enumerate(channels):
            ax = axes[i]
            info = analysis['channels'][channel]
            
            # Plot individual notes as rectangles with note names
            for j, note_data in enumerate(info['notes']):
                start_sec = note_data['start'] / 1000
                duration_sec = max(note_data['duration'] / 1000, 0.1)  # Minimum visual duration
                pitch = note_data['note']
                velocity = note_data['velocity']
                
                # Color based on pitch range with velocity affecting saturation
                base_alpha = max(0.6, velocity / 127)  # Minimum 60% opacity
                
                # Use different colors for different pitch ranges
                if pitch < 48:  # Low notes (bass)
                    color = 'crimson'
                elif pitch < 72:  # Mid notes
                    color = 'royalblue'
                else:  # High notes (melody)
                    color = 'forestgreen'
                
                # Create the note rectangle
                rect = ax.barh(pitch, duration_sec, left=start_sec, height=0.8, 
                              alpha=base_alpha, color=color, 
                              edgecolor='black', linewidth=0.5)
                
                # Add note name text if the note is long enough and not too crowded
                note_name = midi_note_to_name(pitch)
                
                # Only show note names for notes longer than 0.3 seconds or if few notes
                if duration_sec > 0.3 or len(info['notes']) < 50:
                    # Position text in the center of the note
                    text_x = start_sec + duration_sec / 2
                    text_y = pitch
                    
                    # Choose text color for visibility
                    text_color = 'white' if base_alpha > 0.7 else 'black'
                    
                    # Add the note name
                    ax.text(text_x, text_y, note_name, 
                           ha='center', va='center', 
                           fontsize=8, fontweight='bold',
                           color=text_color,
                           bbox=dict(boxstyle="round,pad=0.1", 
                                   facecolor='white', alpha=0.3, edgecolor='none'))
                
                # Add velocity information for very long notes
                if duration_sec > 1.0:
                    vel_text = f"v{velocity}"
                    ax.text(start_sec + 0.05, pitch - 0.3, vel_text,
                           fontsize=6, color='gray', alpha=0.8)
            
            # Formatting
            instrument_name = info['instrument_name']
            if len(instrument_name) > 18:
                instrument_name = instrument_name[:15] + "..."
            
            ax.set_ylabel(f"Channel {channel}\n{instrument_name}", 
                         fontsize=11, fontweight='bold')
            
            # Set x-axis to show complete timeline
            ax.set_xlim(0, x_max)
            
            # Set y-axis to show full pitch range with padding
            if info['pitch_range'][1] > info['pitch_range'][0]:
                pitch_padding = max(2, (info['pitch_range'][1] - info['pitch_range'][0]) * 0.1)
                ax.set_ylim(info['pitch_range'][0] - pitch_padding, 
                           info['pitch_range'][1] + pitch_padding)
            
            # Add note labels on y-axis - show more detail for individual notes
            if info['pitch_range'][1] > info['pitch_range'][0]:
                pitch_span = info['pitch_range'][1] - info['pitch_range'][0]
                
                if pitch_span <= 24:  # Small range - show every note
                    note_ticks = list(range(info['pitch_range'][0], info['pitch_range'][1] + 1))
                    ax.set_yticks(note_ticks)
                    ax.set_yticklabels([midi_note_to_name(n) for n in note_ticks], fontsize=8)
                elif pitch_span <= 48:  # Medium range - show every 2-3 notes
                    note_ticks = list(range(info['pitch_range'][0], info['pitch_range'][1] + 1, 3))
                    ax.set_yticks(note_ticks)
                    ax.set_yticklabels([midi_note_to_name(n) for n in note_ticks], fontsize=9)
                else:  # Large range - show octaves
                    start_octave = (info['pitch_range'][0] // 12) * 12
                    end_octave = ((info['pitch_range'][1] // 12) + 1) * 12
                    note_ticks = list(range(start_octave, end_octave + 1, 12))
                    note_ticks = [n for n in note_ticks 
                                 if info['pitch_range'][0] - 6 <= n <= info['pitch_range'][1] + 6]
                    ax.set_yticks(note_ticks)
                    ax.set_yticklabels([midi_note_to_name(n) for n in note_ticks], fontsize=10)
                
                # Add minor ticks for individual semitones
                if pitch_span <= 36:  # Only for reasonable ranges
                    minor_ticks = list(range(info['pitch_range'][0], info['pitch_range'][1] + 1))
                    ax.set_yticks(minor_ticks, minor=True)
                    ax.grid(True, which='minor', alpha=0.2, linestyle=':', linewidth=0.5)
            
            # Add time markers on x-axis
            if total_duration_sec > 60:  # For long songs, show minutes
                time_step = max(30, int(total_duration_sec / 10))  # ~10 markers max
                time_ticks = list(range(0, int(total_duration_sec) + 1, time_step))
                ax.set_xticks(time_ticks)
                ax.set_xticklabels([f"{t//60}:{t%60:02d}" for t in time_ticks])
            else:  # For short songs, show seconds
                time_step = max(5, int(total_duration_sec / 10))
                time_ticks = list(range(0, int(total_duration_sec) + 1, time_step))
                ax.set_xticks(time_ticks)
                ax.set_xticklabels([f"{t}s" for t in time_ticks])
            
            ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            ax.set_axisbelow(True)
            
            # Add activity summary in corner
            activity_percent = (info['active_time_ms'] / file_info['total_duration_ms']) * 100
            ax.text(0.02, 0.95, f"{info['note_count']} notes\n{activity_percent:.1f}% active", 
                   transform=ax.transAxes, fontsize=9, verticalalignment='top',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
        
        # Add overall x-label
        plt.xlabel("Time", fontsize=12, fontweight='bold')
        plt.tight_layout(rect=(0, 0, 1, 0.96))  # Leave space for title
        
        if output_file:
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            print(f"📊 Visualization saved to: {output_file}")
        else:
            plt.show()
    
    def visualize_usage_summary(self, analysis, output_file=None):
        """Create comprehensive usage visualization with multiple charts."""
        if not MATPLOTLIB_AVAILABLE:
            print("❌ matplotlib not available - install with: pip install matplotlib")
            return
        
        if not analysis:
            return
        
        file_info = analysis['file_info']
        
        # Get active channels sorted by activity
        active_channels = []
        for ch, info in analysis['channels'].items():
            if info['has_activity'] and info['note_count'] > 0:
                activity_percent = (info['active_time_ms'] / file_info['total_duration_ms']) * 100
                active_channels.append((ch, info, activity_percent))
        
        active_channels.sort(key=lambda x: x[2], reverse=True)
        
        if not active_channels:
            print("No active channels to visualize")
            return
        
        # Create subplots
        fig = plt.figure(figsize=(16, 12))
        
        # 1. Channel Activity Bar Chart
        ax1 = plt.subplot(2, 3, 1)
        channels = [f"Ch {ch}" for ch, _, _ in active_channels]
        activities = [activity for _, _, activity in active_channels]
        # Create colors for bars
        cmap = plt.get_cmap('viridis')
        colors = [cmap(i / len(channels)) for i in range(len(channels))]
        
        bars = ax1.bar(channels, activities, color=colors)
        ax1.set_title('Channel Activity (%)', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Active Time %')
        ax1.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar, activity in zip(bars, activities):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{activity:.1f}%', ha='center', va='bottom', fontsize=10)
        
        # 2. Note Count Bar Chart
        ax2 = plt.subplot(2, 3, 2)
        note_counts = [info['note_count'] for _, info, _ in active_channels]
        bars2 = ax2.bar(channels, note_counts, color=colors)
        ax2.set_title('Total Notes Played', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Number of Notes')
        ax2.tick_params(axis='x', rotation=45)
        
        # Add value labels
        for bar, count in zip(bars2, note_counts):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + max(note_counts)*0.01,
                    str(count), ha='center', va='bottom', fontsize=10)
        
        # 3. Instrument Distribution Pie Chart
        ax3 = plt.subplot(2, 3, 3)
        instruments = []
        instrument_activities = []
        
        for ch, info, activity in active_channels:
            instrument_name = info['instrument_name']
            if len(instrument_name) > 20:
                instrument_name = instrument_name[:17] + "..."
            instruments.append(f"Ch{ch}: {instrument_name}")
            instrument_activities.append(activity)
        
        pie_result = ax3.pie(instrument_activities, labels=instruments, 
                            autopct='%1.1f%%', startangle=90)
        wedges = pie_result[0]
        texts = pie_result[1]
        autotexts = pie_result[2] if len(pie_result) > 2 else []
        ax3.set_title('Activity Distribution by Instrument', fontsize=14, fontweight='bold')
        
        # Make text smaller if too many channels
        if len(instruments) > 6:
            for text in texts:
                text.set_fontsize(8)
            for autotext in autotexts:
                autotext.set_fontsize(8)
        
        # 4. Pitch Range Visualization
        ax4 = plt.subplot(2, 3, 4)
        channel_nums = [ch for ch, _, _ in active_channels]
        pitch_mins = [info['pitch_range'][0] for _, info, _ in active_channels]
        pitch_maxs = [info['pitch_range'][1] for _, info, _ in active_channels]
        pitch_ranges = [max_p - min_p for min_p, max_p in zip(pitch_mins, pitch_maxs)]
        
        # Create horizontal bar chart showing pitch ranges
        y_pos = np.arange(len(channel_nums))
        for i, (ch, min_pitch, max_pitch) in enumerate(zip(channel_nums, pitch_mins, pitch_maxs)):
            ax4.barh(i, max_pitch - min_pitch, left=min_pitch, height=0.6, 
                    color=colors[i], alpha=0.7)
            # Add channel label
            ax4.text(min_pitch - 2, i, f'Ch {ch}', ha='right', va='center', fontsize=10)
        
        ax4.set_yticks(y_pos)
        ax4.set_yticklabels([f"Ch {ch}" for ch in channel_nums])
        ax4.set_xlabel('MIDI Note Number')
        ax4.set_title('Pitch Ranges by Channel', fontsize=14, fontweight='bold')
        
        # Add note name labels on x-axis
        note_ticks = list(range(0, 128, 12))
        ax4.set_xticks(note_ticks)
        ax4.set_xticklabels([midi_note_to_name(n) for n in note_ticks], rotation=45)
        ax4.grid(True, alpha=0.3)
        
        # 5. Timeline Activity Heatmap
        ax5 = plt.subplot(2, 3, 5)
        
        # Create time bins (every second)
        duration_sec = file_info['total_duration_ms'] / 1000
        time_bins = int(duration_sec) + 1
        
        # Create activity matrix
        activity_matrix = np.zeros((len(active_channels), time_bins))
        
        for i, (ch, info, _) in enumerate(active_channels):
            for note in info['notes']:
                start_bin = int(note['start'] / 1000)
                end_bin = min(int((note['start'] + note['duration']) / 1000), time_bins - 1)
                for bin_idx in range(start_bin, end_bin + 1):
                    if bin_idx < time_bins:
                        activity_matrix[i, bin_idx] += 1
        
        im = ax5.imshow(activity_matrix, aspect='auto', cmap='YlOrRd', 
                       extent=(0, duration_sec, len(active_channels)-0.5, -0.5))
        ax5.set_xlabel('Time (seconds)')
        ax5.set_ylabel('Channel')
        ax5.set_title('Activity Timeline Heatmap', fontsize=14, fontweight='bold')
        ax5.set_yticks(range(len(active_channels)))
        ax5.set_yticklabels([f"Ch {ch}" for ch, _, _ in active_channels])
        
        # Add colorbar
        plt.colorbar(im, ax=ax5, label='Notes per second')
        
        # 6. Recommendation Summary
        ax6 = plt.subplot(2, 3, 6)
        ax6.axis('off')
        
        # Create recommendation text
        rec_text = "🎯 PIEZO RECOMMENDATIONS\n\n"
        
        piezo_assignments = []
        for i, (ch, info, activity) in enumerate(active_channels[:3]):  # Top 3
            if ch == 9:  # Skip drums
                continue
                
            role = "🎶 MELODY" if info['pitch_range'][0] > 72 else \
                   "🎵 BASS" if info['pitch_range'][1] < 60 else \
                   "🎼 HARMONY"
            
            piezo_assignments.append((i+1, ch, role, info['instrument_name'][:20]))
        
        for piezo_num, ch, role, instrument in piezo_assignments:
            rec_text += f"Piezo {piezo_num}: Channel {ch}\n"
            rec_text += f"  {role}\n"
            rec_text += f"  {instrument}\n\n"
        
        if piezo_assignments:
            channels_str = ','.join([str(ch) for _, ch, _, _ in piezo_assignments])
            rec_text += f"💡 Command:\n"
            rec_text += f"python process_midi.py \\\n"
            rec_text += f"  {Path(file_info['filename']).name} \\\n"
            rec_text += f"  --channels {channels_str} \\\n"
            rec_text += f"  --output songs/output.json"
        
        ax6.text(0.05, 0.95, rec_text, transform=ax6.transAxes, fontsize=11,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.8))
        
        plt.suptitle(f"MIDI Usage Analysis: {Path(file_info['filename']).name}", 
                    fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            print(f"📊 Usage summary saved to: {output_file}")
        else:
            plt.show()
    
    def quick_preview(self, midi_file, show_plot=False, save_plot=False, plot_output=None):
        """Quick analysis and visualization of a MIDI file."""
        analysis = self.analyze_midi_file(midi_file)
        if analysis:
            self.print_analysis(analysis)
            
            if MATPLOTLIB_AVAILABLE and (show_plot or save_plot):
                # Generate default filename if not provided
                if save_plot and not plot_output:
                    base_name = Path(midi_file).stem
                    plot_output = f"{base_name}_preview.png"
                
                # Show and/or save the plot
                if show_plot and not save_plot:
                    self.visualize_channels(analysis)
                elif save_plot and not show_plot:
                    self.visualize_channels(analysis, output_file=plot_output)
                elif show_plot and save_plot:
                    # Show first, then save
                    self.visualize_channels(analysis)
                    # Create a new plot for saving to avoid conflicts
                    self.visualize_channels(analysis, output_file=plot_output)
        
        return analysis
    
    def analyze_conflicts(self, analysis):
        """
        Analyze note conflicts (overlapping notes) in each channel.
        
        Returns:
            Dictionary with conflict analysis for each channel
        """
        conflict_analysis = {}
        
        for channel, info in analysis['channels'].items():
            if not info['has_activity'] or not info['notes']:
                continue
            
            notes = info['notes']
            conflicts = []
            max_simultaneous = 0
            
            # Create events for conflict detection
            events = []
            for i, note in enumerate(notes):
                events.append((note['start'], 'start', i, note))
                events.append((note['start'] + note['duration'], 'end', i, note))
            
            # Sort by time, with 'end' events before 'start' events at same time
            events.sort(key=lambda x: (x[0], x[1] == 'start'))
            
            active_notes = set()
            
            for time, event_type, note_idx, note in events:
                if event_type == 'start':
                    active_notes.add(note_idx)
                    max_simultaneous = max(max_simultaneous, len(active_notes))
                    
                    # Check for conflicts with currently active notes
                    if len(active_notes) > 1:
                        conflict_notes = [notes[idx] for idx in active_notes]
                        conflicts.append({
                            'time': time,
                            'count': len(active_notes),
                            'notes': conflict_notes
                        })
                else:
                    active_notes.discard(note_idx)
            
            # Calculate conflict statistics
            total_conflict_time = 0
            if conflicts:
                # Merge overlapping conflict periods
                conflict_periods = []
                current_start = conflicts[0]['time']
                current_end = current_start
                
                for conflict in conflicts:
                    if conflict_periods and conflict['time'] > current_end + 100:  # 100ms gap
                        conflict_periods.append((current_start, current_end))
                        current_start = conflict['time']
                    current_end = conflict['time']
                
                if current_start <= current_end:
                    conflict_periods.append((current_start, current_end))
                
                total_conflict_time = sum(end - start for start, end in conflict_periods)
            
            conflict_analysis[channel] = {
                'total_conflicts': len(conflicts),
                'max_simultaneous': max_simultaneous,
                'conflict_time_ms': total_conflict_time,
                'conflict_percentage': (total_conflict_time / analysis['file_info']['total_duration_ms']) * 100 if analysis['file_info']['total_duration_ms'] > 0 else 0,
                'needs_splitting': max_simultaneous > 1,
                'recommended_splits': min(max_simultaneous, 4)  # Cap at 4 piezos
            }
        
        return conflict_analysis


def ticks_to_milliseconds(ticks, ticks_per_beat, tempo):
    """
    Convert MIDI ticks to milliseconds.
    
    Args:
        ticks: MIDI ticks
        ticks_per_beat: Ticks per quarter note from MIDI file
        tempo: Microseconds per quarter note (from MIDI tempo events)
    
    Returns:
        Time in milliseconds
    """
    seconds = (ticks / ticks_per_beat) * (tempo / 1000000)
    return int(seconds * 1000)


class MidiProcessor:
    """Process MIDI files and convert to JSON format for the Musician class."""
    
    def __init__(self):
        self.default_tempo = 500000  # 120 BPM in microseconds per quarter note
    
    def split_polyphonic_channel(self, notes, num_splits, strategy='pitch_priority'):
        """
        Split overlapping notes from a single channel into multiple non-conflicting tracks.
        
        Args:
            notes: List of note dictionaries with 'note', 'start', 'duration'
            num_splits: Number of tracks to split into
            strategy: 'pitch_priority' (highest notes first), 'time_priority' (first notes first),
                     'bass_split' (separate bass from melody)
        
        Returns:
            List of note lists, one for each split track
        """
        if not notes:
            return [[] for _ in range(num_splits)]
        
        print(f"🎵 Splitting {len(notes)} notes into {num_splits} non-conflicting tracks...")
        print(f"📝 Sample notes: {notes[:3] if len(notes) >= 3 else notes}")
        
        # Sort notes by start time
        sorted_notes = sorted(notes, key=lambda x: x['start'])
        print(f"📝 Sorted notes count: {len(sorted_notes)}")
        
        # Initialize tracks
        tracks = [[] for _ in range(num_splits)]
        track_end_times = [0] * num_splits  # When each track is free
        
        if strategy == 'bass_split' and num_splits >= 2:
            # For very few notes, use simple distribution instead
            if len(notes) <= num_splits:
                print(f"  Too few notes ({len(notes)}) for bass/melody split, using simple distribution")
                for i, note in enumerate(sorted_notes):
                    tracks[i].append(note)
                return tracks
            
            # Separate bass (lower) from melody (higher) notes
            all_pitches = []
            for note in notes:
                note_name = note['note']
                if isinstance(note_name, str):
                    pitch = self._note_to_pitch(note_name)
                else:
                    pitch = note_name
                all_pitches.append(pitch)
            
            # Use a better splitting point - not median but based on actual pitch gaps
            sorted_pitches = sorted(all_pitches)
            
            # Find the biggest gap in pitches to split bass/melody
            best_split_pitch = sorted_pitches[len(sorted_pitches) // 2]  # Default to median
            max_gap = 0
            for i in range(len(sorted_pitches) - 1):
                gap = sorted_pitches[i + 1] - sorted_pitches[i]
                if gap > max_gap:
                    max_gap = gap
                    best_split_pitch = (sorted_pitches[i] + sorted_pitches[i + 1]) / 2
            
            print(f"  Bass/melody split at pitch {best_split_pitch:.1f} ({midi_note_to_name(int(best_split_pitch))})")
            
            bass_notes = []
            melody_notes = []
            
            for note in sorted_notes:
                note_name = note['note']
                if isinstance(note_name, str):
                    pitch = self._note_to_pitch(note_name)
                else:
                    pitch = note_name
                    
                if pitch < best_split_pitch:
                    bass_notes.append(note)
                else:
                    melody_notes.append(note)
            
            print(f"  → Bass notes: {len(bass_notes)}, Melody notes: {len(melody_notes)}")
            
            # Don't recursively split - just distribute notes directly
            tracks = [[] for _ in range(num_splits)]
            
            # Assign bass notes to first half of tracks
            bass_track_count = max(1, num_splits // 2)
            for i, note in enumerate(bass_notes):
                track_idx = i % bass_track_count
                tracks[track_idx].append(note)
            
            # Assign melody notes to second half of tracks
            melody_track_start = bass_track_count
            melody_track_count = num_splits - bass_track_count
            if melody_track_count > 0:
                for i, note in enumerate(melody_notes):
                    track_idx = melody_track_start + (i % melody_track_count)
                    tracks[track_idx].append(note)
            else:
                # If no melody tracks, put melody notes in bass tracks
                for i, note in enumerate(melody_notes):
                    track_idx = i % bass_track_count
                    tracks[track_idx].append(note)
            
            return tracks
        
        elif strategy == 'pitch_priority':
            # Assign notes to tracks avoiding conflicts
            for note in sorted_notes:
                note_start = note['start']
                note_end = note_start + note['duration']
                
                # Find the best track for this note
                best_track = -1
                
                # Strategy: prefer tracks that are free, then distribute by pitch
                available_tracks = []
                for i in range(num_splits):
                    if track_end_times[i] <= note_start:  # Track is free
                        available_tracks.append(i)
                
                if available_tracks:
                    # Among available tracks, choose based on pitch and distribution
                    note_name = note['note']
                    if isinstance(note_name, str):
                        pitch = self._note_to_pitch(note_name)
                    else:
                        pitch = note_name
                    
                    if len(available_tracks) == 1:
                        best_track = available_tracks[0]
                    else:
                        # Distribute notes more evenly across available tracks
                        # First try to find a track with similar pitch range
                        best_match_track = available_tracks[0]
                        best_pitch_diff = float('inf')
                        
                        for track_idx in available_tracks:
                            if tracks[track_idx]:  # Track has existing notes
                                # Calculate average pitch of existing notes in this track
                                existing_pitches = []
                                for existing_note in tracks[track_idx]:
                                    existing_note_name = existing_note['note']
                                    if isinstance(existing_note_name, str):
                                        existing_pitch = self._note_to_pitch(existing_note_name)
                                    else:
                                        existing_pitch = existing_note_name
                                    existing_pitches.append(existing_pitch)
                                avg_existing_pitch = sum(existing_pitches) / len(existing_pitches)
                                
                                pitch_diff = abs(pitch - avg_existing_pitch)
                                if pitch_diff < best_pitch_diff:
                                    best_pitch_diff = pitch_diff
                                    best_match_track = track_idx
                            else:
                                # Empty track - good candidate
                                best_match_track = track_idx
                                break
                        
                        best_track = best_match_track
                else:
                    # No tracks are completely free, find the one that frees up soonest
                    best_track = min(range(num_splits), key=lambda i: track_end_times[i])
                    
                    # If there's a conflict, we need to handle it
                    conflict_end = track_end_times[best_track]
                    if conflict_end > note_start:
                        print(f"⚠️  Note conflict: Note at {note_start}ms conflicts with track {best_track} "
                              f"(free at {conflict_end}ms). Assigning anyway with potential overlap.")
                
                # Assign the note to the chosen track
                tracks[best_track].append(note)
                track_end_times[best_track] = note_end
        
        elif strategy == 'time_priority':
            # Simple round-robin assignment by time
            for i, note in enumerate(sorted_notes):
                track_idx = i % num_splits
                tracks[track_idx].append(note)
        
        # Calculate statistics
        for i, track in enumerate(tracks):
            if track:
                pitches = []
                for note in track:
                    note_name = note['note']
                    if isinstance(note_name, str):
                        pitch = self._note_to_pitch(note_name)
                    else:
                        pitch = note_name
                    pitches.append(pitch)
                
                if pitches:  # Make sure we have pitches
                    avg_pitch = sum(pitches) / len(pitches)
                    pitch_range = max(pitches) - min(pitches) if len(pitches) > 1 else 0
                    print(f"  Track {i+1}: {len(track)} notes, avg pitch {avg_pitch:.1f} "
                          f"({midi_note_to_name(int(avg_pitch))}), range {pitch_range} semitones")
                else:
                    print(f"  Track {i+1}: {len(track)} notes (no valid pitches)")
        
        return tracks
    
    def process_single_midi(self, midi_file, channels=None, max_polyphony=1, split_channels=None):
        """
        Process a single MIDI file, extracting specified channels.
        
        Args:
            midi_file: Path to MIDI file
            channels: List of channel numbers to extract (None = all non-drum channels)
            max_polyphony: Maximum simultaneous notes per channel (1 for piezos)
            split_channels: Dict mapping channel numbers to number of splits
                          e.g., {0: 3, 1: 2} splits channel 0 into 3 tracks, channel 1 into 2
        
        Returns:
            Dictionary with song data
        """
        print(f"Processing MIDI file: {midi_file}")
        
        try:
            mid = mido.MidiFile(midi_file)
        except Exception as e:
            print(f"Error loading MIDI file: {e}")
            return None
        
        # Get basic info
        ticks_per_beat = mid.ticks_per_beat
        current_tempo = self.default_tempo
        
        # Track notes for each channel
        channel_notes = {}
        if channels is None:
            # Use channels 0-8, 10-15 (skip channel 9 which is drums)
            channels = [i for i in range(16) if i != 9]
        
        for channel in channels:
            channel_notes[channel] = []
        
        # Track active notes (for note_off events)
        active_notes = {}  # {(channel, note): start_time}
        
        current_time = 0
        
        # Process all messages
        for msg in mid:
            current_time += msg.time
            
            if msg.type == 'set_tempo':
                current_tempo = msg.tempo
                print(f"Tempo change: {60000000 // current_tempo} BPM")
            
            elif msg.type == 'note_on' and msg.channel in channels:
                if msg.velocity > 0:  # Note on
                    start_ms = ticks_to_milliseconds(current_time, ticks_per_beat, current_tempo)
                    active_notes[(msg.channel, msg.note)] = start_ms
                else:  # Note off (velocity 0)
                    self._handle_note_off(msg.channel, msg.note, current_time, 
                                        ticks_per_beat, current_tempo, 
                                        active_notes, channel_notes)
            
            elif msg.type == 'note_off' and msg.channel in channels:
                self._handle_note_off(msg.channel, msg.note, current_time, 
                                    ticks_per_beat, current_tempo, 
                                    active_notes, channel_notes)
        
        # Handle any remaining active notes
        total_time_ms = ticks_to_milliseconds(current_time, ticks_per_beat, current_tempo)
        for (channel, note), start_ms in active_notes.items():
            duration = max(100, total_time_ms - start_ms)  # Minimum 100ms duration
            note_name = midi_note_to_name(note)
            channel_notes[channel].append({
                'note': note_name,
                'start': start_ms,
                'duration': duration
            })
        
        # Apply polyphony limiting and sort notes
        # BUT skip polyphony limiting for channels that will be split
        for channel in channel_notes:
            if split_channels and channel in split_channels:
                # Don't limit polyphony - we'll split the overlapping notes instead
                print(f"📝 Channel {channel}: Keeping all {len(channel_notes[channel])} notes for splitting")
                channel_notes[channel].sort(key=lambda x: x['start'])
            else:
                # Apply polyphony limiting for channels that won't be split
                original_count = len(channel_notes[channel])
                channel_notes[channel] = self._limit_polyphony(
                    channel_notes[channel], max_polyphony
                )
                channel_notes[channel].sort(key=lambda x: x['start'])
                if original_count != len(channel_notes[channel]):
                    print(f"📝 Channel {channel}: Limited from {original_count} to {len(channel_notes[channel])} notes (max_polyphony={max_polyphony})")
        
        # Handle channel splitting if requested
        if split_channels:
            print(f"\n🎼 Processing channel splits...")
            final_lines = []
            
            for channel in sorted(channels):
                if not channel_notes[channel]:
                    continue
                    
                if channel in split_channels:
                    num_splits = split_channels[channel]
                    print(f"\n📊 Splitting channel {channel} into {num_splits} tracks:")
                    
                    # Determine splitting strategy based on note analysis
                    notes = channel_notes[channel]
                    print(f"  Channel {channel} has {len(notes)} notes to split")
                    
                    # Extract pitches - notes are stored as note names (strings)
                    pitches = []
                    for note in notes:
                        note_name = note['note']
                        if isinstance(note_name, str):
                            pitch = self._note_to_pitch(note_name)
                        else:
                            pitch = note_name  # Fallback if it's already a number
                        pitches.append(pitch)
                    
                    if not pitches:
                        print(f"  ⚠️  No valid pitches found in channel {channel}")
                        continue
                        
                    pitch_range = max(pitches) - min(pitches)
                    
                    # Choose strategy based on pitch range and number of splits
                    if pitch_range > 24 and num_splits >= 2:  # Large pitch range
                        strategy = 'bass_split'
                        print(f"  Using bass/melody split strategy (pitch range: {pitch_range} semitones)")
                    else:
                        strategy = 'pitch_priority'
                        print(f"  Using pitch priority strategy")
                    
                    split_tracks = self.split_polyphonic_channel(notes, num_splits, strategy)
                    
                    print(f"  Split result: {len(split_tracks)} tracks created")
                    for i, track in enumerate(split_tracks):
                        print(f"  → Track {i+1}: {len(track)} notes")
                        if track:  # Only add non-empty tracks
                            final_lines.append(track)
                            print(f"    Added to final_lines")
                        else:
                            print(f"    Skipped (empty)")
                else:
                    # No splitting requested for this channel
                    final_lines.append(channel_notes[channel])
                    print(f"Channel {channel}: {len(channel_notes[channel])} notes (no split)")
        else:
            # No splitting - use original logic
            final_lines = []
            for channel in sorted(channels):
                if channel_notes[channel]:
                    final_lines.append(channel_notes[channel])
                    print(f"Channel {channel}: {len(channel_notes[channel])} notes")
        
        # Create song data
        song_data = {
            'title': Path(midi_file).stem,
            'duration': total_time_ms,
            'lines': final_lines
        }
        
        print(f"\n✅ Final result: {len(final_lines)} piezo lines")
        
        return song_data
    
    def _handle_note_off(self, channel, note, current_time, ticks_per_beat, 
                        current_tempo, active_notes, channel_notes):
        """Handle a note_off event."""
        key = (channel, note)
        if key in active_notes:
            start_ms = active_notes[key]
            end_ms = ticks_to_milliseconds(current_time, ticks_per_beat, current_tempo)
            duration = max(50, end_ms - start_ms)  # Minimum 50ms duration
            
            note_name = midi_note_to_name(note)
            channel_notes[channel].append({
                'note': note_name,
                'start': start_ms,
                'duration': duration
            })
            
            del active_notes[key]
    
    def _limit_polyphony(self, notes, max_polyphony):
        """
        Limit polyphony by keeping only the highest priority notes.
        For piezos, we typically want max_polyphony=1.
        """
        if max_polyphony >= len(notes):
            return notes
        
        # Sort by start time, then by pitch (higher notes first)
        notes.sort(key=lambda x: (x['start'], -self._note_to_pitch(x['note'])))
        
        # Keep track of active notes and their end times
        active = []
        result = []
        
        for note in notes:
            start = note['start']
            end = start + note['duration']
            
            # Remove finished notes
            active = [(n, e) for n, e in active if e > start]
            
            # If we can add this note
            if len(active) < max_polyphony:
                result.append(note)
                active.append((note, end))
            # Otherwise, replace the lowest pitched active note if this one is higher
            elif max_polyphony == 1:
                # For piezos, just take the highest note
                current_pitch = self._note_to_pitch(note['note'])
                active_pitch = self._note_to_pitch(active[0][0]['note'])
                if current_pitch > active_pitch:
                    result.remove(active[0][0])
                    result.append(note)
                    active[0] = (note, end)
        
        return result
    
    def _note_to_pitch(self, note_name):
        """Convert note name to pitch number for comparison."""
        # Simple pitch ordering - could be improved
        note_order = {'C': 0, 'CS': 1, 'D': 2, 'DS': 3, 'E': 4, 'F': 5,
                     'FS': 6, 'G': 7, 'GS': 8, 'A': 9, 'AS': 10, 'B': 11}
        
        if len(note_name) >= 2:
            note = note_name[:2] if note_name[1] == 'S' else note_name[0]
            octave_str = note_name[len(note):]
            try:
                octave = int(octave_str)
                return octave * 12 + note_order.get(note, 0)
            except:
                return 60  # Default to middle C
        return 60
    
    def process_multiple_midis(self, midi_files, max_polyphony=1):
        """
        Process multiple MIDI files and combine into one song.
        Each file becomes one line/channel.
        """
        print(f"Processing {len(midi_files)} MIDI files...")
        
        lines = []
        total_duration = 0
        titles = []
        
        for midi_file in midi_files:
            song_data = self.process_single_midi(midi_file, channels=[0], 
                                               max_polyphony=max_polyphony)
            if song_data and song_data['lines']:
                lines.append(song_data['lines'][0])  # Take first (and likely only) line
                total_duration = max(total_duration, song_data['duration'])
                titles.append(song_data['title'])
        
        return {
            'title': ' + '.join(titles),
            'duration': total_duration,
            'lines': lines
        }
    
    def save_song(self, song_data, output_file):
        """Save song data to JSON file."""
        # Handle case where output_file has no directory
        output_dir = os.path.dirname(output_file)
        if output_dir:  # Only create directory if there is one
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(song_data, f, indent=2)
        
        print(f"Saved song to: {output_file}")
        print(f"Title: {song_data['title']}")
        print(f"Duration: {song_data['duration']}ms")
        print(f"Lines: {len(song_data['lines'])}")
        for i, line in enumerate(song_data['lines']):
            print(f"  Line {i}: {len(line)} notes")


def main():
    parser = argparse.ArgumentParser(description='Convert MIDI files to JSON for Piezo music player')
    parser.add_argument('midi_files', nargs='+', help='MIDI file(s) to process')
    parser.add_argument('--output', '-o', help='Output JSON file')
    parser.add_argument('--channels', help='Comma-separated channel numbers (e.g., 0,1,2)')
    parser.add_argument('--split', help='Split channels into multiple tracks. Format: "channel:splits,channel:splits" (e.g., "0:3,1:2")')
    parser.add_argument('--max-polyphony', type=int, default=1, 
                       help='Maximum simultaneous notes per channel (default: 1)')
    parser.add_argument('--combine', action='store_true', 
                       help='Combine multiple MIDI files into one song')
    
    # Analysis options
    parser.add_argument('--analyze', '-a', action='store_true',
                       help='Analyze MIDI file(s) and show channel information (text only)')
    parser.add_argument('--preview', '-p', action='store_true',
                       help='Preview MIDI with text analysis (use --plot to add visualization)')
    parser.add_argument('--usage', '-u', action='store_true',
                       help='Show comprehensive usage summary (use --plot for charts)')
    parser.add_argument('--plot', action='store_true',
                       help='Show/save visualization plots (use with --preview or --usage)')
    parser.add_argument('--detailed', action='store_true',
                       help='Show individual notes with labels (for songs with <200 notes)')
    parser.add_argument('--plot-output', help='Save visualization plot to file')
    parser.add_argument('--no-show', action='store_true',
                       help='Save plots but don\'t display them on screen')
    parser.add_argument('--preview-output', help='Custom filename for preview PNG')
    
    args = parser.parse_args()
    
    # If just analyzing or previewing, don't require output file
    if not args.output and not (args.analyze or args.preview or args.usage):
        parser.error("--output is required unless using --analyze, --preview, or --usage")
    
    analyzer = MidiAnalyzer()
    processor = MidiProcessor()
    
    # Analysis mode
    if args.analyze or args.preview or args.usage:
        for midi_file in args.midi_files:
            analysis = analyzer.analyze_midi_file(midi_file)
            if not analysis:
                continue
                
            if args.usage:
                # Always show text analysis
                analyzer.print_analysis(analysis)
                
                # Only create plots if --plot is specified
                if args.plot:
                    show_plot = not args.no_show
                    usage_output = args.plot_output
                    if not usage_output:
                        base_name = Path(midi_file).stem
                        usage_output = f"{base_name}_usage_summary.png"
                    
                    if show_plot:
                        analyzer.visualize_usage_summary(analysis, output_file=usage_output)
                    else:
                        analyzer.visualize_usage_summary(analysis, output_file=usage_output)
                        
            elif args.preview:
                # Handle preview - plotting is optional
                show_plot = args.plot and not args.no_show
                save_plot = args.plot
                preview_output = args.preview_output or args.plot_output
                
                if args.plot and not preview_output:
                    base_name = Path(midi_file).stem
                    suffix = "_detailed_preview" if args.detailed else "_preview"
                    preview_output = f"{base_name}{suffix}.png"
                
                # Always show text analysis first
                analyzer.quick_preview(midi_file, 
                                     show_plot=False, 
                                     save_plot=False,
                                     plot_output=None)
                
                # Then add plot if requested
                if args.plot:
                    if args.detailed:
                        if show_plot:
                            analyzer.visualize_individual_notes(analysis, output_file=preview_output)
                        else:
                            analyzer.visualize_individual_notes(analysis, output_file=preview_output)
                    else:
                        if show_plot:
                            analyzer.visualize_channels(analysis, output_file=preview_output)
                        else:
                            analyzer.visualize_channels(analysis, output_file=preview_output)
                                     
            else:  # args.analyze
                # Always show text analysis
                analyzer.print_analysis(analysis)
                
                # Only create plots if --plot is specified
                if args.plot:
                    show_plot = not args.no_show
                    plot_output = args.plot_output
                    if not plot_output:
                        base_name = Path(midi_file).stem
                        suffix = "_detailed" if args.detailed else "_channels"
                        plot_output = f"{base_name}{suffix}.png"
                    
                    # Choose visualization method
                    if args.detailed:
                        if show_plot:
                            analyzer.visualize_individual_notes(analysis, output_file=plot_output)
                        else:
                            analyzer.visualize_individual_notes(analysis, output_file=plot_output)
                    else:
                        if show_plot:
                            analyzer.visualize_channels(analysis, output_file=plot_output)
                        else:
                            analyzer.visualize_channels(analysis, output_file=plot_output)
        
        # If only analyzing, don't process
        if not args.output:
            return
    
    # Processing mode
    if len(args.midi_files) == 1 and not args.combine:
        # Single MIDI file
        channels = None
        if args.channels:
            channels = [int(c.strip()) for c in args.channels.split(',')]
        
        # Parse split channels
        split_channels = None
        if args.split:
            print(f"🔧 Parsing split argument: '{args.split}'")
            split_channels = {}
            try:
                for split_spec in args.split.split(','):
                    channel_str, splits_str = split_spec.split(':')
                    channel = int(channel_str.strip())
                    splits = int(splits_str.strip())
                    if splits < 2:
                        print(f"⚠️  Warning: Split count must be >= 2, got {splits} for channel {channel}")
                        continue
                    split_channels[channel] = splits
                    print(f"📝 Will split channel {channel} into {splits} tracks")
                print(f"✅ Split channels configured: {split_channels}")
            except ValueError as e:
                print(f"❌ Error parsing split argument: {e}")
                print("   Format should be: --split '0:3,1:2' (split channel 0 into 3, channel 1 into 2)")
                return
        else:
            print("ℹ️  No split argument provided")
        
        song_data = processor.process_single_midi(
            args.midi_files[0], 
            channels=channels, 
            max_polyphony=args.max_polyphony,
            split_channels=split_channels
        )
    else:
        # Multiple MIDI files
        song_data = processor.process_multiple_midis(
            args.midi_files, 
            max_polyphony=args.max_polyphony
        )
    
    if song_data and args.output:
        processor.save_song(song_data, args.output)
    elif not song_data:
        print("Failed to process MIDI file(s)")


if __name__ == '__main__':
    main()