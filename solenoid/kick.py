import board
import digitalio
import time

relay = digitalio.DigitalInOut(board.D16)
# relay.direction = digitalio.Direction.OUTPUT
relay.switch_to_output(value=False, drive_mode=digitalio.DriveMode.PUSH_PULL)

relay.value = True # don't kick

def kick():
    relay.value = False
    time.sleep(0.15)
    relay.value = True

if __name__ == "__main__": 
    kick()
