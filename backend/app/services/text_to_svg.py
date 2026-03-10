"""Text-to-SVG Generation Engine — Phase 13.

Converts text descriptions into SVG graphics using:
- Programmatic icon generation (keyword → geometric SVG)
- Text-to-path rendering (text → SVG <path>)
- AI prompt-to-SVG pipeline (via external API)
- SVG composition & layering
- Shape primitives library
"""

import hashlib
import logging
import math
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Types
# =============================================================================

class IconStyle(str, Enum):
    OUTLINED = "outlined"
    FILLED = "filled"
    DUOTONE = "duotone"
    FLAT = "flat"


class CompositionAlign(str, Enum):
    CENTER = "center"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


@dataclass
class TextToSVGConfig:
    """Configuration for text-to-SVG generation."""
    width: int = 512
    height: int = 512
    style: IconStyle = IconStyle.OUTLINED
    primary_color: str = "#3b82f6"
    secondary_color: str = "#8b5cf6"
    background: Optional[str] = None
    stroke_width: float = 2.0
    padding: float = 0.15  # fraction of dimension
    rounded: bool = True


@dataclass
class CompositionLayer:
    """A layer in SVG composition."""
    svg_content: str
    x: float = 0
    y: float = 0
    width: Optional[float] = None
    height: Optional[float] = None
    opacity: float = 1.0
    rotation: float = 0.0
    scale: float = 1.0
    blend_mode: str = "normal"
    name: str = "Layer"


# =============================================================================
# Icon Shape Library
# =============================================================================

class ShapeLibrary:
    """Library of basic geometric SVG shapes for icon composition."""

    @staticmethod
    def circle(cx: float, cy: float, r: float, **attrs) -> str:
        extra = " ".join(f'{k}="{v}"' for k, v in attrs.items())
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" {extra}/>'

    @staticmethod
    def rect(x: float, y: float, w: float, h: float, rx: float = 0, **attrs) -> str:
        extra = " ".join(f'{k}="{v}"' for k, v in attrs.items())
        return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" {extra}/>'

    @staticmethod
    def line(x1: float, y1: float, x2: float, y2: float, **attrs) -> str:
        extra = " ".join(f'{k}="{v}"' for k, v in attrs.items())
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" {extra}/>'

    @staticmethod
    def polygon(points: List[Tuple[float, float]], **attrs) -> str:
        pts = " ".join(f"{x},{y}" for x, y in points)
        extra = " ".join(f'{k}="{v}"' for k, v in attrs.items())
        return f'<polygon points="{pts}" {extra}/>'

    @staticmethod
    def star(cx: float, cy: float, outer_r: float, inner_r: float, points: int = 5, **attrs) -> str:
        pts = []
        for i in range(points * 2):
            angle = math.pi * i / points - math.pi / 2
            r = outer_r if i % 2 == 0 else inner_r
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        return ShapeLibrary.polygon(pts, **attrs)

    @staticmethod
    def arrow(x: float, y: float, size: float, direction: str = "right", **attrs) -> str:
        s = size
        if direction == "right":
            d = f"M {x},{y - s / 3} L {x + s * 0.7},{y - s / 3} L {x + s * 0.7},{y - s / 2} L {x + s},{y} L {x + s * 0.7},{y + s / 2} L {x + s * 0.7},{y + s / 3} L {x},{y + s / 3} Z"
        elif direction == "up":
            d = f"M {x - s / 3},{y} L {x - s / 3},{y - s * 0.7} L {x - s / 2},{y - s * 0.7} L {x},{y - s} L {x + s / 2},{y - s * 0.7} L {x + s / 3},{y - s * 0.7} L {x + s / 3},{y} Z"
        else:
            d = f"M {x},{y} L {x + s},{y} L {x + s / 2},{y - s} Z"
        extra = " ".join(f'{k}="{v}"' for k, v in attrs.items())
        return f'<path d="{d}" {extra}/>'

    @staticmethod
    def heart(cx: float, cy: float, size: float, **attrs) -> str:
        s = size
        d = (
            f"M {cx},{cy + s * 0.3} "
            f"C {cx},{cy - s * 0.3} {cx - s},{cy - s * 0.3} {cx - s},{cy + s * 0.1} "
            f"C {cx - s},{cy + s * 0.6} {cx},{cy + s} {cx},{cy + s} "
            f"C {cx},{cy + s} {cx + s},{cy + s * 0.6} {cx + s},{cy + s * 0.1} "
            f"C {cx + s},{cy - s * 0.3} {cx},{cy - s * 0.3} {cx},{cy + s * 0.3} Z"
        )
        extra = " ".join(f'{k}="{v}"' for k, v in attrs.items())
        return f'<path d="{d}" {extra}/>'

    @staticmethod
    def gear(cx: float, cy: float, radius: float, teeth: int = 8, **attrs) -> str:
        pts = []
        inner = radius * 0.65
        for i in range(teeth * 2):
            angle = math.pi * i / teeth
            r = radius if i % 2 == 0 else inner
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        return ShapeLibrary.polygon(pts, **attrs)

    @staticmethod
    def cloud(cx: float, cy: float, size: float, **attrs) -> str:
        s = size
        extra = " ".join(f'{k}="{v}"' for k, v in attrs.items())
        return (
            f'<g {extra}>'
            f'<circle cx="{cx - s * 0.3}" cy="{cy}" r="{s * 0.35}"/>'
            f'<circle cx="{cx + s * 0.3}" cy="{cy}" r="{s * 0.35}"/>'
            f'<circle cx="{cx}" cy="{cy - s * 0.2}" r="{s * 0.45}"/>'
            f'<rect x="{cx - s * 0.55}" y="{cy}" width="{s * 1.1}" height="{s * 0.35}" rx="{s * 0.05}"/>'
            f'</g>'
        )


