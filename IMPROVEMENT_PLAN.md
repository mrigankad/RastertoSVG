# Raster to SVG - Improvement Plan

## Executive Summary

Based on comprehensive user personas analysis, this plan introduces **4 Control Levels** to serve all user types while maintaining simplicity for casual users.

**Key Goals:**
1. Give users proper control over conversion parameters
2. Maintain simplicity for casual users (Smart Defaults)
3. Enable advanced workflows for professionals
4. Add preview/comparison capabilities
5. Improve overall UX and workflow efficiency

---

## Control Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CONTROL LEVELS                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Level 1: SMART DEFAULTS         Level 2: GUIDED CONTROL        │
│  ┌─────────────────────────┐    ┌──────────────────────────┐   │
│  │ • Quality Slider        │    │ • Quality Mode Selection │   │
│  │   (Draft/Standard/Pro)  │    │ • Basic Preprocessing    │   │
│  │ • One-Click Convert     │    │ • Simple Color Control   │   │
│  └─────────────────────────┘    └──────────────────────────┘   │
│                                                                 │
│  Level 3: FULL CONTROL           Level 4: PROGRAMMATIC         │
│  ┌─────────────────────────┐    ┌──────────────────────────┐   │
│  │ • Preprocessing Chain   │    │ • REST API Full Access   │   │
│  │ • Color Palette Editor  │    │ • JSON/YAML Config       │   │
│  │ • Vectorization Params  │    │ • Webhooks               │   │
│  │ • Custom Presets        │    │ • CI/CD Integration      │   │
│  └─────────────────────────┘    └──────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Enhanced Preprocessing Controls

### 1.1 Preprocessing Pipeline Builder

**Backend Changes:**
```python
class PreprocessingStep(BaseModel):
    name: str
    enabled: bool
    params: Dict[str, Any]
    order: int

class PreprocessingConfig(BaseModel):
    steps: List[PreprocessingStep]
    
# New endpoints:
POST /api/v1/preprocess/preview      # Preview preprocessing on image
GET  /api/v1/preprocess/filters      # List available filters
POST /api/v1/preprocess/chain        # Apply custom chain
```

**Frontend Components:**
- `PreprocessingPanel.tsx` - Visual pipeline builder
- `FilterCard.tsx` - Individual filter with parameters
- `FilterPreview.tsx` - Before/after comparison

**Available Filters:**
| Filter | Parameters | Description |
|--------|------------|-------------|
| Denoise | method, strength, preserve_edges | Remove image noise |
| Sharpen | amount, radius, threshold | Enhance edges |
| Contrast | method, clip_limit, grid_size | Improve contrast |
| Color Reduce | method, max_colors, dithering | Reduce palette |
| Blur | type, radius, sigma | Smooth image |
| Edge Enhance | operator, strength | Emphasize edges |
| Despeckle | size, iterations | Remove small artifacts |
| Deskew | max_angle, auto_detect | Straighten documents |

### 1.2 Color Palette Editor

**Backend:**
```python
class ColorPaletteConfig(BaseModel):
    mode: Literal["auto", "extract", "custom", "reduce"]
    max_colors: int
    extracted_colors: List[str]  # Hex colors
    custom_colors: List[str]
    dithering: Literal["none", "floyd", "bayer", "atkinson"]
    preserve_transparency: bool
```

**Frontend:**
- Color extraction from uploaded image
- Visual palette editor (add/remove colors)
- Real-time preview of color reduction
- Dithering method selection with preview

### 1.3 Image Type Detection & Override

**Smart Auto-Detection:**
- Analyze image characteristics
- Suggest optimal processing path
- Allow manual override with preview

**Detection Criteria:**
```python
class ImageAnalysis(BaseModel):
    is_photo: bool           # Photo vs illustration
    is_line_art: bool        # Line art detection
    has_text: bool           # OCR-based text detection
    color_complexity: float  # Number of unique colors
    noise_level: float       # Estimated noise
    recommended_mode: str    # Suggested quality mode
```

---

## Phase 2: Advanced SVG Output Controls

### 2.1 Vectorization Parameters

