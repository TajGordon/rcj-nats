import socket

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
if host == 'storm':
    tof_addrs = []
    tof_offsets = {}
    tof_angles = {}
    
else:
    print("no config made for you :(")
