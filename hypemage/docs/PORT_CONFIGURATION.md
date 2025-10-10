# Port Configuration Fix

## Problem
The interface server was hardcoded to port 8080, but Necron (m7) needs to use port 8081 to avoid conflicts when both robots are on the same network.

## Solution
Added automatic port detection based on hostname:
- **Storm (f7.local)**: Uses port 8080
- **Necron (m7.local)**: Uses port 8081
- **Unknown/Development**: Defaults to port 8080

## Changes Made

### 1. Interface Server (`hypemage/interface.py`)
- Added `socket` import for hostname detection
- Added `get_robot_port()` function that:
  - Detects hostname using `socket.gethostname()`
  - Returns 8080 if hostname contains 'f7' (Storm)
  - Returns 8081 if hostname contains 'm7' (Necron)
  - Defaults to 8080 for unknown hostnames
  - Logs the detected hostname and chosen port
- Modified `main()` to use dynamic port

### 2. Client Configuration (`hypemage/client/app.js`)
- Updated hostnames from `localhost` to actual robot hostnames:
  - Storm: `f7.local:8080`
  - Necron: `m7.local:8081`

## Testing

When you start the interface server, you should see:
```
INFO - Detected hostname: m7
INFO - Detected Necron robot (m7) - using port 8081
INFO - Starting Robot Interface Server
INFO - Dashboard: http://0.0.0.0:8081
INFO - WebSocket: ws://0.0.0.0:8081/ws
```

## Network Setup

The client dashboard can now connect to both robots simultaneously:
- **Storm**: `ws://f7.local:8080/ws`
- **Necron**: `ws://m7.local:8081/ws`

This allows you to control both robots from a single dashboard interface.

## Troubleshooting

If the connection still fails:

1. **Check hostname detection**:
   ```bash
   python -c "import socket; print(socket.gethostname())"
   ```
   Should contain either 'f7' or 'm7'

2. **Check port is correct**:
   ```bash
   # On robot
   sudo netstat -tulpn | grep python
   ```
   Should show the correct port (8080 for Storm, 8081 for Necron)

3. **Check firewall**:
   ```bash
   # Allow the port through firewall
   sudo ufw allow 8080
   sudo ufw allow 8081
   ```

4. **Test WebSocket connection**:
   ```javascript
   // In browser console
   const ws = new WebSocket('ws://m7.local:8081/ws');
   ws.onopen = () => console.log('Connected!');
   ws.onerror = (e) => console.error('Error:', e);
   ```

## Future Improvements

Consider reading port configuration from `config.json`:
```json
{
  "interface": {
    "port": 8081,
    "host": "0.0.0.0"
  }
}
```

This would allow manual override without changing code.
