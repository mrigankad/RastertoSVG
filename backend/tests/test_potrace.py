"""Tests for Potrace engine."""

import tempfile
from pathlib import Path

import pytest
from PIL import Image

from app.services.potrace_engine import PotraceEngine


class TestPotraceEngine:
    """Test cases for PotraceEngine class."""

    @pytest.fixture
    def engine(self):
        """Create a Potrace engine instance."""
        return PotraceEngine()

    @pytest.fixture
    def sample_bw_image(self):
        """Create a sample black and white image."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new('1', (100, 100), color=1)
            # Add some black squares
            for i in range(25, 75):
                for j in range(25, 75):
                    img.putpixel((i, j), 0)
            img.save(f.name)
            return f.name

    @pytest.fixture
    def sample_gray_image(self):
        """Create a sample grayscale image."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = Image.new('L', (100, 100), color=200)
            # Add some darker regions
            for i in range(25, 75):
                for j in range(25, 75):
                    img.putpixel((i, j), 50)
            img.save(f.name)
            return f.name

    def test_is_available(self, engine):
        """Test availability check."""
        result = engine.is_available()
        assert isinstance(result, bool)

    def test_supported_formats(self, engine):
        """Test supported formats list."""
        assert ".png" in engine.supported_formats
        assert ".jpg" in engine.supported_formats
        assert ".bmp" in engine.supported_formats

    def test_get_version(self, engine):
        """Test getting version."""
        version = engine.get_version()
        assert isinstance(version, str)

    def test_convert_file_not_found(self, engine):
        """Test conversion with non-existent file."""
        with pytest.raises(FileNotFoundError):
            engine.convert("/nonexistent/file.png", "/tmp/out.svg")

    def test_convert_unsupported_format(self, engine):
        """Test conversion with unsupported format."""
        with tempfile.NamedTemporaryFile(suffix=".xyz") as f:
            with pytest.raises(ValueError):
                engine.convert(f.name, "/tmp/out.svg")

    def test_convert_grayscale(self, engine, sample_gray_image):
        """Test conversion of grayscale image."""
        if not engine.is_available():
            pytest.skip("Potrace not installed")

        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            output_path = f.name

        try:
            result = engine.convert(
                sample_gray_image,
                output_path,
                threshold=128,
                alphamax=1.0,
            )
            assert result["success"] is True
            assert result["engine"] == "potrace"
            assert Path(output_path).exists()
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_convert_pillow(self, engine, sample_gray_image):
        """Test conversion from PIL Image."""
        if not engine.is_available():
            pytest.skip("Potrace not installed")

        img = Image.open(sample_gray_image)

        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            output_path = f.name

        try:
            result = engine.convert_pillow(img, output_path)
            assert result["success"] is True
            assert Path(output_path).exists()
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_convert_parameters(self, engine, sample_gray_image):
        """Test conversion with different parameters."""
        if not engine.is_available():
            pytest.skip("Potrace not installed")

        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            output_path = f.name

        try:
            result = engine.convert(
                sample_gray_image,
                output_path,
                threshold=100,
                alphamax=0.5,
                turnpolicy="majority",
                turdsize=2,
                opticurve=True,
                opttolerance=0.2,
            )
            assert result["success"] is True
            assert result["alphamax"] == 0.5
            assert result["turnpolicy"] == "majority"
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_auto_threshold(self, engine, sample_gray_image):
        """Test automatic thresholding."""
        img = Image.open(sample_gray_image)
        thresholded = engine._auto_threshold(img)
        assert thresholded is not None
