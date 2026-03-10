"""Advanced API models for granular control of preprocessing and conversion."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Preprocessing Filter Models
# =============================================================================


class FilterParams(BaseModel):
    """Base model for filter parameters."""

    enabled: bool = True


class DenoiseParams(FilterParams):
    """Parameters for denoise filter."""

    method: Literal["gaussian", "bilateral", "nlm", "median"] = "bilateral"
    strength: Literal["light", "medium", "heavy"] = "medium"
    preserve_edges: bool = True

    # Method-specific parameters
    kernel_size: int = Field(default=5, ge=3, le=15)
    sigma: float = Field(default=1.0, ge=0.1, le=5.0)

    # Bilateral-specific
    d: int = Field(default=9, ge=1, le=20)
    sigma_color: float = Field(default=75, ge=1, le=150)
    sigma_space: float = Field(default=75, ge=1, le=150)

    # NLM-specific
    h: float = Field(default=10, ge=1, le=30)
    template_window: int = Field(default=7, ge=3, le=15)
    search_window: int = Field(default=21, ge=11, le=35)


class SharpenParams(FilterParams):
    """Parameters for sharpen filter."""

    method: Literal["unsharp_mask", "kernel"] = "unsharp_mask"
    amount: float = Field(default=1.5, ge=0.5, le=3.0)

    # Unsharp mask parameters
    kernel_size: int = Field(default=5, ge=3, le=15)
    sigma: float = Field(default=1.0, ge=0.1, le=5.0)


class ContrastParams(FilterParams):
    """Parameters for contrast enhancement filter."""

    method: Literal["clahe", "histogram", "levels", "sigmoid"] = "clahe"

    # CLAHE parameters
    clip_limit: float = Field(default=2.0, ge=0.5, le=10.0)
    tile_size: int = Field(default=8, ge=4, le=32)

    # Levels parameters
    in_min: int = Field(default=0, ge=0, le=255)
    in_max: int = Field(default=255, ge=0, le=255)
    out_min: int = Field(default=0, ge=0, le=255)
    out_max: int = Field(default=255, ge=0, le=255)

    # Sigmoid parameters
    contrast: float = Field(default=10.0, ge=1.0, le=20.0)
    midpoint: float = Field(default=0.5, ge=0.1, le=0.9)


class ColorReduceParams(FilterParams):
    """Parameters for color reduction filter."""

    method: Literal["kmeans", "median_cut", "quantize"] = "kmeans"
    max_colors: int = Field(default=32, ge=2, le=256)
    dithering: Literal["none", "floyd_steinberg", "bayer", "atkinson", "ordered"] = "none"


class BlurParams(FilterParams):
    """Parameters for blur filter."""

    method: Literal["gaussian", "median", "box"] = "gaussian"
    radius: int = Field(default=3, ge=1, le=15)
    sigma: float = Field(default=1.0, ge=0.1, le=5.0)


class EdgeEnhanceParams(FilterParams):
    """Parameters for edge enhancement filter."""

    method: Literal["laplacian", "sobel", "scharr"] = "laplacian"
    strength: float = Field(default=0.3, ge=0.0, le=1.0)


class DespeckleParams(FilterParams):
    """Parameters for despeckle filter."""

    size: int = Field(default=3, ge=1, le=7)
    iterations: int = Field(default=1, ge=1, le=5)


class DeskewParams(FilterParams):
    """Parameters for deskew filter."""

    max_angle: float = Field(default=15.0, ge=0.0, le=45.0)
    auto_detect: bool = True


class PreprocessingStep(BaseModel):
    """A single preprocessing step in the pipeline."""

    id: str = Field(..., description="Unique step identifier")
    name: Literal[
        "denoise",
        "sharpen",
        "contrast",
        "color_reduce",
        "blur",
        "edge_enhance",
        "despeckle",
        "deskew",
    ]
    enabled: bool = True
    order: int = Field(..., ge=0, le=100)
    params: Dict[str, Any] = Field(default_factory=dict)


class PreprocessingPipeline(BaseModel):
    """Complete preprocessing pipeline configuration."""

    steps: List[PreprocessingStep] = Field(default_factory=list)

    @field_validator("steps")
    @classmethod
    def validate_unique_orders(cls, steps):
        orders = [step.order for step in steps]
        if len(orders) != len(set(orders)):
            raise ValueError("Step orders must be unique")
        return steps


# =============================================================================
# Color Palette Models
# =============================================================================


class ColorInfo(BaseModel):
    """Information about a color."""

    hex: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$")
    rgb: List[int] = Field(..., min_length=3, max_length=3)
    percentage: float = Field(..., ge=0.0, le=100.0)


class ColorPaletteConfig(BaseModel):
    """Configuration for color palette handling."""

    mode: Literal["auto", "extract", "custom", "preserve"] = "auto"
    max_colors: int = Field(default=32, ge=2, le=256)
    extracted_colors: List[str] = Field(default_factory=list)
    custom_colors: List[str] = Field(default_factory=list)
    dithering: Literal["none", "floyd_steinberg", "bayer", "atkinson", "ordered"] = "none"
    preserve_transparency: bool = True


# =============================================================================
# Vectorization Models
# =============================================================================


class VectorizationParams(BaseModel):
    """Parameters for vectorization process."""

    engine: Literal["vtracer", "potrace", "auto"] = "auto"

    # Path generation
    curve_fitting: Literal["auto", "tight", "smooth"] = "auto"
    corner_threshold: float = Field(default=60, ge=0, le=180)
    path_precision: int = Field(default=2, ge=0, le=5)

    # Color handling
    color_mode: Literal["color", "monochrome", "grayscale"] = "color"
    hierarchical: bool = True

    # Optimization
    simplify_paths: bool = True
    smooth_corners: bool = True
    remove_small_paths: bool = True
    min_path_area: float = Field(default=5, ge=0, le=100)


# =============================================================================
# SVG Output Models
# =============================================================================


class SVGOutputConfig(BaseModel):
    """Configuration for SVG output."""

    # ViewBox and Dimensions
    viewbox_mode: Literal["auto", "custom", "percentage"] = "auto"
    custom_width: Optional[int] = Field(default=None, ge=1, le=10000)
    custom_height: Optional[int] = Field(default=None, ge=1, le=10000)

    # Styling
    style_mode: Literal["inline", "css", "attributes"] = "inline"
    add_classes: bool = False
    class_prefix: str = "path-"

    # Optimization
    optimization_level: Literal["none", "light", "standard", "aggressive"] = "standard"
    precision: int = Field(default=2, ge=0, le=6)
    remove_metadata: bool = True
    minify: bool = False

    # IDs and References
    id_prefix: Optional[str] = None
    reuse_paths: bool = True


# =============================================================================
# Control Level Models
# =============================================================================


class ControlLevelConfig(BaseModel):
    """Configuration for different control levels."""

    level: Literal[1, 2, 3] = 2

    # Level 1: Only basic quality selection
    quality_mode: Literal["fast", "standard", "high"] = "standard"

    # Level 2: Guided control with presets
    image_type: Literal["auto", "color", "monochrome"] = "auto"
    color_palette: int = Field(default=32, ge=8, le=256)
    denoise_strength: Literal["light", "medium", "heavy"] = "medium"

    # Level 3: Full control (optional, uses detailed config)
    preprocessing: Optional[PreprocessingPipeline] = None
    palette_config: Optional[ColorPaletteConfig] = None
    vectorization: Optional[VectorizationParams] = None
    output_config: Optional[SVGOutputConfig] = None


# =============================================================================
# Preset Models
# =============================================================================


class ConversionPreset(BaseModel):
    """A saved preset for conversion settings."""

    id: str
    name: str
    description: str
    category: Literal["built_in", "user", "shared"] = "user"
    tags: List[str] = Field(default_factory=list)
    preview_image: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Configuration
    control_level: Literal[1, 2, 3] = 2
    preprocessing: Optional[PreprocessingPipeline] = None
    palette_config: Optional[ColorPaletteConfig] = None
    vectorization: Optional[VectorizationParams] = None
    output_config: Optional[SVGOutputConfig] = None

    # Simple mode settings (for level 1 & 2)
    quality_mode: Optional[Literal["fast", "standard", "high"]] = None
    image_type: Optional[Literal["auto", "color", "monochrome"]] = None
    color_palette: Optional[int] = None


class PresetListResponse(BaseModel):
    """Response for preset list endpoint."""

    presets: List[ConversionPreset]
    total: int
    categories: List[str]


# =============================================================================
# Preview Models
# =============================================================================


class PreviewRequest(BaseModel):
    """Request for preprocessing preview."""

    file_id: str
    preprocessing: Optional[PreprocessingPipeline] = None
    palette_config: Optional[ColorPaletteConfig] = None
    max_dimension: int = Field(default=400, ge=100, le=800)
    step_id: Optional[str] = None  # Preview specific step only


class PreviewResponse(BaseModel):
    """Response for preview request."""

    preview_id: str
    file_id: str
    original_url: str
    processed_url: str
    processing_time: float
    expires_at: datetime
    dimensions: Dict[str, int]


class FilterInfo(BaseModel):
    """Information about available filter."""

    id: str
    name: str
    description: str
    icon: str
    category: Literal["noise", "enhance", "color", "transform", "edge"]
    default_params: Dict[str, Any]
    param_schema: Dict[str, Any]


class AvailableFiltersResponse(BaseModel):
    """Response for available filters endpoint."""

    filters: List[FilterInfo]
    categories: List[str]


# =============================================================================
# Comparison Models
# =============================================================================


class ComparisonRequest(BaseModel):
    """Request for detailed comparison."""

    file_id: str
    modes: List[Literal["fast", "standard", "high", "custom"]]
    custom_config: Optional[ControlLevelConfig] = None
    include_metrics: bool = True


class ComparisonResult(BaseModel):
    """Result for a single mode in comparison."""

    mode: str
    job_id: str
    preview_url: str
    svg_url: Optional[str] = None
    file_size: Optional[int] = None
    processing_time: Optional[float] = None
    metrics: Optional[Dict[str, float]] = None


class ComparisonResponse(BaseModel):
    """Response for comparison request."""

    comparison_id: str
    file_id: str
    results: List[ComparisonResult]
    created_at: datetime


# =============================================================================
# Enhanced Conversion Models
# =============================================================================


class EnhancedConversionRequest(BaseModel):
    """Enhanced conversion request with full control."""

    file_id: str
    control_level: Literal[1, 2, 3] = 2

    # Level 1 & 2 settings
    quality_mode: Literal["fast", "standard", "high"] = "standard"
    image_type: Literal["auto", "color", "monochrome"] = "auto"
    color_palette: int = Field(default=32, ge=8, le=256)
    denoise_strength: Literal["light", "medium", "heavy"] = "medium"

    # Level 3 settings (advanced)
    preset_id: Optional[str] = None
    preprocessing: Optional[PreprocessingPipeline] = None
    palette_config: Optional[ColorPaletteConfig] = None
    vectorization: Optional[VectorizationParams] = None
    output_config: Optional[SVGOutputConfig] = None

    # Options
    generate_preview: bool = True
    webhook_url: Optional[str] = None


class EnhancedConversionResponse(BaseModel):
    """Response for enhanced conversion request."""

    job_id: str
    status: str
    preview_job_id: Optional[str] = None
    created_at: datetime
    estimated_time: Optional[float] = None


# =============================================================================
# Webhook Models
# =============================================================================


class WebhookConfig(BaseModel):
    """Configuration for webhook."""

    id: str
    url: str
    events: List[
        Literal[
            "conversion.started",
            "conversion.progress",
            "conversion.completed",
            "conversion.failed",
            "batch.completed",
        ]
    ]
    secret: Optional[str] = None
    active: bool = True
    created_at: Optional[datetime] = None


class WebhookPayload(BaseModel):
    """Payload sent to webhook."""

    event: str
    timestamp: datetime
    job_id: Optional[str] = None
    batch_id: Optional[str] = None
    data: Dict[str, Any]
    signature: Optional[str] = None


# =============================================================================
# Image Analysis Models
# =============================================================================


class ImageAnalysisResult(BaseModel):
    """Result of image analysis."""

    file_id: str
    is_photo: bool
    is_line_art: bool
    has_text: bool
    color_complexity: float  # 0-1 scale
    unique_colors: int
    noise_level: float  # 0-1 scale
    brightness: float  # 0-1 scale
    contrast: float  # 0-1 scale
    sharpness: float  # 0-1 scale
    recommended_mode: Literal["fast", "standard", "high"]
    recommended_preset: Optional[str] = None
    suggested_filters: List[str] = Field(default_factory=list)


class ImageAnalysisRequest(BaseModel):
    """Request for image analysis."""

    file_id: str
    detailed: bool = False
