"""Image preprocessing service with advanced enhancement techniques."""

import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)


class DenoiseMethod(Enum):
    """Denoising methods."""

    GAUSSIAN = "gaussian"
    BILATERAL = "bilateral"
    NLM = "nlm"
    MEDIAN = "median"


class ContrastMethod(Enum):
    """Contrast enhancement methods."""

    CLAHE = "clahe"
    HISTOGRAM = "histogram"
    LEVELS = "levels"
    SIGMOID = "sigmoid"


class ThresholdMethod(Enum):
    """Thresholding methods for monochrome conversion."""

    OTSU = "otsu"
    ADAPTIVE = "adaptive"
    ADAPTIVE_GAUSSIAN = "adaptive_gaussian"
    MANUAL = "manual"


class DitherMethod(Enum):
    """Dithering methods."""

    FLOYD_STEINBERG = "floyd-steinberg"
    BAYER = "bayer"
    ATKINSON = "atkinson"
    ORDERED = "ordered"


class Preprocessor:
    """
    Image preprocessing pipeline with advanced enhancement techniques.

    Supports three quality modes:
    - Fast: No preprocessing
    - Standard: Color reduction + denoise + contrast
    - High: Standard + sharpening + edge enhancement + dithering
    """

    def __init__(self):
        self.denoise_methods: Dict[DenoiseMethod, Callable] = {
            DenoiseMethod.GAUSSIAN: self._denoise_gaussian,
            DenoiseMethod.BILATERAL: self._denoise_bilateral,
            DenoiseMethod.NLM: self._denoise_nlm,
            DenoiseMethod.MEDIAN: self._denoise_median,
        }

        self.contrast_methods: Dict[ContrastMethod, Callable] = {
            ContrastMethod.CLAHE: self._enhance_clahe,
            ContrastMethod.HISTOGRAM: self._enhance_histogram,
            ContrastMethod.LEVELS: self._enhance_levels,
            ContrastMethod.SIGMOID: self._enhance_sigmoid,
        }

    # ========================================================================
    # Main Pipeline Methods
    # ========================================================================

    def preprocess(
        self,
        image_path: str,
        image_type: str,
        quality_mode: str,
    ) -> np.ndarray:
        """
        Apply preprocessing pipeline based on quality mode.

        Args:
            image_path: Path to input image
            image_type: Type of image (color/monochrome)
            quality_mode: Quality mode (fast/standard/high)

        Returns:
            Preprocessed image as numpy array
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")

        return self.preprocess_array(img, image_type, quality_mode)

    def preprocess_pil(
        self,
        image: Image.Image,
        image_type: str,
        quality_mode: str,
    ) -> Image.Image:
        """
        Apply preprocessing pipeline to a PIL Image.

        Args:
            image: PIL Image object
            image_type: Type of image (color/monochrome)
            quality_mode: Quality mode (fast/standard/high)

        Returns:
            Preprocessed PIL Image
        """
        # Convert PIL to numpy for processing
        img_array = self._pil_to_cv2(image)

        # Process
        result_array = self.preprocess_array(img_array, image_type, quality_mode)

        # Convert back to PIL
        return self._cv2_to_pil(result_array)

    def preprocess_array(
        self,
        image: np.ndarray,
        image_type: str,
        quality_mode: str,
    ) -> np.ndarray:
        """
        Apply preprocessing pipeline to a numpy array (OpenCV format).

        Args:
            image: OpenCV image (BGR format)
            image_type: Type of image (color/monochrome)
            quality_mode: Quality mode (fast/standard/high)

        Returns:
            Preprocessed image as numpy array
        """
        # Fast mode: skip preprocessing
        if quality_mode == "fast":
            return image

        logger.info(f"Preprocessing: {image_type} image with {quality_mode} quality")
        img = image.copy()

        if quality_mode == "standard":
            img = self._apply_standard_pipeline(img, image_type)
        elif quality_mode == "high":
            img = self._apply_high_pipeline(img, image_type)

        return img

    def _apply_standard_pipeline(self, img: np.ndarray, image_type: str) -> np.ndarray:
        """Apply standard preprocessing pipeline."""
        # Color reduction for color images
        if image_type == "color" and len(img.shape) == 3:
            img = self._reduce_colors_kmeans(img, max_colors=32)

        # Denoise with bilateral filter (edge-preserving)
        img = self._denoise_bilateral(img, d=9, sigma_color=75, sigma_space=75)

        # Enhance contrast with CLAHE
        img = self._enhance_clahe(img, clip_limit=2.0, tile_size=8)

        return img

    def _apply_high_pipeline(self, img: np.ndarray, image_type: str) -> np.ndarray:
        """Apply high-quality preprocessing pipeline."""
        # Color reduction with more colors
        if image_type == "color" and len(img.shape) == 3:
            img = self._reduce_colors_kmeans(img, max_colors=128)

        # Heavy denoise with NLM
        if len(img.shape) == 3:
            img = self._denoise_nlm(img, h=10)
        else:
            img = self._denoise_nlm(img, h=10)

        # Enhance contrast more aggressively
        img = self._enhance_clahe(img, clip_limit=3.0, tile_size=8)

        # Sharpen edges
        img = self._sharpen_unsharp_mask(img, kernel_size=5, sigma=1.0, amount=1.5)

        # Edge enhancement
        img = self._enhance_edges(img, method="laplacian")

        return img

    # ========================================================================
    # Color Reduction
    # ========================================================================

    def _reduce_colors_kmeans(
        self, image: np.ndarray, max_colors: int = 32, attempts: int = 10
    ) -> np.ndarray:
        """
        Reduce color palette using k-means clustering.

        Args:
            image: Input image (BGR)
            max_colors: Maximum number of colors
            attempts: Number of k-means attempts

        Returns:
            Color-reduced image
        """
        data = np.float32(image).reshape((-1, 3))
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)

        _, labels, centers = cv2.kmeans(
            data, max_colors, None, criteria, attempts, cv2.KMEANS_RANDOM_CENTERS
        )

        centers = np.uint8(centers)
        result = centers[labels.flatten()]
        result = result.reshape(image.shape)

        logger.debug(f"Reduced colors to {max_colors}")
        return result

    def _reduce_colors_median_cut(self, image: np.ndarray, max_colors: int = 32) -> np.ndarray:
        """
        Reduce colors using median cut algorithm (faster than k-means).

        Args:
            image: Input image (BGR)
            max_colors: Maximum number of colors

        Returns:
            Color-reduced image
        """
        # Convert to PIL for quantization
        pil_img = self._cv2_to_pil(image)
        pil_img = pil_img.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
        pil_img = pil_img.convert("RGB")

        return self._pil_to_cv2(pil_img)

    # ========================================================================
    # Noise Reduction
    # ========================================================================

    def _denoise_gaussian(
        self, image: np.ndarray, kernel_size: int = 5, sigma: float = 1.0
    ) -> np.ndarray:
        """
        Apply Gaussian blur denoising.

        Args:
            image: Input image
            kernel_size: Gaussian kernel size (must be odd)
            sigma: Standard deviation

        Returns:
            Denoised image
        """
        kernel_size = max(3, kernel_size if kernel_size % 2 == 1 else kernel_size + 1)
        return cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)

    def _denoise_bilateral(
        self, image: np.ndarray, d: int = 9, sigma_color: float = 75, sigma_space: float = 75
    ) -> np.ndarray:
        """
        Apply bilateral filter (edge-preserving denoising).

        Args:
            image: Input image
            d: Diameter of pixel neighborhood
            sigma_color: Filter sigma in color space
            sigma_space: Filter sigma in coordinate space

        Returns:
            Denoised image
        """
        return cv2.bilateralFilter(image, d, sigma_color, sigma_space)

    def _denoise_nlm(
        self, image: np.ndarray, h: float = 10, template_window: int = 7, search_window: int = 21
    ) -> np.ndarray:
        """
        Apply Non-Local Means denoising (high quality, slow).

        Args:
            image: Input image
            h: Filter strength
            template_window: Template patch size
            search_window: Search window size

        Returns:
            Denoised image
        """
        if len(image.shape) == 3:
            return cv2.fastNlMeansDenoisingColored(
                image, None, h, h, template_window, search_window
            )
        else:
            return cv2.fastNlMeansDenoising(image, None, h, template_window, search_window)

    def _denoise_median(self, image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
        """
        Apply median filter (good for salt-and-pepper noise).

        Args:
            image: Input image
            kernel_size: Kernel size (must be odd)

        Returns:
            Denoised image
        """
        kernel_size = max(3, kernel_size if kernel_size % 2 == 1 else kernel_size + 1)
        return cv2.medianBlur(image, kernel_size)

    # ========================================================================
    # Contrast Enhancement
    # ========================================================================

    def _enhance_clahe(
        self, image: np.ndarray, clip_limit: float = 2.0, tile_size: int = 8
    ) -> np.ndarray:
        """
        Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).

        Args:
            image: Input image
            clip_limit: Threshold for contrast limiting
            tile_size: Size of grid for histogram equalization

        Returns:
            Enhanced image
        """
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))

        if len(image.shape) == 3:
            # Convert to LAB color space
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            lab_planes = list(cv2.split(lab))
            lab_planes[0] = clahe.apply(lab_planes[0])
            lab = cv2.merge(lab_planes)
            return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        else:
            return clahe.apply(image)

    def _enhance_histogram(self, image: np.ndarray) -> np.ndarray:
        """Apply histogram equalization."""
        if len(image.shape) == 3:
            # Equalize each channel
            channels = cv2.split(image)
            eq_channels = [cv2.equalizeHist(ch) for ch in channels]
            return cv2.merge(eq_channels)
        else:
            return cv2.equalizeHist(image)

    def _enhance_levels(
        self,
        image: np.ndarray,
        in_min: int = 0,
        in_max: int = 255,
        out_min: int = 0,
        out_max: int = 255,
    ) -> np.ndarray:
        """
        Apply levels adjustment (min/max stretching).

        Args:
            image: Input image
            in_min: Input black point
            in_max: Input white point
            out_min: Output black point
            out_max: Output white point

        Returns:
            Enhanced image
        """
        alpha = (out_max - out_min) / (in_max - in_min)
        beta = out_min - alpha * in_min
        return cv2.convertScaleAbs(image, alpha=alpha, beta=beta)

    def _enhance_sigmoid(
        self, image: np.ndarray, contrast: float = 10.0, midpoint: float = 0.5
    ) -> np.ndarray:
        """
        Apply sigmoid contrast enhancement (S-curve).

        Args:
            image: Input image
            contrast: Contrast strength
            midpoint: Midpoint of the curve (0-1)

        Returns:
            Enhanced image
        """
        normalized = image / 255.0
        sigmoid = 1 / (1 + np.exp(-contrast * (normalized - midpoint)))
        return (sigmoid * 255).astype(np.uint8)

    # ========================================================================
    # Sharpening & Edge Enhancement
    # ========================================================================

    def _sharpen_unsharp_mask(
        self, image: np.ndarray, kernel_size: int = 5, sigma: float = 1.0, amount: float = 1.0
    ) -> np.ndarray:
        """
        Apply unsharp mask sharpening.

        Args:
            image: Input image
            kernel_size: Gaussian kernel size
            sigma: Gaussian sigma
            amount: Sharpening strength

        Returns:
            Sharpened image
        """
        blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)
        sharpened = cv2.addWeighted(image, 1 + amount, blurred, -amount, 0)
        return sharpened

    def _sharpen_kernel(self, image: np.ndarray, kernel: Optional[np.ndarray] = None) -> np.ndarray:
        """Apply custom sharpening kernel."""
        if kernel is None:
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        return cv2.filter2D(image, -1, kernel)

    def _enhance_edges(
        self, image: np.ndarray, method: Literal["laplacian", "sobel", "scharr"] = "laplacian"
    ) -> np.ndarray:
        """
        Enhance edges using gradient operators.

        Args:
            image: Input image
            method: Edge detection method

        Returns:
            Edge-enhanced image
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        if method == "laplacian":
            edges = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
        elif method == "sobel":
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            edges = np.sqrt(sobelx**2 + sobely**2)
        elif method == "scharr":
            scharrx = cv2.Scharr(gray, cv2.CV_64F, 1, 0)
            scharry = cv2.Scharr(gray, cv2.CV_64F, 0, 1)
            edges = np.sqrt(scharrx**2 + scharry**2)
        else:
            raise ValueError(f"Unknown edge method: {method}")

        # Normalize and blend with original
        edges = cv2.normalize(edges, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)

        if len(image.shape) == 3:
            edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

        # Blend with original (30% edges, 70% original)
        return cv2.addWeighted(image, 0.7, edges, 0.3, 0)

    # ========================================================================
    # Monochrome Conversion
    # ========================================================================

    def convert_to_monochrome(
        self,
        image: np.ndarray,
        method: ThresholdMethod = ThresholdMethod.OTSU,
        threshold: Optional[int] = None,
    ) -> np.ndarray:
        """
        Convert image to monochrome (binary).

        Args:
            image: Input image
            method: Thresholding method
            threshold: Manual threshold value (0-255)

        Returns:
            Binary image
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        if method == ThresholdMethod.OTSU:
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif method == ThresholdMethod.ADAPTIVE:
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2
            )
        elif method == ThresholdMethod.ADAPTIVE_GAUSSIAN:
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
        elif method == ThresholdMethod.MANUAL:
            if threshold is None:
                threshold = 128
            _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        else:
            raise ValueError(f"Unknown threshold method: {method}")

        return binary

    # ========================================================================
    # Dithering
    # ========================================================================

    def apply_dithering(
        self, image: np.ndarray, method: DitherMethod = DitherMethod.FLOYD_STEINBERG
    ) -> np.ndarray:
        """
        Apply dithering to grayscale image.

        Args:
            image: Input image (grayscale or color)
            method: Dithering algorithm

        Returns:
            Dithered binary image
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        if method == DitherMethod.FLOYD_STEINBERG:
            return self._dither_floyd_steinberg(gray)
        elif method == DitherMethod.BAYER:
            return self._dither_bayer(gray)
        elif method == DitherMethod.ATKINSON:
            return self._dither_atkinson(gray)
        elif method == DitherMethod.ORDERED:
            return self._dither_ordered(gray)
        else:
            raise ValueError(f"Unknown dither method: {method}")

    def _dither_floyd_steinberg(self, image: np.ndarray) -> np.ndarray:
        """Apply Floyd-Steinberg error diffusion dithering."""
        img = image.astype(np.float32)
        height, width = img.shape

        for y in range(height - 1):
            for x in range(1, width - 1):
                old_pixel = img[y, x]
                new_pixel = 255 if old_pixel > 127 else 0
                img[y, x] = new_pixel

                error = old_pixel - new_pixel

                # Distribute error
                img[y, x + 1] += error * 7 / 16
                img[y + 1, x - 1] += error * 3 / 16
                img[y + 1, x] += error * 5 / 16
                img[y + 1, x + 1] += error * 1 / 16

        return np.clip(img, 0, 255).astype(np.uint8)

    def _dither_bayer(self, image: np.ndarray, threshold: int = 128) -> np.ndarray:
        """Apply Bayer ordered dithering."""
        # 4x4 Bayer matrix
        bayer = (
            np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 * 255
        )

        height, width = image.shape
        result = np.zeros((height, width), dtype=np.uint8)

        for y in range(height):
            for x in range(width):
                threshold_value = bayer[y % 4, x % 4]
                result[y, x] = 255 if image[y, x] > threshold_value else 0

        return result

    def _dither_atkinson(self, image: np.ndarray) -> np.ndarray:
        """Apply Atkinson dithering (reduced artifact version of Floyd-Steinberg)."""
        img = image.astype(np.float32)
        height, width = img.shape

        for y in range(height - 2):
            for x in range(1, width - 2):
                old_pixel = img[y, x]
                new_pixel = 255 if old_pixel > 127 else 0
                img[y, x] = new_pixel

                error = (old_pixel - new_pixel) / 8

                # Distribute error to 6 neighbors
                img[y, x + 1] += error
                img[y, x + 2] += error
                img[y + 1, x - 1] += error
                img[y + 1, x] += error
                img[y + 1, x + 1] += error
                img[y + 2, x] += error

        return np.clip(img, 0, 255).astype(np.uint8)

    def _dither_ordered(self, image: np.ndarray) -> np.ndarray:
        """Apply simple ordered dithering using PIL."""
        pil_img = Image.fromarray(image)
        pil_img = pil_img.convert("1", dither=Image.Dither.ORDERED)
        return np.array(pil_img).astype(np.uint8) * 255

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _pil_to_cv2(self, pil_img: Image.Image) -> np.ndarray:
        """Convert PIL Image to OpenCV format (BGR)."""
        rgb_img = pil_img.convert("RGB")
        np_img = np.array(rgb_img)
        return cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)

    def _cv2_to_pil(self, cv_img: np.ndarray) -> Image.Image:
        """Convert OpenCV image (BGR) to PIL Image."""
        if len(cv_img.shape) == 2:
            # Grayscale
            return Image.fromarray(cv_img)
        else:
            rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb_img)

    def get_image_info(self, image: np.ndarray) -> Dict[str, Any]:
        """Get information about an image."""
        info = {
            "shape": image.shape,
            "dtype": str(image.dtype),
            "channels": 1 if len(image.shape) == 2 else image.shape[2],
        }

        if len(image.shape) == 3:
            info["height"] = image.shape[0]
            info["width"] = image.shape[1]
        else:
            info["height"] = image.shape[0]
            info["width"] = image.shape[1]

        return info

    def compare_methods(
        self, image_path: str, output_dir: str, methods: List[str]
    ) -> Dict[str, str]:
        """
        Compare different preprocessing methods and save results.

        Args:
            image_path: Path to input image
            output_dir: Directory to save comparison images
            methods: List of method names to compare

        Returns:
            Dictionary mapping method names to output file paths
        """
        import os

        os.makedirs(output_dir, exist_ok=True)

        img = cv2.imread(image_path)
        results = {}

        for method in methods:
            try:
                if method == "gaussian":
                    result = self._denoise_gaussian(img)
                elif method == "bilateral":
                    result = self._denoise_bilateral(img)
                elif method == "nlm":
                    result = self._denoise_nlm(img)
                elif method == "clahe":
                    result = self._enhance_clahe(img)
                elif method == "sharpen":
                    result = self._sharpen_unsharp_mask(img)
                elif method == "kmeans":
                    result = self._reduce_colors_kmeans(img)
                else:
                    continue

                output_path = os.path.join(output_dir, f"{method}.png")
                cv2.imwrite(output_path, result)
                results[method] = output_path

            except Exception as e:
                logger.error(f"Failed to apply {method}: {e}")

        return results
