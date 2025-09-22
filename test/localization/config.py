import socket

host = socket.gethostname()

if host == 'storm':
    tof_addrs = []
    tof_offsets = {}
    tof_angles = {}
    
    ''' field geometry '''
    # outer walls - just a single coordinate
    left_wall = -2430/2
    right_wall = 2430/2
    top_wall = 1820/2
    bottom_wall = 1820/2
    # goal dimensions - multiply by T[-1, 1] to get opposite goal
    goal_top_wall_y = 450/2
    goal_bottom_wall_y = -450/2
    goal_walls_x = 915
    goal_back_wall_x = 915 + 74

else:
    print("no config made for you :(")
