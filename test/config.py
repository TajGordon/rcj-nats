import socket

hostname = socket.gethostname()

if hostname == 'storm':
    # pick addresses for motors by position
    motor_addresses = {''}
    # pick tofs by their address
    tof_addresses = [
                    0x50, 
                    0x50 + 1 + 2 + 8,
                    0x50 + 2 + 4 + 8,
                    0x50 + 1 + 4 + 8,
                    0x50 + 8,
                    0x50 + 2 + 8,
                    0x50 + 4,
                    0x50 + 4 + 8,
                    ]
    tof_angles = {}
    tof_offsets = {}
    tof_max_distance = 2500