# =============================================================================
# Keyword → Icon Mapper
# =============================================================================

class IconGenerator:
    """Generate simple SVG icons from keyword descriptions."""

    # Keyword → icon shape mapping
    KEYWORD_MAP = {
        # Technology
        "code": "code_brackets",
        "computer": "monitor",
        "phone": "smartphone",
        "email": "envelope",
        "settings": "gear",
        "search": "magnifier",
        "home": "house",
        "user": "person",
        "star": "star",
        "heart": "heart",
        "cloud": "cloud",
        "lock": "padlock",
        "sun": "sun",
        "moon": "crescent",
        "music": "note",
        "camera": "camera",
        "file": "document",
        "folder": "folder",
        "trash": "bin",
        "check": "checkmark",
        "close": "cross",
        "add": "plus",
        "arrow": "arrow",
        "link": "chain",
        "download": "download_arrow",
        "upload": "upload_arrow",
        "play": "play_triangle",
        "pause": "pause_bars",
        "warning": "alert_triangle",
        "info": "info_circle",
        "location": "pin",
        "clock": "clock_face",
        "calendar": "calendar_grid",
        "image": "picture",
        "video": "play_rect",
        "chart": "bar_chart",
        "database": "cylinder",
        "shield": "shield",
        "flag": "flag",
        "bookmark": "bookmark",
        "bell": "bell",
        "key": "key_shape",
        "power": "power_btn",
        "wifi": "wifi_waves",
        "battery": "battery",
        "message": "speech_bubble",
    }

    @classmethod
    def generate(cls, keyword: str, config: Optional[TextToSVGConfig] = None) -> str:
        """Generate an SVG icon from a keyword."""
        if config is None:
            config = TextToSVGConfig()

        keyword = keyword.lower().strip()

        # Find matching shape
        shape_key = cls.KEYWORD_MAP.get(keyword, None)
        if not shape_key:
            # Try partial match
            for kw, sk in cls.KEYWORD_MAP.items():
                if kw in keyword or keyword in kw:
                    shape_key = sk
                    break

        if not shape_key:
            shape_key = "default_circle"

        # Build the icon
        elements = cls._build_icon(shape_key, config)
        return cls._wrap_icon_svg(elements, config, keyword)

    @classmethod
    def _build_icon(cls, shape_key: str, cfg: TextToSVGConfig) -> str:
        """Build icon elements for a shape key."""
        w, h = cfg.width, cfg.height
        cx, cy = w / 2, h / 2
        pad = min(w, h) * cfg.padding
        size = min(w, h) / 2 - pad
        sw = cfg.stroke_width
        c1 = cfg.primary_color
        c2 = cfg.secondary_color
        fill = c1 if cfg.style == IconStyle.FILLED else "none"
        stroke = c1 if cfg.style != IconStyle.FILLED else "none"
        rx = size * 0.1 if cfg.rounded else 0

        builders = {
            "star": lambda: ShapeLibrary.star(cx, cy, size, size * 0.45, fill=fill, stroke=stroke, **{"stroke-width": sw}),
            "heart": lambda: ShapeLibrary.heart(cx, cy - size * 0.2, size * 0.6, fill=fill, stroke=stroke, **{"stroke-width": sw}),
            "gear": lambda: ShapeLibrary.gear(cx, cy, size * 0.7, fill=fill, stroke=stroke, **{"stroke-width": sw}),
            "cloud": lambda: ShapeLibrary.cloud(cx, cy, size * 0.6, fill=c1, stroke="none"),
            "checkmark": lambda: f'<polyline points="{cx - size * 0.3},{cy} {cx - size * 0.05},{cy + size * 0.25} {cx + size * 0.35},{cy - size * 0.25}" fill="none" stroke="{c1}" stroke-width="{sw * 1.5}" stroke-linecap="round" stroke-linejoin="round"/>',
            "cross": lambda: (
                f'<line x1="{cx - size * 0.25}" y1="{cy - size * 0.25}" x2="{cx + size * 0.25}" y2="{cy + size * 0.25}" stroke="{c1}" stroke-width="{sw * 1.5}" stroke-linecap="round"/>'
                f'<line x1="{cx + size * 0.25}" y1="{cy - size * 0.25}" x2="{cx - size * 0.25}" y2="{cy + size * 0.25}" stroke="{c1}" stroke-width="{sw * 1.5}" stroke-linecap="round"/>'
            ),
            "plus": lambda: (
                f'<line x1="{cx}" y1="{cy - size * 0.3}" x2="{cx}" y2="{cy + size * 0.3}" stroke="{c1}" stroke-width="{sw * 1.5}" stroke-linecap="round"/>'
                f'<line x1="{cx - size * 0.3}" y1="{cy}" x2="{cx + size * 0.3}" y2="{cy}" stroke="{c1}" stroke-width="{sw * 1.5}" stroke-linecap="round"/>'
            ),
            "person": lambda: (
                f'<circle cx="{cx}" cy="{cy - size * 0.25}" r="{size * 0.2}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
                f'<path d="M {cx - size * 0.4},{cy + size * 0.5} Q {cx - size * 0.4},{cy + size * 0.05} {cx},{cy + size * 0.05} Q {cx + size * 0.4},{cy + size * 0.05} {cx + size * 0.4},{cy + size * 0.5}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
            ),
            "envelope": lambda: (
                f'<rect x="{cx - size * 0.45}" y="{cy - size * 0.25}" width="{size * 0.9}" height="{size * 0.55}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
                f'<polyline points="{cx - size * 0.45},{cy - size * 0.25} {cx},{cy + size * 0.05} {cx + size * 0.45},{cy - size * 0.25}" fill="none" stroke="{stroke or c1}" stroke-width="{sw}"/>'
            ),
            "house": lambda: (
                f'<path d="M {cx},{cy - size * 0.4} L {cx + size * 0.4},{cy} L {cx + size * 0.3},{cy} L {cx + size * 0.3},{cy + size * 0.35} L {cx - size * 0.3},{cy + size * 0.35} L {cx - size * 0.3},{cy} L {cx - size * 0.4},{cy} Z" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>'
                f'<rect x="{cx - size * 0.08}" y="{cy + size * 0.1}" width="{size * 0.16}" height="{size * 0.25}" fill="{c2 if cfg.style == IconStyle.DUOTONE else fill}" stroke="{stroke}" stroke-width="{sw * 0.5}"/>'
            ),
            "monitor": lambda: (
                f'<rect x="{cx - size * 0.4}" y="{cy - size * 0.35}" width="{size * 0.8}" height="{size * 0.55}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
                f'<line x1="{cx}" y1="{cy + size * 0.2}" x2="{cx}" y2="{cy + size * 0.4}" stroke="{stroke or c1}" stroke-width="{sw}"/>'
                f'<line x1="{cx - size * 0.2}" y1="{cy + size * 0.4}" x2="{cx + size * 0.2}" y2="{cy + size * 0.4}" stroke="{stroke or c1}" stroke-width="{sw}" stroke-linecap="round"/>'
            ),
            "magnifier": lambda: (
                f'<circle cx="{cx - size * 0.08}" cy="{cy - size * 0.08}" r="{size * 0.28}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
                f'<line x1="{cx + size * 0.11}" y1="{cy + size * 0.11}" x2="{cx + size * 0.38}" y2="{cy + size * 0.38}" stroke="{stroke or c1}" stroke-width="{sw * 1.5}" stroke-linecap="round"/>'
            ),
            "padlock": lambda: (
                f'<rect x="{cx - size * 0.25}" y="{cy - size * 0.05}" width="{size * 0.5}" height="{size * 0.45}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
                f'<path d="M {cx - size * 0.15},{cy - size * 0.05} L {cx - size * 0.15},{cy - size * 0.2} A {size * 0.15} {size * 0.15} 0 0 1 {cx + size * 0.15},{cy - size * 0.2} L {cx + size * 0.15},{cy - size * 0.05}" fill="none" stroke="{stroke or c1}" stroke-width="{sw}"/>'
            ),
            "alert_triangle": lambda: (
                f'<path d="M {cx},{cy - size * 0.35} L {cx + size * 0.4},{cy + size * 0.3} L {cx - size * 0.4},{cy + size * 0.3} Z" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>'
                f'<line x1="{cx}" y1="{cy - size * 0.1}" x2="{cx}" y2="{cy + size * 0.08}" stroke="{stroke or c1}" stroke-width="{sw * 1.2}" stroke-linecap="round"/>'
                f'<circle cx="{cx}" cy="{cy + size * 0.2}" r="{sw}" fill="{stroke or c1}"/>'
            ),
            "shield": lambda: (
                f'<path d="M {cx},{cy - size * 0.4} L {cx + size * 0.35},{cy - size * 0.2} L {cx + size * 0.35},{cy + size * 0.1} Q {cx + size * 0.35},{cy + size * 0.45} {cx},{cy + size * 0.5} Q {cx - size * 0.35},{cy + size * 0.45} {cx - size * 0.35},{cy + size * 0.1} L {cx - size * 0.35},{cy - size * 0.2} Z" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
            ),
            "sun": lambda: cls._build_sun(cx, cy, size, c1, sw, cfg.style),
            "pin": lambda: (
                f'<path d="M {cx},{cy + size * 0.45} L {cx - size * 0.22},{cy - size * 0.05} A {size * 0.3} {size * 0.3} 0 1 1 {cx + size * 0.22},{cy - size * 0.05} Z" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
                f'<circle cx="{cx}" cy="{cy - size * 0.18}" r="{size * 0.1}" fill="{cfg.background or "white"}" stroke="{stroke}" stroke-width="{sw * 0.5}"/>'
            ),
            "speech_bubble": lambda: (
                f'<path d="M {cx - size * 0.4},{cy - size * 0.3} L {cx + size * 0.4},{cy - size * 0.3} Q {cx + size * 0.45},{cy - size * 0.3} {cx + size * 0.45},{cy - size * 0.2} L {cx + size * 0.45},{cy + size * 0.1} Q {cx + size * 0.45},{cy + size * 0.2} {cx + size * 0.35},{cy + size * 0.2} L {cx - size * 0.1},{cy + size * 0.2} L {cx - size * 0.25},{cy + size * 0.4} L {cx - size * 0.2},{cy + size * 0.2} L {cx - size * 0.35},{cy + size * 0.2} Q {cx - size * 0.45},{cy + size * 0.2} {cx - size * 0.45},{cy + size * 0.1} L {cx - size * 0.45},{cy - size * 0.2} Q {cx - size * 0.45},{cy - size * 0.3} {cx - size * 0.4},{cy - size * 0.3} Z" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
            ),
            "bar_chart": lambda: (
                f'<rect x="{cx - size * 0.35}" y="{cy + size * 0.05}" width="{size * 0.15}" height="{size * 0.35}" rx="{rx * 0.3}" fill="{c1}"/>'
                f'<rect x="{cx - size * 0.075}" y="{cy - size * 0.2}" width="{size * 0.15}" height="{size * 0.6}" rx="{rx * 0.3}" fill="{c2}"/>'
                f'<rect x="{cx + size * 0.2}" y="{cy - size * 0.35}" width="{size * 0.15}" height="{size * 0.75}" rx="{rx * 0.3}" fill="{c1}"/>'
            ),
        }

        builder = builders.get(shape_key)
        if builder:
            return builder()

        # Default: circle with letter
        letter = keyword[0].upper() if keyword else "?"
        return (
            f'<circle cx="{cx}" cy="{cy}" r="{size * 0.45}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
            f'<text x="{cx}" y="{cy + size * 0.12}" text-anchor="middle" font-size="{size * 0.5}" '
            f'font-family="Arial, sans-serif" font-weight="bold" fill="{c1}">{letter}</text>'
        )

    @staticmethod
    def _build_sun(cx, cy, size, color, sw, style):
        fill = color if style == IconStyle.FILLED else "none"
        stroke = color
        elements = [f'<circle cx="{cx}" cy="{cy}" r="{size * 0.2}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>']
        for i in range(8):
            angle = math.pi * i / 4
            x1 = cx + size * 0.3 * math.cos(angle)
            y1 = cy + size * 0.3 * math.sin(angle)
            x2 = cx + size * 0.45 * math.cos(angle)
            y2 = cy + size * 0.45 * math.sin(angle)
            elements.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round"/>')
        return "\n".join(elements)

    @classmethod
    def get_available_icons(cls) -> List[str]:
        """Get all available icon keywords."""
        return sorted(cls.KEYWORD_MAP.keys())

    @staticmethod
    def _wrap_icon_svg(elements: str, cfg: TextToSVGConfig, keyword: str) -> str:
        bg = f'<rect width="{cfg.width}" height="{cfg.height}" fill="{cfg.background}" rx="24"/>' if cfg.background else ""

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{cfg.width}" height="{cfg.height}" 
     viewBox="0 0 {cfg.width} {cfg.height}" role="img">
    <title>{keyword} icon</title>
    <desc>Generated SVG icon for "{keyword}" by Raster to SVG</desc>
    {bg}
    {elements}
