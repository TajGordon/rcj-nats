# Button System Documentation

## Overview

The button system in Scylla uses GPIO pins on the Raspberry Pi to allow physical button control of the robot. Buttons are **configured by action name** rather than hardcoded, making it easy to remap or add new buttons.

## Architecture

```
Physical Button (GPIO Pin)
    ↓
Button Poller Thread (polls GPIO at ~100 Hz)
    ↓
Button Event Queue
    ↓
Main FSM Loop (_handle_button_input)
    ↓
Action Handler (_handle_pause_button, etc.)
```

## Configuration

Buttons are configured when creating a Scylla instance:

```python
import board
from hypemage.scylla import Scylla, State

config = {
    'buttons': {
        'pause': board.D13,           # Action name → GPIO pin
        'emergency_stop': board.D19,
        'reset_heading': board.D26,
        'toggle_mode': board.D6
    }
}

scylla = Scylla(config=config)
scylla.start()
```

### Available Action Names

Currently implemented button actions:

| Action Name       | Handler Method           | Description                                    |
|-------------------|--------------------------|------------------------------------------------|
| `pause`           | `_handle_pause_button()` | Toggle between PAUSED and previous state       |
| `emergency_stop`  | `_handle_emergency_stop()` | Immediately transition to STOPPED state      |
| `reset_heading`   | `_handle_reset_heading()` | Reset IMU heading to 0 (forward direction)    |
| `toggle_mode`     | `_handle_toggle_mode()`  | Cycle between CHASE_BALL and DEFEND_GOAL      |

## Button Event Format

When a button is pressed, the poller pushes an event to the queue:

```python
{
    'type': 'button_press',
    'action': 'pause',         # The action name from config
    'timestamp': 1234567.89    # time.monotonic() when pressed
}
```

## Adding New Button Actions

To add a new button action:

1. **Add the button to config:**
   ```python
   config = {
       'buttons': {
           'my_new_action': board.D21
       }
   }
   ```

2. **Add a handler in `_handle_button_input()`:**
   ```python
   def _handle_button_input(self, event):
       action = event.get('action')
       
       if action == 'my_new_action':
           self._handle_my_new_action()
       # ... existing handlers ...
   ```

3. **Implement the handler method:**
   ```python
   def _handle_my_new_action(self):
       """Handle my new action"""
       print("My new action button pressed!")
       # Do something useful
       self.transition_to(State.SOME_STATE)
   ```

## Hardware Details

- **Pull-up resistors:** All buttons use internal pull-up resistors (active low)
- **Debouncing:** 50ms debounce time per button
- **Polling rate:** ~100 Hz (every 10ms)
- **Wiring:** Connect button between GPIO pin and GND (no external resistors needed)

### Example Wiring

```
GPIO Pin (e.g., D13) ─┬─ Button ─── GND
                      │
                   (internal pull-up)
```

When button is **not pressed**: GPIO reads HIGH (1)  
When button **is pressed**: GPIO reads LOW (0) → triggers event

## Graceful Fallback

If the `board` module is not available (e.g., running on a dev machine), the button poller runs in stub mode:

```
Warning: board module not available. Button poller disabled.
```

The robot will still function but won't respond to physical buttons.

## Testing Without Hardware

To test button logic without Raspberry Pi hardware:

```python
# Manually inject button events for testing
scylla.queues['button_out'].put({
    'type': 'button_press',
    'action': 'pause',
    'timestamp': time.time()
})
```

## Example: Custom Button Configuration

```python
import board
from hypemage.scylla import Scylla, State

# Map buttons to different actions
config = {
    'buttons': {
        # Primary controls
        'pause': board.D13,
        'emergency_stop': board.D19,
        
        # Navigation controls
        'reset_heading': board.D26,
        'toggle_mode': board.D6,
        
        # Could add more:
        # 'force_kick': board.D5,
        # 'cycle_strategy': board.D12,
    }
}

robot = Scylla(config=config)
robot.transition_to(State.SEARCH_BALL)
robot.start()
```

## Thread Safety

- Button poller runs in a **separate thread** (not process)
- Uses `queue.Queue` for thread-safe communication
- No locks needed - queue handles synchronization
- Events are dropped if queue is full (non-blocking puts)

## Performance

- Minimal overhead (~0.1ms per poll cycle)
- No impact on main FSM loop timing
- Debouncing prevents duplicate events from mechanical bounce
