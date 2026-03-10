"""SVG Animation service — Phase 10.

Adds animation capabilities to SVG output:
- CSS animations (hover, transitions, keyframes)
- SMIL animations (path morphing, color transitions)
- Lottie JSON export (cross-platform animation)
- Animation presets: draw-stroke, fade-in, color-cycle, pulse

All animation is injected into existing SVGs non-destructively.
"""

import json
import logging
import re
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


# =============================================================================
# Animation Types
# =============================================================================

class AnimationType(str, Enum):
    DRAW_STROKE = "draw_stroke"
    FADE_IN = "fade_in"
    COLOR_CYCLE = "color_cycle"
    PULSE = "pulse"
    SLIDE_IN = "slide_in"
    ROTATE = "rotate"
    BOUNCE = "bounce"
    MORPH = "morph"


class AnimationMethod(str, Enum):
    CSS = "css"
    SMIL = "smil"
    LOTTIE = "lottie"


@dataclass
class AnimationConfig:
    """Animation configuration."""
    type: AnimationType = AnimationType.DRAW_STROKE
    method: AnimationMethod = AnimationMethod.CSS
    duration: float = 2.0  # seconds
    delay: float = 0.0
    easing: str = "ease-in-out"
    iteration_count: str = "1"  # "1", "infinite"
    direction: str = "normal"  # "normal", "reverse", "alternate"
    stagger: float = 0.1  # Delay between elements
    colors: List[str] = field(default_factory=lambda: ["#3b82f6", "#8b5cf6", "#ec4899"])


@dataclass
class AnimationResult:
    """Result of animation generation."""
    svg_data: bytes
    method: AnimationMethod
    element_count: int
    animation_time_ms: int
    lottie_json: Optional[dict] = None


# =============================================================================
# CSS Animation Generator
# =============================================================================

class CSSAnimator:
    """Inject CSS animations into SVG elements."""

    @staticmethod
    def animate(svg_data: bytes, config: AnimationConfig) -> bytes:
        """Add CSS animation to SVG."""
        root = ET.fromstring(svg_data)
        ns = {"svg": "http://www.w3.org/2000/svg"}

        # Register SVG namespace
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

        # Build CSS keyframes
        css = CSSAnimator._build_css(config)

        # Inject <style> element
        style_elem = ET.SubElement(root, "style")
        style_elem.text = css

        # Add animation classes to paths
        idx = 0
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag in ("path", "circle", "rect", "polygon", "polyline", "line", "ellipse"):
                delay = config.delay + (idx * config.stagger)
                elem.set("class", f"anim-{config.type.value}")
                elem.set("style", f"animation-delay: {delay:.2f}s;")
                idx += 1

        return ET.tostring(root, encoding="unicode").encode("utf-8")

    @staticmethod
    def _build_css(config: AnimationConfig) -> str:
        """Build CSS keyframes for the animation type."""
        dur = config.duration
        easing = config.easing
        iters = config.iteration_count
        direction = config.direction

        base_props = (
            f"animation-duration: {dur}s; "
            f"animation-timing-function: {easing}; "
            f"animation-iteration-count: {iters}; "
            f"animation-direction: {direction}; "
            f"animation-fill-mode: both;"
        )

        if config.type == AnimationType.DRAW_STROKE:
            return f"""
                .anim-draw_stroke {{
                    animation-name: drawStroke;
                    {base_props}
                    stroke-dasharray: 1000;
                    stroke-dashoffset: 1000;
                }}
                @keyframes drawStroke {{
                    0% {{ stroke-dashoffset: 1000; opacity: 0.3; }}
                    20% {{ opacity: 1; }}
                    100% {{ stroke-dashoffset: 0; opacity: 1; }}
                }}
            """

        elif config.type == AnimationType.FADE_IN:
            return f"""
                .anim-fade_in {{
                    animation-name: fadeIn;
                    {base_props}
                }}
                @keyframes fadeIn {{
                    0% {{ opacity: 0; transform: translateY(10px); }}
                    100% {{ opacity: 1; transform: translateY(0); }}
                }}
            """

        elif config.type == AnimationType.COLOR_CYCLE:
            colors = config.colors
            stops = []
            for i, color in enumerate(colors):
                pct = int((i / max(len(colors) - 1, 1)) * 100)
                stops.append(f"{pct}% {{ fill: {color}; }}")

            return f"""
                .anim-color_cycle {{
                    animation-name: colorCycle;
                    {base_props}
                }}
                @keyframes colorCycle {{
                    {' '.join(stops)}
                }}
            """

        elif config.type == AnimationType.PULSE:
            return f"""
                .anim-pulse {{
                    animation-name: pulse;
                    {base_props}
                    transform-origin: center;
                }}
                @keyframes pulse {{
                    0%, 100% {{ transform: scale(1); opacity: 1; }}
                    50% {{ transform: scale(1.05); opacity: 0.8; }}
                }}
            """

        elif config.type == AnimationType.SLIDE_IN:
            return f"""
                .anim-slide_in {{
                    animation-name: slideIn;
                    {base_props}
                }}
                @keyframes slideIn {{
                    0% {{ transform: translateX(-30px); opacity: 0; }}
                    100% {{ transform: translateX(0); opacity: 1; }}
                }}
            """

        elif config.type == AnimationType.ROTATE:
            return f"""
                .anim-rotate {{
                    animation-name: rotate;
                    {base_props}
                    transform-origin: center;
                }}
                @keyframes rotate {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
            """

        elif config.type == AnimationType.BOUNCE:
            return f"""
                .anim-bounce {{
                    animation-name: bounce;
                    {base_props}
                    transform-origin: center bottom;
                }}
                @keyframes bounce {{
                    0%, 100% {{ transform: translateY(0); }}
                    30% {{ transform: translateY(-15px); }}
                    50% {{ transform: translateY(0); }}
                    70% {{ transform: translateY(-7px); }}
                }}
            """

        return ""


