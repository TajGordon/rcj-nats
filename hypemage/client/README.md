# Multi-Robot Dashboard

A Vue.js-powered web dashboard for controlling and monitoring Storm and Necron robots.

## Features

- **Multi-Robot Support**: Connect to both Storm and Necron simultaneously
- **3 View Modes**: 
  - Both (side-by-side comparison)
  - Storm (detailed single robot view)
  - Necron (detailed single robot view)
- **Modular Widgets**: Toggle visibility of camera, motors, status, and controls
- **Real-Time Updates**: WebSocket connections for live camera feed and motor data
- **Modern UI**: Dark theme with responsive design

## Quick Start

### 1. Configure Robot IPs

Edit `app.js` and update the robot IPs:

```javascript
const ROBOT_CONFIG = {
    storm: { name: 'Storm', host: 'f7.local', interfacePort: 8080, debugPort: 8765 },
    necron: { name: 'Necron', host: 'm7.local', interfacePort: 8080, debugPort: 8765 }
};
```

### 2. Start the Interface Server

On each robot (or locally for testing):

```bash
python -m hypemage.interface
```

This starts:
- Interface server on port 8080 (commands & control)
- Debug manager on port 8765 (camera & sensor data)

### 3. Open the Dashboard

Simply open `index.html` in your browser. The dashboard will:
- Auto-connect to both robots
- Show connection status in the header badges
- Enable controls when robots are connected

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
