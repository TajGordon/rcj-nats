# Close Zone Detection - No Mirror Mask

## Confirmed: Close Zone Searches Raw Frame

The close ball zone detection **does NOT apply the mirror mask**. This is intentional and beneficial.

## How It Works

### Close Zone Detection (First Priority):
```python
# Extract close zone region from RAW FRAME (no mask)
close_zone = frame[y1:y2, x1:x2]

# Convert to HSV and detect orange
hsv_zone = cv2.cvtColor(close_zone, cv2.COLOR_BGR2HSV)
mask_zone = cv2.inRange(hsv_zone, self.lower_orange, self.upper_orange)
```

**Key Point:** Uses `frame` directly, not `self.crop_to_mirror(frame)`

### Normal Detection (Fallback):
```python
# Apply mask to full frame
masked_frame = self.crop_to_mirror(frame)

# Convert to HSV and detect orange
hsv = cv2.cvtColor(masked_frame, cv2.COLOR_BGR2HSV)
mask = cv2.inRange(hsv, self.lower_orange, self.upper_orange)
```

**Key Point:** Uses `self.crop_to_mirror(frame)` which applies the mirror mask

## Why No Mask in Close Zone?

### Advantages:
1. **Works outside mirror circle**
   - Dribbler area may extend beyond mirror
   - No dependency on mirror detection

2. **More reliable**
   - Not affected by mirror detection failures
   - Searches exact rectangle specified in config

3. **Simpler logic**
   - Direct rectangle extraction
   - No coordinate transformations

4. **Faster**
   - Smaller region to process
   - No mask application overhead

### This Means:
✅ Zone works even if positioned outside mirror  
✅ Zone works if mirror detection fails  
✅ Zone searches **entire rectangle** regardless of mirror  
✅ Ball detected in zone even if outside mirror circle  

## Configuration Impact

Since the close zone ignores the mirror mask, you can position it anywhere:

```json
"close_ball_zone": {
  "center_y_offset": -120,  // Can be outside mirror!
  "width": 150,
  "height": 100
}
```

The zone will search the full rectangle at that position, regardless of where the mirror circle is detected.

## Visualization

In the visualization overlay:
- **Purple/Magenta rectangle** shows the exact search area
- This rectangle is **not masked** by the mirror circle
- Ball can be detected anywhere within this rectangle

## Code Location

**File:** `hypemage/camera.py`

**Method:** `_detect_ball_in_close_zone()`

**Line:** Extracts region from raw frame:
```python
close_zone = frame[y1:y2, x1:x2]
```

**NOT using:**
```python
# This would apply mask (not used in close zone)
masked_frame = self.crop_to_mirror(frame)
close_zone = masked_frame[y1:y2, x1:x2]
```

## Summary

| Feature | Close Zone | Normal Detection |
|---------|-----------|------------------|
| **Mask Applied** | ❌ No | ✅ Yes |
| **Search Area** | Small rectangle | Full mirror circle |
| **Works Outside Mirror** | ✅ Yes | ❌ No |
| **Sensitivity** | Extra high | Normal |
| **Priority** | 1st (checked first) | 2nd (fallback) |

The close zone is specifically designed to work **independently** of the mirror mask, making it perfect for detecting balls in the dribbler area even if that area is partially outside the mirror's view! 🎯
