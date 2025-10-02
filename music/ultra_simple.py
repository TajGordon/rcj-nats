# ultra_simple.py - Absolute minimum test
print("HELLO FROM PICO!")
print("Testing basic functionality...")

import time
count = 0

while count < 10:
    print(f"Count: {count}")
    time.sleep(1)
    count += 1

print("Basic test complete!")