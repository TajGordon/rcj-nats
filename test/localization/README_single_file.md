# Single File Robot Localization System

## 🚀 One Command Setup

```bash
# Install dependencies
pip install fastapi uvicorn websockets

# Run everything in one command
python localization_system.py
```

That's it! No multiple terminals, no separate processes.

## 🎯 What This Does

1. **Initializes your robot hardware** (ToF sensors + IMU)
2. **Runs the localization algorithm** (10 Hz position updates)  
3. **Starts a web server** (on port 8000)
4. **Serves the visualization webpage** (with embedded HTML/CSS/JS)
5. **Streams data in real-time** (WebSocket connection)

## 📱 Usage

1. SSH into your robot/Pi
2. Run: `python localization_system.py`
3. Open browser to: `http://your-robot-ip:8000`
4. Watch your robot move on the field in real-time!

## 🔧 Features

- ✅ **Single file** - everything in one place
- ✅ **Single process** - no juggling multiple terminals  
- ✅ **Auto hardware detection** - finds your sensors automatically
- ✅ **Embedded web interface** - no external HTML files needed
- ✅ **Real-time updates** - 10 Hz localization + live web display
- ✅ **Error handling** - graceful failure and recovery
- ✅ **Clean shutdown** - Ctrl+C stops everything properly

## 🐛 Troubleshooting

- **"Hardware initialization failed"** → Check I2C connections
- **"Import errors"** → Run `pip install fastapi uvicorn websockets`
- **"Can't connect to webpage"** → Make sure port 8000 isn't blocked
- **"No ToF sensors"** → Configure your sensors in config.py

## 🎮 SSH Workflow

```bash
# SSH into robot
ssh pi@your-robot-ip

# Navigate to localization folder  
cd /path/to/localization

# Run the complete system
python localization_system.py
```

Then on your laptop, open: `http://your-robot-ip:8000`

**No more juggling multiple SSH sessions!** 🎉