"""Tests for the converter service."""

import tempfile
from pathlib import Path

import pytest
from PIL import Image

from app.services.converter import Converter


class TestConverter:
    """Test cases for Converter class."""

    @pytest.fixture
    def converter(self):
        """Create a converter instance."""
        return Converter()

    @pytest.fixture
    def sample_color_image(self):
        """Create a sample color image."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new('RGB', (100, 100), color='red')
            img.save(f.name)
            return f.name

    @pytest.fixture
    def sample_grayscale_image(self):
        """Create a sample grayscale image."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new('L', (100, 100), color=128)
            img.save(f.name)
            return f.name

    @pytest.fixture
    def sample_bw_image(self):
        """Create a sample black and white image."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new('1', (100, 100), color=1)
            img.save(f.name)
            return f.name

    def test_detect_image_type_color(self, converter, sample_color_image):
        """Test color image detection."""
        result = converter._detect_image_type(sample_color_image)
        assert result == "color"

    def test_detect_image_type_monochrome(self, converter, sample_grayscale_image):
        """Test monochrome image detection."""
        result = converter._detect_image_type(sample_grayscale_image)
        assert result == "monochrome"

    def test_detect_image_type_bw(self, converter, sample_bw_image):
        """Test black and white image detection."""
        result = converter._detect_image_type(sample_bw_image)
        assert result == "monochrome"

    def test_is_grayscale_image_true(self, converter, sample_grayscale_image):
        """Test grayscale detection with grayscale image."""
        img = Image.open(sample_grayscale_image)
        rgb_img = img.convert('RGB')
        assert converter._is_grayscale_image(rgb_img) is True

    def test_is_grayscale_image_false(self, converter, sample_color_image):
        """Test grayscale detection with color image."""
        img = Image.open(sample_color_image)
        assert converter._is_grayscale_image(img) is False

    def test_validate_input_valid(self, converter, sample_color_image):
        """Test input validation with valid file."""
        result = converter.validate_input(sample_color_image)
        assert result["valid"] is True
        assert "format" in result
        assert "size" in result

    def test_validate_input_invalid(self, converter):
        """Test input validation with invalid file."""
        result = converter.validate_input("/nonexistent/file.png")
        assert result["valid"] is False
        assert "error" in result

    def test_convert_file_not_found(self, converter):
        """Test conversion with non-existent file."""
        with pytest.raises(FileNotFoundError):
            converter.convert("/nonexistent/file.png", "/tmp/out.svg")

    def test_get_engine_info(self, converter):
        """Test getting engine information."""
        info = converter.get_engine_info()
        assert "vtracer" in info
        assert "potrace" in info
        assert "available" in info["vtracer"]
        assert "available" in info["potrace"]


class TestConverterIntegration:
    """Integration tests that require VTracer and Potrace."""

    @pytest.fixture
    def converter(self):
        return Converter()

    @pytest.fixture
    def sample_color_image(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new('RGB', (100, 100), color='red')
            img.save(f.name)
            return f.name

    def test_convert_color_image(self, converter, sample_color_image):
        """Test color image conversion (requires VTracer)."""
        engine_info = converter.get_engine_info()
        if not engine_info["vtracer"]["available"]:
            pytest.skip("VTracer not installed")

        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            output_path = f.name

        try:
            result = converter.convert(
                sample_color_image,
                output_path,
                image_type="color",
                quality_mode="fast"
            )

            assert result["success"] is True
            assert result["image_type"] == "color"
            assert Path(output_path).exists()

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_convert_monochrome_image(self, converter):
        """Test monochrome image conversion (requires Potrace)."""
        engine_info = converter.get_engine_info()
        if not engine_info["potrace"]["available"]:
            pytest.skip("Potrace not installed")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new('L', (100, 100), color=128)
            img.save(f.name)
            input_path = f.name

        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            output_path = f.name

        try:
            result = converter.convert(
                input_path,
                output_path,
                image_type="monochrome",
                quality_mode="fast"
            )

            assert result["success"] is True
            assert result["image_type"] == "monochrome"
            assert Path(output_path).exists()

        finally:
            Path(input_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)
