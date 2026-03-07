"""Machine learning-based image enhancement and parameter prediction for vectorization.

Implements three tiers of ML enhancement:
- Tier 1 (sklearn): Feature extraction, image classification, parameter prediction
- Tier 2 (PyTorch + SAM): Semantic segmentation
- Tier 3 (ONNX): Super-resolution and edge enhancement
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import cv2
import numpy as np
from PIL import Image
from sklearn.cluster import MiniBatchKMeans
from sklearn.metrics import silhouette_score

logger = logging.getLogger(__name__)


class MLParamPredictor:
    """Feature extraction and parameter prediction for image vectorization.

    Extracts image features and predicts optimal VTracer/Potrace parameters
    based on image characteristics.
    """

    def __init__(self):
        """Initialize parameter predictor."""
        self.feature_names = [
            "edge_density",
            "texture_complexity",
            "unique_colors",
            "saturation",
            "pixel_count",
            "aspect_ratio",
            "color_variance",
        ]

    def extract_features(self, image: np.ndarray) -> Dict[str, float]:
        """Extract image features for parameter prediction.

        Args:
            image: Input image as numpy array (BGR format from cv2)

        Returns:
            Dictionary with feature names and values
        """
        try:
            h, w = image.shape[:2]

            # Edge density
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 100, 200)
            edge_density = float(np.sum(edges > 0) / (h * w))

            # Texture complexity (Laplacian variance)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            texture_complexity = float(np.var(laplacian))

            # Unique colors (in reduced space)
            if image.ndim == 3:
                # Reduce to 8-bit per channel
                img_8bit = (image // 32 * 32).reshape(-1, 3)
                unique_colors = float(len(np.unique(img_8bit, axis=0)))
            else:
                unique_colors = 256.0

            # Saturation (HSV color space)
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
            saturation = float(np.mean(hsv[:, :, 1]))

            # Pixel count (normalized by 1M pixels)
            pixel_count = float((h * w) / 1_000_000)

            # Aspect ratio
            aspect_ratio = float(w / h if h > 0 else 1.0)

            # Color variance (overall color variation)
            if image.ndim == 3:
                rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).astype(np.float32)
                color_variance = float(np.mean(np.var(rgb, axis=0)))
            else:
                color_variance = 0.0

            features = {
                "edge_density": edge_density,
                "texture_complexity": texture_complexity,
                "unique_colors": unique_colors,
                "saturation": saturation,
                "pixel_count": pixel_count,
                "aspect_ratio": aspect_ratio,
                "color_variance": color_variance,
            }

            logger.debug(f"Extracted features: {features}")
            return features

        except Exception as e:
            logger.warning(f"Feature extraction failed: {e}")
            return {name: 0.0 for name in self.feature_names}

    def classify_image_type(self, image: np.ndarray) -> Literal["photo", "illustration", "line-art", "logo"]:
        """Classify image type based on extracted features.

        Args:
            image: Input image as numpy array

        Returns:
            Image type: 'photo', 'illustration', 'line-art', or 'logo'
        """
        try:
            features = self.extract_features(image)

            edge_density = features["edge_density"]
            texture_complexity = features["texture_complexity"]
            unique_colors = features["unique_colors"]
            saturation = features["saturation"]

            # Heuristic-based classification
            # Line art: High edge density, low texture, few colors
            if edge_density > 0.15 and texture_complexity < 500 and unique_colors < 500:
                return "line-art"

            # Logo: Low texture, moderate colors, distinct shapes
            if texture_complexity < 300 and 10 < unique_colors < 1000:
                return "logo"

            # Photo: High texture, high unique colors, moderate saturation
            if texture_complexity > 1000 and unique_colors > 5000 and saturation < 180:
                return "photo"

            # Illustration: Moderate texture, varied colors, some saturation
            return "illustration"

        except Exception as e:
            logger.warning(f"Image classification failed: {e}, defaulting to illustration")
            return "illustration"

    def predict_vtracer_params(
        self, image: np.ndarray, image_type: Literal["photo", "illustration", "line-art", "logo"]
    ) -> Dict[str, Any]:
        """Predict optimal VTracer parameters based on image characteristics.

        Args:
            image: Input image as numpy array
            image_type: Classified image type

        Returns:
            Dictionary of VTracer parameter overrides
        """
        try:
            features = self.extract_features(image)
            edge_density = features["edge_density"]
            texture_complexity = features["texture_complexity"]
            unique_colors = features["unique_colors"]

            params = {}

            # color_precision: Higher for complex images
            if image_type == "photo":
                params["color_precision"] = min(int(10 + texture_complexity / 200), 20)
            elif image_type == "illustration":
                params["color_precision"] = min(int(8 + texture_complexity / 300), 15)
            else:
                params["color_precision"] = 6

            # filter_speckle: Higher for noisy images
            if texture_complexity > 1500:
                params["filter_speckle"] = 8
            elif texture_complexity > 800:
                params["filter_speckle"] = 4
            else:
                params["filter_speckle"] = 2

            # corner_threshold: Lower for sharp corners (line art)
            if image_type == "line-art":
                params["corner_threshold"] = 45
            elif image_type in ("logo", "illustration"):
                params["corner_threshold"] = 60
            else:
                params["corner_threshold"] = 90

            # segment_length: Higher for smooth images
            if texture_complexity < 500:
                params["segment_length"] = 9
            elif texture_complexity < 1000:
                params["segment_length"] = 7
            else:
                params["segment_length"] = 5

            # splice_threshold: Lower for detailed images
            if edge_density > 0.2:
                params["splice_threshold"] = 45
            else:
                params["splice_threshold"] = 65

            logger.info(f"Predicted VTracer params for {image_type}: {params}")
            return params

        except Exception as e:
            logger.warning(f"VTracer parameter prediction failed: {e}")
            return {}

    def predict_potrace_params(
        self, image: np.ndarray, image_type: Literal["photo", "illustration", "line-art", "logo"]
    ) -> Dict[str, Any]:
        """Predict optimal Potrace parameters based on image characteristics.

        Args:
            image: Input image as numpy array
            image_type: Classified image type

        Returns:
            Dictionary of Potrace parameter overrides
        """
        try:
            features = self.extract_features(image)
            texture_complexity = features["texture_complexity"]
            edge_density = features["edge_density"]

            params = {}

            # alphamax: Lower for sharp corners
            if image_type == "line-art":
                params["alphamax"] = 0.5
            elif image_type in ("logo", "illustration"):
                params["alphamax"] = 0.8
            else:
                params["alphamax"] = 1.3

            # turdsize: Higher for noisy images
            if texture_complexity > 1500:
                params["turdsize"] = 10
            elif texture_complexity > 800:
                params["turdsize"] = 5
            else:
                params["turdsize"] = 2

            # opttolerance: Higher for simpler images
            if image_type in ("line-art", "logo"):
                params["opttolerance"] = 0.5
            elif image_type == "illustration":
                params["opttolerance"] = 0.3
            else:
                params["opttolerance"] = 0.1

            logger.info(f"Predicted Potrace params for {image_type}: {params}")
            return params

        except Exception as e:
            logger.warning(f"Potrace parameter prediction failed: {e}")
            return {}


class AdaptiveColorClustering:
    """Adaptive color clustering using k-means and silhouette scoring."""

    def __init__(self, max_k: int = 64, min_k: int = 2):
        """Initialize color clustering.

        Args:
            max_k: Maximum number of clusters to try
            min_k: Minimum number of clusters
        """
        self.max_k = max_k
        self.min_k = min_k

    def find_optimal_k(self, image: np.ndarray, sample_size: int = 10000) -> int:
        """Find optimal number of color clusters using silhouette score.

        Args:
            image: Input image as numpy array
            sample_size: Number of pixels to sample for faster computation

        Returns:
            Optimal number of clusters
        """
        try:
            # Prepare data
            h, w = image.shape[:2]
            pixels = image.reshape(-1, 3)

            # Sample if too large
            if len(pixels) > sample_size:
                indices = np.random.choice(len(pixels), sample_size, replace=False)
                pixels = pixels[indices]

            best_k = self.min_k
            best_score = -1

            # Try different k values
            for k in range(self.min_k, min(self.max_k + 1, len(pixels))):
                try:
                    kmeans = MiniBatchKMeans(n_clusters=k, n_init=3, random_state=42)
                    labels = kmeans.fit_predict(pixels)

                    # Skip if only one cluster
                    if len(np.unique(labels)) < 2:
                        continue

                    score = silhouette_score(pixels, labels, sample_size=min(1000, len(pixels)))

                    if score > best_score:
                        best_score = score
                        best_k = k

                except Exception as e:
                    logger.debug(f"Error evaluating k={k}: {e}")
                    continue

            logger.info(f"Found optimal k={best_k} (silhouette_score={best_score:.3f})")
            return best_k

        except Exception as e:
            logger.warning(f"Failed to find optimal k: {e}, using default")
            return 16

    def apply_clustering(self, image: np.ndarray, k: Optional[int] = None) -> np.ndarray:
        """Apply k-means color clustering to reduce palette.

        Args:
            image: Input image as numpy array
            k: Number of clusters (auto-detected if None)

        Returns:
            Clustered image with reduced colors
        """
        try:
            if k is None:
                k = self.find_optimal_k(image)

            h, w = image.shape[:2]
            pixels = image.reshape(-1, 3).astype(np.float32)

            # Apply k-means
            kmeans = MiniBatchKMeans(n_clusters=k, n_init=5, random_state=42)
            labels = kmeans.fit_predict(pixels)
            centers = kmeans.cluster_centers_.astype(np.uint8)

            # Map back to image
            result = centers[labels].reshape(h, w, 3).astype(np.uint8)

            logger.debug(f"Applied color clustering with k={k}")
            return result

        except Exception as e:
            logger.warning(f"Color clustering failed: {e}")
            return image


class MLConverter:
    """Main ML enhancement service for vectorization.

    Provides three tiers of enhancement:
    - Tier 1: Feature extraction, classification, parameter prediction (sklearn)
    - Tier 2: Semantic segmentation (SAM via PyTorch)
    - Tier 3: Super-resolution and edge enhancement (ONNX)
    """

    def __init__(self):
        """Initialize ML converter."""
        self.param_predictor = MLParamPredictor()
        self.color_clustering = AdaptiveColorClustering()
        self._sam_vectorizer: Optional[Any] = None
        self._onnx_enhancer: Optional[Any] = None

    @property
    def sam_vectorizer(self) -> Optional[Any]:
        """Lazy-load SAMVectorizer (Tier 2).

        Returns:
            SAMVectorizer instance or None if unavailable
        """
        if self._sam_vectorizer is None:
            try:
                from app.services.sam_vectorizer import SAMVectorizer

                if SAMVectorizer.is_available():
                    self._sam_vectorizer = SAMVectorizer()
                    logger.info("Loaded SAMVectorizer (Tier 2)")
                else:
                    logger.debug("SAMVectorizer not available (torch/segment_anything not installed)")
            except ImportError:
                logger.debug("SAMVectorizer import failed")

        return self._sam_vectorizer

    @property
    def onnx_enhancer(self) -> Optional[Any]:
        """Lazy-load ONNXEnhancer (Tier 3).

        Returns:
            ONNXEnhancer instance or None if unavailable
        """
        if self._onnx_enhancer is None:
            try:
                from app.services.onnx_enhancer import ONNXEnhancer

                if ONNXEnhancer.is_available():
                    self._onnx_enhancer = ONNXEnhancer()
                    logger.info("Loaded ONNXEnhancer (Tier 3)")
                else:
                    logger.debug("ONNXEnhancer not available (onnxruntime not installed)")
            except ImportError:
                logger.debug("ONNXEnhancer import failed")

        return self._onnx_enhancer

    def enhance_for_vectorization(
        self,
        image: np.ndarray,
        image_type: Optional[Literal["photo", "illustration", "line-art", "logo"]] = None,
        apply_tier2: bool = True,
        apply_tier3: bool = True,
    ) -> Tuple[np.ndarray, Dict[str, Any], List[str]]:
        """Enhance image for optimal vectorization with ML techniques.

        This is the main entry point that coordinates all three tiers of enhancement:
        - Tier 1 (always): Feature extraction and parameter prediction
        - Tier 2 (optional): Semantic segmentation for better path tracing
        - Tier 3 (optional): Super-resolution and edge enhancement

        Args:
            image: Input image as numpy array (BGR format from cv2)
            image_type: Image type hint ('photo', 'illustration', 'line-art', 'logo')
                       If None, will be auto-detected
            apply_tier2: Whether to apply Tier 2 enhancements (SAM segmentation)
            apply_tier3: Whether to apply Tier 3 enhancements (ONNX models)

        Returns:
            Tuple of (enhanced_image, param_overrides, steps_applied)
            - enhanced_image: Processed image ready for vectorization
            - param_overrides: Suggested parameter overrides for VTracer/Potrace
            - steps_applied: List of enhancement steps that were applied
        """
        steps_applied: List[str] = []
        param_overrides: Dict[str, Any] = {}
        current_image = image.copy()

        try:
            # Tier 1: Feature extraction and classification
            logger.info("Starting Tier 1 ML enhancement (feature extraction)")

            if image_type is None:
                image_type = self.param_predictor.classify_image_type(current_image)
                logger.info(f"Auto-detected image type: {image_type}")

            steps_applied.append(f"auto_classify:{image_type}")

            # Predict parameters
            vtracer_params = self.param_predictor.predict_vtracer_params(current_image, image_type)
            potrace_params = self.param_predictor.predict_potrace_params(current_image, image_type)

            param_overrides["vtracer"] = vtracer_params
            param_overrides["potrace"] = potrace_params
            steps_applied.append("param_prediction")

            # Adaptive color clustering for color images
            if image_type in ("illustration", "photo"):
                logger.info("Applying adaptive color clustering")
                current_image = self.color_clustering.apply_clustering(current_image)
                steps_applied.append("color_clustering")

            # Tier 2: Semantic segmentation (optional)
            if apply_tier2 and self.sam_vectorizer is not None:
                try:
                    logger.info("Applying Tier 2 SAM segmentation")
                    # Note: SAM enhancement would be integrated here
                    # For now, this is a placeholder for future expansion
                    steps_applied.append("sam_segmentation_placeholder")
                except Exception as e:
                    logger.warning(f"Tier 2 enhancement failed: {e}")

            # Tier 3: Super-resolution and edge enhancement (optional)
            if apply_tier3 and self.onnx_enhancer is not None:
                try:
                    h, w = current_image.shape[:2]
                    min_side = min(h, w)

                    # Super-resolution for small images
                    if min_side < 256:
                        logger.info("Applying Tier 3 super-resolution")
                        current_image = self.onnx_enhancer.super_resolve(current_image, scale=3)
                        steps_applied.append("super_resolution_3x")

                    # Edge enhancement
                    logger.info("Applying Tier 3 edge enhancement")
                    current_image = self.onnx_enhancer.enhance_edges(current_image)
                    steps_applied.append("edge_enhancement")

                except Exception as e:
                    logger.warning(f"Tier 3 enhancement failed: {e}")

            logger.info(f"ML enhancement complete. Steps: {steps_applied}")
            return current_image, param_overrides, steps_applied

        except Exception as e:
            logger.error(f"ML enhancement pipeline failed: {e}")
            # Return original image with empty overrides on failure
            return image, {}, ["error:" + str(e)]
