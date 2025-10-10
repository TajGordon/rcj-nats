# HSV Configuration Fix - Updated to Match Nationals

## Problem
The HSV color ranges in `hypemage/config.json` were using generic/placeholder values that didn't match the calibrated values from the nationals competition implementation.

## Solution
Updated `hypemage/config.json` to use the proven HSV ranges from `nationals/config.json`.

## Changes Applied

### Ball (Orange) Detection
**OLD (Generic values):**
```json
"lower": [10, 100, 100],
"upper": [20, 255, 255]
```

**NEW (Calibrated values from nationals):**
```json
"lower": [0, 222, 144],
"upper": [4, 255, 255]
```

**Analysis:**
- Much narrower Hue range (0-4 vs 10-20) - More precise orange detection
- Much higher Saturation minimum (222 vs 100) - Filters out pale/washed out colors
- Higher Value minimum (144 vs 100) - Filters out dark areas

### Blue Goal Detection
**OLD:**
```json
"lower": [100, 150, 50],
"upper": [120, 255, 255]
```

**NEW:**
```json
"lower": [92, 242, 155],
"upper": [110, 255, 236]
```

**Analysis:**
- Slightly wider Hue range (92-110 vs 100-120)
- Much higher Saturation minimum (242 vs 150) - Only very saturated blues
- Much higher Value minimum (155 vs 50) - Only bright blues
- Slightly lower Value maximum (236 vs 255) - Filters out specular highlights

### Yellow Goal Detection
**OLD:**
```json
"lower": [20, 100, 100],
"upper": [40, 255, 255]
```

**NEW:**
```json
"lower": [14, 202, 97],
"upper": [23, 255, 177]
```

**Analysis:**
- Narrower Hue range (14-23 vs 20-40) - More specific yellow
- Much higher Saturation minimum (202 vs 100) - Only vibrant yellows
- Lower Value maximum (177 vs 255) - Filters out bright highlights

## Format Comparison

### Nationals Format (Flat Array)
```json
"ball": [0, 222, 144, 4, 255, 255]
```
Loaded as:
```python
ColorRange(colours["ball"][:3], colours["ball"][3:])
# lower = [0, 222, 144]
# upper = [4, 255, 255]
```

### Hypemage Format (Nested Structure)
```json
"ball": {
  "lower": [0, 222, 144],
  "upper": [4, 255, 255],
  "min_area": 100,
  "max_area": 50000
}
```
Loaded as:
```python
self.lower_orange = np.array(ball_cfg.get("lower", [0, 222, 144]))
self.upper_orange = np.array(ball_cfg.get("upper", [4, 255, 255]))
```

Both formats work correctly - hypemage just uses a more explicit nested structure with additional parameters (min_area, max_area).

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

## Why These Values Matter

The nationals config values are **calibrated** for the actual competition environment:
- Specific lighting conditions
- Actual ball/goal colors used in RoboCup Junior
- Tested and refined through competition experience

The old generic values were likely causing:
- ❌ Missing actual orange balls (too narrow hue range)
- ❌ Detecting non-ball orange objects (too low saturation)
- ❌ False positives from pale/washed colors
- ❌ Missing goals in different lighting

The new calibrated values provide:
- ✅ Precise color matching
- ✅ Better noise rejection (high saturation minimums)
- ✅ Consistent detection across lighting variations
- ✅ Proven in competition environment

## Testing Recommendations

After updating config, test detection with:

1. **Actual game objects** - Real RCJ ball and goals
2. **Different lighting** - Bright, normal, dim conditions
3. **Different angles** - Ball/goals at various positions
4. **Background noise** - Other colored objects in view

Expected improvements:
- More reliable ball detection
- Fewer false positives
- Better color discrimination
- Consistent performance

## Future Calibration

If you need to recalibrate for different environments:

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
