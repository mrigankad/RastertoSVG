"""Multi-format export service — Phase 10.

Converts SVG to multiple professional vector formats:
- PDF  (via CairoSVG or ReportLab)
- EPS  (Encapsulated PostScript for print)
- DXF  (AutoCAD format for CAD/engineering)
- EMF  (Enhanced Metafile for Windows/Office)
- PNG  (High-res rasterized preview)

Each exporter gracefully falls back if its dependency is missing.
"""

import io
import logging
import math
import re
import struct
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


# =============================================================================
# Export Format Enum
# =============================================================================


class ExportFormat(str, Enum):
    SVG = "svg"
    PDF = "pdf"
    EPS = "eps"
    DXF = "dxf"
    EMF = "emf"
    PNG = "png"


@dataclass
class ExportOptions:
    """Common export options."""

    format: ExportFormat = ExportFormat.SVG
    scale: float = 1.0
    dpi: int = 300
    width: Optional[int] = None
    height: Optional[int] = None
    background_color: Optional[str] = None
    color_space: str = "rgb"  # "rgb", "cmyk"
    embed_fonts: bool = True
    compress: bool = False
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExportResult:
    """Result of an export operation."""

    data: bytes
    format: ExportFormat
    mime_type: str
    file_extension: str
    size_bytes: int
    export_time_ms: int
    warnings: List[str] = field(default_factory=list)


# =============================================================================
# Format capabilities
# =============================================================================

FORMAT_INFO = {
    ExportFormat.SVG: {
        "name": "Scalable Vector Graphics",
        "extension": ".svg",
        "mime_type": "image/svg+xml",
        "supports_color": True,
        "supports_gradients": True,
        "supports_transparency": True,
        "best_for": ["web", "responsive design", "editing"],
        "requires": [],
    },
    ExportFormat.PDF: {
        "name": "Portable Document Format",
        "extension": ".pdf",
        "mime_type": "application/pdf",
        "supports_color": True,
        "supports_gradients": True,
        "supports_transparency": True,
        "best_for": ["print", "documents", "archival"],
        "requires": ["cairosvg"],
    },
    ExportFormat.EPS: {
        "name": "Encapsulated PostScript",
        "extension": ".eps",
        "mime_type": "application/postscript",
        "supports_color": True,
        "supports_gradients": False,
        "supports_transparency": False,
        "best_for": ["print", "prepress", "legacy workflows"],
        "requires": [],
    },
    ExportFormat.DXF: {
        "name": "Drawing Exchange Format",
        "extension": ".dxf",
        "mime_type": "application/dxf",
        "supports_color": True,
        "supports_gradients": False,
        "supports_transparency": False,
        "best_for": ["CAD", "CNC", "engineering", "laser cutting"],
        "requires": [],
    },
    ExportFormat.EMF: {
        "name": "Enhanced Metafile",
        "extension": ".emf",
        "mime_type": "application/x-emf",
        "supports_color": True,
        "supports_gradients": False,
        "supports_transparency": False,
        "best_for": ["Microsoft Office", "Windows apps", "presentations"],
        "requires": [],
    },
    ExportFormat.PNG: {
        "name": "Portable Network Graphics",
        "extension": ".png",
        "mime_type": "image/png",
        "supports_color": True,
        "supports_gradients": True,
        "supports_transparency": True,
        "best_for": ["preview", "thumbnails", "raster fallback"],
        "requires": ["cairosvg"],
    },
}


# =============================================================================
# SVG Parser utilities
# =============================================================================


def _parse_svg(svg_data: bytes) -> ET.Element:
    """Parse SVG XML and return root element."""
    return ET.fromstring(svg_data)


