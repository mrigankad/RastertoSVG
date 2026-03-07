# Phase 5: Quality Modes & Advanced Optimization

**Duration**: 2-3 weeks
**Goal**: Implement advanced quality tiers, ML-based enhancement, and SVG optimization

## Objectives

- Implement three distinct quality modes with clear trade-offs
- Integrate SAMVG or similar ML models for high-quality mode
- Implement advanced SVG optimization and cleanup
- Add edge detection and line smoothing
- Create quality comparison tools
- Establish performance baselines for each mode

## Quality Modes Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    THREE QUALITY TIERS                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  FAST MODE              STANDARD MODE           HIGH MODE    │
│  ─────────────────      ──────────────────      ────────────  │
│  • No preprocessing     • Color reduction       • ML models   │
│  • Direct conversion    • Denoise               • SAMVG       │
│  • < 1s (small images)  • Contrast enhance      • Edge detect │
│  • Basic quality        • < 5s (small images)   • Line smooth │
│  • File size: 30-50KB   • Good quality          • < 30s       │
│  • ✓ Simple graphics    • File size: 20-40KB    • Best quality│
│  • ✓ Screenshots        • ✓ Most use cases      • File: 15KB  │
│  • ✓ Logos              • ✓ Photographs        • ✓ Pro work  │
│                                                 │              │
└─────────────────────────────────────────────────────────────┘
```

## Tasks

### 5.1 Quality Mode Architecture

- [ ] Refactor `backend/app/services/converter.py`:
  ```python
  class QualityModeSelector:
      def get_pipeline(self, mode: str, image_type: str):
          """
          Return processing pipeline for quality mode
          Returns list of processing functions to apply
          """
          pipelines = {
              "fast": self._fast_pipeline,
              "standard": self._standard_pipeline,
              "high": self._high_pipeline
          }
          return pipelines[mode](image_type)

      def _fast_pipeline(self, image_type):
          """Minimal preprocessing"""
          return [
              ("load_image", {}),
              ("convert_direct", {"engine": "vtracer" if image_type == "color" else "potrace"})
          ]

      def _standard_pipeline(self, image_type):
          """Balanced quality/speed"""
          return [
              ("load_image", {}),
              ("reduce_colors", {"max_colors": 32}),
              ("denoise", {"strength": "medium"}),
              ("enhance_contrast", {"factor": 1.5}),
              ("convert", {"engine": "vtracer" if image_type == "color" else "potrace"})
          ]

      def _high_pipeline(self, image_type):
          """Maximum quality"""
          return [
              ("load_image", {}),
              ("reduce_colors", {"max_colors": 128}),
              ("denoise", {"strength": "heavy"}),
              ("enhance_contrast", {"factor": 2.0}),
              ("detect_edges", {"method": "canny"}),
              ("apply_dithering", {"method": "floyd-steinberg"}),
              ("convert_with_ml", {"model": "samvg"}),
              ("optimize_svg", {"level": "high"})
          ]
  ```

- [ ] Implement pipeline execution:
  - Sequential execution of steps
  - Error handling and rollback
  - Intermediate result caching
  - Progress tracking

### 5.2 Edge Detection & Line Enhancement (High Mode)

- [ ] Create `backend/app/services/edge_detector.py`:
  ```python
  class EdgeDetector:
      def detect_edges(self, image, method="canny"):
          """Detect image edges for better vector conversion"""

      def _canny_edge_detection(self, image, sigma=1.0, threshold1=50, threshold2=150):
          """Canny edge detection"""

      def _sobel_edge_detection(self, image):
          """Sobel operator"""

      def _laplacian_edge_detection(self, image):
          """Laplacian method"""

      def enhance_edges(self, image, kernel_size=3):
          """Sharpen and enhance detected edges"""

      def combine_with_original(self, original, edges, weight=0.3):
          """Blend edge detection with original"""
  ```

- [ ] Edge detection methods:
  - **Canny**: Best for most images (balanced sensitivity)
  - **Sobel**: Good for gradients
  - **Laplacian**: Detect zero crossings
  - **Custom**: Morphological operations for specific shapes

### 5.3 Line Smoothing & Simplification

- [ ] Create `backend/app/services/line_smoother.py`:
  ```python
  class LineSmoother:
      def smooth_svg_paths(self, svg_content):
          """Apply smoothing to SVG paths"""

      def catmull_rom_spline(self, points, tension=0.5):
          """Smooth lines using Catmull-Rom spline"""

      def bezier_smoothing(self, points, tension=0.5):
          """Smooth lines using Bezier curves"""

      def rdp_simplification(self, points, epsilon=1.0):
          """Ramer-Douglas-Peucker simplification"""

      def adaptive_smoothing(self, svg, aggressive=True):
          """
          Apply smoothing based on path complexity
          More smoothing for simple paths, less for detail-heavy
          """
  ```

- [ ] Algorithms:
  - **Catmull-Rom**: Smooth curves through control points
  - **Bezier**: Smooth with cubic bezier splines
  - **RDP**: Simplify paths while preserving shape
  - **Adaptive**: Balance between simplification and detail

### 5.4 ML-Based Conversion (SAMVG)

- [ ] Research and integrate SAMVG or alternative:
  - SAMVG (Segment Anything Model for Vectors)
  - Alternative: Use Potrace/VTracer with ML preprocessing
  - Option: Fine-tune existing models

- [ ] Create `backend/app/services/ml_converter.py`:
  ```python
  class MLConverter:
      def __init__(self, model_path=None):
          """Load ML model for conversion"""
          self.model = load_model(model_path)

      def convert_with_ml(self, image_path, output_path):
          """
          Use ML model for higher quality conversion
          Typically slower but better results
          """

      def segment_image(self, image):
          """Segment image into meaningful regions"""

      def vectorize_segments(self, segments):
          """Convert segments to vector paths"""

      def generate_svg(self, paths):
          """Create final SVG from paths"""
  ```

- [ ] Implementation approach:
  - Start with improved Potrace/VTracer configs
  - Add ML model in Phase 5.5 if needed
  - Measure quality improvement
  - Document trade-offs

### 5.5 SVG Optimization

- [ ] Integrate scour (Python) and SVGO (Node.js):
  ```python
  class SVGOptimizer:
      def optimize(self, svg_content, level="standard"):
          """
          Optimize SVG for size and quality
          level: "light", "standard", "aggressive"
          """

      def _remove_metadata(self, svg):
          """Remove comments, metadata, editor-specific attributes"""

      def _simplify_paths(self, svg, epsilon=1.0):
          """Simplify complex paths"""

      def _remove_unused_defs(self, svg):
          """Remove unused gradients, patterns, etc"""

      def _optimize_colors(self, svg):
          """Convert colors to hex, remove redundant stops"""

      def _round_numbers(self, svg, precision=2):
          """Round coordinates to reduce size"""

      def _minify(self, svg):
          """Minify SVG (remove whitespace)"""
  ```

- [ ] Scour integration:
  ```python
  import subprocess
  result = subprocess.run([
      'scour',
      input_file,
      '--output', output_file,
      '--enable-viewboxing',
      '--enable-id-stripping',
      '--shorten-ids',
      '--no-line-breaks'
  ])
  ```

- [ ] SVGO integration:
  - Create Node.js bridge or subprocess calls
  - Configure SVGO plugins
  - Performance: < 100ms for typical files

- [ ] Optimization levels:
  - **Light**: Remove metadata only (99% of original size)
  - **Standard**: + simplify paths (70-80% of original)
  - **Aggressive**: + color optimization (40-60% of original)

### 5.6 Quality Comparison Tools

- [ ] Create `backend/app/services/quality_analyzer.py`:
  ```python
  class QualityAnalyzer:
      def compare_conversions(self, original_image, svg_outputs):
          """
          Compare outputs from different quality modes
          Returns quality metrics for each
          """

      def edge_preservation(self, svg1, svg2):
          """Measure how well edges are preserved"""

      def color_accuracy(self, original, svg):
          """Measure color fidelity (for color images)"""

      def file_size_ratio(self, original_size, svg_size):
          """Calculate size reduction ratio"""

      def complexity_metrics(self, svg):
          """
          Count paths, nodes, etc
          Measure SVG complexity
          """

      def generate_comparison_report(self, image, results):
          """
          Generate HTML report comparing quality modes
          Includes images, metrics, and recommendations
          """
  ```

- [ ] Metrics to track:
  - Processing time
  - Output file size
  - Number of paths/shapes
  - Edge preservation score
  - Color fidelity (if applicable)
  - Visual quality (subjective)

### 5.7 API Enhancements

- [ ] Add quality comparison endpoint:
  ```python
  @router.post("/api/v1/compare")
  async def compare_quality(file_id: str):
      """
      Run all three quality modes and return comparison
      Useful for users to understand trade-offs
      """
  ```

- [ ] Add advanced options:
  ```python
  class AdvancedOptions(BaseModel):
      # Edge detection
      edge_detection: bool = False
      edge_method: str = "canny"

      # Line smoothing
      apply_smoothing: bool = False
      smoothing_method: str = "catmull-rom"

      # SVG optimization
      optimization_level: str = "standard"

      # Color options
      color_palette_size: int = 32
      color_dithering: bool = False

      # Output options
      include_metadata: bool = False
      minify: bool = True
  ```

### 5.8 Benchmarking & Testing

- [ ] Create comprehensive benchmark suite:
  - Test images of various types
  - Measure metrics for each quality mode
  - Generate benchmark reports

- [ ] Benchmark test suite:
  ```python
  # backend/tests/test_quality_modes.py
  def test_fast_mode_speed():
      """Fast mode should complete in < 1s for small images"""

  def test_standard_mode_quality():
      """Standard mode should have good quality"""

  def test_high_mode_quality():
      """High mode should have best quality"""

  def test_quality_comparison():
      """Run all modes on same image, compare"""
  ```

- [ ] Generate benchmark report:
  - Markdown file with results
  - Visual comparisons (before/after)
  - Performance graphs
  - Recommendations

### 5.9 Frontend Updates

- [ ] Update conversion form:
  - Show quality mode descriptions
  - Display estimated time for each mode
  - Show file size estimates
  - Add comparison feature

- [ ] Quality comparison page:
  - Display all three modes side-by-side
  - Show metrics for each
  - Allow toggling between modes
  - Download comparison report

- [ ] Advanced options modal:
  - Edge detection toggle
  - Line smoothing options
  - Optimization level selector
  - Color options (if color image)

### 5.10 Documentation

- [ ] Create `docs/QUALITY_MODES.md`:
  - Explanation of each mode
  - Use case recommendations
  - Performance characteristics
  - Quality trade-offs
  - Examples for each mode

- [ ] Create `docs/SVG_OPTIMIZATION.md`:
  - How optimization works
  - Before/after file sizes
  - Optimization levels
  - Why certain features matter

- [ ] Update API documentation:
  - Document quality mode parameters
  - Document advanced options
  - Add comparison endpoint

## Deliverables

- ✅ Three distinct quality modes implemented
- ✅ Edge detection and line smoothing
- ✅ SVG optimization pipeline
- ✅ Quality comparison tools
- ✅ Comprehensive benchmarks
- ✅ Updated frontend with quality options
- ✅ Documentation with examples
- ✅ Benchmark reports and metrics

## Success Criteria

- [ ] Fast mode completes < 1s for small images
- [ ] Standard mode ~2-5s with good quality
- [ ] High mode ~5-30s with best quality
- [ ] Quality comparison working correctly
- [ ] SVG files 30-60% smaller after optimization
- [ ] All tests pass
- [ ] Documentation clear and helpful
- [ ] Users can make informed quality/speed trade-off

## Quality Mode Characteristics

| Aspect | Fast | Standard | High |
|--------|------|----------|------|
| Speed | < 1s | 2-5s | 5-30s |
| File Size | 30-50KB | 20-40KB | 15-30KB |
| Edge Preservation | Good | Very Good | Excellent |
| Color Accuracy | Good | Very Good | Excellent |
| Processing | Minimal | Balanced | Intensive |
| CPU Usage | Low | Medium | High |

## Next Phase

→ [Phase 6: Production & Deployment](./phase-6-production.md)
