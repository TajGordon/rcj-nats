from dataclasses import dataclass
from typing import Optional, List, Dict
import struct
import config

READ_REG = 0x10

@dataclass
class ToFReading:
    address: int
    distance_mm: int
    angle_rad: Optional[float]
    is_valid: bool = True

@dataclass 
class ToFReadings:
    addresses: List
    valid: Dict[int, bool]
    distances: Dict[int, int]

class ToF:
    def __init__(self, i2c, address, angle, offset):
        self.i2c = i2c
        self.address = address
        self.angle = angle
        self.offset = offset
        
        # storing the data
        self.last_distance = 0
        self.last_sequence = None # the actual sequence / reading from the tof
        self.is_valid = True

        # some filter params
        self.max_distance = config.tof_max_distance - self.offset # subtract offset to get it normalized to from the centre

    def _filter_distance(self, raw_distance):
        # checks if the actual value given is possible, 
        # can add more advanced like sudden change in distance
        if raw_distance > self.max_distance or raw_distance <= 0:
            return raw_distance + self.offset, False
        else:
            return raw_distance + self.offset, True

    def _read(self, fresh: bool):
        write_buf = bytes([READ_REG])
        read_buf = bytearray(5)
        while True:
            self.i2c.writeto(self.address, write_buf)
            self.i2c.readfrom_into(self.address, read_buf)
            seq = read_buf[0]
            distance = struct.unpack('<i', read_buf[1:5])[0]
            if fresh or (self.last_sequence == None) or (seq != self.last_sequence):
                distance, is_valid = self._filter_distance(distance)
                self.last_distance = distance
                self.is_valid = is_valid
                return distance, is_valid

    def w_read(self, fresh: bool):
        write_buf = bytes([READ_REG])
        read_buf = bytearray(5)
        while True:
            self.i2c.writeto(self.address, write_buf)
            self.i2c.readfrom_into(self.address, read_buf)
            seq = read_buf[0]
            raw_distance = struct.unpack('<i', read_buf[1:5])[0]
            if (not fresh) or (self.last_sequence = None) or (seq != self.last_sequence):
                self.last_sequence = seq


class ToFManager:
    def __init__(self, i2c):
        self.i2c = i2c
        self.addresses = []
        self.tofs = []
        self.tof_count = 0

        self.tof_distances = {}
        self.tof_valid = {}

    def _get_ToFReadingsClass(self):
        return ToFReadings(addresses=self.addresses, valid=self.tof_valid, distances=self.tof_distances)

    # OOPs!
    def _setup_tofs(self, tof_addresses, tof_angles, tof_offsets):
        for addr in tof_addresses:
            tof = ToF(self.i2c, addr, tof_angles[addr], tof_offsets[addr])
            self.tofs.append(tof)
            self.addresses.append(addr)
            self.tof_valid[addr] = True
            self.tof_count += 1

    def _update_readings(self, fresh):
        for tof in self.tofs:
            dist, valid = tof.get_reading(fresh=fresh)
            self.tof_distances[tof.address] = dist
            self.tof_valid[tof.address] = valid

    def get_fresh_readings(self):
        self._update_readings(True)
        return self._get_ToFReadingsClass()

    def get_reading(self):
        self._update_readings(False)
        return self._get_ToFReadingsClass()


    


