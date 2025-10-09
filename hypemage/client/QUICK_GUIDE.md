# Multi-Robot Dashboard - Quick Guide

## What Was Created

A complete multi-robot dashboard with:

✅ **Three view modes**: Both (side-by-side), Storm, Necron  
✅ **Modular widgets**: Camera, Motors, ToF, Logs, Status, etc.  
✅ **Toggle visibility**: Show/hide widgets via bottom bar  
✅ **Vue.js powered**: Reactive, modern framework  
✅ **Easy to extend**: Add new widgets with minimal code  

---

## Files Created

```
client/
├── index_new.html              # Main dashboard (Vue.js app)
├── app_new.js                  # Application logic
├── style_new.css               # Modern dark theme
├── config.js                   # Robot IP configuration
│
├── components/
│   ├── widgets.js              # All widget components
│   └── robot-connection.js     # WebSocket helper
│
└── README_DASHBOARD.md         # Complete documentation
```

**Note:** Files are named `*_new.*` to preserve your existing dashboard. Rename when ready to migrate.

---

## How to Use

### 1. Configure Robots

Edit `client/config.js`:

```javascript
const ROBOT_CONFIG = {
    storm: {
        host: '192.168.1.100',  // Your Storm IP
    },
    necron: {
        host: '192.168.1.101',  // Your Necron IP
    }
};
```

### 2. Open Dashboard

```
http://localhost:8080/index_new.html
```

Or access from robot:
```
http://storm-ip:8080/index_new.html
```

### 3. Switch Views

Bottom navigation:
- **Both** - See Storm and Necron side-by-side
- **Storm** - Focus on Storm only (expanded widgets)
- **Necron** - Focus on Necron only (expanded widgets)

### 4. Toggle Widgets

Bottom widget bar:
- ✅ Controls - Start/stop buttons
- ✅ Camera - Live feed
- ✅ Motors - Speed gauges
- ✅ Position - Localization
- ✅ ToF - Sensor radar
- ✅ Logs - Real-time logs
- ✅ Status - Robot info

Check/uncheck to show/hide!

---

## Adding Custom Widgets

### Example: Battery Widget

**1. Create component** (`components/widgets.js`):

```javascript
const BatteryWidget = defineComponent({
    name: 'BatteryWidget',
    props: ['battery', 'expanded'],
    template: `
        <div class="widget battery-widget">
            <h3>🔋 Battery</h3>
            <div class="battery-level">
                <div 
                    class="battery-fill"
                    :style="{width: battery.percentage + '%'}">
                </div>
            </div>
            <p>{{ battery.voltage }}V ({{ battery.percentage }}%)</p>
        </div>
    `
});

app.component('battery-widget', BatteryWidget);
```

**2. Add to container** (`components/widgets.js`):

```javascript
// In RobotWidgets template:
<battery-widget 
    v-if="visibleWidgets.has('battery')"
    :battery="robot.battery"
    :expanded="expanded">
</battery-widget>
```

**3. Add to config** (`config.js`):

```javascript
const WIDGET_TYPES = [
    // ...
    { id: 'battery', name: 'Battery', icon: '🔋', defaultVisible: true }
];
```

**4. Add data** (`app_new.js`):

```javascript
storm: {
    // ...
    battery: {
        voltage: 12.0,
        percentage: 75
    }
}
```

**Done!** Battery widget now appears in toggles.

---

## Architecture

```
┌─────────────────────────────────────────┐
│         Browser (Vue.js App)            │
│  ┌────────────┐      ┌────────────┐    │
│  │   Storm    │      │   Necron   │    │
│  │  Widgets   │      │  Widgets   │    │
│  └──────┬─────┘      └──────┬─────┘    │
└─────────┼────────────────────┼──────────┘
          │                    │
          │ WebSocket          │ WebSocket
          │ :8080/:8765        │ :8080/:8765
          │                    │
          ▼                    ▼
    ┌──────────┐         ┌──────────┐
    │  Storm   │         │  Necron  │
    │  Robot   │         │  Robot   │
    └──────────┘         └──────────┘
```

