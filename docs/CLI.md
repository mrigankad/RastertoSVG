# CLI Documentation

The Raster to SVG Converter includes a command-line interface for batch processing and automation.

## Installation

After setting up the Python environment:

```bash
cd backend
pip install -e .
```

This installs the `raster-to-svg` command.

## Commands

### `convert`

Convert a single image to SVG.

```bash
raster-to-svg convert INPUT_FILE [OPTIONS]
```

**Arguments:**
- `INPUT_FILE` - Path to the input image (required)

**Options:**
- `-o, --output PATH` - Output SVG file path (default: same name with .svg extension)
- `-t, --type [auto|color|monochrome]` - Image type detection (default: auto)
- `-q, --quality [fast|standard|high]` - Quality mode (default: fast)
- `-v, --verbose` - Enable verbose output

**Examples:**

```bash
# Basic conversion
raster-to-svg convert image.png

# Specify output file
raster-to-svg convert image.png -o output.svg

# High quality conversion
raster-to-svg convert photo.jpg --quality high --verbose

# Force monochrome mode
raster-to-svg convert document.png --type monochrome --quality standard
```

### `batch`

Convert multiple images in a directory.

```bash
raster-to-svg batch INPUT_DIR [OPTIONS]
```

**Arguments:**
- `INPUT_DIR` - Directory containing images (required)

**Options:**
- `-o, --output PATH` - Output directory for SVGs (required)
- `-p, --pattern TEXT` - File glob pattern (default: *.png)
- `-q, --quality [fast|standard|high]` - Quality mode (default: fast)

**Examples:**

```bash
# Convert all PNG files
raster-to-svg batch ./input -o ./output

# Convert all images with specific pattern
raster-to-svg batch ./input -o ./output --pattern "*.jpg"

# High quality batch conversion
raster-to-svg batch ./photos -o ./vectors --quality high
```

### `info`

Display tool information and version.

```bash
raster-to-svg info
```

## Quality Modes

### Fast Mode

- No preprocessing
- Direct conversion
- Best for: Simple graphics, screenshots, logos
- Speed: < 1 second per image

### Standard Mode

- Color reduction (32 colors default)
- Denoising
- Contrast enhancement
- Best for: Most images, photographs
- Speed: 2-5 seconds per image

### High Mode

- Full preprocessing pipeline
- ML-enhanced conversion
- Advanced SVG optimization
- Best for: Professional work, complex images
- Speed: 5-30 seconds per image

## Exit Codes

- `0` - Success
- `1` - General error (file not found, invalid input, etc.)
- `2` - Conversion failed

## Environment Variables

The CLI respects these environment variables:

- `RASTER_TO_SVG_QUALITY` - Default quality mode
- `RASTER_TO_SVG_TYPE` - Default image type
- `RASTER_TO_SVG_OUTPUT_DIR` - Default output directory

## Scripting Examples

### Bash Script

```bash
#!/bin/bash

# Convert all images in a directory with progress
for img in ./input/*.{png,jpg,jpeg}; do
    if [ -f "$img" ]; then
        echo "Converting: $img"
        raster-to-svg convert "$img" -o "./output/$(basename "$img" .png).svg" --quality standard
    fi
done
```

### Python Script

```python
import subprocess
from pathlib import Path

def convert_images(input_dir: Path, output_dir: Path, quality: str = "standard"):
    output_dir.mkdir(exist_ok=True)
    
    for img_path in input_dir.glob("*.png"):
        output_path = output_dir / f"{img_path.stem}.svg"
        
        result = subprocess.run(
            ["raster-to-svg", "convert", str(img_path), "-o", str(output_path), "--quality", quality],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✓ Converted: {img_path.name}")
        else:
            print(f"✗ Failed: {img_path.name} - {result.stderr}")

# Usage
convert_images(Path("./input"), Path("./output"), "high")
```

## Troubleshooting

### Command not found

Make sure the virtual environment is activated:
```bash
source backend/venv/bin/activate  # macOS/Linux
backend\venv\Scripts\activate     # Windows
```

### Permission denied

On Linux/macOS, you may need to make the script executable:
```bash
chmod +x backend/venv/bin/raster-to-svg
```

### Out of memory

For large images, reduce the quality mode or increase system memory:
```bash
raster-to-svg convert large-image.png --quality fast
```
