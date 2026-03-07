# Phase 2: Preprocessing Pipeline

**Duration**: 2-3 weeks
**Goal**: Implement image enhancement and preprocessing to improve conversion quality

## Objectives

- Build comprehensive image preprocessing module
- Implement noise reduction, contrast enhancement, edge detection
- Create preprocessing strategy selector
- Integrate with existing converter
- Test on diverse image types
- Document preprocessing effects

## Architecture

```
Input Image
    ↓
Preprocessing Pipeline
├→ Color Reduction (if needed)
├→ Noise Filtering
├→ Contrast Enhancement
├→ Edge Detection/Sharpening
├→ Dithering (for monochrome)
└→ Output to Converter
    ↓
VTracer/Potrace
    ↓
SVG Output
```

## Tasks

### 2.1 Preprocessing Core Module

- [ ] Create `backend/app/services/preprocessor.py`:
  ```python
  class Preprocessor:
      def preprocess(
          self,
          image_path: str,
          image_type: str,
          quality_mode: str
      ) -> Image:
          """Apply preprocessing pipeline based on quality mode"""

      def _reduce_colors(self, image, max_colors=32):
          """Reduce color palette"""

      def _denoise(self, image, strength="medium"):
          """Remove noise"""

      def _enhance_contrast(self, image, factor=1.5):
          """Enhance contrast"""

      def _sharpen(self, image, kernel_size=3):
          """Sharpen edges"""

      def _convert_to_monochrome(self, image, threshold=None):
          """Convert to B&W with optimal threshold"""

      def _apply_dithering(self, image, method="floyd-steinberg"):
          """Apply dithering for better monochrome quality"""
  ```
- [ ] Implement preprocessing strategies:
  - **Fast**: No preprocessing (skip this phase)
  - **Standard**: Color reduction + denoising + contrast
  - **High**: Standard + sharpening + edge enhancement + dithering

### 2.2 Color Reduction

- [ ] Implement `_reduce_colors()`:
  - Use k-means clustering for palette optimization
  - Scikit-image: `skimage.segmentation.quickshift()` or similar
  - Preserve dominant colors
  - Configurable palette sizes (8, 16, 32, 64, 128, 256)
- [ ] Test on:
  - Photographs (preserve color fidelity)
  - Graphics (simplify palettes)
  - Gradients (prevent banding)
- [ ] Measure impact:
  - Conversion time improvement
  - Output quality vs file size trade-off

### 2.3 Noise Reduction

- [ ] Implement multiple denoising methods:
  - **Gaussian Blur**: Simple, fast (cv2.GaussianBlur)
  - **Bilateral Filter**: Edge-preserving (cv2.bilateralFilter)
  - **Non-Local Means**: High quality (cv2.fastNlMeansDenoisingColored)
  - **Morphological**: Opening/closing for B&W (cv2.morphologyEx)
- [ ] Create `_denoise()` with strength levels:
  ```python
  strength_params = {
      "light": {"method": "bilateral", "d": 5, "sigma": 50},
      "medium": {"method": "nlm", "h": 10, "template_window": 7},
      "heavy": {"method": "nlm", "h": 15, "template_window": 9}
  }
  ```
- [ ] Test on:
  - JPEG artifacts
  - Scanned documents with noise
  - Photographs at high ISO

### 2.4 Contrast Enhancement

- [ ] Implement multiple contrast methods:
  - **Histogram Equalization**: CLAHE (cv2.createCLAHE)
  - **Adaptive Contrast**: Local enhancement
  - **Levels Adjustment**: Min/max stretching
  - **Curve Adjustment**: Sigmoid/S-curves
- [ ] Create `_enhance_contrast()`:
  ```python
  def _enhance_contrast(self, image, method="clahe", factor=1.5):
      """
      Apply contrast enhancement
      method: "clahe", "histogram", "levels", "sigmoid"
      factor: strength multiplier (1.0 = no change, 2.0 = strong)
      """
  ```
- [ ] Test on:
  - Low-contrast images
  - High-contrast images
  - Mixed lighting conditions

### 2.5 Sharpening & Edge Enhancement

- [ ] Implement sharpening filters:
  - **Unsharp Mask**: High quality (cv2.filter2D with kernel)
  - **High-Pass Filter**: Frequency domain
  - **Laplacian**: Edge detection (cv2.Laplacian)
- [ ] Create `_sharpen()`:
  ```python
  def _sharpen(self, image, kernel_size=3, strength=1.0):
      """Apply unsharp mask for edge enhancement"""
  ```
- [ ] Parameter tuning:
  - Kernel sizes: 3x3, 5x5, 7x7
  - Strength: 0.5 - 2.0
  - Amount: 0.5 - 1.5

### 2.6 Monochrome Conversion