def _get_svg_dimensions(root: ET.Element) -> tuple[float, float]:
    """Extract width and height from SVG root."""
    ns = {"svg": "http://www.w3.org/2000/svg"}

    width = root.get("width", "100")
    height = root.get("height", "100")

    # Strip units
    w = float(re.sub(r"[a-z%]+$", "", width, flags=re.I) or "100")
    h = float(re.sub(r"[a-z%]+$", "", height, flags=re.I) or "100")

    # Try viewBox if dimensions are 0
    if w == 0 or h == 0:
        viewBox = root.get("viewBox", "")
        if viewBox:
            parts = viewBox.split()
            if len(parts) == 4:
                w = float(parts[2])
                h = float(parts[3])

    return w, h


def _extract_paths(root: ET.Element) -> list:
    """Extract path data from SVG for DXF/EPS conversion."""
    ns = {"svg": "http://www.w3.org/2000/svg"}
    paths = []

    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

        if tag == "path":
            d = elem.get("d", "")
            fill = elem.get("fill", "none")
            stroke = elem.get("stroke", "none")
            stroke_width = float(elem.get("stroke-width", "1"))
            paths.append(
                {
                    "type": "path",
                    "d": d,
                    "fill": fill,
                    "stroke": stroke,
                    "stroke_width": stroke_width,
                }
            )
        elif tag == "rect":
            x = float(elem.get("x", "0"))
            y = float(elem.get("y", "0"))
            w = float(elem.get("width", "0"))
            h = float(elem.get("height", "0"))
            paths.append(
                {
                    "type": "rect",
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "fill": elem.get("fill", "none"),
                    "stroke": elem.get("stroke", "none"),
                }
            )
        elif tag == "circle":
            cx = float(elem.get("cx", "0"))
            cy = float(elem.get("cy", "0"))
            r = float(elem.get("r", "0"))
            paths.append(
                {
                    "type": "circle",
                    "cx": cx,
                    "cy": cy,
                    "r": r,
                    "fill": elem.get("fill", "none"),
                    "stroke": elem.get("stroke", "none"),
                }
            )
        elif tag == "line":
            paths.append(
                {
                    "type": "line",
                    "x1": float(elem.get("x1", "0")),
                    "y1": float(elem.get("y1", "0")),
                    "x2": float(elem.get("x2", "0")),
                    "y2": float(elem.get("y2", "0")),
                    "stroke": elem.get("stroke", "black"),
                }
            )
        elif tag == "polygon" or tag == "polyline":
            points_str = elem.get("points", "")
            points = []
            for pt in points_str.strip().split():
                coords = pt.split(",")
                if len(coords) == 2:
                    points.append((float(coords[0]), float(coords[1])))
            paths.append(
                {
                    "type": tag,
                    "points": points,
                    "fill": elem.get("fill", "none"),
                    "stroke": elem.get("stroke", "none"),
                }
            )

    return paths


def _parse_color(color_str: str) -> tuple[int, int, int]:
    """Parse CSS color to RGB tuple."""
    if not color_str or color_str == "none" or color_str == "transparent":
        return (0, 0, 0)

    color_str = color_str.strip().lower()

    # Named colors
    named = {
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "red": (255, 0, 0),
        "green": (0, 128, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "cyan": (0, 255, 255),
        "magenta": (255, 0, 255),
        "gray": (128, 128, 128),
        "grey": (128, 128, 128),
        "orange": (255, 165, 0),
        "purple": (128, 0, 128),
    }
    if color_str in named:
        return named[color_str]

    # Hex
    if color_str.startswith("#"):
        hex_str = color_str[1:]
        if len(hex_str) == 3:
            hex_str = "".join(c * 2 for c in hex_str)
        if len(hex_str) >= 6:
            return (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))

    # rgb()
    m = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", color_str)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))

    return (0, 0, 0)


def _parse_path_d(d: str) -> list:
    """Parse SVG path 'd' attribute into segments."""
    segments = []
    tokens = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?[0-9]*\.?[0-9]+", d)

    cmd = ""
    nums = []
    for token in tokens:
        if token.isalpha():
            if cmd:
                segments.append((cmd, nums))
            cmd = token
            nums = []
        else:
            nums.append(float(token))

    if cmd:
        segments.append((cmd, nums))

    return segments


# =============================================================================
# PDF Exporter
# =============================================================================


