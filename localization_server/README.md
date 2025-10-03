# 🤖 Robot Localization System

Real-time robot localization system using ToF sensors and IMU, with web-based visualization.

## 🔧 Setup

### 1. Install Server Dependencies

```bash
cd localization_server
pip install -r requirements.txt
```

### 2. Install Robot Dependencies

```bash
# On the robot/development machine
pip install websockets asyncio
```

### 3. Hardware Requirements

- **IMU**: BNO08X connected via I2C
- **ToF Sensors**: Multiple VL53L0X or similar ToF sensors on I2C bus
- **Microcontroller**: Raspberry Pi or similar with CircuitPython/Python support

## 🚀 Running the System

### Step 1: Start the Web Server

```bash
cd localization_server
python main.py
```

The server will start on `http://localhost:8002`

### Step 2: Run the Robot Localization

```bash
cd test/localization
python localizer.py
```

### Step 3: View Results

Open your browser to `http://localhost:8002` to see:
- Real-time robot position and angle
- Live field visualization
- Localization error metrics
- Connection status

## 📡 System Architecture

```
Robot Hardware → localizer.py → WebSocket → Web Server → Browser
    ↓                ↓             ↓          ↓         ↓
[ToF + IMU]    [Localization]  [JSON Data] [FastAPI] [Field View]
```

## 🎯 Features

### Robot Side (`localizer.py`)
- ✅ Real hardware ToF sensor integration
- ✅ IMU angle reading  
- ✅ Particle filter localization algorithm
- ✅ WebSocket data transmission
- ✅ Auto-retry connection logic
- ✅ 10 Hz update rate

### Web Server (`main.py`)
- ✅ FastAPI WebSocket server
- ✅ Multiple client support
- ✅ Real-time data broadcasting
- ✅ Static file serving

### Web Interface (`templates/index.html`)
- ✅ Live field rendering (2430x1820mm RoboCup field)
- ✅ Robot position and orientation display
- ✅ Real-time metrics (position, angle, error)
- ✅ Connection status indicator
- ✅ Responsive design

## 🔧 Configuration

Edit `config.py` to configure your ToF sensors:

```python
if host == 'your_robot_name':
    tof_addrs = [0x29, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F, 0x30]
    tof_offsets = {addr: (0, 0) for addr in tof_addrs}  # Physical offsets
    tof_angles = {  # Sensor mounting angles in degrees
        0x29: 0,    # Front
        0x2A: 45,   # Front-right
        0x2B: 90,   # Right
        0x2C: 135,  # Back-right
        0x2D: 180,  # Back
        0x2E: -135, # Back-left
        0x2F: -90,  # Left
        0x30: -45,  # Front-left
    }
```

## 🐛 Troubleshooting

### "Connection refused" error
- Make sure the web server is running first
- Check that port 8002 is not blocked by firewall

### "Hardware initialization failed"
- Verify I2C connections to ToF sensors and IMU
- Check sensor addresses with `i2cdetect -y 1`
- Ensure proper power supply to sensors

### No sensor data
- Check ToF sensor configuration in `config.py`
- Verify sensor addresses and angles
- Test individual sensors with ToF example code

### Web page not updating
- Check browser console for WebSocket errors
- Verify server is receiving data (check server logs)
- Try refreshing the page

## 📊 Performance

- **Localization Rate**: 10 Hz
- **Web Update Rate**: Real-time (as fast as data arrives)
- **Latency**: < 100ms end-to-end
- **Accuracy**: Depends on ToF sensor placement and field calibration

## 🎮 Usage Tips

1. **Calibration**: Place robot at known position and verify readings
2. **Sensor Placement**: Mount ToF sensors around robot perimeter for 360° coverage
3. **Field Setup**: Ensure field walls match the dimensions in `config.py`
4. **Network**: Use local network for best performance (avoid WiFi lag)

## 🚀 Next Steps

- Add data logging and replay functionality
- Implement advanced filtering (Kalman, particle filter)
- Add multi-robot support
- Create mobile-friendly interface
- Add sensor health monitoring