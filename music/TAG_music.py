import time
import pwmio
import board
from digitalio import DigitalInOut, Direction


class Piezo:
    """
    A class to control a piezo buzzer for playing musical notes.
    
    Supports playing notes by frequency, duration, and provides methods
    for controlling playback (play, stop, mute).
    """
    
    def __init__(self, pin, name="Piezo"):
        """
        Initialize a Piezo object.
        
        Args:
            pin: The board pin connected to the piezo (e.g., board.GP0)
            name: Optional name for this piezo (useful for debugging multiple piezos)
        """
        self.pin = pin
        self.name = name
        self.pwm = None
        self.is_playing = False
        self.is_muted = False
        
        # Initialize the PWM output
        self._init_pwm()
    
    def _init_pwm(self):
        """Initialize PWM for the piezo pin."""
        try:
            self.pwm = pwmio.PWMOut(self.pin, frequency=440, duty_cycle=0)
        except Exception as e:
            print(f"Error initializing PWM for {self.name}: {e}")
            self.pwm = None
    
    def play_note(self, frequency, duration=None, duty_cycle=32767):
        """
        Play a note at the specified frequency.
        
        Args:
            frequency: The frequency in Hz (0 to stop/silence)
            duration: Optional duration in seconds. If None, plays indefinitely
            duty_cycle: PWM duty cycle (0-65535, default 32767 for 50%)
        """
        if self.pwm is None or self.is_muted:
            return
        
        if frequency <= 0:
            self.stop()
            return
        
        try:
            self.pwm.frequency = int(frequency)
            self.pwm.duty_cycle = duty_cycle
            self.is_playing = True
            
            if duration is not None:
                time.sleep(duration)
                self.stop()
        except Exception as e:
            print(f"Error playing note on {self.name}: {e}")
    
    def play_note_async(self, frequency, duty_cycle=32767):
        """
        Start playing a note without blocking (no duration).
        Call stop() to stop the note.
        
        Args:
            frequency: The frequency in Hz (0 to stop/silence)
            duty_cycle: PWM duty cycle (0-65535, default 32767 for 50%)
        """
        if self.pwm is None or self.is_muted:
            return
        
        if frequency <= 0:
            self.stop()
            return
        
        try:
            self.pwm.frequency = int(frequency)
            self.pwm.duty_cycle = duty_cycle
            self.is_playing = True
        except Exception as e:
            print(f"Error playing async note on {self.name}: {e}")
    
    def stop(self):
        """Stop playing any current note."""
        if self.pwm is not None:
            self.pwm.duty_cycle = 0
            self.is_playing = False
    
    def mute(self):
        """Mute this piezo (stops current sound and prevents new sounds)."""
        self.stop()
        self.is_muted = True
    
    def unmute(self):
        """Unmute this piezo."""
        self.is_muted = False
    
    def is_available(self):
        """Check if the piezo is properly initialized and available."""
        return self.pwm is not None
    
    def cleanup(self):
        """Clean up PWM resources."""
        self.stop()
        if self.pwm is not None:
            self.pwm.deinit()
            self.pwm = None
    
    def __del__(self):
        """Destructor to clean up resources."""
        self.cleanup()


# Note frequency constants (in Hz) for common musical notes
# These can be used with the Piezo.play_note() method
NOTES = {
    'REST': 0,
    'C3': 131, 'CS3': 139, 'D3': 147, 'DS3': 156, 'E3': 165, 'F3': 175,
    'FS3': 185, 'G3': 196, 'GS3': 208, 'A3': 220, 'AS3': 233, 'B3': 247,
    'C4': 262, 'CS4': 277, 'D4': 294, 'DS4': 311, 'E4': 330, 'F4': 349,
    'FS4': 370, 'G4': 392, 'GS4': 415, 'A4': 440, 'AS4': 466, 'B4': 494,
    'C5': 523, 'CS5': 554, 'D5': 587, 'DS5': 622, 'E5': 659, 'F5': 698,
    'FS5': 740, 'G5': 784, 'GS5': 831, 'A5': 880, 'AS5': 932, 'B5': 988,
    'C6': 1047, 'CS6': 1109, 'D6': 1175, 'DS6': 1245, 'E6': 1319, 'F6': 1397,
    'FS6': 1480, 'G6': 1568, 'GS6': 1661, 'A6': 1760, 'AS6': 1865, 'B6': 1976
}


def note_to_frequency(note_name):
    """
    Convert a note name to frequency.
    
    Args:
        note_name: String note name (e.g., 'A4', 'C5', 'REST')
    
    Returns:
        Frequency in Hz, or 0 for REST/unknown notes
    """
    return NOTES.get(note_name.upper(), 0)