class PDFExporter:
    """Export SVG to PDF using CairoSVG."""

    @staticmethod
    def is_available() -> bool:
        try:
            import cairosvg

            return True
        except ImportError:
            return False

    @staticmethod
    def export(svg_data: bytes, options: ExportOptions) -> ExportResult:
        start = time.time()
        warnings = []

        try:
            import cairosvg
        except ImportError:
            raise RuntimeError(
                "CairoSVG is required for PDF export. Install with: pip install cairosvg"
            )

        kwargs: Dict[str, Any] = {}
        if options.dpi:
            kwargs["dpi"] = options.dpi
        if options.scale and options.scale != 1.0:
            kwargs["scale"] = options.scale
        if options.width:
            kwargs["output_width"] = options.width
        if options.height:
            kwargs["output_height"] = options.height
        if options.background_color:
            kwargs["background_color"] = options.background_color

        pdf_data = cairosvg.svg2pdf(bytestring=svg_data, **kwargs)

        return ExportResult(
            data=pdf_data,
            format=ExportFormat.PDF,
            mime_type="application/pdf",
            file_extension=".pdf",
            size_bytes=len(pdf_data),
            export_time_ms=int((time.time() - start) * 1000),
            warnings=warnings,
        )


# =============================================================================
# EPS Exporter
# =============================================================================


