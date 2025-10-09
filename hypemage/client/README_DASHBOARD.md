## Multi-Robot Dashboard

Modern, modular dashboard for controlling and monitoring multiple robots simultaneously.

## Features

✅ **Multi-Robot Support** - Connect to Storm and Necron at the same time
✅ **Three Views** - Both (side-by-side), Storm (detailed), Necron (detailed)
✅ **Modular Widgets** - Toggle visibility of camera, motors, logs, ToF, etc.
✅ **Real-Time Data** - WebSocket streaming for live updates
✅ **Responsive Design** - Works on desktop, tablet, and mobile
✅ **Easy to Extend** - Add new widgets with minimal code

---

## Quick Start

### 1. Configure Robot IPs

Edit `config.js`:

```javascript
const ROBOT_CONFIG = {
    storm: {
        host: '192.168.1.100',  // Change to Storm's IP
        // ...
    },
    necron: {
        host: '192.168.1.101',  // Change to Necron's IP
        // ...
    }
};
```

### 2. Open Dashboard

```
http://localhost:8080/index_new.html
```

Or deploy to robots and access via their IPs.

### 3. Use the Dashboard

**Bottom Navigation:**
- Click **Both** to see Storm and Necron side-by-side
- Click **Storm** to focus on Storm only
- Click **Necron** to focus on Necron only

**Widget Toggles:**
- Check/uncheck widgets to show/hide them
- Available: Controls, Camera, Motors, Position, ToF, Logs, Status

---

## File Structure

```
client/
├── index_new.html          # Main dashboard HTML
├── app_new.js              # Vue.js application logic
├── style_new.css           # Modern dark theme CSS
├── config.js               # Robot configuration
│
├── components/
│   ├── widgets.js          # Widget components (camera, motors, etc.)
│   └── robot-connection.js # WebSocket connection helper
│
└── README_DASHBOARD.md     # This file
```

---

## Available Widgets

### 🎮 Controls
- Start/stop robot (debug or production mode)
- Run calibration scripts
- Execute motor tests

### 📷 Camera
- Live camera feed (JPEG stream)
- Ball detection overlay
- Goal detection indicators
- FPS counter

### ⚙️ Motors
- Real-time motor speeds (4 motors)
- Speed bars with direction indicators
- Motor temperatures (expanded view)
- Watchdog status

### 📍 Position (Localization)
- X, Y coordinates
- Heading (angle)
- Confidence level

### 📡 ToF Sensors
- Radar visualization
- Distance readings
- Angle indicators
- Color-coded (green = clear, red = obstacle)

### 📝 Logs
- Real-time log stream
- Color-coded by level (error, warning, info)
- Last 20 lines displayed
- Auto-scrolling

### ℹ️ Status
- Robot running/stopped status
- Process ID
- Debug mode indicator
- Host connection info

---

## Adding a New Widget

### Step 1: Create Widget Component

Edit `components/widgets.js`:

```javascript
const MyNewWidget = defineComponent({
    name: 'MyNewWidget',
    props: ['data', 'expanded'],
    template: `
        <div class="widget my-widget">
            <h3>🎯 My Widget</h3>
            <div class="widget-content">
                <!-- Your content here -->
                <p>{{ data.someValue }}</p>
            </div>
        </div>
    `
});

// Register it
app.component('my-new-widget', MyNewWidget);
```

### Step 2: Add to RobotWidgets Container

In `components/widgets.js`, add to `RobotWidgets` template:

```javascript
template: `
    <div class="widgets-container">
        <!-- Existing widgets... -->
        
        <!-- Your new widget -->
        <my-new-widget 
            v-if="visibleWidgets.has('mywidget')"
            :data="robot.myData"
            :expanded="expanded">
        </my-new-widget>
    </div>
`
```

### Step 3: Add to Config

Edit `config.js`:

```javascript
const WIDGET_TYPES = [
    // Existing widgets...
    { id: 'mywidget', name: 'My Widget', icon: '🎯', defaultVisible: false }
];
```

### Step 4: Add Data to Robot State

Edit `app_new.js`:

```javascript
storm: {
    // Existing state...
    myData: {
        someValue: 0,
        otherValue: 'test'
    }
}
```

**Done!** Your widget now appears in the toggles and can be shown/hidden.