**VTracer-Specific Controls:**
```python
class VectorizationParams(BaseModel):
    # Path generation
    curve_fitting: Literal["auto", "tight", "smooth"] = "auto"
    corner_threshold: float = 60  # degrees
    path_precision: int = 2       # decimal places
    
    # Color handling
    color_mode: Literal["color", "monochrome", "grayscale"] = "color"
    hierarchical: bool = True     # Group by color hierarchy
    
    # Optimization
    simplify_paths: bool = True
    smooth_corners: bool = True
    remove_small_paths: bool = True
    min_path_area: float = 5      # pixels
```

### 2.2 SVG Output Options

```python
class SVGOutputConfig(BaseModel):
    # ViewBox and Dimensions
    viewbox_mode: Literal["auto", "custom", "percentage"] = "auto"
    custom_width: Optional[int] = None
    custom_height: Optional[int] = None
    
    # Styling
    style_mode: Literal["inline", "css", "attributes"] = "inline"
    add_classes: bool = False
    class_prefix: str = "path-"
    
    # Optimization
    optimization_level: Literal["none", "light", "standard", "aggressive"] = "standard"
    precision: int = 2
    remove_metadata: bool = True
    minify: bool = False
    
    # IDs and References
    id_prefix: Optional[str] = None
    reuse_paths: bool = True      # Use <use> for duplicate paths
```

### 2.3 Output Format Variants

Support multiple output formats:
- `svg` - Standard SVG
- `svgz` - Gzipped SVG
- `optimized.svg` - Aggressively optimized
- `pretty.svg` - Human-readable with indentation
- `inline.svg` - Optimized for inline HTML use

---

## Phase 3: Smart Preview & Comparison

### 3.1 Live Preview Mode

**Quick Preview:**
- Generate low-res preview in < 3 seconds
- Show preprocessing effects in real-time
- Compare original vs processed side-by-side

**Implementation:**
```python
@router.post("/preview")
async def generate_preview(
    file_id: str,
    preprocessing_config: PreprocessingConfig,
    max_dimension: int = 400  # Limit for speed
) -> PreviewResponse:
    """Generate quick preview of preprocessing effects."""
```

### 3.2 Comparison Mode

**Features:**
- Compare all 3 quality modes simultaneously
- Slider-based before/after comparison
- Overlay diff visualization
- Detailed metrics comparison

**Frontend Component:**
```typescript
interface ComparisonViewProps {
  modes: ('fast' | 'standard' | 'high' | 'custom')[];
  showMetrics: boolean;
  syncZoom: boolean;
  diffMode: 'side-by-side' | 'slider' | 'overlay';
}
```

### 3.3 Quality Metrics Dashboard

**Display Metrics:**
- File size comparison
- Path count
- Node count
- SSIM (structural similarity)
- Edge preservation score
- Processing time

---

## Phase 4: Workflow & Automation

### 4.1 Preset System

**Preset Types:**
- **Built-in Presets:** Logo, Photo, Line Art, Document, Sketch
- **User Presets:** Save custom configurations
- **Shared Presets:** Share via URL or code

**Preset Structure:**
```json
{
  "id": "logo-professional",
  "name": "Professional Logo",
  "description": "Optimized for logo conversion with sharp edges",
  "category": "logos",
  "preprocessing": {...},
  "vectorization": {...},
  "output": {...},
  "preview_image": "..."
}
```

### 4.2 Batch Processing Templates

**Features:**
- Apply preset to multiple files
- Naming pattern support: `{original}_{preset}_{timestamp}.svg`
- Progress tracking with per-file status
- ZIP download of all results
- Individual file download links

### 4.3 Enhanced API & Webhooks

**New Endpoints:**
```python
# Webhook management
POST   /api/v1/webhooks              # Register webhook
GET    /api/v1/webhooks              # List webhooks
DELETE /api/v1/webhooks/{id}         # Remove webhook

# Preset management
GET    /api/v1/presets               # List presets
POST   /api/v1/presets               # Create preset
PUT    /api/v1/presets/{id}          # Update preset
DELETE /api/v1/presets/{id}          # Delete preset

# Preview
POST   /api/v1/preview               # Generate preview
GET    /api/v1/preview/{preview_id}  # Get preview result

# Comparison
POST   /api/v1/compare/detailed      # Detailed comparison
GET    /api/v1/compare/{id}/metrics  # Get comparison metrics
```

