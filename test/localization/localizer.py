import config
import board
from tof import ToF
from imu import IMU

import math

class Localizer:
    def __init__(self, i2c = board.I2C(board.SCL, board.SDA), tofs=None, imu=IMU(i2c=board.I2C(board.SCL, board.SDA))):
        self.tofs = tofs if tofs is not None else []
        self.tof_angles = [] # used to key for distances
        self.tof_distances = {} # angle -> distance
        # initialize tofs if not provided, this lets us fake the tofs
        if tofs is None:
            for addr in config.tof_addrs:
                self.tofs.append(ToF(addr=addr, offset=config.tof_offsets[addr], angle=config.tof_angles[addr], i2c=i2c))
                self.tof_angles.append(self.tofs[-1].angle)
                self.tof_distances[self.tof_angles[-1]] = 0 # default value
        
        # get angle from the imu, just call 'cur_angle()'
        self.imu = imu

        # for debug stuff (mainly for simulator)
        if tofs is not None:
            self.tofs = tofs
        if imu is not None:
            self.imu = imu

        self.best_guess = [0, 0] # list because fk python tuples
        self.best_error = float('inf')
        
    
    def _update_distances(self):
        for tof in self.tofs:
            dist = tof.next_dist()
            self.tof_distances[tof.angle] = dist
    
    def _cast_ray(self, position, angle):
        # just stores the distance of the closest one 
        # could be changed to report what wall it hit
        # checks ray intersection of each wall / line
        minimum_distance = float('inf') # stores distance squared
        dx = math.cos(angle)
        dy = math.sin(angle)
        for wall in config.walls: # should be 10 walls
            # TODO! write the code
            if wall['type'] == 'horizontal':
                t = (wall['x'] - position[0])/dx
                if t <= 0:
                    continue
                y = t * dy
                if y < wall['y_min'] or y > wall['y_max']:
                    continue
                x = t * dx
                dist = math.sqrt(x**2 + y**2)
                if dist < minimum_distance:
                    minimum_distance = dist
            else:
                t = (wall['y'] - position[0])/dy
                if t <= 0:
                    continue
                x = t * dx
                if x < wall['x_min'] or x > wall['x_max']:
                    continue
                y = t * dy
                dist = (x**2 + y**2) # store distance squared
                if dist < minimum_distance:
                    minimum_distance = dist
        return minimum_distance
    
    def _cast_rays(self, position, bot_angle):
        # goes through each angle and computes the raycast
        distances = {}
        for angle in self.tof_angles:
            dist = self._cast_ray(position, bot_angle + angle)
            distances[angle] = dist
        return distances

        
    def _compute_error(self, position, bot_angle):
        # simple cumulative error function, can be pulled out to create more complex ones
        # for example, you could take into account whether the tof had a huge difference to its last variation - perhaps a bot is blocking / unblocking it
        error = 0
        raycast_distances = self._cast_rays(position, bot_angle)
        for angle in self.tof_angles:
            diff = abs(raycast_distances[angle] - (self.tof_distances[angle] ** 2)) # square the tof distance to match the squared distance from the raycasting
            error += diff
        return error

        
    def localize(self):
        self._update_distances() # update to start the localization with accurate distances
        
        angle = self.imu.cur_angle() # to not recall a bunch of times
        
        # in mm
        move_amount = 32 # power of two cuz why not
        decay_rate = 0.5
        cutoff = 0.05
        while move_amount > cutoff:
            converged = False
            while not converged:
                converged = True
                # only checks on axis aligned grid instead of relative positions
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        guess_pos = [self.best_guess[0] + move_amount * dx, self.best_guess[1] + move_amount * dy]
                        error = self._compute_error(guess_pos, angle)
                        if error < self.best_error:
                            converged = False
                            self.best_error = error
                            self.best_guess = guess_pos
            move_amount *= decay_rate
        
        # now should be able to just do localizer.best_guess, but will return the position as well jsut in case
        return self.best_guess, self.best_error


if __name__ == "__main__":
    from fake_sensors import FakeIMU as IMU, FakeToF as ToF
    fake_tofs = [ToF(addr=0, angle=0, offset=(0, 0)), ToF(addr=1, angle=45, offset=(0, 0)), ToF(addr=2, angle=90, offset=(0, 0)), ToF(addr=3, angle=135, offset=(0, 0)), ToF(addr=4, angle=180, offset=(0, 0)), ToF(addr=5, angle=-135, offset=(0, 0)), ToF(addr=6, angle=-90, offset=(0, 0)), ToF(addr=7, angle=-45, offset=(0, 0))]
    localizer = Localizer(imu=IMU(), tofs=fake_tofs)
    pass # TODO: implement like in localizer_simulator_tester.py