---

## Styling Widgets

Edit `style_new.css`:

```css
.my-widget {
    /* Custom styles for your widget */
    background: var(--bg-tertiary);
    border: 1px solid var(--accent-blue);
}

.my-widget .widget-content {
    /* Content styles */
}
```

Use these CSS variables:
- `--bg-primary` - Main background
- `--bg-secondary` - Panel background
- `--bg-tertiary` - Widget background
- `--accent-blue` - Blue accent
- `--accent-purple` - Purple accent
- `--accent-green` - Green (success)
- `--accent-red` - Red (danger)
- `--accent-yellow` - Yellow (warning)

---

## Handling Robot Data

### Receiving Debug Data

Edit `app_new.js` → `handleDebugMessage()`:

```javascript
handleDebugMessage(robotName, data) {
    const robot = this[robotName];
    
    if (data.subsystem === 'mysubsystem') {
        // Update robot state
        robot.myData.someValue = data.data.value;
    }
}
```

### Sending Commands

```javascript
// From a widget
this.sendCommand('storm', 'run_script', { script_id: 'my_script' });

// Or use helper methods
this.startRobotDebug('storm');
this.stopRobot('necron');
```

---

## View Modes

### Both View
- Shows Storm and Necron side-by-side
- Good for comparing robot states
- Widgets are in compact mode

### Single View (Storm/Necron)
- Shows one robot in detail
- Expanded widgets with more info
- More screen space per widget

---

## Responsive Design

Dashboard adapts to screen size:

- **Desktop (>1200px)**: Both view shows 2 columns
- **Tablet (768-1200px)**: Both view becomes single column
- **Mobile (<768px)**: Optimized single-column layout

---

## Troubleshooting

### Robots Not Connecting

1. Check `config.js` has correct IPs
2. Verify robots are running interface servers
3. Check browser console for errors
4. Try accessing directly: `http://robot-ip:8080`

### Widgets Not Showing

1. Check widget is toggled on (bottom bar)
2. Verify data is being received (browser console)
3. Check robot is sending debug data

### Camera Feed Not Appearing

1. Robot must be in debug mode
2. Debug manager must be running (port 8765)
3. Camera must be sending frames to debug_q

---

## Performance Tips

### For Better Performance:

1. **Disable unused widgets** - Less rendering overhead
2. **Use single view** - Focus on one robot at a time
3. **Limit camera quality** - Lower JPEG quality on robot
4. **Reduce update rate** - Lower debug data frequency

### Network Tips:

1. Use wired Ethernet when possible
2. Ensure good WiFi signal
3. Use 5GHz WiFi (less interference)
4. Keep robots on same network as laptop

---

## Deployment

### Option 1: Serve from Laptop

```bash
# Simple Python HTTP server
cd hypemage/client
python -m http.server 8000

# Access at http://localhost:8000/index_new.html
```

### Option 2: Serve from Robot

Copy client files to robot and use interface server to serve them.

Edit `hypemage/interface.py`:

```python
# Mount client directory
client_dir = Path(__file__).parent / 'client'
app.mount("/", StaticFiles(directory=str(client_dir), html=True), name="client")
```

Access at `http://robot-ip:8080/index_new.html`

---

## Future Enhancements

Easy to add:

- [ ] Field visualization (top-down view)
- [ ] Motor command interface (manual control)
- [ ] Strategy selector
- [ ] Performance graphs (Chart.js)
- [ ] Video recording
- [ ] Screenshot capture
- [ ] Multi-game session tracking
- [ ] Robot health monitoring
- [ ] Battery status widget

---

## Tech Stack

- **Vue.js 3** - Reactive UI framework
- **Chart.js** - Graphing (for future widgets)
- **WebSocket API** - Real-time communication
- **CSS Grid/Flexbox** - Responsive layout
- **ES6 Modules** - Modular JavaScript

**No build step required!** Pure HTML/CSS/JS with CDN libraries.

---

## Summary

- ✅ Connect to multiple robots
- ✅ Three view modes (both, storm, necron)
- ✅ Toggle widgets on/off
- ✅ Modular architecture
- ✅ Easy to extend
- ✅ Modern dark theme
- ✅ Responsive design

**Ready to deploy!** Just configure robot IPs and open the dashboard.
