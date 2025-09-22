import config
from tof import ToF
from imu import IMU

class Localizer:
    def __init__(self, i2c):
        self.tofs = []
        self.angles = [] # used to key for distances
        self.distances = {} # angle -> distance
        
        # get angle from the imu, just call 'cur_angle()'
        self.imu = IMU(i2c=i2c)

        self.best_guess = None
        self.best_error = float('inf')
        
        for addr in config.tof_addrs:
            self.tofs.append(ToF(addr=addr, offset=config.tof_offsets[addr], angle=config.tof_angles[addr], i2c=i2c))
            self.angles.append(self.tofs[-1].angle)
            self.distances[self.angles[-1]] = 0 # default value
    
    def _update_distances(self):
        for tof in self.tofs:
            dist = tof.next_dist()
            self.distances[tof.angle] = dist
    
    def _cast_rays(self, position):
        # goes through each angle and computes the raycast
        # 
        pass
        
    def _compute_error(self, position):
        # simple error function, can be pulled out to create more complex ones
        error = 0

        
    def localize(self):
        self._update_distances() # update to start the localization with accurate distances