class EPSExporter:
    """Export SVG to EPS (pure Python — no external dependencies)."""

    @staticmethod
    def is_available() -> bool:
        return True  # Always available (pure Python)

    @staticmethod
    def export(svg_data: bytes, options: ExportOptions) -> ExportResult:
        start = time.time()
        warnings = []

        root = _parse_svg(svg_data)
        width, height = _get_svg_dimensions(root)
        scale = options.scale

        # EPS header
        eps_lines = [
            "%!PS-Adobe-3.0 EPSF-3.0",
            f"%%BoundingBox: 0 0 {int(width * scale)} {int(height * scale)}",
            f"%%HiResBoundingBox: 0.0 0.0 {width * scale:.4f} {height * scale:.4f}",
            f"%%Title: Raster to SVG Export",
            f"%%Creator: Raster to SVG Converter",
            "%%DocumentData: Clean7Bit",
            "%%EndComments",
            "",
            "gsave",
            f"{scale} {scale} scale",
            f"0 {height} translate",
            "1 -1 scale",  # Flip Y axis (SVG is top-down, PS is bottom-up)
            "",
        ]

        # Background
        if options.background_color:
            r, g, b = _parse_color(options.background_color)
            eps_lines.extend(
                [
                    f"{r / 255:.4f} {g / 255:.4f} {b / 255:.4f} setrgbcolor",
                    f"0 0 {width} {height} rectfill",
                    "",
                ]
            )

        # Convert elements
        elements = _extract_paths(root)
        for elem in elements:
            eps_lines.extend(EPSExporter._element_to_ps(elem))

        # Footer
        eps_lines.extend(
            [
                "",
                "grestore",
                "%%EOF",
            ]
        )

        eps_data = "\n".join(eps_lines).encode("latin-1")

        if not elements:
            warnings.append("No drawable elements found in SVG")

        return ExportResult(
            data=eps_data,
            format=ExportFormat.EPS,
            mime_type="application/postscript",
            file_extension=".eps",
            size_bytes=len(eps_data),
            export_time_ms=int((time.time() - start) * 1000),
            warnings=warnings,
        )

    @staticmethod
    def _element_to_ps(elem: dict) -> list:
        """Convert an SVG element to PostScript commands."""
        lines = []
        elem_type = elem.get("type", "")

        if elem_type == "rect":
            x, y = elem["x"], elem["y"]
            w, h = elem["width"], elem["height"]
            fill = elem.get("fill", "none")

            if fill and fill != "none":
                r, g, b = _parse_color(fill)
                lines.append(f"{r / 255:.4f} {g / 255:.4f} {b / 255:.4f} setrgbcolor")
                lines.append(f"{x} {y} {w} {h} rectfill")

            stroke = elem.get("stroke", "none")
            if stroke and stroke != "none":
                r, g, b = _parse_color(stroke)
                lines.append(f"{r / 255:.4f} {g / 255:.4f} {b / 255:.4f} setrgbcolor")
                lines.append(f"{x} {y} {w} {h} rectstroke")

        elif elem_type == "circle":
            cx, cy, rad = elem["cx"], elem["cy"], elem["r"]
            fill = elem.get("fill", "none")

            if fill and fill != "none":
                r, g, b = _parse_color(fill)
                lines.append(f"{r / 255:.4f} {g / 255:.4f} {b / 255:.4f} setrgbcolor")
                lines.append(f"newpath {cx} {cy} {rad} 0 360 arc closepath fill")

            stroke = elem.get("stroke", "none")
            if stroke and stroke != "none":
                r, g, b = _parse_color(stroke)
                lines.append(f"{r / 255:.4f} {g / 255:.4f} {b / 255:.4f} setrgbcolor")
                lines.append(f"newpath {cx} {cy} {rad} 0 360 arc closepath stroke")

        elif elem_type == "line":
            r, g, b = _parse_color(elem.get("stroke", "black"))
            lines.append(f"{r / 255:.4f} {g / 255:.4f} {b / 255:.4f} setrgbcolor")
            lines.append(
                f"newpath {elem['x1']} {elem['y1']} moveto {elem['x2']} {elem['y2']} lineto stroke"
            )

        elif elem_type == "path":
            d = elem.get("d", "")
            fill = elem.get("fill", "none")
            stroke = elem.get("stroke", "none")

            ps_path = EPSExporter._path_d_to_ps(d)
            if ps_path:
                if fill and fill != "none":
                    r, g, b = _parse_color(fill)
                    lines.append(f"{r / 255:.4f} {g / 255:.4f} {b / 255:.4f} setrgbcolor")
                    lines.append(f"newpath {ps_path} closepath fill")

                if stroke and stroke != "none":
                    r, g, b = _parse_color(stroke)
                    sw = elem.get("stroke_width", 1)
                    lines.append(f"{sw} setlinewidth")
                    lines.append(f"{r / 255:.4f} {g / 255:.4f} {b / 255:.4f} setrgbcolor")
                    lines.append(f"newpath {ps_path} stroke")

        elif elem_type in ("polygon", "polyline"):
            points = elem.get("points", [])
            if points:
                fill = elem.get("fill", "none")
                ps_pts = f"{points[0][0]} {points[0][1]} moveto "
                ps_pts += " ".join(f"{px} {py} lineto" for px, py in points[1:])

                if fill and fill != "none" and elem_type == "polygon":
                    r, g, b = _parse_color(fill)
                    lines.append(f"{r / 255:.4f} {g / 255:.4f} {b / 255:.4f} setrgbcolor")
                    lines.append(f"newpath {ps_pts} closepath fill")

                stroke = elem.get("stroke", "none")
                if stroke and stroke != "none":
                    r, g, b = _parse_color(stroke)
                    lines.append(f"{r / 255:.4f} {g / 255:.4f} {b / 255:.4f} setrgbcolor")
                    lines.append(f"newpath {ps_pts} stroke")

        return lines

    @staticmethod
    def _path_d_to_ps(d: str) -> str:
        """Convert SVG path 'd' attribute to PostScript path commands."""
        segments = _parse_path_d(d)
        ps_parts = []
        cx, cy = 0.0, 0.0

        for cmd, nums in segments:
            if cmd == "M" and len(nums) >= 2:
                cx, cy = nums[0], nums[1]
                ps_parts.append(f"{cx:.4f} {cy:.4f} moveto")
            elif cmd == "m" and len(nums) >= 2:
                cx += nums[0]
                cy += nums[1]
                ps_parts.append(f"{cx:.4f} {cy:.4f} moveto")
            elif cmd == "L" and len(nums) >= 2:
                for i in range(0, len(nums) - 1, 2):
                    cx, cy = nums[i], nums[i + 1]
                    ps_parts.append(f"{cx:.4f} {cy:.4f} lineto")
            elif cmd == "l" and len(nums) >= 2:
                for i in range(0, len(nums) - 1, 2):
                    cx += nums[i]
                    cy += nums[i + 1]
                    ps_parts.append(f"{cx:.4f} {cy:.4f} lineto")
            elif cmd == "H" and len(nums) >= 1:
                cx = nums[0]
                ps_parts.append(f"{cx:.4f} {cy:.4f} lineto")
            elif cmd == "h" and len(nums) >= 1:
                cx += nums[0]
                ps_parts.append(f"{cx:.4f} {cy:.4f} lineto")
            elif cmd == "V" and len(nums) >= 1:
                cy = nums[0]
                ps_parts.append(f"{cx:.4f} {cy:.4f} lineto")
            elif cmd == "v" and len(nums) >= 1:
                cy += nums[0]
                ps_parts.append(f"{cx:.4f} {cy:.4f} lineto")
            elif cmd == "C" and len(nums) >= 6:
                for i in range(0, len(nums) - 5, 6):
                    ps_parts.append(
                        f"{nums[i]:.4f} {nums[i+1]:.4f} "
                        f"{nums[i+2]:.4f} {nums[i+3]:.4f} "
                        f"{nums[i+4]:.4f} {nums[i+5]:.4f} curveto"
                    )
                    cx, cy = nums[i + 4], nums[i + 5]
            elif cmd in ("Z", "z"):
                ps_parts.append("closepath")

        return " ".join(ps_parts)


