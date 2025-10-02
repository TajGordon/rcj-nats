import serial
import time

def monitor_pico():
    """Monitor Pico output with better error handling"""
    
    print("🎵 Monitoring Pico Music System...")
    print("=" * 50)
    
    # Try multiple times to connect
    for attempt in range(5):
        try:
            ser = serial.Serial('COM8', 115200, timeout=1)
            print(f"✅ Connected to Pico (attempt {attempt + 1})")
            break
        except serial.SerialException as e:
            print(f"❌ Attempt {attempt + 1} failed: {e}")
            if attempt < 4:
                print("   Waiting 2 seconds...")
                time.sleep(2)
            else:
                print("❌ Could not connect after 5 attempts")
                print("💡 Try:")
                print("   1. Unplug and replug Pico USB")
                print("   2. Close any other serial connections")
                print("   3. Check if another program is using COM8")
                return
    
    try:
        # Send Ctrl+D to restart
        print("🔄 Sending restart signal...")
        ser.write(b'\x04')  # Ctrl+D
        time.sleep(1)
        
        # Monitor for 30 seconds
        print("📺 Monitoring output (30 seconds):")
        print("-" * 50)
        
        start_time = time.time()
        last_heartbeat = start_time
        
        while time.time() - start_time < 30:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore') 
                print(data, end='')
                last_heartbeat = time.time()
            
            # Show we're still monitoring if no output for 5 seconds
            if time.time() - last_heartbeat > 5:
                print(f"[{int(time.time() - start_time)}s] Still monitoring...")
                last_heartbeat = time.time()
            
            time.sleep(0.1)
        
        print("\n" + "-" * 50)
        print("✅ Monitoring complete")
        
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")
    except Exception as e:
        print(f"\n❌ Error during monitoring: {e}")
    finally:
        try:
            ser.close()
        except:
            pass

if __name__ == "__main__":
    monitor_pico()