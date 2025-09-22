import time
import board
import busio

# magical number!
READ_REG = 0x10

class ToF:
    def __init__(self, addr, offset, angle, i2c = busio.I2C(board.SCL, board.SDA)):
        self.i2c = i2c
        self.addr = addr
        
        self.offset = offset
        self.angle = angle

        # TODO! set to use data from config.py
        self.max_distance = 1000
        self.min_distance = 10

        self.last_seq = None
        self.last_distance = 0
        
    def _read(self, wait):
        write_buf = bytes([(READ_REG)])
        read_buf = bytearray(5)
        while True:
            self.i2c.writeto(self.addr, write_buf)
            self.i2c.readfrom_into(self.addr, read_buf)

            seq = read_buf[0]
            changed = seq != self.last_seq # check if this is a new datapoint - hopefully works fine on None
            # shift the bytes to re-form the integer
            distance = (read_buf[1] | read_buf[2] << 8 | read_buf[3] << 16 | read_buf[4] << 24)

            # if its not changed, and we want a fresh datapoint, don't return
            if changed or not wait:
                self.last_seq = seq
                # if the distance is invalid, return the previous distance
                if distance <= self.max_distance and distance >= self.min_distance:
                    self.last_distance = distance
                return self.last_distance
            # hopefully equivalent to 10 microseconds, but oh well
            time.sleep(0.00001)
    
    def next_dist(self):
        return self._read(wait=True)

    def cur_dist(self):
        return self._read(wait=False)
    

# test code!
if __name__ == "__main__":
    print('no performance benchmarks done; i hope this isn\'t stupidly slow.')
    n = int(input("Enter the number of ToFs you would like to test\n"))
    tof_addrs = []
    for i in range(n):
        addr = int(input(f'What is the address of ToF {i}?\n'))
        tof_addrs.append(addr)
    tofs = []
    i2c = busio.I2C(board.SCL, board.SDA)
    for i in range(n):
        tofs.append(ToF(addr=tof_addrs[i], i2c=i2c))
    
    # TODO! implement the rendering of the data
    import streamlit as st
    st.title('ToF Data')
    cols = st.columns(n)
    tof_sts = [cols[i].metric(label=f"{hex(tof_addrs[i])}", value=0) for i in range(n)]
    
    print("Starting readings")
    while True:
        for i in range(n):
            tof = tofs[i]
            dist = tof.next_dist()
            tof_sts[i].metric(label=f"{hex(tof_addrs[i])}", value=dist)