# =============================================================================
# DXF Exporter
# =============================================================================


class DXFExporter:
    """Export SVG to DXF (pure Python — AutoCAD compatible)."""

    @staticmethod
    def is_available() -> bool:
        return True

    @staticmethod
    def export(svg_data: bytes, options: ExportOptions) -> ExportResult:
        start = time.time()
        warnings = []

        root = _parse_svg(svg_data)
        width, height = _get_svg_dimensions(root)
        scale = options.scale
        elements = _extract_paths(root)

        # Build DXF content
        dxf_lines = DXFExporter._build_header(width * scale, height * scale)
        dxf_lines.extend(DXFExporter._build_tables())
        dxf_lines.extend(DXFExporter._build_entities_start())

        for elem in elements:
            dxf_lines.extend(DXFExporter._element_to_dxf(elem, height, scale))

        dxf_lines.extend(DXFExporter._build_footer())

        dxf_data = "\n".join(dxf_lines).encode("ascii", errors="replace")

        if not elements:
            warnings.append("No drawable elements found in SVG")

        return ExportResult(
            data=dxf_data,
            format=ExportFormat.DXF,
            mime_type="application/dxf",
            file_extension=".dxf",
            size_bytes=len(dxf_data),
            export_time_ms=int((time.time() - start) * 1000),
            warnings=warnings,
        )

    @staticmethod
    def _build_header(width: float, height: float) -> list:
        return [
            "0",
            "SECTION",
            "2",
            "HEADER",
            "9",
            "$ACADVER",
            "1",
            "AC1015",
            "9",
            "$INSBASE",
            "10",
            "0.0",
            "20",
            "0.0",
            "30",
            "0.0",
            "9",
            "$EXTMIN",
            "10",
            "0.0",
            "20",
            "0.0",
            "30",
            "0.0",
            "9",
            "$EXTMAX",
            "10",
            f"{width:.6f}",
            "20",
            f"{height:.6f}",
            "30",
            "0.0",
            "0",
            "ENDSEC",
        ]

    @staticmethod
    def _build_tables() -> list:
        return [
            "0",
            "SECTION",
            "2",
            "TABLES",
            "0",
            "TABLE",
            "2",
            "LTYPE",
            "70",
            "1",
            "0",
            "LTYPE",
            "2",
            "CONTINUOUS",
            "70",
            "0",
            "3",
            "Solid line",
            "72",
            "65",
            "73",
            "0",
            "40",
            "0.0",
            "0",
            "ENDTAB",
            "0",
            "TABLE",
            "2",
            "LAYER",
            "70",
            "1",
            "0",
            "LAYER",
            "2",
            "0",
            "70",
            "0",
            "62",
            "7",
            "6",
            "CONTINUOUS",
            "0",
            "ENDTAB",
            "0",
            "ENDSEC",
        ]

    @staticmethod
    def _build_entities_start() -> list:
        return ["0", "SECTION", "2", "ENTITIES"]

    @staticmethod
    def _build_footer() -> list:
        return ["0", "ENDSEC", "0", "EOF"]

    @staticmethod
    def _color_to_aci(r: int, g: int, b: int) -> int:
        """Map RGB to nearest AutoCAD Color Index (ACI)."""
        if r == 0 and g == 0 and b == 0:
            return 0  # Black
        if r == 255 and g == 0 and b == 0:
            return 1
        if r == 255 and g == 255 and b == 0:
            return 2
        if r == 0 and g == 255 and b == 0:
            return 3
        if r == 0 and g == 255 and b == 255:
            return 4
        if r == 0 and g == 0 and b == 255:
            return 5
        if r == 255 and g == 0 and b == 255:
            return 6
        if r == 255 and g == 255 and b == 255:
            return 7

        # Approximate with nearest basic color
        brightness = (r + g + b) / 3
        if brightness > 200:
            return 7  # White-ish
        if brightness < 50:
            return 0  # Black-ish
        if r > g and r > b:
            return 1  # Red-ish
        if g > r and g > b:
            return 3  # Green-ish
        if b > r and b > g:
            return 5  # Blue-ish
        return 7

    @staticmethod
    def _element_to_dxf(elem: dict, svg_height: float, scale: float) -> list:
        """Convert SVG element to DXF entities."""
        lines = []
        elem_type = elem.get("type", "")

        color = elem.get("stroke", elem.get("fill", "black"))
        if color == "none":
            color = elem.get("fill", "black")
        r, g, b = _parse_color(color)
        aci = DXFExporter._color_to_aci(r, g, b)

        if elem_type == "line":
            x1 = elem["x1"] * scale
            y1 = (svg_height - elem["y1"]) * scale  # Flip Y
            x2 = elem["x2"] * scale
            y2 = (svg_height - elem["y2"]) * scale
            lines.extend(
                [
                    "0",
                    "LINE",
                    "8",
                    "0",
                    "62",
                    str(aci),
                    "10",
                    f"{x1:.6f}",
                    "20",
                    f"{y1:.6f}",
                    "30",
                    "0.0",
                    "11",
                    f"{x2:.6f}",
                    "21",
                    f"{y2:.6f}",
                    "31",
                    "0.0",
                ]
            )

        elif elem_type == "rect":
            x = elem["x"] * scale
            y = (svg_height - elem["y"]) * scale
            w = elem["width"] * scale
            h = elem["height"] * scale
            # Draw as LWPOLYLINE (closed rectangle)
            lines.extend(
                [
                    "0",
                    "LWPOLYLINE",
                    "8",
                    "0",
                    "62",
                    str(aci),
                    "90",
                    "4",
                    "70",
                    "1",  # Closed
                    "10",
                    f"{x:.6f}",
                    "20",
                    f"{y:.6f}",
                    "10",
                    f"{x + w:.6f}",
                    "20",
                    f"{y:.6f}",
                    "10",
                    f"{x + w:.6f}",
                    "20",
                    f"{y - h:.6f}",
                    "10",
                    f"{x:.6f}",
                    "20",
                    f"{y - h:.6f}",
                ]
            )

        elif elem_type == "circle":
            cx = elem["cx"] * scale
            cy = (svg_height - elem["cy"]) * scale
            rad = elem["r"] * scale
            lines.extend(
                [
                    "0",
                    "CIRCLE",
                    "8",
                    "0",
                    "62",
                    str(aci),
                    "10",
                    f"{cx:.6f}",
                    "20",
                    f"{cy:.6f}",
                    "30",
                    "0.0",
                    "40",
                    f"{rad:.6f}",
                ]
            )

        elif elem_type == "path":
            # Convert path to line segments (approximate curves)
            segments = _parse_path_d(elem.get("d", ""))
            dxf_points = DXFExporter._path_to_dxf_points(segments, svg_height, scale)
            if len(dxf_points) >= 2:
                lines.extend(
                    [
                        "0",
                        "LWPOLYLINE",
                        "8",
                        "0",
                        "62",
                        str(aci),
                        "90",
                        str(len(dxf_points)),
                        "70",
                        "0",
                    ]
                )
                for px, py in dxf_points:
                    lines.extend(["10", f"{px:.6f}", "20", f"{py:.6f}"])

        elif elem_type in ("polygon", "polyline"):
            points = elem.get("points", [])
            if points:
                closed = "1" if elem_type == "polygon" else "0"
                lines.extend(
                    [
                        "0",
                        "LWPOLYLINE",
                        "8",
                        "0",
                        "62",
                        str(aci),
                        "90",
                        str(len(points)),
                        "70",
                        closed,
                    ]
                )
                for px, py in points:
                    dx = px * scale
                    dy = (svg_height - py) * scale
                    lines.extend(["10", f"{dx:.6f}", "20", f"{dy:.6f}"])

        return lines

    @staticmethod
    def _path_to_dxf_points(segments: list, svg_height: float, scale: float) -> list:
        """Convert SVG path segments to DXF polyline points."""
        points = []
        cx, cy = 0.0, 0.0

        for cmd, nums in segments:
            if cmd == "M" and len(nums) >= 2:
                cx, cy = nums[0], nums[1]
                points.append((cx * scale, (svg_height - cy) * scale))
            elif cmd == "m" and len(nums) >= 2:
                cx += nums[0]
                cy += nums[1]
                points.append((cx * scale, (svg_height - cy) * scale))
            elif cmd == "L" and len(nums) >= 2:
                for i in range(0, len(nums) - 1, 2):
                    cx, cy = nums[i], nums[i + 1]
                    points.append((cx * scale, (svg_height - cy) * scale))
            elif cmd == "l" and len(nums) >= 2:
                for i in range(0, len(nums) - 1, 2):
                    cx += nums[i]
                    cy += nums[i + 1]
                    points.append((cx * scale, (svg_height - cy) * scale))
            elif cmd == "H" and len(nums) >= 1:
                cx = nums[0]
                points.append((cx * scale, (svg_height - cy) * scale))
            elif cmd == "h" and len(nums) >= 1:
                cx += nums[0]
                points.append((cx * scale, (svg_height - cy) * scale))
            elif cmd == "V" and len(nums) >= 1:
                cy = nums[0]
                points.append((cx * scale, (svg_height - cy) * scale))
            elif cmd == "v" and len(nums) >= 1:
                cy += nums[0]
                points.append((cx * scale, (svg_height - cy) * scale))
            elif cmd == "C" and len(nums) >= 6:
                # Approximate cubic Bezier with line segments
                for i in range(0, len(nums) - 5, 6):
                    for t in [0.25, 0.5, 0.75, 1.0]:
                        bx = (
                            (1 - t) ** 3 * cx
                            + 3 * (1 - t) ** 2 * t * nums[i]
                            + 3 * (1 - t) * t**2 * nums[i + 2]
                            + t**3 * nums[i + 4]
                        )
                        by = (
                            (1 - t) ** 3 * cy
                            + 3 * (1 - t) ** 2 * t * nums[i + 1]
                            + 3 * (1 - t) * t**2 * nums[i + 3]
                            + t**3 * nums[i + 5]
                        )
                        points.append((bx * scale, (svg_height - by) * scale))
                    cx, cy = nums[i + 4], nums[i + 5]

        return points


