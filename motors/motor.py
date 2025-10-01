import board
import busio
from steelbar_powerful_bldc_driver import PowerfulBLDCDriver

# constants
MAX_CURRENT = 65536 * 3
MAX_SPEED = 1_000_000 * 400


class Motor:
    def __init__(
        self,
        addr,
        i2c=busio.I2C(board.SCL, board.SDA),
        current_limit=MAX_CURRENT,
        id_pid_constants=(1500, 200),
        iq_pid_constants=(1500, 200),
        speed_pid_constants=(4e-2, 4e-4, 3e-2),
        position_pid_constants=(275, 0, 0),
        position_region_boundary=250000,
        speed_limit=MAX_SPEED,
        elecangleoffset=1544835584,
        sincoscentre=1255,
    ):
        self.i2c = i2c
        self.addr = addr
        self.driver = PowerfulBLDCDriver(self.i2c, addr)
        self._speed_limit = speed_limit
        self.motor_setup(
            current_limit=current_limit,
            id_pid_constants=id_pid_constants,
            iq_pid_constants=iq_pid_constants,
            speed_pid_constants=speed_pid_constants,
            position_pid_constants=position_pid_constants,
            position_region_boundary=position_region_boundary,
            speed_limit=speed_limit,
            elecangleoffset=elecangleoffset,
            sincoscentre=sincoscentre,
        )

    def motor_setup(
        self,
        current_limit=MAX_CURRENT,
        id_pid_constants=(1500, 200),
        iq_pid_constants=(1500, 200),
        speed_pid_constants=(4e-2, 4e-4, 3e-2),
        position_pid_constants=(275, 0, 0),
        position_region_boundary=250000,
        speed_limit=MAX_SPEED,
        elecangleoffset=1544835584,
        sincoscentre=1255,
    ):
        # PID and limits
        self.driver.set_current_limit_foc(abs(int(current_limit)))
        self.driver.set_id_pid_constants(int(id_pid_constants[0]), int(id_pid_constants[1]))
        self.driver.set_iq_pid_constants(int(iq_pid_constants[0]), int(iq_pid_constants[1]))
        self.driver.set_speed_pid_constants(float(speed_pid_constants[0]), float(speed_pid_constants[1]), float(speed_pid_constants[2]))
        self.driver.set_position_pid_constants(float(position_pid_constants[0]), float(position_pid_constants[1]), float(position_pid_constants[2]))
        self.driver.set_position_region_boundary(float(position_region_boundary))
        self.driver.set_speed_limit(int(speed_limit))
        self._speed_limit = int(speed_limit)

        # Sensor calibration constants (pre-measured)
        # should be stored in the driver itself
        # self.driver.set_ELECANGLEOFFSET(int(elecangleoffset))
        # self.driver.set_SINCOSCENTRE(int(sincoscentre))

        # Operating and command modes
        self.driver.configure_operating_mode_and_sensor(3, 1)  # FOC + sin/cos encoder
        self.driver.configure_command_mode(12)  # speed mode

    def _set_rps(self, rps):
        pass

    def set_speed(self, speed):
        # speed expected in range [-10.0, 10.0]; scale to controller units
        if speed is None:
            return
        speed /= 10 # scale to range [-1.0, 1.0]
        if speed > 1.0:
            speed = 1.0
        if speed < -1.0:
            speed = -1.0
        self.driver.set_speed(int(self._speed_limit * speed))


if __name__ == "__main__":
    motors = {
        4: Motor(30),  # dribbler
        0: Motor(26),  # front left
        1: Motor(27),  # front right
        2: Motor(29),  # back righta
        3: Motor(25),  # back left
    }
    motors[4].set_speed(3)