</svg>'''


# =============================================================================
# SVG Compositor
# =============================================================================

class SVGCompositor:
    """Compose multiple SVG layers into a single SVG."""

    @staticmethod
    def compose(
        layers: List[CompositionLayer],
        width: int = 800,
        height: int = 600,
        background: Optional[str] = None,
    ) -> str:
        """Compose multiple SVG layers into one."""
        elements = []

        if background:
            elements.append(f'<rect width="{width}" height="{height}" fill="{background}"/>')

        for i, layer in enumerate(layers):
            transform_parts = []
            if layer.x != 0 or layer.y != 0:
                transform_parts.append(f"translate({layer.x}, {layer.y})")
            if layer.scale != 1.0:
                transform_parts.append(f"scale({layer.scale})")
            if layer.rotation != 0:
                lw = layer.width or width
                lh = layer.height or height
                transform_parts.append(f"rotate({layer.rotation}, {lw / 2}, {lh / 2})")

            transform = f' transform="{"  ".join(transform_parts)}"' if transform_parts else ""
            opacity = f' opacity="{layer.opacity}"' if layer.opacity < 1.0 else ""
            blend = f' style="mix-blend-mode: {layer.blend_mode};"' if layer.blend_mode != "normal" else ""

            # Extract inner SVG content (strip outer <svg> tags)
            inner = SVGCompositor._extract_inner(layer.svg_content)

            elements.append(
                f'<g id="layer-{i}" data-name="{layer.name}"{transform}{opacity}{blend}>'
                f'{inner}'
                f'</g>'
            )

        content = "\n".join(elements)

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"
     viewBox="0 0 {width} {height}" role="img">
    <title>Composed SVG</title>
    <desc>Multi-layer SVG composition</desc>
    {content}
</svg>'''

    @staticmethod
    def _extract_inner(svg_content: str) -> str:
        """Extract inner content from an SVG string."""
        # Remove XML declaration
        svg_content = re.sub(r'<\?xml[^?]+\?>', '', svg_content)
        # Remove outer <svg> tags
        svg_content = re.sub(r'<svg[^>]*>', '', svg_content, count=1)
        svg_content = re.sub(r'</svg>\s*$', '', svg_content)
        return svg_content.strip()