**Two connections per robot:**
1. Interface WebSocket (ws://robot:8080/ws) - Commands & status
2. Debug WebSocket (ws://robot:8765) - Camera, motors, sensors

---

## Widget System

### How Widgets Work

1. **Component** - Vue component in `components/widgets.js`
2. **Registration** - `app.component('widget-name', Component)`
3. **Container** - Added to `RobotWidgets` template with `v-if`
4. **Toggle** - Uses `visibleWidgets.has('widget-id')`
5. **Data** - Props passed from robot state in `app_new.js`

### Widget Template

```javascript
const MyWidget = defineComponent({
    name: 'MyWidget',
    props: ['data', 'expanded'],  // Data from robot, expanded flag
    template: `
        <div :class="['widget', {expanded}]">
            <h3>Icon Name</h3>
            <div class="content">
                <!-- Your UI here -->
            </div>
        </div>
    `
});
```

---

## Styling

### CSS Variables

```css
:root {
    --bg-primary: #0a0e27;       /* Main background */
    --bg-secondary: #1a1f3a;     /* Panels */
    --bg-tertiary: #2a2f4a;      /* Widgets */
    --accent-blue: #00d4ff;      /* Blue accent */
    --accent-purple: #b74dff;    /* Purple accent */
    --accent-green: #00ff88;     /* Success/running */
    --accent-red: #ff4d4d;       /* Danger/stop */
    --accent-yellow: #ffdd00;    /* Warning */
}
```

### Widget Styling

```css
.my-widget {
    background: var(--bg-tertiary);
    padding: 1.5rem;
    border-radius: 8px;
    border: 1px solid var(--border-color);
}

.my-widget:hover {
    border-color: var(--accent-blue);
    box-shadow: 0 4px 12px rgba(0, 212, 255, 0.2);
}
```

---

## Performance

### Optimizations

✅ **Conditional rendering** - Widgets only render if visible  
✅ **Reactive updates** - Vue updates only changed data  
✅ **WebSocket streams** - Efficient binary protocol  
✅ **JPEG compression** - Camera uses compressed frames  

### Tips

1. Hide unused widgets (less DOM updates)
2. Use single view for better performance
3. Lower camera quality if needed
4. Reduce debug data frequency

---

## Migration from Old Dashboard

### Option 1: Test Side-by-Side

Keep both dashboards:
- Old: `http://robot:8080/index.html`
- New: `http://robot:8080/index_new.html`

### Option 2: Replace Entirely

```bash
cd hypemage/client

# Backup old files
mv index.html index_old.html
mv app.js app_old.js
mv style.css style_old.css

# Use new files
mv index_new.html index.html
mv app_new.js app.js
mv style_new.css style.css
```

---

## Troubleshooting

### Robots Not Connecting

```javascript
// Check config.js has correct IPs
const ROBOT_CONFIG = {
    storm: { host: '192.168.1.100' },  // ← Verify this
    necron: { host: '192.168.1.101' }  // ← Verify this
};
```

### Widgets Not Appearing

1. Check bottom toggle bar - widget enabled?
2. Browser console - any errors?
3. Robot sending data? Check WebSocket messages

### Camera Feed Blank

1. Robot in debug mode?
2. Debug manager running (port 8765)?
3. Camera sending to `debug_q`?

---

## Summary

### What You Get

✅ Multi-robot dashboard (Storm + Necron)  
✅ Three view modes (both/storm/necron)  
✅ Modular widget system  
✅ Toggle widget visibility  
✅ Modern dark theme  
✅ Responsive design  
✅ Easy to extend  

### How to Use

1. Edit `config.js` with robot IPs
2. Open `index_new.html` in browser
3. Click view buttons at bottom
4. Toggle widgets on/off

### How to Extend

1. Create widget component
2. Register with `app.component()`
3. Add to `RobotWidgets` template
4. Add to `WIDGET_TYPES` config
5. Done!

**Ready to use! Just configure IPs and open dashboard.** 🚀
