"""VTracer integration for color image vectorization."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
from PIL import Image
import vtracer

logger = logging.getLogger(__name__)


class VTracerEngine:
    """Wrapper for VTracer color image vectorization."""

    def __init__(self):
        self.name = "vtracer"
        self.supported_formats = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}

    def convert(
        self,
        image_path: str,
        output_path: str,
        color_precision: int = 32,
        hierarchical: bool = True,
        mode: str = "splice",  # splice, stack, or cluster
        filter_speckle: int = 4,
        color_sampling_interval: int = 10,
        layer_difference: int = 10,
        corner_threshold: int = 60,
        length_threshold: float = 4.0,
        max_iterations: int = 20,
        splice_threshold: int = 45,
        path_precision: int = 8,
    ) -> Dict[str, Any]:
        """
        Convert a color image to SVG using VTracer.

        Args:
            image_path: Path to input image
            output_path: Path for output SVG
            color_precision: Number of colors to extract (2-256)
            hierarchical: Enable hierarchical grouping
            mode: Color clustering mode (splice, stack, cluster)
            filter_speckle: Despeckle filter radius (0-16)
            color_sampling_interval: Color sampling interval
            layer_difference: Layer difference threshold
            corner_threshold: Corner detection threshold (0-120)
            length_threshold: Length threshold for path simplification
            max_iterations: Maximum iterations for optimization
            splice_threshold: Splice threshold
            path_precision: Decimal precision for path coordinates

        Returns:
            Dictionary with conversion results
        """
        input_path = Path(image_path)
        out_path = Path(output_path)

        # Validate input
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {image_path}")

        if input_path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Unsupported format: {input_path.suffix}")

        # Ensure output directory exists
        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"Running VTracer on: {image_path}")
            logger.info(f"Color precision: {color_precision}, Mode: {mode}")

            # Use VTracer Python API
            # Convert boolean to string for VTracer API
            vtracer.convert_image_to_svg_py(
                str(input_path),
                str(out_path),
                colormode=None,
                hierarchical="true" if hierarchical else "false",
                mode=mode,
                filter_speckle=filter_speckle,
                color_precision=color_precision,
                layer_difference=layer_difference,
                corner_threshold=corner_threshold,
                length_threshold=length_threshold,
                max_iterations=max_iterations,
                splice_threshold=splice_threshold,
                path_precision=path_precision,
            )

            # Get output file info
            output_size = out_path.stat().st_size if out_path.exists() else 0

            logger.info(f"VTracer conversion successful. Output size: {output_size} bytes")

            return {
                "engine": "vtracer",
                "input_path": str(input_path),
                "output_path": str(out_path),
                "color_precision": color_precision,
                "mode": mode,
                "output_size": output_size,
                "success": True,
            }

        except Exception as e:
            logger.error(f"VTracer failed: {e}")
            raise RuntimeError(f"VTracer conversion failed: {e}")

    def convert_pillow(
        self,
        image: Image.Image,
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Convert a PIL Image object to SVG using VTracer.

        Args:
            image: PIL Image object
            output_path: Path for output SVG
            **kwargs: Additional options passed to convert()

        Returns:
            Dictionary with conversion results
        """
        # Save to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            temp_path = tmp.name
            image.save(temp_path, "PNG")

        try:
            result = self.convert(temp_path, output_path, **kwargs)
            return result
        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

    def is_available(self) -> bool:
        """Check if VTracer is installed and available."""
        try:
            # Check if vtracer Python API is available
            import vtracer
            hasattr(vtracer, 'convert_image_to_svg_py')
            return True
        except ImportError:
            return False