# =============================================================================
# Text-to-Path Renderer
# =============================================================================

class TextRenderer:
    """Render text as SVG with styling."""

    @staticmethod
    def render_text(
        text: str,
        font_size: float = 48,
        font_family: str = "Arial, Helvetica, sans-serif",
        font_weight: str = "bold",
        color: str = "#ffffff",
        background: Optional[str] = "#0f172a",
        width: Optional[int] = None,
        height: Optional[int] = None,
        text_anchor: str = "middle",
        letter_spacing: float = 0,
        line_height: float = 1.4,
    ) -> str:
        """Render text as SVG."""
        lines = text.split("\n")

        # Auto-size
        if width is None:
            width = max(int(len(line) * font_size * 0.6) for line in lines) + int(font_size * 2)
        if height is None:
            height = int(len(lines) * font_size * line_height + font_size * 2)

        cx = width / 2
        start_y = (height - len(lines) * font_size * line_height) / 2 + font_size

        elements = []
        if background:
            elements.append(f'<rect width="{width}" height="{height}" fill="{background}" rx="12"/>')

        for i, line in enumerate(lines):
            y = start_y + i * font_size * line_height
            ls = f' letter-spacing="{letter_spacing}"' if letter_spacing else ""
            elements.append(
                f'<text x="{cx}" y="{y}" text-anchor="{text_anchor}" '
                f'font-family="{font_family}" font-size="{font_size}" '
                f'font-weight="{font_weight}" fill="{color}"{ls}>'
                f'{_escape_xml(line)}</text>'
            )

        content = "\n".join(elements)

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"
     viewBox="0 0 {width} {height}" role="img">
    <title>{_escape_xml(text[:50])}</title>
    {content}