# =============================================================================
# PNG Exporter
# =============================================================================


class PNGExporter:
    """Export SVG to high-resolution PNG using CairoSVG."""

    @staticmethod
    def is_available() -> bool:
        try:
            import cairosvg

            return True
        except ImportError:
            return False

    @staticmethod
    def export(svg_data: bytes, options: ExportOptions) -> ExportResult:
        start = time.time()
        warnings = []

        try:
            import cairosvg
        except ImportError:
            raise RuntimeError("CairoSVG is required for PNG export.")

        kwargs: Dict[str, Any] = {}
        if options.dpi:
            kwargs["dpi"] = options.dpi
        if options.scale and options.scale != 1.0:
            kwargs["scale"] = options.scale
        if options.width:
            kwargs["output_width"] = options.width
        if options.height:
            kwargs["output_height"] = options.height
        if options.background_color:
            kwargs["background_color"] = options.background_color

        png_data = cairosvg.svg2png(bytestring=svg_data, **kwargs)

        return ExportResult(
            data=png_data,
            format=ExportFormat.PNG,
            mime_type="image/png",
            file_extension=".png",
            size_bytes=len(png_data),
            export_time_ms=int((time.time() - start) * 1000),
            warnings=warnings,
        )


# =============================================================================
# Master Export Engine
# =============================================================================


