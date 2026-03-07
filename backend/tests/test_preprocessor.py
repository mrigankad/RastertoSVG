"""Tests for the preprocessor service."""

import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from app.services.preprocessor import (
    Preprocessor,
    DenoiseMethod,
    ContrastMethod,
    ThresholdMethod,
    DitherMethod,
)


class TestPreprocessor:
    """Test cases for Preprocessor class."""

    @pytest.fixture
    def preprocessor(self):
        """Create a preprocessor instance."""
        return Preprocessor()

    @pytest.fixture
    def sample_color_image(self):
        """Create a sample color image."""
        return np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)

    @pytest.fixture
    def sample_grayscale_image(self):
        """Create a sample grayscale image."""
        return np.random.randint(0, 255, (100, 100), dtype=np.uint8)

    # Color Reduction Tests
    def test_reduce_colors_kmeans(self, preprocessor, sample_color_image):
        """Test k-means color reduction."""
        result = preprocessor._reduce_colors_kmeans(sample_color_image, max_colors=8)
        assert result.shape == sample_color_image.shape
        assert result.dtype == np.uint8

    def test_reduce_colors_median_cut(self, preprocessor, sample_color_image):
        """Test median cut color reduction."""
        result = preprocessor._reduce_colors_median_cut(sample_color_image, max_colors=8)
        assert result.shape == sample_color_image.shape
        assert result.dtype == np.uint8

    # Denoise Tests
    def test_denoise_gaussian(self, preprocessor, sample_color_image):
        """Test Gaussian denoising."""
        result = preprocessor._denoise_gaussian(sample_color_image, kernel_size=5, sigma=1.0)
        assert result.shape == sample_color_image.shape

    def test_denoise_bilateral(self, preprocessor, sample_color_image):
        """Test bilateral denoising."""
        result = preprocessor._denoise_bilateral(sample_color_image, d=9, sigma_color=75, sigma_space=75)
        assert result.shape == sample_color_image.shape

    def test_denoise_nlm(self, preprocessor, sample_color_image):
        """Test Non-Local Means denoising."""
        result = preprocessor._denoise_nlm(sample_color_image, h=10)
        assert result.shape == sample_color_image.shape

    def test_denoise_median(self, preprocessor, sample_color_image):
        """Test median denoising."""
        result = preprocessor._denoise_median(sample_color_image, kernel_size=5)
        assert result.shape == sample_color_image.shape

    # Contrast Enhancement Tests
    def test_enhance_clahe_color(self, preprocessor, sample_color_image):
        """Test CLAHE on color image."""
        result = preprocessor._enhance_clahe(sample_color_image, clip_limit=2.0)
        assert result.shape == sample_color_image.shape

    def test_enhance_clahe_grayscale(self, preprocessor, sample_grayscale_image):
        """Test CLAHE on grayscale image."""
        result = preprocessor._enhance_clahe(sample_grayscale_image, clip_limit=2.0)
        assert result.shape == sample_grayscale_image.shape

    def test_enhance_histogram(self, preprocessor, sample_color_image):
        """Test histogram equalization."""
        result = preprocessor._enhance_histogram(sample_color_image)
        assert result.shape == sample_color_image.shape

    def test_enhance_levels(self, preprocessor, sample_color_image):
        """Test levels adjustment."""
        result = preprocessor._enhance_levels(sample_color_image, in_min=10, in_max=240)
        assert result.shape == sample_color_image.shape

    def test_enhance_sigmoid(self, preprocessor, sample_color_image):
        """Test sigmoid contrast enhancement."""
        result = preprocessor._enhance_sigmoid(sample_color_image, contrast=10.0)
        assert result.shape == sample_color_image.shape

    # Sharpening Tests
    def test_sharpen_unsharp_mask(self, preprocessor, sample_color_image):
        """Test unsharp mask sharpening."""
        result = preprocessor._sharpen_unsharp_mask(sample_color_image, kernel_size=5, sigma=1.0, amount=1.5)
        assert result.shape == sample_color_image.shape

    def test_sharpen_kernel(self, preprocessor, sample_color_image):
        """Test custom sharpening kernel."""
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        result = preprocessor._sharpen_kernel(sample_color_image, kernel)
        assert result.shape == sample_color_image.shape

    # Edge Enhancement Tests
    def test_enhance_edges_laplacian(self, preprocessor, sample_color_image):
        """Test Laplacian edge enhancement."""
        result = preprocessor._enhance_edges(sample_color_image, method="laplacian")
        assert result.shape == sample_color_image.shape

    def test_enhance_edges_sobel(self, preprocessor, sample_color_image):
        """Test Sobel edge enhancement."""
        result = preprocessor._enhance_edges(sample_color_image, method="sobel")
        assert result.shape == sample_color_image.shape

    def test_enhance_edges_scharr(self, preprocessor, sample_color_image):
        """Test Scharr edge enhancement."""
        result = preprocessor._enhance_edges(sample_color_image, method="scharr")
        assert result.shape == sample_color_image.shape

    def test_enhance_edges_invalid(self, preprocessor, sample_color_image):
        """Test edge enhancement with invalid method."""
        with pytest.raises(ValueError):
            preprocessor._enhance_edges(sample_color_image, method="invalid")

    # Monochrome Conversion Tests
    def test_convert_to_monochrome_otsu(self, preprocessor, sample_color_image):
        """Test Otsu thresholding."""
        result = preprocessor.convert_to_monochrome(sample_color_image, method=ThresholdMethod.OTSU)
        assert len(result.shape) == 2
        assert result.dtype == np.uint8

    def test_convert_to_monochrome_adaptive(self, preprocessor, sample_color_image):
        """Test adaptive thresholding."""
        result = preprocessor.convert_to_monochrome(sample_color_image, method=ThresholdMethod.ADAPTIVE)
        assert len(result.shape) == 2
        assert result.dtype == np.uint8

    def test_convert_to_monochrome_manual(self, preprocessor, sample_color_image):
        """Test manual thresholding."""
        result = preprocessor.convert_to_monochrome(sample_color_image, method=ThresholdMethod.MANUAL, threshold=128)
        assert len(result.shape) == 2
        assert result.dtype == np.uint8

    def test_convert_to_monochrome_grayscale_input(self, preprocessor, sample_grayscale_image):
        """Test monochrome conversion with grayscale input."""
        result = preprocessor.convert_to_monochrome(sample_grayscale_image, method=ThresholdMethod.OTSU)
        assert len(result.shape) == 2

    # Dithering Tests
    def test_apply_dithering_floyd_steinberg(self, preprocessor, sample_color_image):
        """Test Floyd-Steinberg dithering."""
        result = preprocessor.apply_dithering(sample_color_image, method=DitherMethod.FLOYD_STEINBERG)
        assert len(result.shape) == 2
        assert result.dtype == np.uint8

    def test_apply_dithering_bayer(self, preprocessor, sample_color_image):
        """Test Bayer dithering."""
        result = preprocessor.apply_dithering(sample_color_image, method=DitherMethod.BAYER)
        assert len(result.shape) == 2
        assert result.dtype == np.uint8

    def test_apply_dithering_atkinson(self, preprocessor, sample_color_image):
        """Test Atkinson dithering."""
        result = preprocessor.apply_dithering(sample_color_image, method=DitherMethod.ATKINSON)
        assert len(result.shape) == 2
        assert result.dtype == np.uint8

    def test_apply_dithering_ordered(self, preprocessor, sample_color_image):
        """Test ordered dithering."""
        result = preprocessor.apply_dithering(sample_color_image, method=DitherMethod.ORDERED)
        assert len(result.shape) == 2
        assert result.dtype == np.uint8

    def test_apply_dithering_grayscale_input(self, preprocessor, sample_grayscale_image):
        """Test dithering with grayscale input."""
        result = preprocessor.apply_dithering(sample_grayscale_image, method=DitherMethod.FLOYD_STEINBERG)
        assert len(result.shape) == 2

    # Pipeline Tests
    def test_preprocess_array_fast(self, preprocessor, sample_color_image):
        """Test fast pipeline (should return original)."""
        result = preprocessor.preprocess_array(sample_color_image, "color", "fast")
        assert np.array_equal(result, sample_color_image)

    def test_preprocess_array_standard(self, preprocessor, sample_color_image):
        """Test standard pipeline."""
        result = preprocessor.preprocess_array(sample_color_image, "color", "standard")
        assert result.shape == sample_color_image.shape

    def test_preprocess_array_high(self, preprocessor, sample_color_image):
        """Test high quality pipeline."""
        result = preprocessor.preprocess_array(sample_color_image, "color", "high")
        assert result.shape == sample_color_image.shape

    def test_preprocess_array_monochrome(self, preprocessor, sample_color_image):
        """Test pipeline with monochrome image."""
        result = preprocessor.preprocess_array(sample_color_image, "monochrome", "standard")
        assert result.shape == sample_color_image.shape

    # Utility Tests
    def test_pil_to_cv2(self, preprocessor):
        """Test PIL to OpenCV conversion."""
        pil_img = Image.new('RGB', (100, 100), color='red')
        cv_img = preprocessor._pil_to_cv2(pil_img)
        assert isinstance(cv_img, np.ndarray)
        assert cv_img.shape == (100, 100, 3)

    def test_cv2_to_pil(self, preprocessor, sample_color_image):
        """Test OpenCV to PIL conversion."""
        pil_img = preprocessor._cv2_to_pil(sample_color_image)
        assert isinstance(pil_img, Image.Image)

    def test_cv2_to_pil_grayscale(self, preprocessor, sample_grayscale_image):
        """Test grayscale OpenCV to PIL conversion."""
        pil_img = preprocessor._cv2_to_pil(sample_grayscale_image)
        assert isinstance(pil_img, Image.Image)
        assert pil_img.mode == 'L'

    def test_get_image_info_color(self, preprocessor, sample_color_image):
        """Test getting image info for color image."""
        info = preprocessor.get_image_info(sample_color_image)
        assert info["shape"] == (100, 100, 3)
        assert info["channels"] == 3
        assert info["width"] == 100
        assert info["height"] == 100

    def test_get_image_info_grayscale(self, preprocessor, sample_grayscale_image):
        """Test getting image info for grayscale image."""
        info = preprocessor.get_image_info(sample_grayscale_image)
        assert info["shape"] == (100, 100)
        assert info["channels"] == 1
        assert info["width"] == 100
        assert info["height"] == 100

    def test_compare_methods(self, preprocessor, tmp_path):
        """Test method comparison."""
        # Create test image
        test_img = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        input_path = tmp_path / "test.png"
        cv2.imwrite(str(input_path), test_img)

        output_dir = tmp_path / "output"
        methods = ["gaussian", "bilateral", "clahe"]
        
        results = preprocessor.compare_methods(str(input_path), str(output_dir), methods)
        
        assert len(results) == len(methods)
        for method in methods:
            assert method in results
            assert Path(results[method]).exists()
