"""ONNX-based image enhancement for Tier 3 quality (super-resolution and edge enhancement).

Provides ONNX Runtime-based image enhancements:
- Super-resolution using EDSR model for small images
- Edge enhancement for better path tracing
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ONNXEnhancer:
    """ONNX Runtime-based image enhancement service.

    Tier 3 enhancement provides:
    - Super-resolution (EDSR 3x) for images < 256px on shortest side
    - Edge enhancement for sharper edges in vectorization
    """

    CACHE_DIR = Path.home() / ".cache" / "raster-svg" / "models"
    EDSR_URL = "https://github.com/onnx/models/raw/main/vision/super_resolution/edsr/model/EDSR_x3.onnx"

    def __init__(self):
        """Initialize ONNX enhancer (lazy-loads session on first use)."""
        self._session: Optional[Any] = None
        self._ort_available = False

        try:
            import onnxruntime
            self._ort_available = True
            logger.debug("onnxruntime is available")
        except ImportError:
            logger.debug("onnxruntime not installed, Tier 3 will be unavailable")

    @staticmethod
    def is_available() -> bool:
        """Check if ONNXRuntime is available.

        Returns:
            True if onnxruntime is installed
        """
        try:
            import onnxruntime
            return True
        except ImportError:
            return False

    def _get_or_download_model(self, model_path: Path) -> Optional[Path]:
        """Get EDSR model, downloading if necessary.

        Args:
            model_path: Path where model should be stored

        Returns:
            Path to model file, or None if download fails
        """
        try:
            # Create cache directory
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

            # Return if already exists
            if model_path.exists():
                logger.debug(f"Using cached EDSR model: {model_path}")
                return model_path

            # Try to download
            logger.info("Downloading EDSR model for super-resolution...")
            try:
                import urllib.request
                urllib.request.urlretrieve(self.EDSR_URL, model_path)
                logger.info(f"Downloaded EDSR model to {model_path}")
                return model_path
            except Exception as e:
                logger.warning(f"Failed to download EDSR model: {e}")
                return None

        except Exception as e:
            logger.warning(f"Error in model download: {e}")
            return None

    def _load_session(self) -> Optional[Any]:
        """Lazy-load ONNX Runtime session for EDSR.

        Returns:
            ONNX Runtime InferenceSession or None if unavailable
        """
        if self._session is not None:
            return self._session

        if not self._ort_available:
            logger.debug("onnxruntime not available, cannot load session")
            return None

        try:
            import onnxruntime
            from onnxruntime import InferenceSession, SessionOptions, GraphOptimizationLevel

            model_path = self.CACHE_DIR / "EDSR_x3.onnx"
            downloaded_path = self._get_or_download_model(model_path)

            if downloaded_path is None or not downloaded_path.exists():
                logger.warning("Could not obtain EDSR model, super-resolution unavailable")
                return None

            # Configure session for performance
            sess_options = SessionOptions()
            sess_options.graph_optimization_level = GraphOptimizationLevel.ORT_ENABLE_ALL

            self._session = InferenceSession(str(downloaded_path), sess_options=sess_options, providers=["CPUExecutionProvider"])
            logger.info("Loaded ONNX EDSR super-resolution model")
            return self._session

        except Exception as e:
            logger.warning(f"Failed to load ONNX session: {e}")
            return None

    def super_resolve(self, image: np.ndarray, scale: int = 3) -> np.ndarray:
        """Apply super-resolution using EDSR ONNX model.

        Only applies super-resolution to images with shortest side < 256px.
        Falls back to OpenCV interpolation if ONNX model unavailable.

        Args:
            image: Input image as numpy array (BGR format)
            scale: Upsampling scale (default 3x)

        Returns:
            Super-resolved image (or original if conditions not met)
        """
        try:
            h, w = image.shape[:2]
            min_side = min(h, w)

            # Skip if image already large enough
            if min_side >= 256:
                logger.debug(f"Image too large for super-resolution (min_side={min_side})")
                return image

            logger.info(f"Applying {scale}x super-resolution to {h}x{w} image")

            # Try ONNX EDSR
            session = self._load_session()
            if session is not None:
                try:
                    return self._super_resolve_onnx(image, session, scale)
                except Exception as e:
                    logger.warning(f"ONNX super-resolution failed: {e}, falling back to OpenCV")

            # Fallback to OpenCV interpolation
            return self._super_resolve_opencv(image, scale)

        except Exception as e:
            logger.warning(f"Super-resolution failed: {e}")
            return image

    def _super_resolve_onnx(self, image: np.ndarray, session: Any, scale: int) -> np.ndarray:
        """Apply super-resolution using ONNX EDSR model.

        Args:
            image: Input image as numpy array (BGR)
            session: ONNX Runtime InferenceSession
            scale: Upsampling scale

        Returns:
            Super-resolved image
        """
        try:
            # Convert BGR to RGB and normalize
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            rgb_image = rgb_image.astype(np.float32) / 255.0

            # Prepare input: add batch and channel dims, transpose to NCHW
            input_data = np.expand_dims(np.transpose(rgb_image, (2, 0, 1)), 0).astype(np.float32)

            # Get input/output names
            input_name = session.get_inputs()[0].name
            output_name = session.get_outputs()[0].name

            # Run inference
            result = session.run([output_name], {input_name: input_data})
            output = result[0]

            # Post-process: convert from NCHW to HWC and denormalize
            sr_image = np.squeeze(output)
            sr_image = np.transpose(sr_image, (1, 2, 0))
            sr_image = np.clip(sr_image * 255.0, 0, 255).astype(np.uint8)

            # Convert back to BGR
            sr_image = cv2.cvtColor(sr_image, cv2.COLOR_RGB2BGR)

            h, w = image.shape[:2]
            sr_h, sr_w = sr_image.shape[:2]
            logger.info(f"Super-resolved {h}x{w} to {sr_h}x{sr_w} using ONNX EDSR")

            return sr_image

        except Exception as e:
            logger.warning(f"ONNX super-resolution failed: {e}")
            raise

    def _super_resolve_opencv(self, image: np.ndarray, scale: int) -> np.ndarray:
        """Apply super-resolution using OpenCV interpolation (fallback).

        Args:
            image: Input image as numpy array (BGR)
            scale: Upsampling scale

        Returns:
            Upsampled image
        """
        try:
            h, w = image.shape[:2]
            new_h, new_w = h * scale, w * scale

            # Use Lanczos4 for best quality
            upsampled = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

            logger.info(f"Applied OpenCV super-resolution {h}x{w} to {new_h}x{new_w}")
            return upsampled

        except Exception as e:
            logger.warning(f"OpenCV super-resolution failed: {e}")
            raise

    def enhance_edges(self, image: np.ndarray) -> np.ndarray:
        """Enhance edges in image for better vectorization.

        Uses unsharp masking with optional CLAHE for edge sharpening.

        Args:
            image: Input image as numpy array (BGR)

        Returns:
            Edge-enhanced image
        """
        try:
            logger.info("Applying edge enhancement")

            # Convert to grayscale for edge detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Apply unsharp mask for edge enhancement
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            unsharp = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)

            # Apply CLAHE for contrast enhancement
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            clahe_enhanced = clahe.apply(unsharp)

            # Convert back to 3-channel and apply to original
            if image.ndim == 3:
                # Blend with original image using edge mask
                enhanced = image.copy().astype(np.float32)

                # Simple weighted blend based on edge strength
                edge_mask = cv2.Canny(gray, 100, 200).astype(np.float32) / 255.0
                edge_mask = cv2.GaussianBlur(edge_mask, (3, 3), 0)

                # Apply enhancement more strongly near edges
                for c in range(3):
                    enhanced[:, :, c] = enhanced[:, :, c] * (1 - 0.3 * edge_mask) + clahe_enhanced * (0.3 * edge_mask)

                result = np.clip(enhanced, 0, 255).astype(np.uint8)
            else:
                result = clahe_enhanced

            logger.debug("Edge enhancement complete")
            return result

        except Exception as e:
            logger.warning(f"Edge enhancement failed: {e}")
            return image