- [ ] Implement intelligent B&W conversion:
  - [ ] Otsu's method (automatic threshold) - `cv2.threshold(..., cv2.THRESH_OTSU)`
  - [ ] Local thresholding (adaptive) - `cv2.adaptiveThreshold()`
  - [ ] Multi-level thresholding (edge cases)
  - [ ] Preserve fine details (morphological operations)
- [ ] Create `_convert_to_monochrome()`:
  ```python
  def _convert_to_monochrome(self, image, threshold=None, method="otsu"):
      """
      Convert to binary (0/255) with optimal threshold
      method: "otsu", "adaptive", "manual"
      threshold: manual threshold value if method="manual"
      """
  ```
- [ ] Test on:
  - Documents
  - Screenshots
  - Photographs
  - Mixed content

### 2.7 Dithering

- [ ] Implement dithering algorithms for better monochrome quality:
  - **Floyd-Steinberg**: Classic error diffusion
  - **Bayer**: Ordered dithering (fast)
  - **Atkinson**: Reduced artifacts
  - **Pattern**: Simple patterns
- [ ] Create `_apply_dithering()`:
  ```python
  def _apply_dithering(self, image, method="floyd-steinberg"):
      """Apply dithering to improve grayscale representation"""
  ```
- [ ] Scikit-image methods:
  - `skimage.restoration.denoise_tv_chambolle`
  - Manual implementation of error diffusion
- [ ] Test:
  - Monochrome photographs
  - Gradient images
  - Quality vs file size

### 2.8 Integration with Converter

- [ ] Modify `backend/app/services/converter.py`:
  - Add preprocessing step before conversion
  - Route based on quality_mode:
    ```python
    if quality_mode == "fast":
        converted = self._convert_color(image_path, output_path)
    elif quality_mode == "standard":
        preprocessed = self.preprocessor.preprocess(image_path, "standard")
        converted = self._convert_color(preprocessed, output_path)
    else:  # high
        preprocessed = self.preprocessor.preprocess(image_path, "high")
        converted = self._convert_color(preprocessed, output_path)
    ```
  - Save intermediate preprocessed images (optional, for debugging)
  - Track preprocessing metrics

- [ ] Update CLI:
  - `--show-preprocessing`: Display before/after
  - `--skip-preprocessing`: Force fast mode
  - `--denoise-strength`: Configure denoising
  - `--color-palette`: Set max colors

### 2.9 Testing & Benchmarking

- [ ] Create `backend/tests/test_preprocessor.py`:
  - Test each preprocessing function independently
  - Test preprocessing pipelines
  - Test parameter variations
  - Verify image integrity (not corrupted)
- [ ] Create comparison test suite:
  - Input → No preprocessing → Output
  - Input → Standard preprocessing → Output
  - Input → High preprocessing → Output
  - Visual comparison (generate PDF reports)
- [ ] Performance testing:
  - Measure preprocessing time by image size
  - Memory usage monitoring
  - Establish baselines
- [ ] Quality metrics:
  - Edge preservation
  - Color accuracy (if applicable)
  - Detail retention
  - Artifacts introduced

### 2.10 Documentation & Examples

- [ ] Create `docs/PREPROCESSING.md`:
  - Overview of each technique
  - When to use which method
  - Parameter tuning guide
  - Before/after examples
- [ ] Create example scripts:
  - `examples/denoise_image.py`
  - `examples/color_reduction.py`
  - `examples/threshold_comparison.py`
- [ ] Create visual test suite:
  - Generate side-by-side comparisons
  - Include parameter variation examples

## Deliverables

- ✅ Preprocessing module with multiple techniques
- ✅ Three quality mode strategies implemented
- ✅ Integrated into converter pipeline
- ✅ Comprehensive test suite
- ✅ Performance/quality benchmarks
- ✅ User documentation with examples
- ✅ Before/after comparison examples

## Success Criteria

- [ ] Standard mode produces noticeably better quality than fast mode
- [ ] High mode produces best quality (with reasonable processing time)
- [ ] All tests pass with >80% coverage
- [ ] Performance baselines documented
- [ ] Preprocessing is optional (can be disabled)
- [ ] Works with all supported image formats
- [ ] Edge cases handled (very small, very large images)
- [ ] Documentation includes visual examples

## Performance Expectations

| Image Size | Fast | Standard | High |
|-----------|------|----------|------|
| < 1 MB | < 1s | 1-2s | 2-5s |
| 1-5 MB | 1-2s | 2-5s | 5-15s |
| 5-20 MB | 2-5s | 5-15s | 15-30s |

(Benchmarks to be updated after implementation)

## Next Phase

→ [Phase 3: Backend Infrastructure (API + Async)](./phase-3-api-backend.md)
