"""Edge detection service for image enhancement."""

import logging
from typing import Literal, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class EdgeDetector:
    """
    Edge detection service for improving vectorization quality.

    Supports multiple edge detection algorithms:
    - Canny: Best for most images (balanced sensitivity)
    - Sobel: Good for gradients
    - Laplacian: Detects zero crossings
    - Scharr: Improved Sobel operator
    """

    def __init__(self):
        self.methods = {
            "canny": self._canny_edge_detection,
            "sobel": self._sobel_edge_detection,
            "laplacian": self._laplacian_edge_detection,
            "scharr": self._scharr_edge_detection,
        }

    def detect_edges(
        self,
        image: np.ndarray,
        method: Literal["canny", "sobel", "laplacian", "scharr"] = "canny",
        **kwargs,
    ) -> np.ndarray:
        """
        Detect edges in an image.

        Args:
            image: Input image (BGR or grayscale)
            method: Edge detection algorithm
            **kwargs: Additional parameters for specific methods

        Returns:
            Edge map (grayscale image)
        """
        if method not in self.methods:
            raise ValueError(f"Unknown edge detection method: {method}")

        logger.debug(f"Detecting edges using {method} method")
        return self.methods[method](image, **kwargs)

    def _canny_edge_detection(
        self,
        image: np.ndarray,
        sigma: float = 1.0,
        threshold1: Optional[int] = None,
        threshold2: Optional[int] = None,
    ) -> np.ndarray:
        """
        Canny edge detection.

        Args:
            image: Input image
            sigma: Gaussian blur sigma (for automatic threshold calculation)
            threshold1: Lower threshold (auto-calculated if None)
            threshold2: Upper threshold (auto-calculated if None)

        Returns:
            Edge map
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Auto-calculate thresholds if not provided
        if threshold1 is None or threshold2 is None:
            median = np.median(gray)
            threshold1 = int(max(0, (1.0 - sigma) * median))
            threshold2 = int(min(255, (1.0 + sigma) * median))

        edges = cv2.Canny(gray, threshold1, threshold2)
        return edges

    def _sobel_edge_detection(
        self,
        image: np.ndarray,
        ksize: int = 3,
        scale: float = 1.0,
        delta: float = 0.0,
    ) -> np.ndarray:
        """
        Sobel edge detection.

        Args:
            image: Input image
            ksize: Kernel size (must be 1, 3, 5, or 7)
            scale: Scale factor
            delta: Delta value

        Returns:
            Edge map
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Calculate gradients
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=ksize, scale=scale, delta=delta)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=ksize, scale=scale, delta=delta)

        # Combine gradients
        magnitude = np.sqrt(sobelx**2 + sobely**2)

        # Normalize to 0-255
        magnitude = np.uint8(np.clip(magnitude, 0, 255))

        return magnitude

    def _laplacian_edge_detection(
        self,
        image: np.ndarray,
        ksize: int = 3,
    ) -> np.ndarray:
        """
        Laplacian edge detection.

        Args:
            image: Input image
            ksize: Kernel size (must be odd)

        Returns:
            Edge map
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=ksize)

        # Take absolute value and normalize
        laplacian = np.uint8(np.absolute(laplacian))

        return laplacian

    def _scharr_edge_detection(
        self,
        image: np.ndarray,
        scale: float = 1.0,
        delta: float = 0.0,
    ) -> np.ndarray:
        """
        Scharr edge detection (improved Sobel).

        Args:
            image: Input image
            scale: Scale factor
            delta: Delta value

        Returns:
            Edge map
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Calculate gradients using Scharr
        scharrx = cv2.Scharr(gray, cv2.CV_64F, 1, 0, scale=scale, delta=delta)
        scharry = cv2.Scharr(gray, cv2.CV_64F, 0, 1, scale=scale, delta=delta)

        # Combine gradients
        magnitude = np.sqrt(scharrx**2 + scharry**2)

        # Normalize to 0-255
        magnitude = np.uint8(np.clip(magnitude, 0, 255))

        return magnitude

    def enhance_edges(
        self,
        image: np.ndarray,
        edge_map: np.ndarray,
        weight: float = 0.3,
    ) -> np.ndarray:
        """
        Blend edge map with original image for enhancement.

        Args:
            image: Original image
            edge_map: Edge map from edge detection
            weight: Weight of edge map (0-1)

        Returns:
            Enhanced image
        """
        # Ensure edge_map is same size as image
        if edge_map.shape[:2] != image.shape[:2]:
            edge_map = cv2.resize(edge_map, (image.shape[1], image.shape[0]))

        # Convert edge map to 3 channels if needed
        if len(image.shape) == 3 and len(edge_map.shape) == 2:
            edge_map = cv2.cvtColor(edge_map, cv2.COLOR_GRAY2BGR)

        # Blend
        enhanced = cv2.addWeighted(image, 1.0, edge_map, weight, 0)

        return enhanced

    def detect_contours(
        self,
        edge_map: np.ndarray,
        mode: int = cv2.RETR_EXTERNAL,
        method: int = cv2.CHAIN_APPROX_SIMPLE,
        min_area: float = 100.0,
    ) -> Tuple[list, np.ndarray]:
        """
        Detect contours from edge map.

        Args:
            edge_map: Binary edge image
            mode: Contour retrieval mode
            method: Contour approximation method
            min_area: Minimum contour area to keep

        Returns:
            Tuple of (contours, hierarchy)
        """
        contours, hierarchy = cv2.findContours(edge_map, mode, method)

        # Filter by area
        filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) >= min_area]

        return filtered_contours, hierarchy

    def get_edge_statistics(self, edge_map: np.ndarray) -> dict:
        """Get statistics about edge map."""
        total_pixels = edge_map.size
        edge_pixels = np.count_nonzero(edge_map)
        edge_density = edge_pixels / total_pixels if total_pixels > 0 else 0

        return {
            "total_pixels": total_pixels,
            "edge_pixels": edge_pixels,
            "edge_density": round(edge_density, 4),
            "mean_intensity": round(float(np.mean(edge_map)), 2),
            "max_intensity": int(np.max(edge_map)),
        }

    def compare_methods(self, image: np.ndarray) -> dict:
        """Compare different edge detection methods."""
        results = {}

        for method in ["canny", "sobel", "laplacian", "scharr"]:
            try:
                edge_map = self.detect_edges(image, method)
                stats = self.get_edge_statistics(edge_map)
                results[method] = stats
            except Exception as e:
                results[method] = {"error": str(e)}

        return results
