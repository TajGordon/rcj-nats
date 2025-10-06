import time
import math
import board
import busio
import tajslib
from adafruit_bno08x import (
    BNO_REPORT_ROTATION_VECTOR,
)

from adafruit_bno08x.i2c import BNO08X_I2C

class IMU:
    def __init__(self, i2c = busio.I2C(board.SCL, board.SDA)):
        self.i2c = i2c
        self.bno = BNO08X_I2C(i2c)
        self.bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)

        # not used, just reads from the IMU over i2c - this is probably fine
        # self.heading = 0.0
        # radianss
        # self.angle = 0.0 <-- not used right now
        # offset, to make the initialised direction 0.0
        time.sleep(0.04) # delay to make sure the IMU is initialized
        i, j, k, w = self.bno.quaternion  # type: ignore[reportAttributeAccessIssue]
        self.angle_offset = -(math.atan2(2*(w*k + i*j), 1 - 2 * (j*j + k*k)))
        self.raw_angle = 0

    def reset_heading(self):
        self.angle_offset = -self._get_angle()

    def _get_angle(self):
        # formula courtesy of chatgpt - i'll derive myself later, but it feels like solving using full matrix expansion would be tedious
        i, j, k, w = self._read_quat()
        self.raw_angle = math.atan2(2*(w*k + i*j), 1 - 2 * (j*j + k*k))
        return self.raw_angle

    def _read_quat(self):
        i, j, k, w = self.bno.quaternion # type: ignore[reportAttributeAccessIssue]
        return i,j,k,w
    
    def cur_angle(self):
        return tajslib.add_radians(self._get_angle(), self.angle_offset)


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
    sra = st.metric(label='Raw Angle', value="0.0 °")
    
    from collections import deque
    delta_points = deque(maxlen=1000)
    angle_points = deque(maxlen=1000)
    raw_angle_points = deque(maxlen=1000)

    delta_placeholder = st.line_chart(delta_points)
    raw_angle_placeholder = st.line_chart(raw_angle_points)
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
        raw_angle = imu._get_angle()
        cur_angle = imu.cur_angle()
        delta_angle = get_diff(cur_angle, previous_angle)
        sa.metric(label="Angle", value=f"{math.degrees(cur_angle):.2f} °", delta=f"{math.degrees(delta_angle):.2f} °")
        sra.metric(label="Raw Angle", value=f"{math.degrees(raw_angle):.2f} °")
        previous_angle = cur_angle
        
        delta_points.append(math.degrees(delta_angle))
        raw_angle_points.append(math.degrees(raw_angle))
        angle_points.append(math.degrees(cur_angle))
        
        raw_angle_placeholder.line_chart(raw_angle_points)
        angle_placeholder.line_chart(angle_points)
        delta_placeholder.line_chart(delta_points)
