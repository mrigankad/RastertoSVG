"""Procedural SVG Pattern Generator — Phase 13.

Generates SVG patterns programmatically:
- Geometric patterns (stripes, dots, chevrons, hexagons, waves, diamonds)
- Noise-based organic textures (Perlin-style)
- Gradient mesh backgrounds
- Repeating tile patterns
- Color palette generation
"""

import math
import random
import colorsys
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums & Config
# =============================================================================


class PatternType(str, Enum):
    STRIPES = "stripes"
    DOTS = "dots"
    CHEVRONS = "chevrons"
    HEXAGONS = "hexagons"
    WAVES = "waves"
    DIAMONDS = "diamonds"
    GRID = "grid"
    TRIANGLES = "triangles"
    CIRCLES = "circles"
    CROSSHATCH = "crosshatch"
    NOISE = "noise"
    GRADIENT_MESH = "gradient_mesh"


@dataclass
class PatternConfig:
    """Configuration for pattern generation."""

    pattern_type: PatternType = PatternType.DOTS
    width: int = 800
    height: int = 600
    colors: List[str] = field(default_factory=lambda: ["#3b82f6", "#8b5cf6", "#ec4899"])
    background: str = "#0f172a"
    cell_size: float = 40.0
    stroke_width: float = 2.0
    opacity: float = 1.0
    rotation: float = 0.0
    seed: int = 42
    density: float = 1.0  # 0.1–2.0
    animate: bool = False


@dataclass
class PaletteConfig:
    """Color palette generation config."""

    base_hue: float = 0.6  # 0–1
    scheme: str = "analogous"  # analogous, complementary, triadic, split, monochrome
    count: int = 5
    saturation: float = 0.7
    lightness: float = 0.55


# =============================================================================
# Color Palette Generator
# =============================================================================


