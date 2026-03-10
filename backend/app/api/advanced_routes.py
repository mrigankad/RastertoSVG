"""Advanced API routes for granular control of preprocessing and conversion."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse, JSONResponse

from app.api.advanced_models import (
    AvailableFiltersResponse,
    ComparisonRequest,
    ComparisonResponse,
    ComparisonResult,
    ConversionPreset,
    ControlLevelConfig,
    EnhancedConversionRequest,
    EnhancedConversionResponse,
    FilterInfo,
    ImageAnalysisRequest,
    ImageAnalysisResult,
    PresetListResponse,
    PreviewRequest,
    PreviewResponse,
    PreprocessingStep,
)
from app.config import settings
from app.services.file_manager import FileManager
from app.services.job_tracker import JobTracker
from app.services.preprocessing_pipeline import (
    ColorPaletteExtractor,
    ImageAnalyzer,
    PreprocessingPipelineBuilder,
)
from app.services.webhook_service import get_webhook_service, WebhookConfig
from app.workers.tasks import convert_image_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/advanced", tags=["Advanced Controls"])

# Initialize services
file_manager = FileManager()
job_tracker = JobTracker()
pipeline_builder = PreprocessingPipelineBuilder()
color_extractor = ColorPaletteExtractor()
image_analyzer = ImageAnalyzer()

# In-memory preset store (would use database in production)
PRESETS: Dict[str, ConversionPreset] = {}

# Initialize built-in presets
def init_builtin_presets():
    """Initialize built-in presets."""
    builtin_presets = [
        ConversionPreset(
            id="logo-professional",
            name="Professional Logo",
            description="Optimized for logo conversion with sharp edges and clean colors",
            category="built_in",
            tags=["logo", "vector", "clean"],
            quality_mode="high",
            image_type="color",
        ),
        ConversionPreset(
            id="photo-standard",
            name="Photo Standard",
            description="Balanced settings for photograph conversion",
            category="built_in",
            tags=["photo", "image", "balanced"],
            quality_mode="standard",
            image_type="color",
        ),
        ConversionPreset(
            id="line-art",
            name="Line Art & Illustrations",
            description="Optimized for line drawings and illustrations",
            category="built_in",
            tags=["line-art", "illustration", "drawing"],
            quality_mode="fast",
            image_type="monochrome",
        ),
        ConversionPreset(
            id="document-scan",
            name="Document Scan",
            description="Optimized for scanned documents with deskew and despeckle",
            category="built_in",
            tags=["document", "scan", "text"],
            quality_mode="standard",
            image_type="monochrome",
        ),
        ConversionPreset(
            id="sketch-preserve",
            name="Sketch Preserve",
            description="Preserves pencil/pen sketch details and textures",
            category="built_in",
            tags=["sketch", "art", "preserve"],
            quality_mode="high",
            image_type="monochrome",
        ),
    ]
    
    for preset in builtin_presets:
        PRESETS[preset.id] = preset


init_builtin_presets()


# =============================================================================
# Filter Management Endpoints
# =============================================================================

@router.get("/filters", response_model=AvailableFiltersResponse)
async def get_available_filters() -> AvailableFiltersResponse:
    """Get list of available preprocessing filters."""
    filters = [
        FilterInfo(
            id="denoise",
            name="Denoise",
            description="Remove image noise while preserving edges",
            icon="waves",
            category="noise",
            default_params={
                "method": "bilateral",
                "strength": "medium",
                "preserve_edges": True,
            },
            param_schema={
                "method": {
                    "type": "string",
                    "enum": ["gaussian", "bilateral", "nlm", "median"],
                    "description": "Denoising algorithm",
                },
                "strength": {
                    "type": "string",
                    "enum": ["light", "medium", "heavy"],
                    "description": "Denoising strength",
                },
            },
        ),
        FilterInfo(
            id="sharpen",
            name="Sharpen",
            description="Enhance edge sharpness and details",
            icon="zap",
            category="enhance",
            default_params={
                "method": "unsharp_mask",
                "amount": 1.5,
            },
            param_schema={
                "method": {
                    "type": "string",
                    "enum": ["unsharp_mask", "kernel"],
                    "description": "Sharpening method",
                },
                "amount": {
                    "type": "number",
                    "minimum": 0.5,
                    "maximum": 3.0,
                    "description": "Sharpening strength",
                },
            },
        ),
        FilterInfo(
            id="contrast",
            name="Contrast",
            description="Enhance image contrast",
            icon="sun",
            category="enhance",
            default_params={
                "method": "clahe",
                "clip_limit": 2.0,
                "tile_size": 8,
            },
            param_schema={
                "method": {
                    "type": "string",
                    "enum": ["clahe", "histogram", "levels", "sigmoid"],
                    "description": "Contrast enhancement method",
                },
                "clip_limit": {
                    "type": "number",
                    "minimum": 0.5,
                    "maximum": 10.0,
                    "description": "CLAHE clip limit",
                },
            },
        ),
        FilterInfo(
            id="color_reduce",
            name="Color Reduce",
            description="Reduce number of colors in the image",
            icon="palette",
            category="color",
            default_params={
                "method": "kmeans",
                "max_colors": 32,
                "dithering": "none",
            },
            param_schema={
                "method": {
                    "type": "string",
                    "enum": ["kmeans", "median_cut", "quantize"],
                    "description": "Color reduction method",
                },
                "max_colors": {
                    "type": "integer",
                    "minimum": 2,
                    "maximum": 256,
                    "description": "Maximum number of colors",
                },
            },
        ),
        FilterInfo(
            id="blur",
            name="Blur",
            description="Apply blur effect",
            icon="droplet",
            category="enhance",
            default_params={
                "method": "gaussian",
                "radius": 3,
                "sigma": 1.0,
            },
            param_schema={
                "method": {
                    "type": "string",
                    "enum": ["gaussian", "median", "box"],
                    "description": "Blur method",
                },
                "radius": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 15,
                    "description": "Blur radius",
                },
            },
        ),
        FilterInfo(
            id="edge_enhance",
            name="Edge Enhance",
            description="Enhance edges and boundaries",
            icon="hexagon",
            category="edge",
            default_params={
                "method": "laplacian",
                "strength": 0.3,
            },
            param_schema={
                "method": {
                    "type": "string",
                    "enum": ["laplacian", "sobel", "scharr"],
                    "description": "Edge detection method",
                },
                "strength": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Enhancement strength",
                },
            },
        ),
        FilterInfo(
            id="despeckle",
            name="Despeckle",
            description="Remove small specks and artifacts",
            icon="eraser",
            category="noise",
            default_params={
                "size": 3,
                "iterations": 1,
            },
            param_schema={
                "size": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 7,
                    "description": "Filter size",
                },
                "iterations": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Number of iterations",
                },
            },
        ),
        FilterInfo(
            id="deskew",
            name="Deskew",
            description="Straighten tilted documents",
            icon="rotate-ccw",
            category="transform",
            default_params={
                "max_angle": 15.0,
                "auto_detect": True,
            },
            param_schema={
                "max_angle": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 45.0,
                    "description": "Maximum skew angle to correct",
                },
                "auto_detect": {
                    "type": "boolean",
                    "description": "Automatically detect skew angle",
                },
            },
        ),
    ]
    
    categories = ["noise", "enhance", "color", "transform", "edge"]
    
    return AvailableFiltersResponse(filters=filters, categories=categories)


# =============================================================================
# Preview Endpoints
# =============================================================================

@router.post("/preview", response_model=PreviewResponse)
async def create_preview(request: PreviewRequest) -> PreviewResponse:
    """
    Generate a preview of preprocessing effects.
    
    Returns a quick preview (low resolution) of how the image will look
    after applying the specified preprocessing pipeline.
    """
    # Validate file exists
    upload_path = file_manager.get_upload(request.file_id)
    if not upload_path:
        raise HTTPException(404, "File not found or expired")
    
    try:
        # Load image
        import cv2
        img = cv2.imread(str(upload_path))
        if img is None:
            raise HTTPException(400, "Could not load image")
        
        original_shape = img.shape
        
        # Resize for quick preview
        max_dim = request.max_dimension
        height, width = img.shape[:2]
        scale = min(max_dim / width, max_dim / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        img_small = cv2.resize(img, (new_width, new_height))
        
        # Get or create pipeline
        if request.preprocessing:
            pipeline = request.preprocessing
        else:
            # Use default standard pipeline
            pipeline = pipeline_builder.get_default_pipeline("standard", "color")
        
        # Apply preprocessing
        start_time = datetime.now(timezone.utc)
        processed = pipeline_builder.apply_pipeline(img_small, pipeline)
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Save preview images
        preview_id = str(uuid.uuid4())
        preview_dir = Path(settings.STORAGE_PATH) / "previews"
        preview_dir.mkdir(parents=True, exist_ok=True)
        
        original_preview_path = preview_dir / f"{preview_id}_original.png"
        processed_preview_path = preview_dir / f"{preview_id}_processed.png"
        
        cv2.imwrite(str(original_preview_path), img_small)
        cv2.imwrite(str(processed_preview_path), processed)
        
        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        return PreviewResponse(
            preview_id=preview_id,
            file_id=request.file_id,
            original_url=f"/api/v1/advanced/preview/{preview_id}/original",
            processed_url=f"/api/v1/advanced/preview/{preview_id}/processed",
            processing_time=processing_time,
            expires_at=expires_at,
            dimensions={"width": new_width, "height": new_height},
        )
        
    except Exception as e:
        logger.error(f"Preview generation failed: {e}")
        raise HTTPException(500, f"Failed to generate preview: {str(e)}")


@router.get("/preview/{preview_id}/{type:str}")
async def get_preview_image(preview_id: str, type: str):
    """Get preview image (original or processed)."""
    if type not in ["original", "processed"]:
        raise HTTPException(400, "Invalid preview type")
    
    preview_path = Path(settings.STORAGE_PATH) / "previews" / f"{preview_id}_{type}.png"
    
    if not preview_path.exists():
        raise HTTPException(404, "Preview not found")
    
    return FileResponse(
        path=str(preview_path),
        media_type="image/png",
    )


# =============================================================================
# Color Palette Endpoints
# =============================================================================

@router.post("/extract-colors/{file_id}")
async def extract_colors(
    file_id: str,
    max_colors: int = Query(default=32, ge=2, le=256),
):
    """Extract dominant colors from an image."""
    upload_path = file_manager.get_upload(file_id)
    if not upload_path:
        raise HTTPException(404, "File not found or expired")
    
    try:
        import cv2
        img = cv2.imread(str(upload_path))
        if img is None:
            raise HTTPException(400, "Could not load image")
        
        # Resize for faster processing
        img_small = cv2.resize(img, (200, 200))
        
        palette = color_extractor.extract_palette(img_small, max_colors=max_colors)
        
        return {
            "file_id": file_id,
            "max_colors": max_colors,
            "palette": palette,
            "total_colors": len(palette),
        }
        
    except Exception as e:
        logger.error(f"Color extraction failed: {e}")
        raise HTTPException(500, f"Failed to extract colors: {str(e)}")


# =============================================================================
# Image Analysis Endpoints
# =============================================================================

@router.post("/analyze/{file_id}", response_model=ImageAnalysisResult)
async def analyze_image(file_id: str, detailed: bool = False) -> ImageAnalysisResult:
    """Analyze image characteristics and recommend settings."""
    upload_path = file_manager.get_upload(file_id)
    if not upload_path:
        raise HTTPException(404, "File not found or expired")
    
    try:
        import cv2
        img = cv2.imread(str(upload_path))
        if img is None:
            raise HTTPException(400, "Could not load image")
        
        # Resize for faster analysis
        max_size = 400 if not detailed else 800
        height, width = img.shape[:2]
        scale = min(max_size / max(width, height), 1.0)
        if scale < 1.0:
            img = cv2.resize(img, (int(width * scale), int(height * scale)))
        
        analysis = image_analyzer.analyze(img)
        
        return ImageAnalysisResult(
            file_id=file_id,
            is_photo=analysis["is_photo"],
            is_line_art=analysis["is_line_art"],
            has_text=analysis["has_text"],
            color_complexity=analysis["color_complexity"],
            unique_colors=analysis["unique_colors"],
            noise_level=analysis["noise_level"],
            brightness=analysis["brightness"],
            contrast=analysis["contrast"],
            sharpness=analysis["sharpness"],
            recommended_mode=analysis["recommended_mode"],
            suggested_filters=analysis["suggested_filters"],
        )
        
    except Exception as e:
        logger.error(f"Image analysis failed: {e}")
        raise HTTPException(500, f"Failed to analyze image: {str(e)}")


# =============================================================================
# Preset Endpoints
# =============================================================================

@router.get("/presets", response_model=PresetListResponse)
async def list_presets(
    category: Optional[str] = None,
    search: Optional[str] = None,
) -> PresetListResponse:
    """List available conversion presets."""
    presets = list(PRESETS.values())
    
    # Filter by category
    if category:
        presets = [p for p in presets if p.category == category]
    
    # Filter by search
    if search:
        search_lower = search.lower()
        presets = [
            p for p in presets
            if search_lower in p.name.lower()
            or search_lower in p.description.lower()
            or any(search_lower in tag.lower() for tag in p.tags)
        ]
    
    categories = list(set(p.category for p in PRESETS.values()))
    
    return PresetListResponse(
        presets=presets,
        total=len(presets),
        categories=categories,
    )


@router.get("/presets/{preset_id}", response_model=ConversionPreset)
async def get_preset(preset_id: str) -> ConversionPreset:
    """Get a specific preset by ID."""
    if preset_id not in PRESETS:
        raise HTTPException(404, "Preset not found")
    return PRESETS[preset_id]


@router.post("/presets", response_model=ConversionPreset)
async def create_preset(preset: ConversionPreset) -> ConversionPreset:
    """Create a new custom preset."""
    if preset.id in PRESETS:
        raise HTTPException(400, "Preset ID already exists")
    
    preset.category = "user"
    preset.created_at = datetime.now(timezone.utc)
    preset.updated_at = preset.created_at
    
    PRESETS[preset.id] = preset
    
    return preset


@router.put("/presets/{preset_id}", response_model=ConversionPreset)
async def update_preset(preset_id: str, preset: ConversionPreset) -> ConversionPreset:
    """Update an existing preset."""
    if preset_id not in PRESETS:
        raise HTTPException(404, "Preset not found")
    
    existing = PRESETS[preset_id]
    if existing.category == "built_in":
        raise HTTPException(403, "Cannot modify built-in presets")
    
    preset.updated_at = datetime.now(timezone.utc)
    PRESETS[preset_id] = preset
    
    return preset


@router.delete("/presets/{preset_id}")
async def delete_preset(preset_id: str):
    """Delete a custom preset."""
    if preset_id not in PRESETS:
        raise HTTPException(404, "Preset not found")
    
    existing = PRESETS[preset_id]
    if existing.category == "built_in":
        raise HTTPException(403, "Cannot delete built-in presets")
    
    del PRESETS[preset_id]
    
    return {"status": "deleted", "preset_id": preset_id}


# =============================================================================
# Enhanced Conversion Endpoints
# =============================================================================

@router.post("/convert", response_model=EnhancedConversionResponse)
async def enhanced_convert(request: EnhancedConversionRequest) -> EnhancedConversionResponse:
    """
    Start an enhanced conversion with granular control.
    
    Supports 3 control levels:
    - Level 1: Simple quality mode selection
    - Level 2: Guided control with presets and basic options
    - Level 3: Full control with custom preprocessing pipeline
    """
    # Validate file exists
    upload_path = file_manager.get_upload(request.file_id)
    if not upload_path:
        raise HTTPException(404, "File not found or expired")
    
    try:
        # Build options based on control level
        options = _build_conversion_options(request)
        
        # Estimate processing time
        estimated_time = _estimate_processing_time(request)
        
        # Create job
        job_id = job_tracker.create_job(request.file_id, options)
        
        # Queue conversion task
        task = convert_image_task.delay(job_id)
        
        # Create preview job if requested
        preview_job_id = None
        if request.generate_preview:
            preview_job_id = f"{job_id}_preview"
            # TODO: Queue preview generation task
        
        logger.info(f"Created enhanced conversion job: {job_id}")
        
        return EnhancedConversionResponse(
            job_id=job_id,
            status="pending",
            preview_job_id=preview_job_id,
            created_at=datetime.now(timezone.utc),
            estimated_time=estimated_time,
        )
        
    except Exception as e:
        logger.error(f"Failed to create enhanced conversion: {e}")
        raise HTTPException(500, f"Failed to create conversion: {str(e)}")


def _build_conversion_options(request: EnhancedConversionRequest) -> Dict[str, Any]:
    """Build conversion options from request."""
    options = {
        "control_level": request.control_level,
        "webhook_url": request.webhook_url,
    }
    
    if request.control_level == 1:
        # Simple mode
        options["quality_mode"] = request.quality_mode
        options["image_type"] = "auto"
        
    elif request.control_level == 2:
        # Guided mode
        options["quality_mode"] = request.quality_mode
        options["image_type"] = request.image_type
        options["color_palette"] = request.color_palette
        options["denoise_strength"] = request.denoise_strength
        
        # Build preprocessing pipeline from simple settings
        pipeline = pipeline_builder.get_default_pipeline(
            request.quality_mode,
            request.image_type,
        )
        options["preprocessing"] = pipeline.model_dump()
        
    elif request.control_level == 3:
        # Advanced mode
        if request.preset_id and request.preset_id in PRESETS:
            preset = PRESETS[request.preset_id]
            # Apply preset settings
            if preset.preprocessing:
                options["preprocessing"] = preset.preprocessing.model_dump()
            if preset.palette_config:
                options["palette_config"] = preset.palette_config.model_dump()
            if preset.vectorization:
                options["vectorization"] = preset.vectorization.model_dump()
            if preset.output_config:
                options["output_config"] = preset.output_config.model_dump()
        
        # Override with explicit settings
        if request.preprocessing:
            options["preprocessing"] = request.preprocessing.model_dump()
        if request.palette_config:
            options["palette_config"] = request.palette_config.model_dump()
        if request.vectorization:
            options["vectorization"] = request.vectorization.model_dump()
        if request.output_config:
            options["output_config"] = request.output_config.model_dump()
    
    return options


def _estimate_processing_time(request: EnhancedConversionRequest) -> Optional[float]:
    """Estimate processing time based on settings."""
    base_times = {
        "fast": 1.0,
        "standard": 3.0,
        "high": 8.0,
    }
    
    if request.control_level == 1:
        return base_times.get(request.quality_mode, 3.0)
    
    if request.control_level == 2:
        return base_times.get(request.quality_mode, 3.0)
    
    if request.control_level == 3 and request.preprocessing:
        # Count enabled steps
        enabled_steps = sum(1 for step in request.preprocessing.steps if step.enabled)
        return enabled_steps * 1.5
    
    return None


# =============================================================================
# Comparison Endpoints
# =============================================================================

@router.post("/compare", response_model=ComparisonResponse)
async def create_comparison(request: ComparisonRequest) -> ComparisonResponse:
    """
    Create a comparison of different conversion modes.
    
    Generates previews and conversions for multiple modes simultaneously
    for side-by-side comparison.
    """
    upload_path = file_manager.get_upload(request.file_id)
    if not upload_path:
        raise HTTPException(404, "File not found or expired")
    
    try:
        comparison_id = str(uuid.uuid4())
        results = []
        
        for mode in request.modes:
            # Create job for each mode
            if mode == "custom" and request.custom_config:
                options = _build_conversion_options(
                    EnhancedConversionRequest(
                        file_id=request.file_id,
                        control_level=request.custom_config.control_level,
                        quality_mode=request.custom_config.quality_mode or "standard",
                        image_type=request.custom_config.image_type or "auto",
                        preprocessing=request.custom_config.preprocessing,
                    )
                )
            else:
                options = {
                    "quality_mode": mode,
                    "image_type": "auto",
                    "control_level": 2,
                }
            
            job_id = job_tracker.create_job(request.file_id, options)
            convert_image_task.delay(job_id)
            
            results.append(ComparisonResult(
                mode=mode,
                job_id=job_id,
                preview_url=f"/api/v1/status/{job_id}",
            ))
        
        return ComparisonResponse(
            comparison_id=comparison_id,
            file_id=request.file_id,
            results=results,
            created_at=datetime.now(timezone.utc),
        )
        
    except Exception as e:
        logger.error(f"Comparison creation failed: {e}")
        raise HTTPException(500, f"Failed to create comparison: {str(e)}")


# =============================================================================
# Default Pipeline Endpoints
# =============================================================================

@router.get("/pipeline/defaults/{quality_mode}")
async def get_default_pipeline(
    quality_mode: str,
    image_type: str = "auto",
):
    """Get default preprocessing pipeline for a quality mode."""
    if quality_mode not in ["fast", "standard", "high"]:
        raise HTTPException(400, "Invalid quality mode")
    
    pipeline = pipeline_builder.get_default_pipeline(quality_mode, image_type)
    
    return {
        "quality_mode": quality_mode,
        "image_type": image_type,
        "pipeline": pipeline.model_dump(),
    }


# =============================================================================
# Webhook Endpoints
# =============================================================================

@router.get("/webhooks")
async def list_webhooks(active_only: bool = False):
    """List all configured webhooks."""
    service = get_webhook_service()
    webhooks = service.list_webhooks(active_only=active_only)
    return {
        "webhooks": [w.model_dump() for w in webhooks],
        "total": len(webhooks),
    }


@router.post("/webhooks")
async def create_webhook(
    url: str,
    events: List[str],
    secret: Optional[str] = None,
):
    """Create a new webhook configuration."""
    # Validate events
    valid_events = [
        "conversion.started",
        "conversion.progress",
        "conversion.completed",
        "conversion.failed",
        "batch.completed",
    ]
    
    invalid_events = [e for e in events if e not in valid_events]
    if invalid_events:
        raise HTTPException(400, f"Invalid events: {invalid_events}")
    
    service = get_webhook_service()
    webhook = service.create_webhook(url=url, events=events, secret=secret)
    
    return webhook.model_dump()


@router.get("/webhooks/{webhook_id}")
async def get_webhook(webhook_id: str):
    """Get webhook by ID."""
    service = get_webhook_service()
    webhook = service.get_webhook(webhook_id)
    
    if not webhook:
        raise HTTPException(404, "Webhook not found")
    
    return webhook.model_dump()


@router.put("/webhooks/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    url: Optional[str] = None,
    events: Optional[List[str]] = None,
    secret: Optional[str] = None,
    active: Optional[bool] = None,
):
    """Update webhook configuration."""
    service = get_webhook_service()
    
    webhook = service.update_webhook(
        webhook_id=webhook_id,
        url=url,
        events=events,
        secret=secret,
        active=active,
    )
    
    if not webhook:
        raise HTTPException(404, "Webhook not found")
    
    return webhook.model_dump()


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Delete a webhook."""
    service = get_webhook_service()
    
    if not service.delete_webhook(webhook_id):
        raise HTTPException(404, "Webhook not found")
    
    return {"status": "deleted", "webhook_id": webhook_id}


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: str):
    """Send a test event to a webhook."""
    service = get_webhook_service()
    webhook = service.get_webhook(webhook_id)
    
    if not webhook:
        raise HTTPException(404, "Webhook not found")
    
    import asyncio
    
    # Send test event
    success = await service.send_webhook(
        webhook=webhook,
        event="webhook.test",
        data={"message": "This is a test event", "timestamp": datetime.now(timezone.utc).isoformat()},
    )
    
    if success:
        return {"status": "sent", "message": "Test event sent successfully"}
    else:
        raise HTTPException(500, "Failed to send test event")
