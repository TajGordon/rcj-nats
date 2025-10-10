# HSV Configuration - Current System Values

## Current Configuration
The HSV color ranges in `hypemage/config.json` are currently configured with robot-specific values optimized for different lighting conditions.

## Current Values in Use

### Ball (Orange) Detection

**Storm Robot:**
```json
"lower": [0, 140, 150],
"upper": [20, 255, 255]
```

**Necron Robot:**
```json
"lower": [0, 100, 30],
"upper": [20, 255, 255]
```

**Analysis:**
- **Storm**: Higher saturation (140) and brightness (150) - Optimized for bright lighting
- **Necron**: Lower saturation (100) and brightness (30) - Optimized for varied/dim lighting
- **Both**: Wide hue range (0-20) - Catches various orange ball shades

### Blue Goal Detection
**Both Robots:**
```json
"lower": [100, 150, 50],
"upper": [120, 255, 255]
```

**Analysis:**
- Standard blue hue range (100-120) - Covers typical blue spectrum
- Moderate saturation minimum (150) - Filters pale blues
- Low brightness minimum (50) - Includes darker blues
- Full brightness maximum (255) - Includes bright blues

### Yellow Goal Detection
**Both Robots:**
```json
"lower": [20, 100, 100],
"upper": [40, 255, 255]
```

**Analysis:**
- Standard yellow hue range (20-40) - Covers yellow spectrum
- Moderate saturation minimum (100) - Filters pale yellows
- High brightness minimum (100) - Only bright yellows
- Full brightness maximum (255) - Includes bright yellows

## Configuration Format

### Current Hypemage Format (Nested Structure)
```json
"ball": {
  "lower": [0, 140, 150],
  "upper": [20, 255, 255],
  "min_area": 0,
  "max_area": 500
}
```
Loaded as:
```python
self.lower_orange = np.array(ball_cfg.get("lower", [0, 140, 150]))
self.upper_orange = np.array(ball_cfg.get("upper", [20, 255, 255]))
```

The format includes additional parameters:
- `min_area`: Minimum contour area to filter noise
- `max_area`: Maximum contour area to avoid huge objects

## HSV Color Space Quick Reference

**Hue (H):** 0-179 in OpenCV (0-360° mapped to 0-179)
- 0-10: Red/Orange
- 10-25: Yellow
- 90-110: Blue
- 50-70: Green

**Saturation (S):** 0-255
- 0: Gray (no color)
- 100-150: Pale/washed out
- 200-255: Vibrant/saturated

**Value (V):** 0-255
- 0: Black
- 50-100: Dark
- 150-200: Bright
- 255: Maximum brightness

## Why These Values Work

The current config values are **optimized** for different robot scenarios:
- **Storm**: High-performance values for consistent lighting
- **Necron**: Flexible values for varied lighting conditions
- **Both**: Standard goal detection ranges

### Current Configuration Benefits:
- ✅ **Storm**: Better precision in good lighting conditions
- ✅ **Necron**: More robust detection in varied lighting
- ✅ **Both**: Reliable goal detection across conditions
- ✅ **Flexible**: Different robots optimized for different environments

## Testing Recommendations

To verify current configuration works:

1. **Test with actual RCJ balls and goals**
2. **Test in different lighting conditions**:
   - Storm: Test in bright, consistent lighting
   - Necron: Test in varied/dim lighting
3. **Test at different angles and distances**
4. **Test with background noise** (other colored objects)

### Expected Performance:
- **Storm**: High precision in good lighting
- **Necron**: Robust detection in varied lighting
- **Both**: Reliable goal detection

## Calibration Tools

If you need to adjust values for different environments:

1. Use the calibration script (if available)
2. Capture sample images
3. Use HSV color picker to find ranges
4. Test with actual objects
5. Adjust Saturation/Value minimums to filter noise
6. Update config.json with new values

Tools for calibration:
- OpenCV trackbars for live HSV tuning
- Color picker tools
- Sample image analysis scripts
