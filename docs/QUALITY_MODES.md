# Quality Modes Guide

This document explains the three quality modes available in the Raster to SVG Converter.

## Overview

| Mode | Preprocessing | SVG Optimization | Time | File Size | Best For |
|------|--------------|------------------|------|-----------|----------|
| **Fast** | None | Light | < 1s | 30-50KB | Simple graphics, clean images |
| **Standard** | Color reduction + Denoise + Contrast | Standard | 1-3s | 20-40KB | Most images, photos |
| **High** | Standard + NLM + Sharpen + Edges | Aggressive | 3-10s | 15-30KB | Complex images, professional work |

## Fast Mode

### Pipeline
```
Input Image → VTracer/Potrace → Light SVG Optimization → Output
```

### Characteristics
- **Speed**: Fastest option (< 1 second)
- **Preprocessing**: None
- **Optimization**: Metadata removal only
- **Quality**: Good for simple images
- **File Size**: Moderate (30-50KB typical)

### When to Use
- Simple graphics and icons
- Clean line art
- Screenshots
- When speed is critical
- Batch processing where quality is less important

### Limitations
- No noise reduction
- No color optimization
- May produce jagged edges on complex images
- Larger file sizes

## Standard Mode

### Pipeline
```
Input Image → Color Reduction (32 colors) → Bilateral Denoise → CLAHE Contrast
    → VTracer/Potrace → Scour Optimization → Output
```

### Characteristics
- **Speed**: Balanced (1-3 seconds)
- **Preprocessing**: Color reduction, denoising, contrast enhancement
- **Optimization**: Scour (path simplification, ID shortening)
- **Quality**: Good for most use cases
- **File Size**: Smaller (20-40KB typical)

### When to Use
- Most photographs
- Images with moderate complexity
- Web graphics
- General-purpose conversion
- When you need a good balance of speed and quality

### Preprocessing Steps
1. **Color Reduction**: Reduces palette to 32 colors using K-means clustering
2. **Bilateral Filtering**: Removes noise while preserving edges
3. **CLAHE**: Enhances local contrast for better edge detection

### Optimization
- Removes metadata and comments
- Simplifies paths
- Shortens IDs
- Removes unused definitions

## High Mode

### Pipeline
```
Input Image → Color Reduction (128 colors) → NLM Denoise → CLAHE Contrast
    → Unsharp Mask → Edge Enhancement → VTracer/Potrace
    → Aggressive SVG Optimization → Output
```

### Characteristics
- **Speed**: Slowest (3-10 seconds)
- **Preprocessing**: Full pipeline with advanced techniques
- **Optimization**: Aggressive (color optimization, number rounding, minification)
- **Quality**: Best possible quality
- **File Size**: Smallest (15-30KB typical)

### When to Use
- Complex photographs
- Professional work
- Images with fine details
- When file size is critical
- When quality is more important than speed

### Preprocessing Steps
1. **Color Reduction**: 128 colors for better fidelity
2. **Non-Local Means Denoising**: Best-in-class noise removal
3. **CLAHE Contrast**: Local contrast enhancement
4. **Unsharp Mask**: Edge sharpening
5. **Edge Enhancement**: Laplacian/Sobel edge highlighting

### Optimization
- All Standard optimizations
- Color optimization (RGB→hex, 6-digit→3-digit)
- Number precision reduction
- Aggressive minification
- Path simplification with tolerance

## Quality Comparison

### Example Results

| Metric | Fast | Standard | High |
|--------|------|----------|------|
| Processing Time | 0.5s | 2.1s | 5.8s |
| File Size | 45KB | 28KB | 19KB |
| SSIM Score | 0.85 | 0.92 | 0.96 |
| Edge Preservation | 0.72 | 0.84 | 0.91 |

### Visual Comparison

For a typical photograph:
- **Fast**: May have visible noise, jagged edges, larger file
- **Standard**: Clean image, good edges, moderate file size
- **High**: Cleanest image, sharpest edges, smallest file

## Choosing the Right Mode

### Decision Flowchart

```
Is the image simple (few colors, clean edges)?
├── Yes → Fast Mode
└── No → Is file size critical?
    ├── Yes → High Mode
    └── No → Is it a photograph?
        ├── Yes → Standard Mode
        └── No → Fast Mode
```

### Recommendations by Use Case

| Use Case | Recommended Mode | Reason |
|----------|------------------|--------|
| Simple icons/logos | Fast | No preprocessing needed |
| Web graphics | Standard | Good balance |
| Professional print | High | Best quality |
| Batch processing | Fast | Speed priority |
| E-commerce photos | Standard | Consistent quality |
| Art reproduction | High | Preserve details |

## API Usage

### Get Recommendation

```bash
curl -X POST -d "file_id=<file_id>" http://localhost:8000/api/v1/recommend
```

Response:
```json
{
  "recommended_mode": "standard",
  "reason": "Balanced image suitable for standard processing",
  "characteristics": {
    "resolution": "1920x1080",
    "unique_colors": 4523,
    "edge_density": 0.034,
    "color_variation": 48.2
  }
}
```

### Compare All Modes

```bash
curl -X POST -d "file_id=<file_id>" http://localhost:8000/api/v1/compare
```

Response:
```json
{
  "comparison_id": "<file_id>",
  "jobs": {
    "fast": "<job_id_1>",
    "standard": "<job_id_2>",
    "high": "<job_id_3>"
  }
}
```

### CLI Comparison

```bash
python -m backend.app.cli compare input.png --output ./comparison
```

This will create:
- `input_fast.svg`
- `input_standard.svg`
- `input_high.svg`

## Performance Benchmarks

### Test Image: 1920x1080 photograph

| Mode | Preprocessing | Conversion | Optimization | Total | Output Size |
|------|--------------|------------|--------------|-------|-------------|
| Fast | 0s | 0.4s | 0.1s | 0.5s | 45KB |
| Standard | 1.2s | 0.6s | 0.3s | 2.1s | 28KB |
| High | 4.2s | 1.1s | 0.5s | 5.8s | 19KB |

### Test Image: 512x512 simple logo

| Mode | Preprocessing | Conversion | Optimization | Total | Output Size |
|------|--------------|------------|--------------|-------|-------------|
| Fast | 0s | 0.1s | 0.05s | 0.15s | 12KB |
| Standard | 0.3s | 0.15s | 0.1s | 0.55s | 8KB |
| High | 1.1s | 0.2s | 0.15s | 1.45s | 6KB |

## Tips

1. **Start with Standard**: It's the best choice for 80% of images
2. **Use Fast for Batch**: When processing many simple images
3. **High for Final Output**: When quality is critical
4. **Compare Results**: Use the compare feature to see differences
5. **Monitor File Size**: High mode often produces smaller files despite better quality

## Future Improvements

- ML-based automatic mode selection
- Custom quality profiles
- Per-region quality adjustment
- Content-aware preprocessing
