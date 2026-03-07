"""Tests for VTracer engine."""

import tempfile
from pathlib import Path

import pytest
from PIL import Image

from app.services.vtracer_engine import VTracerEngine


class TestVTracerEngine:
    """Test cases for VTracerEngine class."""

    @pytest.fixture
    def engine(self):
        """Create a VTracer engine instance."""
        return VTracerEngine()

    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Create a simple color image
            img = Image.new('RGB', (100, 100), color='blue')
            # Add some pattern
            for i in range(0, 100, 20):
                for j in range(0, 100, 20):
                    img.putpixel((i, j), (255, 0, 0))
            img.save(f.name)
            return f.name

    def test_is_available(self, engine):
        """Test availability check doesn't crash."""
        # Just ensure it runs without error
        result = engine.is_available()
        assert isinstance(result, bool)

    def test_supported_formats(self, engine):
        """Test supported formats list."""
        assert ".png" in engine.supported_formats
        assert ".jpg" in engine.supported_formats
        assert ".jpeg" in engine.supported_formats

    def test_convert_file_not_found(self, engine):
        """Test conversion with non-existent file."""
        with pytest.raises(FileNotFoundError):
            engine.convert("/nonexistent/file.png", "/tmp/out.svg")

    def test_convert_unsupported_format(self, engine):
        """Test conversion with unsupported format."""
        with tempfile.NamedTemporaryFile(suffix=".xyz") as f:
            with pytest.raises(ValueError):
                engine.convert(f.name, "/tmp/out.svg")

    def test_convert_pillow(self, engine, sample_image):
        """Test conversion from PIL Image."""
        if not engine.is_available():
            pytest.skip("VTracer not installed")

        img = Image.open(sample_image)

        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            output_path = f.name

        try:
            result = engine.convert_pillow(img, output_path)
            assert result["success"] is True
            assert result["engine"] == "vtracer"
            assert Path(output_path).exists()
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_convert_parameters(self, engine, sample_image):
        """Test conversion with different parameters."""
        if not engine.is_available():
            pytest.skip("VTracer not installed")

        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            output_path = f.name

        try:
            result = engine.convert(
                sample_image,
                output_path,
                color_precision=16,
                hierarchical=True,
                mode="splice",
                filter_speckle=4,
            )
            assert result["success"] is True
            assert result["color_precision"] == 16
            assert result["mode"] == "splice"
        finally:
            Path(output_path).unlink(missing_ok=True)
