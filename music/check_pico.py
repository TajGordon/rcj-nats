import serial
import time

# Connect to Pico
try:
    ser = serial.Serial('COM8', 115200, timeout=1)
    print("Connected to Pico on COM8")
    
    # Send Ctrl+C to interrupt
    ser.write(b'\x03')
    time.sleep(0.5)
    
    # Send commands to check file system
    commands = [
        "import os\r\n",
        "print('Files on Pico:')\r\n", 
        "print(os.listdir('/'))\r\n",
        "print('\\nChecking for our files:')\r\n",
        "files_to_check = ['code.py', 'piezo_music.py', 'test_song.json', 'pico_Fetty.json']\r\n",
        "for f in files_to_check:\r\n",
        "    try:\r\n",
        "        with open(f, 'r') as file:\r\n",
        "            print(f'✅ {f} exists ({len(file.read())} bytes)')\r\n",
        "    except:\r\n",
        "        print(f'❌ {f} not found')\r\n"
    ]
    
    for cmd in commands:
        ser.write(cmd.encode())
        time.sleep(0.2)
    
    # Read response
    time.sleep(2)
    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
    print("Pico Response:")
    print(response)
    
    ser.close()
    
except Exception as e:
    print(f"Error connecting to Pico: {e}")
    print("Make sure:")
    print("1. Pico is connected via USB")
    print("2. CircuitPython is installed") 
    print("3. COM8 is the correct port")