import serial
import time

# Connect and force restart
try:
    ser = serial.Serial('COM8', 115200, timeout=1)
    print("Connected to Pico")
    
    # Send Ctrl+D to force reload
    print("Sending Ctrl+D to reload...")
    ser.write(b'\x04')  # Ctrl+D
    time.sleep(1)
    
    # Monitor output for 10 seconds
    print("Monitoring output:")
    print("-" * 30)
    
    start_time = time.time()
    while time.time() - start_time < 10:
        if ser.in_waiting:
            data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            print(data, end='')
        time.sleep(0.1)
    
    print("\n" + "-" * 30)
    ser.close()

except Exception as e:
    print(f"Error: {e}")
    print("Try:")
    print("1. Unplug and replug Pico USB")
    print("2. Press the BOOTSEL button while plugging in")
    print("3. Check if D: drive is still visible")