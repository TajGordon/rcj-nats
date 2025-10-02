# 🎵 Raspberry Pi Pico Piezo Music System Setup Guide

## 📋 **What You Need**

### Hardware:
- Raspberry Pi Pico with CircuitPython installed
- 2-3 Piezo buzzers
- Jumper wires
- Breadboard (optional)

### Software Files (copy to Pico):
1. `piezo_music.py` - The main classes
2. `code.py` - Auto-runs the test routine  
3. `test_song.json` - Simple test song
4. `pico_Fetty.json` - Your Fetty Wap song

## 🔌 **Hardware Connections**

Connect your piezos to these GPIO pins:
- **Piezo 1**: GP17 (Physical pin 22)
- **Piezo 2**: GP14 (Physical pin 19)  
- **Piezo 3**: GP15 (Physical pin 20) - Optional third piezo

**Connection Diagram:**
```
Pico Pin    GPIO    Piezo Connection
--------    ----    ----------------
Pin 22  ->  GP17 -> Piezo 1 (+)
Pin 19  ->  GP14 -> Piezo 2 (+)
Pin 20  ->  GP15 -> Piezo 3 (+) [Optional]
Pin 38  ->  GND  -> All Piezos (-)
```

## 💾 **File Setup on Pico**

### Method 1: Copy Files Directly
1. Connect Pico to computer via USB
2. Pico should appear as a USB drive (CIRCUITPY)
3. Copy these files to the **root directory** of the Pico:
   - `piezo_music.py`
   - `code.py` 
   - `test_song.json`
   - `pico_Fetty.json`

### Method 2: Using Thonny IDE
1. Open Thonny IDE
2. Set interpreter to CircuitPython (Raspberry Pi Pico)
3. Upload files using File -> Save to MicroPython device

## 🚀 **How It Works**

### Automatic Startup:
- When you power on/reset the Pico, `code.py` runs automatically
- No need to manually start anything!

### Test Sequence:
1. **Individual Test**: Each piezo buzzes for 1 second
2. **Simultaneous Test**: Plays a chord with both piezos  
3. **System Test**: Plays a 4-second test melody
4. **Your Song**: Attempts to play `pico_Fetty.json`
5. **Status Report**: Shows which piezos are working

## 🔧 **Troubleshooting**

### "Import piezo_music could not be resolved" 
- Make sure `piezo_music.py` is in the **root directory** of the Pico
- File names are case-sensitive

### "Error initializing PWM"
- Check your wiring connections
- Make sure piezos are connected to the right GPIO pins
- Verify ground connections

### "No song file found"
- Ensure JSON files are in the root directory of the Pico
- Check file names match exactly (case-sensitive)

### No sound from piezos:
- Verify piezo polarity (+ to GPIO, - to GND)
- Test with a multimeter if available
- Try different GPIO pins

## 📁 **Expected File Structure on Pico**

```
CIRCUITPY/
├── code.py              # Auto-runs on startup
├── piezo_music.py       # Main classes
├── test_song.json       # Simple test song
├── pico_Fetty.json      # Your Fetty Wap song
└── lib/                 # CircuitPython libraries (if any)
```

## 🎛️ **Using the Serial Console**

To see the output and debug messages:

### Option 1: Thonny IDE
1. Connect Pico via USB
2. Open Thonny
3. Set interpreter to CircuitPython  
4. View output in the Shell tab

### Option 2: PuTTY/Terminal
1. Find the COM port of your Pico
2. Connect at 115200 baud
3. Reset Pico to see startup messages

## 🎵 **What You Should See**

```
🎵 Piezo Music System Test - Starting...
==================================================
🔧 Initializing piezos...
✅ All piezos initialized successfully!

🧪 INDIVIDUAL PIEZO TEST
==================================================
🔊 Testing Piezo-17 - 1 second buzz at 440Hz...
✅ Piezo-17 test complete
🔊 Testing Piezo-14 - 1 second buzz at 440Hz...
✅ Piezo-14 test complete

🎼 SIMULTANEOUS PIEZO TEST
==================================================
🔊 Testing all piezos simultaneously - 2 second chord...
✅ Simultaneous test complete

🎵 MUSICIAN CLASS TEST
==================================================
🎵 Playing test song...
✅ Test song complete

🎯 LOADING YOUR SONG
==================================================
🎵 Looking for pico_Fetty.json...
🎵 Playing Fetty Wap song...
✅ Song playback complete!

🎯 SYSTEM STATUS
==================================================
📊 Working piezos: 2/2
🎉 ALL SYSTEMS GO! Your piezo music system is ready!

🔄 Test complete - will restart in 10 seconds...
```

## ⚙️ **Customization**

### Adding More Piezos:
1. Edit `code.py`, uncomment the `piezo3` lines
2. Connect third piezo to GP15
3. Update your JSON songs to have 3 lines

### Different GPIO Pins:
1. Edit `code.py` and change `board.GP17`, `board.GP14` to your preferred pins
2. Update your wiring accordingly

### Auto-restart Behavior:
- The test runs every 10 seconds automatically
- Press CTRL+C in serial console to stop
- Reset Pico to restart

## 🎯 **Success Indicators**

✅ **All Working**: You hear individual buzzes, then a chord, then melodies  
⚠️ **Partial**: Some piezos work, check connections on non-working ones  
❌ **Nothing**: Check all connections, verify CircuitPython installation

## 📞 **Next Steps**

Once this works on your Pico, the same code structure will work on your Pi 5 with minimal modifications (mainly pin definitions)!