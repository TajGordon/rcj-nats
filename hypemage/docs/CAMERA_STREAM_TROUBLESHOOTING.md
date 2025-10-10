# Camera Stream Troubleshooting Guide

## Problem: Nothing appears at http://m7.local:8766/stream

### Common Issues & Fixes

## 1. Wrong URL Format ❌

**WRONG:**
- `necron@m7.local:8766/stream` ❌
- `m7.local:8766/stream` ❌ (missing http://)
- `http://m7.local:8766` ❌ (missing /stream)

**CORRECT:**
- `http://m7.local:8766/stream` ✅
- `http://m7.local:8766/` ✅ (test page with embedded stream)

## 2. Script Not Running

**Check if running:**
```bash
# On the robot (m7/Necron)
ps aux | grep camera_stream
```

**Start the script:**
```bash
# Method 1: Direct run
python -m hypemage.scripts.camera_stream

# Method 2: Via interface (from dashboard)
# Click the "Camera" button
```

**Expected output:**
```
[camera_stream] Camera stream starting...
[camera_stream] Starting camera stream HTTP server for necron
[camera_stream] HTTP server: http://0.0.0.0:8766
[camera_stream] Camera initialized
[camera_stream] HTTP server started on port 8766
[camera_stream] Stream URL: http://0.0.0.0:8766/stream
```

## 3. Camera Initialization Failed

**Symptoms:**
- Script exits immediately
- Error: "Failed to initialize camera"

**Diagnostic test:**
```bash
# Run camera test on the robot
python -m hypemage.scripts.test_camera_direct
```

**Common causes:**
- Camera cable disconnected
- Camera in use by another process
- Permission issues
- Picamera2 not installed

**Fixes:**
```bash
# Check camera connection
vcgencmd get_camera

# Kill processes using camera
sudo pkill -f camera
sudo pkill -f libcamera

# Fix permissions
sudo usermod -a -G video $USER
# Then logout and login again
```

## 4. Missing aspect_ratio Config (FIXED)

**Symptom:** Stream crashes when goal detected

**Fix:** Already applied in camera.py:
```python
self.blue_goal_config = {
    ...
    'aspect_ratio_min': 0.3,
    'aspect_ratio_max': 5.0
}
```

## 5. Port Not Accessible

**Test port accessibility:**
```bash
# From your laptop
curl http://m7.local:8766/
```

**Expected response:**
HTML page with "Camera Stream - necron"

**If connection refused:**
- Check firewall on robot
- Verify robot hostname: `ping m7.local`
- Check port is correct (8766 for Necron, 8765 for Storm)

## 6. Browser Caching Issue

**Try:**
- Hard refresh: Ctrl+F5 (Windows) or Cmd+Shift+R (Mac)
- Open in incognito/private window
- Clear browser cache
- Try different browser

## Diagnostic Steps

### Step 1: Run Minimal Test
```bash
# On the robot
python -m hypemage.scripts.test_stream_minimal
```

This will:
- Test camera initialization
- Capture test frame
- Start minimal stream
- Show detailed logs for every frame

### Step 2: Check Logs
Watch terminal output when you connect. Should see:
```
[HH:MM:SS] Client connected from 192.168.x.x
[HH:MM:SS] Frame 0: shape=(480, 640, 3), dtype=uint8
[HH:MM:SS] Encoded JPEG size: 45678 bytes
[HH:MM:SS] Sent frame 0
```

If you DON'T see "Client connected", your browser isn't reaching the server.
If you see "Got None frame", camera hardware issue.

### Step 3: Direct Camera Test
```bash
# On the robot
python -m hypemage.scripts.test_camera_direct
```

Should show:
```
✓ Camera initialized successfully
✓ Frame captured: shape=(480, 640, 3), dtype=uint8
✓ Ball detection ran
✓ Goal detection ran
✓ Captured 10/10 frames successfully
```

## Quick Fixes Checklist

- [ ] Use correct URL: `http://m7.local:8766/stream`
- [ ] Script is running (check `ps aux | grep camera_stream`)
- [ ] Camera cable connected
- [ ] No other process using camera
- [ ] Robot reachable: `ping m7.local` works
- [ ] Port accessible: `curl http://m7.local:8766/` works
- [ ] Browser hard-refresh (Ctrl+F5)
- [ ] Try test page: `http://m7.local:8766/` (includes stream)

## Still Not Working?

### Get Full Diagnostics
```bash
# On the robot, run:
python -m hypemage.scripts.test_camera_direct > camera_test.log 2>&1
python -m hypemage.scripts.test_stream_minimal

# Then check the logs for errors
cat camera_test.log
```

### Check Network Path
```bash
# From your laptop
ping m7.local
nslookup m7.local
curl -v http://m7.local:8766/
```

### Check Process Status
```bash
# On the robot
ps aux | grep camera
netstat -tulpn | grep 8766
```

## Working Indicator

When everything is working, you should see:
1. ✅ Script prints "HTTP server started on port 8766"
2. ✅ Browser loads the URL without error
3. ✅ Video feed appears with green text overlay
4. ✅ Frame counter increments
5. ✅ Detection overlays appear when objects visible

## Performance Tips

If stream is slow/laggy:
- Reduce quality in camera_stream.py: `IMWRITE_JPEG_QUALITY, 70`
- Lower FPS: `await asyncio.sleep(1/15)` # 15 FPS instead of 30
- Check network: `ping m7.local` should be <10ms
