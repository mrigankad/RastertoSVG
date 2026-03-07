"""Potrace integration for monochrome image vectorization."""

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, Literal, Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class PotraceEngine:
    """Wrapper for Potrace bitmap tracing."""

    def __init__(self):
        self.name = "potrace"
        self.supported_formats = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".pbm", ".pgm", ".ppm"}

    def convert(
        self,
        image_path: str,
        output_path: str,
        threshold: Optional[int] = None,
        alphamax: float = 1.0,
        turnpolicy: Literal[
            "black", "white", "left", "right", "minority", "majority", "random"
        ] = "minority",
        turdsize: int = 2,
        opticurve: bool = True,
        opttolerance: float = 0.2,
        blacklevel: float = 0.5,
        invert: bool = False,
    ) -> Dict[str, Any]:
        """
        Convert a monochrome image to SVG using Potrace.

        Args:
            image_path: Path to input image
            output_path: Path for output SVG
            threshold: Binarization threshold (0-255), None for auto
            alphamax: Corner detection threshold (0-1.334)
            turnpolicy: Policy for ambiguous turns
            turdsize: Suppress speckles smaller than this
            opticurve: Enable curve optimization
            opttolerance: Optimization tolerance
            blacklevel: Black/white cutoff (0-1)
            invert: Invert the image

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

        # Preprocess: Convert to PNM format (Potrace's preferred input)
        try:
            img = Image.open(input_path)

            # Convert to grayscale
            if img.mode != "L":
                img = img.convert("L")

            # Apply threshold if specified
            if threshold is not None:
                img = img.point(lambda x: 0 if x < threshold else 255, "1")
            else:
                # Auto threshold using Otsu's method
                img = self._auto_threshold(img)

            # Invert if requested
            if invert:
                img = Image.eval(img, lambda x: 255 - x)

            # Save as PNM for Potrace
            temp_pnm = out_path.with_suffix(".pnm")
            img.save(temp_pnm, "PPM")

        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            raise RuntimeError(f"Image preprocessing failed: {e}")

        try:
            # Build Potrace command
            cmd = [
                "potrace",
                "-s",  # SVG output
                "-o",
                str(out_path),
                "-a",
                str(alphamax),
                "-t",
                str(turdsize),
                "--turnpolicy",
                turnpolicy,
                "-O",
                str(opttolerance),
                "-k",
                str(blacklevel),
            ]

            if opticurve:
                cmd.append(
                    "-n"
                )  # No curve optimization = False, so we don't add -n if opticurve=True
            else:
                cmd.append(
                    "-O"
                )  # Actually -O controls opttolerance, -n disables curve optimization
                cmd.append(str(opttolerance))

            if invert:
                cmd.append("-i")

            cmd.append(str(temp_pnm))

            logger.info(f"Running Potrace: {' '.join(cmd)}")

            # Execute Potrace
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            if result.stderr:
                logger.warning(f"Potrace stderr: {result.stderr}")

            # Get output file info
            output_size = out_path.stat().st_size if out_path.exists() else 0

            return {
                "engine": "potrace",
                "input_path": str(input_path),
                "output_path": str(out_path),
                "alphamax": alphamax,
                "turnpolicy": turnpolicy,
                "output_size": output_size,
                "success": True,
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Potrace failed: {e.stderr}")
            raise RuntimeError(f"Potrace conversion failed: {e.stderr}")
        except FileNotFoundError:
            logger.error("Potrace not found. Please install potrace.")
            raise RuntimeError(
                "Potrace not found. Install with: apt-get install potrace (Linux) or brew install potrace (macOS)"
            )
        finally:
            # Clean up temp file
            temp_pnm.unlink(missing_ok=True)

    def convert_pillow(self, image: Image.Image, output_path: str, **kwargs) -> Dict[str, Any]:
        """
        Convert a PIL Image object to SVG using Potrace.

        Args:
            image: PIL Image object
            output_path: Path for output SVG
            **kwargs: Additional options passed to convert()

        Returns:
            Dictionary with conversion results
        """
        import tempfile

        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            temp_path = tmp.name
            # Convert to grayscale for Potrace
            if image.mode != "L":
                image = image.convert("L")
            image.save(temp_path, "PNG")

        try:
            result = self.convert(temp_path, output_path, **kwargs)
            return result
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def _auto_threshold(self, image: Image.Image) -> Image.Image:
        """Apply automatic threshold using Otsu's method."""
        import cv2

        # Convert PIL to numpy array
        img_array = np.array(image)

        # Apply Otsu's thresholding
        _, thresh = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Convert back to PIL
        return Image.fromarray(thresh)

    def is_available(self) -> bool:
        """Check if Potrace is installed and available."""
        try:
            subprocess.run(["potrace", "-v"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_version(self) -> str:
        """Get Potrace version."""
        try:
            result = subprocess.run(["potrace", "-v"], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except:
            return "unknown"