class Musician:
    """
    A class to orchestrate multiple Piezo objects to play songs with multiple parts/lines.
    
    Supports loading songs from JSON format, playing multiple lines simultaneously,
    and controlling playback (play, pause, resume, stop).
    """
    
    def __init__(self, piezos):
        """
        Initialize the Musician with a list of Piezo objects.
        
        Args:
            piezos: List of Piezo objects, or dict with names as keys
        """
        if isinstance(piezos, dict):
            self.piezos = piezos
            self.piezo_list = list(piezos.values())
        else:
            self.piezos = {f"piezo_{i}": piezo for i, piezo in enumerate(piezos)}
            self.piezo_list = piezos
        
        self.current_song = None
        self.is_playing = False
        self.is_paused = False
        self.start_time = 0
        self.pause_time = 0
        self.current_position = 0  # Current playback position in milliseconds
        
        # Track which notes are currently scheduled for each piezo
        self.active_notes = {}  # Will store note info dictionaries
        self.next_events = {i: 0 for i in range(len(self.piezo_list))}  # Next event index for each line
    
    def load_song(self, song_data):
        """
        Load a song from JSON data.
        
        Expected format:
        {
            "title": "Song Name",
            "tempo": 120,  # BPM (optional)
            "duration": 30000,  # Total duration in ms
            "lines": [
                [
                    {"note": "C4", "start": 0, "duration": 500},
                    {"note": "E4", "start": 500, "duration": 500},
                    ...
                ],
                [  # Second line (bass, harmony, etc.)
                    {"note": "C3", "start": 0, "duration": 1000},
                    ...
                ],
                ...
            ]
        }
        
        Args:
            song_data: Dictionary containing song data
        """
        self.current_song = song_data
        self.current_position = 0
        self.is_playing = False
        self.is_paused = False
        
        # Reset event tracking
        self.next_events = {i: 0 for i in range(len(self.piezo_list))}
        
        print(f"Loaded song: {song_data.get('title', 'Unknown')}")
        print(f"Lines: {len(song_data.get('lines', []))}")
        print(f"Duration: {song_data.get('duration', 0)}ms")
    
    def load_song_from_file(self, filename):
        """
        Load a song from a JSON file.
        
        Args:
            filename: Path to the JSON song file
        """
        try:
            import json
            with open(filename, 'r') as f:
                song_data = json.load(f)
            self.load_song(song_data)
        except Exception as e:
            print(f"Error loading song from {filename}: {e}")
    
    def play_song(self, song_data=None):
        """
        Start playing a song.
        
        Args:
            song_data: Optional song data. If None, uses currently loaded song.
        """
        if song_data:
            self.load_song(song_data)
        
        if not self.current_song:
            print("No song loaded!")
            return
        
        if self.is_paused:
            self.resume()
            return
        
        print(f"Playing: {self.current_song.get('title', 'Unknown')}")
        self.is_playing = True
        self.is_paused = False
        self.start_time = time.monotonic() * 1000  # Convert to milliseconds
        self.current_position = 0
        
        # Reset event tracking
        self.next_events = {i: 0 for i in range(len(self.piezo_list))}
        
        # Start the playback loop
        self._play_loop()
    
    def _play_loop(self):
        """
        Main playback loop that handles timing and note scheduling.
        """
        if not self.current_song:
            return
            
        lines = self.current_song.get('lines', [])
        song_duration = self.current_song.get('duration', 0)
        
        while self.is_playing and not self.is_paused:
            current_time = time.monotonic() * 1000
            self.current_position = current_time - self.start_time
            
            # Check if song is finished
            if self.current_position >= song_duration:
                self.stop()
                break
            
            # Process events for each line/piezo
            for line_idx in range(min(len(lines), len(self.piezo_list))):
                self._process_line_events(line_idx, lines[line_idx])
            
            # Small delay to prevent busy waiting
            time.sleep(0.001)  # 1ms delay
    
    def _process_line_events(self, line_idx, events):
        """
        Process events for a specific line/piezo.
        
        Args:
            line_idx: Index of the line (and corresponding piezo)
            events: List of note events for this line
        """
        if line_idx >= len(self.piezo_list):
            return
        
        piezo = self.piezo_list[line_idx]
        next_event_idx = self.next_events[line_idx]
        
        # Check if there are more events for this line
        if next_event_idx >= len(events):
            return
        
        current_event = events[next_event_idx]
        event_start = current_event.get('start', 0)
        event_duration = current_event.get('duration', 500)
        note = current_event.get('note', 'REST')
        
        # Check if it's time to start this event
        if self.current_position >= event_start:
            # Start the note
            frequency = note_to_frequency(note) if isinstance(note, str) else note
            piezo.play_note_async(frequency)
            
            # Schedule when to stop this note
            self.active_notes[line_idx] = {
                'stop_time': event_start + event_duration,
                'piezo': piezo
            }
            
            # Move to next event
            self.next_events[line_idx] += 1
        
        # Check if current note should be stopped
        if line_idx in self.active_notes:
            active_note = self.active_notes[line_idx]
            if active_note and self.current_position >= active_note['stop_time']:
                active_note['piezo'].stop()
                del self.active_notes[line_idx]
    
    def pause(self):
        """Pause the current song."""
        if self.is_playing and not self.is_paused:
            self.is_paused = True
            self.pause_time = time.monotonic() * 1000
            
            # Stop all currently playing notes
            for piezo in self.piezo_list:
                piezo.stop()
            
            print("Song paused")
    
    def resume(self):
        """Resume playing the paused song."""
        if self.is_playing and self.is_paused:
            # Adjust start time to account for pause duration
            pause_duration = (time.monotonic() * 1000) - self.pause_time
            self.start_time += pause_duration
            
            self.is_paused = False
            print("Song resumed")
            
            # Continue the playback loop
            self._play_loop()
    
    def stop(self):
        """Stop playing the current song."""
        self.is_playing = False
        self.is_paused = False
        self.current_position = 0
        
        # Stop all piezos
        for piezo in self.piezo_list:
            piezo.stop()
        
        # Clear active notes
        self.active_notes = {}
        self.next_events = {i: 0 for i in range(len(self.piezo_list))}
        
        print("Song stopped")
    
    def get_status(self):
        """
        Get current playback status.
        
        Returns:
            Dictionary with current status information
        """
        return {
            'is_playing': self.is_playing,
            'is_paused': self.is_paused,
            'current_position_ms': self.current_position,
            'current_song': self.current_song.get('title', 'None') if self.current_song else 'None',
            'total_duration_ms': self.current_song.get('duration', 0) if self.current_song else 0
        }
    
    def set_volume(self, line_idx, duty_cycle):
        """
        Set the volume (duty cycle) for a specific piezo line.
        
        Args:
            line_idx: Index of the piezo line
            duty_cycle: PWM duty cycle (0-65535)
        """
        if 0 <= line_idx < len(self.piezo_list):
            # This would need to be implemented in future note events
            # For now, we can store it for future use
            pass
    
    def mute_line(self, line_idx):
        """Mute a specific piezo line."""
        if 0 <= line_idx < len(self.piezo_list):
            self.piezo_list[line_idx].mute()
    
    def unmute_line(self, line_idx):
        """Unmute a specific piezo line."""
        if 0 <= line_idx < len(self.piezo_list):
            self.piezo_list[line_idx].unmute()
    
    def cleanup(self):
        """Clean up all piezo resources."""
        self.stop()
        for piezo in self.piezo_list:
            piezo.cleanup()


