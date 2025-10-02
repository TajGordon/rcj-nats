from dataclasses import dataclass
from tof import ToFManager, ToF, ToFReading


@dataclass
class Pose:
    angle: float
    x: float   
    y: float

class Localization:
    def __init__(self, i2c):
        self.latest_estimate = Pose(angle=0, x=0, y=0)
        self.tof = ToF()

    def estimate_position(self):
        pass
