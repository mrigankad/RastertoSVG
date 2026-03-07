"""Core conversion service with preprocessing integration."""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from app.services.preprocessor import Preprocessor, ThresholdMethod, DitherMethod
from app.services.vtracer_engine import VTracerEngine
from app.services.potrace_engine import PotraceEngine
from app.services.optimizer import SVGOptimizer
from app.services.edge_detector import EdgeDetector
from app.services.line_smoother import LineSmoother

logger = logging.getLogger(__name__)


class Converter:
    """
    Main conversion service that routes to appropriate engines.
    
    Supports three quality modes with distinct pipelines:
    - Fast: No preprocessing, direct conversion
    - Standard: Color reduction + bilateral denoise + CLAHE contrast + standard optimization
    - High: Standard + NLM denoise + unsharp mask + edge enhancement + aggressive optimization + line smoothing
    """

    def __init__(self):
        self.preprocessor = Preprocessor()
        self.vtracer = VTracerEngine()
        self.potrace = PotraceEngine()
        self.optimizer = SVGOptimizer()
        self.edge_detector = EdgeDetector()
        self.line_smoother = LineSmoother()
        self._ml_converter = None  # Lazy-loaded ML enhancement service

    def convert(
        self,
        input_path: str,
        output_path: str,
        image_type: Literal["auto", "color", "monochrome"] = "auto",
        quality_mode: Literal["fast", "standard", "high"] = "standard",
    ) -> Dict[str, Any]:
        """
        Convert raster image to SVG.

        Args:
            input_path: Path to input image
            output_path: Path for output SVG
            image_type: auto, color, or monochrome
            quality_mode: fast, standard, or high

        Returns:
            Dictionary with conversion results and metadata
        """
        start_time = time.time()
        preprocessing_time = 0
        conversion_time = 0
        optimization_time = 0

        input_path_obj = Path(input_path)

        # Validate input
        if not input_path_obj.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Check file size
        file_size = input_path_obj.stat().st_size
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            raise ValueError("File too large (max 50MB)")

        # Auto-detect image type if needed
        if image_type == "auto":
            image_type = self._detect_image_type(input_path)
            logger.info(f"Auto-detected image type: {image_type}")

        # Load image
        try:
            img = cv2.imread(input_path)
            if img is None:
                raise ValueError(f"Could not load image: {input_path}")
            original_shape = img.shape
        except Exception as e:
            raise ValueError(f"Could not load image: {e}")

        # Apply preprocessing (skip for fast mode)
        ml_steps_applied = []
        ml_params = {}
        if quality_mode != "fast":
            logger.info(f"Applying {quality_mode} preprocessing")
            prep_start = time.time()
            img = self.preprocessor.preprocess_array(img, image_type, quality_mode)
            preprocessing_time = time.time() - prep_start
            logger.info(f"Preprocessing completed in {preprocessing_time:.3f}s")

        # Apply ML enhancement (high mode only)
        if quality_mode == "high":
            img, ml_params, ml_steps_applied = self._apply_ml_enhancement(img, image_type)

        # Convert based on image type
        conv_start = time.time()
        if image_type == "color":
            result = self._convert_color(img, output_path, quality_mode, ml_params)
        else:
            result = self._convert_monochrome(img, output_path, quality_mode, ml_params)
        conversion_time = time.time() - conv_start

        # Apply SVG optimization
        opt_start = time.time()
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            # Choose optimization level
            opt_level = {
                "fast": "light",
                "standard": "standard",
                "high": "aggressive",
            }.get(quality_mode, "standard")
            
            optimized = self.optimizer.optimize(svg_content, level=opt_level)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(optimized)
            
            optimization_time = time.time() - opt_start
            result["optimization_applied"] = True
            result["optimization_level"] = opt_level
            
        except Exception as e:
            logger.warning(f"SVG optimization failed: {e}")
            result["optimization_applied"] = False

        # Add metadata
        result.update({
            "input_path": str(input_path),
            "output_path": str(output_path),
            "image_type": image_type,
            "quality_mode": quality_mode,
            "original_shape": original_shape,
            "file_size_bytes": file_size,
            "preprocessing_time": preprocessing_time,
            "conversion_time": conversion_time,
            "optimization_time": optimization_time,
            "processing_time": time.time() - start_time,
        })

        # Add preprocessing info
        if quality_mode == "standard":
            result["preprocessing_applied"] = [
                "color_reduction",
                "bilateral_denoise",
                "clahe_contrast"
            ]
        elif quality_mode == "high":
            result["preprocessing_applied"] = [
                "color_reduction",
                "nlm_denoise",
                "clahe_contrast",
                "unsharp_mask",
                "edge_enhancement",
                "aggressive_svg_optimization"
            ] + ml_steps_applied

        # Validate output
        output_path_obj = Path(output_path)
        if output_path_obj.exists():
            result["output_size_bytes"] = output_path_obj.stat().st_size
            if result["output_size_bytes"] > 0:
                result["compression_ratio"] = file_size / result["output_size_bytes"]

        return result

    def _detect_image_type(self, image_path: str) -> Literal["color", "monochrome"]:
        """
        Detect if image is color or monochrome.

        Args:
            image_path: Path to image

        Returns:
            "color" or "monochrome"
        """
        try:
            # Load with PIL for mode detection
            img = Image.open(image_path)

            # Check mode
            if img.mode == '1':  # 1-bit bilevel
                return "monochrome"
            elif img.mode == 'L':  # Grayscale
                return "monochrome"
            elif img.mode in ('RGB', 'RGBA', 'P'):
                # Check if it's actually grayscale disguised as RGB
                if self._is_grayscale_image(img):
                    return "monochrome"
                return "color"
            else:
                # For other modes, convert and check
                rgb_img = img.convert('RGB')
                if self._is_grayscale_image(rgb_img):
                    return "monochrome"
                return "color"

        except Exception as e:
            logger.warning(f"Could not detect image type: {e}, defaulting to color")
            return "color"

    def _is_grayscale_image(self, img: Image.Image) -> bool:
        """Check if an RGB image is actually grayscale."""
        # Sample pixels to check (faster than checking all)
        width, height = img.size
        sample_size = min(1000, width * height)

        import random
        random.seed(42)  # For reproducibility

        img_rgb = img.convert('RGB')
        pixels = list(img_rgb.getdata())

        # Sample pixels
        if len(pixels) > sample_size:
            pixels = random.sample(pixels, sample_size)

        # Check if R == G == B for all sampled pixels
        for r, g, b in pixels:
            if r != g or g != b:
                return False

        return True

    def _convert_color(
        self,
        image: np.ndarray,
        output_path: str,
        quality_mode: str,
        ml_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Use VTracer for color images."""
        logger.info(f"Converting color image with VTracer ({quality_mode} mode)")

        # Convert OpenCV to PIL for VTracer
        pil_img = self.preprocessor._cv2_to_pil(image)

        # Adjust VTracer parameters based on quality mode
        if quality_mode == "fast":
            result = self.vtracer.convert_pillow(
                pil_img,
                output_path,
                color_precision=16,
                max_iterations=10,
                filter_speckle=4,
            )
        elif quality_mode == "standard":
            result = self.vtracer.convert_pillow(
                pil_img,
                output_path,
                color_precision=32,
                max_iterations=20,
                filter_speckle=2,
            )
        else:  # high
            # Merge ML parameters with base high mode parameters
            params = {
                'color_precision': 64,
                'max_iterations': 30,
                'filter_speckle': 1,
                'path_precision': 10,
                'hierarchical': True,
            }
            if ml_params:
                # Override with ML-predicted values
                params.update({k: v for k, v in ml_params.items() if k in params})

            result = self.vtracer.convert_pillow(pil_img, output_path, **params)

        return result

    def _convert_monochrome(
        self,
        image: np.ndarray,
        output_path: str,
        quality_mode: str,
        ml_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Use Potrace for monochrome images."""
        logger.info(f"Converting monochrome image with Potrace ({quality_mode} mode)")

        # Ensure image is grayscale for Potrace
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            pil_img = Image.fromarray(gray)
        else:
            pil_img = Image.fromarray(image)

        # Adjust Potrace parameters based on quality mode
        if quality_mode == "fast":
            result = self.potrace.convert_pillow(
                pil_img,
                output_path,
                alphamax=1.0,
                turdsize=4,
                opticurve=False,
            )
        elif quality_mode == "standard":
            result = self.potrace.convert_pillow(
                pil_img,
                output_path,
                alphamax=1.0,
                turdsize=2,
                opticurve=True,
                opttolerance=0.2,
            )
        else:  # high
            # Merge ML parameters with base high mode parameters
            params = {
                'alphamax': 0.5,
                'turdsize': 1,
                'opticurve': True,
                'opttolerance': 0.1,
                'turnpolicy': "minority",
            }
            if ml_params:
                # Override with ML-predicted values
                params.update({k: v for k, v in ml_params.items() if k in params})

            result = self.potrace.convert_pillow(pil_img, output_path, **params)

        return result

    def _apply_ml_enhancement(
        self,
        image: np.ndarray,
        image_type: str
    ) -> Tuple[np.ndarray, Dict[str, Any], List[str]]:
        """Apply multi-tier ML enhancement for high quality mode.

        Lazy-loads MLConverter on first use. Gracefully falls back if ML unavailable.

        Args:
            image: Input image (BGR)
            image_type: "color" or "monochrome"

        Returns:
            Tuple of (enhanced_image, param_overrides, steps_applied)
        """
        if self._ml_converter is None:
            try:
                from app.services.ml_converter import MLConverter
                self._ml_converter = MLConverter()
                logger.info("Loaded ML enhancement service")
            except ImportError:
                logger.warning("MLConverter not available (sklearn not installed)")
                return image, {}, []
            except Exception as e:
                logger.warning(f"Failed to load MLConverter: {e}")
                return image, {}, []

        try:
            enhanced_image, param_overrides, steps_applied = self._ml_converter.enhance_for_vectorization(
                image, image_type
            )
            logger.info(f"ML enhancement applied: {steps_applied}")
            return enhanced_image, param_overrides, steps_applied
        except Exception as e:
            logger.warning(f"ML enhancement failed, continuing without ML: {e}")
            return image, {}, []

    def get_engine_info(self) -> Dict[str, Any]:
        """Get information about available engines."""
        return {
            "vtracer": {
                "available": self.vtracer.is_available(),
                "name": self.vtracer.name,
                "formats": list(self.vtracer.supported_formats),
            },
            "potrace": {
                "available": self.potrace.is_available(),
                "name": self.potrace.name,
                "version": self.potrace.get_version(),
                "formats": list(self.potrace.supported_formats),
            },
        }

    def validate_input(self, image_path: str) -> Dict[str, Any]:
        """Validate input file and return info."""
        path = Path(image_path)

        if not path.exists():
            return {"valid": False, "error": "File not found"}

        try:
            # Get PIL info
            img = Image.open(image_path)
            info = {
                "valid": True,
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
                "width": img.width,
                "height": img.height,
                "file_size": path.stat().st_size,
            }

            # Add more details if possible
            try:
                info["dpi"] = img.info.get("dpi")
            except:
                pass

            return info

        except Exception as e:
            return {"valid": False, "error": str(e)}

    def get_supported_formats(self) -> list:
        """Get list of supported input formats."""
        return ["PNG", "JPG", "JPEG", "BMP", "TIFF", "GIF", "WEBP"]
