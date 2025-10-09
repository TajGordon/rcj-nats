# Robot Interface System

Simple web-based interface for controlling and debugging the robot.

## Architecture

```
┌─────────────────────────────────────────┐
│  Client (Browser)                       │
│  http://robot:8080                      │
└────────────┬────────────────────────────┘
             │ WebSocket
             ▼
┌─────────────────────────────────────────┐
│  Interface Server (port 8080)           │
│  - Manages robot processes              │
│  - Handles commands from client         │
│  - Serves web UI files                  │
└────┬────────────────────────────────────┘
     │ subprocess
     ▼
┌─────────────────────────────────────────┐
│  Robot (scylla.py)                      │
│  └─ DebugManager (port 8765)            │
│      └─ Client connects here for debug  │
└─────────────────────────────────────────┘
```

## Components

### 1. **Interface Server** (`interface.py`)
- WebSocket server on port 8080
- Manages robot lifecycle (start/stop)
- Extensible command handlers
- Monitors process status

### 2. **Client App** (`client/`)
- Web-based UI (HTML/CSS/JavaScript)
- Connects to interface server via WebSocket
- Sends commands, displays status
- Shows debug data (camera feed, motor speeds)

### 3. **Debug Manager** (`debug/debug_manager.py`)
- Started by robot when `--debug` flag is set
- Collects debug data from all subsystems
- WebSocket server on port 8765
- Broadcasts data to connected clients

## Usage

### Start Interface Server (on Robot Pi)

```bash
# SSH into robot
ssh pi@robot.local

# Start interface server
python -m hypemage.interface

# Server will listen on:
# - WebSocket: ws://robot:8080 (commands)
# - HTTP: http://robot:8080 (web UI - TODO: add static file serving)
```

### Access from Laptop/Phone

1. Open browser: `http://robot.local:8080`
2. Click "▶️ Start Robot (Debug)" to launch with debug
3. Camera feed and motor status will appear
4. Use "⏹️ Stop Robot" to stop

### Available Commands

| Command | Description |
|---------|-------------|
| `scylla_debug` | Start robot with debug enabled (port 8765 for debug data) |
| `scylla_production` | Start robot without debug (competition mode) |
| `stop_robot` | Stop running robot gracefully |
| `get_status` | Get current robot status |
| `color_calibration` | Launch color calibration tool |
| `motor_test` | Launch motor test script |
| `get_logs` | Get recent log entries |

### Adding New Commands

Edit `interface.py`:

```python
def __init__(self):
    self.commands = {
        'scylla_debug': self._scylla_debug,
        'scylla_production': self._scylla_production,
        'my_new_command': self._my_new_handler,  # Add here
    }

def _my_new_handler(self, args: Dict[str, Any]) -> Dict[str, Any]:
    """Custom command handler"""
    try:
        # Launch your script
        proc = subprocess.Popen(['python', 'my_script.py'])
        return {'success': True, 'pid': proc.pid}
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

Then use from client:
```javascript
sendCommand('my_new_command', {arg1: 'value'});
```

## Multi-Robot Support (Future)

### Approach: Each bot hosts its own interface server

```
Necron Bot (192.168.1.100):
  └─ interface.py (port 8080)

Storm Bot (192.168.1.101):
  └─ interface.py (port 8080)

Client Browser:
  ├─ Tab 1: http://192.168.1.100:8080 (Necron)
  └─ Tab 2: http://192.168.1.101:8080 (Storm)
```

### Setup on Each Bot

1. SSH into bot: `ssh pi@necron.local`
2. Configure autostart (systemd or cron)
3. Interface server starts on boot
4. Access from any device on network

### Systemd Service (Auto-start on Boot)

Create `/etc/systemd/system/robot-interface.service`:

```ini
[Unit]
Description=Robot Interface Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/rcj-nats
ExecStart=/usr/bin/python3 -m hypemage.interface
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable robot-interface.service
sudo systemctl start robot-interface.service
```

Check status:
```bash
sudo systemctl status robot-interface.service
```

## Debug Data Flow

When robot is started with `--debug`:

```
Robot starts:
  └─ DebugManager starts (port 8765)

Camera process:
  └─ Sends CameraDebugData to debug_q
       └─ DebugManager receives
            └─ Broadcasts via WebSocket to clients

Client:
  ├─ Connects to ws://robot:8080 (interface)
  └─ Connects to ws://robot:8765 (debug data)
       └─ Receives camera frames, motor speeds, etc.
```

## Security Notes

### Development (Safe Network)
- Interface binds to `0.0.0.0:8080` (all interfaces)
- Anyone on network can control robot
- OK for testing/development

### Competition (Public Network)
- Change to bind only to localhost: `127.0.0.1:8080`
- Use SSH tunnel from laptop:
  ```bash
  ssh -L 8080:localhost:8080 pi@robot.local
  ```
- Then access: `http://localhost:8080` (tunnels to robot)

### Future: Add Authentication
- Add password/token to WebSocket connection
- Reject unauthorized clients
- See `interface.py` for implementation

## File Structure

```
hypemage/
├── interface.py           # Interface server
├── scylla.py              # Main robot FSM
├── debug/
│   ├── debug_data.py      # Debug dataclasses
│   ├── debug_manager.py   # Debug collector (WebSocket server)
│   └── color_calibration.py  # Utility script
└── client/
    ├── index.html         # Web UI
    ├── app.js             # WebSocket client logic
    └── style.css          # Styling
```

## Example Session

1. **Start interface on robot:**
   ```bash
   pi@robot:~/rcj-nats$ python -m hypemage.interface
   INFO - Interface server listening on ws://0.0.0.0:8080
   ```

2. **Open browser on laptop:**
   - Navigate to `http://robot.local:8080`
   - See dashboard with "Start Robot (Debug)" button

3. **Click "Start Robot (Debug)":**
   - Interface launches: `python -m hypemage.scylla --debug`
   - Robot starts, DebugManager starts on port 8765
   - Client auto-connects to port 8765
   - Camera feed appears, motor gauges update

4. **Click "Stop Robot":**
   - Interface sends SIGTERM to robot process
   - Robot shuts down gracefully
   - Debug connection closes

## Troubleshooting

### Can't connect to interface
- Check robot is on network: `ping robot.local`
- Check interface is running: `ssh pi@robot.local 'pgrep -f interface.py'`
- Check firewall: `sudo ufw status`

### No camera feed in debug mode
- Check DebugManager started: Look for "Debug server listening on ws://0.0.0.0:8765" in logs
- Check client connected to port 8765: Open browser console (F12)
- Check camera process is sending debug data

### Robot doesn't stop
- Check process status: `ps aux | grep scylla`
- Manual kill: `pkill -f scylla.py`
- Check logs: `tail -f ~/robot_logs/robot.log`

## Next Steps

1. ✅ Interface server created
2. ✅ Client web UI created
3. ⚠️ TODO: Add HTTP server to serve client files (currently need to copy `client/` to robot)
4. ⚠️ TODO: Integrate debug data display (camera/motors)
5. ⚠️ TODO: Add authentication for security
6. ⚠️ TODO: Add mDNS discovery for multi-robot