</svg>'''

    @staticmethod
    def render_styled_heading(
        text: str,
        style: str = "gradient",
        font_size: float = 72,
        colors: Optional[List[str]] = None,
        width: int = 800,
        height: int = 200,
    ) -> str:
        """Render a styled heading with effects."""
        if colors is None:
            colors = ["#3b82f6", "#8b5cf6", "#ec4899"]

        cx = width / 2
        cy = height / 2 + font_size * 0.3

        defs = ""
        fill = colors[0]

        if style == "gradient":
            stops = []
            for i, color in enumerate(colors):
                pct = int(i / max(len(colors) - 1, 1) * 100)
                stops.append(f'<stop offset="{pct}%" stop-color="{color}"/>')
            defs = f'''<defs>
                <linearGradient id="heading-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                    {"".join(stops)}
                </linearGradient>
            </defs>'''
            fill = "url(#heading-grad)"

        elif style == "outline":
            return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
    <text x="{cx}" y="{cy}" text-anchor="middle" font-family="Arial, sans-serif" 
          font-size="{font_size}" font-weight="900" fill="none" 
          stroke="{colors[0]}" stroke-width="2">{_escape_xml(text)}</text>
</svg>'''

        elif style == "shadow":
            shadow_offset = font_size * 0.04
            return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
    <text x="{cx + shadow_offset}" y="{cy + shadow_offset}" text-anchor="middle" 
          font-family="Arial, sans-serif" font-size="{font_size}" font-weight="900" 
          fill="{colors[-1]}" opacity="0.3">{_escape_xml(text)}</text>
    <text x="{cx}" y="{cy}" text-anchor="middle" font-family="Arial, sans-serif" 
          font-size="{font_size}" font-weight="900" fill="{colors[0]}">{_escape_xml(text)}</text>
</svg>'''

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
    {defs}
    <text x="{cx}" y="{cy}" text-anchor="middle" font-family="Arial, sans-serif" 
          font-size="{font_size}" font-weight="900" fill="{fill}">{_escape_xml(text)}</text>
</svg>'''


def _escape_xml(text: str) -> str:
    """Escape XML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
