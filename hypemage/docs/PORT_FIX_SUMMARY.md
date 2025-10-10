# Interface Port Configuration - Final

## The Problem

Dashboard couldn't connect to robots, showing errors like:
```
Firefox can't establish a connection to the server at ws://m7.local:8081/ws
Firefox can't establish a connection to the server at ws://f7.local:8080/ws
```

## The Solution

Simplified the configuration to always connect over the network using `.local` hostnames.

## Changes Made

### 1. Server Side: Auto Port Detection (`hypemage/interface.py`)
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

**What it does**:
- Automatically detects which robot it's running on
- Storm (f7) uses port 8080
- Necron (m7) uses port 8081
- No configuration needed!

### 2. Client Side: Network Addresses (`hypemage/client/app.js`)
```javascript
const ROBOT_CONFIG = {
    storm: { 
        host: 'f7.local',    // Network hostname
        interfacePort: 8080, 
        debugPort: 8765 
    },
    necron: { 
        host: 'm7.local',    // Network hostname
        interfacePort: 8081, 
        debugPort: 8766 
    }
};
```

**What it does**:
- Dashboard connects to both robots via network
- Works from your laptop when on same WiFi
- No mode switching needed - it just works!

## Network Architecture

```
┌──────────────────────────────────────────────┐
│            Your Laptop (Coding)              │
│                                              │
│  Browser: http://f7.local:8080               │
│  Dashboard connects to:                      │
│    - ws://f7.local:8080/ws  (Storm)          │
│    - ws://m7.local:8081/ws  (Necron)         │
└──────────────┬───────────────┬───────────────┘
               │               │
       Same WiFi Network       │
               │               │
      ┌────────▼────────┐     │
      │  Storm (f7)     │     │
      │                 │     │
      │  Interface:     │     │
      │  Port 8080      │     │
      └─────────────────┘     │
                              │
                     ┌────────▼────────┐
                     │  Necron (m7)    │
                     │                 │
                     │  Interface:     │
                     │  Port 8081      │
                     └─────────────────┘
```

## How It Works

1. **On Storm (f7)**:
   - Run: `python -m hypemage.interface`
   - Detects hostname contains 'f7'
   - Starts on port 8080
   - Serves dashboard at `http://f7.local:8080`

2. **On Necron (m7)**:
   - Run: `python -m hypemage.interface`
   - Detects hostname contains 'm7'
   - Starts on port 8081
   - Serves dashboard at `http://m7.local:8081`

3. **From your laptop**:
   - Open `http://f7.local:8080` or `http://m7.local:8081`
   - Dashboard loads and connects to **both** robots
   - Control both robots from single interface!

## Files Changed

1. ✅ `hypemage/interface.py` - Added `get_robot_port()` function
2. ✅ `hypemage/client/app.js` - Simplified to network-only config
3. ✅ `hypemage/client/README.md` - Updated instructions
4. ✅ `hypemage/docs/PORT_CONFIGURATION.md` - Comprehensive guide

## Quick Start

### On Each Robot

```bash
# SSH to robot
ssh pi@f7.local  # or m7.local

# Start interface
cd ~/rcj-nats
python -m hypemage.interface
```

### On Your Laptop

```bash
# Just open browser to either robot
firefox http://f7.local:8080
# or
firefox http://m7.local:8081
```

Both URLs give you the same dashboard that controls both robots!

## Verification Checklist

On robots, when you start interface, you should see:

**Storm (f7)**:
```
INFO - Detected hostname: f7
INFO - Detected Storm robot (f7) - using port 8080
INFO - Dashboard: http://0.0.0.0:8080
INFO - WebSocket: ws://0.0.0.0:8080/ws
```

**Necron (m7)**:
```
INFO - Detected hostname: m7
INFO - Detected Necron robot (m7) - using port 8081
INFO - Dashboard: http://0.0.0.0:8081
INFO - WebSocket: ws://0.0.0.0:8081/ws
```

In browser console (F12):
```
=== Multi-Robot Dashboard ===
Storm: ws://f7.local:8080/ws
Necron: ws://m7.local:8081/ws
==============================
```

## Troubleshooting

### Still can't connect?

1. **Verify network connectivity**:
   ```bash
   ping f7.local
   ping m7.local
   ```
   Both should respond. If not, check robots are on WiFi.

2. **Check interface servers running**:
   ```bash
   # SSH to each robot
   ps aux | grep interface
   ```
   Should show Python process.

3. **Check firewall** (on robots):
   ```bash
   sudo ufw allow 8080
   sudo ufw allow 8081
   ```

4. **Test direct WebSocket** (browser console F12):
   ```javascript
   new WebSocket('ws://f7.local:8080/ws');
   new WebSocket('ws://m7.local:8081/ws');
   ```
   Check for errors.

### Connection works but no data?

- Debug server might not be running
- Check `debug_manager.py` is active
- Debug uses ports 8765 (Storm) and 8766 (Necron)

## Benefits of This Setup

✅ **Simple**: No mode switching or configuration changes  
✅ **Consistent**: Same setup for development and competition  
✅ **Flexible**: Access from any device on network  
✅ **Multi-robot**: Control both robots simultaneously  
✅ **Automatic**: Ports are auto-detected based on hostname

## Next Steps

1. Deploy code to both robots
2. Start interface servers on both
3. Open dashboard from laptop
4. Verify both robots connect (green badges in header)
5. Test controls and camera feeds

---

**No more port confusion!** 🎉
