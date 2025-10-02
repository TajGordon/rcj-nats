import serial
import time

# Connect to Pico and send the simple test code
try:
    ser = serial.Serial('COM8', 115200, timeout=1)
    print("Connected to Pico...")
    
    # Interrupt current code
    ser.write(b'\x03')  # Ctrl+C
    time.sleep(0.5)
    
    # Check what's currently running
    ser.write(b'print("Current code.py status:")\r\n')
    time.sleep(0.5)
    
    # Try to see the current code.py content (first few lines)
    commands = [
        'with open("code.py", "r") as f:\r\n',
        '    lines = f.readlines()[:10]\r\n', 
        '    print("First 10 lines of code.py:")\r\n',
        '    for i, line in enumerate(lines):\r\n',
        '        print(f"{i+1}: {line.strip()}")\r\n'
    ]
    
    for cmd in commands:
        ser.write(cmd.encode())
        time.sleep(0.1)
    
    # Read response
    time.sleep(2)
    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
    print("Current code.py content:")
    print(response)
    
    ser.close()

except Exception as e:
    print(f"Error: {e}")