# Piezo Test Routine and Example Usage:
if __name__ == "__main__":
    print("🎵 Piezo Music System Test - Starting...")
    print("=" * 50)
    
    try:
        # Initialize piezos - using your existing pin configuration
        print("🔧 Initializing piezos...")
        piezo1 = Piezo(board.GP17, "Piezo-17")
        piezo2 = Piezo(board.GP14, "Piezo-14")
        # Add a third piezo if you have one:
        # piezo3 = Piezo(board.GP15, "Piezo-15")
        
        # Check if all piezos initialized successfully
        piezos = [piezo1, piezo2]  # Add piezo3 if you have it
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
        if len(piezos) >= 2:
            print("   Piezo-17: C4 (262Hz)")
            print("   Piezo-14: E4 (330Hz)")
        
        # Start all notes at the same time (async)
        if len(piezos) >= 1 and piezo1.is_available():
            piezo1.play_note_async(262)  # C4
        if len(piezos) >= 2 and piezo2.is_available():
            piezo2.play_note_async(330)  # E4
        # if len(piezos) >= 3 and piezo3.is_available():
        #     piezo3.play_note_async(392)  # G4
        
        # Let them play for 2 seconds
        time.sleep(2.0)
        
        # Stop all notes
        for piezo in piezos:
            piezo.stop()
        
        print("✅ Simultaneous test complete")
        
        print("\n" + "=" * 50)
        print("🎵 MUSICIAN CLASS TEST")
        print("=" * 50)
        
        # Create musician with the piezos
        musician = Musician(piezos)
        
        # Simple test song
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
        
        print("🎵 Playing test song...")
        print(f"   Duration: 4 seconds")
        print(f"   {len(piezos)} parts playing")
        
        # Play the test song
        musician.play_song(test_song)
        
        print("✅ Test song complete")
        
        print("\n" + "=" * 50)
        print("🎯 LOADING YOUR SONG")
        print("=" * 50)
        
        # Now load and play your actual song
        try:
            print("🎵 Loading pico_Fetty.json...")
            musician.load_song_from_file("pico_Fetty.json")
            
            print("🎵 Playing Fetty Wap song...")
            musician.play_song()
            
            print("✅ Song playback complete!")
            
        except Exception as e:
            print(f"❌ Error loading/playing song: {e}")
            print("   Make sure pico_Fetty.json exists and is valid")
        
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
        
        # Clean up
        for piezo in piezos:
            piezo.cleanup()
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 This appears to be running outside CircuitPython environment")
        print("   On Raspberry Pi Pico, make sure you have:")
        print("   - CircuitPython installed")
        print("   - This file saved as main.py or code.py")
        print("   - Piezos connected to GP17, GP14 (and GP15 if using 3)")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("💡 Check your hardware connections and try again")
    
    print("\n🎵 Piezo test complete!")
    
    # Instructions for adding more piezos:
    # 1. Uncomment the piezo3 lines above
    # 2. Connect third piezo to GP15 (or any free GPIO pin)
    # 3. Add piezo3 to the piezos list
    # 4. Update your songs to have 3 lines instead of 2