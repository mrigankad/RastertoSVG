"""Generative Features API routes — Phase 13.

Endpoints:
— Icons
- GET  /generate/icons               — Available icon keywords
- POST /generate/icon                — Generate icon from keyword

— Patterns
- GET  /generate/patterns            — Available pattern types
- POST /generate/pattern             — Generate SVG pattern

— Text
- POST /generate/text                — Render text as SVG
- POST /generate/heading             — Styled heading (gradient/outline/shadow)

— Palette
- GET  /generate/palette/schemes     — Available color schemes
- POST /generate/palette             — Generate color palette

— Composition
- POST /generate/compose             — Compose multiple SVG layers
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.services.text_to_svg import (
    IconGenerator,
    TextToSVGConfig,
    IconStyle,
    TextRenderer,
    SVGCompositor,
    CompositionLayer,
)
from app.services.pattern_generator import (
    PatternGenerator,
    PatternConfig,
    PatternType,
    PaletteGenerator,
    PaletteConfig,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["Generative Features (Phase 13)"])


# =============================================================================
# Request / Response Models
# =============================================================================

class IconRequest(BaseModel):
    keyword: str = Field(description="Icon keyword: heart, star, home, user, etc.")
    width: int = Field(default=512, ge=16, le=4096)
    height: int = Field(default=512, ge=16, le=4096)
    style: str = Field(default="outlined", description="outlined, filled, duotone, flat")
    primary_color: str = "#3b82f6"
    secondary_color: str = "#8b5cf6"
    background: Optional[str] = None
    stroke_width: float = Field(default=2.0, ge=0.5, le=20.0)
    padding: float = Field(default=0.15, ge=0.0, le=0.4)

class PatternRequest(BaseModel):
    pattern_type: str = Field(default="dots", description="Pattern type: dots, stripes, hexagons, waves, etc.")
    width: int = Field(default=800, ge=50, le=4096)
    height: int = Field(default=600, ge=50, le=4096)
    colors: List[str] = Field(default=["#3b82f6", "#8b5cf6", "#ec4899"])
    background: str = "#0f172a"
    cell_size: float = Field(default=40.0, ge=5.0, le=200.0)
    stroke_width: float = Field(default=2.0, ge=0.5, le=10.0)
    opacity: float = Field(default=1.0, ge=0.1, le=1.0)
    rotation: float = Field(default=0.0, ge=-180, le=180)
    seed: int = Field(default=42)
    density: float = Field(default=1.0, ge=0.1, le=3.0)
    animate: bool = False

class TextRequest(BaseModel):
    text: str = Field(max_length=5000)
    font_size: float = Field(default=48, ge=8, le=500)
    font_family: str = "Arial, Helvetica, sans-serif"
    font_weight: str = "bold"
    color: str = "#ffffff"
    background: Optional[str] = "#0f172a"
    width: Optional[int] = Field(default=None, ge=50, le=4096)
    height: Optional[int] = Field(default=None, ge=50, le=4096)
    letter_spacing: float = Field(default=0, ge=-10, le=50)
    line_height: float = Field(default=1.4, ge=0.8, le=3.0)

class HeadingRequest(BaseModel):
    text: str = Field(max_length=200)
    style: str = Field(default="gradient", description="gradient, outline, shadow")
    font_size: float = Field(default=72, ge=12, le=500)
    colors: List[str] = Field(default=["#3b82f6", "#8b5cf6", "#ec4899"])
    width: int = Field(default=800, ge=100, le=4096)
    height: int = Field(default=200, ge=50, le=2048)

class PaletteRequest(BaseModel):
    base_hue: float = Field(default=0.6, ge=0.0, le=1.0)
    scheme: str = Field(default="analogous", description="analogous, complementary, triadic, split, monochrome")
    count: int = Field(default=5, ge=2, le=20)
    saturation: float = Field(default=0.7, ge=0.0, le=1.0)
    lightness: float = Field(default=0.55, ge=0.0, le=1.0)

class PaletteResponse(BaseModel):
    colors: List[str]
    scheme: str
    count: int

class ComposeLayerInput(BaseModel):
    svg_content: str
    x: float = 0
    y: float = 0
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    rotation: float = Field(default=0.0, ge=-360, le=360)
    scale: float = Field(default=1.0, ge=0.01, le=10.0)
    blend_mode: str = "normal"
    name: str = "Layer"

class ComposeRequest(BaseModel):
    layers: List[ComposeLayerInput]
    width: int = Field(default=800, ge=50, le=4096)
    height: int = Field(default=600, ge=50, le=4096)
    background: Optional[str] = None


# =============================================================================
# Icon Endpoints
# =============================================================================

@router.get("/icons")
async def get_icon_keywords():
    """Get all available icon keywords."""
    return {
        "keywords": IconGenerator.get_available_icons(),
        "styles": [s.value for s in IconStyle],
        "total": len(IconGenerator.get_available_icons()),
    }


@router.post("/icon")
async def generate_icon(request: IconRequest):
    """Generate an SVG icon from a keyword."""
    try:
        icon_style = IconStyle(request.style)
    except ValueError:
        icon_style = IconStyle.OUTLINED

    config = TextToSVGConfig(
        width=request.width,
        height=request.height,
        style=icon_style,
        primary_color=request.primary_color,
        secondary_color=request.secondary_color,
        background=request.background,
        stroke_width=request.stroke_width,
        padding=request.padding,
    )

    svg = IconGenerator.generate(request.keyword, config)

    return Response(
        content=svg.encode("utf-8"),
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": f'inline; filename="{request.keyword}_icon.svg"',
            "X-Icon-Keyword": request.keyword,
            "X-Icon-Style": request.style,
        },
    )


# =============================================================================
# Pattern Endpoints
# =============================================================================

@router.get("/patterns")
async def get_pattern_types():
    """Get all available pattern types."""
    return {
        "patterns": PatternGenerator.get_pattern_types(),
        "total": len(PatternType),
    }


@router.post("/pattern")
async def generate_pattern(request: PatternRequest):
    """Generate a procedural SVG pattern."""
    try:
        pt = PatternType(request.pattern_type)
    except ValueError:
        raise HTTPException(400, f"Invalid pattern type: {request.pattern_type}. Available: {[p.value for p in PatternType]}")

    config = PatternConfig(
        pattern_type=pt,
        width=request.width,
        height=request.height,
        colors=request.colors,
        background=request.background,
        cell_size=request.cell_size,
        stroke_width=request.stroke_width,
        opacity=request.opacity,
        rotation=request.rotation,
        seed=request.seed,
        density=request.density,
        animate=request.animate,
    )

    svg = PatternGenerator.generate(config)

    return Response(
        content=svg.encode("utf-8"),
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": f'inline; filename="{request.pattern_type}_pattern.svg"',
            "X-Pattern-Type": request.pattern_type,
        },
    )


# =============================================================================
# Text Endpoints
# =============================================================================

@router.post("/text")
async def render_text(request: TextRequest):
    """Render text as SVG."""
    if not request.text.strip():
        raise HTTPException(400, "Text cannot be empty")

    svg = TextRenderer.render_text(
        text=request.text,
        font_size=request.font_size,
        font_family=request.font_family,
        font_weight=request.font_weight,
        color=request.color,
        background=request.background,
        width=request.width,
        height=request.height,
        letter_spacing=request.letter_spacing,
        line_height=request.line_height,
    )

    return Response(
        content=svg.encode("utf-8"),
        media_type="image/svg+xml",
        headers={"Content-Disposition": 'inline; filename="text.svg"'},
    )


@router.post("/heading")
async def render_heading(request: HeadingRequest):
    """Render a styled heading as SVG."""
    if not request.text.strip():
        raise HTTPException(400, "Text cannot be empty")

    svg = TextRenderer.render_styled_heading(
        text=request.text,
        style=request.style,
        font_size=request.font_size,
        colors=request.colors,
        width=request.width,
        height=request.height,
    )

    return Response(
        content=svg.encode("utf-8"),
        media_type="image/svg+xml",
        headers={"Content-Disposition": 'inline; filename="heading.svg"'},
    )


# =============================================================================
# Palette Endpoints
# =============================================================================

@router.get("/palette/schemes")
async def get_palette_schemes():
    """Get available color palette schemes."""
    return {
        "schemes": PaletteGenerator.get_schemes(),
        "total": len(PaletteGenerator.get_schemes()),
    }


@router.post("/palette", response_model=PaletteResponse)
async def generate_palette(request: PaletteRequest):
    """Generate a harmonious color palette."""
    if request.scheme not in PaletteGenerator.get_schemes():
        raise HTTPException(400, f"Invalid scheme: {request.scheme}. Available: {PaletteGenerator.get_schemes()}")

    config = PaletteConfig(
        base_hue=request.base_hue,
        scheme=request.scheme,
        count=request.count,
        saturation=request.saturation,
        lightness=request.lightness,
    )

    colors = PaletteGenerator.generate(config)

    return PaletteResponse(
        colors=colors,
        scheme=request.scheme,
        count=len(colors),
    )


# =============================================================================
# Composition Endpoint
# =============================================================================

@router.post("/compose")
async def compose_svg(request: ComposeRequest):
    """Compose multiple SVG layers into a single SVG."""
    if not request.layers:
        raise HTTPException(400, "At least one layer is required")
    if len(request.layers) > 20:
        raise HTTPException(400, "Maximum 20 layers allowed")

    layers = [
        CompositionLayer(
            svg_content=layer.svg_content,
            x=layer.x,
            y=layer.y,
            opacity=layer.opacity,
            rotation=layer.rotation,
            scale=layer.scale,
            blend_mode=layer.blend_mode,
            name=layer.name,
        )
        for layer in request.layers
    ]

    svg = SVGCompositor.compose(
        layers=layers,
        width=request.width,
        height=request.height,
        background=request.background,
    )

    return Response(
        content=svg.encode("utf-8"),
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": 'inline; filename="composed.svg"',
            "X-Layer-Count": str(len(layers)),
        },
    )
