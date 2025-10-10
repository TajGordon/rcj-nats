# Multi-Robot Dashboard

A Vue.js-powered web dashboard for controlling and monitoring Storm and Necron robots.

## Features

- **Multi-Robot Support**: Connect to both Storm and Necron simultaneously over network
- **3 View Modes**: 
  - Both (side-by-side comparison)
  - Storm (detailed single robot view)
  - Necron (detailed single robot view)
- **Modular Widgets**: Toggle visibility of camera, motors, status, and controls
- **Real-Time Updates**: WebSocket connections for live camera feed and motor data
- **Modern UI**: Dark theme with responsive design

## Quick Start

### Prerequisites

1. **Robots must be on the same network** as your laptop
2. **mDNS/Bonjour** must be working (`.local` hostnames)
3. **Interface servers running** on both robots

### Setup

1. **On Storm robot (f7)**:
   ```bash
   cd ~/rcj-nats
   python -m hypemage.interface
   ```
   Output should show:
   ```
   INFO - Detected Storm robot (f7) - using port 8080
   INFO - Dashboard: http://0.0.0.0:8080
   INFO - WebSocket: ws://0.0.0.0:8080/ws
   ```

2. **On Necron robot (m7)**:
   ```bash
   cd ~/rcj-nats
   python -m hypemage.interface
   ```
   Output should show:
   ```
   INFO - Detected Necron robot (m7) - using port 8081
   INFO - Dashboard: http://0.0.0.0:8081
   INFO - WebSocket: ws://0.0.0.0:8081/ws
   ```

3. **Open dashboard from your laptop**:
   - Option A: `http://f7.local:8080` (connects to Storm's server)
   - Option B: `http://m7.local:8081` (connects to Necron's server)
   - **Either option can control both robots!**

## Configuration

The robot addresses are configured in `app.js`:

```javascript
const ROBOT_CONFIG = {
    storm: { 
        host: 'f7.local',   // Storm's hostname
        interfacePort: 8080, // Storm's interface port
        debugPort: 8765 
    },
    necron: { 
        host: 'm7.local',    // Necron's hostname
        interfacePort: 8081, // Necron's interface port
        debugPort: 8766 
    }
};
```

### Port Reference

| Robot  | Hostname | Interface Port | Debug Port | WebSocket URL           |
|--------|----------|----------------|------------|-------------------------|
| Storm  | f7.local | 8080           | 8765       | ws://f7.local:8080/ws   |
| Necron | m7.local | 8081           | 8766       | ws://m7.local:8081/ws   |

## Usage

### View Modes

Use the bottom navigation to switch between views:
- **Both**: See both robots side-by-side
- **Storm**: Full-screen Storm view
- **Necron**: Full-screen Necron view

### Widget Toggles

Use the checkboxes at the bottom to show/hide widgets:
- **🎮 Controls**: Start/stop buttons and status
- **📷 Camera**: Live camera feed (when robot is in debug mode)
- **⚙️ Motors**: Motor speeds and temperatures
- **ℹ️ Status**: Connection and host information

### Robot Control

**Debug Mode**: Starts robot with camera and sensor debugging enabled
**Stop**: Stops the running robot process

## Files

- `index.html` - Dashboard HTML structure (Vue.js app)
- `app.js` - Vue.js application logic and WebSocket handling
- `style.css` - Modern dark theme styling

## Architecture

```
Browser                     Robot
┌─────────────┐            ┌──────────────────┐
│             │            │                  │
│  Dashboard  │ ─WS:8080─► │ Interface Server │ ─► Commands
│  (Vue.js)   │            │                  │
│             │ ◄─WS:8765─ │ Debug Manager    │ ◄─ Camera/Motors
└─────────────┘            └──────────────────┘
```

## Customization

### Adding a New Widget

1. Edit `AVAILABLE_WIDGETS` in `app.js`:
```javascript
{ id: 'my-widget', name: 'My Widget', icon: '🔧' }
```

2. Add data to robot state in `createRobotState()`:
```javascript
myCustomData: { value: 0 }
```

3. Add widget HTML in `index.html`:
```html
<div v-if="storm.visibleWidgets.has('my-widget')" class="widget">
    <h3>🔧 My Widget</h3>
    <p>{{ storm.myCustomData.value }}</p>
</div>
```

4. Update data in `handleDebugMessage()`:
```javascript
if (subsystem === 'custom') {
    robot.myCustomData.value = payload.value;
}
```

### Changing Theme Colors

Edit CSS variables in `style.css`:

```css
:root {
    --bg-dark: #0a0e27;
    --accent-blue: #00d4ff;
    --accent-purple: #b74dff;
    /* ... */
}
```

## Troubleshooting

**Connection Issues**:
- Check robot IPs in `ROBOT_CONFIG`
- Ensure interface server is running on the robot
- Check browser console for WebSocket errors

**Camera Not Showing**:
- Start robot in Debug mode
- Check that debug manager is running on port 8765
- Verify camera feed is being sent (check robot logs)

**Widgets Not Updating**:
- Check WebSocket connection in browser DevTools
- Verify debug manager is sending updates
- Check browser console for JavaScript errors

## Development

No build step required! Just edit the files and refresh the browser.

All dependencies are loaded from CDN:
- Vue.js 3 (production build)

## License

Part of the RCJ NATS project.