# =============================================================================
# SMIL Animation Generator
# =============================================================================

class SMILAnimator:
    """Add SMIL animations directly to SVG elements."""

    @staticmethod
    def animate(svg_data: bytes, config: AnimationConfig) -> bytes:
        """Add SMIL animation to SVG."""
        root = ET.fromstring(svg_data)
        ET.register_namespace("", "http://www.w3.org/2000/svg")

        idx = 0
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag in ("path", "circle", "rect", "polygon", "polyline", "line", "ellipse"):
                delay = config.delay + (idx * config.stagger)
                SMILAnimator._add_smil_element(elem, config, delay, tag)
                idx += 1

        return ET.tostring(root, encoding="unicode").encode("utf-8")

    @staticmethod
    def _add_smil_element(elem: ET.Element, config: AnimationConfig, delay: float, tag: str):
        """Add SMIL <animate> or <animateTransform> to an element."""
        dur = f"{config.duration}s"
        begin = f"{delay}s"
        repeat = "indefinite" if config.iteration_count == "infinite" else config.iteration_count

        ns = "http://www.w3.org/2000/svg"

        if config.type == AnimationType.FADE_IN:
            anim = ET.SubElement(elem, f"{{{ns}}}animate")
            anim.set("attributeName", "opacity")
            anim.set("from", "0")
            anim.set("to", "1")
            anim.set("dur", dur)
            anim.set("begin", begin)
            anim.set("fill", "freeze")
            anim.set("repeatCount", repeat)
            elem.set("opacity", "0")

        elif config.type == AnimationType.COLOR_CYCLE:
            if config.colors:
                anim = ET.SubElement(elem, f"{{{ns}}}animate")
                anim.set("attributeName", "fill")
                anim.set("values", ";".join(config.colors))
                anim.set("dur", dur)
                anim.set("begin", begin)
                anim.set("repeatCount", repeat)

        elif config.type == AnimationType.PULSE:
            anim = ET.SubElement(elem, f"{{{ns}}}animateTransform")
            anim.set("attributeName", "transform")
            anim.set("type", "scale")
            anim.set("values", "1;1.05;1")
            anim.set("dur", dur)
            anim.set("begin", begin)
            anim.set("repeatCount", repeat)
            anim.set("additive", "sum")

        elif config.type == AnimationType.ROTATE:
            anim = ET.SubElement(elem, f"{{{ns}}}animateTransform")
            anim.set("attributeName", "transform")
            anim.set("type", "rotate")
            anim.set("from", "0")
            anim.set("to", "360")
            anim.set("dur", dur)
            anim.set("begin", begin)
            anim.set("repeatCount", repeat)
            anim.set("additive", "sum")

        elif config.type == AnimationType.DRAW_STROKE:
            # SMIL stroke-dashoffset animation
            anim = ET.SubElement(elem, f"{{{ns}}}animate")
            anim.set("attributeName", "stroke-dashoffset")
            anim.set("from", "1000")
            anim.set("to", "0")
            anim.set("dur", dur)
            anim.set("begin", begin)
            anim.set("fill", "freeze")
            elem.set("stroke-dasharray", "1000")
            elem.set("stroke-dashoffset", "1000")