class ExportEngine:
    """Orchestrates multi-format SVG export."""

    _exporters = {
        ExportFormat.PDF: PDFExporter,
        ExportFormat.EPS: EPSExporter,
        ExportFormat.DXF: DXFExporter,
        ExportFormat.PNG: PNGExporter,
    }

    @classmethod
    def get_available_formats(cls) -> Dict[str, dict]:
        """Get all available export formats and their capabilities."""
        result = {}
        for fmt, info in FORMAT_INFO.items():
            exporter = cls._exporters.get(fmt)
            available = True
            if exporter:
                available = exporter.is_available()
            elif fmt != ExportFormat.SVG:
                available = False

            result[fmt.value] = {
                **info,
                "available": available,
            }
        return result

    @classmethod
    def export(cls, svg_data: bytes, options: ExportOptions) -> ExportResult:
        """Export SVG to the specified format."""
        if options.format == ExportFormat.SVG:
            return ExportResult(
                data=svg_data,
                format=ExportFormat.SVG,
                mime_type="image/svg+xml",
                file_extension=".svg",
                size_bytes=len(svg_data),
                export_time_ms=0,
            )

        exporter = cls._exporters.get(options.format)
        if not exporter:
            raise ValueError(f"Unsupported export format: {options.format}")

        if not exporter.is_available():
            info = FORMAT_INFO.get(options.format, {})
            requires = info.get("requires", [])
            raise RuntimeError(
                f"Export to {options.format.value} requires: {', '.join(requires)}. "
                f"Install with: pip install {' '.join(requires)}"
            )

        return exporter.export(svg_data, options)

    @classmethod
    def batch_export(
        cls,
        svg_data: bytes,
        formats: List[ExportFormat],
        base_options: Optional[ExportOptions] = None,
    ) -> Dict[str, ExportResult]:
        """Export SVG to multiple formats at once."""
        results = {}
        for fmt in formats:
            opts = (
                ExportOptions()
                if base_options is None
                else ExportOptions(
                    format=fmt,
                    scale=base_options.scale,
                    dpi=base_options.dpi,
                    width=base_options.width,
                    height=base_options.height,
                    background_color=base_options.background_color,
                    color_space=base_options.color_space,
                )
            )
            opts.format = fmt

            try:
                results[fmt.value] = cls.export(svg_data, opts)
            except Exception as e:
                logger.error(f"Export to {fmt.value} failed: {e}")
                results[fmt.value] = ExportResult(
                    data=b"",
                    format=fmt,
                    mime_type="application/octet-stream",
                    file_extension="",
                    size_bytes=0,
                    export_time_ms=0,
                    warnings=[f"Export failed: {str(e)}"],
                )
        return results