class PaletteGenerator:
    """Generate harmonious color palettes."""

    @staticmethod
    def generate(config: PaletteConfig) -> List[str]:
        """Generate a color palette based on color theory."""
        h = config.base_hue
        s = config.saturation
        l = config.lightness
        n = config.count

        hues = []

        if config.scheme == "analogous":
            spread = 0.08
            hues = [(h + i * spread - (n // 2) * spread) % 1.0 for i in range(n)]

        elif config.scheme == "complementary":
            hues = [h]
            comp = (h + 0.5) % 1.0
            for i in range(n - 1):
                hues.append((comp + (i - (n - 2) / 2) * 0.03) % 1.0)

        elif config.scheme == "triadic":
            base_hues = [h, (h + 1 / 3) % 1.0, (h + 2 / 3) % 1.0]
            while len(hues) < n:
                for bh in base_hues:
                    if len(hues) >= n:
                        break
                    hues.append(bh)

        elif config.scheme == "split":
            hues = [h, (h + 5 / 12) % 1.0, (h + 7 / 12) % 1.0]
            while len(hues) < n:
                hues.append((h + random.uniform(-0.05, 0.05)) % 1.0)

        elif config.scheme == "monochrome":
            hues = [h] * n
            return [
                PaletteGenerator._hsl_to_hex(
                    h, s * (0.3 + 0.7 * i / max(n - 1, 1)), 0.2 + 0.6 * i / max(n - 1, 1)
                )
                for i in range(n)
            ]

        else:
            hues = [(h + i / n) % 1.0 for i in range(n)]

        return [
            PaletteGenerator._hsl_to_hex(
                hue,
                s * (0.8 + 0.4 * random.random()),
                l * (0.8 + 0.4 * random.random()),
            )
            for hue in hues
        ]

    @staticmethod
    def _hsl_to_hex(h: float, s: float, l: float) -> str:
        s = max(0, min(1, s))
        l = max(0, min(1, l))
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

    @staticmethod
    def get_schemes() -> List[str]:
        return ["analogous", "complementary", "triadic", "split", "monochrome"]


# =============================================================================
# SVG Pattern Generator
# =============================================================================


class PatternGenerator:
    """Generate SVG patterns procedurally."""

    @classmethod
    def generate(cls, config: PatternConfig) -> str:
        """Generate SVG pattern based on config."""
        random.seed(config.seed)

        generators = {
            PatternType.STRIPES: cls._gen_stripes,
            PatternType.DOTS: cls._gen_dots,
            PatternType.CHEVRONS: cls._gen_chevrons,
            PatternType.HEXAGONS: cls._gen_hexagons,
            PatternType.WAVES: cls._gen_waves,
            PatternType.DIAMONDS: cls._gen_diamonds,
            PatternType.GRID: cls._gen_grid,
            PatternType.TRIANGLES: cls._gen_triangles,
            PatternType.CIRCLES: cls._gen_circles,
            PatternType.CROSSHATCH: cls._gen_crosshatch,
            PatternType.NOISE: cls._gen_noise,
            PatternType.GRADIENT_MESH: cls._gen_gradient_mesh,
        }

        gen_func = generators.get(config.pattern_type, cls._gen_dots)
        elements = gen_func(config)

        svg = cls._wrap_svg(elements, config)
        return svg

    @classmethod
    def get_pattern_types(cls) -> List[Dict]:
        """Get available pattern types with descriptions."""
        return [
            {
                "type": "stripes",
                "name": "Stripes",
                "description": "Parallel diagonal or straight lines",
            },
            {"type": "dots", "name": "Polka Dots", "description": "Evenly spaced circular dots"},
            {"type": "chevrons", "name": "Chevrons", "description": "V-shaped zigzag pattern"},
            {"type": "hexagons", "name": "Hexagons", "description": "Honeycomb hexagonal grid"},
            {"type": "waves", "name": "Waves", "description": "Sinusoidal wave pattern"},
            {"type": "diamonds", "name": "Diamonds", "description": "Rotated square diamond grid"},
            {"type": "grid", "name": "Grid", "description": "Regular rectangular grid"},
            {
                "type": "triangles",
                "name": "Triangles",
                "description": "Tessellated triangle pattern",
            },
            {
                "type": "circles",
                "name": "Concentric Circles",
                "description": "Expanding concentric rings",
            },
            {"type": "crosshatch", "name": "Crosshatch", "description": "Crossed diagonal lines"},
            {"type": "noise", "name": "Noise", "description": "Organic noise-based texture"},
            {
                "type": "gradient_mesh",
                "name": "Gradient Mesh",
                "description": "Smooth gradient mesh background",
            },
        ]

    # =========================================================================
    # Pattern Generators
    # =========================================================================

    @staticmethod
    def _gen_stripes(cfg: PatternConfig) -> str:
        elements = []
        spacing = cfg.cell_size / cfg.density
        angle = cfg.rotation or 45

        for i in range(int((cfg.width + cfg.height) * 2 / spacing)):
            offset = i * spacing - cfg.height
            color = cfg.colors[i % len(cfg.colors)]
            elements.append(
                f'<line x1="{offset}" y1="0" x2="{offset + cfg.height}" y2="{cfg.height}" '
                f'stroke="{color}" stroke-width="{cfg.stroke_width}" opacity="{cfg.opacity}" '
                f'transform="rotate({angle} {cfg.width / 2} {cfg.height / 2})"/>'
            )
        return "\n".join(elements)

    @staticmethod
    def _gen_dots(cfg: PatternConfig) -> str:
        elements = []
        spacing = cfg.cell_size / cfg.density
        radius = cfg.cell_size * 0.2

        for row in range(int(cfg.height / spacing) + 2):
            for col in range(int(cfg.width / spacing) + 2):
                x = col * spacing + (spacing / 2 if row % 2 else 0)
                y = row * spacing
                color = cfg.colors[(row + col) % len(cfg.colors)]
                r = radius * (0.7 + 0.3 * random.random())
                elements.append(
                    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
                    f'fill="{color}" opacity="{cfg.opacity}"/>'
                )
        return "\n".join(elements)

    @staticmethod
    def _gen_chevrons(cfg: PatternConfig) -> str:
        elements = []
        spacing = cfg.cell_size / cfg.density
        h = spacing * 0.6

        for row in range(int(cfg.height / spacing) + 2):
            for col in range(int(cfg.width / spacing) + 2):
                x = col * spacing
                y = row * spacing
                color = cfg.colors[row % len(cfg.colors)]

                path = f"M {x},{y + h} L {x + spacing / 2},{y} L {x + spacing},{y + h}"
                elements.append(
                    f'<path d="{path}" fill="none" stroke="{color}" '
                    f'stroke-width="{cfg.stroke_width}" opacity="{cfg.opacity}"/>'
                )
        return "\n".join(elements)

    @staticmethod
    def _gen_hexagons(cfg: PatternConfig) -> str:
        elements = []
        size = cfg.cell_size / cfg.density
        w = size * 2
        h = size * math.sqrt(3)

        for row in range(int(cfg.height / h) + 2):
            for col in range(int(cfg.width / (w * 0.75)) + 2):
                cx = col * w * 0.75
                cy = row * h + (h / 2 if col % 2 else 0)
                color = cfg.colors[(row + col) % len(cfg.colors)]

                points = []
                for i in range(6):
                    angle = math.pi / 3 * i - math.pi / 6
                    px = cx + size * math.cos(angle)
                    py = cy + size * math.sin(angle)
                    points.append(f"{px:.1f},{py:.1f}")

                elements.append(
                    f'<polygon points="{" ".join(points)}" fill="none" '
                    f'stroke="{color}" stroke-width="{cfg.stroke_width}" opacity="{cfg.opacity}"/>'
                )
        return "\n".join(elements)

    @staticmethod
    def _gen_waves(cfg: PatternConfig) -> str:
        elements = []
        spacing = cfg.cell_size / cfg.density
        amp = spacing * 0.4

        for row in range(int(cfg.height / spacing) + 2):
            y_base = row * spacing
            color = cfg.colors[row % len(cfg.colors)]

            path_parts = [f"M 0,{y_base}"]
            for x in range(0, int(cfg.width) + 20, 10):
                y = y_base + amp * math.sin(x * 0.05 + row * 0.5)
                path_parts.append(f"L {x},{y:.1f}")

            elements.append(
                f'<path d="{" ".join(path_parts)}" fill="none" '
                f'stroke="{color}" stroke-width="{cfg.stroke_width}" opacity="{cfg.opacity}"/>'
            )
        return "\n".join(elements)

    @staticmethod
    def _gen_diamonds(cfg: PatternConfig) -> str:
        elements = []
        size = cfg.cell_size / cfg.density
        half = size / 2

        for row in range(int(cfg.height / size) + 2):
            for col in range(int(cfg.width / size) + 2):
                cx = col * size + (half if row % 2 else 0)
                cy = row * size
                color = cfg.colors[(row + col) % len(cfg.colors)]

                points = f"{cx},{cy - half} {cx + half},{cy} {cx},{cy + half} {cx - half},{cy}"
                elements.append(
                    f'<polygon points="{points}" fill="{color}" ' f'opacity="{cfg.opacity * 0.6}"/>'
                )
        return "\n".join(elements)

    @staticmethod
    def _gen_grid(cfg: PatternConfig) -> str:
        elements = []
        spacing = cfg.cell_size / cfg.density
        color = cfg.colors[0] if cfg.colors else "#666"

        for x in range(0, int(cfg.width) + 1, int(spacing)):
            elements.append(
                f'<line x1="{x}" y1="0" x2="{x}" y2="{cfg.height}" '
                f'stroke="{color}" stroke-width="{cfg.stroke_width * 0.5}" opacity="{cfg.opacity * 0.5}"/>'
            )
        for y in range(0, int(cfg.height) + 1, int(spacing)):
            elements.append(
                f'<line x1="0" y1="{y}" x2="{cfg.width}" y2="{y}" '
                f'stroke="{color}" stroke-width="{cfg.stroke_width * 0.5}" opacity="{cfg.opacity * 0.5}"/>'
            )
        return "\n".join(elements)

    @staticmethod
    def _gen_triangles(cfg: PatternConfig) -> str:
        elements = []
        size = cfg.cell_size / cfg.density
        h = size * math.sqrt(3) / 2

        for row in range(int(cfg.height / h) + 2):
            for col in range(int(cfg.width / size) + 2):
                x = col * size + (size / 2 if row % 2 else 0)
                y = row * h
                color = cfg.colors[(row + col) % len(cfg.colors)]

                # Upward triangle
                p1 = f"{x},{y}"
                p2 = f"{x + size / 2},{y + h}"
                p3 = f"{x - size / 2},{y + h}"

                elements.append(
                    f'<polygon points="{p1} {p2} {p3}" fill="{color}" '
                    f'opacity="{cfg.opacity * 0.5}"/>'
                )
        return "\n".join(elements)

    @staticmethod
    def _gen_circles(cfg: PatternConfig) -> str:
        elements = []
        cx, cy = cfg.width / 2, cfg.height / 2
        max_r = max(cfg.width, cfg.height) * 0.8
        spacing = cfg.cell_size / cfg.density

        r = spacing
        i = 0
        while r < max_r:
            color = cfg.colors[i % len(cfg.colors)]
            elements.append(
                f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" '
                f'fill="none" stroke="{color}" stroke-width="{cfg.stroke_width}" '
                f'opacity="{cfg.opacity}"/>'
            )
            r += spacing
            i += 1
        return "\n".join(elements)

    @staticmethod
    def _gen_crosshatch(cfg: PatternConfig) -> str:
        elements = []
        spacing = cfg.cell_size / cfg.density
        color1 = cfg.colors[0] if cfg.colors else "#666"
        color2 = cfg.colors[1] if len(cfg.colors) > 1 else color1

        for i in range(int((cfg.width + cfg.height) * 2 / spacing)):
            offset = i * spacing - cfg.height
            elements.append(
                f'<line x1="{offset}" y1="0" x2="{offset + cfg.height}" y2="{cfg.height}" '
                f'stroke="{color1}" stroke-width="{cfg.stroke_width * 0.5}" opacity="{cfg.opacity * 0.5}"/>'
            )
            elements.append(
                f'<line x1="{cfg.width - offset}" y1="0" x2="{cfg.width - offset - cfg.height}" y2="{cfg.height}" '
                f'stroke="{color2}" stroke-width="{cfg.stroke_width * 0.5}" opacity="{cfg.opacity * 0.5}"/>'
            )
        return "\n".join(elements)

    @staticmethod
    def _gen_noise(cfg: PatternConfig) -> str:
        elements = []
        cell = max(4, int(cfg.cell_size / (cfg.density * 2)))

        for y in range(0, cfg.height, cell):
            for x in range(0, cfg.width, cell):
                val = random.random()
                color = cfg.colors[int(val * len(cfg.colors)) % len(cfg.colors)]
                opacity = 0.1 + val * cfg.opacity * 0.7

                elements.append(
                    f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
                    f'fill="{color}" opacity="{opacity:.2f}"/>'
                )
        return "\n".join(elements)

    @staticmethod
    def _gen_gradient_mesh(cfg: PatternConfig) -> str:
        elements = []
        defs = []

        # Create gradient definitions
        for i, color in enumerate(cfg.colors):
            cx = random.randint(0, cfg.width)
            cy = random.randint(0, cfg.height)
            r = max(cfg.width, cfg.height) * (0.4 + 0.3 * random.random())

            defs.append(
                f"""<radialGradient id="mesh-{i}" cx="{cx}" cy="{cy}" r="{r}" 
                gradientUnits="userSpaceOnUse">
                <stop offset="0%" stop-color="{color}" stop-opacity="0.8"/>
                <stop offset="100%" stop-color="{color}" stop-opacity="0"/>
            </radialGradient>"""
            )

            elements.append(
                f'<rect x="0" y="0" width="{cfg.width}" height="{cfg.height}" '
                f'fill="url(#mesh-{i})"/>'
            )

        defs_str = "\n".join(defs)
        elements_str = "\n".join(elements)
        return f"<defs>{defs_str}</defs>\n{elements_str}"

    # =========================================================================
    # SVG Wrapper
    # =========================================================================

    @staticmethod
    def _wrap_svg(content: str, cfg: PatternConfig) -> str:
        anim_css = ""
        if cfg.animate:
            anim_css = """
            <style>
                @keyframes patternFloat {
                    0%, 100% { transform: translate(0, 0); }
                    50% { transform: translate(5px, -5px); }
                }
                svg > *:not(rect:first-child):not(defs):not(style) {
                    animation: patternFloat 4s ease-in-out infinite;
                }
            </style>"""

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{cfg.width}" height="{cfg.height}" 
     viewBox="0 0 {cfg.width} {cfg.height}" role="img">
    <title>Generated {cfg.pattern_type.value} pattern</title>
    <desc>Procedurally generated SVG pattern by Raster to SVG Converter</desc>
    {anim_css}
    <rect width="{cfg.width}" height="{cfg.height}" fill="{cfg.background}"/>
    {content}
</svg>"""
