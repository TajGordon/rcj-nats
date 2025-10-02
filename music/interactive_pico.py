import serial
import time

try:
    ser = serial.Serial('COM8', 115200, timeout=1)
    print("Connected! Now you can type commands.")
    print("Commands to try:")
    print("  Ctrl+C - interrupt")
    print("  Ctrl+D - reload") 
    print("  help() - show help")
    print("  import board; print(dir(board)) - show pins")
    print("\nType 'quit' to exit this program")
    print("-" * 40)
    
    # Interactive mode
    while True:
        # Check for input from Pico
        if ser.in_waiting:
            data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
            print(data, end='')
        
        # Simple way to exit
        if input() == 'quit':
            break
        
        time.sleep(0.1)
    
    ser.close()

except KeyboardInterrupt:
    print("\nExiting...")
    ser.close()
except Exception as e:
    print(f"Error: {e}")