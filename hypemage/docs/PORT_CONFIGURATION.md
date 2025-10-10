# Port Configuration & Network Setup

## Overview

The interface system uses different ports for each robot to allow simultaneous operation on the same network:
- **Storm (f7.local)**: Port 8080
- **Necron (m7.local)**: Port 8081

This allows you to control both robots from a single dashboard interface, even when they're both running at the same time.

## Architecture

### Server Side (`hypemage/interface.py`)
The interface server automatically detects which robot it's running on based on hostname:
```python
def get_robot_port() -> int:
    hostname = socket.gethostname().lower()
    if 'f7' in hostname:
        return 8080  # Storm
    elif 'm7' in hostname:
        return 8081  # Necron
    else:
        return 8080  # Default
```

When you start the interface on each robot, it automatically selects the correct port.

### Client Side (`hypemage/client/app.js`)
The dashboard connects to both robots over the network:

```javascript
const ROBOT_CONFIG = {
    storm: { 
        host: 'f7.local',    // Storm's network hostname
        interfacePort: 8080, // Storm's port
        debugPort: 8765 
    },
    necron: { 
        host: 'm7.local',    // Necron's network hostname
        interfacePort: 8081, // Necron's port
        debugPort: 8766 
    }
};
```

## Deployment

### On Storm (f7)

```bash
# SSH to Storm
ssh pi@f7.local  # or your username

# Navigate to project
cd ~/rcj-nats

# Start interface server
python -m hypemage.interface
```

Expected output:
```
INFO - Detected hostname: f7
INFO - Detected Storm robot (f7) - using port 8080
INFO - Starting Robot Interface Server
INFO - Dashboard: http://0.0.0.0:8080
INFO - WebSocket: ws://0.0.0.0:8080/ws
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

### On Necron (m7)

```bash
# SSH to Necron
ssh pi@m7.local  # or your username

# Navigate to project
cd ~/rcj-nats

# Start interface server
python -m hypemage.interface
```

Expected output:
```
INFO - Detected hostname: m7
INFO - Detected Necron robot (m7) - using port 8081
INFO - Starting Robot Interface Server
INFO - Dashboard: http://0.0.0.0:8081
INFO - WebSocket: ws://0.0.0.0:8081/ws
INFO:     Uvicorn running on http://0.0.0.0:8081 (Press CTRL+C to quit)
```

### Access from Your Laptop

Open either URL in your browser:
- **Storm's dashboard**: `http://f7.local:8080`
- **Necron's dashboard**: `http://m7.local:8081`

**Note**: Both dashboards can control both robots! The dashboard automatically connects to both `f7.local:8080` and `m7.local:8081` via WebSocket, regardless of which robot is serving the HTML page.

## Port Mapping

| Robot  | Hostname | Interface Port | Debug Port | WebSocket URL           |
|--------|----------|----------------|------------|-------------------------|
| Storm  | f7.local | 8080           | 8765       | ws://f7.local:8080/ws   |
| Necron | m7.local | 8081           | 8766       | ws://m7.local:8081/ws   |

## Troubleshooting

### Error: "Firefox can't establish a connection"

**Cause**: Robot not on network, interface server not running, or firewall blocking.

**Solutions**:

1. **Check robots are on network**:
   ```bash
   ping f7.local
   ping m7.local
   ```
   Should get responses. If not, check robot WiFi/Ethernet.

2. **Check interface servers are running**:
   ```bash
   # On each robot
   ps aux | grep interface
   ```
   Should show `python -m hypemage.interface` running.

3. **Check firewall** (on robots):
   ```bash
   sudo ufw allow 8080
   sudo ufw allow 8081
   sudo ufw allow 8765
   sudo ufw allow 8766
   ```

4. **Verify mDNS/Bonjour** is working:
   ```bash
   # Install if missing
   sudo apt-get install avahi-daemon
   sudo systemctl start avahi-daemon
   ```

### Error: "Address already in use"

**Cause**: Another process is using the port.

**Solution**:
```bash
# Find process using the port
sudo lsof -i :8080
sudo lsof -i :8081

# Kill it
sudo kill -9 <PID>
```

### Hostname detection fails

**Cause**: Server doesn't recognize hostname.

**Solution**: Edit `interface.py` line 502-510 to add your hostname pattern:
```python
if 'f7' in hostname or 'your-storm-name' in hostname:
    return 8080
elif 'm7' in hostname or 'your-necron-name' in hostname:
    return 8081
```

### Only one robot connects

**Cause**: One interface server isn't running or is on wrong port.

**Solution**:
1. Check both servers are running
2. Verify correct ports in browser console (F12):
   ```
   === Multi-Robot Dashboard ===
   Storm: ws://f7.local:8080/ws
   Necron: ws://m7.local:8081/ws
   ```

## Network Requirements

### Same Network
All devices (laptop + robots) must be on the same WiFi/network.

### Firewall (on robots)
```bash
sudo ufw allow 8080  # Storm interface
sudo ufw allow 8081  # Necron interface
sudo ufw allow 8765  # Storm debug
sudo ufw allow 8766  # Necron debug
```

### mDNS/Bonjour
Ensure `.local` hostname resolution works:
```bash
# Install if missing (on robots)
sudo apt-get install avahi-daemon
sudo systemctl enable avahi-daemon
sudo systemctl start avahi-daemon
```

## Quick Reference

**Check hostname**:
```bash
hostname
```

**Check server port**:
```bash
python -c "import socket; hostname = socket.gethostname(); print(f'{hostname}: port', 8080 if 'f7' in hostname else 8081 if 'm7' in hostname else 8080)"
```

**Test WebSocket from browser** (F12 Console):
```javascript
const ws = new WebSocket('ws://f7.local:8080/ws');
ws.onopen = () => console.log('✓ Storm connected!');
ws.onerror = (e) => console.error('✗ Storm failed:', e);

const ws2 = new WebSocket('ws://m7.local:8081/ws');
ws2.onopen = () => console.log('✓ Necron connected!');
ws2.onerror = (e) => console.error('✗ Necron failed:', e);
```

**View server logs**:
```bash
# On robot, if running in background
journalctl -u interface -f
```
