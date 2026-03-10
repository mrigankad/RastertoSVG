"""Export & Animation API routes — Phase 10.

Endpoints:
- GET  /export/formats          — Available export formats
- POST /export/convert          — Convert SVG to target format
- POST /export/batch            — Batch export to multiple formats
- GET  /animation/presets       — Available animation presets
- POST /animation/apply         — Apply animation to SVG
- POST /animation/lottie        — Export SVG as Lottie JSON
- POST /enhance/responsive      — Make SVG responsive + accessible
- POST /enhance/stats           — Get SVG statistics
- POST /enhance/gradients       — Add gradient definitions
"""

import io
import logging
import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from app.services.format_exporters import (
    ExportEngine,
    ExportFormat,
    ExportOptions,
    FORMAT_INFO,
)
from app.services.svg_animator import (
    SVGAnimationEngine,
    AnimationConfig,
    AnimationType,
    AnimationMethod,
)
from app.services.svg_enhancer import SVGEnhancer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["Export & Animation (Phase 10)"])


# =============================================================================
# Request / Response Models
# =============================================================================

class ExportRequest(BaseModel):
    format: str = Field(description="Target format: svg, pdf, eps, dxf, emf, png")
    scale: float = Field(default=1.0, ge=0.1, le=10.0)
    dpi: int = Field(default=300, ge=72, le=1200)
    width: Optional[int] = Field(default=None, ge=1, le=32768)
    height: Optional[int] = Field(default=None, ge=1, le=32768)
    background_color: Optional[str] = None
    color_space: str = Field(default="rgb")

class BatchExportRequest(BaseModel):
    formats: List[str] = Field(description="List of target formats")
    scale: float = Field(default=1.0, ge=0.1, le=10.0)
    dpi: int = Field(default=300, ge=72, le=1200)

class AnimationRequest(BaseModel):
    preset: Optional[str] = Field(default=None, description="Preset name: draw_stroke, fade_in, color_cycle, pulse")
    type: Optional[str] = Field(default=None, description="Animation type override")
    method: str = Field(default="css", description="css, smil, or lottie")
    duration: float = Field(default=2.0, ge=0.1, le=30.0)
    delay: float = Field(default=0.0, ge=0.0, le=10.0)
    stagger: float = Field(default=0.1, ge=0.0, le=2.0)
    easing: str = Field(default="ease-in-out")
    iteration_count: str = Field(default="1")
    colors: List[str] = Field(default=["#3b82f6", "#8b5cf6", "#ec4899"])

class EnhanceRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    make_responsive: bool = True
    add_accessibility: bool = True
    add_metadata: bool = True
    minify: bool = False
    lang: str = "en"

class GradientDef(BaseModel):
    id: str
    type: str = "linear"
    stops: List[dict]
    x1: str = "0%"
    y1: str = "0%"
    x2: str = "100%"
    y2: str = "0%"
    cx: str = "50%"
    cy: str = "50%"
    r: str = "50%"

class FormatInfoResponse(BaseModel):
    formats: dict
    available_count: int
    total_count: int

class ExportResponse(BaseModel):
    format: str
    file_extension: str
    size_bytes: int
    export_time_ms: int
    warnings: List[str] = []

class BatchExportResponse(BaseModel):
    results: dict
    total_time_ms: int

class AnimationPresetsResponse(BaseModel):
    presets: dict
    methods: List[str]
    types: List[str]

class SVGStatsResponse(BaseModel):
    stats: dict


# =============================================================================
# Export Endpoints
# =============================================================================

@router.get("/formats", response_model=FormatInfoResponse)
async def get_export_formats():
    """Get all available export formats and their capabilities."""
    formats = ExportEngine.get_available_formats()
    available = sum(1 for f in formats.values() if f.get("available"))

    return FormatInfoResponse(
        formats=formats,
        available_count=available,
        total_count=len(formats),
    )


@router.post("/convert")
async def export_svg(
    svg_file: UploadFile = File(...),
    format: str = Form("pdf"),
    scale: float = Form(1.0),
    dpi: int = Form(300),
    width: Optional[int] = Form(None),
    height: Optional[int] = Form(None),
    background_color: Optional[str] = Form(None),
):
    """Convert SVG to the specified format."""
    if not svg_file.filename or not svg_file.filename.lower().endswith(('.svg', '.xml')):
        raise HTTPException(400, "Please upload an SVG file")

    svg_data = await svg_file.read()
    if len(svg_data) > 50 * 1024 * 1024:
        raise HTTPException(413, "SVG file too large (max 50MB)")

    try:
        export_format = ExportFormat(format.lower())
    except ValueError:
        raise HTTPException(400, f"Unsupported format: {format}. Available: {[f.value for f in ExportFormat]}")

    options = ExportOptions(
        format=export_format,
        scale=scale,
        dpi=dpi,
        width=width,
        height=height,
        background_color=background_color,
    )

    try:
        result = ExportEngine.export(svg_data, options)
    except RuntimeError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(500, f"Export failed: {str(e)}")

    # Return the file
    filename = svg_file.filename.rsplit(".", 1)[0] + result.file_extension

    return Response(
        content=result.data,
        media_type=result.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Time-Ms": str(result.export_time_ms),
            "X-Export-Size-Bytes": str(result.size_bytes),
        },
    )


