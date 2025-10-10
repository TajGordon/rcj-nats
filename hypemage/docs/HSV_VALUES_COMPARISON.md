# HSV Values - Current Configuration

## Current HSV Values in Use

| Robot | Color | Parameter | Current Value | Notes |
|-------|-------|-----------|---------------|-------|
| **Storm** | **Ball (Orange)** | H min | 0 | Red-orange range |
| | | H max | 20 | Wide orange range |
| | | S min | 140 | Moderate saturation |
| | | S max | 255 | Full saturation |
| | | V min | 150 | Bright minimum |
| | | V max | 255 | Full brightness |
| **Necron** | **Ball (Orange)** | H min | 0 | Red-orange range |
| | | H max | 20 | Wide orange range |
| | | S min | 100 | Lower saturation |
| | | S max | 255 | Full saturation |
| | | V min | 30 | Dark minimum |
| | | V max | 255 | Full brightness |
| **Both** | **Blue Goal** | H min | 100 | Blue range |
| | | H max | 120 | Standard blue |
| | | S min | 150 | Moderate saturation |
| | | S max | 255 | Full saturation |
| | | V min | 50 | Dark minimum |
| | | V max | 255 | Full brightness |
| **Both** | **Yellow Goal** | H min | 20 | Yellow range |
| | | H max | 40 | Standard yellow |
| | | S min | 100 | Moderate saturation |
| | | S max | 255 | Full saturation |
| | | V min | 100 | Bright minimum |
| | | V max | 255 | Full brightness |

## Key Insights

### Ball Detection (Orange)
- **Storm**: Higher saturation (140) and brightness (150) - Better for well-lit conditions
- **Necron**: Lower saturation (100) and brightness (30) - Better for varied lighting
- **Both**: Wide hue range (0-20) - Catches various orange shades
- **Impact**: Different robots optimized for different lighting conditions

### Blue Goal
- **Standard Range**: 100-120 hue - Covers typical blue spectrum
- **Moderate Saturation**: 150 minimum - Filters pale blues
- **Low Brightness**: 50 minimum - Includes darker blues
- **Impact**: Reliable blue goal detection across lighting

### Yellow Goal  
- **Standard Range**: 20-40 hue - Covers yellow spectrum
- **Moderate Saturation**: 100 minimum - Filters pale yellows
- **High Brightness**: 100 minimum - Only bright yellows
- **Impact**: Good yellow detection, may miss darker yellows

## Current Configuration Analysis

### Storm Robot (Higher Performance)
- ✅ Higher saturation (140) - Better color discrimination
- ✅ Higher brightness (150) - Works well in good lighting
- ✅ Wide hue range (0-20) - Catches various orange balls
- ⚠️ May struggle in dim lighting

### Necron Robot (More Flexible)
- ✅ Lower saturation (100) - Works in varied lighting
- ✅ Lower brightness (30) - Detects balls in shadows
- ✅ Same hue range (0-20) - Consistent ball detection
- ⚠️ May have more false positives in bright conditions

## Visual Representation

### Ball - Orange Detection Range
```
Storm:  H=[0-20°] (20° range) 🔴🟠🟡 (red-orange-yellow)
        S=[140-255] (moderate to high saturation)
        V=[150-255] (bright only)

Necron: H=[0-20°] (20° range) 🔴🟠🟡 (red-orange-yellow)  
        S=[100-255] (low to high saturation)
        V=[30-255] (dark to bright)
```

### Blue Goal Detection Range
```
Both:   H=[100-120°] (20° range) 💙💙 (standard blue)
        S=[150-255] (moderate to high saturation)
        V=[50-255] (dark to bright)
```

### Yellow Goal Detection Range
```
Both:   H=[20-40°] (20° range) 🟡🟡 (standard yellow)
        S=[100-255] (moderate to high saturation)
        V=[100-255] (bright only)
```

## Current Status

These values are **currently in use** in the system and should work for:
- ✅ Ball detection in various lighting conditions
- ✅ Goal detection for both blue and yellow goals
- ✅ Different robot configurations (Storm vs Necron)

### Robot-Specific Optimizations:
- **Storm**: Optimized for bright, consistent lighting
- **Necron**: Optimized for varied/dim lighting conditions

### If Detection Issues Occur:
1. **Lighting**: Check if lighting matches robot's optimization
2. **Camera**: Verify camera exposure and white balance
3. **Objects**: Ensure balls/goals are within detection ranges
4. **Calibration**: Use camera calibration tools if needed

The HSV ranges are **currently configured and functional** ✅
