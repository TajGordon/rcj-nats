import board
import digitalio
import time

class Button:
    def __init__(self, pin, name=None, pull=digitalio.Pull.UP):
        self.name = name or f"Button_{pin}"
        self.pin = pin
        self.pull = pull
        self.last_press = 0
        self.last_up = 0
        self.debounce_time = 0.05
        self._setup()
    
    def _setup(self):
        self.button = digitalio.DigitalInOut(self.pin)
        self.button.direction = digitalio.Direction.INPUT
        self.button.pull = self.pull

    def is_pressed(self):
        current_time = time.monotonic()
        if not self.button.value:  # Button is pressed (active low)
            if self.last_up > self.last_press and (current_time - self.last_press) > self.debounce_time:
                self.last_press = current_time
                return True
        else:
            self.last_up = current_time
        return False
    


if __name__ == "__main__":
    print("Button Test")
    try:
        buttons = [Button(board.D13, name="1"), Button(board.D19, name="2"), Button(board.D26, name="3")]
    except Error as e:
        print(f"Error initializing buttons: {e}")
    while True:
        for button in buttons:
            if button.is_pressed():
                print(f"{button.name} pressed")
        time.sleep(0.01)  # Small delay to avoid busy waiting