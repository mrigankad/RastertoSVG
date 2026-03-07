"""SVG optimization and cleanup service."""

import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from xml.dom import minidom

import scour
from scour import scour as scour_module

logger = logging.getLogger(__name__)


class SVGOptimizer:
    """
    SVG optimization and cleanup service.

    Supports three optimization levels:
    - Light: Remove metadata only
    - Standard: Light + simplify paths + remove unused defs
    - Aggressive: Standard + color optimization + aggressive simplification
    """

    def __init__(self):
        self.optimization_levels = {
            "light": self._optimize_light,
            "standard": self._optimize_standard,
            "aggressive": self._optimize_aggressive,
        }

    def optimize(
        self,
        svg_content: str,
        level: Literal["light", "standard", "aggressive"] = "standard",
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Optimize SVG content.

        Args:
            svg_content: Raw SVG content
            level: Optimization level
            options: Additional optimization options

        Returns:
            Optimized SVG content
        """
        if level not in self.optimization_levels:
            raise ValueError(f"Invalid optimization level: {level}")

        logger.info(f"Optimizing SVG with level: {level}")
        original_size = len(svg_content)

        # Run optimization
        optimized = self.optimization_levels[level](svg_content, options or {})

        final_size = len(optimized)
        reduction = (1 - final_size / original_size) * 100 if original_size > 0 else 0

        logger.info(
            f"Optimized SVG: {original_size} → {final_size} bytes ({reduction:.1f}% reduction)"
        )

        return optimized

    def _optimize_light(self, svg_content: str, options: Dict[str, Any]) -> str:
        """Light optimization - remove metadata only."""
        # Remove comments
        svg_content = re.sub(r"<!--.*?-->", "", svg_content, flags=re.DOTALL)

        # Remove unnecessary whitespace between tags
        svg_content = re.sub(r">\s+<", "><", svg_content)

        return svg_content.strip()

    def _optimize_standard(self, svg_content: str, options: Dict[str, Any]) -> str:
        """Standard optimization - use Scour."""
        # First apply light optimization
        svg_content = self._optimize_light(svg_content, options)

        # Use Scour for standard optimization
        try:
            # Create Scour options
            scour_options = scour_module.SanitizeOptions()
            scour_options.enable_viewboxing = True
            scour_options.strip_comments = True
            scour_options.strip_ids = True
            scour_options.shorten_ids = True
            scour_options.remove_metadata = True
            scour_options.remove_descriptive_elements = True
            scour_options.strip_xml_prolog = True
            scour_options.group_collapsing = True
            scour_options.create_groups = True
            scour_options.keep_editor_data = False
            scour_options.keep_defs = False
            scour_options.renderer_workaround = True
            scour_options.strip_xml_space_attribute = True

            # Run Scour
            optimized = scour_module.scour_string(svg_content, scour_options)
            return optimized
        except Exception as e:
            logger.warning(f"Scour optimization failed: {e}, returning light-optimized content")
            return svg_content

    def _optimize_aggressive(self, svg_content: str, options: Dict[str, Any]) -> str:
        """Aggressive optimization - standard + additional optimizations."""
        # First apply standard optimization
        svg_content = self._optimize_standard(svg_content, options)

        # Round numbers to reduce precision
        precision = options.get("precision", 2)
        svg_content = self._round_numbers(svg_content, precision)

        # Optimize colors
        svg_content = self._optimize_colors(svg_content)

        # Simplify paths more aggressively
        tolerance = options.get("simplify_tolerance", 0.5)
        svg_content = self._simplify_paths(svg_content, tolerance)

        # Remove unused defs
        svg_content = self._remove_unused_defs(svg_content)

        # Minify
        svg_content = self._minify(svg_content)

        return svg_content

    def _round_numbers(self, svg_content: str, precision: int = 2) -> str:
        """Round numeric values in SVG to reduce file size."""
        import re

        def round_match(match):
            try:
                num = float(match.group(0))
                return str(round(num, precision))
            except ValueError:
                return match.group(0)

        # Match decimal numbers
        pattern = r"-?\d+\.\d+"
        return re.sub(pattern, round_match, svg_content)

    def _optimize_colors(self, svg_content: str) -> str:
        """Optimize color declarations in SVG."""
        # Convert rgb() to hex
        import re

        def rgb_to_hex(match):
            try:
                r, g, b = map(int, match.groups())
                return f"#{r:02x}{g:02x}{b:02x}"
            except:
                return match.group(0)

        svg_content = re.sub(
            r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",
            rgb_to_hex,
            svg_content,
            flags=re.IGNORECASE,
        )

        # Convert 6-digit hex to 3-digit where possible
        def shorten_hex(match):
            hex_color = match.group(1)
            if len(hex_color) == 6:
                if (
                    hex_color[0] == hex_color[1]
                    and hex_color[2] == hex_color[3]
                    and hex_color[4] == hex_color[5]
                ):
                    return f"#{hex_color[0]}{hex_color[2]}{hex_color[4]}"
            return match.group(0)

        svg_content = re.sub(r"#([0-9a-fA-F]{6})", shorten_hex, svg_content)

        return svg_content

    def _simplify_paths(self, svg_content: str, tolerance: float = 0.5) -> str:
        """Simplify SVG paths using RDP algorithm."""
        try:
            from xml.etree import ElementTree as ET

            # Parse SVG
            root = ET.fromstring(svg_content)

            # Find all path elements
            for path in root.iter("{http://www.w3.org/2000/svg}path"):
                d = path.get("d", "")
                if d:
                    simplified = self._simplify_path_data(d, tolerance)
                    path.set("d", simplified)

            # Convert back to string
            return ET.tostring(root, encoding="unicode")
        except Exception as e:
            logger.warning(f"Path simplification failed: {e}")
            return svg_content

    def _simplify_path_data(self, path_data: str, tolerance: float) -> str:
        """Simplify SVG path data using RDP algorithm."""
        # This is a simplified version - in production, use a proper SVG path parser
        # For now, just remove redundant commands
        import re

        # Remove redundant spaces and commands
        path_data = re.sub(r"\s+", " ", path_data)
        path_data = re.sub(r"\s*,\s*", ",", path_data)

        return path_data.strip()

    def _remove_unused_defs(self, svg_content: str) -> str:
        """Remove unused definitions from SVG."""
        try:
            from xml.etree import ElementTree as ET

            root = ET.fromstring(svg_content)

            # Get all IDs that are referenced
            referenced_ids = set()
            for elem in root.iter():
                for attr in ["href", "xlink:href", "url"]:
                    val = elem.get(attr, "")
                    if val.startswith("#"):
                        referenced_ids.add(val[1:])
                    elif "url(#" in val:
                        # Extract ID from url(#id)
                        import re

                        match = re.search(r"url\(#([^)]+)\)", val)
                        if match:
                            referenced_ids.add(match.group(1))

            # Remove unused defs
            for defs in root.iter("{http://www.w3.org/2000/svg}defs"):
                for child in list(defs):
                    elem_id = child.get("id")
                    if elem_id and elem_id not in referenced_ids:
                        defs.remove(child)

            return ET.tostring(root, encoding="unicode")
        except Exception as e:
            logger.warning(f"Removing unused defs failed: {e}")
            return svg_content

    def _minify(self, svg_content: str) -> str:
        """Minify SVG by removing unnecessary whitespace."""
        import re

        # Remove whitespace between tags
        svg_content = re.sub(r">\s+<", "><", svg_content)

        # Remove leading/trailing whitespace in text content
        svg_content = re.sub(r">\s+", ">", svg_content)
        svg_content = re.sub(r"\s+<", "<", svg_content)

        return svg_content.strip()

    def optimize_with_svgo(self, svg_content: str, config: Optional[Dict] = None) -> str:
        """
        Optimize SVG using SVGO (requires Node.js and SVGO installed).

        Args:
            svg_content: SVG content to optimize
            config: SVGO configuration

        Returns:
            Optimized SVG content
        """
        try:
            # Create temp files
            with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as input_file:
                input_file.write(svg_content)
                input_path = input_file.name

            output_path = input_path.replace(".svg", ".optimized.svg")

            # Run SVGO
            cmd = ["svgo", input_path, "-o", output_path]

            if config:
                # Write config to temp file
                import json

                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                ) as config_file:
                    json.dump(config, config_file)
                    cmd.extend(["--config", config_file.name])

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Read optimized content
            with open(output_path, "r") as f:
                optimized = f.read()

            # Cleanup
            Path(input_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)

            return optimized

        except FileNotFoundError:
            logger.warning("SVGO not found, falling back to Python optimization")
            return self.optimize(svg_content, "aggressive")
        except subprocess.CalledProcessError as e:
            logger.error(f"SVGO failed: {e.stderr}")
            return svg_content

    def get_stats(self, svg_content: str) -> Dict[str, Any]:
        """Get statistics about SVG content."""
        try:
            from xml.etree import ElementTree as ET

            root = ET.fromstring(svg_content)

            # Count elements
            element_counts = {}
            total_elements = 0
            for elem in root.iter():
                tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                element_counts[tag] = element_counts.get(tag, 0) + 1
                total_elements += 1

            # Get file size
            size_bytes = len(svg_content.encode("utf-8"))

            # Get dimensions
            width = root.get("width", "unknown")
            height = root.get("height", "unknown")
            viewbox = root.get("viewBox", "unknown")

            return {
                "size_bytes": size_bytes,
                "size_kb": round(size_bytes / 1024, 2),
                "total_elements": total_elements,
                "element_counts": element_counts,
                "width": width,
                "height": height,
                "viewbox": viewbox,
            }
        except Exception as e:
            logger.error(f"Failed to get SVG stats: {e}")
            return {"error": str(e)}

    def compare_optimizations(self, svg_content: str) -> Dict[str, Any]:
        """Compare different optimization levels on the same SVG."""
        results = {}
        original_size = len(svg_content)

        for level in ["light", "standard", "aggressive"]:
            try:
                optimized = self.optimize(svg_content, level)
                size = len(optimized)
                reduction = (1 - size / original_size) * 100 if original_size > 0 else 0

                results[level] = {
                    "size_bytes": size,
                    "size_kb": round(size / 1024, 2),
                    "reduction_percent": round(reduction, 2),
                    "content": optimized if size < 10000 else None,  # Only include for small files
                }
            except Exception as e:
                results[level] = {"error": str(e)}

        return {
            "original_size_bytes": original_size,
            "original_size_kb": round(original_size / 1024, 2),
            "optimizations": results,
        }