**Webhook Events:**
- `conversion.started`
- `conversion.progress`
- `conversion.completed`
- `conversion.failed`
- `batch.completed`

### 4.4 CLI Improvements

```bash
# Preset usage
raster-to-svg convert input.png --preset logo-professional

# Config file
raster-to-svg convert input.png --config my-settings.yaml

# Preview
raster-to-svg preview input.png --preprocessing denoise,sharpen

# Batch with template
raster-to-svg batch ./images --preset photo-standard --output ./svgs

# Watch mode
raster-to-svg watch ./input --preset auto --output ./output
```

---

## Phase 5: UI/UX Enhancements

### 5.1 Control Level Toggle

```typescript
interface ControlLevel {
  level: 1 | 2 | 3;
  name: string;
  description: string;
  visibleOptions: string[];
}
```

**Level 1 (Simple):**
- Quality slider only
- Hide all advanced options
- Large, friendly convert button

**Level 2 (Guided):**
- Quality mode cards
- Basic preprocessing toggles
- Simple color palette slider

**Level 3 (Advanced):**
- All preprocessing controls
- Color palette editor
- Vectorization parameters
- Output configuration

### 5.2 New UI Components

1. **PreprocessingPipeline** - Drag-and-drop filter chain
2. **ColorPaletteEditor** - Visual color management
3. **ComparisonViewer** - Side-by-side/slider comparison
4. **MetricsPanel** - Quality statistics display
5. **PresetSelector** - Visual preset cards
6. **BatchQueue** - Batch progress tracking
7. **PreviewCanvas** - Live preview display

### 5.3 Responsive Layout Improvements

- Collapsible panels for mobile
- Touch-friendly controls
- Keyboard shortcuts
- Dark mode support

---

## Implementation Timeline

### Week 1-2: Foundation
- [ ] Backend: Preprocessing pipeline architecture
- [ ] Backend: Preview generation endpoint
- [ ] Frontend: Control level toggle
- [ ] Frontend: New store structure for advanced options

### Week 3-4: Preprocessing Controls
- [ ] Backend: Individual filter endpoints
- [ ] Frontend: PreprocessingPanel component
- [ ] Frontend: FilterCard components
- [ ] Integration: Live preview

### Week 5-6: Color & Vectorization
- [ ] Backend: Color palette extraction
- [ ] Frontend: ColorPaletteEditor
- [ ] Backend: Vectorization parameter support
- [ ] Frontend: Vectorization controls

### Week 7-8: Comparison & Presets
- [ ] Backend: Comparison endpoint
- [ ] Frontend: ComparisonViewer
- [ ] Backend: Preset system
- [ ] Frontend: PresetSelector

### Week 9-10: API & Automation
- [ ] Backend: Webhook support
- [ ] Backend: Enhanced batch processing
- [ ] CLI: Config file support
- [ ] Documentation: API updates

### Week 11-12: Polish & Release
- [ ] UI/UX refinements
- [ ] Testing & bug fixes
- [ ] Documentation
- [ ] Performance optimization

---

## Technical Considerations

### Performance
- Preview generation: < 3 seconds target
- Use thumbnail-sized images for preview
- Cache preprocessing results
- Lazy load advanced UI components

### Backward Compatibility
- All existing endpoints remain functional
- Default behavior unchanged for Level 1
- Existing presets map to new system

### Storage
- Preview images stored temporarily (1 hour TTL)
- Presets stored in Redis with backup
- User preferences in localStorage

### Security
- Validate all preprocessing parameters
- Limit preview image size
- Rate limit preview generation
- Sanitize custom color inputs

---

## Success Metrics

- **User Engagement:** 30% increase in conversions per session
- **Power User Adoption:** 20% of users use Level 3 controls
- **Preview Usage:** 70% of users check preview before converting
- **Performance:** Preview generation < 3 seconds
- **API Usage:** 50% increase in API calls (indicates integration)
