import time
import math
import board
import busio
from adafruit_bno08x import (
    BNO_REPORT_ROTATION_VECTOR,
)

from adafruit_bno08x.i2c import BNO08X_I2C

class IMU:
    def __init__(self, i2c = busio.I2C(board.SCL, board.SDA)):
        # not used, just reads from the IMU over i2c - this is probably fine
        # self.heading = 0.0
        # radianss
        self.angle = 0.0

        self.i2c = i2c
        self.bno = BNO08X_I2C(i2c)
        self.bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)

    def _get_angle(self):
        # formula courtesy of chatgpt - i'll derive myself later, but it feels like solving using full matrix expansion would be tedious
        i, j, k, w = self._read_quat()
        yaw = math.atan2(2*(w*k + i*j), 1 - 2 * (j*j + k*k))
        return yaw

    def _read_quat(self):
        i, j, k, w = self.bno.quaternion # type: ignore[reportAttributeAccessIssue]
        return i,j,k,w



# test code
if __name__ == "__main__":
    # streamlit setup
    import streamlit as st
    st.title('IMU Data')
    col1, col2, col3, col4 = st.columns(4)
    si = col1.metric("I", 0)
    sj = col2.metric("J", 0)
    sk = col3.metric("K", 0)
    sw = col4.metric("W", 0)
    
    sa = st.metric(label='Angle', value="0.0 °", delta="0.0 °")
    
    from collections import deque
    delta_points = deque(maxlen=1000)
    angle_points = deque(maxlen=1000)

    delta_placeholder = st.line_chart(delta_points)
    angle_placeholder = st.line_chart(angle_points)
    
    def get_diff(a, b):
        dif = a - b
        while dif > math.pi:
            dif -= 2 * math.pi
        while dif < -math.pi:
            dif += 2 * math.pi
        return dif

    # imu setup
    imu = IMU()
    previous_angle = 0.0
    while True:
        # the raw quat stuff
        i, j, k, w = imu._read_quat()
        si.metric('I', i)
        sj.metric('J', j)
        sk.metric('K', k)
        sw.metric('W', w)
        
        # the angle
        angle = imu._get_angle()
        delta_angle = get_diff(angle, previous_angle)
        sa.metric(label="Angle", value=f"{math.degrees(angle):.2f} °", delta=f"{math.degrees(delta_angle):.2f} °")
        previous_angle = angle
        
        delta_points.append(math.degrees(delta_angle))
        angle_points.append(math.degrees(angle))
        
        angle_placeholder.line_chart(angle_points)
        delta_placeholder.line_chart(delta_points)
