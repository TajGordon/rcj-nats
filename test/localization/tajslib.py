import math

def add_radians(a, b):
    c = a + b
    while c > math.pi:
        c -= 2 * math.pi
    while c < -math.pi:
        c += 2 * math.pi
    return c