# =============================================================================
# Lottie Export
# =============================================================================

class LottieExporter:
    """Convert SVG to Lottie JSON format."""

    @staticmethod
    def export(svg_data: bytes, config: AnimationConfig) -> dict:
        """Export SVG to Lottie JSON."""
        root = ET.fromstring(svg_data)
        width_str = root.get("width", "100")
        height_str = root.get("height", "100")
        width = float(re.sub(r"[a-z%]+$", "", width_str, flags=re.I) or "100")
        height = float(re.sub(r"[a-z%]+$", "", height_str, flags=re.I) or "100")

        fps = 30
        total_frames = int(config.duration * fps)

        lottie = {
            "v": "5.7.1",
            "fr": fps,
            "ip": 0,
            "op": total_frames,
            "w": int(width),
            "h": int(height),
            "nm": "SVG Animation",
            "ddd": 0,
            "assets": [],
            "layers": [],
        }

        # Convert SVG elements to Lottie shape layers
        idx = 0
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag in ("path", "rect", "circle", "ellipse"):
                layer = LottieExporter._element_to_layer(elem, tag, idx, config, total_frames)
                if layer:
                    lottie["layers"].append(layer)
                    idx += 1

        return lottie

    @staticmethod
    def _element_to_layer(elem: ET.Element, tag: str, idx: int, config: AnimationConfig, total_frames: int) -> Optional[dict]:
        """Convert SVG element to a Lottie layer."""
        delay_frames = int((config.delay + idx * config.stagger) * 30)

        fill_color = elem.get("fill", "#000000")
        if fill_color == "none":
            fill_color = "#000000"

        r, g, b = 0, 0, 0
        if fill_color.startswith("#") and len(fill_color) >= 7:
            r = int(fill_color[1:3], 16)
            g = int(fill_color[3:5], 16)
            b = int(fill_color[5:7], 16)

        layer = {
            "ddd": 0,
            "ind": idx,
            "ty": 4,  # Shape layer
            "nm": f"Shape {idx}",
            "sr": 1,
            "ks": {
                "o": LottieExporter._animated_opacity(config, delay_frames, total_frames),
                "r": {"a": 0, "k": 0},
                "p": {"a": 0, "k": [0, 0, 0]},
                "a": {"a": 0, "k": [0, 0, 0]},
                "s": {"a": 0, "k": [100, 100, 100]},
            },
            "ao": 0,
            "shapes": [],
            "ip": delay_frames,
            "op": total_frames,
            "st": delay_frames,
        }

        # Add shape data
        if tag == "rect":
            x = float(elem.get("x", "0"))
            y = float(elem.get("y", "0"))
            w = float(elem.get("width", "0"))
            h = float(elem.get("height", "0"))
            layer["shapes"].append({
                "ty": "rc",
                "d": 1,
                "s": {"a": 0, "k": [w, h]},
                "p": {"a": 0, "k": [x + w / 2, y + h / 2]},
                "r": {"a": 0, "k": 0},
            })

        elif tag == "circle" or tag == "ellipse":
            cx = float(elem.get("cx", "0"))
            cy = float(elem.get("cy", "0"))
            rx = float(elem.get("r", elem.get("rx", "0")))
            ry = float(elem.get("r", elem.get("ry", str(rx))))
            layer["shapes"].append({
                "ty": "el",
                "d": 1,
                "s": {"a": 0, "k": [rx * 2, ry * 2]},
                "p": {"a": 0, "k": [cx, cy]},
            })

        # Add fill
        layer["shapes"].append({
            "ty": "fl",
            "c": {"a": 0, "k": [r / 255, g / 255, b / 255, 1]},
            "o": {"a": 0, "k": 100},
            "r": 1,
        })

        return layer

    @staticmethod
    def _animated_opacity(config: AnimationConfig, delay: int, total: int) -> dict:
        """Create animated opacity for fade-in effect."""
        if config.type == AnimationType.FADE_IN:
            return {
                "a": 1,
                "k": [
                    {
                        "i": {"x": [0.42], "y": [1]},
                        "o": {"x": [0.58], "y": [0]},
                        "t": delay,
                        "s": [0],
                    },
                    {
                        "t": delay + int(config.duration * 30),
                        "s": [100],
                    },
                ],
            }
        return {"a": 0, "k": 100}


