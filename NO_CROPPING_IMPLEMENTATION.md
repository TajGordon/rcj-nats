# No Cropping - Mirror Mask Only Implementation

## Changes Made

### Problem
The camera system was cropping frames to the mirror bounding box, which could cause:
1. Mirror detection to fail if it received a cropped frame
2. Loss of mirror tracking between detection cycles
3. Confusion with coordinate systems (cropped vs full frame)

### Solution
**Never crop, only mask!** The entire system now works with full frames and uses circular masking.

## Key Changes

### 1. `camera.py` - Core Detection Changes

#### `update_mirror_mask()`
- **Before**: Calculated crop region, updated frame_center relative to crop
- **After**: 
  - No cropping ever - `mirror_crop_region` is always `(0, 0, width, height)`
  - `frame_center_x` and `frame_center_y` are the mirror center in **full frame coordinates**
  - Mirror mask is created for the full frame
  - If detection fails, **keeps previous good detection** instead of losing it

```python
# NO CROPPING - we use full frame everywhere
self.mirror_crop_region = (0, 0, width, height)

# Frame center is just the mirror center in full frame coordinates
self.frame_center_x = center_x
self.frame_center_y = center_y
```

#### `detect_mirror_circle()`
- Added frame size validation to warn if frame might be cropped
- Stores expected frame size on first run
- Ensures detection always works with full original frame

#### `crop_to_mirror()`
- **Before**: Actually cropped the image `return image[y1:y2, x1:x2]`
- **After**: Just applies the circular mask and returns full frame
- Renamed internally but kept function name for compatibility

```python
def crop_to_mirror(self, image):
    """Apply mirror mask to the image (returns full frame with mask applied)"""
    # Apply mask instead of cropping
    return self.apply_mirror_mask(image)
```

#### `detect_ball()` and `detect_goals()`
- Now work with full masked frames
- Ball/goal coordinates are in **full frame coordinates**
- Updated comments to reflect this

### 2. `test_mirror_visualization.py` - Visualization Changes

#### Removed `create_square_mirror_view()`
Created `create_full_frame_visualization()` instead:
- Works with full frames (no cropping or resizing)
- Applies mirror mask (black outside circle)
- Draws all overlays on full frame:
  - Green circle for mirror boundary
  - Crosshair at center
  - Cyan arrow for forward direction
  - Orange circle and line for ball
  - Info text overlays

#### Display
- Left panel: Original frame with minimal overlay
- Right panel: Full frame with mirror mask and all visualizations
- Both show the same resolution (no scaling/cropping)

## Benefits

### ✅ Reliability
- Mirror detection never loses tracking
- Failed detection keeps previous good result
- No coordinate confusion

### ✅ Simplicity
- All coordinates in one system (full frame)
- No coordinate transformations needed
- Easier to debug

### ✅ Accuracy
- Ball/goal positions are exact in full frame
- No rounding errors from scaling
- Direct pixel coordinates

### ✅ Visualization
- See the full camera view
- Understand what the robot sees
- Better for debugging

## Coordinate System

### Before (Cropped)
```
Full Frame → Detect Mirror → Crop → Adjust Coordinates → Detect Objects
                                ↓
                        Object coords in cropped frame
                        Need to translate back to full frame
```

### After (Masked)
```
Full Frame → Detect Mirror → Apply Mask → Detect Objects
                                    ↓
                        Object coords in full frame
                        No translation needed!
```

## Important Notes

### For Ball Detection
- `ball_result.center_x`, `ball_result.center_y` are in **full frame coordinates**
- `camera.frame_center_x`, `camera.frame_center_y` are the **mirror center in full frame**
- `horizontal_error` calculation remains the same
- No coordinate adjustments needed!

### For Visualization
```python
# Everything is in full frame coordinates now
ball_x = ball_result.center_x  # Already in full frame
ball_y = ball_result.center_y  # Already in full frame
center_x = camera.frame_center_x  # Mirror center in full frame
center_y = camera.frame_center_y  # Mirror center in full frame

# Draw directly - no coordinate transformation!
cv2.circle(frame, (ball_x, ball_y), radius, color, thickness)
cv2.line(frame, (center_x, center_y), (ball_x, ball_y), color, thickness)
```

### For Chase Ball Logic
```python
# No changes needed - horizontal_error already correct
ball_angle_from_center = ball.horizontal_error * 90.0  # Still works!
```

## Testing

### What to Verify

1. **Mirror Detection**
   - Run visualization tool
   - Green circle should align with physical mirror
   - Click "Redetect Mirror" - should re-detect correctly
   - Mirror should never be "lost" during operation

2. **Ball Tracking**
   - Place ball at different positions
   - Orange circle should appear around ball
   - Orange line should connect mirror center to ball
   - Angle and distance should be accurate

3. **Coordinate Accuracy**
   - Ball position numbers should match what you see
   - No jumps or discontinuities in position
   - Smooth tracking as ball moves

4. **Full Frame Display**
   - Both visualization panels show same dimensions
   - No cropping or scaling artifacts
   - Can see entire camera view

## Migration Notes

### If You Had Code Using Cropped Coordinates

**Before**:
```python
# Ball was in cropped coordinates
ball_x_full = ball_result.center_x + crop_region[0]
ball_y_full = ball_result.center_y + crop_region[1]
```

**After**:
```python
# Ball is already in full frame coordinates
ball_x_full = ball_result.center_x  # No adjustment needed!
ball_y_full = ball_result.center_y  # No adjustment needed!
```

### Camera Methods That Changed Behavior

- `crop_to_mirror()` - Now returns masked full frame, not cropped
- `update_mirror_mask()` - Sets `frame_center` to full frame coords
- All detection methods - Return full frame coordinates

## Files Modified

1. **`hypemage/camera.py`**
   - `update_mirror_mask()` - No cropping, keeps failed detections
   - `detect_mirror_circle()` - Frame size validation
   - `crop_to_mirror()` - Returns masked full frame
   - `detect_ball()` - Works with full frames
   - `detect_goals()` - Works with full frames

2. **`hypemage/test_mirror_visualization.py`**
   - `create_full_frame_visualization()` - New full frame viz
   - `frame_broadcaster()` - Uses new visualization
   - HTML - Updated panel titles

## Summary

🎯 **Core Principle**: Never crop, always use the full frame with circular masking

✅ **Result**: More reliable, simpler, and more accurate detection system

📊 **Visualization**: Shows exactly what the robot sees without any transformations

---

**Status**: ✅ Complete  
**Date**: October 11, 2025
