import socket
import math
host = socket.gethostname()

# global ones - not bot specific
walls = [
    # field walls
    {'type': 'vertical',   'x': -2430/2, 'y_min': -1820/2, 'y_max':  1820/2}, # left                   wall
    {'type': 'vertical',   'x':  2430/2, 'y_min': -1820/2, 'y_max':  1820/2}, # right                  wall
    {'type': 'horizontal', 'y':  1820/2, 'x_min': -2430/2, 'x_max':  2430/2}, # top                    wall
    {'type': 'horizontal', 'y': -1820/2, 'x_min': -2430/2, 'x_max':  2430/2}, # bottom                 wall
    # goal walls
    {'type': 'vertical',   'x':  989,    'y_min': -450/2,  'y_max':  450/2},  # right goal back
    {'type': 'vertical',   'x': -989,    'y_min': -450/2,  'y_max':  450/2},  # left  goal back
    {'type': 'horizontal', 'y':  450/2,  'x_min':  915,    'x_max':  2430/2}, # right goal top    side wall
    {'type': 'horizontal', 'y': -450/2,  'x_min':  915,    'x_max':  2430/2}, # right goal bottom side wall
    {'type': 'horizontal', 'y':  450/2,  'x_min': -915,    'x_max': -2430/2}, # left  goal top    side wall
    {'type': 'horizontal', 'y': -450/2,  'x_min': -915,    'x_max': -2430/2}, # left  goal bottom side wall
]

# bot-specific config
if True:
    imu_addr = 0x4a
    tof_addrs = [
        0x50 + 2, 
        0x50 + 2 + 4 + 8,
        0x50 + 4 + 8,
        0x50 + 1 + 2 + 4 + 8,
        0x50 + 1 + 4 + 8,
        0x50,
        0x50 + 2 + 8,
        0x50 + 8,
        ]
    tof_offsets = [8.5, 80, 80, 80, 80, 80, 80, 80] # mm
    tof_offsets = {0x50+2: 8.5, 0x50+2+4+8: 80, 0x50+4+8: 80, 0x50+1+2+4+8: 80, 0x50+1+4+8: 80, 0x50: 80, 0x50+2+8: 80, 0x50+8: 80}
    tof_angles = list(map(math.radians, [0, 60, 90, 135, 180, -135, -90, -60]))
    tof_angles = {0x50+2: 0, 0x50+2+4+8: 60, 0x50+4+8: 90, 0x50+1+2+4+8: 135, 0x50+1+4+8: 180, 0x50: -135, 0x50+2+8: -90, 0x50+8: -60}

    
else:
    print("no config made for you :(")