# =============================================================================
# Master Animation Engine
# =============================================================================

class SVGAnimationEngine:
    """Orchestrates SVG animation generation."""

    PRESETS = {
        "draw_stroke": AnimationConfig(
            type=AnimationType.DRAW_STROKE,
            duration=2.5,
            stagger=0.15,
            easing="ease-in-out",
        ),
        "fade_in": AnimationConfig(
            type=AnimationType.FADE_IN,
            duration=1.5,
            stagger=0.1,
            easing="ease-out",
        ),
        "color_cycle": AnimationConfig(
            type=AnimationType.COLOR_CYCLE,
            duration=3.0,
            stagger=0.2,
            iteration_count="infinite",
            colors=["#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b", "#3b82f6"],
        ),
        "pulse": AnimationConfig(
            type=AnimationType.PULSE,
            duration=1.0,
            stagger=0.05,
            iteration_count="infinite",
            easing="ease-in-out",
        ),
    }

    @classmethod
    def animate(
        cls,
        svg_data: bytes,
        config: Optional[AnimationConfig] = None,
        preset: Optional[str] = None,
    ) -> AnimationResult:
        """Apply animation to SVG."""
        start = time.time()

        if preset and preset in cls.PRESETS:
            config = cls.PRESETS[preset]
        elif config is None:
            config = cls.PRESETS["draw_stroke"]

        # Count elements
        root = ET.fromstring(svg_data)
        elem_count = sum(
            1 for elem in root.iter()
            if (elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag)
            in ("path", "circle", "rect", "polygon", "polyline", "line", "ellipse")
        )

        # Apply animation
        lottie_json = None
        if config.method == AnimationMethod.CSS:
            animated_svg = CSSAnimator.animate(svg_data, config)
        elif config.method == AnimationMethod.SMIL:
            animated_svg = SMILAnimator.animate(svg_data, config)
        elif config.method == AnimationMethod.LOTTIE:
            lottie_json = LottieExporter.export(svg_data, config)
            animated_svg = svg_data  # Original SVG unchanged
        else:
            animated_svg = svg_data

        return AnimationResult(
            svg_data=animated_svg,
            method=config.method,
            element_count=elem_count,
            animation_time_ms=int((time.time() - start) * 1000),
            lottie_json=lottie_json,
        )

    @classmethod
    def get_presets(cls) -> Dict[str, dict]:
        """Get available animation presets."""
        return {
            name: {
                "type": config.type.value,
                "method": config.method.value,
                "duration": config.duration,
                "description": {
                    "draw_stroke": "Animated stroke drawing effect — paths appear as if being drawn",
                    "fade_in": "Elements fade in sequentially with a slight upward motion",
                    "color_cycle": "Colors cycle through a palette continuously",
                    "pulse": "Gentle pulsing scale effect on each element",
                }.get(name, ""),
            }
            for name, config in cls.PRESETS.items()
        }
