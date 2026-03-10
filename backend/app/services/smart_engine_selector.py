"""Smart Engine Selector — ML-based image classifier for optimal engine routing.

Analyzes image characteristics and selects the best vectorization engine:
- Line art / logos → Potrace (fast, clean paths)
- Color graphics / illustrations → VTracer (good color clustering)
- Photographs / complex → SAM + DiffVG pipeline (highest fidelity)
- Documents / scans → Potrace + deskew/despeckle pipeline

Uses feature extraction (edge density, color complexity, texture analysis)
to produce a confidence-scored recommendation.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple

import cv2
import numpy as np
from scipy import ndimage

logger = logging.getLogger(__name__)


class EngineType(str, Enum):
    """Available vectorization engines."""

    POTRACE = "potrace"
    VTRACER = "vtracer"
    SAM_VTRACER = "sam_vtracer"  # SAM segmentation + VTracer per region
    SAM_DIFFVG = "sam_diffvg"  # SAM segmentation + DiffVG refinement
    AUTO = "auto"


class ImageCategory(str, Enum):
    """Classified image categories."""

    LINE_ART = "line_art"
    LOGO = "logo"
    ILLUSTRATION = "illustration"
    PHOTOGRAPH = "photograph"
    DOCUMENT = "document"
    SKETCH = "sketch"
    ICON = "icon"
    UNKNOWN = "unknown"


@dataclass
class ImageFeatures:
    """Extracted image features for classification."""

    # Spatial features
    width: int = 0
    height: int = 0
    aspect_ratio: float = 1.0
    megapixels: float = 0.0

    # Color features
    unique_colors: int = 0
    color_complexity: float = 0.0  # 0-1: ratio of unique colors to total pixels
    dominant_colors: int = 0  # number of dominant color clusters
    is_grayscale: bool = False
    has_transparency: bool = False
    color_variance: float = 0.0  # variance in color distribution
    saturation_mean: float = 0.0
    saturation_std: float = 0.0

    # Edge features
    edge_density: float = 0.0  # ratio of edge pixels to total
    edge_continuity: float = 0.0  # how continuous/connected edges are
    strong_edge_ratio: float = 0.0  # ratio of strong edges
    corner_density: float = 0.0  # Harris corner density

    # Texture features
    texture_energy: float = 0.0  # GLCM energy (uniformity)
    texture_contrast: float = 0.0  # GLCM contrast
    texture_homogeneity: float = 0.0  # GLCM homogeneity

    # Noise features
    noise_level: float = 0.0  # Laplacian variance normalized

    # Region features
    large_uniform_regions: int = 0  # number of large uniform color regions
    small_detail_regions: int = 0  # number of small detail regions

    # Frequency features
    high_freq_ratio: float = 0.0  # ratio of high-frequency content
    low_freq_ratio: float = 0.0  # ratio of low-frequency content

    # Shape features
    contour_count: int = 0
    avg_contour_complexity: float = 0.0  # average perimeter/area ratio


@dataclass
class EngineRecommendation:
    """Recommendation for which engine to use."""

    engine: EngineType
    confidence: float  # 0-1 confidence score
    category: ImageCategory
    reasoning: str
    alternative_engine: Optional[EngineType] = None
    alternative_confidence: float = 0.0
    suggested_params: Dict[str, Any] = field(default_factory=dict)
    preprocessing_hints: List[str] = field(default_factory=list)
    estimated_quality: float = 0.0  # 0-1 expected output quality
    estimated_time: float = 0.0  # seconds


class SmartEngineSelector:
    """Analyzes images and selects the optimal vectorization engine.

    Uses a combination of:
    1. Color analysis (unique colors, saturation, gradients)
    2. Edge analysis (density, continuity, corners)
    3. Texture analysis (GLCM features)
    4. Frequency analysis (FFT high/low frequency ratio)
    5. Shape analysis (contour complexity)

    to classify the image and route to the best engine.
    """

    # Classification thresholds (tuned empirically)
    THRESHOLDS = {
        "line_art_edge_density": 0.08,
        "line_art_color_complexity": 0.02,
        "logo_uniform_regions": 5,
        "logo_color_count_max": 16,
        "photo_color_complexity": 0.15,
        "photo_texture_contrast": 0.3,
        "document_edge_density": 0.05,
        "sketch_edge_continuity": 0.3,
        "icon_max_size": 512,
        "icon_max_colors": 32,
    }

    def __init__(self):
        self._feature_cache: Dict[str, ImageFeatures] = {}

    def analyze_and_select(
        self,
        image: np.ndarray,
        prefer_speed: bool = False,
        prefer_quality: bool = False,
        force_engine: Optional[EngineType] = None,
    ) -> EngineRecommendation:
        """Analyze image and recommend the best vectorization engine.

        Args:
            image: Input image (BGR format from OpenCV)
            prefer_speed: If True, bias toward faster engines
            prefer_quality: If True, bias toward higher-quality engines
            force_engine: If set, use this engine but still analyze the image

        Returns:
            EngineRecommendation with engine choice, confidence, and params
        """
        # Extract features
        features = self.extract_features(image)

        # Classify the image
        category, category_confidence = self._classify_image(features)

        # Select engine based on classification
        if force_engine and force_engine != EngineType.AUTO:
            engine = force_engine
            confidence = category_confidence
        else:
            engine, confidence = self._select_engine(
                category, features, prefer_speed, prefer_quality
            )

        # Get the alternative engine
        alt_engine, alt_confidence = self._get_alternative(engine, category, features)

        # Generate suggested parameters
        suggested_params = self._get_suggested_params(engine, category, features)

        # Generate preprocessing hints
        preprocessing_hints = self._get_preprocessing_hints(category, features)

        # Estimate quality and time
        est_quality = self._estimate_quality(engine, category, features)
        est_time = self._estimate_time(engine, features)

        # Build reasoning
        reasoning = self._build_reasoning(category, engine, features, category_confidence)

        return EngineRecommendation(
            engine=engine,
            confidence=confidence,
            category=category,
            reasoning=reasoning,
            alternative_engine=alt_engine,
            alternative_confidence=alt_confidence,
            suggested_params=suggested_params,
            preprocessing_hints=preprocessing_hints,
            estimated_quality=est_quality,
            estimated_time=est_time,
        )

    def extract_features(self, image: np.ndarray) -> ImageFeatures:
        """Extract comprehensive image features for classification.

        Args:
            image: Input image (BGR format)

        Returns:
            ImageFeatures dataclass with all extracted features
        """
        features = ImageFeatures()

        h, w = image.shape[:2]
        features.width = w
        features.height = h
        features.aspect_ratio = w / max(h, 1)
        features.megapixels = (w * h) / 1_000_000

        # Work with a smaller image for speed
        max_dim = 512
        scale = min(max_dim / max(w, h), 1.0)
        if scale < 1.0:
            small = cv2.resize(image, (int(w * scale), int(h * scale)))
        else:
            small = image.copy()

        # Color features
        self._extract_color_features(small, features)

        # Edge features
        self._extract_edge_features(small, features)

        # Texture features
        self._extract_texture_features(small, features)

        # Noise features
        self._extract_noise_features(small, features)

        # Frequency features
        self._extract_frequency_features(small, features)

        # Shape/contour features
        self._extract_shape_features(small, features)

        return features

    def _extract_color_features(self, image: np.ndarray, features: ImageFeatures) -> None:
        """Extract color-related features."""
        h, w = image.shape[:2]
        total_pixels = h * w

        if len(image.shape) == 2:
            # Grayscale
            features.is_grayscale = True
            features.unique_colors = len(np.unique(image))
            features.color_complexity = features.unique_colors / 256
            features.saturation_mean = 0.0
            features.saturation_std = 0.0
            return

        # Convert to different color spaces
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Check if effectively grayscale
        saturation = hsv[:, :, 1].astype(float)
        features.saturation_mean = float(np.mean(saturation))
        features.saturation_std = float(np.std(saturation))
        features.is_grayscale = features.saturation_mean < 15

        # Unique colors (sampled for speed)
        flat = image.reshape(-1, 3)
        sample_size = min(50000, len(flat))
        indices = np.random.choice(len(flat), sample_size, replace=False)
        sampled = flat[indices]

        # Quantize to reduce noise in color counting
        quantized = (sampled // 8) * 8
        unique = np.unique(quantized, axis=0)
        features.unique_colors = len(unique)
        features.color_complexity = min(1.0, features.unique_colors / 1000)

        # Color variance
        features.color_variance = float(np.mean(np.std(flat.astype(float), axis=0)))

        # Dominant colors via mini-batch k-means
        try:
            from sklearn.cluster import MiniBatchKMeans

            n_clusters = min(16, len(unique))
            if n_clusters >= 2:
                kmeans = MiniBatchKMeans(
                    n_clusters=n_clusters, random_state=42, n_init=3, batch_size=1000
                )
                labels = kmeans.fit_predict(sampled.astype(float))

                # Count clusters with >5% of pixels
                counts = np.bincount(labels, minlength=n_clusters)
                significant = np.sum(counts > (sample_size * 0.05))
                features.dominant_colors = int(significant)
        except Exception:
            features.dominant_colors = min(features.unique_colors, 8)

        # Large uniform regions
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary)

        large_threshold = total_pixels * 0.01  # regions > 1% of image
        features.large_uniform_regions = int(np.sum(stats[1:, cv2.CC_STAT_AREA] > large_threshold))
        small_threshold = total_pixels * 0.001
        features.small_detail_regions = int(np.sum(stats[1:, cv2.CC_STAT_AREA] < small_threshold))

    def _extract_edge_features(self, image: np.ndarray, features: ImageFeatures) -> None:
        """Extract edge-related features."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        h, w = gray.shape[:2]
        total_pixels = h * w

        # Canny edge detection
        edges = cv2.Canny(gray, 50, 150)
        edge_pixels = np.count_nonzero(edges)
        features.edge_density = edge_pixels / total_pixels

        # Strong edges (higher threshold)
        strong_edges = cv2.Canny(gray, 100, 200)
        features.strong_edge_ratio = np.count_nonzero(strong_edges) / max(edge_pixels, 1)

        # Edge continuity (connected components of edge map)
        num_labels, _, stats, _ = cv2.connectedComponentsWithStats(edges)
        if num_labels > 1:
            areas = stats[1:, cv2.CC_STAT_AREA]
            mean_area = np.mean(areas)
            # Higher mean area = more continuous edges
            features.edge_continuity = min(1.0, mean_area / 50)

        # Harris corner detection
        corners = cv2.cornerHarris(gray.astype(np.float32), 2, 3, 0.04)
        corner_count = np.sum(corners > 0.01 * corners.max())
        features.corner_density = corner_count / total_pixels

    def _extract_texture_features(self, image: np.ndarray, features: ImageFeatures) -> None:
        """Extract texture features using GLCM-inspired metrics."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Simplified GLCM features via local statistics
        # Energy (uniformity) — high for uniform regions
        local_std = ndimage.generic_filter(gray.astype(float), np.std, size=5)
        features.texture_energy = 1.0 - min(1.0, float(np.mean(local_std)) / 50)

        # Contrast — difference between neighboring pixels
        dx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        dy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(dx**2 + dy**2)
        features.texture_contrast = min(1.0, float(np.mean(gradient_magnitude)) / 100)

        # Homogeneity — inverse difference moment approximation
        features.texture_homogeneity = 1.0 - features.texture_contrast

    def _extract_noise_features(self, image: np.ndarray, features: ImageFeatures) -> None:
        """Extract noise level estimation."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Laplacian variance method for noise estimation
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        lap_var = float(np.var(laplacian))

        # Normalize (empirically: low noise ~100, high noise ~5000+)
        features.noise_level = min(1.0, lap_var / 3000)

    def _extract_frequency_features(self, image: np.ndarray, features: ImageFeatures) -> None:
        """Extract frequency domain features via FFT."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # 2D FFT
        f = np.fft.fft2(gray.astype(float))
        fshift = np.fft.fftshift(f)
        magnitude = np.abs(fshift)

        h, w = gray.shape[:2]
        cy, cx = h // 2, w // 2

        # Create radial mask
        Y, X = np.ogrid[:h, :w]
        r = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
        max_r = np.sqrt(cx**2 + cy**2)

        # Low frequency: inner 20%
        low_mask = r < (max_r * 0.2)
        # High frequency: outer 60%
        high_mask = r > (max_r * 0.4)

        total_energy = np.sum(magnitude)
        if total_energy > 0:
            features.low_freq_ratio = float(np.sum(magnitude[low_mask]) / total_energy)
            features.high_freq_ratio = float(np.sum(magnitude[high_mask]) / total_energy)
        else:
            features.low_freq_ratio = 1.0
            features.high_freq_ratio = 0.0

    def _extract_shape_features(self, image: np.ndarray, features: ImageFeatures) -> None:
        """Extract shape/contour features."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Find contours
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        features.contour_count = len(contours)

        if contours:
            complexities = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                perimeter = cv2.arcLength(cnt, True)
                if area > 0:
                    # Circularity: 4*pi*area / perimeter^2 (1.0 = perfect circle)
                    complexity = perimeter / (2 * np.sqrt(np.pi * area))
                    complexities.append(complexity)

            if complexities:
                features.avg_contour_complexity = float(np.mean(complexities))

    def _classify_image(self, features: ImageFeatures) -> Tuple[ImageCategory, float]:
        """Classify the image into a category.

        Returns:
            Tuple of (ImageCategory, confidence)
        """
        scores: Dict[ImageCategory, float] = {}

        # === LINE ART ===
        line_art_score = 0.0
        if features.edge_density > self.THRESHOLDS["line_art_edge_density"]:
            line_art_score += 0.3
        if features.color_complexity < self.THRESHOLDS["line_art_color_complexity"]:
            line_art_score += 0.3
        if features.is_grayscale or features.dominant_colors <= 2:
            line_art_score += 0.2
        if features.texture_energy > 0.7:
            line_art_score += 0.2
        scores[ImageCategory.LINE_ART] = line_art_score

        # === LOGO ===
        logo_score = 0.0
        if features.large_uniform_regions >= self.THRESHOLDS["logo_uniform_regions"]:
            logo_score += 0.25
        if features.dominant_colors <= self.THRESHOLDS["logo_color_count_max"]:
            logo_score += 0.25
        if features.texture_energy > 0.6:
            logo_score += 0.2
        if features.edge_continuity > 0.4:
            logo_score += 0.15
        if features.contour_count < 100:
            logo_score += 0.15
        scores[ImageCategory.LOGO] = logo_score

        # === ICON ===
        icon_score = 0.0
        max_size = self.THRESHOLDS["icon_max_size"]
        if features.width <= max_size and features.height <= max_size:
            icon_score += 0.3
        if features.dominant_colors <= self.THRESHOLDS["icon_max_colors"]:
            icon_score += 0.25
        if features.texture_energy > 0.5:
            icon_score += 0.2
        if features.large_uniform_regions >= 3:
            icon_score += 0.25
        scores[ImageCategory.ICON] = icon_score

        # === ILLUSTRATION ===
        illustration_score = 0.0
        if 0.02 < features.color_complexity < 0.15:
            illustration_score += 0.3
        if features.dominant_colors > 4 and features.dominant_colors <= 32:
            illustration_score += 0.25
        if features.texture_energy > 0.4:
            illustration_score += 0.2
        if features.edge_density > 0.03:
            illustration_score += 0.15
        if features.saturation_mean > 30:
            illustration_score += 0.1
        scores[ImageCategory.ILLUSTRATION] = illustration_score

        # === PHOTOGRAPH ===
        photo_score = 0.0
        if features.color_complexity > self.THRESHOLDS["photo_color_complexity"]:
            photo_score += 0.3
        if features.texture_contrast > self.THRESHOLDS["photo_texture_contrast"]:
            photo_score += 0.2
        if features.high_freq_ratio > 0.3:
            photo_score += 0.2
        if features.noise_level > 0.1:
            photo_score += 0.15
        if features.dominant_colors > 10:
            photo_score += 0.15
        scores[ImageCategory.PHOTOGRAPH] = photo_score

        # === DOCUMENT ===
        document_score = 0.0
        if features.is_grayscale or features.saturation_mean < 20:
            document_score += 0.25
        if features.edge_density < self.THRESHOLDS["document_edge_density"]:
            document_score += 0.2
        if features.large_uniform_regions > 3:
            document_score += 0.2
        if features.texture_energy > 0.7:
            document_score += 0.2
        if features.aspect_ratio > 0.6 and features.aspect_ratio < 0.9:
            document_score += 0.15  # Portrait-ish ratio typical of docs
        scores[ImageCategory.DOCUMENT] = document_score

        # === SKETCH ===
        sketch_score = 0.0
        if features.is_grayscale or features.saturation_mean < 25:
            sketch_score += 0.2
        if features.edge_continuity < self.THRESHOLDS["sketch_edge_continuity"]:
            sketch_score += 0.25  # Sketches have discontinuous strokes
        if features.edge_density > 0.03 and features.edge_density < 0.12:
            sketch_score += 0.25
        if features.noise_level > 0.15:
            sketch_score += 0.15  # Paper texture / pencil grain
        if features.texture_homogeneity > 0.5:
            sketch_score += 0.15
        scores[ImageCategory.SKETCH] = sketch_score

        # Pick the category with highest score
        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]

        # Normalize confidence
        confidence = min(1.0, best_score)

        # If confidence is too low, mark as unknown
        if confidence < 0.3:
            return ImageCategory.UNKNOWN, confidence

        return best_category, confidence

    def _select_engine(
        self,
        category: ImageCategory,
        features: ImageFeatures,
        prefer_speed: bool,
        prefer_quality: bool,
    ) -> Tuple[EngineType, float]:
        """Select the best engine for the given category.

        Returns:
            Tuple of (EngineType, confidence)
        """
        # Engine mapping by category
        category_engines = {
            ImageCategory.LINE_ART: (EngineType.POTRACE, 0.95),
            ImageCategory.LOGO: (EngineType.VTRACER, 0.90),
            ImageCategory.ICON: (EngineType.VTRACER, 0.90),
            ImageCategory.ILLUSTRATION: (EngineType.VTRACER, 0.85),
            ImageCategory.PHOTOGRAPH: (EngineType.SAM_VTRACER, 0.80),
            ImageCategory.DOCUMENT: (EngineType.POTRACE, 0.92),
            ImageCategory.SKETCH: (EngineType.POTRACE, 0.88),
            ImageCategory.UNKNOWN: (EngineType.VTRACER, 0.60),
        }

        engine, confidence = category_engines.get(category, (EngineType.VTRACER, 0.60))

        # Apply speed/quality biases
        if prefer_speed:
            if engine in (EngineType.SAM_VTRACER, EngineType.SAM_DIFFVG):
                engine = EngineType.VTRACER
                confidence *= 0.85

        if prefer_quality:
            if engine == EngineType.VTRACER and category == ImageCategory.PHOTOGRAPH:
                engine = EngineType.SAM_DIFFVG
                confidence *= 0.90
            elif engine == EngineType.VTRACER and features.color_complexity > 0.1:
                engine = EngineType.SAM_VTRACER
                confidence *= 0.85

        # If image is grayscale, always prefer Potrace
        if features.is_grayscale and engine not in (EngineType.POTRACE,):
            engine = EngineType.POTRACE
            confidence = max(confidence, 0.85)

        return engine, confidence

    def _get_alternative(
        self,
        primary: EngineType,
        category: ImageCategory,
        features: ImageFeatures,
    ) -> Tuple[Optional[EngineType], float]:
        """Get alternative engine recommendation."""
        alternatives = {
            EngineType.POTRACE: (EngineType.VTRACER, 0.70),
            EngineType.VTRACER: (EngineType.SAM_VTRACER, 0.65),
            EngineType.SAM_VTRACER: (EngineType.VTRACER, 0.75),
            EngineType.SAM_DIFFVG: (EngineType.SAM_VTRACER, 0.70),
        }
        return alternatives.get(primary, (None, 0.0))

    def _get_suggested_params(
        self,
        engine: EngineType,
        category: ImageCategory,
        features: ImageFeatures,
    ) -> Dict[str, Any]:
        """Generate optimized parameters based on image analysis."""
        params: Dict[str, Any] = {"engine": engine.value}

        if engine in (EngineType.VTRACER, EngineType.SAM_VTRACER):
            # VTracer parameters
            if category == ImageCategory.LOGO:
                params.update(
                    {
                        "color_precision": min(features.dominant_colors * 2, 64),
                        "filter_speckle": 2,
                        "corner_threshold": 60,
                        "mode": "splice",
                        "hierarchical": True,
                        "path_precision": 8,
                    }
                )
            elif category == ImageCategory.ILLUSTRATION:
                params.update(
                    {
                        "color_precision": min(features.dominant_colors * 3, 128),
                        "filter_speckle": 3,
                        "corner_threshold": 45,
                        "mode": "splice",
                        "hierarchical": True,
                        "path_precision": 6,
                    }
                )
            elif category == ImageCategory.PHOTOGRAPH:
                params.update(
                    {
                        "color_precision": 64,
                        "filter_speckle": 1,
                        "corner_threshold": 30,
                        "mode": "splice",
                        "hierarchical": True,
                        "path_precision": 10,
                        "max_iterations": 30,
                    }
                )
            elif category == ImageCategory.ICON:
                params.update(
                    {
                        "color_precision": min(features.dominant_colors * 2, 32),
                        "filter_speckle": 4,
                        "corner_threshold": 90,
                        "mode": "splice",
                        "hierarchical": True,
                        "path_precision": 4,
                    }
                )
            else:
                params.update(
                    {
                        "color_precision": 32,
                        "filter_speckle": 3,
                        "corner_threshold": 60,
                    }
                )

        elif engine == EngineType.POTRACE:
            # Potrace parameters
            if category == ImageCategory.LINE_ART:
                params.update(
                    {
                        "alphamax": 0.5,
                        "turdsize": 2,
                        "opticurve": True,
                        "opttolerance": 0.1,
                        "turnpolicy": "minority",
                    }
                )
            elif category == ImageCategory.DOCUMENT:
                params.update(
                    {
                        "alphamax": 1.0,
                        "turdsize": 5,
                        "opticurve": True,
                        "opttolerance": 0.2,
                        "turnpolicy": "majority",
                    }
                )
            elif category == ImageCategory.SKETCH:
                params.update(
                    {
                        "alphamax": 0.8,
                        "turdsize": 3,
                        "opticurve": True,
                        "opttolerance": 0.15,
                        "turnpolicy": "minority",
                    }
                )
            else:
                params.update(
                    {
                        "alphamax": 1.0,
                        "turdsize": 2,
                        "opticurve": True,
                        "opttolerance": 0.2,
                    }
                )

        return params

    def _get_preprocessing_hints(
        self,
        category: ImageCategory,
        features: ImageFeatures,
    ) -> List[str]:
        """Generate preprocessing recommendations based on analysis."""
        hints = []

        # Noise handling
        if features.noise_level > 0.3:
            hints.append("high_noise_detected: use NLM denoising (h=12-15)")
        elif features.noise_level > 0.15:
            hints.append("moderate_noise: use bilateral filter")

        # Contrast
        if features.texture_contrast < 0.15:
            hints.append("low_contrast: apply CLAHE enhancement")

        # Color reduction
        if features.color_complexity > 0.2 and category != ImageCategory.PHOTOGRAPH:
            hints.append(
                f"high_color_count: reduce to {min(features.dominant_colors * 2, 64)} colors"
            )

        # Edge enhancement
        if category in (ImageCategory.LINE_ART, ImageCategory.SKETCH):
            if features.edge_density < 0.05:
                hints.append("weak_edges: apply edge enhancement")

        # Document-specific
        if category == ImageCategory.DOCUMENT:
            hints.append("document: apply deskew and despeckle")
            if not features.is_grayscale:
                hints.append("document_color: convert to grayscale first")

        # Sharpening
        if features.noise_level < 0.1 and features.texture_contrast < 0.25:
            hints.append("soft_image: apply unsharp mask sharpening")

        # Super-resolution hint for small images
        if features.megapixels < 0.1:
            hints.append("low_resolution: consider AI upscaling before conversion")

        return hints

    def _estimate_quality(
        self,
        engine: EngineType,
        category: ImageCategory,
        features: ImageFeatures,
    ) -> float:
        """Estimate output quality (0-1) based on engine and image properties."""
        base_quality = {
            EngineType.POTRACE: 0.85,
            EngineType.VTRACER: 0.80,
            EngineType.SAM_VTRACER: 0.90,
            EngineType.SAM_DIFFVG: 0.95,
        }

        quality = base_quality.get(engine, 0.75)

        # Adjust based on category suitability
        good_matches = {
            (EngineType.POTRACE, ImageCategory.LINE_ART): 0.05,
            (EngineType.POTRACE, ImageCategory.DOCUMENT): 0.05,
            (EngineType.VTRACER, ImageCategory.LOGO): 0.05,
            (EngineType.VTRACER, ImageCategory.ILLUSTRATION): 0.05,
            (EngineType.SAM_VTRACER, ImageCategory.PHOTOGRAPH): 0.05,
        }
        quality += good_matches.get((engine, category), 0.0)

        # Penalize for noise
        if features.noise_level > 0.3:
            quality -= 0.1

        return min(1.0, max(0.0, quality))

    def _estimate_time(self, engine: EngineType, features: ImageFeatures) -> float:
        """Estimate processing time in seconds."""
        # Base times per engine
        base_times = {
            EngineType.POTRACE: 0.5,
            EngineType.VTRACER: 1.0,
            EngineType.SAM_VTRACER: 5.0,
            EngineType.SAM_DIFFVG: 10.0,
        }

        base = base_times.get(engine, 2.0)

        # Scale by image size
        size_factor = max(1.0, features.megapixels)

        return base * size_factor

    def _build_reasoning(
        self,
        category: ImageCategory,
        engine: EngineType,
        features: ImageFeatures,
        confidence: float,
    ) -> str:
        """Build a human-readable reasoning string."""
        reasons = []

        reasons.append(f"Image classified as '{category.value}' " f"(confidence: {confidence:.0%})")

        if features.is_grayscale:
            reasons.append("Grayscale image detected")
        else:
            reasons.append(
                f"{features.dominant_colors} dominant colors, "
                f"color complexity: {features.color_complexity:.2f}"
            )

        reasons.append(
            f"Edge density: {features.edge_density:.3f}, "
            f"Texture energy: {features.texture_energy:.2f}"
        )

        engine_reasons = {
            EngineType.POTRACE: "Potrace selected for clean monochrome/line-art tracing",
            EngineType.VTRACER: "VTracer selected for color-aware vectorization",
            EngineType.SAM_VTRACER: "SAM+VTracer selected for semantic segmentation-guided conversion",
            EngineType.SAM_DIFFVG: "SAM+DiffVG selected for highest quality with gradient optimization",
        }
        reasons.append(engine_reasons.get(engine, f"{engine.value} selected"))

        if features.noise_level > 0.2:
            reasons.append(f"⚠ Noise level is elevated ({features.noise_level:.2f})")

        return " | ".join(reasons)

    def get_engine_capabilities(self) -> Dict[str, Any]:
        """Get information about all available engines and their capabilities."""
        return {
            "engines": [
                {
                    "id": EngineType.POTRACE.value,
                    "name": "Potrace",
                    "description": "Classic bitmap tracer. Best for monochrome, line art, and documents.",
                    "best_for": ["line_art", "document", "sketch"],
                    "color_support": False,
                    "speed": "fast",
                    "quality_range": "0.80-0.95",
                    "requires_gpu": False,
                },
                {
                    "id": EngineType.VTRACER.value,
                    "name": "VTracer",
                    "description": "Modern color-aware tracer. Best for logos, icons, and illustrations.",
                    "best_for": ["logo", "icon", "illustration"],
                    "color_support": True,
                    "speed": "medium",
                    "quality_range": "0.75-0.90",
                    "requires_gpu": False,
                },
                {
                    "id": EngineType.SAM_VTRACER.value,
                    "name": "SAM + VTracer",
                    "description": "Semantic segmentation + VTracer. Best for photos and complex images.",
                    "best_for": ["photograph", "complex"],
                    "color_support": True,
                    "speed": "slow",
                    "quality_range": "0.85-0.95",
                    "requires_gpu": True,
                },
                {
                    "id": EngineType.SAM_DIFFVG.value,
                    "name": "SAM + DiffVG",
                    "description": "Semantic segmentation + differentiable rendering. Highest quality.",
                    "best_for": ["photograph", "gradient", "artistic"],
                    "color_support": True,
                    "speed": "very_slow",
                    "quality_range": "0.90-0.98",
                    "requires_gpu": True,
                },
            ],
            "categories": [c.value for c in ImageCategory],
        }
