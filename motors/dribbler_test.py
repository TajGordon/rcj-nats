from motor import Motor


if __name__ == "__main__":
    speed = input("Speed for motor: ")
    motor = Motor(30)
    motor.set_speed(speed)
    _ = input("Press any key to exit")
    motor.set_speed(0)