@router.post("/batch", response_model=BatchExportResponse)
async def batch_export(
    svg_file: UploadFile = File(...),
    formats: str = Form("pdf,eps,dxf"),
    scale: float = Form(1.0),
    dpi: int = Form(300),
):
    """Export SVG to multiple formats at once. Returns metadata (files via /convert)."""
    svg_data = await svg_file.read()
    start = time.time()

    format_list = [f.strip() for f in formats.split(",")]
    export_formats = []
    for f in format_list:
        try:
            export_formats.append(ExportFormat(f.lower()))
        except ValueError:
            raise HTTPException(400, f"Unsupported format: {f}")

    options = ExportOptions(scale=scale, dpi=dpi)
    results = ExportEngine.batch_export(svg_data, export_formats, options)

    response_results = {}
    for fmt, result in results.items():
        response_results[fmt] = {
            "success": result.size_bytes > 0,
            "size_bytes": result.size_bytes,
            "export_time_ms": result.export_time_ms,
            "file_extension": result.file_extension,
            "warnings": result.warnings,
        }

    return BatchExportResponse(
        results=response_results,
        total_time_ms=int((time.time() - start) * 1000),
    )


# =============================================================================
# Animation Endpoints
# =============================================================================

@router.get("/animation/presets", response_model=AnimationPresetsResponse)
async def get_animation_presets():
    """Get available animation presets."""
    return AnimationPresetsResponse(
        presets=SVGAnimationEngine.get_presets(),
        methods=[m.value for m in AnimationMethod],
        types=[t.value for t in AnimationType],
    )


@router.post("/animation/apply")
async def apply_animation(
    svg_file: UploadFile = File(...),
    preset: Optional[str] = Form(None),
    animation_type: Optional[str] = Form(None),
    method: str = Form("css"),
    duration: float = Form(2.0),
    delay: float = Form(0.0),
    stagger: float = Form(0.1),
    iteration_count: str = Form("1"),
):
    """Apply animation to an SVG file."""
    svg_data = await svg_file.read()

    config = None
    if not preset:
        anim_type = AnimationType(animation_type) if animation_type else AnimationType.DRAW_STROKE
        config = AnimationConfig(
            type=anim_type,
            method=AnimationMethod(method),
            duration=duration,
            delay=delay,
            stagger=stagger,
            iteration_count=iteration_count,
        )

    try:
        result = SVGAnimationEngine.animate(svg_data, config=config, preset=preset)
    except Exception as e:
        logger.error(f"Animation failed: {e}")
        raise HTTPException(500, f"Animation failed: {str(e)}")

    filename = svg_file.filename.rsplit(".", 1)[0] + "_animated.svg"

    return Response(
        content=result.svg_data,
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Animation-Method": result.method.value,
            "X-Element-Count": str(result.element_count),
            "X-Animation-Time-Ms": str(result.animation_time_ms),
        },
    )


@router.post("/animation/lottie")
async def export_lottie(
    svg_file: UploadFile = File(...),
    preset: Optional[str] = Form("fade_in"),
    duration: float = Form(2.0),
):
    """Export SVG as Lottie JSON for cross-platform animation."""
    svg_data = await svg_file.read()

    config = AnimationConfig(
        type=AnimationType.FADE_IN,
        method=AnimationMethod.LOTTIE,
        duration=duration,
    )

    result = SVGAnimationEngine.animate(svg_data, config=config, preset=preset)

    if not result.lottie_json:
        # Generate Lottie even if preset didn't use LOTTIE method
        from app.services.svg_animator import LottieExporter
        lottie = LottieExporter.export(svg_data, config)
    else:
        lottie = result.lottie_json

    import json
    lottie_bytes = json.dumps(lottie, indent=2).encode("utf-8")
    filename = svg_file.filename.rsplit(".", 1)[0] + ".json"

    return Response(
        content=lottie_bytes,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# =============================================================================
# Enhancement Endpoints
# =============================================================================

@router.post("/enhance/responsive")
async def enhance_svg(
    svg_file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    make_responsive: bool = Form(True),
    add_accessibility: bool = Form(True),
    minify: bool = Form(False),
):
    """Enhance SVG with responsiveness, accessibility, and metadata."""
    svg_data = await svg_file.read()

    try:
        enhanced = SVGEnhancer.enhance(
            svg_data,
            title=title,
            description=description,
            make_responsive=make_responsive,
            add_accessibility=add_accessibility,
            minify=minify,
        )
    except Exception as e:
        logger.error(f"Enhancement failed: {e}")
        raise HTTPException(500, f"Enhancement failed: {str(e)}")

    filename = svg_file.filename.rsplit(".", 1)[0] + "_enhanced.svg"

    return Response(
        content=enhanced,
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/enhance/stats", response_model=SVGStatsResponse)
async def get_svg_stats(svg_file: UploadFile = File(...)):
    """Analyze SVG and return detailed statistics."""
    svg_data = await svg_file.read()

    try:
        stats = SVGEnhancer.get_svg_stats(svg_data)
    except Exception as e:
        raise HTTPException(400, f"Invalid SVG: {str(e)}")

    return SVGStatsResponse(stats=stats)


@router.post("/enhance/gradients")
async def add_gradients(
    svg_file: UploadFile = File(...),
    gradient_id: str = Form("grad1"),
    gradient_type: str = Form("linear"),
    color_start: str = Form("#3b82f6"),
    color_end: str = Form("#8b5cf6"),
):
    """Add gradient definitions to an SVG."""
    svg_data = await svg_file.read()

    gradients = [{
        "id": gradient_id,
        "type": gradient_type,
        "stops": [
            {"offset": "0%", "color": color_start},
            {"offset": "100%", "color": color_end},
        ],
    }]

    try:
        result = SVGEnhancer.add_gradient_defs(svg_data, gradients)
    except Exception as e:
        raise HTTPException(500, f"Failed to add gradients: {str(e)}")

    return Response(
        content=result,
        media_type="image/svg+xml",
    )
