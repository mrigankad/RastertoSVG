# Phase 1: Core Engine & CLI Tool

**Duration**: 2-3 weeks
**Goal**: Build a functional command-line tool for basic raster-to-SVG conversion

## Objectives

- Integrate VTracer and Potrace as core conversion engines
- Build Typer CLI with common use cases
- Implement file I/O and basic error handling
- Create unit tests for conversion logic
- Achieve basic color and monochrome conversion capabilities

## Architecture

```
User Input (CLI)
    ↓
Typer CLI Handler
    ↓
Converter Service
    ├→ VTracer (color images)
    ├→ Potrace (monochrome)
    └→ SVG Output
    ↓
File Output (.svg)
```

## Tasks

### 1.1 VTracer Integration

- [ ] Research and install VTracer:
  - Add `vtracer` to requirements.txt or build from source if needed
  - Document Python wrapper/bindings
  - Test basic color conversion
- [ ] Create wrapper module `backend/app/services/vtracer_engine.py`:
  - `convert_with_vtracer(image_path, color_precision, output_path)`
  - Configure parameters:
    - `color_precision` (1-256, default 32)
    - `hierarchical` (enable hierarchical grouping)
    - `mode` (color clustering mode)
  - Error handling for unsupported formats
  - Logging for debugging
- [ ] Test with sample images:
  - Photograph with many colors
  - Simple colorful graphic
  - Verify SVG output quality

### 1.2 Potrace Integration

- [ ] Research and install Potrace:
  - Add `pypotrace` or similar binding to requirements.txt
  - Or use subprocess wrapper if no Python bindings
  - Test basic monochrome conversion
- [ ] Create wrapper module `backend/app/services/potrace_engine.py`:
  - `convert_with_potrace(image_path, threshold, output_path)`
  - Configure parameters:
    - `threshold` (0-255, default 128)
    - `alphamax` (corner detection sensitivity)
    - `turnpolicy` (corner handling)
  - Automatic monochrome conversion (if needed)
  - Error handling
- [ ] Test with sample images:
  - Black and white document
  - Grayscale with clear contrast
  - Verify SVG output accuracy

### 1.3 Converter Service

- [ ] Create `backend/app/services/converter.py`:
  ```python
  class Converter:
      def convert(
          self,
          input_path: str,
          output_path: str,
          image_type: str = "auto",  # auto, color, monochrome
          quality_mode: str = "fast"  # fast, standard, high
      ) -> Dict[str, Any]:
          """Main conversion method"""

      def _auto_detect_type(self, image_path: str) -> str:
          """Detect if color or monochrome"""

      def _convert_color(self, image_path: str, output_path: str):
          """Use VTracer for color images"""

      def _convert_monochrome(self, image_path: str, output_path: str):
          """Use Potrace for monochrome"""
  ```
- [ ] Implement auto-detection logic:
  - Detect if image is color or monochrome
  - Route to appropriate engine
  - Handle edge cases (mostly color with some black/white)
- [ ] Result validation:
  - Check SVG was created
  - Validate SVG structure (basic XML check)
  - File size validation
  - Return metadata (processing time, colors used, file size)

### 1.4 Typer CLI Implementation

- [ ] Create `backend/app/cli.py`:
  ```python
  @app.command()
  def convert(
      input_file: str = typer.Argument(..., help="Input raster image"),
      output_file: str = typer.Option(..., help="Output SVG file"),
      image_type: str = typer.Option("auto", help="auto|color|monochrome"),
      quality: str = typer.Option("fast", help="fast|standard|high"),
      verbose: bool = typer.Option(False, help="Verbose output"),
  ):
      """Convert raster image to SVG"""

  @app.command()
  def batch(
      input_dir: str = typer.Argument(...),
      output_dir: str = typer.Option(...),
      pattern: str = typer.Option("*.png", help="File glob pattern"),
  ):
      """Batch convert directory of images"""

  @app.command()
  def info():
      """Show tool information and version"""
  ```
- [ ] CLI Features:
  - Progress bar for single conversions
  - Support for common formats: PNG, JPG, BMP, TIFF
  - Dry-run mode (`--dry-run`)
  - Output verbosity levels
  - Help documentation
- [ ] Error messages:
  - File not found
  - Unsupported format
  - Conversion failed (with reason)
  - Permissions issues
- [ ] Entry point:
  - Create setup.py or pyproject.toml entry point
  - Command: `raster-to-svg convert input.png --output output.svg`

### 1.5 File I/O & Validation

- [ ] Input validation:
  - Check file exists
  - Check readable permissions
  - Validate image format
  - Check file size limits (prevent memory bombs)
- [ ] Output handling:
  - Create output directory if needed
  - Handle existing file conflicts (overwrite, skip, or error)
  - Set proper file permissions
  - Verify SVG is valid XML
- [ ] Supported formats:
  - Input: PNG, JPG, JPEG, BMP, TIFF, GIF (static), WEBP
  - Output: SVG (text-based)

### 1.6 Testing

- [ ] Create `backend/tests/test_vtracer.py`:
  - Test VTracer with sample color image
  - Test parameter variations
  - Test error handling (invalid input)
- [ ] Create `backend/tests/test_potrace.py`:
  - Test Potrace with monochrome image
  - Test parameter variations
  - Test error handling
- [ ] Create `backend/tests/test_converter.py`:
  - Test auto-detection (color vs monochrome)
  - Test routing to correct engine
  - Test result validation
  - Test file I/O (create, overwrite, permissions)
- [ ] Create `backend/tests/test_cli.py`:
  - Test CLI argument parsing
  - Test file input/output
  - Test error messages
  - Use Typer's test runner
- [ ] Sample test images:
  - Create or source test images for each format
  - Include edge cases (very small, very large, specific colors)
  - Store in `backend/tests/fixtures/images/`

### 1.7 Documentation

- [ ] Create `docs/CLI.md`:
  - Usage examples
  - Parameter documentation
  - Supported formats
  - Troubleshooting
- [ ] Add docstrings to all public methods
- [ ] Create example scripts:
  - `examples/convert_single.py`
  - `examples/batch_convert.py`
  - `examples/color_vs_bw.py`

### 1.8 Performance & Optimization

- [ ] Profile conversion speed:
  - Measure time per image size
  - Identify bottlenecks
  - Document baseline performance
- [ ] Memory usage:
  - Measure memory with large images
  - Implement streaming if needed
  - Add progress callbacks for long operations

## Deliverables

- ✅ VTracer integration working
- ✅ Potrace integration working
- ✅ Converter service with auto-detection
- ✅ Functional CLI tool
- ✅ Comprehensive test suite (>80% coverage)
- ✅ User documentation
- ✅ Performance baseline established

## Success Criteria

- [ ] CLI successfully converts a color PNG to SVG
- [ ] CLI successfully converts a monochrome PNG to SVG
- [ ] Output SVG is valid and renders correctly
- [ ] All tests pass
- [ ] Error handling covers common cases
- [ ] Performance baseline documented
- [ ] User can install via pip and run immediately
- [ ] Help text is clear and helpful

## Known Limitations (to address in later phases)

- No preprocessing (color reduction, noise removal)
- Single image processing only (no batching infrastructure yet)
- No advanced quality control
- Output optimization limited
- No API access

## Next Phase

→ [Phase 2: Preprocessing Pipeline](./phase-2-preprocessing.md)
