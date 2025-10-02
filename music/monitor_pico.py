import serial
import time

# Monitor Pico output
try:
    ser = serial.Serial('COM8', 115200, timeout=1)
    print("🔍 Monitoring Pico output...")
    print("=" * 50)
    
    start_time = time.time()
    
    while time.time() - start_time < 15:  # Monitor for 15 seconds
        if ser.in_waiting:
            data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            print(data, end='')
        time.sleep(0.1)
    
    print("\n" + "=" * 50)
    print("Monitoring complete")
    ser.close()

except Exception as e:
    print(f"Error: {e}")