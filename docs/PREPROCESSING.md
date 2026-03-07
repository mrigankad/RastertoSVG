# Preprocessing Guide

The preprocessing pipeline improves conversion quality by cleaning and enhancing images before vectorization.

## Overview

Three quality modes control preprocessing intensity:

| Mode | Preprocessing | Speed | Best For |
|------|--------------|-------|----------|
| **Fast** | None | < 1s | Simple graphics, clean images |
| **Standard** | Color reduction + Denoise + CLAHE | 1-3s | Most images, photos |
| **High** | Standard + Sharpen + Edge enhance | 3-10s | Complex images, professional work |

## CLI Usage

```bash
# Standard quality with preprocessing
raster-to-svg convert image.png --quality standard

# High quality with full preprocessing
raster-to-svg convert image.png --quality high --verbose

# Show preprocessing steps
raster-to-svg convert image.png --quality standard --show-preprocessing

# Preprocess without converting
raster-to-svg preprocess image.png --output ./processed --quality standard

# Compare all preprocessing methods
raster-to-svg preprocess image.png --output ./comparison --compare

# Apply dithering
raster-to-svg dither image.png --output dithered.png --method floyd-steinberg
```

## Preprocessing Methods

### Color Reduction

Reduces the number of colors in an image for cleaner vectorization.

**Methods:**
- **K-means clustering**: Best quality, groups similar colors
- **Median cut**: Fast, good for most images

**Parameters:**
- `max_colors`: 8-256 (default: 32 for standard, 128 for high)

### Noise Reduction

Removes noise and artifacts from images.

| Method | Speed | Quality | Best For |
|--------|-------|---------|----------|
| **Gaussian** | Fast | Low | General smoothing |
| **Bilateral** | Medium | High | Edge-preserving (recommended) |
| **Non-Local Means** | Slow | Highest | Heavy noise, JPEG artifacts |
| **Median** | Fast | Medium | Salt-and-pepper noise |

### Contrast Enhancement

Improves image contrast for better edge detection.

| Method | Description |
|--------|-------------|
| **CLAHE** | Adaptive histogram equalization (recommended) |
| **Histogram** | Global histogram equalization |
| **Levels** | Min/max stretching |
| **Sigmoid** | S-curve contrast (smooth) |

### Sharpening

Enhances edge definition.

**Unsharp Mask:**
- `kernel_size`: Blur kernel size (default: 5)
- `sigma`: Blur amount (default: 1.0)
- `amount`: Sharpening strength (default: 1.5)

### Edge Enhancement

Highlights edges for better tracing.

| Method | Description |
|--------|-------------|
| **Laplacian** | Second-derivative edge detection |
| **Sobel** | First-derivative, gradient-based |
| **Scharr** | Improved Sobel operator |

### Monochrome Conversion

Converts images to black and white.

| Method | Description |
|--------|-------------|
| **Otsu** | Automatic threshold (default) |
| **Adaptive** | Local thresholding for uneven lighting |
| **Manual** | Fixed threshold value |

### Dithering

Converts grayscale to black and white while preserving tones.

| Method | Description | Best For |
|--------|-------------|----------|
| **Floyd-Steinberg** | Error diffusion | Most images |
| **Bayer** | Ordered dithering | Fast processing |
| **Atkinson** | Reduced artifact diffusion | Photos |
| **Ordered** | Pattern-based | Simple graphics |

## Python API

```python
from app.services.preprocessor import Preprocessor

# Create preprocessor
preprocessor = Preprocessor()

# Apply full pipeline
result = preprocessor.preprocess(
    "input.png",
    image_type="color",
    quality_mode="standard"
)

# Individual methods
from PIL import Image

img = Image.open("input.png")

# Color reduction
reduced = preprocessor._reduce_colors_kmeans(img, max_colors=32)

# Denoise
denoised = preprocessor._denoise_bilateral(img)

# Enhance contrast
enhanced = preprocessor._enhance_clahe(img, clip_limit=2.0)

# Sharpen
sharpened = preprocessor._sharpen_unsharp_mask(img, amount=1.5)

# Convert to monochrome
binary = preprocessor.convert_to_monochrome(img, method="otsu")

# Apply dithering
dithered = preprocessor.apply_dithering(img, method="floyd-steinberg")
```

## Examples

### Remove JPEG Artifacts

```bash
# Heavy denoising for JPEG artifacts
raster-to-svg preprocess photo.jpg --output clean.png --quality high
```

### Prepare Line Art

```bash
# Enhance contrast and sharpen for line art
raster-to-svg convert drawing.png --quality high
```

### Reduce Color Palette

```bash
# Custom color palette size
raster-to-svg convert illustration.png --quality standard --colors 16
```

### Create Dithered Monochrome

```bash
# Convert to black and white with dithering
raster-to-svg dither photo.jpg --output dithered.png --method atkinson
```

## Performance Tips

1. **Use Fast mode** for clean images to save time
2. **Use Standard mode** for most photographs
3. **Use High mode** only when necessary (complex images, artifacts)
4. **Batch process** multiple images with same settings
5. **Compare methods** to find best for your image type

## Troubleshooting

### Colors look posterized
- Increase color palette size: `--colors 64`
- Use High quality mode

### Edges look jagged
- Enable sharpening with High mode
- Use bilateral denoise instead of Gaussian

### Noise not removed
- Switch to High mode for NLM denoising
- Preprocess separately to compare methods

### Slow processing
- Use Standard mode instead of High
- Reduce image resolution before processing
- Use Fast mode for batch processing
