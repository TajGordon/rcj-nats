import time
import board
import busio
import adafruit_bno08x
from adafruit_bno08x.i2c import BNO08X_I2C



class IMU:
    def __init__(self):
        self.heading = 0.0