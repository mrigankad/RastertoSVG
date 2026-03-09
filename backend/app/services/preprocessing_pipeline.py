"""Advanced preprocessing pipeline with granular control."""

import logging
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from app.api.advanced_models import (
    BlurParams,
    ColorPaletteConfig,
    ColorReduceParams,
    ContrastParams,
    DenoiseParams,
    DeskewParams,
    DespeckleParams,
    EdgeEnhanceParams,
    PreprocessingPipeline,
    PreprocessingStep,
    SharpenParams,
)
from app.services.preprocessor import (
    ContrastMethod,
    DenoiseMethod,
    DitherMethod,
    Preprocessor,
    ThresholdMethod,
)

logger = logging.getLogger(__name__)


class PreprocessingPipelineBuilder:
    """Builds and executes custom preprocessing pipelines."""

    def __init__(self):
        self.preprocessor = Preprocessor()
        self.filter_registry: Dict[str, Callable] = {
            "denoise": self._apply_denoise,
            "sharpen": self._apply_sharpen,
            "contrast": self._apply_contrast,
            "color_reduce": self._apply_color_reduce,
            "blur": self._apply_blur,
            "edge_enhance": self._apply_edge_enhance,
            "despeckle": self._apply_despeckle,
            "deskew": self._apply_deskew,
        }

    def apply_pipeline(
        self,
        image: np.ndarray,
        pipeline: PreprocessingPipeline,
        step_id: Optional[str] = None,
    ) -> np.ndarray:
        """
        Apply preprocessing pipeline to image.

        Args:
            image: Input image as numpy array
            pipeline: Preprocessing pipeline configuration
            step_id: If provided, only apply this specific step

        Returns:
            Processed image
        """
        result = image.copy()

        # Sort steps by order
        sorted_steps = sorted(pipeline.steps, key=lambda x: x.order)

        for step in sorted_steps:
            if not step.enabled:
                continue

            if step_id and step.id != step_id:
                continue

            if step.name in self.filter_registry:
                try:
                    result = self.filter_registry[step.name](result, step.params)
                    logger.debug(f"Applied filter: {step.name}")
                except Exception as e:
                    logger.error(f"Failed to apply filter {step.name}: {e}")
                    raise
            else:
                logger.warning(f"Unknown filter: {step.name}")

        return result

    def apply_pipeline_pil(
        self,
        image: Image.Image,
        pipeline: PreprocessingPipeline,
        step_id: Optional[str] = None,
    ) -> Image.Image:
        """
        Apply preprocessing pipeline to PIL Image.

        Args:
            image: Input PIL Image
            pipeline: Preprocessing pipeline configuration
            step_id: If provided, only apply this specific step

        Returns:
            Processed PIL Image
        """
        # Convert PIL to OpenCV
        cv_image = self._pil_to_cv2(image)

        # Apply pipeline
        result = self.apply_pipeline(cv_image, pipeline, step_id)

        # Convert back to PIL
        return self._cv2_to_pil(result)

    def _apply_denoise(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply denoise filter."""
        denoise_params = DenoiseParams(**params)

        if not denoise_params.enabled:
            return image

        method = denoise_params.method

        # Map strength to parameters
        strength_multiplier = {
            "light": 0.7,
            "medium": 1.0,
            "heavy": 1.5,
        }.get(denoise_params.strength, 1.0)

        if method == "gaussian":
            kernel_size = int(denoise_params.kernel_size * strength_multiplier)
            kernel_size = max(3, kernel_size if kernel_size % 2 == 1 else kernel_size + 1)
            return self.preprocessor._denoise_gaussian(
                image, kernel_size=kernel_size, sigma=denoise_params.sigma
            )

        elif method == "bilateral":
            d = int(denoise_params.d * strength_multiplier)
            sigma_color = denoise_params.sigma_color * strength_multiplier
            sigma_space = denoise_params.sigma_space * strength_multiplier
            return self.preprocessor._denoise_bilateral(
                image, d=d, sigma_color=sigma_color, sigma_space=sigma_space
            )

        elif method == "nlm":
            h = denoise_params.h * strength_multiplier
            return self.preprocessor._denoise_nlm(
                image,
                h=h,
                template_window=denoise_params.template_window,
                search_window=denoise_params.search_window,
            )

        elif method == "median":
            kernel_size = int(denoise_params.kernel_size * strength_multiplier)
            kernel_size = max(3, kernel_size if kernel_size % 2 == 1 else kernel_size + 1)
            return self.preprocessor._denoise_median(image, kernel_size=kernel_size)

        return image

    def _apply_sharpen(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply sharpen filter."""
        sharpen_params = SharpenParams(**params)

        if not sharpen_params.enabled:
            return image

        if sharpen_params.method == "unsharp_mask":
            return self.preprocessor._sharpen_unsharp_mask(
                image,
                kernel_size=sharpen_params.kernel_size,
                sigma=sharpen_params.sigma,
                amount=sharpen_params.amount,
            )
        else:
            return self.preprocessor._sharpen_kernel(image)

    def _apply_contrast(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply contrast enhancement."""
        contrast_params = ContrastParams(**params)

        if not contrast_params.enabled:
            return image

        method = contrast_params.method

        if method == "clahe":
            return self.preprocessor._enhance_clahe(
                image,
                clip_limit=contrast_params.clip_limit,
                tile_size=contrast_params.tile_size,
            )
        elif method == "histogram":
            return self.preprocessor._enhance_histogram(image)
        elif method == "levels":
            return self.preprocessor._enhance_levels(
                image,
                in_min=contrast_params.in_min,
                in_max=contrast_params.in_max,
                out_min=contrast_params.out_min,
                out_max=contrast_params.out_max,
            )
        elif method == "sigmoid":
            return self.preprocessor._enhance_sigmoid(
                image,
                contrast=contrast_params.contrast,
                midpoint=contrast_params.midpoint,
            )

        return image

    def _apply_color_reduce(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply color reduction."""
        color_params = ColorReduceParams(**params)

        if not color_params.enabled:
            return image

        method = color_params.method
        max_colors = color_params.max_colors

        if method == "kmeans":
            return self.preprocessor._reduce_colors_kmeans(image, max_colors=max_colors)
        elif method == "median_cut":
            return self.preprocessor._reduce_colors_median_cut(image, max_colors=max_colors)
        else:
            # Default to kmeans
            return self.preprocessor._reduce_colors_kmeans(image, max_colors=max_colors)

    def _apply_blur(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply blur filter."""
        blur_params = BlurParams(**params)

        if not blur_params.enabled:
            return image

        method = blur_params.method
        radius = blur_params.radius
        radius = max(3, radius if radius % 2 == 1 else radius + 1)

        if method == "gaussian":
            return cv2.GaussianBlur(image, (radius, radius), blur_params.sigma)
        elif method == "median":
            if len(image.shape) == 3:
                # Median blur for each channel
                channels = cv2.split(image)
                blurred_channels = [cv2.medianBlur(ch, radius) for ch in channels]
                return cv2.merge(blurred_channels)
            else:
                return cv2.medianBlur(image, radius)
        else:  # box
            return cv2.blur(image, (radius, radius))

    def _apply_edge_enhance(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply edge enhancement."""
        edge_params = EdgeEnhanceParams(**params)

        if not edge_params.enabled:
            return image

        enhanced = self.preprocessor._enhance_edges(image, method=edge_params.method)

        # Blend based on strength
        if edge_params.strength < 1.0:
            enhanced = cv2.addWeighted(
                image, 1 - edge_params.strength,
                enhanced, edge_params.strength, 0
            )

        return enhanced

    def _apply_despeckle(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply despeckle filter (remove small artifacts)."""
        despeckle_params = DespeckleParams(**params)

        if not despeckle_params.enabled:
            return image

        result = image.copy()

        for _ in range(despeckle_params.iterations):
            if len(result.shape) == 3:
                # Convert to grayscale for analysis
                gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
            else:
                gray = result

            # Detect small noise using morphological operations
            kernel = np.ones(
                (despeckle_params.size, despeckle_params.size), np.uint8
            )
            opening = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
            closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)

            if len(result.shape) == 3:
                closing = cv2.cvtColor(closing, cv2.COLOR_GRAY2BGR)

            result = closing

        return result

    def _apply_deskew(self, image: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply deskew (straighten tilted documents)."""
        deskew_params = DeskewParams(**params)

        if not deskew_params.enabled:
            return image

        if deskew_params.auto_detect:
            angle = self._detect_skew_angle(image)
        else:
            angle = 0  # Would need manual angle input

        if abs(angle) > 0.1:
            return self._rotate_image(image, angle)

        return image

    def _detect_skew_angle(self, image: np.ndarray) -> float:
        """Detect the skew angle of a document."""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Apply threshold
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return 0.0

        # Find the largest contour
        largest_contour = max(contours, key=cv2.contourArea)

        # Get minimum area rectangle
        rect = cv2.minAreaRect(largest_contour)
        angle = rect[2]

        # Normalize angle
        if angle < -45:
            angle = 90 + angle
        elif angle > 45:
            angle = angle - 90

        return angle

    def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Rotate image by given angle."""
        height, width = image.shape[:2]
        center = (width // 2, height // 2)

        # Get rotation matrix
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        # Calculate new bounding dimensions
        abs_cos = abs(rotation_matrix[0, 0])
        abs_sin = abs(rotation_matrix[0, 1])

        new_width = int(height * abs_sin + width * abs_cos)
        new_height = int(height * abs_cos + width * abs_sin)

        # Adjust rotation matrix
        rotation_matrix[0, 2] += new_width / 2 - center[0]
        rotation_matrix[1, 2] += new_height / 2 - center[1]

        # Rotate
        rotated = cv2.warpAffine(
            image, rotation_matrix, (new_width, new_height),
            borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255)
        )

        return rotated

    def _pil_to_cv2(self, pil_img: Image.Image) -> np.ndarray:
        """Convert PIL Image to OpenCV format."""
        rgb_img = pil_img.convert("RGB")
        np_img = np.array(rgb_img)
        return cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)

    def _cv2_to_pil(self, cv_img: np.ndarray) -> Image.Image:
        """Convert OpenCV image to PIL Image."""
        if len(cv_img.shape) == 2:
            return Image.fromarray(cv_img)
        else:
            rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb_img)

    def get_default_pipeline(self, quality_mode: str, image_type: str) -> PreprocessingPipeline:
        """Get default preprocessing pipeline for quality mode."""
        steps = []

        if quality_mode == "fast":
            # No preprocessing
            pass

        elif quality_mode == "standard":
            steps = [
                PreprocessingStep(
                    id=str(uuid.uuid4()),
                    name="color_reduce",
                    order=0,
                    enabled=image_type == "color",
                    params={"method": "kmeans", "max_colors": 32, "dithering": "none"},
                ),
                PreprocessingStep(
                    id=str(uuid.uuid4()),
                    name="denoise",
                    order=1,
                    enabled=True,
                    params={
                        "method": "bilateral",
                        "strength": "medium",
                        "preserve_edges": True,
                        "d": 9,
                        "sigma_color": 75,
                        "sigma_space": 75,
                    },
                ),
                PreprocessingStep(
                    id=str(uuid.uuid4()),
                    name="contrast",
                    order=2,
                    enabled=True,
                    params={
                        "method": "clahe",
                        "clip_limit": 2.0,
                        "tile_size": 8,
                    },
                ),
            ]

        elif quality_mode == "high":
            steps = [
                PreprocessingStep(
                    id=str(uuid.uuid4()),
                    name="color_reduce",
                    order=0,
                    enabled=image_type == "color",
                    params={"method": "kmeans", "max_colors": 128, "dithering": "none"},
                ),
                PreprocessingStep(
                    id=str(uuid.uuid4()),
                    name="denoise",
                    order=1,
                    enabled=True,
                    params={
                        "method": "nlm",
                        "strength": "heavy",
                        "preserve_edges": True,
                        "h": 10,
                        "template_window": 7,
                        "search_window": 21,
                    },
                ),
                PreprocessingStep(
                    id=str(uuid.uuid4()),
                    name="contrast",
                    order=2,
                    enabled=True,
                    params={
                        "method": "clahe",
                        "clip_limit": 3.0,
                        "tile_size": 8,
                    },
                ),
                PreprocessingStep(
                    id=str(uuid.uuid4()),
                    name="sharpen",
                    order=3,
                    enabled=True,
                    params={
                        "method": "unsharp_mask",
                        "amount": 1.5,
                        "kernel_size": 5,
                        "sigma": 1.0,
                    },
                ),
                PreprocessingStep(
                    id=str(uuid.uuid4()),
                    name="edge_enhance",
                    order=4,
                    enabled=True,
                    params={
                        "method": "laplacian",
                        "strength": 0.3,
                    },
                ),
            ]

        return PreprocessingPipeline(steps=steps)


class ColorPaletteExtractor:
    """Extract and manage color palettes from images."""

    def __init__(self):
        self.preprocessor = Preprocessor()

    def extract_palette(
        self,
        image: np.ndarray,
        max_colors: int = 32,
        include_percentages: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Extract dominant colors from image.

        Args:
            image: Input image
            max_colors: Maximum number of colors to extract
            include_percentages: Whether to calculate color percentages

        Returns:
            List of color information dictionaries
        """
        # Convert to RGB if needed
        if len(image.shape) == 3:
            if image.shape[2] == 3:
                # Assume BGR from OpenCV
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                rgb_image = image
        else:
            # Grayscale - convert to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

        # Reshape for k-means
        data = np.float32(rgb_image).reshape((-1, 3))

        # Apply k-means clustering
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
        _, labels, centers = cv2.kmeans(
            data, max_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
        )

        # Build palette
        palette = []
        total_pixels = len(labels)

        for i, center in enumerate(centers):
            r, g, b = int(center[0]), int(center[1]), int(center[2])
            hex_color = f"#{r:02x}{g:02x}{b:02x}"

            color_info = {
                "hex": hex_color,
                "rgb": [r, g, b],
            }

            if include_percentages:
                count = np.sum(labels == i)
                percentage = (count / total_pixels) * 100
                color_info["percentage"] = round(percentage, 2)

            palette.append(color_info)

        # Sort by percentage if available
        if include_percentages:
            palette.sort(key=lambda x: x["percentage"], reverse=True)

        return palette

    def apply_palette(
        self,
        image: np.ndarray,
        palette_config: ColorPaletteConfig,
    ) -> np.ndarray:
        """
        Apply color palette configuration to image.

        Args:
            image: Input image
            palette_config: Color palette configuration

        Returns:
            Image with applied palette
        """
        if palette_config.mode == "preserve":
            return image

        max_colors = palette_config.max_colors

        if palette_config.mode == "custom" and palette_config.custom_colors:
            # Use custom colors
            colors = [
                [int(color[i:i+2], 16) for i in (1, 3, 5)]  # Convert hex to RGB
                for color in palette_config.custom_colors
            ]
            return self._apply_custom_palette(image, colors)

        else:
            # Auto or extract - use k-means
            return self.preprocessor._reduce_colors_kmeans(image, max_colors=max_colors)

    def _apply_custom_palette(
        self,
        image: np.ndarray,
        colors: List[List[int]],
    ) -> np.ndarray:
        """Apply a custom color palette to an image."""
        # Convert colors to numpy array
        palette = np.array(colors, dtype=np.float32)

        # Reshape image data
        data = np.float32(image).reshape((-1, 3))

        # Find nearest color for each pixel
        distances = np.sqrt(((data[:, np.newaxis, :] - palette) ** 2).sum(axis=2))
        nearest = np.argmin(distances, axis=1)

        # Apply palette colors
        result = palette[nearest].reshape(image.shape).astype(np.uint8)

        return result


class ImageAnalyzer:
    """Analyze images to recommend optimal settings."""

    def analyze(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Analyze image characteristics.

        Args:
            image: Input image

        Returns:
            Dictionary with analysis results
        """
        analysis = {}

        # Basic info
        analysis["shape"] = image.shape
        analysis["channels"] = 1 if len(image.shape) == 2 else image.shape[2]

        # Convert to grayscale for analysis
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Brightness
        analysis["brightness"] = round(np.mean(gray) / 255, 3)

        # Contrast
        analysis["contrast"] = round(np.std(gray) / 128, 3)

        # Sharpness (using Laplacian variance)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        analysis["sharpness"] = round(min(laplacian_var / 500, 1.0), 3)

        # Color complexity
        if len(image.shape) == 3:
            # Count unique colors (downsample for performance)
            small = cv2.resize(image, (100, 100))
            unique_colors = len(np.unique(small.reshape(-1, 3), axis=0))
            analysis["unique_colors"] = unique_colors
            analysis["color_complexity"] = round(min(unique_colors / 1000, 1.0), 3)
            analysis["is_grayscale"] = unique_colors < 256
        else:
            analysis["unique_colors"] = len(np.unique(gray))
            analysis["color_complexity"] = 0.0
            analysis["is_grayscale"] = True

        # Noise level
        noise = self._estimate_noise(gray)
        analysis["noise_level"] = round(noise, 3)

        # Edge density (line art detection)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        analysis["edge_density"] = round(edge_density, 3)
        analysis["is_line_art"] = edge_density > 0.1 and analysis["color_complexity"] < 0.3

        # Photo detection
        analysis["is_photo"] = (
            analysis["color_complexity"] > 0.5 and
            analysis["unique_colors"] > 1000 and
            not analysis["is_line_art"]
        )

        # Text detection (simplified)
        analysis["has_text"] = self._detect_text_regions(gray)

        # Recommendations
        analysis["recommended_mode"] = self._recommend_mode(analysis)
        analysis["suggested_filters"] = self._suggest_filters(analysis)

        return analysis

    def _estimate_noise(self, gray: np.ndarray) -> float:
        """Estimate noise level in image."""
        # Use median absolute deviation
        median = cv2.medianBlur(gray, 3)
        diff = np.abs(gray.astype(np.float32) - median.astype(np.float32))
        mad = np.median(diff)
        noise = min(mad / 30, 1.0)  # Normalize
        return noise

    def _detect_text_regions(self, gray: np.ndarray) -> bool:
        """Simple text region detection."""
        # Use MSER to detect text-like regions
        mser = cv2.MSER_create()
        regions, _ = mser.detectRegions(gray)

        # Count regions that could be text
        text_like_regions = 0
        for region in regions:
            if 10 < len(region) < 1000:
                text_like_regions += 1

        return text_like_regions > 10

    def _recommend_mode(self, analysis: Dict[str, Any]) -> str:
        """Recommend quality mode based on analysis."""
        if analysis["is_line_art"]:
            return "fast"  # Line art usually doesn't need preprocessing
        elif analysis["noise_level"] > 0.3 or analysis["is_photo"]:
            return "high"
        elif analysis["color_complexity"] > 0.5:
            return "standard"
        else:
            return "standard"

    def _suggest_filters(self, analysis: Dict[str, Any]) -> List[str]:
        """Suggest preprocessing filters based on analysis."""
        suggestions = []

        if analysis["noise_level"] > 0.2:
            suggestions.append("denoise")

        if analysis["contrast"] < 0.3:
            suggestions.append("contrast")

        if analysis["sharpness"] < 0.3:
            suggestions.append("sharpen")

        if analysis["color_complexity"] > 0.7:
            suggestions.append("color_reduce")

        if analysis.get("is_photo", False):
            suggestions.append("edge_enhance")

        return suggestions
