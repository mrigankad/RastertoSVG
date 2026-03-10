"""API models for the AI-Powered Vectorization Engine (Phase 7)."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Engine Selection Models
# =============================================================================

class EngineCapability(BaseModel):
    """Information about a single engine's capabilities."""
    id: str
    name: str
    description: str
    best_for: List[str]
    color_support: bool
    speed: str
    quality_range: str
    requires_gpu: bool


class EngineCapabilitiesResponse(BaseModel):
    """Response with all available engine capabilities."""
    engines: List[EngineCapability]
    categories: List[str]


class ImageFeatureReport(BaseModel):
    """Report of extracted image features."""
    dimensions: str
    megapixels: float
    is_grayscale: bool
    unique_colors: int
    dominant_colors: int
    color_complexity: float
    edge_density: float
    texture_energy: float
    noise_level: float
    contour_count: int


class EngineRecommendationResponse(BaseModel):
    """Engine recommendation with confidence and reasoning."""
    engine: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    category: str
    reasoning: str
    alternative: Optional[str] = None
    estimated_quality: float = Field(default=0.0, ge=0.0, le=1.0)
    estimated_time: float = Field(default=0.0, ge=0.0)
    suggested_params: Dict[str, Any] = Field(default_factory=dict)
    preprocessing_hints: List[str] = Field(default_factory=list)


class NoiseAnalysisReport(BaseModel):
    """Noise analysis results."""
    noise_score: float = Field(..., ge=0.0, le=1.0)
    noise_type: str
    recommendation: Dict[str, Any] = Field(default_factory=dict)


class ImageAnalysisResponse(BaseModel):
    """Full image analysis response."""
    recommendation: EngineRecommendationResponse
    features: ImageFeatureReport
    noise: NoiseAnalysisReport
    capabilities: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# AI Conversion Models
# =============================================================================

class AIConversionRequest(BaseModel):
    """Request for AI-powered conversion."""
    file_id: str = Field(..., description="Uploaded file ID")
    mode: Literal["auto", "speed", "balanced", "quality", "max_quality"] = Field(
        default="auto",
        description="Quality mode — 'auto' lets AI decide"
    )
    engine_override: Optional[str] = Field(
        default=None,
        description="Force a specific engine (potrace, vtracer, sam_vtracer, sam_diffvg)"
    )
    
    # Feature toggles
    enable_ai_preprocessing: bool = Field(
        default=True,
        description="Enable smart preprocessing (denoise, contrast, sharpen)"
    )
    enable_sam: bool = Field(
        default=True,
        description="Enable SAM-guided segmentation for complex images"
    )
    enable_optimization: bool = Field(
        default=True,
        description="Enable DiffVG-inspired SVG post-optimization"
    )
    enable_gradients: bool = Field(
        default=True,
        description="Detect and add SVG gradient fills"
    )
    enable_upscale: bool = Field(
        default=True,
        description="Auto-upscale small images"
    )
    enable_bg_removal: bool = Field(
        default=False,
        description="Remove background before conversion"
    )
    
    # Custom parameters
    custom_params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Custom engine parameters to override AI suggestions"
    )
    
    # Options
    webhook_url: Optional[str] = Field(
        default=None,
        description="Webhook URL for conversion completion notification"
    )
    generate_preview: bool = Field(
        default=True,
        description="Generate a preview image alongside the SVG"
    )


class AIConversionTimings(BaseModel):
    """Timing breakdown for AI conversion."""
    load: Optional[float] = None
    analysis: Optional[float] = None
    ai_preprocessing: Optional[float] = None
    sam_segmentation: Optional[float] = None
    conversion: Optional[float] = None
    optimization: Optional[float] = None


class AIConversionResponse(BaseModel):
    """Response for AI-powered conversion."""
    job_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    engine_used: Optional[str] = None
    category_detected: Optional[str] = None
    confidence: Optional[float] = None
    mode: str
    
    # AI feature usage
    ai_features_used: List[str] = Field(default_factory=list)
    preprocessing_steps: List[str] = Field(default_factory=list)
    
    # Results (populated when completed)
    output_url: Optional[str] = None
    output_size_bytes: Optional[int] = None
    
    # Timing
    estimated_time: Optional[float] = None
    timings: Optional[AIConversionTimings] = None
    total_time: Optional[float] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now())


# =============================================================================
# AI Preprocessing Models
# =============================================================================

class AIPreprocessingRequest(BaseModel):
    """Request for AI-only preprocessing (without conversion)."""
    file_id: str
    enable_denoise: bool = True
    enable_upscale: bool = True
    enable_bg_removal: bool = False
    enable_contrast: bool = True
    enable_sharpen: bool = True
    upscale_factor: int = Field(default=2, ge=2, le=4)
    min_dimension: int = Field(default=800, ge=256, le=4096)


class AIPreprocessingResponse(BaseModel):
    """Response for AI preprocessing."""
    preview_id: str
    file_id: str
    original_url: str
    processed_url: str
    steps_applied: List[str]
    noise_analysis: Optional[Dict[str, Any]] = None
    processing_time: float
    original_size: Dict[str, int]
    processed_size: Dict[str, int]


# =============================================================================
# Background Removal Models
# =============================================================================

class BackgroundRemovalRequest(BaseModel):
    """Request for AI background removal."""
    file_id: str
    method: Literal["auto", "grabcut", "color", "edge"] = "auto"
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class BackgroundRemovalResponse(BaseModel):
    """Response for background removal."""
    preview_id: str
    file_id: str
    original_url: str
    processed_url: str
    method_used: str
    mask_coverage: float
    processing_time: float


# =============================================================================
# Noise Analysis Models
# =============================================================================

class NoiseAnalysisRequest(BaseModel):
    """Request for noise analysis."""
    file_id: str


class NoiseAnalysisResponse(BaseModel):
    """Detailed noise analysis response."""
    file_id: str
    noise_score: float = Field(..., ge=0.0, le=1.0)
    noise_type: str
    laplacian_variance: float
    mad_noise: float
    local_noise: float
    high_freq_noise: float
    recommendation: Dict[str, Any]


# =============================================================================
# Capabilities Models
# =============================================================================

class AICapabilitiesResponse(BaseModel):
    """Response with all AI engine capabilities."""
    engines: Dict[str, Any]
    ai_preprocessing: Dict[str, Any]
    diffvg_optimizer: Dict[str, Any]
    sam_available: bool
    modes: Dict[str, str]
